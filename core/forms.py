from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, Professional

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=(
            ('CLIENT', 'Quiero contratar servicios (Cliente)'),
            ('PROFESSIONAL', 'Quiero ofrecer mis servicios (Trabajador)'),
        ),
        widget=forms.RadioSelect,
        label="¿Cuál es tu objetivo en ObraYa?",
        required=True
    )
    phone = forms.CharField(
        max_length=20, 
        label="Número de Teléfono / WhatsApp", 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: +593 999999999'})
    )

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=commit)
        role = self.cleaned_data.get('role')
        phone = self.cleaned_data.get('phone')
        
        # Guardar perfil
        profile = user.profile
        profile.role = role
        profile.phone = phone
        profile.save()
        
        # Si es profesional, crear el perfil de profesional vacío por defecto
        if role == 'PROFESSIONAL':
            Professional.objects.create(
                user=user,
                name=f"{user.first_name or user.username}",
                specialty="General",
                initials=f"{user.username[:2].upper()}",
                location="Guayaquil",
                about="Profesional nuevo listo para trabajar."
            )
        return user

class AdminProfessionalForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nombre de Usuario")
    email = forms.EmailField(label="Correo Electrónico", required=False)
    first_name = forms.CharField(max_length=150, label="Nombre", required=False)
    last_name = forms.CharField(max_length=150, label="Apellido", required=False)
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña", required=False, help_text="Dejar vacío si no desea cambiarla.")
    
    # Professional fields
    specialty = forms.CharField(max_length=200, label="Especialidad")
    experience = forms.CharField(max_length=50, label="Experiencia (Años)")
    level = forms.CharField(max_length=100, label="Nivel/Categoría", initial="Experto")
    available = forms.CharField(max_length=100, label="Disponibilidad", initial="Disponible hoy")
    location = forms.CharField(max_length=200, label="Ciudad/Ubicación", initial="Guayaquil")
    about = forms.CharField(widget=forms.Textarea, label="Acerca de / Descripción", required=False)
    phone = forms.CharField(max_length=20, label="WhatsApp / Teléfono", required=False)

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        self.pro_instance = kwargs.pop('pro_instance', None)
        super().__init__(*args, **kwargs)
        if self.user_instance and self.pro_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['email'].initial = self.user_instance.email
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['specialty'].initial = self.pro_instance.specialty
            self.fields['experience'].initial = self.pro_instance.experience
            self.fields['level'].initial = self.pro_instance.level
            self.fields['available'].initial = self.pro_instance.available
            self.fields['location'].initial = self.pro_instance.location
            self.fields['about'].initial = self.pro_instance.about
            if hasattr(self.user_instance, 'profile'):
                self.fields['phone'].initial = self.user_instance.profile.phone

class AdminClientForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nombre de Usuario")
    email = forms.EmailField(label="Correo Electrónico", required=False)
    first_name = forms.CharField(max_length=150, label="Nombre", required=False)
    last_name = forms.CharField(max_length=150, label="Apellido", required=False)
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña", required=False, help_text="Dejar vacío si no desea cambiarla.")
    
    # Client fields
    phone = forms.CharField(max_length=20, label="Número de Teléfono / WhatsApp", required=False)

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
        if self.user_instance:
            self.fields['username'].initial = self.user_instance.username
            self.fields['email'].initial = self.user_instance.email
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            if hasattr(self.user_instance, 'profile'):
                self.fields['phone'].initial = self.user_instance.profile.phone
