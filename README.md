# ObraYa - Multi-oficios 🏗️

**Confianza para construir.** Plataforma web PWA que conecta clientes con maestros de oficios (albañiles, pintores, gasfiteros, electricistas) en Ecuador.

## 🚀 Características

- **Cotizador Inteligente con IA** — Los clientes describen su problema y reciben una estimación de precio y tiempo automatizada.
- **Bolsa de Trabajo** — Los maestros ven solicitudes activas de clientes y las aceptan en un clic.
- **Sistema de Créditos** — Los maestros gastan 1 crédito por cada trabajo aceptado. Modelo de monetización pay-per-lead.
- **Notificaciones In-App** — Campana de notificaciones en tiempo real (trabajo aceptado, trabajo reabierto, créditos).
- **PWA Instalable** — Service Worker con caché offline, manifest.json y soporte Apple/Android para instalación como app nativa.
- **3 Dashboards** — Panel de Administrador, Panel de Profesional/Maestro y Panel de Cliente.
- **Mapa Interactivo** — Integración con Google Maps para localización de profesionales cercanos.
- **Modo Oscuro** — Alternancia de tema claro/oscuro con persistencia en localStorage.

## 🛠️ Stack Tecnológico

| Tecnología | Uso |
|---|---|
| **Django 5.0** | Backend, ORM, autenticación |
| **SQLite** | Base de datos (desarrollo) |
| **HTML/CSS/JS** | Frontend responsivo |
| **Google Maps API** | Geolocalización de profesionales |
| **Gemini AI** | Motor del cotizador inteligente |
| **PWA** | Service Worker + manifest para instalación nativa |

## 📦 Instalación Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/Jaisartuyk/Multi-oficios.git
cd Multi-oficios

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo .env
# Copiar .env.example y configurar las variables

# 5. Migraciones
python manage.py makemigrations
python manage.py migrate

# 6. Crear superusuario (admin)
python manage.py createsuperuser

# 7. Ejecutar servidor
python manage.py runserver
```

## 📁 Estructura del Proyecto

```
Multi-oficios/
├── core/                  # App principal de Django
│   ├── models.py          # UserProfile, Professional, JobRequest, Notification
│   ├── views.py           # Vistas y API de notificaciones
│   ├── access.py          # Decoradores de control de acceso por rol
│   └── forms.py           # Formularios de registro y admin
├── templates/core/        # Templates HTML
├── static/
│   ├── css/styles.css     # Diseño responsivo completo
│   ├── js/app.js          # Lógica frontend (tabs, mapa, tema)
│   ├── manifest.json      # PWA manifest
│   └── sw.js              # Service Worker
└── obraya/settings.py     # Configuración Django
```

## 👥 Roles de Usuario

- **Admin** — Gestiona usuarios, profesionales, créditos y métricas.
- **Profesional/Maestro** — Ve la bolsa de trabajo, acepta solicitudes, gestiona su perfil.
- **Cliente** — Solicita cotizaciones IA, ve el estado de sus trabajos, contacta maestros.

## 📄 Licencia

Este proyecto es privado. © 2026 ObraYa.
