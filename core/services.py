from django.db import transaction
from django.db.models import Avg, F
from django.utils import timezone

from .models import JobRequest, Notification, Payment, Professional, Quote, Recharge, Review


class WorkflowError(Exception):
    pass


def notify(recipient, notif_type, title, message, link):
    if recipient:
        Notification.objects.create(
            recipient=recipient,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link,
        )


@transaction.atomic
def apply_recharge(cleaned_data):
    professional = Professional.objects.select_for_update().get(
        pk=cleaned_data['professional'].pk
    )
    credits = cleaned_data['credits_added']
    professional.credits = F('credits') + credits
    professional.save(update_fields=['credits'])
    professional.refresh_from_db(fields=['credits'])

    recharge = Recharge.objects.create(
        professional=professional,
        amount_paid=cleaned_data['amount_paid'],
        credits_added=credits,
        payment_method=cleaned_data['payment_method'],
    )
    notify(
        professional.user,
        'CREDITS',
        'Recarga confirmada',
        f'Se añadieron {credits} créditos a tu cuenta.',
        '/dashboard/profesional/',
    )
    return recharge


@transaction.atomic
def submit_quote(professional_id, job_id, cleaned_data):
    professional = Professional.objects.select_for_update().get(pk=professional_id)
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.status not in {'PENDING', 'QUOTED'} or job.professional_id:
        raise WorkflowError('Este trabajo ya no recibe cotizaciones.')

    quote = Quote.objects.select_for_update().filter(
        job=job,
        professional=professional,
    ).first()
    is_new = quote is None
    if is_new and professional.credits <= 0:
        raise WorkflowError('No tienes créditos suficientes para cotizar.')

    if is_new:
        professional.credits = F('credits') - 1
        professional.save(update_fields=['credits'])
        quote = Quote(job=job, professional=professional)

    quote.amount = cleaned_data['amount']
    quote.estimated_days = cleaned_data['estimated_days']
    quote.message = cleaned_data.get('message', '')
    quote.status = 'SUBMITTED'
    quote.save()

    if job.status == 'PENDING':
        job.status = 'QUOTED'
        job.save(update_fields=['status', 'updated_at'])

    notify(
        job.client,
        'SYSTEM',
        'Nueva cotización',
        f'{professional.name} envió una cotización para "{job.title}".',
        '/dashboard/cliente/',
    )
    return quote


@transaction.atomic
def select_quote(client, quote_id):
    quote = Quote.objects.select_for_update().select_related('job', 'professional').get(
        pk=quote_id
    )
    job = JobRequest.objects.select_for_update().get(pk=quote.job_id)
    if job.client_id != client.id:
        raise WorkflowError('No puedes seleccionar una cotización de otro cliente.')
    if job.status not in {'PENDING', 'QUOTED'} or quote.status != 'SUBMITTED':
        raise WorkflowError('La cotización ya no está disponible.')

    job.professional = quote.professional
    job.selected_quote = quote
    job.status = 'ACCEPTED'
    job.save(update_fields=['professional', 'selected_quote', 'status', 'updated_at'])
    quote.status = 'ACCEPTED'
    quote.save(update_fields=['status', 'updated_at'])
    Quote.objects.filter(job=job, status='SUBMITTED').exclude(pk=quote.pk).update(
        status='REJECTED'
    )

    notify(
        quote.professional.user,
        'JOB_ACCEPTED',
        'Tu cotización fue seleccionada',
        f'El cliente seleccionó tu propuesta para "{job.title}".',
        '/dashboard/profesional/#my-jobs',
    )
    return job


@transaction.atomic
def start_job(professional_id, job_id):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.professional_id != professional_id or job.status != 'ACCEPTED':
        raise WorkflowError('Este trabajo no puede iniciarse.')
    job.status = 'IN_PROGRESS'
    job.save(update_fields=['status', 'updated_at'])
    notify(
        job.client,
        'SYSTEM',
        'Trabajo iniciado',
        f'El profesional inició "{job.title}".',
        '/dashboard/cliente/',
    )
    return job


@transaction.atomic
def mark_job_finished(professional_id, job_id):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.professional_id != professional_id or job.status not in {'ACCEPTED', 'IN_PROGRESS'}:
        raise WorkflowError('Este trabajo no puede marcarse como finalizado.')
    job.status = 'AWAITING_CONFIRMATION'
    job.save(update_fields=['status', 'updated_at'])
    notify(
        job.client,
        'SYSTEM',
        'Trabajo pendiente de confirmación',
        f'El profesional terminó "{job.title}". Confirma el resultado.',
        '/dashboard/cliente/',
    )
    return job


@transaction.atomic
def confirm_job_completion(client, job_id):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.client_id != client.id or job.status != 'AWAITING_CONFIRMATION':
        raise WorkflowError('Este trabajo no puede confirmarse.')
    job.status = 'COMPLETED'
    job.save(update_fields=['status', 'updated_at'])
    Professional.objects.filter(pk=job.professional_id).update(jobs=F('jobs') + 1)

    payment = Payment.objects.select_for_update().filter(job=job).first()
    if payment and payment.status == 'VERIFIED':
        payment.status = 'RELEASED'
        if payment.guarantee_status == 'PENDING':
            payment.guarantee_status = 'ACTIVE'
        payment.save(update_fields=['status', 'guarantee_status'])

    notify(
        job.professional.user if job.professional else None,
        'SYSTEM',
        'Trabajo confirmado',
        f'El cliente confirmó la finalización de "{job.title}".',
        '/dashboard/profesional/#my-jobs',
    )
    return job


@transaction.atomic
def reopen_job(client, job_id):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.client_id != client.id or job.status not in {
        'ACCEPTED',
        'IN_PROGRESS',
        'AWAITING_CONFIRMATION',
    }:
        raise WorkflowError('Este trabajo no puede reabrirse.')

    professional = None
    if job.professional_id:
        professional = Professional.objects.select_for_update().get(pk=job.professional_id)
        professional.credits = F('credits') + 1
        professional.save(update_fields=['credits'])
    if job.selected_quote_id:
        Quote.objects.filter(pk=job.selected_quote_id).update(status='WITHDRAWN')
    Quote.objects.filter(job=job, status='REJECTED').update(status='SUBMITTED')

    old_user = professional.user if professional else None
    job.professional = None
    job.selected_quote = None
    job.status = 'QUOTED' if Quote.objects.filter(job=job, status='SUBMITTED').exists() else 'PENDING'
    job.save(update_fields=['professional', 'selected_quote', 'status', 'updated_at'])
    notify(
        old_user,
        'JOB_REOPENED',
        'Trabajo reabierto',
        f'El cliente reabrió "{job.title}". El crédito fue devuelto.',
        '/dashboard/profesional/#job-market',
    )
    return job


@transaction.atomic
def cancel_assignment(professional_id, job_id):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.professional_id != professional_id or job.status not in {'ACCEPTED', 'IN_PROGRESS'}:
        raise WorkflowError('Esta asignación no puede cancelarse.')
    professional = Professional.objects.select_for_update().get(pk=professional_id)
    professional.credits = F('credits') + 1
    professional.save(update_fields=['credits'])

    if job.selected_quote_id:
        Quote.objects.filter(pk=job.selected_quote_id).update(status='WITHDRAWN')
    Quote.objects.filter(job=job, status='REJECTED').update(status='SUBMITTED')
    job.professional = None
    job.selected_quote = None
    job.status = 'QUOTED' if Quote.objects.filter(job=job, status='SUBMITTED').exists() else 'PENDING'
    job.save(update_fields=['professional', 'selected_quote', 'status', 'updated_at'])
    notify(
        job.client,
        'JOB_REOPENED',
        'Asignación cancelada',
        f'{professional.name} liberó "{job.title}". Volvió a cotizaciones.',
        '/dashboard/cliente/',
    )
    return job


@transaction.atomic
def create_payment(client, job_id, cleaned_data):
    job = JobRequest.objects.select_for_update().select_related(
        'professional',
        'selected_quote',
    ).get(pk=job_id)
    if job.client_id != client.id or not job.professional_id or not job.selected_quote_id:
        raise WorkflowError('El trabajo todavía no tiene una cotización seleccionada.')
    if job.status not in {'ACCEPTED', 'IN_PROGRESS', 'AWAITING_CONFIRMATION'}:
        raise WorkflowError('No se puede registrar un pago para este trabajo.')
    if Payment.objects.filter(job=job).exists():
        raise WorkflowError('Este trabajo ya tiene un pago registrado.')

    return Payment.objects.create(
        job=job,
        client=client,
        professional=job.professional,
        amount=job.selected_quote.amount,
        method=cleaned_data['method'],
        receipt_reference=cleaned_data['receipt_reference'],
        receipt_url=cleaned_data.get('receipt_url', ''),
        guarantee_status='PENDING' if cleaned_data.get('request_guarantee') else 'NOT_REQUESTED',
    )


@transaction.atomic
def update_payment_status(payment_id, status):
    allowed = {'VERIFIED', 'RELEASED', 'REFUNDED'}
    if status not in allowed:
        raise WorkflowError('Estado de pago inválido.')
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    payment.status = status
    if status == 'VERIFIED':
        payment.verified_at = timezone.now()
        if payment.guarantee_status == 'PENDING':
            payment.guarantee_status = 'ACTIVE'
    elif status == 'REFUNDED' and payment.guarantee_status == 'ACTIVE':
        payment.guarantee_status = 'RESOLVED'
    payment.save(update_fields=['status', 'verified_at', 'guarantee_status'])
    notify(
        payment.client,
        'SYSTEM',
        'Pago actualizado',
        f'El pago de "{payment.job.title}" ahora está {payment.get_status_display().lower()}.',
        '/dashboard/cliente/',
    )
    return payment


@transaction.atomic
def create_verified_review(client, job_id, cleaned_data):
    job = JobRequest.objects.select_for_update().get(pk=job_id)
    if job.client_id != client.id or job.status != 'COMPLETED' or not job.professional_id:
        raise WorkflowError('Este trabajo no admite una reseña.')
    if Review.objects.filter(job=job).exists():
        raise WorkflowError('Este trabajo ya fue calificado.')

    review = Review.objects.create(
        job=job,
        client=client,
        professional=job.professional,
        **cleaned_data,
    )
    aggregate = Review.objects.filter(professional=job.professional).aggregate(
        rating=Avg('rating'),
        punctuality=Avg('punctuality'),
    )
    Professional.objects.filter(pk=job.professional_id).update(
        rating=round(aggregate['rating'] or 5, 1),
        punctuality=round((aggregate['punctuality'] or 5) * 20),
    )
    return review
