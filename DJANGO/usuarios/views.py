from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate, login as iniciar_sesion_django, logout as cerrar_sesion_django
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Rol, Permiso, RolPermiso, Usuario, UsuarioRol
from .serializers import (
    RolSerializer, PermisoSerializer, RolPermisoSerializer,
    UsuarioSerializer, UsuarioListSerializer, UsuarioRolSerializer,
)


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


def construir_datos_sesion(usuario):
    """Estructura estandar para exponer datos de la sesion autenticada."""
    roles = list(
        usuario.usuario_roles.select_related('rol').values(
            'rol__id',
            'rol__nombre'
        )
    )
    permisos = list(
        Permiso.objects.filter(
            rol_permisos__rol__usuario_roles__usuario=usuario
        ).distinct().values('id', 'codigo', 'nombre', 'modulo')
    )

    return {
        "usuario": {
            "id": usuario.id,
            "username": usuario.username,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
        },
        "roles": [
            {"id": rol['rol__id'], "nombre": rol['rol__nombre']}
            for rol in roles
        ],
        "permisos": permisos,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PERMISOS
# ─────────────────────────────────────────────────────────────────────────────
class PermisoViewSet(viewsets.ViewSet):
    """CRUD completo para Permiso."""

    def list(self, request):
        return respuesta_estandar(data=PermisoSerializer(Permiso.objects.all(), many=True).data, mensaje="Permisos obtenidos.")

    def create(self, request):
        s = PermisoSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Permiso creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear permiso.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=PermisoSerializer(get_object_or_404(Permiso, pk=pk)).data, mensaje="Permiso obtenido.")

    def update(self, request, pk=None):
        s = PermisoSerializer(get_object_or_404(Permiso, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Permiso actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = PermisoSerializer(get_object_or_404(Permiso, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Permiso actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        get_object_or_404(Permiso, pk=pk).eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Permiso eliminado (baja lógica).")


# ─────────────────────────────────────────────────────────────────────────────
#  ROLES
# ─────────────────────────────────────────────────────────────────────────────
class RolViewSet(viewsets.ViewSet):
    """CRUD completo para Rol con acciones para gestionar sus permisos."""

    def list(self, request):
        return respuesta_estandar(data=RolSerializer(Rol.objects.all(), many=True).data, mensaje="Roles obtenidos.")

    def create(self, request):
        s = RolSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Rol creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear rol.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=RolSerializer(get_object_or_404(Rol, pk=pk)).data, mensaje="Rol obtenido.")

    def update(self, request, pk=None):
        s = RolSerializer(get_object_or_404(Rol, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Rol actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = RolSerializer(get_object_or_404(Rol, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Rol actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        get_object_or_404(Rol, pk=pk).eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Rol eliminado (baja lógica).")

    # Asignar / quitar permiso a un rol
    @action(detail=True, methods=['post'], url_path='asignar-permiso')
    def asignar_permiso(self, request, pk=None):
        rol = get_object_or_404(Rol, pk=pk)
        s = RolPermisoSerializer(data={**request.data, 'rol': rol.pk})
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Permiso asignado al rol.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al asignar permiso.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='quitar-permiso/(?P<permiso_id>[^/.]+)')
    def quitar_permiso(self, request, pk=None, permiso_id=None):
        rp = get_object_or_404(RolPermiso, rol_id=pk, permiso_id=permiso_id)
        rp.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Permiso removido del rol (baja lógica).")


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIOS
# ─────────────────────────────────────────────────────────────────────────────
class UsuarioViewSet(viewsets.ViewSet):
    """CRUD completo para Usuario con gestión de roles."""

    @action(detail=False, methods=['get'], url_path='csrf', permission_classes=[AllowAny])
    @ensure_csrf_cookie
    def csrf(self, request):
        """Inicializa la cookie CSRF para autenticacion por sesion."""
        return respuesta_estandar(
            data={"csrf_cookie": "ok"},
            mensaje="Cookie CSRF configurada."
        )

    @action(detail=False, methods=['post'], url_path='iniciar-sesion', permission_classes=[AllowAny])
    def iniciar_sesion(self, request):
        """Autentica por username o correo y abre sesion nativa de Django."""
        identificador = (request.data.get('identificador') or '').strip()
        password = request.data.get('password')

        if not identificador or not password:
            return respuesta_estandar(
                data={"identificador": ["El identificador es requerido."], "password": ["La contraseña es requerida."]},
                mensaje="Credenciales incompletas.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        usuario_obj = Usuario.objects.filter(
            Q(username__iexact=identificador) | Q(correo__iexact=identificador),
            is_active=True
        ).first()

        if not usuario_obj:
            return respuesta_estandar(
                mensaje="Usuario o contraseña inválidos.",
                estado="error",
                codigo=status.HTTP_401_UNAUTHORIZED
            )

        usuario_autenticado = authenticate(request, username=usuario_obj.username, password=password)
        if not usuario_autenticado:
            return respuesta_estandar(
                mensaje="Usuario o contraseña inválidos.",
                estado="error",
                codigo=status.HTTP_401_UNAUTHORIZED
            )

        iniciar_sesion_django(request, usuario_autenticado)
        return respuesta_estandar(
            data=construir_datos_sesion(usuario_autenticado),
            mensaje="Sesión iniciada correctamente.",
            codigo=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='cerrar-sesion')
    def cerrar_sesion(self, request):
        """Cierra la sesion autenticada actual."""
        cerrar_sesion_django(request)
        return respuesta_estandar(mensaje="Sesión cerrada correctamente.")

    @action(detail=False, methods=['get'], url_path='sesion-actual', permission_classes=[AllowAny])
    def sesion_actual(self, request):
        """Devuelve datos de la sesion actual o 401 si no hay autenticacion."""
        if not request.user or not request.user.is_authenticated:
            return respuesta_estandar(
                mensaje="No hay sesión activa.",
                estado="error",
                codigo=status.HTTP_401_UNAUTHORIZED
            )

        return respuesta_estandar(
            data=construir_datos_sesion(request.user),
            mensaje="Sesión activa obtenida."
        )

    def list(self, request):
        return respuesta_estandar(data=UsuarioListSerializer(Usuario.objects.all(), many=True).data, mensaje="Usuarios obtenidos.")

    def create(self, request):
        s = UsuarioSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Usuario creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear usuario.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=UsuarioSerializer(get_object_or_404(Usuario, pk=pk)).data, mensaje="Usuario obtenido.")

    def update(self, request, pk=None):
        s = UsuarioSerializer(get_object_or_404(Usuario, pk=pk), data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Usuario actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = UsuarioSerializer(get_object_or_404(Usuario, pk=pk), data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Usuario actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        usuario = get_object_or_404(Usuario, pk=pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return respuesta_estandar(mensaje="Usuario desactivado correctamente.")

    # Asignar / quitar rol a un usuario
    @action(detail=True, methods=['post'], url_path='asignar-rol')
    def asignar_rol(self, request, pk=None):
        usuario = get_object_or_404(Usuario, pk=pk)
        s = UsuarioRolSerializer(data={**request.data, 'usuario': usuario.pk})
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Rol asignado al usuario.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al asignar rol.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='quitar-rol/(?P<rol_id>[^/.]+)')
    def quitar_rol(self, request, pk=None, rol_id=None):
        ur = get_object_or_404(UsuarioRol, usuario_id=pk, rol_id=rol_id)
        ur.delete()
        return respuesta_estandar(mensaje="Rol removido del usuario.")


# ─────────────────────────────────────────────────────────────────────────────
#  ROL ↔ PERMISO  (tabla intermedia — CRUD directo)
# ─────────────────────────────────────────────────────────────────────────────
class RolPermisoViewSet(viewsets.ViewSet):
    """CRUD directo sobre la tabla intermedia Rol ↔ Permiso."""

    def list(self, request):
        return respuesta_estandar(data=RolPermisoSerializer(RolPermiso.objects.all(), many=True).data, mensaje="Asignaciones Rol-Permiso obtenidas.")

    def create(self, request):
        s = RolPermisoSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Permiso asignado al rol.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al asignar permiso al rol.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=RolPermisoSerializer(get_object_or_404(RolPermiso, pk=pk)).data, mensaje="Asignación Rol-Permiso obtenida.")

    def destroy(self, request, pk=None):
        instancia = get_object_or_404(RolPermiso, pk=pk)
        instancia.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Asignación Rol-Permiso eliminada (baja lógica).")


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIO ↔ ROL  (tabla intermedia — CRUD directo)
# ─────────────────────────────────────────────────────────────────────────────
class UsuarioRolViewSet(viewsets.ViewSet):
    """CRUD directo sobre la tabla intermedia Usuario ↔ Rol."""

    def list(self, request):
        return respuesta_estandar(data=UsuarioRolSerializer(UsuarioRol.objects.all(), many=True).data, mensaje="Asignaciones Usuario-Rol obtenidas.")

    def create(self, request):
        s = UsuarioRolSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Rol asignado al usuario.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al asignar rol al usuario.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=UsuarioRolSerializer(get_object_or_404(UsuarioRol, pk=pk)).data, mensaje="Asignación Usuario-Rol obtenida.")

    def destroy(self, request, pk=None):
        get_object_or_404(UsuarioRol, pk=pk).delete()
        return respuesta_estandar(mensaje="Asignación Usuario-Rol eliminada.")

