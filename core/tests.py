from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Professional


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
