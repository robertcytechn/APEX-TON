from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from categoria_operativa.models import CategoriaOperativa
from configuraciones_globales.models import ConfiguracionGlobal, RubroContable
from libro_estado_resultados.models import LibroEstadoResultados
from reportes_diarios.models import MovimientoDiario, ReporteDiario
from reportes_diarios.views import (
    _construir_datos_libro_operativo_detallado,
    _construir_detalle_capturas_por_categoria,
    _dia_contable_actual,
    _obtener_o_crear_reporte_del_dia,
)
from sucursales.models import Sucursal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NOMBRE_MARCA = 'BinsurMX'
URL_SISTEMA = 'https://cytechn.ddns.net/apex'

MIME_EXCEL = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
MIME_PDF = 'application/pdf'


# 1) Para que sirve: convertir valores diversos a Decimal para calculos contables seguros.
# 2) Como funciona: convierte a texto y captura errores de formato con fallback 0.
# 3) Que hace: evita romper sumatorias cuando llegan nulos o cadenas invalidas.
# 4) Como editarla: aplica quantize aqui si se requiere precision forzada en cada paso.
def _a_decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


# 1) Para que sirve: normalizar valores numericos para JSON y plantillas.
# 2) Como funciona: intenta float con fallback a 0.0 ante errores.
# 3) Que hace: simplifica serializacion de metricas para correos y adjuntos.
# 4) Como editarla: devuelve str si en futuro se desea precision textual exacta.
def _a_flotante(valor):
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


# 1) Para que sirve: dar formato monetario uniforme para texto visible en correo.
# 2) Como funciona: aplica separador de miles y dos decimales fijos.
# 3) Que hace: hace legibles los montos en resumen ejecutivo.
# 4) Como editarla: cambia simbolo o locale segun lineamientos del negocio.
def _formatear_moneda(valor):
    return f"${_a_flotante(valor):,.2f}"


# 1) Para que sirve: convertir fecha a etiqueta legible en espanol para asunto y cuerpo.
# 2) Como funciona: usa strftime con dia/mes/anio en dos digitos.
# 3) Que hace: estandariza periodos en plantillas y nombres de archivo.
# 4) Como editarla: reemplaza formato si direccion solicita otro orden de fecha.
def _formatear_fecha(fecha_objetivo):
    if not fecha_objetivo:
        return '-'
    return fecha_objetivo.strftime('%d/%m/%Y')


# 1) Para que sirve: devolver nombre del mes para textos ejecutivos.
# 2) Como funciona: mapea numero de mes a etiqueta en espanol.
# 3) Que hace: mejora legibilidad de asunto y encabezado mensual.
# 4) Como editarla: sustituye por i18n dinamico si se agrega multi-idioma.
def _nombre_mes(numero_mes):
    nombres = {
        1: 'enero',
        2: 'febrero',
        3: 'marzo',
        4: 'abril',
        5: 'mayo',
        6: 'junio',
        7: 'julio',
        8: 'agosto',
        9: 'septiembre',
        10: 'octubre',
        11: 'noviembre',
        12: 'diciembre',
    }
    return nombres.get(int(numero_mes or 0), 'mes_desconocido')


# 1) Para que sirve: generar marca de tiempo estable para nombres de archivos adjuntos.
# 2) Como funciona: toma hora local del servidor y devuelve formato YYYYMMDD_HHMMSS.
# 3) Que hace: evita colisiones y mejora trazabilidad por casino en correos ejecutivos.
# 4) Como editarla: ajusta el formato solo si negocio cambia estandar de nomenclatura.
def _generar_marca_tiempo_archivo():
    return timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')


# 1) Para que sirve: limpiar y deduplicar lista de destinatarios de correo.
# 2) Como funciona: recorta espacios, valida minimo y elimina repetidos conservando orden.
# 3) Que hace: evita envios duplicados o direcciones vacias.
# 4) Como editarla: incorpora validacion regex estricta si se necesita mayor control.
def normalizar_destinatarios(destinatarios):
    if not destinatarios:
        return []

    vistos = set()
    resultado = []

    for destinatario in destinatarios:
        correo = str(destinatario or '').strip()
        if not correo or '@' not in correo:
            continue
        llave = correo.lower()
        if llave in vistos:
            continue
        vistos.add(llave)
        resultado.append(correo)

    return resultado


# 1) Para que sirve: obtener destinatarios globales de correo desde configuración en base de datos.
# 2) Como funciona: lee la clave DESTINATARIOS_CORREOS y separa correos por coma/salto/;.
# 3) Que hace: centraliza la fuente de destinatarios para envíos diarios y mensuales.
# 4) Como editarla: cambia la clave por defecto o el parser si el formato almacenado evoluciona.
def obtener_destinatarios_globales_configurados(clave_configuracion='DESTINATARIOS_CORREOS'):
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


# 1) Para que sirve: calcular anio/mes del periodo anterior al de referencia.
# 2) Como funciona: toma el primer dia del mes y retrocede un dia.
# 3) Que hace: entrega el mes cerrado que debe enviarse el dia 1.
# 4) Como editarla: usa otra logica de corte si cambia el calendario contable.
def obtener_periodo_mes_anterior(fecha_referencia=None):
    fecha_base = fecha_referencia or timezone.localdate()
    primer_dia_mes = fecha_base.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes - timedelta(days=1)
    return ultimo_dia_mes_anterior.year, ultimo_dia_mes_anterior.month


# 1) Para que sirve: detectar rubros no contables por reglas semanticas del dominio.
# 2) Como funciona: normaliza identificadores y evalua patrones SIN_RUBRO/NO_CONTABLE.
# 3) Que hace: evita contaminar totales de estado de resultados.
# 4) Como editarla: amplia patrones si negocio agrega nuevas etiquetas especiales.
def _rubro_es_no_contable(rubro_id=None, rubro_tipo=None, rubro_padre_clave=None, rubro_padre_nombre=None):
    identificador = str(rubro_id or '').strip().replace('-', '_').replace(' ', '_').upper()
    tipo_rubro = str(rubro_tipo or '').strip().replace('-', '_').replace(' ', '_').upper()
    padre_clave = str(rubro_padre_clave or '').strip().replace('-', '_').replace(' ', '_').upper()
    padre_nombre = str(rubro_padre_nombre or '').strip().replace('-', '_').replace(' ', '_').upper()
    huella_padre = f"{padre_clave} {padre_nombre}"

    if not identificador:
        return True

    if identificador in {'SIN_RUBRO_CONTABLE', 'SINRUBROCONTABLE', 'SIN_RUBRO', 'SINRUBRO'}:
        return True

    if tipo_rubro in {'NO_CONTABLE', 'NOCONTABLE'}:
        return True

    if 'NO_CONTABLE' in huella_padre or 'NOCONTABLE' in huella_padre:
        return True

    if 'SIN_GRUPO' in huella_padre or 'SINGRUPO' in huella_padre:
        return True

    return False


# 1) Para que sirve: decidir si un rubro impacta los totales contables oficiales.
# 2) Como funciona: combina bandera del padre y clasificacion no contable.
# 3) Que hace: mantiene consistencia entre tiempo real y snapshots historicos.
# 4) Como editarla: centraliza cualquier ajuste de inclusion/exclusion contable.
def _rubro_debe_considerarse_en_estado_resultados(
    rubro_id=None,
    rubro_tipo=None,
    rubro_padre_clave=None,
    rubro_padre_nombre=None,
    considerar_padre=True,
):
    if not bool(considerar_padre):
        return False

    return not _rubro_es_no_contable(
        rubro_id=rubro_id,
        rubro_tipo=rubro_tipo,
        rubro_padre_clave=rubro_padre_clave,
        rubro_padre_nombre=rubro_padre_nombre,
    )


# 1) Para que sirve: preparar base de rubros con estructura homogenea para reportes mensuales.
# 2) Como funciona: consulta catalogo activo y precarga montos en cero por rubro.
# 3) Que hace: garantiza que el adjunto mensual siempre tenga estructura completa.
# 4) Como editarla: agrega columnas nuevas aqui para reflejarlas en excel/pdf.
def _construir_rubros_base_estado_resultados():
    rubros = (
        RubroContable.objects.filter(eliminado_en__isnull=True)
        .select_related('padre')
        .order_by('padre__nombre', 'nombre')
        .values('id', 'nombre', 'tipo', 'padre__clave', 'padre__nombre', 'padre__considerar_en_estado_resultados')
    )

    base = {}
    for rubro in rubros:
        base[rubro['id']] = {
            'rubro_id': rubro['id'],
            'rubro_nombre': rubro['nombre'],
            'rubro_tipo': rubro.get('tipo'),
            'rubro_padre': rubro.get('padre__nombre') or 'SIN GRUPO',
            'rubro_padre_clave': rubro.get('padre__clave'),
            'rubro_padre_considerar_en_estado_resultados': _rubro_debe_considerarse_en_estado_resultados(
                rubro_id=rubro['id'],
                rubro_tipo=rubro.get('tipo'),
                rubro_padre_clave=rubro.get('padre__clave'),
                rubro_padre_nombre=rubro.get('padre__nombre'),
                considerar_padre=rubro.get('padre__considerar_en_estado_resultados', True),
            ),
            'total_ingresos': 0.0,
            'total_egresos': 0.0,
            'resultado_neto': 0.0,
        }

    return base


# 1) Para que sirve: construir los datos del libro operativo para un rango de fechas.
# 2) Como funciona: delega al helper unificado de views.py que ya replica el endpoint completo.
# 3) Que hace: garantiza que correo, PDF y Excel reciban exactamente las mismas filas que la UI.
# 4) Como editarla: cualquier cambio del libro operativo vive en views._construir_datos_libro_operativo_detallado.
def construir_datos_libro_operativo(sucursal_id, fecha_inicio, fecha_fin, crear_si_falta=True):
    return _construir_datos_libro_operativo_detallado(
        sucursal_id=sucursal_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        filtro_forzado=bool(fecha_inicio == fecha_fin),
        crear_si_falta=crear_si_falta,
    )


# 1) Para que sirve: construir los datos detallados con bancos y por categoria del libro operativo.
# 2) Como funciona: combina el detalle del libro principal y el desglose por categoria operativa.
# 3) Que hace: alimenta correo HTML/TXT y adjuntos Excel/PDF con el reporte diario completo.
# 4) Como editarla: agrega aqui campos derivados nuevos antes de exponerlos a las plantillas.
def _construir_paquete_datos_diario_completo(sucursal_id, fecha_inicio, fecha_fin):
    datos_libro = _construir_datos_libro_operativo_detallado(
        sucursal_id=sucursal_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        filtro_forzado=bool(fecha_inicio == fecha_fin),
        crear_si_falta=True,
    )
    detalle_categorias = _construir_detalle_capturas_por_categoria(
        sucursal_id=sucursal_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    datos_libro['detalle_categorias'] = detalle_categorias
    return datos_libro




# 1) Para que sirve: obtener categorias destacadas del dia para bloque ejecutivo del correo.
# 2) Como funciona: agrega ingresos/egresos por categoria desde movimientos del dia.
# 3) Que hace: presenta los principales focos de flujo diario en el resumen HTML.
# 4) Como editarla: cambia criterio de ranking para priorizar neto o volumen.
def _obtener_categorias_destacadas_dia(sucursal_id, fecha_contable, limite=6):
    movimientos = MovimientoDiario.objects.filter(
        reporte__sucursal_id=sucursal_id,
        reporte__fecha_contable=fecha_contable,
        eliminado_en__isnull=True,
    ).select_related('concepto__categoria')

    acumulado = defaultdict(lambda: {'ingresos': Decimal('0'), 'egresos': Decimal('0')})

    for movimiento in movimientos:
        categoria = getattr(getattr(movimiento, 'concepto', None), 'categoria', None)
        if not categoria:
            continue

        nombre_categoria = categoria.nombre or 'SIN CATEGORIA'
        tipo_movimiento = str(getattr(movimiento.concepto, 'tipo', '') or '').upper()
        monto = _a_decimal(movimiento.monto)

        if tipo_movimiento == 'INGRESO':
            acumulado[nombre_categoria]['ingresos'] += monto
        else:
            acumulado[nombre_categoria]['egresos'] += monto

    categorias = []
    for nombre, valores in acumulado.items():
        ingresos = _a_flotante(valores['ingresos'])
        egresos = _a_flotante(valores['egresos'])
        neto = ingresos - egresos
        categorias.append({
            'nombre': nombre,
            'ingresos': ingresos,
            'egresos': egresos,
            'neto': neto,
            'ingresos_texto': _formatear_moneda(ingresos),
            'egresos_texto': _formatear_moneda(egresos),
            'neto_texto': _formatear_moneda(neto),
        })

    categorias.sort(key=lambda item: abs(item['ingresos']) + abs(item['egresos']), reverse=True)
    return categorias[: max(1, int(limite))]


# 1) Para que sirve: calcular metricas de estado de resultados mensual por sucursal.
# 2) Como funciona: prioriza snapshot historico cerrado y hace fallback a tiempo real.
# 3) Que hace: alimenta plantilla de cierre mensual y adjuntos oficiales.
# 4) Como editarla: mantener consistencia con endpoint estado_resultados cuando evolucione.
def construir_datos_estado_resultados_mensual(sucursal_id, anio, mes):
    sucursal = Sucursal.objects.filter(id=sucursal_id).first()
    if not sucursal:
        raise ValueError('No existe la sucursal solicitada para generar el cierre mensual.')

    fecha_inicio = date(int(anio), int(mes), 1)
    fecha_fin = date(int(anio), int(mes), monthrange(int(anio), int(mes))[1])
    rubros_base = _construir_rubros_base_estado_resultados()

    libro = LibroEstadoResultados.objects.filter(
        sucursal_id=sucursal_id,
        anio=anio,
        mes=mes,
        estado_mes=LibroEstadoResultados.EstadoMes.CERRADO,
        eliminado_en__isnull=True,
    ).first()

    if libro:
        desglose_snapshot_crudo = libro.desglose_por_rubro or []
        desglose_snapshot = []

        if isinstance(desglose_snapshot_crudo, dict):
            for nombre_rubro, totales in desglose_snapshot_crudo.items():
                desglose_snapshot.append({
                    'rubro_id': f'LEGADO::{nombre_rubro}',
                    'rubro_nombre': nombre_rubro,
                    'rubro_tipo': 'NO_CONTABLE',
                    'rubro_padre': 'SIN GRUPO',
                    'rubro_padre_clave': None,
                    'rubro_padre_considerar_en_estado_resultados': False,
                    'total_ingresos': float((totales or {}).get('ingresos') or 0),
                    'total_egresos': float((totales or {}).get('egresos') or 0),
                    'resultado_neto': float((totales or {}).get('neto') or 0),
                })
        elif isinstance(desglose_snapshot_crudo, list):
            desglose_snapshot = [item for item in desglose_snapshot_crudo if isinstance(item, dict)]

        for rubro in desglose_snapshot:
            rubro_id = rubro.get('rubro_id')
            if rubro_id in rubros_base:
                rubros_base[rubro_id]['total_ingresos'] = _a_flotante(rubro.get('total_ingresos'))
                rubros_base[rubro_id]['total_egresos'] = _a_flotante(rubro.get('total_egresos'))
                rubros_base[rubro_id]['resultado_neto'] = _a_flotante(rubro.get('resultado_neto'))
                continue

            considerar = _rubro_debe_considerarse_en_estado_resultados(
                rubro_id=rubro_id,
                rubro_tipo=rubro.get('rubro_tipo'),
                rubro_padre_clave=rubro.get('rubro_padre_clave'),
                rubro_padre_nombre=rubro.get('rubro_padre'),
                considerar_padre=rubro.get('rubro_padre_considerar_en_estado_resultados', False),
            )
            rubros_base[rubro_id] = {
                'rubro_id': rubro_id,
                'rubro_nombre': rubro.get('rubro_nombre') or 'SIN RUBRO CONTABLE',
                'rubro_tipo': rubro.get('rubro_tipo') or 'NO_CONTABLE',
                'rubro_padre': rubro.get('rubro_padre') or 'SIN GRUPO',
                'rubro_padre_clave': rubro.get('rubro_padre_clave'),
                'rubro_padre_considerar_en_estado_resultados': considerar,
                'total_ingresos': _a_flotante(rubro.get('total_ingresos')),
                'total_egresos': _a_flotante(rubro.get('total_egresos')),
                'resultado_neto': _a_flotante(rubro.get('resultado_neto')),
            }

        rubros_lista = list(rubros_base.values())
        rubros_lista.sort(key=lambda rubro_item: ((rubro_item.get('rubro_padre') or ''), (rubro_item.get('rubro_nombre') or '')))

        rubros_considerados = [
            rubro_item for rubro_item in rubros_lista
            if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
        ]
        rubros_no_considerados = [
            rubro_item for rubro_item in rubros_lista
            if not bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
        ]

        total_ingresos_considerados = sum(_a_flotante(rubro_item.get('total_ingresos')) for rubro_item in rubros_considerados)
        total_egresos_considerados = sum(_a_flotante(rubro_item.get('total_egresos')) for rubro_item in rubros_considerados)
        resultado_neto_considerado = total_ingresos_considerados - total_egresos_considerados
        total_ingresos_no_considerados = sum(_a_flotante(rubro_item.get('total_ingresos')) for rubro_item in rubros_no_considerados)
        total_egresos_no_considerados = sum(_a_flotante(rubro_item.get('total_egresos')) for rubro_item in rubros_no_considerados)
        resultado_neto_no_considerado = total_ingresos_no_considerados - total_egresos_no_considerados

        return {
            'fuente': 'snapshot_historico',
            'sucursal': {'id': sucursal.id, 'nombre': sucursal.nombre},
            'periodo': f"{anio}/{mes:02d}",
            'anio': int(anio),
            'mes': int(mes),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado_mes': libro.estado_mes,
            'saldo_arrastre_inicio': _a_flotante(libro.saldo_arrastre_inicio),
            'total_ingresos': _a_flotante(total_ingresos_considerados),
            'total_egresos': _a_flotante(total_egresos_considerados),
            'resultado_neto': _a_flotante(resultado_neto_considerado),
            'saldo_arrastre_fin': _a_flotante(libro.saldo_arrastre_inicio) + _a_flotante(resultado_neto_considerado),
            'total_ingresos_no_considerados': _a_flotante(total_ingresos_no_considerados),
            'total_egresos_no_considerados': _a_flotante(total_egresos_no_considerados),
            'resultado_neto_no_considerado': _a_flotante(resultado_neto_no_considerado),
            'por_rubro': rubros_lista,
            'movimientos': 0,
        }

    movimientos = MovimientoDiario.objects.filter(
        reporte__sucursal_id=sucursal_id,
        reporte__fecha_contable__year=anio,
        reporte__fecha_contable__month=mes,
        eliminado_en__isnull=True,
    ).select_related('concepto__rubro_contable', 'concepto__rubro_contable__padre')

    por_rubro = dict(rubros_base)

    for movimiento in movimientos:
        rubro = movimiento.concepto.rubro_contable
        rubro_id = rubro.id if rubro else 'SIN_RUBRO_CONTABLE'
        rubro_nombre = rubro.nombre if rubro else 'SIN RUBRO CONTABLE'
        rubro_tipo = rubro.tipo if rubro else 'NO_CONTABLE'
        rubro_padre = rubro.padre.nombre if rubro and rubro.padre else 'SIN GRUPO'
        rubro_padre_clave = rubro.padre.clave if rubro and rubro.padre else None
        rubro_padre_considerar = _rubro_debe_considerarse_en_estado_resultados(
            rubro_id=rubro_id,
            rubro_tipo=rubro_tipo,
            rubro_padre_clave=rubro_padre_clave,
            rubro_padre_nombre=rubro_padre,
            considerar_padre=(bool(rubro.padre.considerar_en_estado_resultados) if rubro and rubro.padre else False),
        )

        if rubro_id not in por_rubro:
            por_rubro[rubro_id] = {
                'rubro_id': rubro_id,
                'rubro_nombre': rubro_nombre,
                'rubro_tipo': rubro_tipo,
                'rubro_padre': rubro_padre,
                'rubro_padre_clave': rubro_padre_clave,
                'rubro_padre_considerar_en_estado_resultados': rubro_padre_considerar,
                'total_ingresos': 0.0,
                'total_egresos': 0.0,
                'resultado_neto': 0.0,
            }

        campo = 'total_ingresos' if movimiento.concepto.tipo == 'INGRESO' else 'total_egresos'
        por_rubro[rubro_id][campo] += _a_flotante(movimiento.monto)

    for rubro_item in por_rubro.values():
        rubro_item['resultado_neto'] = _a_flotante(rubro_item.get('total_ingresos')) - _a_flotante(rubro_item.get('total_egresos'))

    rubros_lista = list(por_rubro.values())
    rubros_lista.sort(key=lambda rubro_item: ((rubro_item.get('rubro_padre') or ''), (rubro_item.get('rubro_nombre') or '')))

    rubros_considerados = [
        rubro_item for rubro_item in rubros_lista
        if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
    ]
    rubros_no_considerados = [
        rubro_item for rubro_item in rubros_lista
        if not bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
    ]

    total_ingresos_considerados = sum(_a_flotante(rubro_item.get('total_ingresos')) for rubro_item in rubros_considerados)
    total_egresos_considerados = sum(_a_flotante(rubro_item.get('total_egresos')) for rubro_item in rubros_considerados)
    resultado_neto_considerado = total_ingresos_considerados - total_egresos_considerados
    total_ingresos_no_considerados = sum(_a_flotante(rubro_item.get('total_ingresos')) for rubro_item in rubros_no_considerados)
    total_egresos_no_considerados = sum(_a_flotante(rubro_item.get('total_egresos')) for rubro_item in rubros_no_considerados)
    resultado_neto_no_considerado = total_ingresos_no_considerados - total_egresos_no_considerados

    primer_reporte = ReporteDiario.objects.filter(
        sucursal_id=sucursal_id,
        fecha_contable__year=anio,
        fecha_contable__month=mes,
    ).order_by('fecha_contable').first()
    saldo_arrastre_inicio = _a_flotante(primer_reporte.saldo_arrastre_inicio if primer_reporte else 0)

    return {
        'fuente': 'tiempo_real',
        'sucursal': {'id': sucursal.id, 'nombre': sucursal.nombre},
        'periodo': f"{anio}/{mes:02d}",
        'anio': int(anio),
        'mes': int(mes),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado_mes': 'ABIERTO',
        'saldo_arrastre_inicio': saldo_arrastre_inicio,
        'total_ingresos': _a_flotante(total_ingresos_considerados),
        'total_egresos': _a_flotante(total_egresos_considerados),
        'resultado_neto': _a_flotante(resultado_neto_considerado),
        'saldo_arrastre_fin': saldo_arrastre_inicio + _a_flotante(resultado_neto_considerado),
        'total_ingresos_no_considerados': _a_flotante(total_ingresos_no_considerados),
        'total_egresos_no_considerados': _a_flotante(total_egresos_no_considerados),
        'resultado_neto_no_considerado': _a_flotante(resultado_neto_no_considerado),
        'por_rubro': rubros_lista,
        'movimientos': movimientos.count(),
    }


# 1) Para que sirve: aplicar estilos base a una celda de encabezado de Excel.
# 2) Como funciona: combina negritas, color de fondo y alineacion centrada.
# 3) Que hace: mejora legibilidad del archivo adjunto para direccion.
# 4) Como editarla: ajusta paleta si cambia la identidad visual del correo.
def _estilizar_encabezado_excel(celda):
    celda.font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    celda.fill = PatternFill(fill_type='solid', fgColor='0F172A')
    celda.alignment = Alignment(horizontal='center', vertical='center')


PALETA_TIPO_FILA_PDF = {
    'SALDO_INICIAL': '#E0F2FE',
    'SEPARADOR_FECHA': '#DBEAFE',
    'SEPARADOR_AJUSTES': '#FEF3C7',
    'AJUSTE_CONTABLE': '#F8FAFC',
    'TOTAL_PERIODO': '#FDE68A',
    'EFECTIVO_FISICO': '#FECACA',
}


# 1) Para que sirve: formatear fecha ISO de fila a etiqueta corta dd/mm/aa para tablas.
# 2) Como funciona: parsea ISO y aplica strftime con tolerancia ante valores invalidos.
# 3) Que hace: alinea las columnas Fecha del PDF/Excel con la vista web.
# 4) Como editarla: ajusta el formato si cambia la convencion regional.
def _formatear_fecha_corta(valor):
    if not valor:
        return ''
    try:
        return date.fromisoformat(str(valor)).strftime('%d/%m/%y')
    except Exception:
        return str(valor)


# 1) Para que sirve: construir el bloque Tabla del libro operativo para reportlab.
# 2) Como funciona: arma encabezado, filas y aplica colores por tipo_fila.
# 3) Que hace: reusa misma estructura para hoja principal y por categoria.
# 4) Como editarla: cambia anchos de columna o paleta cuando cambie el diseno.
def _construir_tabla_libro_pdf(filas, ancho_total=540):
    encabezados = ['Fecha', 'Concepto', 'Ingreso', 'Egreso', 'Saldo']
    filas_detalle = [encabezados]
    tipos_fila = []

    for fila in filas:
        filas_detalle.append([
            _formatear_fecha_corta(fila.get('fecha')),
            str(fila.get('concepto') or ''),
            _formatear_moneda(fila.get('ingreso')) if fila.get('ingreso') is not None else '-',
            _formatear_moneda(fila.get('egreso')) if fila.get('egreso') is not None else '-',
            _formatear_moneda(fila.get('saldo')) if fila.get('saldo') is not None else '-',
        ])
        tipos_fila.append(str(fila.get('tipo_fila') or ''))

    anchos = [
        int(ancho_total * 0.11),
        int(ancho_total * 0.42),
        int(ancho_total * 0.155),
        int(ancho_total * 0.155),
        ancho_total - int(ancho_total * 0.11) - int(ancho_total * 0.42) - int(ancho_total * 0.155) - int(ancho_total * 0.155),
    ]

    tabla = Table(filas_detalle, colWidths=anchos, repeatRows=1)
    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])

    for indice, tipo_fila in enumerate(tipos_fila, start=1):
        color_fondo = PALETA_TIPO_FILA_PDF.get(tipo_fila)
        if color_fondo:
            estilo.add('BACKGROUND', (0, indice), (-1, indice), colors.HexColor(color_fondo))
            estilo.add('FONTNAME', (0, indice), (-1, indice), 'Helvetica-Bold')
        if tipo_fila == 'SEPARADOR_AJUSTES':
            estilo.add('SPAN', (0, indice), (-1, indice))
            estilo.add('ALIGN', (0, indice), (-1, indice), 'CENTER')

    tabla.setStyle(estilo)
    return tabla


# 1) Para que sirve: dibujar tarjetas KPI horizontales en PDF (saldo inicial / ingresos / egresos / final).
# 2) Como funciona: arma una tabla 4 columnas con encabezados de paleta y valores monetarios.
# 3) Que hace: replica la franja superior del Reporte Diario en pantalla.
# 4) Como editarla: agrega o quita columnas si cambia el set de KPIs visibles.
def _construir_tarjetas_kpi_pdf(saldo_inicial, total_ingresos, total_egresos, saldo_final, ancho_total=540):
    kpis = [
        ['Saldo inicial', 'Total ingresos', 'Total egresos', 'Saldo final'],
        [
            _formatear_moneda(saldo_inicial),
            _formatear_moneda(total_ingresos),
            _formatear_moneda(total_egresos),
            _formatear_moneda(saldo_final),
        ],
    ]
    ancho_columna = int(ancho_total / 4)
    tabla = Table(kpis, colWidths=[ancho_columna] * 4)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F0FDF4')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#FFF1F2')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#F8FAFC')),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#166534')),
        ('TEXTCOLOR', (2, 0), (2, 0), colors.HexColor('#9F1239')),
        ('TEXTCOLOR', (3, 0), (3, 0), colors.HexColor('#334155')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tabla


# 1) Para que sirve: construir adjunto Excel del reporte diario fiel a la vista web.
# 2) Como funciona: crea hoja Reporte_Diario con resumen, tabla principal y bancos, y una hoja por cada categoria.
# 3) Que hace: entrega archivo de auditoria con el mismo desglose que ven los usuarios.
# 4) Como editarla: ajusta colores, anchos o agrega hojas nuevas conforme evolucione el reporte.
def generar_excel_libro_operativo(datos_libro):
    libro = Workbook()
    hoja_principal = libro.active
    hoja_principal.title = 'Reporte_Diario'

    resumen = datos_libro.get('resumen') or {}
    sucursal_nombre = (datos_libro.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    fecha_exportacion = timezone.localtime(timezone.now())
    filtro = datos_libro.get('filtro_aplicado') or {}

    periodo = _formatear_fecha(date.fromisoformat(filtro.get('fecha_inicio'))) if filtro.get('fecha_inicio') else '-'
    if filtro.get('fecha_inicio') and filtro.get('fecha_fin') and filtro.get('fecha_inicio') != filtro.get('fecha_fin'):
        periodo = f"{_formatear_fecha(date.fromisoformat(filtro.get('fecha_inicio')))} al {_formatear_fecha(date.fromisoformat(filtro.get('fecha_fin')))}"

    fila_actual = 1
    hoja_principal.cell(row=fila_actual, column=1, value='Reporte diario operativo').font = Font(
        name='Calibri', size=14, bold=True, color='0F172A'
    )
    fila_actual += 1

    encabezado_meta = [
        ('Fecha de exportacion', fecha_exportacion.strftime('%d/%m/%Y %H:%M:%S')),
        ('Casino', sucursal_nombre),
        ('Periodo', periodo),
    ]
    for etiqueta, valor in encabezado_meta:
        hoja_principal.cell(row=fila_actual, column=1, value=etiqueta).font = Font(
            name='Calibri', size=11, bold=True, color='0F172A'
        )
        hoja_principal.cell(row=fila_actual, column=2, value=valor)
        fila_actual += 1

    fila_actual += 1
    celda_indicador = hoja_principal.cell(row=fila_actual, column=1, value='Indicador')
    celda_valor = hoja_principal.cell(row=fila_actual, column=2, value='Valor')
    _estilizar_encabezado_excel(celda_indicador)
    _estilizar_encabezado_excel(celda_valor)
    fila_actual += 1

    indicadores = [
        ('Saldo inicial del rango', _a_flotante(resumen.get('saldo_inicial')), True),
        ('Total ingresos', _a_flotante(resumen.get('total_ingresos')), True),
        ('Total egresos', _a_flotante(resumen.get('total_egresos')), True),
        ('Saldo final', _a_flotante(resumen.get('saldo_final')), True),
        ('Dias consultados', int(resumen.get('dias_consultados') or 0), False),
        ('Dias con reporte', int(resumen.get('dias_con_reporte') or 0), False),
    ]
    for etiqueta, valor, es_moneda in indicadores:
        hoja_principal.cell(row=fila_actual, column=1, value=etiqueta).font = Font(
            name='Calibri', size=11, bold=True, color='0F172A'
        )
        celda_valor = hoja_principal.cell(row=fila_actual, column=2, value=valor)
        celda_valor.number_format = '#,##0.00' if es_moneda else '0'
        celda_valor.alignment = Alignment(horizontal='right', vertical='center')
        fila_actual += 1

    fila_actual += 1

    nombres_bancos = {'BANORTE AHIS', 'BANORTE BAHIA', 'BBVA BAHIA'}
    filas_libro = datos_libro.get('filas') or []
    bancos = datos_libro.get('bancos_informativos') or []
    detalle_categorias = datos_libro.get('detalle_categorias') or []

    filas_principales = [
        fila for fila in filas_libro
        if str(fila.get('concepto') or '').strip().upper() not in nombres_bancos
        and str(fila.get('tipo_fila') or '') != 'SEPARADOR_AJUSTES'
    ]

    ultima_fila_tabla = _escribir_tabla_libro_excel(hoja_principal, filas_principales, fila_inicio=fila_actual)
    fila_actual = ultima_fila_tabla + 2

    if bancos:
        hoja_principal.cell(row=fila_actual, column=1, value='Bancos (Informativo)').font = Font(
            name='Calibri', size=12, bold=True, color='0F172A'
        )
        fila_actual += 1
        celda_concepto = hoja_principal.cell(row=fila_actual, column=2, value='Concepto')
        celda_actual = hoja_principal.cell(row=fila_actual, column=3, value='Actual')
        _estilizar_encabezado_excel(celda_concepto)
        _estilizar_encabezado_excel(celda_actual)
        fila_actual += 1
        for fila in bancos:
            monto = fila.get('ingreso') if fila.get('ingreso') is not None else fila.get('egreso')
            hoja_principal.cell(row=fila_actual, column=2, value=str(fila.get('concepto') or ''))
            celda_monto = hoja_principal.cell(
                row=fila_actual,
                column=3,
                value=_a_flotante(monto) if monto is not None else None,
            )
            celda_monto.number_format = '#,##0.00'
            celda_monto.alignment = Alignment(horizontal='right', vertical='center')
            fila_actual += 1

    hoja_principal.column_dimensions['A'].width = 12
    hoja_principal.column_dimensions['B'].width = 46
    hoja_principal.column_dimensions['C'].width = 18
    hoja_principal.column_dimensions['D'].width = 18
    hoja_principal.column_dimensions['E'].width = 18

    nombres_existentes = set(libro.sheetnames)
    for categoria in detalle_categorias:
        nombre_categoria = str(categoria.get('categoria_nombre') or 'CATEGORIA').strip()
        nombre_hoja = _nombre_hoja_categoria_excel(nombre_categoria, nombres_existentes)
        nombres_existentes.add(nombre_hoja)
        _escribir_hoja_libro_excel(
            libro=libro,
            nombre_hoja=nombre_hoja,
            filas=categoria.get('filas') or [],
            encabezado_extra=[
                ('Captura operativa', nombre_categoria),
                ('Saldo inicial del mes', _a_flotante(categoria.get('saldo_inicial_mes'))),
                ('Total ingresos', _a_flotante(categoria.get('total_ingresos'))),
                ('Total egresos', _a_flotante(categoria.get('total_egresos'))),
                ('Saldo final', _a_flotante(categoria.get('saldo_final'))),
                ('', ''),
            ],
        )

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# 1) Para que sirve: generar nombre seguro para hoja Excel respetando 31 caracteres.
# 2) Como funciona: limpia caracteres prohibidos y corta a longitud maxima.
# 3) Que hace: evita errores de openpyxl al usar nombres de categoria con simbolos.
# 4) Como editarla: ajusta lista de caracteres prohibidos si Microsoft amplia restricciones.
def _nombre_hoja_categoria_excel(nombre_categoria, nombres_existentes):
    prohibidos = '\\/?*[]:'
    limpio = ''.join('_' if caracter in prohibidos else caracter for caracter in str(nombre_categoria))
    base = limpio.strip()[:28] or 'CATEGORIA'
    candidato = base
    contador = 2
    while candidato in nombres_existentes:
        sufijo = f"_{contador}"
        candidato = (base[: max(1, 31 - len(sufijo))] + sufijo)
        contador += 1
    return candidato


# 1) Para que sirve: escribir una tabla de libro operativo en una hoja existente.
# 2) Como funciona: dibuja encabezados, filas y aplica estilos por tipo_fila.
# 3) Que hace: reutiliza el formato del reporte diario en varias hojas.
# 4) Como editarla: ajusta anchos o colores si cambia el diseno.
def _escribir_tabla_libro_excel(hoja, filas, fila_inicio=1):
    encabezados = ['Fecha', 'Concepto', 'Ingreso', 'Egreso', 'Saldo']
    for indice_columna, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(row=fila_inicio, column=indice_columna, value=encabezado)
        _estilizar_encabezado_excel(celda)

    fila_datos = fila_inicio + 1
    ultima_fila = fila_inicio

    paleta = {
        'SALDO_INICIAL': 'E0F2FE',
        'SEPARADOR_FECHA': 'DBEAFE',
        'SEPARADOR_AJUSTES': 'FEF3C7',
        'AJUSTE_CONTABLE': 'F8FAFC',
        'TOTAL_PERIODO': 'FDE68A',
        'EFECTIVO_FISICO': 'FECACA',
    }

    for indice, fila in enumerate(filas, start=fila_datos):
        ingreso = fila.get('ingreso')
        egreso = fila.get('egreso')
        saldo = fila.get('saldo')

        hoja.cell(row=indice, column=1, value=_formatear_fecha_corta(fila.get('fecha')))
        hoja.cell(row=indice, column=2, value=str(fila.get('concepto') or ''))
        hoja.cell(row=indice, column=3, value=_a_flotante(ingreso) if ingreso is not None else None)
        hoja.cell(row=indice, column=4, value=_a_flotante(egreso) if egreso is not None else None)
        hoja.cell(row=indice, column=5, value=_a_flotante(saldo) if saldo is not None else None)

        for columna in (3, 4, 5):
            celda = hoja.cell(row=indice, column=columna)
            celda.number_format = '#,##0.00'
            celda.alignment = Alignment(horizontal='right', vertical='center')

        color_fondo = paleta.get(str(fila.get('tipo_fila') or ''))
        if color_fondo:
            for columna in range(1, 6):
                celda = hoja.cell(row=indice, column=columna)
                celda.fill = PatternFill(fill_type='solid', fgColor=color_fondo)
                celda.font = Font(name='Calibri', size=10, bold=True, color='111827')

        ultima_fila = indice

    hoja.column_dimensions['A'].width = 12
    hoja.column_dimensions['B'].width = 46
    hoja.column_dimensions['C'].width = 18
    hoja.column_dimensions['D'].width = 18
    hoja.column_dimensions['E'].width = 18
    return ultima_fila


# 1) Para que sirve: escribir una hoja Excel completa con encabezado, filas y formato.
# 2) Como funciona: arma encabezado opcional, fila de columnas y aplica colores por tipo_fila.
# 3) Que hace: garantiza que todas las hojas del reporte usen el mismo lenguaje visual.
# 4) Como editarla: agrega columnas o estilos centralizados aqui.
def _escribir_hoja_libro_excel(libro, nombre_hoja, filas, encabezado_extra=None):
    hoja = libro.create_sheet(nombre_hoja)
    fila_actual = 1

    if encabezado_extra:
        for etiqueta, valor in encabezado_extra:
            hoja.cell(row=fila_actual, column=1, value=etiqueta).font = Font(name='Calibri', size=11, bold=True, color='0F172A')
            celda_valor = hoja.cell(row=fila_actual, column=2, value=valor)
            if isinstance(valor, (int, float)):
                celda_valor.number_format = '#,##0.00'
                celda_valor.alignment = Alignment(horizontal='right', vertical='center')
            fila_actual += 1

    _escribir_tabla_libro_excel(hoja, filas, fila_inicio=fila_actual)


# 1) Para que sirve: construir adjunto PDF fiel a la vista del Reporte Diario.
# 2) Como funciona: replica encabezado, KPIs, libro detallado, bancos y agrega pagina por categoria.
# 3) Que hace: permite revision formal sin depender del frontend, mostrando cada captura completa.
# 4) Como editarla: ajusta paleta, anchos o secciones nuevas en el dibujo del documento.
def generar_pdf_libro_operativo(datos_libro):
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    ancho_contenido = documento.width

    estilos = getSampleStyleSheet()
    elementos = []

    sucursal_nombre = (datos_libro.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    filtro = datos_libro.get('filtro_aplicado') or {}
    resumen = datos_libro.get('resumen') or {}
    bancos = datos_libro.get('bancos_informativos') or []
    detalle_categorias = datos_libro.get('detalle_categorias') or []
    filas_libro = datos_libro.get('filas') or []

    nombres_bancos = {'BANORTE AHIS', 'BANORTE BAHIA', 'BBVA BAHIA'}
    filas_principales = [
        fila for fila in filas_libro
        if str(fila.get('concepto') or '').strip().upper() not in nombres_bancos
        and str(fila.get('tipo_fila') or '') != 'SEPARADOR_AJUSTES'
    ]

    fecha_inicio = date.fromisoformat(filtro.get('fecha_inicio')) if filtro.get('fecha_inicio') else None
    fecha_fin = date.fromisoformat(filtro.get('fecha_fin')) if filtro.get('fecha_fin') else None
    periodo_texto = _formatear_fecha(fecha_inicio) if fecha_inicio else '-'
    if fecha_inicio and fecha_fin and fecha_inicio != fecha_fin:
        periodo_texto = f"{_formatear_fecha(fecha_inicio)} al {_formatear_fecha(fecha_fin)}"

    elementos.append(Paragraph('Reporte Diario Operativo', estilos['Heading2']))
    elementos.append(Paragraph(f"Casino: <b>{sucursal_nombre}</b>", estilos['BodyText']))
    elementos.append(Paragraph(f"Periodo contable: <b>{periodo_texto}</b>", estilos['BodyText']))
    elementos.append(Paragraph(
        f"Fecha de exportacion: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')}",
        estilos['BodyText'],
    ))
    elementos.append(Spacer(1, 8))

    elementos.append(_construir_tarjetas_kpi_pdf(
        saldo_inicial=resumen.get('saldo_inicial'),
        total_ingresos=resumen.get('total_ingresos'),
        total_egresos=resumen.get('total_egresos'),
        saldo_final=resumen.get('saldo_final'),
        ancho_total=ancho_contenido,
    ))

    elementos.append(Paragraph(
        f"Movimientos registrados: {len([f for f in filas_principales if f.get('tipo_fila') == 'MOVIMIENTO_ADMIN'])} "
        f"| Dias consultados: {int(resumen.get('dias_consultados') or 0)} "
        f"| Dias con reporte: {int(resumen.get('dias_con_reporte') or 0)}",
        estilos['BodyText'],
    ))
    elementos.append(Spacer(1, 10))

    elementos.append(_construir_tabla_libro_pdf(filas_principales, ancho_total=ancho_contenido))

    if bancos:
        elementos.append(Spacer(1, 14))
        elementos.append(Paragraph('Bancos (Informativo)', estilos['Heading3']))
        bancos_data = [['Concepto', 'Actual']]
        for fila in bancos:
            monto = fila.get('ingreso') if fila.get('ingreso') is not None else fila.get('egreso')
            bancos_data.append([
                str(fila.get('concepto') or ''),
                _formatear_moneda(monto) if monto is not None else '-',
            ])
        ancho_concepto = int(ancho_contenido * 0.6)
        tabla_bancos = Table(bancos_data, colWidths=[ancho_concepto, ancho_contenido - ancho_concepto], repeatRows=1)
        tabla_bancos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elementos.append(tabla_bancos)

    for categoria in detalle_categorias:
        elementos.append(PageBreak())
        nombre_categoria = str(categoria.get('categoria_nombre') or 'CATEGORIA').strip()
        elementos.append(Paragraph(f"Captura: {nombre_categoria}", estilos['Heading2']))
        elementos.append(Paragraph(
            f"Casino: <b>{sucursal_nombre}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Periodo: <b>{periodo_texto}</b>",
            estilos['BodyText'],
        ))
        elementos.append(Spacer(1, 6))
        elementos.append(_construir_tarjetas_kpi_pdf(
            saldo_inicial=categoria.get('saldo_inicial_mes'),
            total_ingresos=categoria.get('total_ingresos'),
            total_egresos=categoria.get('total_egresos'),
            saldo_final=categoria.get('saldo_final'),
            ancho_total=ancho_contenido,
        ))
        elementos.append(Spacer(1, 8))
        elementos.append(_construir_tabla_libro_pdf(categoria.get('filas') or [], ancho_total=ancho_contenido))

    documento.build(elementos)
    return salida.getvalue()


# 1) Para que sirve: construir adjunto Excel del cierre mensual por casino.
# 2) Como funciona: crea hoja de resumen y hoja de rubros con montos considerados/no considerados.
# 3) Que hace: entrega respaldo mensual en formato editable para direccion.
# 4) Como editarla: agrega columnas de comparativo si se requiere variacion vs mes previo.
def generar_excel_cierre_mensual(datos_mensuales):
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = 'Resumen'

    sucursal_nombre = (datos_mensuales.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    anio = int(datos_mensuales.get('anio') or 0)
    mes = int(datos_mensuales.get('mes') or 0)
    periodo_texto = f"{_nombre_mes(mes).capitalize()} {anio}"

    filas_resumen = [
        ['Estado de resultados mensual', ''],
        ['Fecha de exportacion', timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')],
        ['Casino', sucursal_nombre],
        ['Periodo', periodo_texto],
        ['Fuente de datos', str(datos_mensuales.get('fuente') or 'tiempo_real')],
        ['', ''],
        ['Indicador', 'Valor'],
        ['Saldo arrastre inicio', _a_flotante(datos_mensuales.get('saldo_arrastre_inicio'))],
        ['Total ingresos', _a_flotante(datos_mensuales.get('total_ingresos'))],
        ['Total egresos', _a_flotante(datos_mensuales.get('total_egresos'))],
        ['Resultado neto', _a_flotante(datos_mensuales.get('resultado_neto'))],
        ['Saldo arrastre fin', _a_flotante(datos_mensuales.get('saldo_arrastre_fin'))],
        ['Ingresos no considerados', _a_flotante(datos_mensuales.get('total_ingresos_no_considerados'))],
        ['Egresos no considerados', _a_flotante(datos_mensuales.get('total_egresos_no_considerados'))],
        ['Neto no considerado', _a_flotante(datos_mensuales.get('resultado_neto_no_considerado'))],
    ]

    for fila in filas_resumen:
        hoja_resumen.append(fila)

    hoja_resumen['A1'].font = Font(name='Calibri', size=14, bold=True, color='0F172A')
    _estilizar_encabezado_excel(hoja_resumen['A7'])
    _estilizar_encabezado_excel(hoja_resumen['B7'])

    for indice_fila in range(8, 16):
        hoja_resumen[f'B{indice_fila}'].number_format = '#,##0.00'

    hoja_resumen.column_dimensions['A'].width = 42
    hoja_resumen.column_dimensions['B'].width = 24

    hoja_detalle = libro.create_sheet('Estado_Resultados_Mensual')
    encabezados = ['Grupo', 'Rubro', 'Ingresos', 'Egresos', 'Resultado_neto', 'Considerado']
    hoja_detalle.append(encabezados)

    for columna in range(1, len(encabezados) + 1):
        _estilizar_encabezado_excel(hoja_detalle.cell(row=1, column=columna))

    for indice, rubro in enumerate(datos_mensuales.get('por_rubro') or [], start=2):
        considerado = bool(rubro.get('rubro_padre_considerar_en_estado_resultados', False))
        hoja_detalle.append([
            str(rubro.get('rubro_padre') or ''),
            str(rubro.get('rubro_nombre') or ''),
            _a_flotante(rubro.get('total_ingresos')),
            _a_flotante(rubro.get('total_egresos')),
            _a_flotante(rubro.get('resultado_neto')),
            'SI' if considerado else 'NO',
        ])

        for columna in (3, 4, 5):
            hoja_detalle.cell(row=indice, column=columna).number_format = '#,##0.00'
            hoja_detalle.cell(row=indice, column=columna).alignment = Alignment(horizontal='right', vertical='center')

        if not considerado:
            for columna in range(1, 7):
                hoja_detalle.cell(row=indice, column=columna).fill = PatternFill(fill_type='solid', fgColor='F8FAFC')
                hoja_detalle.cell(row=indice, column=columna).font = Font(name='Calibri', size=10, color='475569')

    hoja_detalle.column_dimensions['A'].width = 26
    hoja_detalle.column_dimensions['B'].width = 44
    hoja_detalle.column_dimensions['C'].width = 18
    hoja_detalle.column_dimensions['D'].width = 18
    hoja_detalle.column_dimensions['E'].width = 18
    hoja_detalle.column_dimensions['F'].width = 14

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# 1) Para que sirve: construir adjunto PDF del cierre mensual completo.
# 2) Como funciona: dibuja bloque de resumen y tabla de rubros con marcador de consideracion.
# 3) Que hace: facilita revision ejecutiva del mes cerrado en formato portable.
# 4) Como editarla: incorporar pagina extra de insights cuando direccion lo solicite.
def generar_pdf_cierre_mensual(datos_mensuales):
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20,
    )

    estilos = getSampleStyleSheet()
    elementos = []

    sucursal_nombre = (datos_mensuales.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    anio = int(datos_mensuales.get('anio') or 0)
    mes = int(datos_mensuales.get('mes') or 0)
    periodo_texto = f"{_nombre_mes(mes).capitalize()} {anio}"

    elementos.append(Paragraph('Estado de Resultados Mensual', estilos['Heading2']))
    elementos.append(Paragraph(f"Casino: {sucursal_nombre}", estilos['BodyText']))
    elementos.append(Paragraph(f"Periodo: {periodo_texto}", estilos['BodyText']))
    elementos.append(Paragraph(f"Fuente de datos: {datos_mensuales.get('fuente')}", estilos['BodyText']))
    elementos.append(Paragraph(f"Fecha de exportacion: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')}", estilos['BodyText']))
    elementos.append(Spacer(1, 10))

    tabla_resumen_datos = [
        ['Indicador', 'Valor'],
        ['Saldo arrastre inicio', _formatear_moneda(datos_mensuales.get('saldo_arrastre_inicio'))],
        ['Total ingresos', _formatear_moneda(datos_mensuales.get('total_ingresos'))],
        ['Total egresos', _formatear_moneda(datos_mensuales.get('total_egresos'))],
        ['Resultado neto', _formatear_moneda(datos_mensuales.get('resultado_neto'))],
        ['Saldo arrastre fin', _formatear_moneda(datos_mensuales.get('saldo_arrastre_fin'))],
        ['Ingresos no considerados', _formatear_moneda(datos_mensuales.get('total_ingresos_no_considerados'))],
        ['Egresos no considerados', _formatear_moneda(datos_mensuales.get('total_egresos_no_considerados'))],
    ]

    tabla_resumen = Table(tabla_resumen_datos, colWidths=[250, 170], repeatRows=1)
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 12))

    filas_detalle = [['Grupo', 'Rubro', 'Ingresos', 'Egresos', 'Resultado neto', 'Considerado']]
    for rubro in datos_mensuales.get('por_rubro') or []:
        filas_detalle.append([
            str(rubro.get('rubro_padre') or ''),
            str(rubro.get('rubro_nombre') or ''),
            _formatear_moneda(rubro.get('total_ingresos')),
            _formatear_moneda(rubro.get('total_egresos')),
            _formatear_moneda(rubro.get('resultado_neto')),
            'SI' if bool(rubro.get('rubro_padre_considerar_en_estado_resultados', False)) else 'NO',
        ])

    tabla_detalle = Table(filas_detalle, colWidths=[120, 260, 110, 110, 120, 80], repeatRows=1)
    estilo_detalle = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    for indice_fila, rubro in enumerate(datos_mensuales.get('por_rubro') or [], start=1):
        if bool(rubro.get('rubro_padre_considerar_en_estado_resultados', False)):
            continue
        estilo_detalle.add('BACKGROUND', (0, indice_fila), (-1, indice_fila), colors.HexColor('#F8FAFC'))
        estilo_detalle.add('TEXTCOLOR', (0, indice_fila), (-1, indice_fila), colors.HexColor('#475569'))

    tabla_detalle.setStyle(estilo_detalle)
    elementos.append(tabla_detalle)

    documento.build(elementos)
    return salida.getvalue()


PALETA_TIPO_FILA_HTML = {
    'SALDO_INICIAL': '#e0f2fe',
    'SEPARADOR_FECHA': '#dbeafe',
    'SEPARADOR_AJUSTES': '#fef3c7',
    'AJUSTE_CONTABLE': '#f8fafc',
    'TOTAL_PERIODO': '#fde68a',
    'EFECTIVO_FISICO': '#fecaca',
}


# 1) Para que sirve: serializar una fila del libro operativo para plantillas HTML/TXT.
# 2) Como funciona: aplica formateadores monetarios y precalcula colores de fondo.
# 3) Que hace: evita logica en plantillas y mantiene la vista fiel al Reporte Diario.
# 4) Como editarla: agrega campos derivados nuevos cuando se sumen variantes de fila.
def _normalizar_fila_para_template(fila):
    tipo_fila = str(fila.get('tipo_fila') or '')
    return {
        'fecha_texto': _formatear_fecha_corta(fila.get('fecha')),
        'concepto': str(fila.get('concepto') or ''),
        'ingreso_texto': _formatear_moneda(fila.get('ingreso')) if fila.get('ingreso') is not None else '-',
        'egreso_texto': _formatear_moneda(fila.get('egreso')) if fila.get('egreso') is not None else '-',
        'saldo_texto': _formatear_moneda(fila.get('saldo')) if fila.get('saldo') is not None else '-',
        'tipo_fila': tipo_fila,
        'color_fondo': PALETA_TIPO_FILA_HTML.get(tipo_fila, '#ffffff'),
        'es_separador_ajustes': tipo_fila == 'SEPARADOR_AJUSTES',
        'es_separador_fecha': tipo_fila == 'SEPARADOR_FECHA',
        'es_total_periodo': tipo_fila == 'TOTAL_PERIODO',
        'es_efectivo_fisico': tipo_fila == 'EFECTIVO_FISICO',
    }


# 1) Para que sirve: crear el paquete completo del correo diario ejecutivo por casino.
# 2) Como funciona: genera contexto HTML/TXT y adjuntos Excel/PDF del mismo corte diario.
# 3) Que hace: deja listo el envio manual o programado sin duplicar logica.
# 4) Como editarla: agrega nuevas metricas al contexto y a las plantillas asociadas.
def construir_paquete_correo_resumen_diario_ejecutivo(sucursal, fecha_contable=None):
    if isinstance(sucursal, int):
        sucursal = Sucursal.objects.filter(id=sucursal).first()
    if not sucursal:
        raise ValueError('Sucursal invalida para construir el resumen diario ejecutivo.')

    fecha_objetivo = fecha_contable or _dia_contable_actual()
    if isinstance(fecha_objetivo, str):
        fecha_objetivo = date.fromisoformat(fecha_objetivo)

    fecha_inicio_mes = fecha_objetivo.replace(day=1)
    periodo_contable_texto = _formatear_fecha(fecha_inicio_mes)
    if fecha_inicio_mes != fecha_objetivo:
        periodo_contable_texto = f"{_formatear_fecha(fecha_inicio_mes)} al {_formatear_fecha(fecha_objetivo)}"

    datos_libro = _construir_paquete_datos_diario_completo(
        sucursal_id=sucursal.id,
        fecha_inicio=fecha_inicio_mes,
        fecha_fin=fecha_objetivo,
    )

    resumen = datos_libro.get('resumen') or {}
    bancos_informativos = datos_libro.get('bancos_informativos') or []
    detalle_categorias = datos_libro.get('detalle_categorias') or []
    filas_libro_principal = [
        fila for fila in (datos_libro.get('filas') or [])
        if str(fila.get('concepto') or '').strip().upper() not in {'BANORTE AHIS', 'BANORTE BAHIA', 'BBVA BAHIA'}
        and str(fila.get('tipo_fila') or '') != 'SEPARADOR_AJUSTES'
    ]

    filas_template = [_normalizar_fila_para_template(fila) for fila in filas_libro_principal]
    bancos_template = [_normalizar_fila_para_template(fila) for fila in bancos_informativos]
    detalle_categorias_template = [
        {
            **categoria,
            'saldo_inicial_mes_texto': _formatear_moneda(categoria.get('saldo_inicial_mes')),
            'total_ingresos_texto': _formatear_moneda(categoria.get('total_ingresos')),
            'total_egresos_texto': _formatear_moneda(categoria.get('total_egresos')),
            'saldo_final_texto': _formatear_moneda(categoria.get('saldo_final')),
            'filas_template': [_normalizar_fila_para_template(fila) for fila in (categoria.get('filas') or [])],
        }
        for categoria in detalle_categorias
    ]

    categorias_destacadas = _obtener_categorias_destacadas_dia(sucursal.id, fecha_objetivo)
    total_movimientos = MovimientoDiario.objects.filter(
        reporte__sucursal_id=sucursal.id,
        reporte__fecha_contable__range=(fecha_inicio_mes, fecha_objetivo),
        eliminado_en__isnull=True,
    ).count()

    contexto = {
        'marca_nombre': NOMBRE_MARCA,
        'url_sistema': URL_SISTEMA,
        'sucursal_nombre': sucursal.nombre,
        'periodo_contable_texto': periodo_contable_texto,
        'fecha_envio_texto': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
        'saldo_inicial_texto': _formatear_moneda(resumen.get('saldo_inicial')),
        'ingresos_texto': _formatear_moneda(resumen.get('total_ingresos')),
        'egresos_texto': _formatear_moneda(resumen.get('total_egresos')),
        'saldo_final_texto': _formatear_moneda(resumen.get('saldo_final')),
        'dias_consultados': int(resumen.get('dias_consultados') or 0),
        'dias_con_reporte': int(resumen.get('dias_con_reporte') or 0),
        'total_movimientos': int(total_movimientos),
        'categorias_destacadas': categorias_destacadas,
        'filas_libro': filas_template,
        'bancos_informativos': bancos_template,
        'detalle_categorias': detalle_categorias_template,
    }

    cuerpo_html = render_to_string('reportes_diarios/correos/resumen_diario_ejecutivo.html', contexto)
    cuerpo_texto = render_to_string('reportes_diarios/correos/resumen_diario_ejecutivo.txt', contexto)

    sucursal_slug = slugify(sucursal.nombre or f'sucursal_{sucursal.id}') or f'sucursal_{sucursal.id}'
    fecha_slug = fecha_objetivo.strftime('%Y%m%d')
    marca_tiempo_archivo = _generar_marca_tiempo_archivo()

    adjuntos = [
        {
            'nombre': f"reporte_diario_{sucursal_slug}_{fecha_slug}_{marca_tiempo_archivo}.xlsx",
            'contenido': generar_excel_libro_operativo(datos_libro),
            'mime': MIME_EXCEL,
        },
        {
            'nombre': f"reporte_diario_{sucursal_slug}_{fecha_slug}_{marca_tiempo_archivo}.pdf",
            'contenido': generar_pdf_libro_operativo(datos_libro),
            'mime': MIME_PDF,
        },
    ]

    asunto = f"[{NOMBRE_MARCA}] Reporte de cierre día contable {_formatear_fecha(fecha_objetivo)} (acumulado del mes)"

    return {
        'tipo': 'diario',
        'sucursal_id': sucursal.id,
        'sucursal_nombre': sucursal.nombre,
        'periodo': f"{fecha_inicio_mes.isoformat()}_al_{fecha_objetivo.isoformat()}",
        'marca_tiempo_archivo': marca_tiempo_archivo,
        'asunto': asunto,
        'texto': cuerpo_texto,
        'html': cuerpo_html,
        'adjuntos': adjuntos,
    }


# 1) Para que sirve: obtener rubros principales para destacar en resumen mensual ejecutivo.
# 2) Como funciona: ordena por magnitud neta y devuelve un subconjunto legible.
# 3) Que hace: enfoca la lectura de direccion en los rubros mas relevantes.
# 4) Como editarla: cambia criterio a ingresos o egresos segun criterio financiero.
def _obtener_rubros_destacados(datos_mensuales, limite=8):
    rubros = list(datos_mensuales.get('por_rubro') or [])
    rubros_ordenados = sorted(
        rubros,
        key=lambda item: abs(_a_flotante(item.get('resultado_neto'))),
        reverse=True,
    )

    respuesta = []
    for rubro in rubros_ordenados[: max(1, int(limite))]:
        respuesta.append({
            'rubro_padre': rubro.get('rubro_padre') or 'SIN GRUPO',
            'rubro_nombre': rubro.get('rubro_nombre') or 'SIN RUBRO CONTABLE',
            'ingresos_texto': _formatear_moneda(rubro.get('total_ingresos')),
            'egresos_texto': _formatear_moneda(rubro.get('total_egresos')),
            'neto_texto': _formatear_moneda(rubro.get('resultado_neto')),
            'considerado': bool(rubro.get('rubro_padre_considerar_en_estado_resultados', False)),
        })

    return respuesta


# 1) Para que sirve: crear el paquete completo del correo de cierre mensual por casino.
# 2) Como funciona: arma contexto y adjuntos del mes objetivo (por defecto mes anterior).
# 3) Que hace: deja listo el envio del resumen ejecutivo del cierre mensual.
# 4) Como editarla: agrega comparativos intermensuales cuando se habiliten KPIs extra.
def construir_paquete_correo_cierre_mensual_ejecutivo(sucursal, anio=None, mes=None):
    if isinstance(sucursal, int):
        sucursal = Sucursal.objects.filter(id=sucursal).first()
    if not sucursal:
        raise ValueError('Sucursal invalida para construir el cierre mensual ejecutivo.')

    if anio is None or mes is None:
        anio, mes = obtener_periodo_mes_anterior()

    datos_mensuales = construir_datos_estado_resultados_mensual(
        sucursal_id=sucursal.id,
        anio=int(anio),
        mes=int(mes),
    )

    rubros_destacados = _obtener_rubros_destacados(datos_mensuales)
    periodo_texto = f"{_nombre_mes(int(mes)).capitalize()} {int(anio)}"

    contexto = {
        'marca_nombre': NOMBRE_MARCA,
        'url_sistema': URL_SISTEMA,
        'sucursal_nombre': sucursal.nombre,
        'periodo_texto': periodo_texto,
        'fuente': str(datos_mensuales.get('fuente') or 'tiempo_real'),
        'fecha_envio_texto': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
        'saldo_inicio_texto': _formatear_moneda(datos_mensuales.get('saldo_arrastre_inicio')),
        'ingresos_texto': _formatear_moneda(datos_mensuales.get('total_ingresos')),
        'egresos_texto': _formatear_moneda(datos_mensuales.get('total_egresos')),
        'neto_texto': _formatear_moneda(datos_mensuales.get('resultado_neto')),
        'saldo_fin_texto': _formatear_moneda(datos_mensuales.get('saldo_arrastre_fin')),
        'ingresos_no_considerados_texto': _formatear_moneda(datos_mensuales.get('total_ingresos_no_considerados')),
        'egresos_no_considerados_texto': _formatear_moneda(datos_mensuales.get('total_egresos_no_considerados')),
        'neto_no_considerado_texto': _formatear_moneda(datos_mensuales.get('resultado_neto_no_considerado')),
        'movimientos_mes': int(datos_mensuales.get('movimientos') or 0),
        'rubros_destacados': rubros_destacados,
    }

    cuerpo_html = render_to_string('reportes_diarios/correos/cierre_mensual_ejecutivo.html', contexto)
    cuerpo_texto = render_to_string('reportes_diarios/correos/cierre_mensual_ejecutivo.txt', contexto)

    sucursal_slug = slugify(sucursal.nombre or f'sucursal_{sucursal.id}') or f'sucursal_{sucursal.id}'
    periodo_slug = f"{int(anio)}{int(mes):02d}"
    marca_tiempo_archivo = _generar_marca_tiempo_archivo()

    adjuntos = [
        {
            'nombre': f"cierre_mensual_{sucursal_slug}_{periodo_slug}_{marca_tiempo_archivo}.xlsx",
            'contenido': generar_excel_cierre_mensual(datos_mensuales),
            'mime': MIME_EXCEL,
        },
        {
            'nombre': f"cierre_mensual_{sucursal_slug}_{periodo_slug}_{marca_tiempo_archivo}.pdf",
            'contenido': generar_pdf_cierre_mensual(datos_mensuales),
            'mime': MIME_PDF,
        },
    ]

    asunto = f"[{NOMBRE_MARCA}] Reporte de cierre mes {periodo_texto}"

    return {
        'tipo': 'mensual',
        'sucursal_id': sucursal.id,
        'sucursal_nombre': sucursal.nombre,
        'periodo': f"{int(anio)}-{int(mes):02d}",
        'marca_tiempo_archivo': marca_tiempo_archivo,
        'asunto': asunto,
        'texto': cuerpo_texto,
        'html': cuerpo_html,
        'adjuntos': adjuntos,
    }


# 1) Para que sirve: enviar un paquete de correo preconstruido con adjuntos.
# 2) Como funciona: compone EmailMultiAlternatives y reutiliza conexion opcional.
# 3) Que hace: desacopla generacion de contenido y paso de transporte SMTP.
# 4) Como editarla: agrega CC/CCO o cabeceras cuando el proceso lo requiera.
def enviar_paquete_correo(paquete_correo, destinatarios, conexion=None):
    lista_destinatarios = normalizar_destinatarios(destinatarios)
    if not lista_destinatarios:
        raise ValueError('Se requiere al menos un destinatario valido para enviar el correo.')

    conexion_correo = conexion or get_connection(fail_silently=False)

    mensaje = EmailMultiAlternatives(
        subject=paquete_correo.get('asunto') or f'[{NOMBRE_MARCA}] Notificacion',
        body=paquete_correo.get('texto') or '',
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=lista_destinatarios,
        connection=conexion_correo,
    )

    cuerpo_html = paquete_correo.get('html')
    if cuerpo_html:
        mensaje.attach_alternative(cuerpo_html, 'text/html')

    for adjunto in paquete_correo.get('adjuntos') or []:
        mensaje.attach(
            filename=str(adjunto.get('nombre') or 'adjunto.bin'),
            content=adjunto.get('contenido') or b'',
            mimetype=str(adjunto.get('mime') or 'application/octet-stream'),
        )

    enviados = conexion_correo.send_messages([mensaje]) or 0
    return {
        'enviados': int(enviados),
        'destinatarios': lista_destinatarios,
        'asunto': paquete_correo.get('asunto') or '',
    }


# 1) Para que sirve: resolver sucursales objetivo para ejecuciones manuales de resumen.
# 2) Como funciona: filtra por ids opcionales y estado activo/no eliminado.
# 3) Que hace: evita enviar reportes de sucursales inexistentes o inactivas.
# 4) Como editarla: incorpora validaciones por rol cuando se exponga via endpoint.
def obtener_sucursales_objetivo(sucursal_ids=None):
    consulta = Sucursal.objects.filter(eliminado_en__isnull=True, estado=Sucursal.Estado.ACTIVO)
    if sucursal_ids:
        consulta = consulta.filter(id__in=list(sucursal_ids))
    return list(consulta.order_by('nombre'))
