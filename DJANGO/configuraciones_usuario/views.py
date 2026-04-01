from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ConfiguracionUsuario
from .serializers import ConfiguracionUsuarioSerializer


# 1) Para qué sirve: devolver respuestas homogéneas en configuración de usuario.
# 2) Cómo funciona: encapsula data/mensaje/estado en formato estándar.
# 3) Qué hace: simplifica consumo del frontend de preferencias.
# 4) Cómo editarla: ajusta el contrato de salida aquí cuando se redefine estándar API.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: administrar preferencias visuales y de experiencia por usuario.
# 2) Cómo funciona: ofrece endpoints para ver, actualizar y restablecer configuración propia.
# 3) Qué hace: separa permisos de autoservicio y consulta administrativa.
# 4) Cómo editarla: agrega nuevas preferencias en serializer/modelo y ajusta flujo mi_configuracion.
class ConfiguracionUsuarioViewSet(viewsets.ViewSet):
    """
    ViewSet para las preferencias de interfaz del usuario autenticado.

    Diseño centrado en el usuario actual:
    - GET  /mi-configuracion/  → Devuelve (o crea) la configuración del usuario autenticado.
    - PATCH /mi-configuracion/ → Actualiza parcialmente la configuración del usuario autenticado.
    - POST  /mi-configuracion/restablecer/ → Restablece todos los valores a los defaults del sistema.

    Solo el ADMINISTRADOR puede listar y acceder a configuraciones de otros usuarios.
    """

    permission_classes = [IsAuthenticated]

    # ── Endpoint principal: configuración del usuario autenticado ─────────────

    @action(detail=False, methods=['get', 'patch'], url_path='mi-configuracion')
    def mi_configuracion(self, request):
        """
        GET  → Devuelve la configuración del usuario autenticado.
               Si aún no existe, la crea automáticamente con los valores por defecto.
        PATCH → Actualiza parcialmente los campos enviados en el body.
                El campo 'usuario' es ignorado; siempre aplica al usuario autenticado.
        """
        config, creada = ConfiguracionUsuario.objects.get_or_create(
            usuario=request.user
        )

        if request.method == 'GET':
            mensaje = "Configuración creada con valores por defecto." if creada else "Configuración de usuario obtenida."
            return respuesta_estandar(
                data=ConfiguracionUsuarioSerializer(config).data,
                mensaje=mensaje,
                codigo=status.HTTP_201_CREATED if creada else status.HTTP_200_OK
            )

        # PATCH
        serializer = ConfiguracionUsuarioSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(
                data=serializer.data,
                mensaje="Configuración actualizada correctamente."
            )
        return respuesta_estandar(
            data=serializer.errors,
            mensaje="Error al actualizar la configuración.",
            estado="error",
            codigo=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'], url_path='mi-configuracion/restablecer')
    def restablecer(self, request):
        """
        Restablece la configuración del usuario autenticado a los valores
        por defecto del sistema. Elimina la entrada actual y la recrea limpia.
        """
        ConfiguracionUsuario.objects.filter(usuario=request.user).delete()
        config = ConfiguracionUsuario.objects.create(
            usuario=request.user,
            creado_por=request.user
        )
        return respuesta_estandar(
            data=ConfiguracionUsuarioSerializer(config).data,
            mensaje="Configuración restablecida a los valores por defecto.",
            codigo=status.HTTP_200_OK
        )

    # ── Endpoints administrativos (lista/detalle de cualquier usuario) ────────

    def list(self, request):
        """
        Lista todas las configuraciones de usuario.
        Solo accesible para ADMINISTRADOR o is_superuser.
        """
        if not (request.user.is_superuser or _es_administrador(request.user)):
            return respuesta_estandar(
                mensaje="No tiene permisos para listar configuraciones de otros usuarios.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )
        qs = ConfiguracionUsuario.objects.select_related('usuario').all()
        return respuesta_estandar(
            data=ConfiguracionUsuarioSerializer(qs, many=True).data,
            mensaje="Configuraciones de usuario obtenidas."
        )

    def retrieve(self, request, pk=None):
        """
        Detalle de la configuración de un usuario específico por ID.
        El usuario autenticado solo puede ver su propia configuración,
        salvo que sea ADMINISTRADOR.
        """
        try:
            config = ConfiguracionUsuario.objects.select_related('usuario').get(pk=pk)
        except ConfiguracionUsuario.DoesNotExist:
            return respuesta_estandar(
                mensaje="Configuración no encontrada.",
                estado="error",
                codigo=status.HTTP_404_NOT_FOUND
            )

        if config.usuario != request.user and not (request.user.is_superuser or _es_administrador(request.user)):
            return respuesta_estandar(
                mensaje="No tiene permisos para ver la configuración de otro usuario.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        return respuesta_estandar(
            data=ConfiguracionUsuarioSerializer(config).data,
            mensaje="Configuración obtenida."
        )


# 1) Para qué sirve: validar de forma reusable si un usuario posee rol ADMINISTRADOR.
# 2) Cómo funciona: consulta relación usuario_roles con comparación case-insensitive.
# 3) Qué hace: devuelve bool para autorizar endpoints administrativos.
# 4) Cómo editarla: cambia el criterio aquí si la estrategia de roles evoluciona.
def _es_administrador(usuario):
    """Verifica si el usuario tiene el rol ADMINISTRADOR."""
    try:
        return usuario.usuario_roles.filter(rol__nombre__iexact='ADMINISTRADOR').exists()
    except Exception:
        return False
