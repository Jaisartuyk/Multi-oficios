import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'obraya.settings')
django.setup()

from django.contrib.auth.models import User

# Puedes cambiar estos valores creando variables en Railway:
# DJANGO_SUPERUSER_USERNAME y DJANGO_SUPERUSER_PASSWORD
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@obraya.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    print(f"Creando superusuario: {username}...")
    User.objects.create_superuser(username, email, password)
    print(f"¡Superusuario '{username}' creado exitosamente!")
else:
    print(f"El superusuario '{username}' ya existe. Saltando creación.")
