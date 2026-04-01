from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import CategoriaOperativa, Concepto, DetalleParametrizado
from .serializers import (
    CategoriaOperativaSerializer, CategoriaOperativaListSerializer,
    ConceptoSerializer, ConceptoListSerializer,
    DetalleParametrizadoSerializer,
)


# 1) Para qué sirve: homologar respuestas del módulo de categorías operativas.
# 2) Cómo funciona: genera objeto JSON estándar con status, message y data.
# 3) Qué hace: normaliza éxito/error para consumo de frontend administrativo.
# 4) Cómo editarla: cambia estructura aquí si el contrato API corporativo evoluciona.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# ─────────────────────────────────────────────────────────────────────────────
#  CATEGORÍA OPERATIVA
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: administrar pestañas/categorías que agrupan el flujo operativo.
# 2) Cómo funciona: expone CRUD y transiciones de estado (activar/desactivar/bloquear).
# 3) Qué hace: mantiene catálogo maestro de categorías para captura diaria.
# 4) Cómo editarla: agrega nuevas acciones de ciclo de vida como métodos @action.
class CategoriaOperativaViewSet(viewsets.ViewSet):
    """
    CRUD completo para CategoriaOperativa (Pestañas).
    El detalle de cada categoría incluye sus conceptos y detalles parametrizados anidados.
    Acciones extra:
      - activar / desactivar / bloquear → Cambios de estado de ciclo de vida.
    """

    def list(self, request):
        qs = CategoriaOperativa.objects.all()
        return respuesta_estandar(data=CategoriaOperativaListSerializer(qs, many=True).data, mensaje="Categorías operativas obtenidas.")

    def create(self, request):
        s = CategoriaOperativaSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Categoría operativa creada.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear categoría.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(CategoriaOperativa, pk=pk)
        return respuesta_estandar(data=CategoriaOperativaSerializer(obj).data, mensaje="Categoría operativa obtenida.")

    def update(self, request, pk=None):
        s = CategoriaOperativaSerializer(get_object_or_404(CategoriaOperativa, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Categoría operativa actualizada.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = CategoriaOperativaSerializer(get_object_or_404(CategoriaOperativa, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Categoría actualizada parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(CategoriaOperativa, pk=pk)
        obj.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Categoría operativa eliminada (baja lógica).")

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        obj = get_object_or_404(CategoriaOperativa.todos, pk=pk)
        obj.activar()
        return respuesta_estandar(data=CategoriaOperativaListSerializer(obj).data, mensaje=f"Categoría '{obj.nombre}' activada.")

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        obj = get_object_or_404(CategoriaOperativa, pk=pk)
        obj.desactivar()
        return respuesta_estandar(data=CategoriaOperativaListSerializer(obj).data, mensaje=f"Categoría '{obj.nombre}' desactivada.")

    @action(detail=True, methods=['post'], url_path='bloquear')
    def bloquear(self, request, pk=None):
        obj = get_object_or_404(CategoriaOperativa, pk=pk)
        obj.bloquear()
        return respuesta_estandar(data=CategoriaOperativaListSerializer(obj).data, mensaje=f"Categoría '{obj.nombre}' bloqueada.")


# ─────────────────────────────────────────────────────────────────────────────
#  CONCEPTO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: administrar conceptos transaccionales asociados a categoría.
# 2) Cómo funciona: CRUD con filtrado opcional por categoria_id en query params.
# 3) Qué hace: define unidades operativas de captura (ingreso/egreso).
# 4) Cómo editarla: incorpora validaciones por tipo o rubro antes de guardar.
class ConceptoViewSet(viewsets.ViewSet):
    """
    CRUD completo para Concepto.
    Soporta filtrado opcional por categoría via query param: ?categoria_id=<id>
    """

    def list(self, request):
        qs = Concepto.objects.all()
        categoria_id = request.query_params.get('categoria_id')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return respuesta_estandar(data=ConceptoListSerializer(qs, many=True).data, mensaje="Conceptos obtenidos.")

    def create(self, request):
        s = ConceptoSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Concepto creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear concepto.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=ConceptoSerializer(get_object_or_404(Concepto, pk=pk)).data, mensaje="Concepto obtenido.")

    def update(self, request, pk=None):
        s = ConceptoSerializer(get_object_or_404(Concepto, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Concepto actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = ConceptoSerializer(get_object_or_404(Concepto, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Concepto actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        get_object_or_404(Concepto, pk=pk).eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Concepto eliminado (baja lógica).")


# ─────────────────────────────────────────────────────────────────────────────
#  DETALLE PARAMETRIZADO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: administrar campos dinámicos por categoría operativa.
# 2) Cómo funciona: CRUD con filtro por categoria_id para carga contextual.
# 3) Qué hace: permite extender captura sin alterar esquema fijo de movimientos.
# 4) Cómo editarla: agrega validaciones de compatibilidad de tipos en create/update.
class DetalleParametrizadoViewSet(viewsets.ViewSet):
    """
    CRUD completo para DetalleParametrizado.
    Soporta filtrado opcional por categoría via query param: ?categoria_id=<id>
    """

    def list(self, request):
        qs = DetalleParametrizado.objects.all()
        categoria_id = request.query_params.get('categoria_id')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return respuesta_estandar(data=DetalleParametrizadoSerializer(qs, many=True).data, mensaje="Detalles parametrizados obtenidos.")

    def create(self, request):
        s = DetalleParametrizadoSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Detalle parametrizado creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear detalle.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=DetalleParametrizadoSerializer(get_object_or_404(DetalleParametrizado, pk=pk)).data, mensaje="Detalle obtenido.")

    def update(self, request, pk=None):
        s = DetalleParametrizadoSerializer(get_object_or_404(DetalleParametrizado, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Detalle parametrizado actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = DetalleParametrizadoSerializer(get_object_or_404(DetalleParametrizado, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Detalle actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        get_object_or_404(DetalleParametrizado, pk=pk).eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Detalle parametrizado eliminado (baja lógica).")
