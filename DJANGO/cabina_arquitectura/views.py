from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from configuraciones_globales.models import ConfiguracionGlobal, RubroContable
from core.permisos import EsAdministrador
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario

from .serializers import (
    ConfiguracionGlobalCabinaSerializer,
    RolCabinaSerializer,
    RubroContableCabinaSerializer,
    SucursalCabinaSerializer,
    UsuarioCabinaSerializer,
)


def respuesta_estandar(data=None, mensaje='Operacion exitosa', estado='success', codigo=status.HTTP_200_OK):
    return Response({'status': estado, 'message': mensaje, 'data': data}, status=codigo)


class BaseCabinaAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, EsAdministrador]


class RolCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = RolCabinaSerializer(Rol.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Roles obtenidos.')

    def create(self, request):
        serializer = RolCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        return respuesta_estandar(data=RolCabinaSerializer(obj).data, mensaje='Rol obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        serializer = RolCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        serializer = RolCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Rol eliminado (baja logica).')


class UsuarioCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = UsuarioCabinaSerializer(Usuario.objects.select_related('sucursal').all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Usuarios obtenidos.')

    def create(self, request):
        serializer = UsuarioCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        return respuesta_estandar(data=UsuarioCabinaSerializer(obj).data, mensaje='Usuario obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        serializer = UsuarioCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        serializer = UsuarioCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        usuario = get_object_or_404(Usuario, pk=pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return respuesta_estandar(mensaje='Usuario desactivado correctamente.')


class SucursalCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = SucursalCabinaSerializer(Sucursal.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Sucursales obtenidas.')

    def create(self, request):
        serializer = SucursalCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal creada.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        return respuesta_estandar(data=SucursalCabinaSerializer(obj).data, mensaje='Sucursal obtenida.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal actualizada.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal actualizada parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Sucursal eliminada (baja logica).')


class ConfiguracionGlobalCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = ConfiguracionGlobalCabinaSerializer(ConfiguracionGlobal.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Configuraciones globales obtenidas.')

    def create(self, request):
        serializer = ConfiguracionGlobalCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global creada.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        return respuesta_estandar(data=ConfiguracionGlobalCabinaSerializer(obj).data, mensaje='Configuracion global obtenida.')

    def update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global actualizada.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global actualizada parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Configuracion global eliminada (baja logica).')


class RubroContableCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = RubroContableCabinaSerializer(RubroContable.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Rubros contables obtenidos.')

    def create(self, request):
        serializer = RubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        return respuesta_estandar(data=RubroContableCabinaSerializer(obj).data, mensaje='Rubro contable obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Rubro contable eliminado (baja logica).')
