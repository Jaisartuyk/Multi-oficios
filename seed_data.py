import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'obraya.settings')
django.setup()

from core.models import Category, Professional, Service

CATEGORIES = [
    {'name': 'Albanileria', 'icon': 'brick-wall', 'demand': 'Alta'},
    {'name': 'Pintura', 'icon': 'paint-roller', 'demand': 'Express'},
    {'name': 'Electricidad', 'icon': 'zap', 'demand': '24/7'},
    {'name': 'Gasfiteria', 'icon': 'droplets', 'demand': 'Urgente'},
    {'name': 'Soldadura', 'icon': 'flame', 'demand': 'Taller'},
    {'name': 'Carpinteria', 'icon': 'hammer', 'demand': 'Medida'},
    {'name': 'Jardineria', 'icon': 'leaf', 'demand': 'Semanal'},
    {'name': 'Limpieza', 'icon': 'sparkles', 'demand': 'Hogar'},
]

PROFESSIONALS = [
    {
        'id': 1,
        'name': 'Carlos Mendez',
        'specialty': 'Maestro albanil y acabados',
        'level': 'Maestro Elite',
        'rating': 4.9,
        'jobs': 186,
        'distance': '1.8 km',
        'eta': '12 min',
        'response': '8 min',
        'punctuality': 98,
        'price': '$$',
        'available': 'Disponible hoy',
        'badge': 'Identidad verificada',
        'initials': 'CM',
        'experience': '12 anos',
        'location': 'Centro, Guayaquil',
        'lat': -2.1900,
        'lng': -79.8890,
        'about': 'Especialista en remodelaciones, mamposteria, enlucidos y reparaciones estructurales ligeras.',
        'portfolio': ['Bano renovado', 'Muro terminado', 'Piso nivelado'],
    },
    {
        'id': 2,
        'name': 'Valeria Torres',
        'specialty': 'Electricista residencial',
        'level': 'Experto',
        'rating': 4.8,
        'jobs': 141,
        'distance': '2.4 km',
        'eta': '18 min',
        'response': '11 min',
        'punctuality': 96,
        'price': '$$$',
        'available': 'Agenda abierta',
        'badge': 'Garantia ObraYa',
        'initials': 'VT',
        'experience': '9 anos',
        'location': 'Urdesa, Guayaquil',
        'lat': -2.1715,
        'lng': -79.9069,
        'about': 'Instalaciones, tableros, puntos electricos, diagnostico de fallas y seguridad preventiva.',
        'portfolio': ['Tablero seguro', 'Iluminacion LED', 'Cableado nuevo'],
    },
    {
        'id': 3,
        'name': 'Jorge Salazar',
        'specialty': 'Gasfiteria y emergencias',
        'level': 'Profesional',
        'rating': 4.7,
        'jobs': 97,
        'distance': '3.1 km',
        'eta': '22 min',
        'response': '6 min',
        'punctuality': 94,
        'price': '$$',
        'available': 'Emergencia 24/7',
        'badge': 'Respuesta rapida',
        'initials': 'JS',
        'experience': '7 anos',
        'location': 'La Puntilla, Samborondon',
        'lat': -2.1393,
        'lng': -79.8681,
        'about': 'Reparacion de fugas, griferia, calentadores, tuberias y mantenimiento de banos/cocinas.',
        'portfolio': ['Fuga reparada', 'Cocina instalada', 'Ducha optimizada'],
    },
]

SERVICES = [
    {'name': 'Reparar fuga de agua', 'range': '$25 - $70', 'time': '1-3 h'},
    {'name': 'Pintar departamento', 'range': '$180 - $520', 'time': '1-3 dias'},
    {'name': 'Instalar tomacorrientes', 'range': '$35 - $110', 'time': '2-4 h'},
    {'name': 'Construir pared liviana', 'range': '$220 - $680', 'time': '2-5 dias'},
]

def seed():
    print("Eliminando datos antiguos...")
    Category.objects.all().delete()
    Professional.objects.all().delete()
    Service.objects.all().delete()

    print("Creando categorias...")
    for c in CATEGORIES:
        Category.objects.create(**c)
    
    print("Creando profesionales...")
    for p in PROFESSIONALS:
        p_data = dict(p)
        if 'id' in p_data:
            del p_data['id']
        Professional.objects.create(**p_data)

    print("Creando servicios...")
    for s in SERVICES:
        Service.objects.create(**s)

    print("Base de datos poblada exitosamente con datos de prueba.")

if __name__ == '__main__':
    seed()
