from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ConfiguracionGlobal, PadreRubroContable, RubroContable
from .serializers import (
    ConfiguracionGlobalSerializer,
    PadreRubroContableSerializer,
    RubroContableSerializer,
)


# 1) Para qué sirve: aplicar formato estándar de respuesta para configuraciones globales.
# 2) Cómo funciona: retorna status/message/data con código HTTP configurable.
# 3) Qué hace: uniforma contratos de éxito y error de este módulo.
# 4) Cómo editarla: ajusta estructura aquí si cambia la convención global de API.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    """Genera una respuesta JSON estandarizada conforme a las reglas del proyecto."""
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# ─────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────

# 1) Para qué sirve: administrar variables globales consumidas por todo el sistema.
# 2) Cómo funciona: expone CRUD directo del modelo ConfiguracionGlobal.
# 3) Qué hace: permite alta/edición de parámetros como tipos de cambio u horarios.
# 4) Cómo editarla: agrega validaciones de negocio en create/update si se vuelven obligatorias.
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

# 1) Para qué sirve: administrar catálogo global de rubros contables.
# 2) Cómo funciona: provee CRUD para el modelo RubroContable.
# 3) Qué hace: habilita clasificación contable para consolidación de resultados.
# 4) Cómo editarla: integra reglas jerárquicas de padre/tipo dentro de create/update.
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


class PadreRubroContableViewSet(viewsets.ViewSet):
    """
    CRUD completo para PadreRubroContable.
      list    -> GET    /padres-rubros/
      create  -> POST   /padres-rubros/
      retrieve-> GET    /padres-rubros/{id}/
      update  -> PUT    /padres-rubros/{id}/
      partial -> PATCH  /padres-rubros/{id}/
      destroy -> DELETE /padres-rubros/{id}/
    """

    def list(self, request):
        queryset = PadreRubroContable.objects.all().order_by('nombre')
        serializer = PadreRubroContableSerializer(queryset, many=True)
        return respuesta_estandar(data=serializer.data, mensaje="Padres de rubro obtenidos correctamente.")

    def create(self, request):
        serializer = PadreRubroContableSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(
                data=serializer.data,
                mensaje="Padre de rubro creado correctamente.",
                codigo=status.HTTP_201_CREATED
            )
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al crear el padre de rubro.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        instancia = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableSerializer(instancia)
        return respuesta_estandar(data=serializer.data, mensaje="Padre de rubro obtenido correctamente.")

    def update(self, request, pk=None):
        instancia = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableSerializer(instancia, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Padre de rubro actualizado correctamente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar el padre de rubro.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def partial_update(self, request, pk=None):
        instancia = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableSerializer(instancia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje="Padre de rubro actualizado parcialmente.")
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar parcialmente el padre de rubro.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(PadreRubroContable, pk=pk)
        if instancia.rubros_contables.exists():
            return respuesta_estandar(
                data={"rubros_asociados": instancia.rubros_contables.count()},
                mensaje="No se puede eliminar el padre porque tiene rubros contables asociados.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        instancia.delete()
        return respuesta_estandar(data=None, mensaje="Padre de rubro eliminado correctamente.")
