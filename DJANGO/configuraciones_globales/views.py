from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ConfiguracionGlobal, RubroContable
from .serializers import ConfiguracionGlobalSerializer, RubroContableSerializer


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    """Genera una respuesta JSON estandarizada conforme a las reglas del proyecto."""
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# ─────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────

class ConfiguracionGlobalViewSet(viewsets.ViewSet):
    """
    CRUD completo para ConfiguracionGlobal.
      list    → GET    /configuraciones/
      create  → POST   /configuraciones/
      retrieve→ GET    /configuraciones/{id}/
      update  → PUT    /configuraciones/{id}/
      partial → PATCH  /configuraciones/{id}/
      destroy → DELETE /configuraciones/{id}/
    """

    def list(self, request):
        queryset = ConfiguracionGlobal.objects.all()
        serializer = ConfiguracionGlobalSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Configuraciones globales obtenidas correctamente.")

    def create(self, request):
        serializer = ConfiguracionGlobalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(
                data=serializer.data,
                mensaje="Configuración global creada correctamente.",
                codigo=status.HTTP_201_CREATED
            )
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al crear la configuración global.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Configuración global obtenida correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Configuración global actualizada correctamente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar la configuración global.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Configuración global actualizada parcialmente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar parcialmente la configuración global.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(ConfiguracionGlobal, pk=pk)
        instancia.delete()
        return respuesta_estandar(data=None, mensaje="Configuración global eliminada correctamente.")


# ─────────────────────────────────────────────
#  RUBRO CONTABLE
# ─────────────────────────────────────────────

class RubroContableViewSet(viewsets.ViewSet):
    """
    CRUD completo para RubroContable.
      list    → GET    /rubros/
      create  → POST   /rubros/
      retrieve→ GET    /rubros/{id}/
      update  → PUT    /rubros/{id}/
      partial → PATCH  /rubros/{id}/
      destroy → DELETE /rubros/{id}/
    """

    def list(self, request):
        queryset = RubroContable.objects.all()
        serializer = RubroContableSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Rubros contables obtenidos correctamente.")

    def create(self, request):
        serializer = RubroContableSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(
                data=serializer.data,
                mensaje="Rubro contable creado correctamente.",
                codigo=status.HTTP_201_CREATED
            )
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al crear el rubro contable.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Rubro contable obtenido correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Rubro contable actualizado correctamente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar el rubro contable.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Rubro contable actualizado parcialmente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar parcialmente el rubro contable.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(RubroContable, pk=pk)
        instancia.delete()
        return respuesta_estandar(data=None, mensaje="Rubro contable eliminado correctamente.")
