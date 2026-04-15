import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from categoria_operativa.models import Concepto, CategoriaOperativa
from core.permisos import VentanaHorariaPermiso, EsAdministrador
from .models import ReporteDiario, MovimientoDiario
from .serializers import (
    ReporteDiarioSerializer, ReporteDiarioListSerializer,
    MovimientoDiarioSerializer, MovimientoDiarioListSerializer,
)
from sucursales.models import Sucursal


# 1) Para qué sirve: homologar la estructura JSON de salida de este módulo.
# 2) Cómo funciona: encapsula datos, mensaje, estado y código HTTP en un Response DRF.
# 3) Qué hace: evita respuestas inconsistentes entre endpoints del mismo ViewSet.
# 4) Cómo editarla: si cambia el contrato API global, ajusta este helper y propaga el mismo patrón.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: calcular el día contable oficial conforme a regla T-1 del negocio.
# 2) Cómo funciona: usa la zona horaria del servidor y resta un día a la fecha local.
# 3) Qué hace: devuelve la fecha que se usa para abrir/cerrar reportes y registrar movimientos.
# 4) Cómo editarla: si el negocio cambia la regla de día contable, modifica esta función central.
def _dia_contable_actual():
    """
    Retorna la fecha contable correcta: siempre el día anterior (T-1) a la fecha
    del servidor en la zona horaria configurada.
    El backend NO acepta la fecha del frontend; la calcula internamente.
    """
    return timezone.localdate() - timezone.timedelta(days=1)


# 1) Para qué sirve: parsear la fecha contable enviada por query/body en formato ISO.
# 2) Cómo funciona: intenta convertir texto YYYY-MM-DD a objeto date y valida vacíos.
# 3) Qué hace: estandariza la lectura de fecha_contable para endpoints de captura/calendario.
# 4) Cómo editarla: ajusta el formato permitido aquí si negocio habilita otros formatos de entrada.
def _parsear_fecha_contable(valor_fecha):
    if valor_fecha in (None, ''):
        return None

    if hasattr(valor_fecha, 'year') and hasattr(valor_fecha, 'month') and hasattr(valor_fecha, 'day'):
        return valor_fecha

    try:
        return datetime.strptime(str(valor_fecha), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError("La fecha_contable debe estar en formato YYYY-MM-DD.")


# 1) Para qué sirve: determinar si una fecha contable excede el límite operativo de captura.
# 2) Cómo funciona: compara contra el día contable actual menos 5 días naturales.
# 3) Qué hace: devuelve True cuando el día queda bloqueado por antigüedad.
# 4) Cómo editarla: ajusta los días de tolerancia si cambia la regla de negocio.
def _fecha_contable_bloqueada_por_antiguedad(fecha_contable):
    limite_minimo = _dia_contable_actual() - timedelta(days=5)
    return fecha_contable < limite_minimo


# 1) Para qué sirve: validar autorización de cierre según roles permitidos de negocio.
# 2) Cómo funciona: consulta relación usuario-rol y también permite superusuario/staff.
# 3) Qué hace: limita cierre de día a CONTADOR, GERENTE y ADMINISTRADOR.
# 4) Cómo editarla: agrega o remueve roles de la lista según reglas futuras.
def _usuario_puede_cerrar_dia(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser or usuario.is_staff:
        return True

    try:
        return usuario.usuario_roles.filter(
            rol__nombre__in=['CONTADOR', 'GERENTE', 'ADMINISTRADOR']
        ).exists()
    except Exception:
        return False


# 1) Para qué sirve: validar pertenencia de un usuario a un conjunto de roles nominales.
# 2) Cómo funciona: consulta usuario_roles con comparación case-sensitive por negocio.
# 3) Qué hace: permite reutilizar reglas de autorización sin duplicar lógica en endpoints.
# 4) Cómo editarla: cambia a iregex/iexact si se necesita tolerancia adicional de nombre.
def _usuario_tiene_roles(usuario, roles_permitidos):
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser or usuario.is_staff:
        return True
    try:
        return usuario.usuario_roles.filter(rol__nombre__in=roles_permitidos).exists()
    except Exception:
        return False


# 1) Para qué sirve: identificar perfiles directivos con capacidad de consulta avanzada.
# 2) Cómo funciona: delega validación a helper de roles y privilegios globales.
# 3) Qué hace: habilita filtros por rango de fechas en reportes diarios.
# 4) Cómo editarla: agrega roles de lectura ejecutiva cuando negocio lo solicite.
def _usuario_es_directivo(usuario):
    return _usuario_tiene_roles(usuario, ['DIRECTOR', 'ADMINISTRADOR'])


# 1) Para qué sirve: identificar perfiles operativos que solo consultan día contable actual.
# 2) Cómo funciona: valida roles CONTADOR/GERENTE y excluye directivos con acceso amplio.
# 3) Qué hace: fuerza filtros a día actual y sucursal asignada para evitar sobreexposición.
# 4) Cómo editarla: agrega roles equivalentes si se crea una nueva jerarquía operativa.
def _usuario_es_operativo(usuario):
    return _usuario_tiene_roles(usuario, ['CONTADOR', 'GERENTE']) and not _usuario_es_directivo(usuario)


# 1) Para qué sirve: convertir valores monetarios a Decimal seguro para cálculos de arrastre.
# 2) Cómo funciona: intenta cast a string+Decimal y retorna 0 ante errores de formato.
# 3) Qué hace: evita fallas por None o cadenas inválidas en sumas contables.
# 4) Cómo editarla: agrega quantize si negocio exige redondeo estricto en todos los pasos.
def _a_decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


# 1) Para qué sirve: serializar Decimal a float en payload JSON del libro diario.
# 2) Cómo funciona: aplica cast seguro con fallback en 0.0.
# 3) Qué hace: simplifica consumo en frontend para celdas monetarias y cálculos visuales.
# 4) Cómo editarla: cambia a string si se requiere precisión textual exacta en cliente.
def _a_flotante(valor):
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


# 1) Para qué sirve: resolver filtros efectivos de consulta según rol y parámetros enviados.
# 2) Cómo funciona: fuerza día/sucursal en operativos y permite rango en perfiles directivos.
# 3) Qué hace: unifica reglas de visibilidad para listados y libro operativo.
# 4) Cómo editarla: ajusta límites de rango o parámetros admitidos si cambia el UX de filtros.
def _resolver_filtros_consulta_reportes(request):
    usuario = request.user
    dia_actual = _dia_contable_actual()

    es_directivo = _usuario_es_directivo(usuario)
    es_operativo = _usuario_es_operativo(usuario)

    if not es_directivo and not es_operativo:
        raise PermissionError('No tienes permisos para consultar reporte diario.')

    if es_operativo:
        sucursal_usuario = getattr(usuario, 'sucursal_id', None)
        if not sucursal_usuario:
            raise ValueError('Tu usuario no tiene una sucursal asignada para consultar el reporte diario.')
        return {
            'sucursal_id': int(sucursal_usuario),
            'fecha_inicio': dia_actual,
            'fecha_fin': dia_actual,
            'filtro_forzado': True,
        }

    sucursal_cruda = request.query_params.get('sucursal_id') or getattr(usuario, 'sucursal_id', None)
    if not sucursal_cruda:
        raise ValueError("El parámetro 'sucursal_id' es obligatorio para la consulta.")

    try:
        sucursal_id = int(sucursal_cruda)
        if sucursal_id <= 0:
            raise ValueError('sucursal_id inválido')
    except (TypeError, ValueError):
        raise ValueError("El parámetro 'sucursal_id' debe ser un entero válido.")

    fecha_inicio_txt = request.query_params.get('fecha_inicio') or request.query_params.get('fecha_desde')
    fecha_fin_txt = request.query_params.get('fecha_fin') or request.query_params.get('fecha_hasta')

    if fecha_inicio_txt or fecha_fin_txt:
        fecha_inicio = _parsear_fecha_contable(fecha_inicio_txt) if fecha_inicio_txt else None
        fecha_fin = _parsear_fecha_contable(fecha_fin_txt) if fecha_fin_txt else None

        if fecha_inicio is None and fecha_fin is None:
            fecha_inicio = dia_actual
            fecha_fin = dia_actual
        elif fecha_inicio is None:
            fecha_inicio = fecha_fin
        elif fecha_fin is None:
            fecha_fin = fecha_inicio
    else:
        anio = request.query_params.get('anio')
        mes = request.query_params.get('mes')
        dia = request.query_params.get('dia')

        if anio not in (None, '') or mes not in (None, '') or dia not in (None, ''):
            if anio in (None, '') or mes in (None, '') or dia in (None, ''):
                raise ValueError("Para usar anio/mes/dia debes enviar los tres parámetros completos.")
            try:
                fecha_unica = datetime(int(anio), int(mes), int(dia)).date()
            except ValueError:
                raise ValueError("Los parámetros 'anio', 'mes' y 'dia' deben formar una fecha válida.")
            fecha_inicio = fecha_unica
            fecha_fin = fecha_unica
        else:
            fecha_inicio = dia_actual
            fecha_fin = dia_actual

    if fecha_inicio > fecha_fin:
        raise ValueError("'fecha_inicio' no puede ser mayor que 'fecha_fin'.")

    if fecha_inicio > dia_actual or fecha_fin > dia_actual:
        raise ValueError('No se permite consultar fechas contables futuras.')

    if (fecha_fin - fecha_inicio).days > 62:
        raise ValueError('El rango máximo permitido es de 63 días por consulta.')

    return {
        'sucursal_id': sucursal_id,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'filtro_forzado': False,
    }


# 1) Para qué sirve: cerrar un reporte con cálculo consolidado de ingresos/egresos.
# 2) Cómo funciona: calcula totales en vivo, toma snapshots de tipo de cambio y persiste cierre.
# 3) Qué hace: deja el día contable bloqueado para nuevas modificaciones.
# 4) Cómo editarla: integra nuevas métricas de cierre en este único punto central.
def _cerrar_reporte_diario(reporte, usuario):
    movimientos = reporte.movimientos.filter(eliminado_en__isnull=True)
    ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
    egresos = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
    neto = ingresos - egresos

    try:
        tasa_usd = _obtener_tasa_cambio_por_claves(['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD'])
        tasa_eur = _obtener_tasa_cambio_por_claves(['TIPO_CAMBIO_EUR'])
        if tasa_usd is not None:
            reporte.tipo_cambio_usd_snapshot = tasa_usd
        if tasa_eur is not None:
            reporte.tipo_cambio_eur_snapshot = tasa_eur
    except Exception:
        pass

    reporte.total_ingresos = ingresos
    reporte.total_egresos = egresos
    reporte.resultado_neto = neto
    reporte.saldo_arrastre_fin = reporte.saldo_arrastre_inicio + neto
    reporte.estado_reporte = ReporteDiario.EstadoReporte.CERRADO
    reporte.cerrado_en = timezone.now()
    reporte.cerrado_por = usuario
    reporte.save()

    # Mantener continuidad de arrastre cuando el siguiente día ya existe en estado abierto.
    reporte_siguiente = ReporteDiario.objects.filter(
        sucursal_id=reporte.sucursal_id,
        fecha_contable=reporte.fecha_contable + timedelta(days=1),
        estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
    ).first()
    if reporte_siguiente and reporte_siguiente.saldo_arrastre_inicio != reporte.saldo_arrastre_fin:
        reporte_siguiente.saldo_arrastre_inicio = reporte.saldo_arrastre_fin
        reporte_siguiente.save()

    return reporte


# 1) Para qué sirve: construir un resumen ejecutivo del día contable para tablero rápido.
# 2) Cómo funciona: cruza movimientos capturados contra conceptos recurrentes activos.
# 3) Qué hace: muestra métricas de avance y conceptos faltantes para detectar omisiones.
# 4) Cómo editarla: amplía los campos retornados si se requieren KPIs adicionales.
def _construir_resumen_rapido_reporte(reporte, usuario):
    from categoria_operativa.models import Concepto

    movimientos = reporte.movimientos.filter(eliminado_en__isnull=True).select_related('concepto', 'concepto__categoria')
    ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
    egresos = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
    neto = ingresos - egresos

    conceptos_recurrentes = Concepto.objects.filter(
        estado='ACTIVO',
        es_recurrente=True,
        categoria__estado='ACTIVO'
    )

    conceptos_capturados_ids = movimientos.values_list('concepto_id', flat=True)
    conceptos_faltantes = conceptos_recurrentes.exclude(id__in=conceptos_capturados_ids)
    faltantes_detalle = [
        {
            'id': item['id'],
            'nombre': item['nombre'],
            'tipo': item['tipo'],
            'categoria_id': item['categoria_id'],
            'categoria_nombre': item['categoria__nombre'],
            'categoria_clave': item['categoria__clave'],
        }
        for item in conceptos_faltantes.values(
            'id', 'nombre', 'tipo', 'categoria_id', 'categoria__nombre', 'categoria__clave'
        )[:40]
    ]

    total_recurrentes = conceptos_recurrentes.count()
    total_faltantes = conceptos_faltantes.count()

    return {
        'reporte_id': reporte.id,
        'sucursal_id': reporte.sucursal_id,
        'fecha_contable': reporte.fecha_contable.isoformat(),
        'estado_reporte': reporte.estado_reporte,
        'cerrado_en': timezone.localtime(reporte.cerrado_en).isoformat() if reporte.cerrado_en else None,
        'movimientos_registrados': movimientos.count(),
        'ingresos_capturados': ingresos,
        'egresos_capturados': egresos,
        'resultado_neto_capturado': neto,
        'conceptos_recurrentes_totales': total_recurrentes,
        'conceptos_recurrentes_capturados': max(total_recurrentes - total_faltantes, 0),
        'conceptos_recurrentes_faltantes': total_faltantes,
        'faltantes_recurrentes': faltantes_detalle,
        'puede_cerrar_dia': bool(
            reporte.estado_reporte == ReporteDiario.EstadoReporte.ABIERTO
            and reporte.fecha_contable <= _dia_contable_actual()
            and _usuario_puede_cerrar_dia(usuario)
        ),
    }


# 1) Para qué sirve: obtener una tasa de cambio válida buscando varias claves configurables.
# 2) Cómo funciona: recorre una lista de claves y devuelve el primer valor tipado disponible.
# 3) Qué hace: abstrae fallback de configuración para USD/EUR u otras variantes.
# 4) Cómo editarla: agrega nuevas claves al arreglo de entrada sin tocar lógica de consumo.
def _obtener_tasa_cambio_por_claves(claves):
    from configuraciones_globales.models import ConfiguracionGlobal

    for clave in claves:
        configuracion = ConfiguracionGlobal.objects.filter(clave=clave).first()
        if not configuracion:
            continue
        valor = configuracion.valor_tipado
        if valor not in (None, ''):
            return valor
    return None


# 1) Para qué sirve: asegurar que cada sucursal tenga reporte diario para el día contable.
# 2) Cómo funciona: usa get_or_create con bloqueo transaccional y encadena saldos del reporte previo.
# 3) Qué hace: devuelve el reporte del día y un indicador de creación para flujo de API.
# 4) Cómo editarla: si cambian snapshots o reglas de arrastre, ajusta defaults y cálculo aquí.
def _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_contable=None):
    """
    Obtiene el ReporteDiario del día contable actual (T-1) para la sucursal dada.
    Si no existe, lo crea automáticamente, encadenando el saldo_arrastre_inicio
    desde el saldo_arrastre_fin del reporte anterior.
    """
    fecha = fecha_contable or _dia_contable_actual()

    with transaction.atomic():
        reporte, creado = ReporteDiario.objects.select_for_update().get_or_create(
            sucursal_id=sucursal_id,
            fecha_contable=fecha,
            defaults={'estado_reporte': ReporteDiario.EstadoReporte.ABIERTO}
        )

        # Encadenar saldo de arrastre desde el día anterior con cálculo dinámico.
        anterior = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__lt=fecha,
        ).order_by('-fecha_contable').first()

        saldo_arrastre_esperado = _a_decimal(reporte.saldo_arrastre_inicio)
        if anterior:
            movimientos_anterior = anterior.movimientos.filter(eliminado_en__isnull=True)
            ingresos_anterior = _a_decimal(movimientos_anterior.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'])
            egresos_anterior = _a_decimal(movimientos_anterior.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'])
            saldo_arrastre_esperado = _a_decimal(anterior.saldo_arrastre_inicio) + ingresos_anterior - egresos_anterior

        requiere_guardado = False

        if reporte.saldo_arrastre_inicio != saldo_arrastre_esperado:
            reporte.saldo_arrastre_inicio = saldo_arrastre_esperado
            requiere_guardado = True

        if creado:
            # Snapshot del tipo de cambio actual
            try:
                tasa_usd = _obtener_tasa_cambio_por_claves(['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD'])
                tasa_eur = _obtener_tasa_cambio_por_claves(['TIPO_CAMBIO_EUR'])
                if tasa_usd is not None:
                    reporte.tipo_cambio_usd_snapshot = tasa_usd
                if tasa_eur is not None:
                    reporte.tipo_cambio_eur_snapshot = tasa_eur
            except Exception:
                pass
            requiere_guardado = True

        if requiere_guardado:
            reporte.save()

    return reporte, creado


# 1) Para qué sirve: normalizar texto numérico capturado desde UI con coma/punto mixto.
# 2) Cómo funciona: detecta patrón decimal y transforma a formato interpretable por Decimal.
# 3) Qué hace: previene errores por separadores regionales en monto y monto_divisa.
# 4) Cómo editarla: añade nuevas reglas de parsing si se soportan otros formatos locales.
def _normalizar_texto_decimal(valor):
    if not isinstance(valor, str):
        return valor

    texto = valor.strip()
    if not texto:
        return texto

    if ',' in texto and '.' in texto:
        if texto.rfind(',') > texto.rfind('.'):
            return texto.replace('.', '').replace(',', '.')
        return texto.replace(',', '')

    if ',' in texto:
        return texto.replace('.', '').replace(',', '.')

    return texto


# 1) Para qué sirve: construir payload seguro para serializador de movimientos.
# 2) Cómo funciona: clona request.data, fuerza reporte_id del backend y normaliza campos numéricos/JSON.
# 3) Qué hace: elimina dependencia de datos sensibles enviados por frontend.
# 4) Cómo editarla: agrega aquí cualquier campo nuevo que requiera limpieza previa a validación.
def _construir_datos_movimiento(request, reporte_id):
    datos = request.data.copy()
    datos['reporte'] = reporte_id
    datos.pop('sucursal_id', None)

    if 'monto' in datos:
        datos['monto'] = _normalizar_texto_decimal(datos.get('monto'))
    if 'monto_divisa' in datos:
        datos['monto_divisa'] = _normalizar_texto_decimal(datos.get('monto_divisa'))

    detalles = datos.get('detalles_snapshot')
    if isinstance(detalles, str):
        try:
            detalles_parseados = json.loads(detalles)
        except json.JSONDecodeError:
            detalles_parseados = {}
        datos['detalles_snapshot'] = detalles_parseados if isinstance(detalles_parseados, dict) else {}

    return datos


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTE DIARIO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: exponer API de encabezado del día contable (reporte diario).
# 2) Cómo funciona: combina permisos, filtros, cierres y reaperturas sobre ReporteDiario.
# 3) Qué hace: gobierna ciclo de vida ABIERTO/CERRADO de cada jornada por sucursal.
# 4) Cómo editarla: agrega nuevas acciones de negocio como métodos @action en este ViewSet.
class ReporteDiarioViewSet(viewsets.ViewSet):
    """
    CRUD para ReporteDiario con acciones de cierre y reapertura.

    Permisos:
        - Lectura (GET): solo autenticación.
        - Escritura (POST/PATCH/DELETE): requiere estar DENTRO del horario de operación.
        - Reapertura: exclusivo para ADMINISTRADOR.
                - Cierre: exclusivo para CONTADOR, GERENTE, ADMINISTRADOR o superusuario.
    """

    def get_permissions(self):
        """Aplica VentanaHorariaPermiso a toda operación que modifica estado o datos."""
        acciones_escritura = (
            'create',
            'update',
            'partial_update',
            'destroy',
            'cerrar',
            'cerrar_actual',
            'reabrir',
        )

        if self.action in acciones_escritura:
            if self.action == 'reabrir':
                return [IsAuthenticated(), EsAdministrador(), VentanaHorariaPermiso()]
            return [IsAuthenticated(), VentanaHorariaPermiso()]
        return [IsAuthenticated()]

    def list(self, request):
        try:
            filtros = _resolver_filtros_consulta_reportes(request)
        except PermissionError as error:
            return respuesta_estandar(mensaje=str(error), estado='error', codigo=status.HTTP_403_FORBIDDEN)
        except ValueError as error:
            return respuesta_estandar(mensaje=str(error), estado='error', codigo=status.HTTP_400_BAD_REQUEST)

        qs = ReporteDiario.objects.filter(
            sucursal_id=filtros['sucursal_id'],
            fecha_contable__range=(filtros['fecha_inicio'], filtros['fecha_fin']),
        ).order_by('-fecha_contable')

        return respuesta_estandar(
            data=ReporteDiarioListSerializer(qs, many=True, context={'request': request}).data,
            mensaje="Reportes diarios obtenidos."
        )

    @action(detail=False, methods=['get'], url_path='libro-operativo')
    def libro_operativo(self, request):
        """
        Devuelve el reporte diario en formato tabular por columnas:
        FECHA | PARTIDA | CONCEPTO | INGRESO | EGRESO | SALDO.

        Reglas:
        - CONTADOR/GERENTE: solo día contable actual y sucursal asignada.
        - DIRECTOR/ADMINISTRADOR: puede consultar rango de fechas.
        - El armado usa categorías de base de datos y calcula arrastre secuencial.
        """
        try:
            filtros = _resolver_filtros_consulta_reportes(request)
        except PermissionError as error:
            return respuesta_estandar(mensaje=str(error), estado='error', codigo=status.HTTP_403_FORBIDDEN)
        except ValueError as error:
            return respuesta_estandar(mensaje=str(error), estado='error', codigo=status.HTTP_400_BAD_REQUEST)

        sucursal = Sucursal.objects.filter(id=filtros['sucursal_id']).first()
        if not sucursal:
            return respuesta_estandar(
                mensaje='No existe la sucursal solicitada para esta consulta.',
                estado='error',
                codigo=status.HTTP_404_NOT_FOUND
            )

        fecha_inicio = filtros['fecha_inicio']
        fecha_fin = filtros['fecha_fin']

        reportes_qs = ReporteDiario.objects.filter(
            sucursal_id=filtros['sucursal_id'],
            fecha_contable__range=(fecha_inicio, fecha_fin),
        ).order_by('fecha_contable')

        if filtros['filtro_forzado'] and fecha_inicio == fecha_fin and not reportes_qs.exists():
            reporte_hoy, _ = _obtener_o_crear_reporte_del_dia(filtros['sucursal_id'], fecha_inicio)
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
            sucursal_id=filtros['sucursal_id'],
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

        # Recalcular y sincronizar totales por día para reportes abiertos del rango.
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

        return respuesta_estandar(
            data={
                'sucursal': {
                    'id': sucursal.id,
                    'nombre': sucursal.nombre,
                },
                'filtro_aplicado': {
                    'sucursal_id': filtros['sucursal_id'],
                    'fecha_inicio': fecha_inicio.isoformat(),
                    'fecha_fin': fecha_fin.isoformat(),
                    'filtro_forzado': filtros['filtro_forzado'],
                },
                'resumen': resumen,
                'filas': filas,
            },
            mensaje='Libro operativo diario obtenido correctamente.'
        )

    @action(detail=False, methods=['get'], url_path='actual')
    def actual(self, request):
        """
        Obtiene (o crea) el reporte del día contable actual (T-1) para la sucursal indicada.
        """
        sucursal_id = request.query_params.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El parámetro 'sucursal_id' es obligatorio.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        try:
            fecha_contable = _parsear_fecha_contable(request.query_params.get('fecha_contable'))
        except ValueError as error:
            return respuesta_estandar(
                mensaje=str(error),
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_objetivo = fecha_contable or _dia_contable_actual()
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite capturar en fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        if _fecha_contable_bloqueada_por_antiguedad(fecha_objetivo):
            return respuesta_estandar(
                mensaje="No se permite crear ni editar capturas en fechas contables con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        reporte, creado = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)
        return respuesta_estandar(
            data=ReporteDiarioSerializer(reporte, context={'request': request}).data,
            mensaje="Reporte del día contable creado automáticamente." if creado else "Reporte del día contable obtenido."
        )

    @action(detail=False, methods=['get'], url_path='resumen-actual')
    def resumen_actual(self, request):
        sucursal_id = request.query_params.get('sucursal_id') or getattr(request.user, 'sucursal_id', None)
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El parámetro 'sucursal_id' es obligatorio.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_contable = _parsear_fecha_contable(request.query_params.get('fecha_contable'))
        except ValueError as error:
            return respuesta_estandar(
                mensaje=str(error),
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_objetivo = fecha_contable or _dia_contable_actual()
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite consultar resumen en fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)
        resumen = _construir_resumen_rapido_reporte(reporte, request.user)
        return respuesta_estandar(data=resumen, mensaje="Resumen del día contable obtenido.")

    @action(detail=False, methods=['post'], url_path='cerrar-actual')
    def cerrar_actual(self, request):
        if not _usuario_puede_cerrar_dia(request.user):
            return respuesta_estandar(
                mensaje="No tienes permisos para ejecutar el cierre de día.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        sucursal_id = request.data.get('sucursal_id') or getattr(request.user, 'sucursal_id', None)
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El campo 'sucursal_id' es obligatorio.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_contable_cruda = request.data.get('fecha_contable')
        if fecha_contable_cruda in (None, ''):
            return respuesta_estandar(
                mensaje="El campo 'fecha_contable' es obligatorio para cerrar un día contable específico.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_contable = _parsear_fecha_contable(fecha_contable_cruda)
        except ValueError as error:
            return respuesta_estandar(
                mensaje=str(error),
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_objetivo = fecha_contable
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite cerrar fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)
            reporte = ReporteDiario.todos.select_for_update().get(pk=reporte.pk)

            if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
                return respuesta_estandar(
                    mensaje="El reporte ya está cerrado.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST
                )

            reporte = _cerrar_reporte_diario(reporte, request.user)

        return respuesta_estandar(
            data=ReporteDiarioSerializer(reporte, context={'request': request}).data,
            mensaje=f"Reporte del día {reporte.fecha_contable} cerrado correctamente."
        )

    @action(detail=False, methods=['get'], url_path='calendario-mensual')
    def calendario_mensual(self, request):
        sucursal_id = request.query_params.get('sucursal_id')
        anio = request.query_params.get('anio')
        mes = request.query_params.get('mes')

        if not sucursal_id or anio in (None, '') or mes in (None, ''):
            return respuesta_estandar(
                mensaje="Los parámetros 'sucursal_id', 'anio' y 'mes' son obligatorios.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        try:
            anio_valor = int(anio)
            mes_valor = int(mes)
            if mes_valor < 1 or mes_valor > 12:
                raise ValueError('Mes fuera de rango')
        except ValueError:
            return respuesta_estandar(
                mensaje="Los parámetros 'anio' y 'mes' deben ser enteros válidos.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        dia_actual_contable = _dia_contable_actual()
        total_dias_mes = monthrange(anio_valor, mes_valor)[1]
        fecha_inicio = datetime(anio_valor, mes_valor, 1).date()
        fecha_fin = datetime(anio_valor, mes_valor, total_dias_mes).date()

        reportes_mes = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__range=(fecha_inicio, fecha_fin)
        ).prefetch_related('movimientos')

        reportes_por_fecha = {reporte.fecha_contable: reporte for reporte in reportes_mes}
        dias = []

        for dia in range(1, total_dias_mes + 1):
            fecha = datetime(anio_valor, mes_valor, dia).date()
            reporte = reportes_por_fecha.get(fecha)

            if fecha > dia_actual_contable:
                codigo_estado = 'FUTURO_BLOQUEADO'
                color = 'azul'
                mensaje_estado = 'Dia futuro: aun no capturable'
            elif not reporte:
                if _fecha_contable_bloqueada_por_antiguedad(fecha):
                    codigo_estado = 'CERRADO_POR_ANTIGUEDAD'
                    color = 'rojo'
                    mensaje_estado = 'Dia cerrado por antiguedad (mas de 5 dias)'
                else:
                    codigo_estado = 'VENCIDO_SIN_CAPTURA' if fecha < dia_actual_contable else 'ABIERTO_SIN_CAPTURA'
                    color = 'rojo' if fecha < dia_actual_contable else 'verde'
                    mensaje_estado = 'Dia pasado sin captura' if fecha < dia_actual_contable else 'Dia actual disponible para captura'
            elif reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
                fecha_cierre_local = timezone.localtime(reporte.cerrado_en).date() if reporte.cerrado_en else fecha
                fecha_cierre_en_tiempo = fecha + timedelta(days=1)
                if fecha_cierre_local <= fecha_cierre_en_tiempo:
                    codigo_estado = 'CERRADO_EN_TIEMPO'
                    color = 'verde'
                    mensaje_estado = 'Cerrado en tiempo'
                else:
                    codigo_estado = 'CERRADO_TARDIO'
                    color = 'morado'
                    mensaje_estado = 'Cerrado tardio'
            else:
                if _fecha_contable_bloqueada_por_antiguedad(fecha):
                    codigo_estado = 'CERRADO_POR_ANTIGUEDAD'
                    color = 'rojo'
                    mensaje_estado = 'Dia cerrado por antiguedad (mas de 5 dias)'
                elif fecha < dia_actual_contable:
                    codigo_estado = 'ABIERTO_TARDIO'
                    color = 'morado'
                    mensaje_estado = 'Abierto fuera de tiempo'
                else:
                    codigo_estado = 'ABIERTO_SIN_CAPTURA'
                    color = 'verde'
                    mensaje_estado = 'Dia actual abierto para captura'

            dias.append({
                'fecha_contable': fecha.isoformat(),
                'dia': dia,
                'codigo_estado': codigo_estado,
                'color': color,
                'mensaje_estado': mensaje_estado,
                'editable': bool(
                    fecha <= dia_actual_contable
                    and not _fecha_contable_bloqueada_por_antiguedad(fecha)
                    and (not reporte or reporte.estado_reporte == ReporteDiario.EstadoReporte.ABIERTO)
                ),
                'reporte_id': reporte.id if reporte else None,
                'estado_reporte': reporte.estado_reporte if reporte else None,
                'total_ingresos': reporte.total_ingresos if reporte else 0,
                'total_egresos': reporte.total_egresos if reporte else 0,
                'resultado_neto': reporte.resultado_neto if reporte else 0,
            })

        return respuesta_estandar(
            data={
                'sucursal_id': int(sucursal_id),
                'anio': anio_valor,
                'mes': mes_valor,
                'dia_contable_actual': dia_actual_contable.isoformat(),
                'dias': dias,
            },
            mensaje='Calendario mensual de dias contables obtenido.'
        )

    def create(self, request):
        """Crea un ReporteDiario para una sucursal. La fecha contable es asignada automáticamente (T-1)."""
        sucursal_id = request.data.get('sucursal')
        if not sucursal_id:
            return respuesta_estandar(mensaje="El campo 'sucursal' es obligatorio.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        try:
            fecha_contable = _parsear_fecha_contable(request.data.get('fecha_contable'))
        except ValueError as error:
            return respuesta_estandar(mensaje=str(error), estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        fecha_objetivo = fecha_contable or _dia_contable_actual()
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite crear reportes para fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        if _fecha_contable_bloqueada_por_antiguedad(fecha_objetivo):
            return respuesta_estandar(
                mensaje="No se permite crear ni editar capturas en fechas contables con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        reporte, creado = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)
        mensaje = "Reporte diario creado automáticamente." if creado else "Ya existe un reporte para el día contable actual."
        codigo = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
        return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje=mensaje, codigo=codigo)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ReporteDiario, pk=pk)
        return respuesta_estandar(data=ReporteDiarioSerializer(obj, context={'request': request}).data, mensaje="Reporte diario obtenido.")

    def partial_update(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if _fecha_contable_bloqueada_por_antiguedad(reporte.fecha_contable):
            return respuesta_estandar(
                mensaje="No se permite editar reportes con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El reporte está cerrado. Use el flujo de reapertura si es necesario.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = ReporteDiarioSerializer(reporte, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje="Reporte actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if _fecha_contable_bloqueada_por_antiguedad(reporte.fecha_contable):
            return respuesta_estandar(
                mensaje="No se permite eliminar reportes con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="No se puede eliminar un reporte cerrado.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        reporte.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje="Reporte diario eliminado (baja lógica).")

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """
        Cierre manual del día contable.
        Usa transaction.atomic + select_for_update para evitar condiciones de carrera.
        El cierre automático lo ejecuta la tarea Celery `cerrar_dia_contable`.
        """
        if not _usuario_puede_cerrar_dia(request.user):
            return respuesta_estandar(
                mensaje="No tienes permisos para ejecutar el cierre de día.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            reporte = ReporteDiario.todos.select_for_update().get(pk=pk)
            if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
                return respuesta_estandar(mensaje="El reporte ya está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

            reporte = _cerrar_reporte_diario(reporte, request.user)

        return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje=f"Reporte del día {reporte.fecha_contable} cerrado correctamente.")

    @action(detail=True, methods=['post'], url_path='reabrir')
    def reabrir(self, request, pk=None):
        """
        Reabre un reporte cerrado. EXCLUSIVO para ADMINISTRADOR.
        Deja rastro en el historial de simple_history (quién y cuándo reabrió).
        Tras la reapertura, el día puede ser modificado nuevamente si el horario lo permite.
        """
        with transaction.atomic():
            reporte = ReporteDiario.todos.select_for_update().get(pk=pk)
            if _fecha_contable_bloqueada_por_antiguedad(reporte.fecha_contable):
                return respuesta_estandar(
                    mensaje="No se permite reabrir reportes con más de 5 días de antigüedad.",
                    estado="error",
                    codigo=status.HTTP_403_FORBIDDEN
                )
            if reporte.estado_reporte != ReporteDiario.EstadoReporte.CERRADO:
                return respuesta_estandar(mensaje="El reporte no está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

            reporte.estado_reporte = ReporteDiario.EstadoReporte.ABIERTO
            reporte.cerrado_en     = None
            reporte.cerrado_por    = None
            # El motivo de reapertura queda en el history con el usuario autenticado
            reporte._history_user  = request.user
            reporte.save()

        return respuesta_estandar(
            data=ReporteDiarioSerializer(reporte, context={'request': request}).data,
            mensaje=f"Reporte del día {reporte.fecha_contable} reabierto por {request.user.username}. Queda registrado en el historial."
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MOVIMIENTO DIARIO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: exponer API de líneas de captura operativa del día.
# 2) Cómo funciona: vincula concepto+sucursal al reporte T-1 y aplica restricciones de cierre/horario.
# 3) Qué hace: crea, actualiza, lista y elimina movimientos con validación de estado contable.
# 4) Cómo editarla: integra nuevas reglas de captura en create/captura_rapida antes del serializer.
class MovimientoDiarioViewSet(viewsets.ViewSet):
    """
    CRUD de movimientos diarios.

    Regla crítica de T-1: El backend IGNORA cualquier `reporte` o `fecha_contable`
    enviada por el frontend. El reporte se asigna automáticamente por el backend
    según la sucursal del movimiento y el día contable actual (T-1).

    Soporta filtrado por ?reporte_id= y ?categoria_id=
    """

    def get_permissions(self):
        acciones_escritura = ('create', 'update', 'partial_update', 'destroy', 'captura_rapida')
        if self.action in acciones_escritura:
            return [IsAuthenticated(), VentanaHorariaPermiso()]
        return [IsAuthenticated()]

    def list(self, request):
        qs = MovimientoDiario.objects.all()
        if reporte_id := request.query_params.get('reporte_id'):
            qs = qs.filter(reporte_id=reporte_id)
        if categoria_id := request.query_params.get('categoria_id'):
            qs = qs.filter(concepto__categoria_id=categoria_id)
        return respuesta_estandar(data=MovimientoDiarioListSerializer(qs, many=True, context={'request': request}).data, mensaje="Movimientos obtenidos.")

    def create(self, request):
        """
        Registra un movimiento. El backend calcula automáticamente el ReporteDiario (T-1).
        El frontend DEBE enviar: concepto, monto, sucursal_id (y opcionalmente: monto_divisa, tipo_divisa, detalles_snapshot, notas).
        El campo 'reporte' que envíe el frontend es IGNORADO.
        """
        sucursal_id = request.data.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(mensaje="El campo 'sucursal_id' es obligatorio.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        try:
            fecha_contable = _parsear_fecha_contable(request.data.get('fecha_contable'))
        except ValueError as error:
            return respuesta_estandar(mensaje=str(error), estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        fecha_objetivo = fecha_contable or _dia_contable_actual()
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite capturar en fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        if _fecha_contable_bloqueada_por_antiguedad(fecha_objetivo):
            return respuesta_estandar(
                mensaje="No se permite crear ni editar capturas en fechas contables con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)

        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día contable ya fue cerrado. No se pueden agregar movimientos.",
                estado="error", codigo=status.HTTP_403_FORBIDDEN
            )

        # Construir datos ignorando el 'reporte' del frontend y forzando el calculado
        datos = _construir_datos_movimiento(request, reporte.pk)

        s = MovimientoDiarioSerializer(data=datos)
        if s.is_valid():
            mov = s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento registrado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al registrar movimiento.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='captura-rapida')
    def captura_rapida(self, request):
        """
        Crea o actualiza automáticamente el movimiento del día contable para un concepto.
        Se usa para capturas por tabla con autoguardado en frontend.

        Reglas de guardado:
        - Si llega `movimiento_id`, actualiza ese movimiento puntual.
        - Si la categoría del concepto tiene detalles parametrizados activos y NO llega `movimiento_id`, crea un movimiento nuevo.
        - Si la categoría no tiene detalles parametrizados activos y NO llega `movimiento_id`, mantiene el comportamiento histórico de upsert por concepto.
        """
        sucursal_id = request.data.get('sucursal_id')
        concepto_id = request.data.get('concepto')

        if not sucursal_id or not concepto_id:
            return respuesta_estandar(
                mensaje="Los campos 'sucursal_id' y 'concepto' son obligatorios.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_contable = _parsear_fecha_contable(request.data.get('fecha_contable'))
        except ValueError as error:
            return respuesta_estandar(
                mensaje=str(error),
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_objetivo = fecha_contable or _dia_contable_actual()
        if fecha_objetivo > _dia_contable_actual():
            return respuesta_estandar(
                mensaje="No se permite capturar en fechas contables futuras.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        if _fecha_contable_bloqueada_por_antiguedad(fecha_objetivo):
            return respuesta_estandar(
                mensaje="No se permite crear ni editar capturas en fechas contables con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id, fecha_objetivo)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día contable ya fue cerrado. No se pueden registrar cambios.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            datos = _construir_datos_movimiento(request, reporte.id)
            movimiento_id = request.data.get('movimiento_id')

            # Campo de control de flujo para backend; no forma parte del serializer.
            datos.pop('movimiento_id', None)

            movimiento_existente = None

            if movimiento_id not in (None, ''):
                try:
                    movimiento_id = int(movimiento_id)
                except (TypeError, ValueError):
                    return respuesta_estandar(
                        mensaje="El campo 'movimiento_id' debe ser un entero válido.",
                        estado="error",
                        codigo=status.HTTP_400_BAD_REQUEST
                    )

                movimiento_existente = MovimientoDiario.objects.filter(
                    id=movimiento_id,
                    reporte_id=reporte.id,
                    concepto_id=concepto_id,
                ).first()

                if movimiento_existente is None:
                    return respuesta_estandar(
                        mensaje="No se encontró el movimiento solicitado para actualizar en esta captura.",
                        estado="error",
                        codigo=status.HTTP_404_NOT_FOUND
                    )
            else:
                concepto = Concepto.objects.filter(id=concepto_id).select_related('categoria').first()
                if concepto is None:
                    return respuesta_estandar(
                        mensaje="El concepto enviado no existe.",
                        estado="error",
                        codigo=status.HTTP_400_BAD_REQUEST
                    )

                categoria_tiene_detalles_parametrizados = concepto.categoria.detalles_parametrizados.filter(
                    estado='ACTIVO',
                    eliminado_en__isnull=True,
                ).exists()

                if not categoria_tiene_detalles_parametrizados:
                    movimiento_existente = MovimientoDiario.objects.filter(
                        reporte_id=reporte.id,
                        concepto_id=concepto_id
                    ).first()

            if movimiento_existente:
                serializador = MovimientoDiarioSerializer(movimiento_existente, data=datos, partial=True)
            else:
                serializador = MovimientoDiarioSerializer(data=datos)

            if not serializador.is_valid():
                return respuesta_estandar(
                    data=serializador.errors,
                    mensaje="Error al guardar captura rápida.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST
                )

            movimiento = serializador.save()

        mensaje = "Movimiento actualizado en captura rápida." if movimiento_existente else "Movimiento creado en captura rápida."
        return respuesta_estandar(
            data=MovimientoDiarioSerializer(movimiento, context={'request': request}).data,
            mensaje=mensaje,
            codigo=status.HTTP_200_OK if movimiento_existente else status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=MovimientoDiarioSerializer(get_object_or_404(MovimientoDiario, pk=pk), context={'request': request}).data, mensaje="Movimiento obtenido.")

    def update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if _fecha_contable_bloqueada_por_antiguedad(mov.reporte.fecha_contable):
            return respuesta_estandar(
                mensaje="No se permite editar movimientos con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El día está cerrado. Edite dejando rastro en el historial mediante una reapertura.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = MovimientoDiarioSerializer(mov, data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if _fecha_contable_bloqueada_por_antiguedad(mov.reporte.fecha_contable):
            return respuesta_estandar(
                mensaje="No se permite editar movimientos con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El día está cerrado.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = MovimientoDiarioSerializer(mov, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if _fecha_contable_bloqueada_por_antiguedad(mov.reporte.fecha_contable):
            return respuesta_estandar(
                mensaje="No se permite eliminar movimientos con más de 5 días de antigüedad.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día está cerrado. Para anular un movimiento contable use el flujo de contrapartida.",
                estado="error", codigo=status.HTTP_403_FORBIDDEN
            )
        mov.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje="Movimiento eliminado (baja lógica).")


