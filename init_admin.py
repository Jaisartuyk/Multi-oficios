import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'obraya.settings')
django.setup()

from django.contrib.auth.models import User

# Railway must provide these values. Never create a production administrator
# with credentials embedded in source code.
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not username or not password:
    print('Superuser creation skipped: configure DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD.')
elif not User.objects.filter(username=username).exists():
    print(f"Creando superusuario: {username}...")
    User.objects.create_superuser(username, email, password)
    print(f"¡Superusuario '{username}' creado exitosamente!")
else:
    print(f"El superusuario '{username}' ya existe. Saltando creación.")
