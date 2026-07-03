from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.views.decorators.http import require_POST
from .access import redirect_to_role_dashboard, role_required
from .models import Category, Professional, Service, JobRequest, UserProfile, Notification, Recharge
from .forms import CustomUserCreationForm, AdminProfessionalForm, AdminClientForm
from django.contrib.auth.forms import AuthenticationForm

ADMIN_METRICS = [
    {'label': 'Trabajos activos', 'value': '1,248', 'trend': '+18%'},
    {'label': 'Pagos procesados', 'value': '$84.2K', 'trend': '+12%'},
    {'label': 'Profesionales verificados', 'value': '7,430', 'trend': '+31%'},
    {'label': 'Fraude prevenido', 'value': '96 casos', 'trend': '-9%'},
]

@role_required('ADMIN', 'PROFESSIONAL', 'CLIENT')
def dashboard_redirect(request):
    return redirect_to_role_dashboard(request.user)


@role_required('CLIENT')
def home(request):
    categories = Category.objects.all()
    # Filter out professionals who are not available
    professionals = Professional.objects.exclude(available='No disponible temporalmente')
    services = Service.objects.all()

    q = request.GET.get('q', '').strip()
    if q:
        professionals = professionals.filter(
            models.Q(name__icontains=q) |
            models.Q(specialty__icontains=q) |
            models.Q(about__icontains=q)
        )

    return render(request, 'core/home.html', {
        'categories': categories,
        'professionals': professionals,
        'services': services,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'q': q,
    })

@role_required('CLIENT')
def professional_detail(request, professional_id):
    try:
        professional = Professional.objects.get(id=professional_id)
    except Professional.DoesNotExist:
        raise Http404('Profesional no encontrado')
    return render(request, 'core/professional_detail.html', {'professional': professional})

@role_required('CLIENT')
def estimator(request):
    result = None
    if request.method == 'POST':
        brief = request.POST.get('brief', '').strip() or 'Reparación general del hogar'
        
        estimated_price = '$45 - $150'
        estimated_time = '2 a 6 horas'
        if 'pintar' in brief.lower() or 'pintura' in brief.lower():
            estimated_price = '$180 - $500'
            estimated_time = '1 a 3 días'
        elif 'electric' in brief.lower() or 'luz' in brief.lower() or 'corto' in brief.lower():
            estimated_price = '$35 - $110'
            estimated_time = '2 a 4 horas'
        elif 'fuga' in brief.lower() or 'tubo' in brief.lower() or 'agua' in brief.lower():
            estimated_price = '$25 - $70'
            estimated_time = '1 a 3 horas'
            
        result = {
            'brief': brief,
            'technical': 'La IA detecta un trabajo de mantenimiento residencial con evaluación previa, protección de área y verificación final.',
            'materials': ['Material principal según el oficio', 'Selladores o fijaciones', 'Equipo de seguridad', 'Limpieza post-servicio'],
            'time': estimated_time,
            'budget': f'{estimated_price} referencial',
        }
        
        JobRequest.objects.create(
            client=request.user,
            title=brief[:100],
            description=brief,
            estimated_price=estimated_price,
            estimated_time=estimated_time,
            status='PENDING'
        )
        messages.success(request, '¡Tu cotización ha sido procesada y guardada en tu panel!')
        
    return render(request, 'core/estimator.html', {'result': result})

# FRONTEND ADMIN VIEWS
@role_required('ADMIN')
def admin_panel(request):
    recent_jobs = JobRequest.objects.all().order_by('-created_at')[:5]
    all_pros = Professional.objects.all().count()
    all_clients = UserProfile.objects.filter(role='CLIENT').count()

    return render(request, 'core/admin_panel.html', {
        'metrics': ADMIN_METRICS,
        'recent_jobs': recent_jobs,
        'pros_count': all_pros,
        'clients_count': all_clients
    })

@role_required('ADMIN')
def admin_users(request):
    users = User.objects.all().select_related('profile', 'professional_profile').order_by('-id')
    return render(request, 'core/admin_users.html', {'users_list': users})

@role_required('ADMIN')
def admin_recharges(request):
    if request.method == 'POST':
        pro_id = request.POST.get('professional_id')
        amount = request.POST.get('amount')
        credits = request.POST.get('credits')
        method = request.POST.get('method')
        
        pro = get_object_or_404(Professional, id=pro_id)
        pro.credits += int(credits)
        pro.save()
        
        Recharge.objects.create(
            professional=pro,
            amount_paid=amount,
            credits_added=credits,
            payment_method=method
        )
        
        Notification.objects.create(
            recipient=pro.user,
            notif_type='CREDITS',
            title='¡Recarga Exitosa!',
            message=f'Se han añadido {credits} créditos a tu cuenta por tu pago de ${amount}.',
            link='/dashboard/profesional/'
        )
        messages.success(request, f'Se han recargado {credits} créditos a {pro.name}.')
        return redirect('admin_recharges')
        
    recharges = Recharge.objects.all().select_related('professional').order_by('-created_at')
    professionals = Professional.objects.all().order_by('name')
    
    total_ingresos = sum(r.amount_paid for r in recharges)
    
    return render(request, 'core/admin_recharges.html', {
        'recharges': recharges,
        'professionals': professionals,
        'total_ingresos': total_ingresos
    })

@role_required('ADMIN')
def admin_add_professional(request):
    if request.method == 'POST':
        form = AdminProfessionalForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password'] or '12345'
            
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
            password = form.cleaned_data['password'] or '12345'
            
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
        if action == 'reopen_job':
            job_id = request.POST.get('job_id')
            try:
                job = JobRequest.objects.get(id=job_id, client=request.user, status='ACCEPTED')
                old_professional = job.professional
                job.status = 'PENDING'
                job.professional = None
                job.save()
                messages.success(request, 'La solicitud ha sido publicada nuevamente en la Bolsa de Trabajo.')
                # Notify the professional that the job was reopened
                if old_professional and old_professional.user:
                    Notification.objects.create(
                        recipient=old_professional.user,
                        notif_type='JOB_REOPENED',
                        title='Trabajo devuelto a la bolsa',
                        message=f'El cliente ha reabierto la solicitud "{job.title}". Ya no estás asignado a este trabajo.',
                        link='/dashboard/profesional/#job-market'
                    )
            except JobRequest.DoesNotExist:
                messages.error(request, 'No se pudo reabrir la solicitud o ya no se encuentra en estado aceptado.')
            return redirect('client_dashboard')

    requests = JobRequest.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'core/client_dashboard.html', {'requests': requests})

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

    jobs = JobRequest.objects.filter(professional=professional).order_by('-created_at')
    pending_jobs = JobRequest.objects.filter(status='PENDING').order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            professional.available = request.POST.get('available', professional.available)
            professional.specialty = request.POST.get('specialty', professional.specialty)
            professional.about = request.POST.get('about', professional.about)
            professional.location = request.POST.get('location', professional.location)
            
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            if lat:
                try:
                    professional.lat = float(lat)
                except ValueError:
                    pass
            if lng:
                try:
                    professional.lng = float(lng)
                except ValueError:
                    pass

            professional.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('/dashboard/profesional/#professional-profile')
        elif action == 'accept_job':
            if professional.credits <= 0:
                messages.error(request, 'No tienes créditos suficientes para aceptar trabajos. Por favor contacta al administrador para realizar una recarga.')
                return redirect('/dashboard/profesional/#job-market')
            
            job_id = request.POST.get('job_id')
            try:
                job = JobRequest.objects.get(id=job_id, status='PENDING')
                
                # Deduct 1 credit
                professional.credits -= 1
                professional.save()
                
                job.professional = professional
                job.status = 'ACCEPTED'
                job.save()
                messages.success(request, f'Has aceptado el trabajo: {job.title}. ¡Se ha descontado 1 crédito!')
                # Notify the client that their job was accepted
                Notification.objects.create(
                    recipient=job.client,
                    notif_type='JOB_ACCEPTED',
                    title='¡Tu solicitud fue aceptada!',
                    message=f'{professional.name} ha aceptado tu trabajo "{job.title}". Haz clic para ver su perfil y contactarlo.',
                    link=f'/profesional/{professional.id}/'
                )
                return redirect('/dashboard/profesional/#my-jobs')
            except JobRequest.DoesNotExist:
                messages.error(request, 'El trabajo ya no está disponible.')
                return redirect('/dashboard/profesional/#job-market')
        return redirect('professional_dashboard')

    print(f"DEBUG: API KEY in settings is -> '{settings.GOOGLE_MAPS_API_KEY}'")
    return render(request, 'core/professional_dashboard.html', {
        'professional': professional,
        'jobs': jobs,
        'pending_jobs': pending_jobs,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
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
    
    notifs = Notification.objects.filter(recipient=request.user, is_read=False)[:20]
    data = {
        'unread_count': notifs.count(),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notif_type,
                'link': n.link or '/',
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
