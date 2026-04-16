from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reportes_diarios.servicios_resumenes_correo import (
    construir_paquete_correo_cierre_mensual_ejecutivo,
    construir_paquete_correo_resumen_diario_ejecutivo,
    enviar_paquete_correo,
    normalizar_destinatarios,
    obtener_destinatarios_globales_configurados,
    obtener_periodo_mes_anterior,
    obtener_sucursales_objetivo,
)


# 1) Para que sirve: parsear fecha ISO de opcion CLI para resumen diario.
# 2) Como funciona: usa date.fromisoformat y valida formato esperado.
# 3) Que hace: evita ejecuciones con fecha invalida en comandos manuales.
# 4) Como editarla: agrega formatos alternos solo si se estandarizan en el proyecto.
def _parsear_fecha_iso(valor):
    if valor in (None, ''):
        return None
    try:
        return date.fromisoformat(str(valor))
    except ValueError as error:
        raise CommandError("La opcion --fecha-contable debe usar formato YYYY-MM-DD.") from error


# 1) Para que sirve: persistir localmente un paquete de correo para revision previa.
# 2) Como funciona: crea carpeta destino y guarda html/txt/adjuntos.
# 3) Que hace: habilita validar plantillas y archivos sin enviar correo real.
# 4) Como editarla: agrega metadata JSON si se requiere trazabilidad adicional.
def _guardar_paquete_en_archivos(paquete, carpeta_base):
    tipo = str(paquete.get('tipo') or 'correo')
    sucursal = str(paquete.get('sucursal_nombre') or 'sucursal').strip()
    periodo = str(paquete.get('periodo') or timezone.localdate().isoformat())

    nombre_carpeta = f"{tipo}_{sucursal}_{periodo}".replace(' ', '_').replace('/', '-')
    carpeta_destino = Path(carpeta_base) / nombre_carpeta
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    (carpeta_destino / 'correo.html').write_text(paquete.get('html') or '', encoding='utf-8')
    (carpeta_destino / 'correo.txt').write_text(paquete.get('texto') or '', encoding='utf-8')

    for adjunto in paquete.get('adjuntos') or []:
        nombre_archivo = str(adjunto.get('nombre') or 'adjunto.bin')
        contenido = adjunto.get('contenido') or b''
        (carpeta_destino / nombre_archivo).write_bytes(contenido)

    return carpeta_destino


class Command(BaseCommand):
    help = (
        'Genera plantillas y adjuntos del resumen diario ejecutivo por casino o del cierre mensual. '
        'Puede solo guardar archivos o enviar correos SMTP sin usar scheduler.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            choices=['diario', 'mensual'],
            required=True,
            help='Tipo de resumen a preparar: diario o mensual.',
        )
        parser.add_argument(
            '--sucursal-id',
            action='append',
            dest='sucursal_ids',
            type=int,
            help='ID de sucursal objetivo. Puede repetirse varias veces. Si se omite, usa todas las sucursales activas.',
        )
        parser.add_argument(
            '--destinatario',
            action='append',
            dest='destinatarios',
            help='Correo destinatario global. Puede repetirse varias veces.',
        )
        parser.add_argument(
            '--sin-correo-sucursal',
            action='store_true',
            help='No incluir el correo registrado en la sucursal como destinatario automatico.',
        )
        parser.add_argument(
            '--fecha-contable',
            dest='fecha_contable',
            help='Fecha contable para resumen diario en formato YYYY-MM-DD. Si se omite usa T-1.',
        )
        parser.add_argument(
            '--anio',
            type=int,
            help='Anio para cierre mensual. Si se omite usa mes anterior.',
        )
        parser.add_argument(
            '--mes',
            type=int,
            help='Mes (1-12) para cierre mensual. Si se omite usa mes anterior.',
        )
        parser.add_argument(
            '--solo-generar',
            action='store_true',
            help='Solo genera archivos en disco (html, txt, pdf, xlsx) sin enviar correos.',
        )
        parser.add_argument(
            '--carpeta-salida',
            default=str(Path(settings.BASE_DIR) / 'media' / 'correos_preparados'),
            help='Carpeta destino para --solo-generar.',
        )

    # 1) Para que sirve: ejecutar flujo manual de generacion/envio de resumenes ejecutivos.
    # 2) Como funciona: recorre sucursales activas, construye paquete y decide guardar o enviar.
    # 3) Que hace: deja lista la operacion diaria/mensual sin depender de tareas programadas.
    # 4) Como editarla: conecta aqui los disparadores automaticos cuando se habiliten.
    def handle(self, *args, **options):
        tipo = options.get('tipo')
        sucursal_ids = options.get('sucursal_ids') or []
        destinatarios_configurados = obtener_destinatarios_globales_configurados()
        destinatarios_globales = normalizar_destinatarios(options.get('destinatarios') or [])
        destinatarios_base = normalizar_destinatarios(destinatarios_configurados + destinatarios_globales)
        sin_correo_sucursal = bool(options.get('sin_correo_sucursal'))
        solo_generar = bool(options.get('solo_generar'))
        carpeta_salida = Path(options.get('carpeta_salida') or Path(settings.BASE_DIR) / 'media' / 'correos_preparados')

        fecha_contable = _parsear_fecha_iso(options.get('fecha_contable'))
        anio = options.get('anio')
        mes = options.get('mes')

        if tipo == 'mensual':
            if (anio is None) ^ (mes is None):
                raise CommandError('Para tipo mensual debes enviar ambos --anio y --mes, o ninguno.')
            if anio is None and mes is None:
                anio, mes = obtener_periodo_mes_anterior()
            if int(mes) < 1 or int(mes) > 12:
                raise CommandError('La opcion --mes debe estar entre 1 y 12.')

        sucursales = obtener_sucursales_objetivo(sucursal_ids)
        if not sucursales:
            raise CommandError('No se encontraron sucursales activas para procesar.')

        conexion = None
        if not solo_generar:
            conexion = get_connection(fail_silently=False)

        total_procesadas = 0
        total_enviadas = 0
        total_omitidas = 0

        for sucursal in sucursales:
            if tipo == 'diario':
                paquete = construir_paquete_correo_resumen_diario_ejecutivo(
                    sucursal=sucursal,
                    fecha_contable=fecha_contable,
                )
            else:
                paquete = construir_paquete_correo_cierre_mensual_ejecutivo(
                    sucursal=sucursal,
                    anio=anio,
                    mes=mes,
                )

            total_procesadas += 1

            if solo_generar:
                carpeta_destino = _guardar_paquete_en_archivos(paquete, carpeta_salida)
                self.stdout.write(self.style.SUCCESS(f"Generado: {sucursal.nombre} -> {carpeta_destino}"))
                continue

            destinatarios = list(destinatarios_base)
            if not sin_correo_sucursal and getattr(sucursal, 'correo', None):
                destinatarios.append(sucursal.correo)
            destinatarios = normalizar_destinatarios(destinatarios)

            if not destinatarios:
                total_omitidas += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Omitido {sucursal.nombre}: sin destinatarios validos. Usa --destinatario o configura correo de sucursal."
                    )
                )
                continue

            resultado = enviar_paquete_correo(
                paquete_correo=paquete,
                destinatarios=destinatarios,
                conexion=conexion,
            )
            enviados = int(resultado.get('enviados') or 0)
            total_enviadas += enviados

            if enviados > 0:
                self.stdout.write(self.style.SUCCESS(f"Enviado ({tipo}) {sucursal.nombre} -> {', '.join(destinatarios)}"))
            else:
                self.stdout.write(self.style.WARNING(f"Sin confirmacion de envio para {sucursal.nombre}."))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Resumen de ejecucion'))
        self.stdout.write(f"- Tipo: {tipo}")
        self.stdout.write(f"- Sucursales procesadas: {total_procesadas}")
        if solo_generar:
            self.stdout.write(f"- Modo: solo generacion en {carpeta_salida}")
        else:
            self.stdout.write(f"- Correos confirmados por SMTP: {total_enviadas}")
            self.stdout.write(f"- Sucursales omitidas por destinatarios: {total_omitidas}")
