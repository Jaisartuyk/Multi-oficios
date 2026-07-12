from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('PROFESSIONAL', 'Profesional/Trabajador'),
        ('CLIENT', 'Cliente'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CLIENT')
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, default='')
    lat = models.FloatField(blank=True, null=True)
    lng = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def whatsapp_number(self):
        if not self.phone:
            return ""
        # Filtrar solo dígitos
        num = "".join(c for c in self.phone if c.isdigit())
        if not num:
            return ""
        
        # Si empieza con 09... (móvil de Ecuador de 10 dígitos)
        if num.startswith("0") and len(num) == 10:
            return "593" + num[1:]
        # Si empieza con 9... (móvil de Ecuador sin el 0 inicial)
        elif num.startswith("9") and len(num) == 9:
            return "593" + num
        # Si ya tiene el código de Ecuador 593
        elif num.startswith("593"):
            return num
        return num


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'ADMIN' if instance.is_superuser else 'CLIENT'
        UserProfile.objects.create(user=instance, role=role)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        role = 'ADMIN' if instance.is_superuser else 'CLIENT'
        UserProfile.objects.create(user=instance, role=role)

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    icon = models.CharField(max_length=50, verbose_name="Icono de Lucide")
    demand = models.CharField(max_length=50, verbose_name="Etiqueta de Demanda")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name

class Professional(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='professional_profile', verbose_name="Usuario de Django")
    name = models.CharField(max_length=150, verbose_name="Nombre")
    specialty = models.CharField(max_length=200, verbose_name="Especialidad")
    level = models.CharField(max_length=100, verbose_name="Nivel")
    rating = models.DecimalField(max_digits=3, decimal_places=1, verbose_name="Calificación", default=5.0)
    jobs = models.IntegerField(verbose_name="Trabajos realizados", default=0)
    credits = models.IntegerField(verbose_name="Créditos", default=3)
    distance = models.CharField(max_length=50, verbose_name="Distancia", default="0.0 km")
    eta = models.CharField(max_length=50, verbose_name="Tiempo de llegada (ETA)", default="15 min")
    response = models.CharField(max_length=50, verbose_name="Tiempo de respuesta", default="10 min")
    punctuality = models.IntegerField(verbose_name="Puntualidad (%)", default=100)
    price = models.CharField(max_length=10, verbose_name="Nivel de precio", default="$$")
    available = models.CharField(max_length=100, verbose_name="Disponibilidad", default="Disponible hoy")
    badge = models.CharField(max_length=100, verbose_name="Insignia", default="Identidad verificada")
    initials = models.CharField(max_length=5, verbose_name="Iniciales")
    experience = models.CharField(max_length=50, verbose_name="Experiencia", default="1 año")
    location = models.CharField(max_length=200, verbose_name="Ubicación")
    lat = models.FloatField(verbose_name="Latitud", default=-2.1894)
    lng = models.FloatField(verbose_name="Longitud", default=-79.8891)
    about = models.TextField(verbose_name="Acerca de")
    portfolio = models.JSONField(verbose_name="Portafolio (Lista de strings)", default=list)
    coverage_radius_km = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Radio de cobertura (km)",
    )

    class Meta:
        verbose_name = "Profesional"
        verbose_name_plural = "Profesionales"

    def __str__(self):
        return self.name

class Service(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre del Servicio")
    range = models.CharField(max_length=100, verbose_name="Rango de precio")
    time = models.CharField(max_length=100, verbose_name="Tiempo estimado")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return self.name

class JobRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente de Cotización'),
        ('QUOTED', 'Cotizado'),
        ('ACCEPTED', 'Profesional seleccionado'),
        ('IN_PROGRESS', 'En ejecucion'),
        ('AWAITING_CONFIRMATION', 'Esperando confirmacion del cliente'),
        ('COMPLETED', 'Completado'),
        ('CANCELLED', 'Cancelado'),
    )
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests_made', verbose_name="Cliente")
    professional = models.ForeignKey(Professional, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs', verbose_name="Profesional")
    title = models.CharField(max_length=200, verbose_name="Título del Trabajo")
    description = models.TextField(verbose_name="Descripción o Problema")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ultima actualizacion")
    address = models.CharField(max_length=250, blank=True, default='', verbose_name="Sector del trabajo")
    lat = models.FloatField(blank=True, null=True, verbose_name="Latitud del trabajo")
    lng = models.FloatField(blank=True, null=True, verbose_name="Longitud del trabajo")
    selected_quote = models.ForeignKey(
        'Quote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_for_jobs',
        verbose_name="Cotizacion seleccionada",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    estimated_price = models.CharField(max_length=100, blank=True, null=True, verbose_name="Precio Estimado")
    estimated_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tiempo Estimado")

    class Meta:
        verbose_name = "Solicitud de Trabajo"
        verbose_name_plural = "Solicitudes de Trabajo"

    def __str__(self):
        return f"{self.title} - {self.client.username} ({self.get_status_display()})"


class Quote(models.Model):
    STATUS_CHOICES = (
        ('SUBMITTED', 'Enviada'),
        ('ACCEPTED', 'Aceptada'),
        ('REJECTED', 'No seleccionada'),
        ('WITHDRAWN', 'Retirada'),
    )
    job = models.ForeignKey(JobRequest, on_delete=models.CASCADE, related_name='quotes')
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='quotes')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    message = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'professional'],
                name='unique_quote_per_professional_job',
            ),
        ]
        ordering = ['amount', 'created_at']

    def __str__(self):
        return f"{self.professional.name}: ${self.amount} - {self.job.title}"


class Review(models.Model):
    job = models.OneToOneField(JobRequest, on_delete=models.CASCADE, related_name='review')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='verified_reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    punctuality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1500, blank=True)
    admin_observation = models.TextField(verbose_name="Observación para el administrador", blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}/5 - {self.professional.name}"


class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente de verificacion'),
        ('VERIFIED', 'Verificado'),
        ('RELEASED', 'Liberado al profesional'),
        ('REFUNDED', 'Reembolsado'),
    )
    GUARANTEE_CHOICES = (
        ('NOT_REQUESTED', 'No solicitada'),
        ('PENDING', 'Pendiente'),
        ('ACTIVE', 'Activa'),
        ('RESOLVED', 'Resuelta'),
    )
    METHOD_CHOICES = (
        ('TRANSFER', 'Transferencia'),
        ('DEUNA', 'DeUna'),
        ('CASH', 'Efectivo'),
    )
    job = models.OneToOneField(JobRequest, on_delete=models.CASCADE, related_name='payment')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    professional = models.ForeignKey(Professional, on_delete=models.PROTECT, related_name='payments_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    receipt_reference = models.CharField(max_length=200)
    receipt_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    guarantee_status = models.CharField(
        max_length=20,
        choices=GUARANTEE_CHOICES,
        default='NOT_REQUESTED',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.job.title} - ${self.amount} ({self.get_status_display()})"


class PortfolioItem(models.Model):
    professional = models.ForeignKey(
        Professional,
        on_delete=models.CASCADE,
        related_name='portfolio_items',
    )
    image_url = models.URLField(max_length=500)
    caption = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_video(self):
        if not self.image_url:
            return False
        url = self.image_url.lower()
        extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '/video/')
        return any(ext in url for ext in extensions)



class AiUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_usage')
    date = models.DateField()
    requests = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_ai_usage_per_day'),
        ]


class Notification(models.Model):
    NOTIF_TYPES = (
        ('JOB_ACCEPTED', 'Trabajo aceptado'),
        ('JOB_REOPENED', 'Trabajo reabierto'),
        ('NEW_JOB', 'Nueva solicitud'),
        ('CREDITS', 'Créditos recargados'),
        ('SYSTEM', 'Sistema'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Destinatario")
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='SYSTEM', verbose_name="Tipo")
    title = models.CharField(max_length=200, verbose_name="Título")
    message = models.TextField(verbose_name="Mensaje")
    is_read = models.BooleanField(default=False, verbose_name="Leída")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    link = models.CharField(max_length=300, blank=True, null=True, verbose_name="Enlace")

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_notif_type_display()}] {self.title} → {self.recipient.username}"

class Recharge(models.Model):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='recharges', verbose_name="Profesional")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Pagado ($)")
    credits_added = models.IntegerField(verbose_name="Créditos Añadidos")
    payment_method = models.CharField(max_length=50, choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('DEUNA', 'DeUna')], default='TRANSFERENCIA', verbose_name="Método de Pago")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recarga")

    class Meta:
        verbose_name = "Recarga de Créditos"
        verbose_name_plural = "Historial de Recargas"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.professional.name} - +{self.credits_added} créditos (${self.amount_paid})"


class ChatRoom(models.Model):
    job = models.OneToOneField(JobRequest, on_delete=models.CASCADE, related_name='chat_room')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat: {self.job.title} (Activo: {self.is_active})"


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    file_url = models.URLField(blank=True, null=True, max_length=500)
    file_type = models.CharField(max_length=50, blank=True, null=True) # 'image', 'audio', 'video', 'document'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content or '[Archivo]'}"

from allauth.account.signals import user_signed_up

@receiver(user_signed_up)
def update_role_after_signup(request, user, **kwargs):
    # Revisamos si el usuario tenía la intención de ser profesional
    intended_role = request.session.get('intended_role')
    
    if intended_role == 'PROFESSIONAL':
        # El post_save de arriba ya le creó un perfil como CLIENTE. Lo actualizamos:
        if hasattr(user, 'profile'):
            user.profile.role = 'PROFESSIONAL'
            user.profile.save()
            
        # Crear perfil de Profesional si no existe
        if not Professional.objects.filter(user=user).exists():
            Professional.objects.create(
                user=user,
                name=user.get_full_name() or user.username,
                specialty="General",
                initials=(user.get_full_name() or user.username)[:2].upper(),
                location="Guayaquil",
                about="Profesional nuevo registrado vía inicio de sesión social."
            )
            
        # Limpiamos la variable de sesión para que no afecte a futuros inicios de sesión
        request.session.pop('intended_role', None)
