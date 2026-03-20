from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Sucursal
from .serializers import SucursalSerializer, SucursalListSerializer


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    """Genera una respuesta JSON estandarizada conforme a las reglas del proyecto."""
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


class SucursalViewSet(viewsets.ViewSet):
    """
    CRUD completo para Sucursal con acciones de ciclo de vida.
      list        → GET    /sucursales/
      create      → POST   /sucursales/
      retrieve    → GET    /sucursales/{id}/
      update      → PUT    /sucursales/{id}/
      partial     → PATCH  /sucursales/{id}/
      destroy     → DELETE /sucursales/{id}/   (soft-delete)
      activar     → POST   /sucursales/{id}/activar/
      desactivar  → POST   /sucursales/{id}/desactivar/
      bloquear    → POST   /sucursales/{id}/bloquear/
    """

    def list(self, request):
        queryset = Sucursal.objects.all()
        serializer = SucursalListSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Sucursales obtenidas correctamente.")

    def create(self, request):
        serializer = SucursalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(
                data=serializer.data,
                mensaje="Sucursal creada correctamente.",
                codigo=status.HTTP_201_CREATED
            )
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al crear la sucursal.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Sucursal obtenida correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Sucursal actualizada correctamente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar la sucursal.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Sucursal actualizada parcialmente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar parcialmente la sucursal.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        """Eliminación lógica — nunca borra el registro físicamente."""
        instancia = get_object_or_404(Sucursal, pk=pk)
        usuario = request.user if request.user.is_authenticated else None
        instancia.eliminar_logico(usuario=usuario)
        return respuesta_estandar(data=None, mensaje="Sucursal eliminada correctamente (baja lógica).")

    # ── Acciones de ciclo de vida ─────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        instancia = get_object_or_404(Sucursal.todos, pk=pk)
        instancia.activar()
        return respuesta_estandar(
            data=SucursalSerializer(instancia).data,
            mensaje=f"Sucursal '{instancia.nombre}' activada correctamente."
        )

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        instancia = get_object_or_404(Sucursal, pk=pk)
        instancia.desactivar()
        return respuesta_estandar(
            data=SucursalSerializer(instancia).data,
            mensaje=f"Sucursal '{instancia.nombre}' desactivada correctamente."
        )

    @action(detail=True, methods=['post'], url_path='bloquear')
    def bloquear(self, request, pk=None):
        instancia = get_object_or_404(Sucursal, pk=pk)
        instancia.bloquear()
        return respuesta_estandar(
            data=SucursalSerializer(instancia).data,
            mensaje=f"Sucursal '{instancia.nombre}' bloqueada correctamente."
        )
