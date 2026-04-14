from datetime import timedelta

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from categoria_operativa.models import CategoriaOperativa
from configuraciones_globales.models import RubroContable
from reportes_diarios.models import ReporteDiario, MovimientoDiario
from sucursales.models import Sucursal


# 1) Para qué sirve: estandarizar salidas JSON del endpoint de estado de resultados.
# 2) Cómo funciona: encapsula payload, mensaje y estado HTTP en formato común.
# 3) Qué hace: facilita integración de frontend y manejo uniforme de errores.
# 4) Cómo editarla: ajusta aquí si cambia el contrato global de respuestas API.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: validar si el usuario puede consultar estadísticas ejecutivas.
# 2) Cómo funciona: autoriza DIRECTOR/ADMINISTRADOR o superusuario/staff.
# 3) Qué hace: restringe el endpoint sensible solo a perfiles estratégicos.
# 4) Cómo editarla: agrega/quita roles permitidos según política de seguridad.
def _usuario_puede_ver_estadisticas(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.is_superuser or usuario.is_staff:
        return True
    try:
        return usuario.usuario_roles.filter(rol__nombre__in=['DIRECTOR', 'ADMINISTRADOR']).exists()
    except Exception:
        return False


# 1) Para qué sirve: convertir montos Decimal/None a float seguro para respuestas JSON.
# 2) Cómo funciona: intenta casteo y aplica fallback a 0.0 ante errores.
# 3) Qué hace: evita fallos de serialización y simplifica cálculos de frontend.
# 4) Cómo editarla: cambia precisión o tipo de retorno si se requiere formato distinto.
def _a_flotante(valor):
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


# 1) Para qué sirve: normalizar cadenas de rubros para validaciones semánticas.
# 2) Cómo funciona: recorta, mayusculiza y unifica separadores a guion bajo.
# 3) Qué hace: facilita identificar patrones como SIN_GRUPO o NO_CONTABLE.
# 4) Cómo editarla: agrega más sustituciones si surgen nuevos formatos de catálogos.
def _normalizar_texto_rubro(valor):
    return str(valor or '').strip().replace('-', '_').replace(' ', '_').upper()


# 1) Para qué sirve: detectar rubros que no deben impactar estado de resultados.
# 2) Cómo funciona: evalúa ausencia de rubro y marcadores semánticos de no contable.
# 3) Qué hace: clasifica como no contable casos SIN_RUBRO, SIN_GRUPO o NO_CONTABLE.
# 4) Cómo editarla: amplía patrones cuando se incorporen nuevas nomenclaturas.
def _rubro_es_no_contable(rubro=None, rubro_id=None, rubro_tipo=None, rubro_padre_clave=None, rubro_padre_nombre=None):
    if rubro is not None:
        rubro_id = getattr(rubro, 'id', rubro_id)
        rubro_tipo = getattr(rubro, 'tipo', rubro_tipo)
        padre = getattr(rubro, 'padre', None)
        rubro_padre_clave = getattr(padre, 'clave', rubro_padre_clave) if padre else rubro_padre_clave
        rubro_padre_nombre = getattr(padre, 'nombre', rubro_padre_nombre) if padre else rubro_padre_nombre

    identificador = _normalizar_texto_rubro(rubro_id)
    tipo_rubro = _normalizar_texto_rubro(rubro_tipo)
    padre_clave = _normalizar_texto_rubro(rubro_padre_clave)
    padre_nombre = _normalizar_texto_rubro(rubro_padre_nombre)
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


# 1) Para qué sirve: decidir si un rubro impacta los totales contables del reporte.
# 2) Cómo funciona: combina bandera del padre con clasificación semántica contable.
# 3) Qué hace: excluye no contables aunque el flag histórico venga en true.
# 4) Cómo editarla: centraliza reglas para mantener consistencia entre tiempo real e histórico.
def _rubro_debe_considerarse_en_estado_resultados(
    rubro=None,
    rubro_id=None,
    rubro_tipo=None,
    rubro_padre_clave=None,
    rubro_padre_nombre=None,
    considerar_padre=True,
):
    if not bool(considerar_padre):
        return False

    return not _rubro_es_no_contable(
        rubro=rubro,
        rubro_id=rubro_id,
        rubro_tipo=rubro_tipo,
        rubro_padre_clave=rubro_padre_clave,
        rubro_padre_nombre=rubro_padre_nombre,
    )


# 1) Para qué sirve: parsear fechas ISO recibidas por query string.
# 2) Cómo funciona: usa parse_date de Django y valida vacíos/formato.
# 3) Qué hace: unifica entrada de filtros fecha, fecha_inicio y fecha_fin.
# 4) Cómo editarla: agrega formatos alternos si negocio los habilita.
def _parsear_fecha_iso(valor, nombre_parametro):
    if valor in (None, ''):
        return None
    fecha = timezone.datetime.strptime(str(valor), '%Y-%m-%d').date()
    if fecha is None:
        raise ValueError(f"El parámetro '{nombre_parametro}' debe tener formato YYYY-MM-DD.")
    return fecha


# 1) Para qué sirve: calcular variación porcentual entre dos valores de forma segura.
# 2) Cómo funciona: maneja división entre cero y redondea a dos decimales.
# 3) Qué hace: entrega indicador comparable entre periodo actual y anterior.
# 4) Cómo editarla: cambia regla cuando el valor anterior es cero según criterio financiero.
def _variacion_porcentual(valor_actual, valor_anterior):
    actual = _a_flotante(valor_actual)
    anterior = _a_flotante(valor_anterior)
    if anterior == 0:
        if actual == 0:
            return 0.0
        return None
    return round(((actual - anterior) / abs(anterior)) * 100, 2)


# 1) Para qué sirve: construir estado de resultados mensual o diario según filtros.
# 2) Cómo funciona: prioriza snapshot histórico cerrado y cae a cálculo en tiempo real.
# 3) Qué hace: entrega métricas por rubro/categoría para análisis ejecutivo.
# 4) Cómo editarla: amplía lógica de agregación en get y _construir_rubros_base si cambian reportes.
class EstadoResultadosAPIView(APIView):
    """
    Endpoint de Estado de Resultados con modo dual:

    - Mes CERRADO (LibroEstadoResultados.estado_mes == CERRADO):
      Devuelve directamente el snapshot guardado en `LibroEstadoResultados.desglose_por_rubro`.
      Lectura instantánea, sin costo de agregación. Ideal para consultas del rol Director.

    - Mes en CURSO (no hay libro cerrado):
      Agrega en tiempo real desde MovimientoDiario. Siempre refleja el estado actual.

        Parámetros de query:
            - sucursal_id (obligatorio)
            - mes         (opcional, default: mes actual)
            - anio        (opcional, default: año actual)

    GET /api/estado-resultados/?sucursal_id=1&mes=3&anio=2026
    """

    @staticmethod
    def _construir_rubros_base():
        rubros = (
            RubroContable.objects.filter(eliminado_en__isnull=True)
            .select_related('padre')
            .order_by('padre__nombre', 'nombre')
            .values('id', 'nombre', 'tipo', 'padre__clave', 'padre__nombre', 'padre__considerar_en_estado_resultados')
        )
        return {
            rubro['id']: {
                "rubro_id": rubro['id'],
                "rubro_nombre": rubro['nombre'],
                "rubro_tipo": rubro['tipo'],
                "rubro_padre": rubro.get('padre__nombre') or 'SIN GRUPO',
                "rubro_padre_clave": rubro.get('padre__clave'),
                "rubro_padre_considerar_en_estado_resultados": _rubro_debe_considerarse_en_estado_resultados(
                    rubro_id=rubro['id'],
                    rubro_tipo=rubro.get('tipo'),
                    rubro_padre_clave=rubro.get('padre__clave'),
                    rubro_padre_nombre=rubro.get('padre__nombre'),
                    considerar_padre=rubro.get('padre__considerar_en_estado_resultados', True),
                ),
                "total_ingresos": 0.0,
                "total_egresos": 0.0,
                "resultado_neto": 0.0,
            }
            for rubro in rubros
        }

    def get(self, request):
        sucursal_id = request.query_params.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El parámetro 'sucursal_id' es obligatorio.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        hoy = timezone.localdate()
        try:
            mes  = int(request.query_params.get('mes', hoy.month))
            anio = int(request.query_params.get('anio', hoy.year))
        except ValueError:
            return respuesta_estandar(
                mensaje="Los parámetros 'mes' y 'anio' deben ser números enteros.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        if mes < 1 or mes > 12:
            return respuesta_estandar(
                mensaje="El parámetro 'mes' debe estar en el rango 1-12.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        # ── Modo 1: Mes CERRADO → devolver snapshot del libro ─────────────────
        try:
            from libro_estado_resultados.models import LibroEstadoResultados
            libro = LibroEstadoResultados.objects.filter(
                sucursal_id=sucursal_id,
                anio=anio,
                mes=mes,
                estado_mes=LibroEstadoResultados.EstadoMes.CERRADO,
                eliminado_en__isnull=True,
            ).first()

            if libro:
                rubros_base = self._construir_rubros_base()
                desglose_snapshot_crudo = libro.desglose_por_rubro or []
                desglose_snapshot = []

                if isinstance(desglose_snapshot_crudo, dict):
                    # Compatibilidad con snapshots legados donde el desglose era un dict por nombre de rubro.
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
                        rubros_base[rubro_id]['total_ingresos'] = float(rubro.get('total_ingresos') or 0)
                        rubros_base[rubro_id]['total_egresos'] = float(rubro.get('total_egresos') or 0)
                        rubros_base[rubro_id]['resultado_neto'] = float(rubro.get('resultado_neto') or 0)
                        continue

                    rubros_base[rubro_id] = {
                        "rubro_id": rubro_id,
                        "rubro_nombre": rubro.get('rubro_nombre') or 'SIN RUBRO CONTABLE',
                        "rubro_tipo": rubro.get('rubro_tipo') or 'NO_CONTABLE',
                        "rubro_padre": rubro.get('rubro_padre') or 'SIN GRUPO',
                        "rubro_padre_clave": rubro.get('rubro_padre_clave'),
                        "rubro_padre_considerar_en_estado_resultados": _rubro_debe_considerarse_en_estado_resultados(
                            rubro_id=rubro_id,
                            rubro_tipo=rubro.get('rubro_tipo'),
                            rubro_padre_clave=rubro.get('rubro_padre_clave'),
                            rubro_padre_nombre=rubro.get('rubro_padre'),
                            considerar_padre=rubro.get('rubro_padre_considerar_en_estado_resultados', True),
                        ),
                        "total_ingresos": float(rubro.get('total_ingresos') or 0),
                        "total_egresos": float(rubro.get('total_egresos') or 0),
                        "resultado_neto": float(rubro.get('resultado_neto') or 0),
                    }

                rubros_lista = list(rubros_base.values())
                rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))

                rubros_considerados = [
                    rubro_item for rubro_item in rubros_lista
                    if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
                ]
                rubros_no_considerados = [
                    rubro_item for rubro_item in rubros_lista
                    if not bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
                ]
                total_ingresos_considerados = sum(float(rubro_item.get('total_ingresos') or 0) for rubro_item in rubros_considerados)
                total_egresos_considerados = sum(float(rubro_item.get('total_egresos') or 0) for rubro_item in rubros_considerados)
                resultado_neto_considerado = total_ingresos_considerados - total_egresos_considerados
                total_ingresos_no_considerados = sum(float(rubro_item.get('total_ingresos') or 0) for rubro_item in rubros_no_considerados)
                total_egresos_no_considerados = sum(float(rubro_item.get('total_egresos') or 0) for rubro_item in rubros_no_considerados)
                resultado_neto_no_considerado = total_ingresos_no_considerados - total_egresos_no_considerados

                data = {
                    "fuente":               "snapshot_historico",
                    "sucursal_id":          int(sucursal_id),
                    "periodo":              f"{anio}/{mes:02d}",
                    "estado_mes":           libro.estado_mes,
                    "saldo_arrastre_inicio": float(libro.saldo_arrastre_inicio),
                    "total_ingresos":       float(total_ingresos_considerados),
                    "total_egresos":        float(total_egresos_considerados),
                    "resultado_neto":       float(resultado_neto_considerado),
                    "saldo_arrastre_fin":   float(libro.saldo_arrastre_inicio) + float(resultado_neto_considerado),
                    "total_ingresos_no_considerados": float(total_ingresos_no_considerados),
                    "total_egresos_no_considerados": float(total_egresos_no_considerados),
                    "resultado_neto_no_considerado": float(resultado_neto_no_considerado),
                    "tipo_cambio_usd":      float(libro.tipo_cambio_usd_snapshot),
                    "tipo_cambio_eur":      float(libro.tipo_cambio_eur_snapshot),
                    "cerrado_en":           libro.cerrado_en.isoformat() if libro.cerrado_en else None,
                    "por_rubro":            rubros_lista,
                    "por_categoria":        [],  # No disponible en snapshot — consultar MovimientoDiario si se necesita
                }
                return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} — datos del cierre histórico.")
        except Exception:
            pass  # Si no hay libro, continuar con modo en tiempo real

        # ── Modo 2: Mes en curso → agregar en tiempo real ──────────────────────
        movimientos = MovimientoDiario.objects.filter(
            reporte__sucursal_id=sucursal_id,
            reporte__fecha_contable__year=anio,
            reporte__fecha_contable__month=mes,
            eliminado_en__isnull=True,
        ).select_related(
            'concepto__categoria',
            'concepto__rubro_contable',
            'concepto__rubro_contable__padre',
        )

        rubros_base = self._construir_rubros_base()

        def construir_respuesta_sin_movimientos(mensaje):
            rubros_lista = list(rubros_base.values())
            rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))
            return respuesta_estandar(
                data={
                    "fuente": "tiempo_real",
                    "sucursal_id": int(sucursal_id),
                    "periodo": f"{anio}/{mes:02d}",
                    "total_ingresos": 0,
                    "total_egresos": 0,
                    "resultado_neto": 0,
                    "por_categoria": [],
                    "por_rubro": rubros_lista,
                },
                mensaje=mensaje,
            )

        if not movimientos.exists():
            return construir_respuesta_sin_movimientos(f"Sin movimientos registrados para {anio}/{mes:02d}.")

        # Desglose por Categoría Operativa
        por_categoria = {}
        por_rubro = dict(rubros_base)
        for mov in movimientos:
            cat   = mov.concepto.categoria
            rubro = mov.concepto.rubro_contable
            rubro_id = rubro.id if rubro else 'SIN_RUBRO_CONTABLE'
            rubro_nombre = rubro.nombre if rubro else 'SIN RUBRO CONTABLE'
            rubro_tipo = rubro.tipo if rubro else 'NO_CONTABLE'
            rubro_padre = rubro.padre.nombre if rubro and rubro.padre else 'SIN GRUPO'
            rubro_padre_clave = rubro.padre.clave if rubro and rubro.padre else None
            rubro_padre_considerar = _rubro_debe_considerarse_en_estado_resultados(
                rubro=rubro,
                rubro_id=rubro_id,
                rubro_tipo=rubro_tipo,
                rubro_padre_clave=rubro_padre_clave,
                rubro_padre_nombre=rubro_padre,
                considerar_padre=(bool(rubro.padre.considerar_en_estado_resultados) if rubro and rubro.padre else False),
            )

            if cat.id not in por_categoria:
                por_categoria[cat.id] = {"categoria_id": cat.id, "categoria_nombre": cat.nombre, "categoria_clave": cat.clave, "tipo": cat.tipo, "total_ingresos": 0, "total_egresos": 0, "resultado_neto": 0}
            if rubro_id not in por_rubro:
                por_rubro[rubro_id] = {
                    "rubro_id": rubro_id,
                    "rubro_nombre": rubro_nombre,
                    "rubro_tipo": rubro_tipo,
                    "rubro_padre": rubro_padre,
                    "rubro_padre_clave": rubro_padre_clave,
                    "rubro_padre_considerar_en_estado_resultados": rubro_padre_considerar,
                    "total_ingresos": 0.0,
                    "total_egresos": 0.0,
                    "resultado_neto": 0.0,
                }

            campo = 'total_ingresos' if mov.concepto.tipo == 'INGRESO' else 'total_egresos'
            por_categoria[cat.id][campo] += float(mov.monto)
            por_rubro[rubro_id][campo] += float(mov.monto)

        for d in list(por_categoria.values()) + list(por_rubro.values()):
            d['resultado_neto'] = d['total_ingresos'] - d['total_egresos']

        reportes_mes = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__year=anio,
            fecha_contable__month=mes,
        )

        primer_reporte = reportes_mes.order_by('fecha_contable').first()
        saldo_inicio = float(primer_reporte.saldo_arrastre_inicio) if primer_reporte else 0

        rubros_lista = list(por_rubro.values())
        rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))

        rubros_considerados = [
            rubro_item for rubro_item in rubros_lista
            if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
        ]
        rubros_no_considerados = [
            rubro_item for rubro_item in rubros_lista
            if not bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
        ]
        total_ingresos_considerados = sum(float(rubro_item.get('total_ingresos') or 0) for rubro_item in rubros_considerados)
        total_egresos_considerados = sum(float(rubro_item.get('total_egresos') or 0) for rubro_item in rubros_considerados)
        resultado_neto_considerado = total_ingresos_considerados - total_egresos_considerados
        total_ingresos_no_considerados = sum(float(rubro_item.get('total_ingresos') or 0) for rubro_item in rubros_no_considerados)
        total_egresos_no_considerados = sum(float(rubro_item.get('total_egresos') or 0) for rubro_item in rubros_no_considerados)
        resultado_neto_no_considerado = total_ingresos_no_considerados - total_egresos_no_considerados

        data = {
            "fuente":               "tiempo_real",
            "sucursal_id":          int(sucursal_id),
            "periodo":              f"{anio}/{mes:02d}",
            "saldo_arrastre_inicio": saldo_inicio,
            "total_ingresos":       float(total_ingresos_considerados),
            "total_egresos":        float(total_egresos_considerados),
            "resultado_neto":       float(resultado_neto_considerado),
            "saldo_proyectado_fin":  saldo_inicio + float(resultado_neto_considerado),
            "total_ingresos_no_considerados": float(total_ingresos_no_considerados),
            "total_egresos_no_considerados": float(total_egresos_no_considerados),
            "resultado_neto_no_considerado": float(resultado_neto_no_considerado),
            "por_categoria":        list(por_categoria.values()),
            "por_rubro":            rubros_lista,
        }

        return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} calculado en tiempo real.")


# 1) Para qué sirve: exponer tablero analítico avanzado con filtros de operación.
# 2) Cómo funciona: consolida métricas y series desde MovimientoDiario según rango y filtros.
# 3) Qué hace: alimenta gráficas ejecutivas para DIRECTOR y ADMINISTRADOR.
# 4) Cómo editarla: amplía agregaciones (ej. por hora o por responsable) dentro de get.
class EstadisticasOperativasAPIView(APIView):
    """
    Endpoint de estadísticas operativas avanzadas.

    Filtros soportados:
      - fecha (YYYY-MM-DD) para un solo día.
      - fecha_inicio / fecha_fin (YYYY-MM-DD) para rango inclusivo.
      - sucursal_id (opcional).
      - categoria_id o categoria_ids (opcional; categoria_ids acepta CSV).
      - tipo_concepto: TODOS | INGRESO | EGRESO.
    """

    def get(self, request):
        if not _usuario_puede_ver_estadisticas(request.user):
            return respuesta_estandar(
                mensaje="No tienes permisos para consultar el módulo de estadísticas.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN,
            )

        hoy_contable = timezone.localdate() - timezone.timedelta(days=1)

        try:
            fecha_unica = _parsear_fecha_iso(request.query_params.get('fecha'), 'fecha')
            fecha_inicio = _parsear_fecha_iso(request.query_params.get('fecha_inicio'), 'fecha_inicio')
            fecha_fin = _parsear_fecha_iso(request.query_params.get('fecha_fin'), 'fecha_fin')
        except ValueError as error:
            return respuesta_estandar(mensaje=str(error), estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        if fecha_unica:
            fecha_inicio = fecha_unica
            fecha_fin = fecha_unica
        else:
            if fecha_inicio is None and fecha_fin is None:
                fecha_fin = hoy_contable
                fecha_inicio = fecha_fin - timedelta(days=29)
            elif fecha_inicio is None:
                fecha_inicio = fecha_fin
            elif fecha_fin is None:
                fecha_fin = fecha_inicio

        if fecha_inicio > fecha_fin:
            return respuesta_estandar(
                mensaje="La fecha_inicio no puede ser mayor a la fecha_fin.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        sucursal_id = request.query_params.get('sucursal_id')
        if sucursal_id not in (None, ''):
            try:
                sucursal_id = int(sucursal_id)
            except (TypeError, ValueError):
                return respuesta_estandar(
                    mensaje="El parámetro 'sucursal_id' debe ser un entero válido.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )
        else:
            sucursal_id = None

        categorias_filtradas = []
        categoria_id = request.query_params.get('categoria_id')
        categoria_ids_csv = request.query_params.get('categoria_ids')

        if categoria_id not in (None, ''):
            try:
                categorias_filtradas.append(int(categoria_id))
            except (TypeError, ValueError):
                return respuesta_estandar(
                    mensaje="El parámetro 'categoria_id' debe ser un entero válido.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

        if categoria_ids_csv:
            try:
                categorias_filtradas.extend(
                    [int(valor.strip()) for valor in str(categoria_ids_csv).split(',') if valor.strip()]
                )
            except ValueError:
                return respuesta_estandar(
                    mensaje="El parámetro 'categoria_ids' debe ser una lista CSV de enteros válidos.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

        categorias_filtradas = sorted(set(categorias_filtradas))

        tipo_concepto = str(request.query_params.get('tipo_concepto', 'TODOS') or 'TODOS').strip().upper()
        if tipo_concepto not in ('TODOS', 'INGRESO', 'EGRESO'):
            return respuesta_estandar(
                mensaje="El parámetro 'tipo_concepto' solo permite valores TODOS, INGRESO o EGRESO.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        movimientos_qs = MovimientoDiario.objects.filter(
            eliminado_en__isnull=True,
            reporte__eliminado_en__isnull=True,
            reporte__fecha_contable__range=(fecha_inicio, fecha_fin),
        )

        if sucursal_id:
            movimientos_qs = movimientos_qs.filter(reporte__sucursal_id=sucursal_id)

        if categorias_filtradas:
            movimientos_qs = movimientos_qs.filter(concepto__categoria_id__in=categorias_filtradas)

        if tipo_concepto != 'TODOS':
            movimientos_qs = movimientos_qs.filter(concepto__tipo=tipo_concepto)

        totales = movimientos_qs.aggregate(
            total_ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            total_egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            total_montos=Sum('monto'),
            total_movimientos=Count('id'),
            total_movimientos_ingresos=Count('id', filter=Q(concepto__tipo='INGRESO')),
            total_movimientos_egresos=Count('id', filter=Q(concepto__tipo='EGRESO')),
        )

        total_ingresos = _a_flotante(totales.get('total_ingresos'))
        total_egresos = _a_flotante(totales.get('total_egresos'))
        total_movimientos = int(totales.get('total_movimientos') or 0)
        total_montos = _a_flotante(totales.get('total_montos'))
        resultado_neto = total_ingresos - total_egresos

        dias_periodo = (fecha_fin - fecha_inicio).days + 1
        dias_con_movimientos = movimientos_qs.values('reporte__fecha_contable').distinct().count()
        ticket_promedio = (total_montos / total_movimientos) if total_movimientos else 0.0
        promedio_diario_neto = (resultado_neto / dias_periodo) if dias_periodo else 0.0

        por_dia_raw = movimientos_qs.values('reporte__fecha_contable').annotate(
            ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            movimientos=Count('id'),
        ).order_by('reporte__fecha_contable')

        mapa_por_dia = {
            item['reporte__fecha_contable']: {
                'ingresos': _a_flotante(item.get('ingresos')),
                'egresos': _a_flotante(item.get('egresos')),
                'movimientos': int(item.get('movimientos') or 0),
            }
            for item in por_dia_raw
        }

        por_dia = []
        cursor = fecha_inicio
        while cursor <= fecha_fin:
            info = mapa_por_dia.get(cursor, {'ingresos': 0.0, 'egresos': 0.0, 'movimientos': 0})
            neto = _a_flotante(info['ingresos']) - _a_flotante(info['egresos'])
            por_dia.append(
                {
                    'fecha': cursor.isoformat(),
                    'ingresos': _a_flotante(info['ingresos']),
                    'egresos': _a_flotante(info['egresos']),
                    'neto': neto,
                    'movimientos': int(info['movimientos']),
                }
            )
            cursor += timedelta(days=1)

        mejor_dia = max(por_dia, key=lambda item: item['neto'], default=None)
        peor_dia = min(por_dia, key=lambda item: item['neto'], default=None)

        por_categoria_raw = movimientos_qs.values(
            'concepto__categoria_id',
            'concepto__categoria__nombre',
            'concepto__categoria__clave',
        ).annotate(
            ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            movimientos=Count('id'),
        ).order_by('-movimientos')

        por_categoria = []
        for item in por_categoria_raw:
            ingresos = _a_flotante(item.get('ingresos'))
            egresos = _a_flotante(item.get('egresos'))
            por_categoria.append(
                {
                    'categoria_id': item.get('concepto__categoria_id'),
                    'categoria_nombre': item.get('concepto__categoria__nombre') or 'SIN CATEGORIA',
                    'categoria_clave': item.get('concepto__categoria__clave') or '',
                    'ingresos': ingresos,
                    'egresos': egresos,
                    'neto': ingresos - egresos,
                    'movimientos': int(item.get('movimientos') or 0),
                }
            )

        por_rubro_raw = movimientos_qs.values(
            'concepto__rubro_contable_id',
            'concepto__rubro_contable__nombre',
            'concepto__rubro_contable__padre__nombre',
        ).annotate(
            ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            movimientos=Count('id'),
        ).order_by('-movimientos')

        por_rubro = []
        for item in por_rubro_raw:
            ingresos = _a_flotante(item.get('ingresos'))
            egresos = _a_flotante(item.get('egresos'))
            nombre_rubro = item.get('concepto__rubro_contable__nombre') or 'SIN RUBRO CONTABLE'
            nombre_padre = item.get('concepto__rubro_contable__padre__nombre') or 'SIN PADRE'
            por_rubro.append(
                {
                    'rubro_id': item.get('concepto__rubro_contable_id') or 'SIN_RUBRO',
                    'rubro_nombre': nombre_rubro,
                    'rubro_padre_nombre': nombre_padre,
                    'rubro_nombre_con_padre': f"{nombre_rubro} - {nombre_padre}",
                    'ingresos': ingresos,
                    'egresos': egresos,
                    'neto': ingresos - egresos,
                    'movimientos': int(item.get('movimientos') or 0),
                }
            )

        por_sucursal_raw = movimientos_qs.values(
            'reporte__sucursal_id',
            'reporte__sucursal__nombre',
        ).annotate(
            ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            movimientos=Count('id'),
        ).order_by('-movimientos')

        por_sucursal = []
        for item in por_sucursal_raw:
            ingresos = _a_flotante(item.get('ingresos'))
            egresos = _a_flotante(item.get('egresos'))
            por_sucursal.append(
                {
                    'sucursal_id': item.get('reporte__sucursal_id'),
                    'sucursal_nombre': item.get('reporte__sucursal__nombre') or 'SIN SUCURSAL',
                    'ingresos': ingresos,
                    'egresos': egresos,
                    'neto': ingresos - egresos,
                    'movimientos': int(item.get('movimientos') or 0),
                }
            )

        top_conceptos_raw = movimientos_qs.values(
            'concepto_id',
            'concepto__nombre',
            'concepto__tipo',
            'concepto__categoria__nombre',
            'concepto__categoria__clave',
        ).annotate(
            monto_total=Sum('monto'),
            movimientos=Count('id'),
        ).order_by('-monto_total')[:15]

        top_conceptos = [
            {
                'concepto_id': item.get('concepto_id'),
                'concepto_nombre': item.get('concepto__nombre') or 'SIN CONCEPTO',
                'concepto_tipo': item.get('concepto__tipo') or 'SIN TIPO',
                'categoria_nombre': item.get('concepto__categoria__nombre') or 'SIN CATEGORIA',
                'categoria_clave': item.get('concepto__categoria__clave') or '',
                'monto_total': _a_flotante(item.get('monto_total')),
                'movimientos': int(item.get('movimientos') or 0),
            }
            for item in top_conceptos_raw
        ]

        longitud_periodo = dias_periodo
        fecha_inicio_anterior = fecha_inicio - timedelta(days=longitud_periodo)
        fecha_fin_anterior = fecha_inicio - timedelta(days=1)

        movimientos_anterior_qs = MovimientoDiario.objects.filter(
            eliminado_en__isnull=True,
            reporte__eliminado_en__isnull=True,
            reporte__fecha_contable__range=(fecha_inicio_anterior, fecha_fin_anterior),
        )

        if sucursal_id:
            movimientos_anterior_qs = movimientos_anterior_qs.filter(reporte__sucursal_id=sucursal_id)
        if categorias_filtradas:
            movimientos_anterior_qs = movimientos_anterior_qs.filter(concepto__categoria_id__in=categorias_filtradas)
        if tipo_concepto != 'TODOS':
            movimientos_anterior_qs = movimientos_anterior_qs.filter(concepto__tipo=tipo_concepto)

        totales_anterior = movimientos_anterior_qs.aggregate(
            total_ingresos=Sum('monto', filter=Q(concepto__tipo='INGRESO')),
            total_egresos=Sum('monto', filter=Q(concepto__tipo='EGRESO')),
            total_movimientos=Count('id'),
        )

        ingresos_anterior = _a_flotante(totales_anterior.get('total_ingresos'))
        egresos_anterior = _a_flotante(totales_anterior.get('total_egresos'))
        neto_anterior = ingresos_anterior - egresos_anterior

        catalogo_sucursales = list(
            Sucursal.objects.filter(eliminado_en__isnull=True, estado='ACTIVO')
            .values('id', 'nombre', 'clave')
            .order_by('nombre')
        )
        catalogo_categorias = list(
            CategoriaOperativa.objects.filter(eliminado_en__isnull=True, estado='ACTIVO')
            .values('id', 'nombre', 'clave', 'tipo')
            .order_by('nombre')
        )

        data = {
            'filtros_aplicados': {
                'fecha': fecha_unica.isoformat() if fecha_unica else None,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat(),
                'sucursal_id': sucursal_id,
                'categoria_ids': categorias_filtradas,
                'tipo_concepto': tipo_concepto,
                'dias_periodo': dias_periodo,
                'dias_con_movimientos': dias_con_movimientos,
            },
            'catalogos': {
                'sucursales': catalogo_sucursales,
                'categorias': catalogo_categorias,
                'tipos_concepto': [
                    {'label': 'Todos', 'value': 'TODOS'},
                    {'label': 'Ingresos', 'value': 'INGRESO'},
                    {'label': 'Egresos', 'value': 'EGRESO'},
                ],
            },
            'resumen_general': {
                'total_movimientos': total_movimientos,
                'total_ingresos': total_ingresos,
                'total_egresos': total_egresos,
                'resultado_neto': resultado_neto,
                'ticket_promedio': ticket_promedio,
                'promedio_diario_neto': promedio_diario_neto,
                'ratio_ingresos_egresos': round((total_ingresos / total_egresos), 4) if total_egresos else None,
                'mejor_dia': mejor_dia,
                'peor_dia': peor_dia,
                'distribucion_tipo': [
                    {
                        'tipo': 'INGRESO',
                        'movimientos': int(totales.get('total_movimientos_ingresos') or 0),
                        'monto': total_ingresos,
                    },
                    {
                        'tipo': 'EGRESO',
                        'movimientos': int(totales.get('total_movimientos_egresos') or 0),
                        'monto': total_egresos,
                    },
                ],
            },
            'comparativo_periodo_anterior': {
                'fecha_inicio': fecha_inicio_anterior.isoformat(),
                'fecha_fin': fecha_fin_anterior.isoformat(),
                'total_movimientos': int(totales_anterior.get('total_movimientos') or 0),
                'total_ingresos': ingresos_anterior,
                'total_egresos': egresos_anterior,
                'resultado_neto': neto_anterior,
                'variacion_porcentual': {
                    'ingresos': _variacion_porcentual(total_ingresos, ingresos_anterior),
                    'egresos': _variacion_porcentual(total_egresos, egresos_anterior),
                    'resultado_neto': _variacion_porcentual(resultado_neto, neto_anterior),
                },
            },
            'series': {
                'por_dia': por_dia,
                'por_categoria': por_categoria,
                'por_rubro': por_rubro,
                'por_sucursal': por_sucursal,
                'top_conceptos': top_conceptos,
            },
        }

        return respuesta_estandar(data=data, mensaje="Estadísticas operativas obtenidas correctamente.")

