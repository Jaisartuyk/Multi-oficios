import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'obraya.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client

client = Client()
try:
    print("Testing GET /login/...")
    response = client.get('/login/')
    print("Status code:", response.status_code)
    if response.status_code == 500:
        if hasattr(response, 'context') and response.context:
            print("Context exists")
        # If there's an exception, it might be in response.content
        print(response.content.decode('utf-8', errors='ignore')[:2000])
except Exception as e:
    import traceback
    traceback.print_exc()
