from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from configuraciones_globales.models import ConfiguracionGlobal, PadreRubroContable, RubroContable
from core.permisos import EsAdministrador, EsDirector
from fondos_fijos.models import FondoFijo
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario
from usuarios.servicios_correo_credenciales import enviar_correo_credenciales_usuario

from .serializers import (
    ConfiguracionGlobalCabinaSerializer,
    ConfiguracionGlobalDirectorCabinaSerializer,
    PadreRubroContableCabinaSerializer,
    RolCabinaSerializer,
    RubroContableCabinaSerializer,
    SucursalDirectorCabinaSerializer,
    SucursalCabinaSerializer,
    UsuarioDirectorCabinaSerializer,
    UsuarioCabinaSerializer,
)


def respuesta_estandar(data=None, mensaje='Operacion exitosa', estado='success', codigo=status.HTTP_200_OK):
    return Response({'status': estado, 'message': mensaje, 'data': data}, status=codigo)


class BaseCabinaAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, EsAdministrador]


class BaseCabinaDirectorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, EsDirector]


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
    @action(detail=False, methods=['get'], url_path='opciones')
    def opciones(self, request):
        campo_tipo = RubroContable._meta.get_field('tipo')

        opciones_padre = [
            {
                'id': padre.id,
                'label': padre.nombre,
                'value': padre.id,
                'clave': padre.clave,
                'nombre': padre.nombre,
            }
            for padre in PadreRubroContable.objects.all().order_by('nombre')
        ]
        opciones_tipo = [{'label': etiqueta, 'value': valor} for valor, etiqueta in campo_tipo.choices]

        data = {
            'padres': opciones_padre,
            'tipos': opciones_tipo,
        }
        return respuesta_estandar(data=data, mensaje='Opciones de rubro contable obtenidas.')

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


class PadreRubroContableCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = PadreRubroContableCabinaSerializer(PadreRubroContable.objects.all().order_by('nombre'), many=True).data
        return respuesta_estandar(data=data, mensaje='Padres de rubro contable obtenidos.')

    def create(self, request):
        serializer = PadreRubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        return respuesta_estandar(data=PadreRubroContableCabinaSerializer(obj).data, mensaje='Padre de rubro contable obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        if obj.rubros_contables.exists():
            return respuesta_estandar(
                data={'rubros_asociados': obj.rubros_contables.count()},
                mensaje='No se puede eliminar el padre porque tiene rubros contables asociados.',
                estado='error',
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Padre de rubro contable eliminado (baja logica).')


class FondoFijoDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def list(self, request):
        data = [
            {
                'id': fondo.id,
                'nombre': fondo.nombre,
                'descripcion': fondo.descripcion,
            }
            for fondo in FondoFijo.objects.all().order_by('nombre')
        ]
        return respuesta_estandar(data=data, mensaje='Catalogo de fondos fijos obtenido.')


class SucursalDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def list(self, request):
        queryset = Sucursal.objects.all().prefetch_related('asignaciones_fondos_fijos__fondo_fijo')
        data = SucursalDirectorCabinaSerializer(queryset, many=True).data
        return respuesta_estandar(data=data, mensaje='Sucursales obtenidas para cabina de director.')

    def create(self, request):
        serializer = SucursalDirectorCabinaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal creada y fondos fijos asignados.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear sucursal para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Sucursal.objects.prefetch_related('asignaciones_fondos_fijos__fondo_fijo'), pk=pk)
        return respuesta_estandar(data=SucursalDirectorCabinaSerializer(obj).data, mensaje='Sucursal obtenida para cabina de director.')


class UsuarioDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def obtener_queryset_operativos(self):
        return Usuario.objects.select_related('sucursal').filter(
            Q(usuario_roles__rol__nombre__iexact='CONTADOR') | Q(usuario_roles__rol__nombre__iexact='GERENTE')
        ).distinct()

    @action(detail=False, methods=['get'], url_path='roles-disponibles')
    def roles_disponibles(self, request):
        roles = Rol.objects.filter(
            Q(nombre__iexact='CONTADOR') | Q(nombre__iexact='GERENTE')
        ).order_by('nombre')
        data = [{'id': rol.id, 'nombre': rol.nombre} for rol in roles]
        return respuesta_estandar(data=data, mensaje='Roles disponibles para director obtenidos.')

    def list(self, request):
        queryset = self.obtener_queryset_operativos()
        data = UsuarioDirectorCabinaSerializer(queryset, many=True).data
        return respuesta_estandar(data=data, mensaje='Usuarios de captura operativa obtenidos.')

    def create(self, request):
        serializer = UsuarioDirectorCabinaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            usuario = serializer.save()
            contrasena_generada = getattr(serializer, '_contrasena_generada', None)

            resultado_correo = enviar_correo_credenciales_usuario(
                usuario=usuario,
                contrasena_visible=contrasena_generada,
                es_reinicio=False,
            )

            data = UsuarioDirectorCabinaSerializer(
                usuario,
                context={'contrasena_generada': contrasena_generada}
            ).data
            data['correo_enviado'] = resultado_correo.get('enviado', False)
            data['detalle_correo'] = resultado_correo.get('error', '')

            mensaje = 'Usuario creado para captura operativa y correo enviado.'
            if not data['correo_enviado']:
                mensaje = 'Usuario creado para captura operativa, pero no se pudo enviar el correo.'

            return respuesta_estandar(data=data, mensaje=mensaje, codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear usuario para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        data = UsuarioDirectorCabinaSerializer(obj).data
        return respuesta_estandar(data=data, mensaje='Usuario operativo obtenido para director.')

    def update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        serializer = UsuarioDirectorCabinaSerializer(obj, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario operativo actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario operativo.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        serializer = UsuarioDirectorCabinaSerializer(obj, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario operativo actualizado parcialmente para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar parcialmente usuario operativo.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reiniciar-password')
    def reiniciar_password(self, request, pk=None):
        usuario = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)

        contrasena_generada = UsuarioDirectorCabinaSerializer.generar_contrasena_numerica()
        usuario.set_password(contrasena_generada)
        usuario.requiere_cambio_password = True
        usuario.actualizado_por = request.user
        usuario.save(update_fields=['password', 'requiere_cambio_password', 'actualizado_por', 'actualizado_en'])

        resultado_correo = enviar_correo_credenciales_usuario(
            usuario=usuario,
            contrasena_visible=contrasena_generada,
            es_reinicio=True,
        )

        data = UsuarioDirectorCabinaSerializer(
            usuario,
            context={'contrasena_generada': contrasena_generada}
        ).data
        data['correo_enviado'] = resultado_correo.get('enviado', False)
        data['detalle_correo'] = resultado_correo.get('error', '')

        mensaje = 'Contrasena reiniciada y correo enviado al usuario.'
        if not data['correo_enviado']:
            mensaje = 'Contrasena reiniciada, pero no se pudo enviar el correo al usuario.'

        return respuesta_estandar(data=data, mensaje=mensaje)


class ConfiguracionGlobalDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def list(self, request):
        data = ConfiguracionGlobalDirectorCabinaSerializer(ConfiguracionGlobal.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Configuraciones globales obtenidas para director.')

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        return respuesta_estandar(data=ConfiguracionGlobalDirectorCabinaSerializer(obj).data, mensaje='Configuracion global obtenida para director.')

    def create(self, request):
        return respuesta_estandar(
            mensaje='No tienes permiso para crear variables globales.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )

    def update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalDirectorCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Valor de configuracion global actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar valor de configuracion.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalDirectorCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Valor de configuracion global actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar valor de configuracion.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        return respuesta_estandar(
            mensaje='No tienes permiso para eliminar variables globales.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )


class RubroContableDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    @action(detail=False, methods=['get'], url_path='opciones')
    def opciones(self, request):
        campo_tipo = RubroContable._meta.get_field('tipo')

        opciones_padre = [
            {
                'id': padre.id,
                'label': padre.nombre,
                'value': padre.id,
                'clave': padre.clave,
                'nombre': padre.nombre,
            }
            for padre in PadreRubroContable.objects.all().order_by('nombre')
        ]
        opciones_tipo = [{'label': etiqueta, 'value': valor} for valor, etiqueta in campo_tipo.choices]

        data = {
            'padres': opciones_padre,
            'tipos': opciones_tipo,
        }
        return respuesta_estandar(data=data, mensaje='Opciones de rubro contable obtenidas para director.')

    def list(self, request):
        data = RubroContableCabinaSerializer(RubroContable.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Rubros contables obtenidos para director.')

    def create(self, request):
        serializer = RubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable creado para director.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        return respuesta_estandar(data=RubroContableCabinaSerializer(obj).data, mensaje='Rubro contable obtenido para director.')

    def update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        return respuesta_estandar(
            mensaje='No tienes permiso para eliminar rubros contables desde cabina de director.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )
