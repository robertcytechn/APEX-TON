import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

ASUNTO_CORREO_BIENVENIDA = 'BinsurMX | Bienvenido a la plataforma'
ASUNTO_CORREO_REINICIO = 'BinsurMX | Reinicio de acceso'


# 1) Para que sirve: limpiar destinatarios para evitar envios invalidos o duplicados.
# 2) Como funciona: valida formato basico con @ y deduplica por lowercase.
# 3) Que hace: retorna lista de correos lista para SMTP.
# 4) Como editarla: sustituye por validador mas estricto si negocio lo requiere.
def normalizar_destinatarios(destinatarios):
    vistos = set()
    resultado = []

    for destinatario in destinatarios or []:
        correo = str(destinatario or '').strip()
        if not correo or '@' not in correo:
            continue

        llave = correo.lower()
        if llave in vistos:
            continue

        vistos.add(llave)
        resultado.append(correo)

    return resultado


# 1) Para que sirve: enviar correo de bienvenida o reinicio con credenciales visibles.
# 2) Como funciona: renderiza plantilla txt/html y envia con EmailMultiAlternatives.
# 3) Que hace: notifica al usuario su usuario, contrasena y ligas de acceso.
# 4) Como editarla: agrega campos de contexto para nuevas politicas de onboarding.
def enviar_correo_credenciales_usuario(usuario, contrasena_visible, es_reinicio=False):
    destinatarios = normalizar_destinatarios([getattr(usuario, 'correo', '')])
    if not destinatarios:
        return {
            'enviado': False,
            'error': 'No hay correo valido para enviar credenciales al usuario.'
        }

    enlace_dashboard = getattr(settings, 'URL_PUBLICA_DASHBOARD_BINSUR', 'https://cytechn.ddns.net/apex/')
    enlace_login = getattr(settings, 'URL_PUBLICA_LOGIN_BINSUR', 'https://cytechn.ddns.net/apex/auth/login')

    contexto = {
        'nombre_usuario': getattr(usuario, 'nombre', '') or getattr(usuario, 'username', ''),
        'username': getattr(usuario, 'username', ''),
        'contrasena_visible': str(contrasena_visible or ''),
        'enlace_dashboard': enlace_dashboard,
        'enlace_login': enlace_login,
        'es_reinicio': bool(es_reinicio),
    }

    asunto = ASUNTO_CORREO_REINICIO if es_reinicio else ASUNTO_CORREO_BIENVENIDA

    try:
        cuerpo_texto = render_to_string('usuarios/correo_credenciales_usuario.txt', contexto)
        cuerpo_html = render_to_string('usuarios/correo_credenciales_usuario.html', contexto)

        mensaje = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        mensaje.attach_alternative(cuerpo_html, 'text/html')

        enviados = int(mensaje.send(fail_silently=False) or 0)
        if enviados <= 0:
            return {
                'enviado': False,
                'error': 'No fue posible confirmar el envio del correo de credenciales.'
            }

        return {
            'enviado': True,
            'error': ''
        }
    except Exception as exc:
        logger.exception('Error enviando correo de credenciales para usuario %s', getattr(usuario, 'id', 'sin_id'))
        return {
            'enviado': False,
            'error': f'Error enviando correo: {exc}'
        }
