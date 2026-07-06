from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from django.views.decorators.http import require_POST
from math import asin, cos, radians, sin, sqrt
from .access import redirect_to_role_dashboard, role_required
from .ai import AiLimitError, generate_estimate
from .models import (
    Category,
    JobRequest,
    Notification,
    Payment,
    PortfolioItem,
    Professional,
    Quote,
    Recharge,
    Service,
    UserProfile,
)
from .forms import (
    AdminClientForm,
    AdminProfessionalForm,
    CustomUserCreationForm,
    PaymentForm,
    PortfolioItemForm,
    QuoteForm,
    RechargeForm,
    ReviewForm,
)
from .services import (
    WorkflowError,
    apply_recharge,
    cancel_assignment,
    confirm_job_completion,
    create_payment,
    create_verified_review,
    mark_job_finished,
    reopen_job,
    select_quote,
    start_job,
    submit_quote,
    update_payment_status,
)
from django.contrib.auth.forms import AuthenticationForm

def parse_coordinate(value, minimum, maximum):
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    return coordinate if minimum <= coordinate <= maximum else None


def haversine_km(lat1, lng1, lat2, lng2):
    radius = 6371
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    return 2 * radius * asin(sqrt(value))


def professionals_in_job_range(job):
    professionals = list(
        Professional.objects.filter(user__isnull=False).exclude(
            available='No disponible temporalmente'
        )
    )
    if job.lat is None or job.lng is None:
        return professionals
    return [
        professional
        for professional in professionals
        if haversine_km(job.lat, job.lng, professional.lat, professional.lng)
        <= professional.coverage_radius_km
    ]

@role_required('ADMIN', 'PROFESSIONAL', 'CLIENT')
def dashboard_redirect(request):
    return redirect_to_role_dashboard(request.user)


@role_required('CLIENT')
def home(request):
    categories = Category.objects.all()
    professionals = list(
        Professional.objects.exclude(available='No disponible temporalmente')
        .select_related('user__profile')
        .prefetch_related('portfolio_items')
    )
    services = Service.objects.all()

    q = request.GET.get('q', '').strip()
    if q:
        query = q.casefold()
        professionals = [
            professional
            for professional in professionals
            if query in professional.name.casefold()
            or query in professional.specialty.casefold()
            or query in professional.about.casefold()
        ]

    client_lat = parse_coordinate(request.GET.get('lat'), -90, 90)
    client_lng = parse_coordinate(request.GET.get('lng'), -180, 180)
    if client_lat is not None and client_lng is not None:
        request.user.profile.lat = client_lat
        request.user.profile.lng = client_lng
        request.user.profile.save(update_fields=['lat', 'lng'])
    else:
        client_lat = request.user.profile.lat
        client_lng = request.user.profile.lng

    if client_lat is not None and client_lng is not None:
        nearby = []
        for professional in professionals:
            distance = haversine_km(client_lat, client_lng, professional.lat, professional.lng)
            professional.display_distance = f'{distance:.1f} km'
            if distance <= professional.coverage_radius_km:
                nearby.append((distance, professional))
        professionals = [professional for _, professional in sorted(nearby, key=lambda item: item[0])]

    map_professionals = [
        {
            'id': professional.id,
            'name': professional.name,
            'specialty': professional.specialty,
            'rating': str(professional.rating),
            'location': professional.location,
            'lat': round(professional.lat, 2),
            'lng': round(professional.lng, 2),
        }
        for professional in professionals
    ]

    return render(request, 'core/home.html', {
        'categories': categories,
        'professionals': professionals,
        'map_professionals': map_professionals,
        'services': services,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'q': q,
        'has_client_location': client_lat is not None and client_lng is not None,
    })

@role_required('CLIENT')
def professional_detail(request, professional_id):
    try:
        professional = (
            Professional.objects.select_related('user__profile')
            .prefetch_related('portfolio_items', 'verified_reviews')
            .get(id=professional_id)
        )
    except Professional.DoesNotExist:
        raise Http404('Profesional no encontrado')
    return render(request, 'core/professional_detail.html', {'professional': professional})

@role_required('CLIENT')
def estimator(request):
    result = None
    if request.method == 'POST':
        brief = request.POST.get('brief', '').strip()
        if len(brief) < 10:
            messages.error(request, 'Describe el trabajo con al menos 10 caracteres.')
            return render(request, 'core/estimator.html', {'result': None})
        try:
            estimate = generate_estimate(request.user, brief)
        except AiLimitError as error:
            messages.error(request, str(error))
            return render(request, 'core/estimator.html', {'result': None})

        result = {
            'brief': brief,
            'technical': estimate['technical'],
            'materials': estimate['materials'],
            'time': estimate['estimated_time'],
            'budget': f"{estimate['estimated_price']} referencial",
            'safety_notes': estimate.get('safety_notes', []),
            'source': estimate.get('source', 'rules'),
        }
        job = JobRequest.objects.create(
            client=request.user,
            title=brief[:100],
            description=brief,
            estimated_price=estimate['estimated_price'],
            estimated_time=estimate['estimated_time'],
            address=request.POST.get('address', '').strip()[:250],
            lat=parse_coordinate(request.POST.get('lat'), -90, 90),
            lng=parse_coordinate(request.POST.get('lng'), -180, 180),
            status='PENDING',
        )
        notifications = [
            Notification(
                recipient=professional.user,
                notif_type='NEW_JOB',
                title='Nuevo trabajo disponible',
                message=f'Se solicita: "{job.title}". Revisa los detalles y cotiza.',
                link='/dashboard/profesional/#job-market',
            )
            for professional in professionals_in_job_range(job)
        ]
        Notification.objects.bulk_create(notifications)
        messages.success(request, 'La solicitud fue creada y ya puede recibir cotizaciones.')
        
    return render(request, 'core/estimator.html', {'result': result})

# FRONTEND ADMIN VIEWS
@role_required('ADMIN')
def admin_panel(request):
    recent_jobs = JobRequest.objects.all().order_by('-created_at')[:5]
    all_pros = Professional.objects.all().count()
    all_clients = UserProfile.objects.filter(role='CLIENT').count()
    active_jobs = JobRequest.objects.exclude(status__in=['COMPLETED', 'CANCELLED']).count()
    processed_payments = Payment.objects.filter(
        status__in=['VERIFIED', 'RELEASED']
    ).aggregate(total=Sum('amount'))['total'] or 0
    active_guarantees = Payment.objects.filter(
        guarantee_status__in=['PENDING', 'ACTIVE']
    ).count()
    metrics = [
        {'label': 'Trabajos activos', 'value': active_jobs, 'trend': 'En operación'},
        {'label': 'Pagos procesados', 'value': f'${processed_payments}', 'trend': 'Verificados'},
        {'label': 'Profesionales', 'value': all_pros, 'trend': 'Registrados'},
        {'label': 'Garantías activas', 'value': active_guarantees, 'trend': 'En seguimiento'},
    ]

    return render(request, 'core/admin_panel.html', {
        'metrics': metrics,
        'recent_jobs': recent_jobs,
        'pros_count': all_pros,
        'clients_count': all_clients,
        'active_guarantees': active_guarantees,
    })

@role_required('ADMIN')
def admin_users(request):
    users = User.objects.all().select_related('profile', 'professional_profile').order_by('-id')
    return render(request, 'core/admin_users.html', {'users_list': users})

@role_required('ADMIN')
def admin_recharges(request):
    form = RechargeForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            recharge = apply_recharge(form.cleaned_data)
            messages.success(
                request,
                f'Se añadieron {recharge.credits_added} créditos a {recharge.professional.name}.',
            )
            return redirect('admin_recharges')
        messages.error(request, 'Revisa los datos de la recarga.')
        
    recharges = Recharge.objects.all().select_related('professional').order_by('-created_at')
    total_ingresos = recharges.aggregate(total=Sum('amount_paid'))['total'] or 0
    
    return render(request, 'core/admin_recharges.html', {
        'form': form,
        'recharges': recharges,
        'total_ingresos': total_ingresos,
    })


@role_required('ADMIN')
def admin_payments(request):
    if request.method == 'POST':
        try:
            update_payment_status(
                request.POST.get('payment_id'),
                request.POST.get('status'),
            )
            messages.success(request, 'Estado del pago actualizado.')
        except (Payment.DoesNotExist, WorkflowError):
            messages.error(request, 'No se pudo actualizar el pago.')
        return redirect('admin_payments')

    payments = Payment.objects.select_related(
        'job',
        'client',
        'professional',
    ).order_by('-created_at')
    return render(request, 'core/admin_payments.html', {'payments': payments})


@role_required('ADMIN')
def admin_add_professional(request):
    if request.method == 'POST':
        form = AdminProfessionalForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            
            # Crear User
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
            
            # Configurar Perfil
            profile = user.profile
            profile.role = 'PROFESSIONAL'
            profile.phone = form.cleaned_data['phone']
            profile.save()
            
            # Crear Professional
            Professional.objects.create(
                user=user,
                name=f"{first_name} {last_name}".strip() or username,
                specialty=form.cleaned_data['specialty'],
                experience=form.cleaned_data['experience'],
                level=form.cleaned_data['level'],
                available=form.cleaned_data['available'],
                location=form.cleaned_data['location'],
                about=form.cleaned_data['about'],
                initials=username[:2].upper()
            )
            
            messages.success(request, f'Profesional {username} creado con éxito.')
            return redirect('admin_users')
    else:
        form = AdminProfessionalForm()
        
    return render(request, 'core/admin_pro_form.html', {'form': form, 'title': 'Agregar Profesional'})

@role_required('ADMIN')
def admin_edit_professional(request, user_id):
    user = get_object_or_404(User, id=user_id)
    pro = get_object_or_404(Professional, user=user)
    
    if request.method == 'POST':
        form = AdminProfessionalForm(request.POST, user_instance=user, pro_instance=pro)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()
            
            profile = user.profile
            profile.phone = form.cleaned_data['phone']
            profile.save()
            
            pro.name = f"{user.first_name} {user.last_name}".strip() or user.username
            pro.specialty = form.cleaned_data['specialty']
            pro.experience = form.cleaned_data['experience']
            pro.level = form.cleaned_data['level']
            pro.available = form.cleaned_data['available']
            pro.location = form.cleaned_data['location']
            pro.about = form.cleaned_data['about']
            pro.save()
            
            messages.success(request, f'Profesional {user.username} modificado con éxito.')
            return redirect('admin_users')
    else:
        form = AdminProfessionalForm(user_instance=user, pro_instance=pro)
        
    return render(request, 'core/admin_pro_form.html', {'form': form, 'title': f'Editar Profesional: {user.username}'})

@role_required('ADMIN')
def admin_add_client(request):
    if request.method == 'POST':
        form = AdminClientForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
            
            profile = user.profile
            profile.role = 'CLIENT'
            profile.phone = form.cleaned_data['phone']
            profile.save()
            
            messages.success(request, f'Cliente {username} creado con éxito.')
            return redirect('admin_users')
    else:
        form = AdminClientForm()
        
    return render(request, 'core/admin_client_form.html', {'form': form, 'title': 'Agregar Cliente'})

@role_required('ADMIN')
def admin_edit_client(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminClientForm(request.POST, user_instance=user)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()
            
            profile = user.profile
            profile.phone = form.cleaned_data['phone']
            profile.save()
            
            messages.success(request, f'Cliente {user.username} modificado con éxito.')
            return redirect('admin_users')
    else:
        form = AdminClientForm(user_instance=user)
        
    return render(request, 'core/admin_client_form.html', {'form': form, 'title': f'Editar Cliente: {user.username}'})

@role_required('ADMIN')
@require_POST
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.delete()
    messages.success(request, f'Usuario {username} eliminado del sistema.')
    return redirect('admin_users')

# END FRONTEND ADMIN VIEWS

@role_required('CLIENT')
def client_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'select_quote':
                select_quote(request.user, request.POST.get('quote_id'))
                messages.success(request, 'Cotización seleccionada. Ya puedes registrar el pago.')
            elif action == 'reopen_job':
                reopen_job(request.user, request.POST.get('job_id'))
                messages.success(request, 'La solicitud volvió a recibir cotizaciones.')
            elif action in {'confirm_completion', 'complete_job'}:
                confirm_job_completion(request.user, request.POST.get('job_id'))
                messages.success(request, 'Trabajo confirmado. Ahora puedes dejar una reseña.')
            elif action == 'submit_review':
                form = ReviewForm(request.POST)
                if not form.is_valid():
                    raise WorkflowError('Revisa los datos de la reseña.')
                create_verified_review(
                    request.user,
                    request.POST.get('job_id'),
                    form.cleaned_data,
                )
                messages.success(request, 'Gracias. Tu reseña verificada fue publicada.')
            elif action == 'record_payment':
                form = PaymentForm(request.POST)
                if not form.is_valid():
                    raise WorkflowError('Revisa el comprobante de pago.')
                create_payment(
                    request.user,
                    request.POST.get('job_id'),
                    form.cleaned_data,
                )
                messages.success(request, 'Comprobante registrado para verificación.')
        except (
            JobRequest.DoesNotExist,
            Payment.DoesNotExist,
            Quote.DoesNotExist,
            WorkflowError,
        ) as error:
            messages.error(request, str(error) or 'No se pudo completar la acción.')
        return redirect('client_dashboard')

    requests = (
        JobRequest.objects.filter(client=request.user)
        .select_related('professional', 'selected_quote', 'payment', 'review')
        .prefetch_related('quotes__professional')
        .order_by('-created_at')
    )
    return render(request, 'core/client_dashboard.html', {
        'requests': requests,
        'payment_form': PaymentForm(),
        'review_form': ReviewForm(),
    })

@role_required('PROFESSIONAL')
def professional_dashboard(request):
    try:
        professional = request.user.professional_profile
    except Professional.DoesNotExist:
        professional = Professional.objects.create(
            user=request.user,
            name=request.user.username,
            specialty="General",
            initials=request.user.username[:2].upper(),
            location="Guayaquil"
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'update_profile':
                professional.available = request.POST.get('available', professional.available)
                professional.specialty = request.POST.get('specialty', professional.specialty)[:200]
                professional.about = request.POST.get('about', professional.about)[:3000]
                professional.location = request.POST.get('location', professional.location)[:200]
                professional.coverage_radius_km = max(
                    1,
                    min(100, int(request.POST.get('coverage_radius_km', 10))),
                )
                lat = parse_coordinate(request.POST.get('lat'), -90, 90)
                lng = parse_coordinate(request.POST.get('lng'), -180, 180)
                if lat is not None and lng is not None:
                    professional.lat = lat
                    professional.lng = lng
                professional.save()
                messages.success(request, 'Perfil actualizado correctamente.')
            elif action == 'submit_quote':
                form = QuoteForm(request.POST)
                if not form.is_valid():
                    raise WorkflowError('Revisa monto, tiempo y mensaje de la cotización.')
                submit_quote(
                    professional.id,
                    request.POST.get('job_id'),
                    form.cleaned_data,
                )
                messages.success(request, 'Cotización enviada. Se descontó un crédito.')
            elif action == 'start_job':
                start_job(professional.id, request.POST.get('job_id'))
                messages.success(request, 'Trabajo iniciado.')
            elif action in {'mark_finished', 'complete_job'}:
                mark_job_finished(professional.id, request.POST.get('job_id'))
                messages.success(request, 'Trabajo enviado al cliente para confirmación.')
            elif action == 'cancel_job':
                cancel_assignment(professional.id, request.POST.get('job_id'))
                messages.success(request, 'Asignación cancelada y crédito devuelto.')
            elif action == 'add_portfolio':
                form = PortfolioItemForm(request.POST)
                if not form.is_valid():
                    raise WorkflowError('Revisa la URL y descripción del portafolio.')
                item = form.save(commit=False)
                item.professional = professional
                item.save()
                messages.success(request, 'Imagen añadida al portafolio.')
            elif action == 'remove_portfolio':
                PortfolioItem.objects.filter(
                    pk=request.POST.get('item_id'),
                    professional=professional,
                ).delete()
                messages.success(request, 'Elemento eliminado del portafolio.')
        except (JobRequest.DoesNotExist, Professional.DoesNotExist, WorkflowError, ValueError) as error:
            messages.error(request, str(error) or 'No se pudo completar la acción.')
        return redirect('professional_dashboard')

    jobs = (
        JobRequest.objects.filter(professional=professional)
        .select_related('client__profile', 'selected_quote')
        .order_by('-created_at')
    )
    pending_jobs = list(
        JobRequest.objects.filter(status__in=['PENDING', 'QUOTED'])
        .select_related('client__profile')
        .prefetch_related('quotes')
        .order_by('-created_at')
    )
    pending_jobs = [
        job
        for job in pending_jobs
        if job.lat is None
        or job.lng is None
        or haversine_km(job.lat, job.lng, professional.lat, professional.lng)
        <= professional.coverage_radius_km
    ]
    own_quotes = {
        quote.job_id: quote
        for quote in professional.quotes.filter(job__in=pending_jobs)
    }
    for job in pending_jobs:
        job.my_quote = own_quotes.get(job.id)

    return render(request, 'core/professional_dashboard.html', {
        'professional': professional,
        'jobs': jobs,
        'pending_jobs': pending_jobs,
        'quote_form': QuoteForm(),
        'portfolio_form': PortfolioItemForm(),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect_to_role_dashboard(request.user)
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.username}! Tu cuenta ha sido creada.')
            return redirect_to_role_dashboard(user)
        else:
            messages.error(request, 'Error al crear la cuenta. Revisa los datos.')
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect_to_role_dashboard(request.user)
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Has iniciado sesión como {username}.')
                return redirect_to_role_dashboard(user)
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
        
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


def notifications_api(request):
    """Return unread notifications as JSON for the notification bell."""
    if not request.user.is_authenticated:
        return JsonResponse({'notifications': [], 'unread_count': 0})
    
    unread = Notification.objects.filter(recipient=request.user, is_read=False)
    notifs = list(unread[:20])
    data = {
        'unread_count': unread.count(),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notif_type,
                'link': n.link if n.link and n.link.startswith('/') else '/',
                'created': n.created_at.strftime('%d/%m/%Y %H:%M'),
            } for n in notifs
        ]
    }
    return JsonResponse(data)


@require_POST
def notifications_mark_read(request):
    """Mark one or all notifications as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=401)
    
    notif_id = request.POST.get('id')
    if notif_id:
        Notification.objects.filter(id=notif_id, recipient=request.user).update(is_read=True)
    else:
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    return JsonResponse({'ok': True})


def offline(request):
    return render(request, 'core/offline.html')


def serve_sw(request):
    """Serve the service worker from root scope."""
    import os
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    from django.http import HttpResponse
    return HttpResponse(content, content_type='application/javascript')


def serve_manifest(request):
    """Serve manifest.json from root."""
    import os
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    with open(manifest_path, 'r') as f:
        content = f.read()
    from django.http import HttpResponse
    return HttpResponse(content, content_type='application/manifest+json')
