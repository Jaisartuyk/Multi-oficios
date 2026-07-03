from django.db import models
from django.contrib.auth.models import User
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

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

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
        ('ACCEPTED', 'Aceptado / En Progreso'),
        ('COMPLETED', 'Completado'),
        ('CANCELLED', 'Cancelado'),
    )
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests_made', verbose_name="Cliente")
    professional = models.ForeignKey(Professional, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs', verbose_name="Profesional")
    title = models.CharField(max_length=200, verbose_name="Título del Trabajo")
    description = models.TextField(verbose_name="Descripción o Problema")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    estimated_price = models.CharField(max_length=100, blank=True, null=True, verbose_name="Precio Estimado")
    estimated_time = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tiempo Estimado")

    class Meta:
        verbose_name = "Solicitud de Trabajo"
        verbose_name_plural = "Solicitudes de Trabajo"

    def __str__(self):
        return f"{self.title} - {self.client.username} ({self.get_status_display()})"


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
