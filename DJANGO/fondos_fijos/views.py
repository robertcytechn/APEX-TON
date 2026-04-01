from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import FondoFijo, SucursalFondoFijo
from .serializers import FondoFijoSerializer, SucursalFondoFijoSerializer


# 1) Para qué sirve: unificar respuestas JSON del módulo de fondos fijos.
# 2) Cómo funciona: retorna estructura status/message/data con código configurable.
# 3) Qué hace: estandariza respuestas para altas, consultas y errores.
# 4) Cómo editarla: actualiza formato aquí si cambia la norma de contrato API.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: administrar catálogo de fondos fijos disponibles.
# 2) Cómo funciona: implementa CRUD del modelo FondoFijo con baja lógica.
# 3) Qué hace: permite crear y mantener fondos base para asignación por sucursal.
# 4) Cómo editarla: incluye validaciones de negocio en create/update según reglas financieras.
class FondoFijoViewSet(viewsets.ViewSet):
    """CRUD completo para FondoFijo."""

    def list(self, request):
        queryset = FondoFijo.objects.all()
        serializer = FondoFijoSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Fondos fijos obtenidos correctamente.")

    def create(self, request):
        serializer = FondoFijoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Fondo fijo creado correctamente.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje="Error al crear el fondo fijo.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(FondoFijo, pk=pk)
        serializer = FondoFijoSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Fondo fijo obtenido correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(FondoFijo, pk=pk)
        serializer = FondoFijoSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Fondo fijo actualizado correctamente.")
        return respuesta_estandar(data=serializer.errors, mensaje="Error al actualizar el fondo fijo.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(FondoFijo, pk=pk)
        serializer = FondoFijoSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Fondo fijo actualizado parcialmente.")
        return respuesta_estandar(data=serializer.errors, mensaje="Error al actualizar parcialmente.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(FondoFijo, pk=pk)
        usuario = request.user if request.user.is_authenticated else None
        instancia.eliminar_logico(usuario=usuario)
        return respuesta_estandar(data=None, mensaje="Fondo fijo eliminado correctamente (baja lógica).")


# 1) Para qué sirve: administrar asignaciones de fondos fijos por sucursal.
# 2) Cómo funciona: CRUD de la relación SucursalFondoFijo con datos relacionados.
# 3) Qué hace: define qué fondo aplica a cada sucursal y en qué monto/configuración.
# 4) Cómo editarla: agrega reglas de unicidad o vigencia en create/update según operación.
class SucursalFondoFijoViewSet(viewsets.ViewSet):
    """CRUD completo para la asignación de fondos fijos por sucursal."""

    def list(self, request):
        queryset = SucursalFondoFijo.objects.select_related('sucursal', 'fondo_fijo').all()
        serializer = SucursalFondoFijoSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Asignaciones de fondos fijos obtenidas correctamente.")

    def create(self, request):
        serializer = SucursalFondoFijoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Asignación de fondo fijo creada correctamente.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje="Error al crear la asignación de fondo fijo.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(SucursalFondoFijo, pk=pk)
        serializer = SucursalFondoFijoSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Asignación de fondo fijo obtenida correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(SucursalFondoFijo, pk=pk)
        serializer = SucursalFondoFijoSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Asignación de fondo fijo actualizada correctamente.")
        return respuesta_estandar(data=serializer.errors, mensaje="Error al actualizar la asignación de fondo fijo.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(SucursalFondoFijo, pk=pk)
        serializer = SucursalFondoFijoSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Asignación de fondo fijo actualizada parcialmente.")
        return respuesta_estandar(data=serializer.errors, mensaje="Error al actualizar parcialmente la asignación.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(SucursalFondoFijo, pk=pk)
        usuario = request.user if request.user.is_authenticated else None
        instancia.eliminar_logico(usuario=usuario)
        return respuesta_estandar(data=None, mensaje="Asignación de fondo fijo eliminada correctamente (baja lógica).")
