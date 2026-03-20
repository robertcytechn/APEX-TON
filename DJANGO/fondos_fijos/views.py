from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import FondoFijo
from .serializers import FondoFijoSerializer


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


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
