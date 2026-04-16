from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand
from django.utils import timezone

DESTINATARIOS_PREDETERMINADOS = [
    'robert.cy93@gmail.com',
    'marcelaf@gbentretenimiento.com',
]


# 1) Para qué sirve: construir versión texto del correo de prueba para clientes sin HTML.
# 2) Cómo funciona: retorna cuerpo plano con resumen de la prueba de formato.
# 3) Qué hace: asegura legibilidad y entregabilidad mínima del mensaje.
# 4) Cómo editarla: agrega más secciones si cambian los bloques del HTML principal.
def construir_contenido_texto(fecha_envio_local):
    return (
        'Correo de prueba de BinsurMX (antes APEX)\n\n'
        f'Fecha de envío: {fecha_envio_local:%d/%m/%Y %H:%M:%S}\n\n'
        'Este correo sirve para validar cómo se verán los envíos automáticos del sistema '\
        'en distintos clientes de correo.\n\n'
        'Incluye:\n'
        '- Encabezado corporativo\n'
        '- Métricas operativas de ejemplo\n'
        '- Barras de progreso simuladas\n'
        '- Segmentos tipográficos con estilos distintos\n\n'
        'Si recibiste este mensaje, la integración SMTP está funcionando correctamente.\n'
        'Equipo BinsurMX.'
    )


# 1) Para qué sirve: crear plantilla HTML de prueba visual para correos automáticos.
# 2) Cómo funciona: arma layout responsivo compatible con clientes email comunes.
# 3) Qué hace: muestra iconos, métricas, bloques y tipografías para validación estética.
# 4) Cómo editarla: cambia colores/indicadores conservando estilos inline para compatibilidad.
def construir_contenido_html(fecha_envio_local):
    metricas = [
        {'titulo': 'Movimientos del día', 'valor': '1,248', 'icono': '📈', 'color': '#0ea5e9'},
        {'titulo': 'Ingresos capturados', 'valor': '$ 1,824,320.50', 'icono': '💸', 'color': '#10b981'},
        {'titulo': 'Egresos capturados', 'valor': '$ 1,221,905.80', 'icono': '🏦', 'color': '#f59e0b'},
        {'titulo': 'Resultado neto', 'valor': '$ 602,414.70', 'icono': '✅', 'color': '#6366f1'},
    ]

    barras = [
        {'etiqueta': 'Captura operativa', 'porcentaje': 86, 'color': '#0ea5e9'},
        {'etiqueta': 'Conciliación diaria', 'porcentaje': 74, 'color': '#10b981'},
        {'etiqueta': 'Cierre contable', 'porcentaje': 91, 'color': '#6366f1'},
        {'etiqueta': 'Monitoreo de incidencias', 'porcentaje': 63, 'color': '#f97316'},
    ]

    columnas_metricas = ''.join(
        (
            '<td style="padding:8px;" width="50%">'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">'
            f'<tr><td style="padding:14px 14px 10px 14px;font-family:Segoe UI, Tahoma, sans-serif;background:{metrica["color"]}14;">'
            f'<div style="font-size:18px;line-height:1;margin-bottom:8px;">{metrica["icono"]}</div>'
            f'<div style="font-size:12px;color:#334155;letter-spacing:.02em;">{metrica["titulo"]}</div>'
            f'<div style="font-size:20px;font-weight:700;color:#0f172a;margin-top:6px;">{metrica["valor"]}</div>'
            '</td></tr></table>'
            '</td>'
        )
        for metrica in metricas
    )

    barras_html = ''.join(
        (
            '<tr>'
            f'<td style="font-family:Segoe UI, Tahoma, sans-serif;font-size:13px;color:#1e293b;padding:8px 0 6px 0;">{barra["etiqueta"]}</td>'
            '</tr>'
            '<tr>'
            '<td style="padding-bottom:12px;">'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#e2e8f0;border-radius:999px;">'
            '<tr>'
            f'<td width="{barra["porcentaje"]}%" style="height:12px;background:{barra["color"]};border-radius:999px;"></td>'
            f'<td width="{100 - barra["porcentaje"]}%" style="height:12px;"></td>'
            '</tr>'
            '</table>'
            f'<div style="font-family:Segoe UI, Tahoma, sans-serif;font-size:12px;color:#475569;margin-top:4px;">{barra["porcentaje"]}%</div>'
            '</td>'
            '</tr>'
        )
        for barra in barras
    )

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Prueba visual BinsurMX</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f8fafc;padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="width:680px;max-width:96%;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;">
          <tr>
            <td style="padding:0;background:linear-gradient(120deg,#0f172a,#0ea5e9,#10b981);">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="padding:24px 28px 28px 28px;">
                    <div style="font-family:Segoe UI, Tahoma, sans-serif;font-size:12px;color:#dbeafe;letter-spacing:.14em;text-transform:uppercase;">Correo de prueba automática</div>
                    <h1 style="margin:10px 0 0 0;font-family:Segoe UI, Tahoma, sans-serif;font-size:30px;line-height:1.2;color:#ffffff;">BinsurMX <span style="font-weight:400;">(antes APEX)</span></h1>
                    <p style="margin:12px 0 0 0;font-family:Segoe UI, Tahoma, sans-serif;font-size:14px;line-height:1.6;color:#e2e8f0;max-width:560px;">
                      Este mensaje valida el estilo de los correos automáticos del sistema: identidad visual,
                      iconografía, métricas operativas y legibilidad en distintos clientes de correo.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:22px 20px 8px 20px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  {columnas_metricas}
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:8px 28px 8px 28px;">
              <h2 style="margin:0 0 10px 0;font-family:Segoe UI, Tahoma, sans-serif;font-size:18px;color:#0f172a;">Estado operativo simulado</h2>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                {barras_html}
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:6px 28px 8px 28px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e2e8f0;border-radius:12px;">
                <tr>
                  <td style="padding:14px 16px;font-family:Georgia, 'Times New Roman', serif;font-size:15px;color:#1f2937;background:#f9fafb;">
                    📝 <strong>Bloque serif:</strong> ideal para mensajes formales, comunicados institucionales y cierres ejecutivos.
                  </td>
                </tr>
                <tr>
                  <td style="padding:14px 16px;font-family:Consolas, 'Courier New', monospace;font-size:13px;color:#0f172a;background:#ecfeff;">
                    &gt; BLOQUE MONO: conciliacion_ok=true | cierre_mes=pendiente | alerta_riesgo=normal
                  </td>
                </tr>
                <tr>
                  <td style="padding:14px 16px;font-family:Segoe UI, Tahoma, sans-serif;font-size:14px;color:#0f172a;background:#f8fafc;">
                    🎯 <strong>Bloque sans-serif:</strong> recomendado para notificaciones operativas, recordatorios y alertas del día a día.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:10px 28px 28px 28px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
                <tr>
                  <td style="font-family:Segoe UI, Tahoma, sans-serif;font-size:13px;color:#475569;padding-bottom:8px;">
                    Fecha de envío: <strong>{fecha_envio_local:%d/%m/%Y %H:%M:%S}</strong>
                  </td>
                </tr>
                <tr>
                  <td style="font-family:Segoe UI, Tahoma, sans-serif;font-size:13px;color:#475569;line-height:1.6;">
                    Si recibiste este correo, la configuración SMTP de BinsurMX está activa y lista para notificaciones automáticas.
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:14px;">
                    <a href="https://cytechn.ddns.net/apex" style="display:inline-block;background:#0f172a;color:#ffffff;text-decoration:none;font-family:Segoe UI, Tahoma, sans-serif;font-size:13px;padding:10px 16px;border-radius:10px;">
                      Entrar a BinsurMX
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


class Command(BaseCommand):
    help = 'Envía un correo de prueba visual de BinsurMX para validar formato HTML y SMTP.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--destinatario',
            action='append',
            dest='destinatarios',
            help='Correo destinatario. Puede repetirse varias veces.',
        )
        parser.add_argument(
            '--asunto',
            default='[Prueba] Correo automático BinsurMX (antes APEX)',
            help='Asunto personalizado para el correo de prueba.',
        )

    # 1) Para qué sirve: ejecutar envío de prueba SMTP con plantilla HTML de validación.
    # 2) Cómo funciona: compone correo por destinatario y lo envía usando conexión configurada.
    # 3) Qué hace: permite verificar formato visual y entregabilidad en cuentas reales.
    # 4) Cómo editarla: ajusta asunto, remitente o destinatarios según entorno de pruebas.
    def handle(self, *args, **options):
        destinatarios = options.get('destinatarios') or DESTINATARIOS_PREDETERMINADOS
        asunto = options.get('asunto') or '[Prueba] Correo automático BinsurMX (antes APEX)'

        fecha_envio_local = timezone.localtime(timezone.now())
        contenido_texto = construir_contenido_texto(fecha_envio_local)
        contenido_html = construir_contenido_html(fecha_envio_local)

        conexion = get_connection(fail_silently=False)
        mensajes = []

        for correo_destino in destinatarios:
            mensaje = EmailMultiAlternatives(
                subject=asunto,
                body=contenido_texto,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[correo_destino],
                connection=conexion,
            )
            mensaje.attach_alternative(contenido_html, 'text/html')
            mensajes.append(mensaje)

        enviados = conexion.send_messages(mensajes) or 0
        total = len(mensajes)

        if enviados == total:
            self.stdout.write(self.style.SUCCESS(f'Correos enviados correctamente: {enviados}/{total}'))
            for correo_destino in destinatarios:
                self.stdout.write(self.style.SUCCESS(f' - {correo_destino}'))
            return

        self.stdout.write(self.style.WARNING(f'Envío parcial: {enviados}/{total}'))
        for correo_destino in destinatarios:
            self.stdout.write(self.style.WARNING(f' - {correo_destino}'))
