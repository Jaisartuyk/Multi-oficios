import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AiUsage


class AiLimitError(Exception):
    pass


def fallback_estimate(brief):
    normalized = brief.lower()
    estimated_price = '$45 - $150'
    estimated_time = '2 a 6 horas'
    materials = ['Material principal según diagnóstico', 'Fijaciones', 'Equipo de seguridad']
    if 'pint' in normalized:
        estimated_price = '$180 - $500'
        estimated_time = '1 a 3 días'
        materials = ['Pintura', 'Sellador', 'Cinta de enmascarar', 'Protección de superficies']
    elif any(word in normalized for word in ('electric', 'luz', 'corto')):
        estimated_price = '$35 - $110'
        estimated_time = '2 a 4 horas'
        materials = ['Cable certificado', 'Conectores', 'Protección eléctrica']
    elif any(word in normalized for word in ('fuga', 'tubo', 'agua')):
        estimated_price = '$25 - $70'
        estimated_time = '1 a 3 horas'
        materials = ['Accesorios de tubería', 'Sellador', 'Repuestos según diagnóstico']
    return {
        'technical': 'Evaluación referencial basada en la descripción. Requiere inspección profesional.',
        'materials': materials,
        'estimated_time': estimated_time,
        'estimated_price': estimated_price,
        'safety_notes': ['No manipules instalaciones riesgosas sin un profesional calificado.'],
        'source': 'rules',
    }


@transaction.atomic
def consume_ai_request(user):
    today = timezone.localdate()
    usage, _ = AiUsage.objects.select_for_update().get_or_create(
        user=user,
        date=today,
        defaults={'requests': 0},
    )
    if usage.requests >= settings.GEMINI_DAILY_LIMIT:
        raise AiLimitError(
            f'Alcanzaste el límite diario de {settings.GEMINI_DAILY_LIMIT} análisis.'
        )
    usage.requests += 1
    usage.save(update_fields=['requests'])


def generate_estimate(user, brief):
    brief = brief.strip()[:2000]
    if not settings.GEMINI_API_KEY:
        return fallback_estimate(brief)

    consume_ai_request(user)
    try:
        from google import genai

        schema = {
            'type': 'object',
            'properties': {
                'technical': {'type': 'string'},
                'materials': {'type': 'array', 'items': {'type': 'string'}},
                'estimated_time': {'type': 'string'},
                'estimated_price': {'type': 'string'},
                'safety_notes': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': [
                'technical',
                'materials',
                'estimated_time',
                'estimated_price',
                'safety_notes',
            ],
        }
        prompt = (
            'Actúa como estimador de mantenimiento y construcción para Guayaquil, Ecuador. '
            'Genera una referencia prudente en USD, sin afirmar que es precio final. '
            'Identifica riesgos y recomienda inspección presencial. Solicitud del cliente: '
            f'{brief}'
        )
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_json_schema': schema,
                'temperature': 0.2,
                'max_output_tokens': 700,
            },
        )
        data = response.parsed if isinstance(response.parsed, dict) else json.loads(response.text)
        data['source'] = 'gemini'
        return data
    except AiLimitError:
        raise
    except Exception:
        result = fallback_estimate(brief)
        result['source'] = 'fallback'
        return result
