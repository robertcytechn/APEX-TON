from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from categoria_operativa.models import CategoriaOperativa
from configuraciones_globales.models import ConfiguracionGlobal, RubroContable
from libro_estado_resultados.models import LibroEstadoResultados
from reportes_diarios.models import MovimientoDiario, ReporteDiario
from reportes_diarios.views import _dia_contable_actual, _obtener_o_crear_reporte_del_dia
from sucursales.models import Sucursal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
# 2) Como funciona: replica reglas del endpoint libro-operativo para calculo de saldos.
# 3) Que hace: provee insumo unico para correo diario y adjuntos Excel/PDF.
# 4) Como editarla: mantener en sincronia con la logica del endpoint de reportes diarios.
def construir_datos_libro_operativo(sucursal_id, fecha_inicio, fecha_fin, crear_si_falta=True):
    sucursal = Sucursal.objects.filter(id=sucursal_id).first()
    if not sucursal:
        raise ValueError('No existe la sucursal solicitada para generar el resumen diario.')

    reportes_qs = ReporteDiario.objects.filter(
        sucursal_id=sucursal_id,
        fecha_contable__range=(fecha_inicio, fecha_fin),
    ).order_by('fecha_contable')

    if crear_si_falta and fecha_inicio == fecha_fin and not reportes_qs.exists():
        reporte_hoy, _ = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_inicio)
        reportes_qs = ReporteDiario.objects.filter(pk=reporte_hoy.pk)

    reportes = list(reportes_qs)
    reportes_por_fecha = {reporte.fecha_contable: reporte for reporte in reportes}
    ids_reportes = [reporte.id for reporte in reportes]

    movimientos = list(
        MovimientoDiario.objects.filter(
            reporte_id__in=ids_reportes,
            eliminado_en__isnull=True,
        ).select_related('reporte', 'concepto__categoria')
    )

    resumen_por_categoria = defaultdict(lambda: {'ingreso': Decimal('0'), 'egreso': Decimal('0')})
    totales_por_fecha = defaultdict(lambda: {'ingreso': Decimal('0'), 'egreso': Decimal('0')})

    categorias_consulta = list(
        CategoriaOperativa.objects.filter(eliminado_en__isnull=True)
        .order_by('orden', 'nombre')
        .values('id', 'clave', 'nombre', 'orden')
    )
    categorias_por_id = {categoria['id']: categoria for categoria in categorias_consulta}

    for movimiento in movimientos:
        categoria = getattr(getattr(movimiento, 'concepto', None), 'categoria', None)
        if categoria and categoria.id not in categorias_por_id:
            registro_categoria = {
                'id': categoria.id,
                'clave': categoria.clave,
                'nombre': categoria.nombre,
                'orden': categoria.orden,
            }
            categorias_consulta.append(registro_categoria)
            categorias_por_id[categoria.id] = registro_categoria

    categorias_consulta.sort(key=lambda categoria: (categoria.get('orden') or 0, categoria.get('nombre') or ''))

    for movimiento in movimientos:
        categoria = getattr(getattr(movimiento, 'concepto', None), 'categoria', None)
        if not categoria:
            continue

        fecha_movimiento = movimiento.reporte.fecha_contable
        monto_movimiento = _a_decimal(movimiento.monto)
        tipo_movimiento = str(getattr(movimiento.concepto, 'tipo', '') or '').upper()

        if tipo_movimiento == 'INGRESO':
            resumen_por_categoria[categoria.id]['ingreso'] += monto_movimiento
            totales_por_fecha[fecha_movimiento]['ingreso'] += monto_movimiento
        else:
            resumen_por_categoria[categoria.id]['egreso'] += monto_movimiento
            totales_por_fecha[fecha_movimiento]['egreso'] += monto_movimiento

    reporte_previo = ReporteDiario.objects.filter(
        sucursal_id=sucursal_id,
        fecha_contable__lt=fecha_inicio,
    ).order_by('-fecha_contable').first()

    saldo_arrastre_actual = Decimal('0')
    if reporte_previo:
        if reporte_previo.estado_reporte == ReporteDiario.EstadoReporte.ABIERTO:
            movimientos_previos = reporte_previo.movimientos.filter(eliminado_en__isnull=True)
            ingresos_previos = _a_decimal(movimientos_previos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'])
            egresos_previos = _a_decimal(movimientos_previos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'])
            saldo_arrastre_actual = _a_decimal(reporte_previo.saldo_arrastre_inicio) + ingresos_previos - egresos_previos
        else:
            saldo_arrastre_actual = _a_decimal(reporte_previo.saldo_arrastre_fin)

    saldo_inicial_rango = saldo_arrastre_actual
    total_ingresos_rango = Decimal('0')
    total_egresos_rango = Decimal('0')
    dias_con_reporte = 0

    fecha_cursor = fecha_inicio
    while fecha_cursor <= fecha_fin:
        reporte_dia = reportes_por_fecha.get(fecha_cursor)
        if reporte_dia:
            dias_con_reporte += 1

        saldo_inicial_dia = saldo_arrastre_actual
        ingreso_dia = _a_decimal(totales_por_fecha[fecha_cursor]['ingreso'])
        egreso_dia = _a_decimal(totales_por_fecha[fecha_cursor]['egreso'])
        neto_dia = ingreso_dia - egreso_dia

        if reporte_dia and reporte_dia.estado_reporte == ReporteDiario.EstadoReporte.ABIERTO:
            saldo_fin_dia = saldo_inicial_dia + neto_dia
            requiere_actualizacion = any([
                _a_decimal(reporte_dia.saldo_arrastre_inicio) != saldo_inicial_dia,
                _a_decimal(reporte_dia.total_ingresos) != ingreso_dia,
                _a_decimal(reporte_dia.total_egresos) != egreso_dia,
                _a_decimal(reporte_dia.resultado_neto) != neto_dia,
                _a_decimal(reporte_dia.saldo_arrastre_fin) != saldo_fin_dia,
            ])
            if requiere_actualizacion:
                reporte_dia.saldo_arrastre_inicio = saldo_inicial_dia
                reporte_dia.total_ingresos = ingreso_dia
                reporte_dia.total_egresos = egreso_dia
                reporte_dia.resultado_neto = neto_dia
                reporte_dia.saldo_arrastre_fin = saldo_fin_dia
                reporte_dia.save()

        total_ingresos_rango += ingreso_dia
        total_egresos_rango += egreso_dia
        fecha_cursor += timedelta(days=1)

    filas = []
    saldo_acumulado = saldo_inicial_rango

    filas.append({
        'partida': 'SALDO',
        'concepto': 'SALDO INICIAL',
        'ingreso': None,
        'egreso': None,
        'saldo': _a_flotante(saldo_acumulado),
        'tipo_fila': 'SALDO_INICIAL',
    })

    for categoria in categorias_consulta:
        resumen_categoria = resumen_por_categoria.get(categoria['id']) or {'ingreso': Decimal('0'), 'egreso': Decimal('0')}
        ingreso_categoria = _a_decimal(resumen_categoria['ingreso'])
        egreso_categoria = _a_decimal(resumen_categoria['egreso'])
        saldo_acumulado = saldo_acumulado + ingreso_categoria - egreso_categoria

        filas.append({
            'partida': categoria.get('clave') or 'CATEGORIA',
            'concepto': categoria.get('nombre') or 'SIN CATEGORIA',
            'ingreso': _a_flotante(ingreso_categoria) if ingreso_categoria > 0 else None,
            'egreso': _a_flotante(egreso_categoria) if egreso_categoria > 0 else None,
            'saldo': _a_flotante(saldo_acumulado),
            'tipo_fila': 'CATEGORIA_RESUMEN',
        })

    filas.append({
        'partida': 'TOTAL',
        'concepto': 'TOTAL DEL PERIODO',
        'ingreso': _a_flotante(total_ingresos_rango),
        'egreso': _a_flotante(total_egresos_rango),
        'saldo': _a_flotante(saldo_acumulado),
        'tipo_fila': 'TOTAL_PERIODO',
    })

    filas.append({
        'partida': 'EFECTIVO',
        'concepto': 'EFECTIVO FISICO ESPERADO EN SALA',
        'ingreso': None,
        'egreso': None,
        'saldo': _a_flotante(saldo_acumulado),
        'tipo_fila': 'EFECTIVO_FISICO',
    })

    resumen = {
        'saldo_inicial': _a_flotante(saldo_inicial_rango),
        'total_ingresos': _a_flotante(total_ingresos_rango),
        'total_egresos': _a_flotante(total_egresos_rango),
        'saldo_final': _a_flotante(saldo_acumulado),
        'dias_consultados': int((fecha_fin - fecha_inicio).days) + 1,
        'dias_con_reporte': dias_con_reporte,
    }

    return {
        'sucursal': {
            'id': sucursal.id,
            'nombre': sucursal.nombre,
        },
        'filtro_aplicado': {
            'sucursal_id': sucursal_id,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'filtro_forzado': bool(fecha_inicio == fecha_fin),
        },
        'resumen': resumen,
        'filas': filas,
    }


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


# 1) Para que sirve: construir adjunto Excel del libro operativo diario completo.
# 2) Como funciona: crea hojas Resumen y Libro_Operativo con formato monetario.
# 3) Que hace: entrega archivo compatible con Microsoft Excel para auditoria.
# 4) Como editarla: agrega columnas nuevas en hoja detalle cuando crezca el reporte.
def generar_excel_libro_operativo(datos_libro):
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = 'Resumen'

    resumen = datos_libro.get('resumen', {})
    sucursal_nombre = (datos_libro.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    fecha_exportacion = timezone.localtime(timezone.now())
    filtro = datos_libro.get('filtro_aplicado') or {}

    periodo = _formatear_fecha(date.fromisoformat(filtro.get('fecha_inicio'))) if filtro.get('fecha_inicio') else '-'
    if filtro.get('fecha_inicio') and filtro.get('fecha_fin') and filtro.get('fecha_inicio') != filtro.get('fecha_fin'):
        periodo = f"{_formatear_fecha(date.fromisoformat(filtro.get('fecha_inicio')))} al {_formatear_fecha(date.fromisoformat(filtro.get('fecha_fin')))}"

    filas_resumen = [
        ['Reporte diario operativo', ''],
        ['Fecha de exportacion', fecha_exportacion.strftime('%d/%m/%Y %H:%M:%S')],
        ['Casino', sucursal_nombre],
        ['Periodo', periodo],
        ['', ''],
        ['Indicador', 'Valor'],
        ['Saldo inicial del rango', _a_flotante(resumen.get('saldo_inicial'))],
        ['Total ingresos', _a_flotante(resumen.get('total_ingresos'))],
        ['Total egresos', _a_flotante(resumen.get('total_egresos'))],
        ['Saldo final', _a_flotante(resumen.get('saldo_final'))],
        ['Dias consultados', int(resumen.get('dias_consultados') or 0)],
        ['Dias con reporte', int(resumen.get('dias_con_reporte') or 0)],
    ]

    for fila in filas_resumen:
        hoja_resumen.append(fila)

    hoja_resumen['A1'].font = Font(name='Calibri', size=14, bold=True, color='0F172A')
    _estilizar_encabezado_excel(hoja_resumen['A6'])
    _estilizar_encabezado_excel(hoja_resumen['B6'])

    for indice_fila in (7, 8, 9, 10):
        hoja_resumen[f'B{indice_fila}'].number_format = '#,##0.00'

    hoja_resumen.column_dimensions['A'].width = 36
    hoja_resumen.column_dimensions['B'].width = 24

    hoja_libro = libro.create_sheet('Libro_Operativo')
    encabezados = ['Partida', 'Concepto', 'Ingreso', 'Egreso', 'Saldo', 'Tipo_fila']
    hoja_libro.append(encabezados)

    for columna in range(1, len(encabezados) + 1):
        _estilizar_encabezado_excel(hoja_libro.cell(row=1, column=columna))

    colores_tipo_fila = {
        'SALDO_INICIAL': 'E0F2FE',
        'TOTAL_PERIODO': 'FDE68A',
        'EFECTIVO_FISICO': 'A7F3D0',
    }

    for indice, fila in enumerate(datos_libro.get('filas') or [], start=2):
        hoja_libro.append([
            str(fila.get('partida') or ''),
            str(fila.get('concepto') or ''),
            _a_flotante(fila.get('ingreso')) if fila.get('ingreso') is not None else None,
            _a_flotante(fila.get('egreso')) if fila.get('egreso') is not None else None,
            _a_flotante(fila.get('saldo')),
            str(fila.get('tipo_fila') or ''),
        ])

        for columna in (3, 4, 5):
            hoja_libro.cell(row=indice, column=columna).number_format = '#,##0.00'
            hoja_libro.cell(row=indice, column=columna).alignment = Alignment(horizontal='right', vertical='center')

        color_fondo = colores_tipo_fila.get(str(fila.get('tipo_fila') or ''))
        if color_fondo:
            for columna in range(1, 7):
                hoja_libro.cell(row=indice, column=columna).fill = PatternFill(fill_type='solid', fgColor=color_fondo)
                hoja_libro.cell(row=indice, column=columna).font = Font(name='Calibri', size=10, bold=True, color='111827')

    hoja_libro.column_dimensions['A'].width = 18
    hoja_libro.column_dimensions['B'].width = 46
    hoja_libro.column_dimensions['C'].width = 18
    hoja_libro.column_dimensions['D'].width = 18
    hoja_libro.column_dimensions['E'].width = 18
    hoja_libro.column_dimensions['F'].width = 22

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# 1) Para que sirve: construir adjunto PDF del libro operativo diario completo.
# 2) Como funciona: dibuja resumen y tabla detallada con estilos por tipo de fila.
# 3) Que hace: permite revision formal del reporte sin depender del frontend.
# 4) Como editarla: ajusta anchos de columna si cambian campos o tamano de letra.
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

    estilos = getSampleStyleSheet()
    elementos = []

    sucursal_nombre = (datos_libro.get('sucursal') or {}).get('nombre') or 'SIN SUCURSAL'
    filtro = datos_libro.get('filtro_aplicado') or {}
    resumen = datos_libro.get('resumen') or {}

    fecha_inicio = date.fromisoformat(filtro.get('fecha_inicio')) if filtro.get('fecha_inicio') else None
    fecha_fin = date.fromisoformat(filtro.get('fecha_fin')) if filtro.get('fecha_fin') else None

    periodo_texto = _formatear_fecha(fecha_inicio) if fecha_inicio else '-'
    if fecha_inicio and fecha_fin and fecha_inicio != fecha_fin:
        periodo_texto = f"{_formatear_fecha(fecha_inicio)} al {_formatear_fecha(fecha_fin)}"

    elementos.append(Paragraph('Reporte Diario Operativo', estilos['Heading2']))
    elementos.append(Paragraph(f"Casino: {sucursal_nombre}", estilos['BodyText']))
    elementos.append(Paragraph(f"Periodo: {periodo_texto}", estilos['BodyText']))
    elementos.append(Paragraph(f"Fecha de exportacion: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')}", estilos['BodyText']))
    elementos.append(Spacer(1, 10))

    tabla_resumen_datos = [
        ['Indicador', 'Valor'],
        ['Saldo inicial del rango', _formatear_moneda(resumen.get('saldo_inicial'))],
        ['Total ingresos', _formatear_moneda(resumen.get('total_ingresos'))],
        ['Total egresos', _formatear_moneda(resumen.get('total_egresos'))],
        ['Saldo final', _formatear_moneda(resumen.get('saldo_final'))],
        ['Dias consultados', str(int(resumen.get('dias_consultados') or 0))],
        ['Dias con reporte', str(int(resumen.get('dias_con_reporte') or 0))],
    ]

    tabla_resumen = Table(tabla_resumen_datos, colWidths=[220, 160], repeatRows=1)
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ]))

    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 12))

    filas_detalle = [['Partida', 'Concepto', 'Ingreso', 'Egreso', 'Saldo']]
    tipos_fila = []
    for fila in datos_libro.get('filas') or []:
        filas_detalle.append([
            str(fila.get('partida') or ''),
            str(fila.get('concepto') or ''),
            _formatear_moneda(fila.get('ingreso')) if fila.get('ingreso') is not None else '-',
            _formatear_moneda(fila.get('egreso')) if fila.get('egreso') is not None else '-',
            _formatear_moneda(fila.get('saldo')),
        ])
        tipos_fila.append(str(fila.get('tipo_fila') or ''))

    tabla_detalle = Table(filas_detalle, colWidths=[60, 200, 88, 88, 88], repeatRows=1)
    estilo_detalle = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    colores_tipo_fila = {
        'SALDO_INICIAL': colors.HexColor('#E0F2FE'),
        'TOTAL_PERIODO': colors.HexColor('#FDE68A'),
        'EFECTIVO_FISICO': colors.HexColor('#A7F3D0'),
    }

    for indice_tabla, tipo_fila in enumerate(tipos_fila, start=1):
        color = colores_tipo_fila.get(tipo_fila)
        if color is None:
            continue
        estilo_detalle.add('BACKGROUND', (0, indice_tabla), (-1, indice_tabla), color)
        estilo_detalle.add('FONTNAME', (0, indice_tabla), (-1, indice_tabla), 'Helvetica-Bold')

    tabla_detalle.setStyle(estilo_detalle)
    elementos.append(tabla_detalle)

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

    datos_libro = construir_datos_libro_operativo(
        sucursal_id=sucursal.id,
        fecha_inicio=fecha_objetivo,
        fecha_fin=fecha_objetivo,
        crear_si_falta=True,
    )

    resumen = datos_libro.get('resumen') or {}
    categorias_destacadas = _obtener_categorias_destacadas_dia(sucursal.id, fecha_objetivo)
    total_movimientos = MovimientoDiario.objects.filter(
        reporte__sucursal_id=sucursal.id,
        reporte__fecha_contable=fecha_objetivo,
        eliminado_en__isnull=True,
    ).count()

    contexto = {
        'marca_nombre': NOMBRE_MARCA,
        'url_sistema': URL_SISTEMA,
        'sucursal_nombre': sucursal.nombre,
        'fecha_contable_texto': _formatear_fecha(fecha_objetivo),
        'fecha_envio_texto': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
        'saldo_inicial_texto': _formatear_moneda(resumen.get('saldo_inicial')),
        'ingresos_texto': _formatear_moneda(resumen.get('total_ingresos')),
        'egresos_texto': _formatear_moneda(resumen.get('total_egresos')),
        'saldo_final_texto': _formatear_moneda(resumen.get('saldo_final')),
        'dias_consultados': int(resumen.get('dias_consultados') or 0),
        'dias_con_reporte': int(resumen.get('dias_con_reporte') or 0),
        'total_movimientos': int(total_movimientos),
        'categorias_destacadas': categorias_destacadas,
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

    asunto = f"[{NOMBRE_MARCA}] Reporte de cierre día contable {_formatear_fecha(fecha_objetivo)}"

    return {
        'tipo': 'diario',
        'sucursal_id': sucursal.id,
        'sucursal_nombre': sucursal.nombre,
        'periodo': fecha_objetivo.isoformat(),
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
