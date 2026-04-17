import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

ASUNTO_CORREO_BIENVENIDA = 'BinsurMX | Bienvenido a la plataforma'
ASUNTO_CORREO_REINICIO = 'BinsurMX | Reinicio de acceso'
CLAVE_CONFIG_DESTINATARIO_BACKUP_CREDENCIALES = 'DESTINATARIO_BACKUP'


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


# 1) Para que sirve: leer correos de respaldo para copia de altas de usuarios.
# 2) Como funciona: consulta ConfiguracionGlobal DESTINATARIO_BACKUP y normaliza lista de correos.
# 3) Que hace: agrega destinatarios adicionales para auditoria de nuevas altas.
# 4) Como editarla: ajusta la clave si negocio cambia nombre de variable global.
def obtener_destinatarios_respaldo_credenciales(
    clave_configuracion=CLAVE_CONFIG_DESTINATARIO_BACKUP_CREDENCIALES,
):
    try:
        from configuraciones_globales.models import ConfiguracionGlobal

        configuracion = ConfiguracionGlobal.objects.filter(clave=clave_configuracion).first()
        if not configuracion:
            return []

        valor_configurado = configuracion.valor_tipado
        if valor_configurado in (None, ''):
            return []

        if isinstance(valor_configurado, (list, tuple, set)):
            candidatos = [str(item or '').strip() for item in valor_configurado]
            return normalizar_destinatarios(candidatos)

        texto = str(valor_configurado)
        separador_unificado = texto.replace('\n', ',').replace(';', ',')
        candidatos = [segmento.strip() for segmento in separador_unificado.split(',')]
        return normalizar_destinatarios(candidatos)
    except Exception as exc:
        logger.warning('No fue posible resolver DESTINATARIO_BACKUP para credenciales: %s', exc)
        return []


# 1) Para que sirve: enviar correo de bienvenida o reinicio con credenciales visibles.
# 2) Como funciona: renderiza plantilla txt/html y envia con EmailMultiAlternatives.
# 3) Que hace: notifica al usuario su usuario, contrasena y ligas de acceso.
# 4) Como editarla: agrega campos de contexto para nuevas politicas de onboarding.
def enviar_correo_credenciales_usuario(
    usuario,
    contrasena_visible,
    es_reinicio=False,
    incluir_destinatarios_respaldo=False,
):
    destinatarios_principales = normalizar_destinatarios([getattr(usuario, 'correo', '')])
    if not destinatarios_principales:
        return {
            'enviado': False,
            'error': 'No hay correo valido para enviar credenciales al usuario.'
        }

    destinatarios_respaldo = []
    if incluir_destinatarios_respaldo:
        destinatarios_respaldo = obtener_destinatarios_respaldo_credenciales()

    destinatarios = normalizar_destinatarios(destinatarios_principales + destinatarios_respaldo)

    enlace_dashboard = getattr(settings, 'URL_PUBLICA_DASHBOARD_BINSUR', 'https://cytechn.ddns.net/apex')
    enlace_login = getattr(settings, 'URL_PUBLICA_LOGIN_BINSUR', 'https://cytechn.ddns.net/apex')

    nombre_completo = str(getattr(usuario, 'nombre', '') or '').strip() or str(getattr(usuario, 'username', '') or '').strip()
    casino_asignado = str(getattr(getattr(usuario, 'sucursal', None), 'nombre', '') or '').strip() or 'No asignado'

    contexto = {
        'nombre_usuario': nombre_completo,
        'nombre_completo': nombre_completo,
        'username': getattr(usuario, 'username', ''),
        'contrasena_visible': str(contrasena_visible or ''),
        'casino_asignado': casino_asignado,
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
            'error': '',
            'destinatarios': destinatarios,
            'destinatarios_respaldo': destinatarios_respaldo,
        }
    except Exception as exc:
        logger.exception('Error enviando correo de credenciales para usuario %s', getattr(usuario, 'id', 'sin_id'))
        return {
            'enviado': False,
            'error': f'Error enviando correo: {exc}'
        }
