from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


ROLE_DASHBOARDS = {
    'ADMIN': 'admin_panel',
    'PROFESSIONAL': 'professional_dashboard',
    'CLIENT': 'client_dashboard',
}


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'ADMIN'

    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', 'CLIENT')


def dashboard_name_for(user):
    return ROLE_DASHBOARDS.get(get_user_role(user), 'login')


def redirect_to_role_dashboard(user):
    return redirect('feed')


def role_required(*allowed_roles):
    allowed = set(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if get_user_role(request.user) not in allowed:
                messages.error(request, 'No tienes permisos para acceder a esa seccion.')
                return redirect_to_role_dashboard(request.user)

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
