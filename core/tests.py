from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from unittest import skipUnless

from .forms import RechargeForm
from .models import JobRequest, Payment, Professional, Quote, Recharge, Review
from .services import (
    WorkflowError,
    apply_recharge,
    confirm_job_completion,
    create_payment,
    create_verified_review,
    mark_job_finished,
    select_quote,
    start_job,
    submit_quote,
)


class RoleAccessTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='cliente',
            password='test-password',
        )

        self.professional_user = User.objects.create_user(
            username='profesional',
            password='test-password',
        )
        self.professional_user.profile.role = 'PROFESSIONAL'
        self.professional_user.profile.save()
        Professional.objects.create(
            user=self.professional_user,
            name='Profesional de prueba',
            specialty='Electricidad',
            level='Profesional',
            initials='PP',
            location='Guayaquil',
            about='Perfil usado para pruebas de acceso.',
        )

        self.admin_user = User.objects.create_superuser(
            username='administrador',
            email='admin@example.com',
            password='test-password',
        )

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('login'))

    def test_client_only_accesses_client_experience(self):
        self.client.force_login(self.client_user)

        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('client_dashboard')).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse('professional_dashboard')),
            reverse('client_dashboard'),
        )
        self.assertRedirects(
            self.client.get(reverse('admin_panel')),
            reverse('client_dashboard'),
        )

    def test_professional_only_accesses_professional_experience(self):
        self.client.force_login(self.professional_user)

        self.assertEqual(
            self.client.get(reverse('professional_dashboard')).status_code,
            200,
        )
        self.assertRedirects(
            self.client.get(reverse('home')),
            reverse('professional_dashboard'),
        )
        self.assertRedirects(
            self.client.get(reverse('estimator')),
            reverse('professional_dashboard'),
        )
        self.assertRedirects(
            self.client.get(reverse('admin_panel')),
            reverse('professional_dashboard'),
        )

    def test_admin_only_accesses_administration_experience(self):
        self.client.force_login(self.admin_user)

        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse('home')),
            reverse('admin_panel'),
        )
        self.assertRedirects(
            self.client.get(reverse('client_dashboard')),
            reverse('admin_panel'),
        )
        self.assertRedirects(
            self.client.get(reverse('professional_dashboard')),
            reverse('admin_panel'),
        )

    def test_dashboard_route_redirects_each_role(self):
        cases = (
            (self.client_user, 'client_dashboard'),
            (self.professional_user, 'professional_dashboard'),
            (self.admin_user, 'admin_panel'),
        )

        for user, destination in cases:
            self.client.force_login(user)
            self.assertRedirects(
                self.client.get(reverse('dashboard_redirect')),
                reverse(destination),
            )
            self.client.logout()

    def test_authenticated_login_page_redirects_by_role(self):
        cases = (
            (self.client_user, 'client_dashboard'),
            (self.professional_user, 'professional_dashboard'),
            (self.admin_user, 'admin_panel'),
        )

        for user, destination in cases:
            self.client.force_login(user)
            self.assertRedirects(
                self.client.get(reverse('login')),
                reverse(destination),
            )
            self.client.logout()


class MarketplaceWorkflowTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user('cliente-flow', password='test-password')
        self.pro_user = User.objects.create_user('pro-flow', password='test-password')
        self.pro_user.profile.role = 'PROFESSIONAL'
        self.pro_user.profile.save()
        self.professional = Professional.objects.create(
            user=self.pro_user,
            name='Profesional Flow',
            specialty='Electricidad',
            level='Profesional',
            initials='PF',
            location='Guayaquil',
            about='Prueba',
            credits=3,
        )
        self.other_user = User.objects.create_user('pro-other', password='test-password')
        self.other_user.profile.role = 'PROFESSIONAL'
        self.other_user.profile.save()
        self.other_professional = Professional.objects.create(
            user=self.other_user,
            name='Otro Profesional',
            specialty='Pintura',
            level='Profesional',
            initials='OP',
            location='Guayaquil',
            about='Prueba',
            credits=3,
        )
        self.job = JobRequest.objects.create(
            client=self.client_user,
            title='Reparar instalación',
            description='Revisar instalación eléctrica',
            status='PENDING',
        )

    def quote(self, professional=None, amount='80.00'):
        professional = professional or self.professional
        return submit_quote(
            professional.id,
            self.job.id,
            {
                'amount': amount,
                'estimated_days': 2,
                'message': 'Incluye materiales básicos.',
            },
        )

    def test_quote_charges_one_credit_only_once(self):
        quote = self.quote()
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.credits, 2)

        submit_quote(
            self.professional.id,
            self.job.id,
            {'amount': '75.00', 'estimated_days': 1, 'message': 'Actualizada'},
        )
        self.professional.refresh_from_db()
        quote.refresh_from_db()
        self.assertEqual(self.professional.credits, 2)
        self.assertEqual(str(quote.amount), '75.00')

    def test_only_one_quote_can_be_selected(self):
        first = self.quote()
        second = self.quote(self.other_professional, '90.00')

        select_quote(self.client_user, first.id)
        with self.assertRaises(WorkflowError):
            select_quote(self.client_user, second.id)

        self.job.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.job.selected_quote, first)
        self.assertEqual(first.status, 'ACCEPTED')
        self.assertEqual(second.status, 'REJECTED')

    def test_formal_job_states_and_verified_review(self):
        quote = self.quote()
        select_quote(self.client_user, quote.id)
        start_job(self.professional.id, self.job.id)
        mark_job_finished(self.professional.id, self.job.id)
        confirm_job_completion(self.client_user, self.job.id)
        review = create_verified_review(
            self.client_user,
            self.job.id,
            {'rating': 5, 'punctuality': 4, 'quality': 5, 'comment': 'Excelente'},
        )

        self.job.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(self.job.status, 'COMPLETED')
        self.assertEqual(review.job, self.job)
        self.assertEqual(self.professional.rating, 5)
        self.assertEqual(self.professional.punctuality, 80)
        self.assertEqual(Review.objects.count(), 1)

    def test_payment_uses_selected_quote_amount_and_guarantee(self):
        quote = self.quote(amount='125.50')
        select_quote(self.client_user, quote.id)
        payment = create_payment(
            self.client_user,
            self.job.id,
            {
                'method': 'TRANSFER',
                'receipt_reference': 'TRX-123',
                'request_guarantee': True,
            },
        )
        self.assertEqual(str(payment.amount), '125.50')
        self.assertEqual(payment.guarantee_status, 'PENDING')

    def test_recharge_form_rejects_negative_values(self):
        form = RechargeForm({
            'professional': self.professional.id,
            'amount_paid': '-1',
            'credits_added': '-5',
            'payment_method': 'TRANSFERENCIA',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(Recharge.objects.count(), 0)

    def test_valid_recharge_is_atomic(self):
        form = RechargeForm({
            'professional': self.professional.id,
            'amount_paid': '10.00',
            'credits_added': '8',
            'payment_method': 'TRANSFERENCIA',
        })
        self.assertTrue(form.is_valid(), form.errors)
        apply_recharge(form.cleaned_data)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.credits, 11)
        self.assertEqual(Recharge.objects.count(), 1)

    def test_admin_delete_requires_post(self):
        admin = User.objects.create_superuser('admin-flow', 'admin@example.com', 'password')
        target = User.objects.create_user('delete-me', password='password')
        self.client.force_login(admin)
        url = reverse('admin_delete_user', args=[target.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(url), reverse('admin_users'))
        self.assertFalse(User.objects.filter(pk=target.id).exists())

    def test_notification_api_sanitizes_external_links(self):
        from .models import Notification

        Notification.objects.create(
            recipient=self.client_user,
            title='Aviso',
            message='<img src=x onerror=alert(1)>',
            link='javascript:alert(1)',
        )
        self.client.force_login(self.client_user)
        response = self.client.get(reverse('notifications_api'))
        self.assertEqual(response.json()['notifications'][0]['link'], '/')


@skipUnless(connection.vendor == 'postgresql', 'La concurrencia real requiere PostgreSQL.')
class ConcurrentQuoteSelectionTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_selection_has_one_winner(self):
        import threading
        from django.db import close_old_connections

        client_user = User.objects.create_user('concurrent-client', password='password')
        job = JobRequest.objects.create(client=client_user, title='Trabajo', description='Detalle')
        quotes = []
        for index in range(2):
            user = User.objects.create_user(f'concurrent-pro-{index}', password='password')
            user.profile.role = 'PROFESSIONAL'
            user.profile.save()
            professional = Professional.objects.create(
                user=user,
                name=f'Pro {index}',
                specialty='General',
                level='Profesional',
                initials=f'P{index}',
                location='Guayaquil',
                about='Prueba',
                credits=2,
            )
            quotes.append(submit_quote(
                professional.id,
                job.id,
                {'amount': 50 + index, 'estimated_days': 1, 'message': ''},
            ))

        barrier = threading.Barrier(2)
        results = []

        def select(quote_id):
            close_old_connections()
            barrier.wait()
            try:
                select_quote(User.objects.get(pk=client_user.pk), quote_id)
                results.append('ok')
            except WorkflowError:
                results.append('rejected')
            finally:
                close_old_connections()

        threads = [threading.Thread(target=select, args=(quote.id,)) for quote in quotes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        job.refresh_from_db()
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(Quote.objects.filter(job=job, status='ACCEPTED').count(), 1)
