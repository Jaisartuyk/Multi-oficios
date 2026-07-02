from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('', views.home, name='home'),
    path('profesional/<int:professional_id>/', views.professional_detail, name='professional_detail'),
    path('cotizador/', views.estimator, name='estimator'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/usuarios/', views.admin_users, name='admin_users'),
    path('admin-panel/profesionales/crear/', views.admin_add_professional, name='admin_add_professional'),
    path('admin-panel/profesionales/editar/<int:user_id>/', views.admin_edit_professional, name='admin_edit_professional'),
    path('admin-panel/clientes/crear/', views.admin_add_client, name='admin_add_client'),
    path('admin-panel/clientes/editar/<int:user_id>/', views.admin_edit_client, name='admin_edit_client'),
    path('admin-panel/usuarios/eliminar/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('dashboard/cliente/', views.client_dashboard, name='client_dashboard'),
    path('dashboard/profesional/', views.professional_dashboard, name='professional_dashboard'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # PWA
    path('sw.js', views.serve_sw, name='service_worker'),
    path('manifest.json', views.serve_manifest, name='manifest'),
    # Notifications API
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/read/', views.notifications_mark_read, name='notifications_mark_read'),
]
