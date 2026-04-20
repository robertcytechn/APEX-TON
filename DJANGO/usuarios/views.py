import logging
from uuid import uuid4

from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate, login as iniciar_sesion_django, logout as cerrar_sesion_django, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.permisos import usuario_tiene_rol
from .models import Rol, Permiso, RolPermiso, Usuario, UsuarioRol, TicketSoporteTecnico
from .serializers import (
    RolSerializer, PermisoSerializer, RolPermisoSerializer,
    UsuarioSerializer, UsuarioListSerializer, UsuarioRolSerializer,
    SolicitudSoporteTecnicoSerializer, TicketSoporteTecnicoAdminSerializer,
    TicketSoporteTecnicoSeguimientoSerializer,
)
from .servicios_correo_credenciales import normalizar_destinatarios


logger = logging.getLogger(__name__)

DESTINATARIO_SOPORTE_PRINCIPAL = 'robert-cyby@hotmail.com'
DESTINATARIO_SOPORTE_COPIA = 'robertot@gbentretenimiento.com'


# 1) Para qué sirve: mantener un formato único de respuesta para toda la app de usuarios.
# 2) Cómo funciona: empaqueta estado, mensaje y datos en la estructura estándar del proyecto.
# 3) Qué hace: simplifica control de errores y parsing consistente en frontend.
# 4) Cómo editarla: si el contrato global cambia, actualiza esta función y reutiliza en todo el módulo.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: armar el payload completo de sesión autenticada.
# 2) Cómo funciona: consulta roles/permisos del usuario y los serializa en estructura plana.
# 3) Qué hace: entrega información necesaria para control de acceso en cliente.
# 4) Cómo editarla: agrega campos nuevos de usuario, rol o permiso en el diccionario de retorno.
def construir_url_foto_perfil(usuario, request=None):
    if not getattr(usuario, 'foto_perfil', None):
        return None

    # Se devuelve ruta relativa para evitar hosts internos cuando hay proxy inverso.
    return usuario.foto_perfil.url


def construir_datos_sesion(usuario, request=None):
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
            "sucursal_id": usuario.sucursal_id,
            "sucursal_nombre": usuario.sucursal.nombre if usuario.sucursal else None,
            "foto_perfil_url": construir_url_foto_perfil(usuario, request),
            "is_superuser": usuario.is_superuser,
            "is_staff": usuario.is_staff,
            "requiere_cambio_password": usuario.requiere_cambio_password,
        },
        "roles": [
            {"id": rol['rol__id'], "nombre": rol['rol__nombre']}
            for rol in roles
        ],
        "permisos": permisos,
    }


def resolver_etiqueta_opcion(valor, opciones):
    """Resuelve etiqueta de una opción DRF ChoiceField a partir de su valor."""
    tabla = dict(opciones)
    return tabla.get(valor, valor)


def generar_folio_soporte(usuario_id):
    """Construye un folio único y legible para tickets de soporte técnico."""
    marca_tiempo = timezone.now().strftime('%Y%m%d-%H%M%S')
    sufijo = uuid4().hex[:6].upper()
    return f"ST-{marca_tiempo}-{usuario_id}-{sufijo}"


def usuario_administrador_habilitado(usuario):
    """Valida privilegios administrativos para consultas/seguimiento de tickets."""
    return usuario_tiene_rol(usuario, 'ADMINISTRADOR')


# ─────────────────────────────────────────────────────────────────────────────
#  PERMISOS
# ─────────────────────────────────────────────────────────────────────────────
# 1) Para qué sirve: administrar catálogo de permisos granulares del sistema.
# 2) Cómo funciona: expone CRUD directo sobre Permiso con serializador DRF.
# 3) Qué hace: permite alta, consulta, actualización y baja lógica de permisos.
# 4) Cómo editarla: incorpora validaciones adicionales en create/update si cambian reglas de seguridad.
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
# 1) Para qué sirve: administrar roles y sus asignaciones de permisos.
# 2) Cómo funciona: combina CRUD de Rol con acciones @action para asignar/quitar permisos.
# 3) Qué hace: centraliza autorización basada en rol según arquitectura del proyecto.
# 4) Cómo editarla: agrega nuevas acciones de gestión de permisos manteniendo respuesta_estandar.
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
# 1) Para qué sirve: administrar usuarios y autenticación por sesión de Django.
# 2) Cómo funciona: expone endpoints de login/logout/sesión y CRUD de usuario/roles.
# 3) Qué hace: coordina identidad, estado activo y asignación de roles por usuario.
# 4) Cómo editarla: si cambian credenciales o flujo de sesión, ajusta acciones csrf/iniciar/cerrar/sesion_actual.
class UsuarioViewSet(viewsets.ViewSet):
    """CRUD completo para Usuario con gestión de roles."""

    @action(detail=False, methods=['get'], url_path='csrf', permission_classes=[AllowAny], authentication_classes=[])
    def csrf(self, request):
        """Inicializa la cookie CSRF para autenticacion por sesion."""
        token = get_token(request)
        return respuesta_estandar(
            data={"csrf_cookie": "ok", "csrf_token": token},
            mensaje="Cookie CSRF configurada."
        )

    @action(detail=False, methods=['post'], url_path='iniciar-sesion', permission_classes=[AllowAny], authentication_classes=[])
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
            data=construir_datos_sesion(usuario_autenticado, request),
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
            data=construir_datos_sesion(request.user, request),
            mensaje="Sesión activa obtenida."
        )

    # 1) Para qué sirve: construir el payload del perfil propio para pantalla de cuenta.
    # 2) Cómo funciona: reúne datos base del usuario y nombres de roles asignados.
    # 3) Qué hace: entrega estructura lista para formulario de perfil en frontend.
    # 4) Cómo editarla: agrega campos de cuenta aquí cuando el módulo de perfil crezca.
    def _construir_datos_perfil_propio(self, usuario, request):
        roles = list(usuario.usuario_roles.select_related('rol').values('rol__id', 'rol__nombre'))
        return {
            "id": usuario.id,
            "username": usuario.username,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "sucursal_id": usuario.sucursal_id,
            "sucursal_nombre": usuario.sucursal.nombre if usuario.sucursal else None,
            "roles": [
                {"id": rol['rol__id'], "nombre": rol['rol__nombre']}
                for rol in roles
            ],
            "foto_perfil_url": construir_url_foto_perfil(usuario, request),
            "is_superuser": usuario.is_superuser,
            "is_staff": usuario.is_staff,
            "requiere_cambio_password": usuario.requiere_cambio_password,
        }

    # 1) Para qué sirve: consultar y actualizar perfil del usuario autenticado.
    # 2) Cómo funciona: GET devuelve snapshot de cuenta; PATCH permite correo, foto y contraseña.
    # 3) Qué hace: centraliza edición de datos personales sin exponer nombre completo editable.
    # 4) Cómo editarla: agrega más campos permitidos validando reglas de negocio antes de guardar.
    @action(
        detail=False,
        methods=['get', 'patch'],
        url_path='perfil-propio',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def perfil_propio(self, request):
        if not request.user or not request.user.is_authenticated:
            return respuesta_estandar(
                mensaje="No hay sesión activa.",
                estado="error",
                codigo=status.HTTP_401_UNAUTHORIZED
            )

        usuario = request.user
        if request.method == 'GET':
            return respuesta_estandar(
                data=self._construir_datos_perfil_propio(usuario, request),
                mensaje="Perfil obtenido correctamente."
            )

        correo = request.data.get('correo', None)
        password_actual = request.data.get('password_actual')
        password_nueva = request.data.get('password_nueva')
        password_confirmacion = request.data.get('password_confirmacion')
        foto_perfil = request.FILES.get('foto_perfil')
        eliminar_foto = str(request.data.get('eliminar_foto', '')).strip().lower() in {'1', 'true', 'si', 'yes'}

        campos_actualizar = []
        cambio_password = any([password_actual, password_nueva, password_confirmacion])

        if usuario.requiere_cambio_password and not cambio_password:
            return respuesta_estandar(
                data={"password": ["Debes cambiar tu contraseña para continuar usando el sistema."]},
                mensaje="Cambio de contraseña obligatorio.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        if correo is not None:
            correo_limpio = str(correo).strip()
            if correo_limpio:
                existe_correo = Usuario.objects.exclude(pk=usuario.pk).filter(correo__iexact=correo_limpio).exists()
                if existe_correo:
                    return respuesta_estandar(
                        data={"correo": ["Este correo ya está en uso por otro usuario."]},
                        mensaje="No se pudo actualizar el perfil.",
                        estado="error",
                        codigo=status.HTTP_400_BAD_REQUEST,
                    )
                usuario.correo = correo_limpio
            else:
                usuario.correo = None
            campos_actualizar.append('correo')

        if eliminar_foto and usuario.foto_perfil:
            usuario.foto_perfil.delete(save=False)
            usuario.foto_perfil = None
            campos_actualizar.append('foto_perfil')

        if foto_perfil:
            if usuario.foto_perfil:
                usuario.foto_perfil.delete(save=False)
            usuario.foto_perfil = foto_perfil
            if 'foto_perfil' not in campos_actualizar:
                campos_actualizar.append('foto_perfil')

        if cambio_password:
            if not password_actual or not password_nueva or not password_confirmacion:
                return respuesta_estandar(
                    data={"password": ["Debes capturar contraseña actual, nueva y confirmación para cambiar contraseña."]},
                    mensaje="No se pudo actualizar el perfil.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

            if not usuario.check_password(password_actual):
                return respuesta_estandar(
                    data={"password_actual": ["La contraseña actual no es válida."]},
                    mensaje="No se pudo actualizar el perfil.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

            if password_nueva != password_confirmacion:
                return respuesta_estandar(
                    data={"password_confirmacion": ["La confirmación no coincide con la nueva contraseña."]},
                    mensaje="No se pudo actualizar el perfil.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

            try:
                validate_password(password_nueva, usuario)
            except DjangoValidationError as error_validacion:
                return respuesta_estandar(
                    data={"password_nueva": list(error_validacion.messages)},
                    mensaje="No se pudo actualizar el perfil.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST,
                )

            usuario.set_password(password_nueva)
            campos_actualizar.append('password')
            if usuario.requiere_cambio_password:
                usuario.requiere_cambio_password = False
                campos_actualizar.append('requiere_cambio_password')

        if not campos_actualizar:
            return respuesta_estandar(
                data=self._construir_datos_perfil_propio(usuario, request),
                mensaje="No se detectaron cambios para actualizar."
            )

        usuario.save(update_fields=list(dict.fromkeys(campos_actualizar)))

        if cambio_password:
            update_session_auth_hash(request, usuario)

        return respuesta_estandar(
            data=self._construir_datos_perfil_propio(usuario, request),
            mensaje="Perfil actualizado correctamente."
        )

    @action(detail=False, methods=['post'], url_path='soporte-tecnico/solicitudes')
    def crear_solicitud_soporte(self, request):
        """Recibe ticket de soporte, lo persiste y envía correo al canal técnico + acuse al usuario."""
        if not request.user or not request.user.is_authenticated:
            return respuesta_estandar(
                mensaje="No hay sesión activa.",
                estado="error",
                codigo=status.HTTP_401_UNAUTHORIZED,
            )

        serializador = SolicitudSoporteTecnicoSerializer(data=request.data)
        if not serializador.is_valid():
            return respuesta_estandar(
                data=serializador.errors,
                mensaje="No se pudo enviar la solicitud de soporte.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        datos = serializador.validated_data
        usuario = request.user

        nombre_usuario = str(getattr(usuario, 'nombre', '') or '').strip() or str(getattr(usuario, 'username', '') or '').strip()
        correo_usuario = str(getattr(usuario, 'correo', '') or '').strip()
        correo_usuario_visible = correo_usuario or 'No capturado'
        sucursal_nombre = getattr(getattr(usuario, 'sucursal', None), 'nombre', None) or 'No asignada'
        roles_usuario = list(usuario.usuario_roles.select_related('rol').values_list('rol__nombre', flat=True))
        roles_texto = ', '.join(roles_usuario) if roles_usuario else 'Sin rol asignado'

        problema_principal_codigo = datos['problema_principal']
        comportamiento_codigo = datos['comportamiento_observado']
        prioridad_codigo = datos.get('prioridad', 'MEDIA')
        dispositivo_codigo = datos.get('dispositivo', 'ESCRITORIO')

        problema_principal = resolver_etiqueta_opcion(problema_principal_codigo, SolicitudSoporteTecnicoSerializer.PROBLEMAS_PRINCIPALES)
        comportamiento = resolver_etiqueta_opcion(comportamiento_codigo, SolicitudSoporteTecnicoSerializer.COMPORTAMIENTOS)
        prioridad = resolver_etiqueta_opcion(prioridad_codigo, SolicitudSoporteTecnicoSerializer.PRIORIDADES)
        dispositivo = resolver_etiqueta_opcion(dispositivo_codigo, SolicitudSoporteTecnicoSerializer.DISPOSITIVOS)

        mapa_areas = dict(SolicitudSoporteTecnicoSerializer.AREAS_AFECTADAS)
        areas_codigos = list(datos.get('areas_afectadas', []))
        areas_legibles = [mapa_areas.get(area, area) for area in areas_codigos]
        areas_texto = ', '.join(areas_legibles) if areas_legibles else 'No especificadas'

        folio = generar_folio_soporte(getattr(usuario, 'id', '0'))
        intentos_folio = 0
        while TicketSoporteTecnico.todos.filter(folio=folio).exists() and intentos_folio < 5:
            folio = generar_folio_soporte(getattr(usuario, 'id', '0'))
            intentos_folio += 1

        if TicketSoporteTecnico.todos.filter(folio=folio).exists():
            return respuesta_estandar(
                mensaje='No fue posible generar un folio único para la solicitud.',
                estado='error',
                codigo=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ticket = TicketSoporteTecnico.objects.create(
            folio=folio,
            usuario=usuario,
            usuario_nombre=nombre_usuario or 'Sin nombre',
            usuario_username=str(getattr(usuario, 'username', '') or '').strip(),
            usuario_correo=correo_usuario or None,
            usuario_sucursal=sucursal_nombre,
            usuario_roles=roles_usuario,
            problema_principal=problema_principal_codigo,
            problema_principal_etiqueta=problema_principal,
            areas_afectadas=areas_codigos,
            areas_afectadas_etiquetas=areas_legibles,
            comportamiento_observado=comportamiento_codigo,
            comportamiento_observado_etiqueta=comportamiento,
            prioridad=prioridad_codigo,
            prioridad_etiqueta=prioridad,
            dispositivo=dispositivo_codigo,
            dispositivo_etiqueta=dispositivo,
            pagina_afectada=datos.get('pagina_afectada') or '',
            descripcion_detallada=datos['descripcion_detallada'],
            pasos_reproduccion=datos.get('pasos_reproduccion') or '',
            bloqueo_operativo=bool(datos.get('bloqueo_operativo')),
            creado_por=usuario,
            actualizado_por=usuario,
        )

        asunto = f"Soporte APEX-TON | {problema_principal} | {ticket.folio}"
        cuerpo = (
            "Nueva solicitud de soporte técnico\n"
            "================================\n\n"
            f"Folio: {ticket.folio}\n"
            f"Fecha: {timezone.now():%Y-%m-%d %H:%M:%S}\n"
            f"Bloqueo operativo: {'Sí' if ticket.bloqueo_operativo else 'No'}\n\n"
            "Datos del usuario\n"
            "-----------------\n"
            f"Nombre: {ticket.usuario_nombre or 'Sin nombre'}\n"
            f"Usuario: {ticket.usuario_username or 'sin_username'}\n"
            f"Correo: {correo_usuario_visible}\n"
            f"Sucursal: {ticket.usuario_sucursal or 'No asignada'}\n"
            f"Roles: {roles_texto}\n\n"
            "Detalle del incidente\n"
            "---------------------\n"
            f"Problema principal: {ticket.problema_principal_etiqueta}\n"
            f"Áreas afectadas: {areas_texto}\n"
            f"Comportamiento observado: {ticket.comportamiento_observado_etiqueta}\n"
            f"Prioridad: {ticket.prioridad_etiqueta}\n"
            f"Dispositivo: {ticket.dispositivo_etiqueta}\n"
            f"Página afectada: {ticket.pagina_afectada or 'No especificada'}\n\n"
            "Descripción detallada\n"
            "---------------------\n"
            f"{ticket.descripcion_detallada}\n\n"
            "Pasos para reproducir\n"
            "---------------------\n"
            f"{ticket.pasos_reproduccion or 'No especificados'}\n"
        )

        destinatarios_to = normalizar_destinatarios([DESTINATARIO_SOPORTE_PRINCIPAL])
        destinatarios_cc = normalizar_destinatarios([DESTINATARIO_SOPORTE_COPIA])
        errores_envio = []
        correo_soporte_enviado = False
        correo_confirmacion_enviado = False

        if not destinatarios_to:
            logger.error('No se encontró destinatario principal para soporte técnico.')
            errores_envio.append('No existe destinatario principal para soporte técnico.')
        else:
            destinatarios_to_lower = {correo.lower() for correo in destinatarios_to}
            destinatarios_cc = [correo for correo in destinatarios_cc if correo.lower() not in destinatarios_to_lower]

            reply_to = normalizar_destinatarios([correo_usuario]) if correo_usuario else []

            try:
                mensaje = EmailMultiAlternatives(
                    subject=asunto,
                    body=cuerpo,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    to=destinatarios_to,
                    cc=destinatarios_cc,
                    reply_to=reply_to,
                )

                enviados = int(mensaje.send(fail_silently=False) or 0)
                correo_soporte_enviado = enviados > 0
                if not correo_soporte_enviado:
                    errores_envio.append('No fue posible confirmar el envío al canal de soporte técnico.')
            except Exception as exc:
                logger.exception('Error enviando solicitud de soporte %s para usuario %s', ticket.folio, getattr(usuario, 'id', 'sin_id'))
                errores_envio.append(f'Error enviando correo a soporte: {exc}')

        destinatario_confirmacion = normalizar_destinatarios([ticket.usuario_correo]) if ticket.usuario_correo else []
        if destinatario_confirmacion:
            asunto_confirmacion = f"APEX-TON | Ticket recibido {ticket.folio}"
            cuerpo_confirmacion = (
                "Hola,\n\n"
                "Tu solicitud de soporte técnico fue registrada correctamente en APEX-TON.\n\n"
                f"Folio: {ticket.folio}\n"
                f"Fecha de registro: {timezone.now():%Y-%m-%d %H:%M:%S}\n"
                f"Problema principal: {ticket.problema_principal_etiqueta}\n"
                f"Prioridad: {ticket.prioridad_etiqueta}\n"
                "Estado inicial: Nuevo\n\n"
                "Este folio te servirá para dar seguimiento con el equipo de soporte.\n\n"
                "Gracias."
            )

            try:
                correo_confirmacion = EmailMultiAlternatives(
                    subject=asunto_confirmacion,
                    body=cuerpo_confirmacion,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    to=destinatario_confirmacion,
                )
                confirmacion_enviada = int(correo_confirmacion.send(fail_silently=False) or 0)
                correo_confirmacion_enviado = confirmacion_enviada > 0
                if not correo_confirmacion_enviado:
                    errores_envio.append('No fue posible confirmar el envío del correo de acuse al usuario.')
            except Exception as exc:
                logger.exception('Error enviando confirmación de ticket %s al usuario %s', ticket.folio, getattr(usuario, 'id', 'sin_id'))
                errores_envio.append(f'Error enviando acuse al usuario: {exc}')

        ticket.correo_soporte_enviado = correo_soporte_enviado
        ticket.correo_confirmacion_enviado = correo_confirmacion_enviado
        ticket.detalle_error_envio = ' | '.join(errores_envio)
        ticket.actualizado_por = usuario
        ticket.save(
            update_fields=[
                'correo_soporte_enviado',
                'correo_confirmacion_enviado',
                'detalle_error_envio',
                'actualizado_por',
                'actualizado_en',
            ]
        )

        mensaje_respuesta = 'Solicitud de soporte enviada correctamente.'
        if not correo_soporte_enviado:
            mensaje_respuesta = 'Solicitud registrada con folio, pero no se pudo enviar al canal de soporte.'
        elif ticket.usuario_correo and not correo_confirmacion_enviado:
            mensaje_respuesta = 'Solicitud enviada a soporte, pero no se pudo enviar correo de confirmación al usuario.'

        return respuesta_estandar(
            data={
                'folio': ticket.folio,
                'ticket_id': ticket.id,
                'destinatario_principal': destinatarios_to,
                'destinatario_copia': destinatarios_cc,
                'correo_soporte_enviado': correo_soporte_enviado,
                'correo_confirmacion_enviado': correo_confirmacion_enviado,
                'detalle_error_envio': ticket.detalle_error_envio,
            },
            mensaje=mensaje_respuesta,
            codigo=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='soporte-tecnico/eventos')
    def listar_eventos_soporte(self, request):
        """Lista tickets de soporte técnico para seguimiento administrativo."""
        if not usuario_administrador_habilitado(request.user):
            return respuesta_estandar(
                mensaje='Solo administradores pueden consultar eventos de soporte técnico.',
                estado='error',
                codigo=status.HTTP_403_FORBIDDEN,
            )

        estado_filtro = str(request.query_params.get('estado_seguimiento', '') or '').strip().upper()
        busqueda = str(request.query_params.get('busqueda', '') or '').strip()

        queryset = TicketSoporteTecnico.objects.select_related('usuario', 'atendido_por').order_by('-creado_en')

        if estado_filtro:
            queryset = queryset.filter(estado_seguimiento=estado_filtro)

        if busqueda:
            queryset = queryset.filter(
                Q(folio__icontains=busqueda)
                | Q(usuario_nombre__icontains=busqueda)
                | Q(usuario_username__icontains=busqueda)
                | Q(usuario_correo__icontains=busqueda)
                | Q(problema_principal_etiqueta__icontains=busqueda)
                | Q(descripcion_detallada__icontains=busqueda)
            )

        data = TicketSoporteTecnicoAdminSerializer(queryset, many=True).data
        return respuesta_estandar(
            data=data,
            mensaje='Eventos de soporte obtenidos correctamente.',
        )

    @action(detail=False, methods=['patch'], url_path='soporte-tecnico/eventos/(?P<ticket_id>[^/.]+)')
    def actualizar_evento_soporte(self, request, ticket_id=None):
        """Permite al administrador actualizar estado y notas de seguimiento de tickets."""
        if not usuario_administrador_habilitado(request.user):
            return respuesta_estandar(
                mensaje='Solo administradores pueden actualizar eventos de soporte técnico.',
                estado='error',
                codigo=status.HTTP_403_FORBIDDEN,
            )

        ticket = get_object_or_404(TicketSoporteTecnico, pk=ticket_id)
        serializador = TicketSoporteTecnicoSeguimientoSerializer(data=request.data)
        if not serializador.is_valid():
            return respuesta_estandar(
                data=serializador.errors,
                mensaje='No se pudo actualizar el ticket de soporte.',
                estado='error',
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        datos = serializador.validated_data
        ticket.estado_seguimiento = datos['estado_seguimiento']
        ticket.notas_seguimiento = str(datos.get('notas_seguimiento', '') or '').strip()
        ticket.atendido_por = request.user
        ticket.atendido_en = timezone.now()
        ticket.actualizado_por = request.user

        if ticket.estado_seguimiento in {
            TicketSoporteTecnico.EstadoSeguimiento.COMPLETADO,
            TicketSoporteTecnico.EstadoSeguimiento.DESCARTADO,
        }:
            ticket.resuelto_en = timezone.now()
        else:
            ticket.resuelto_en = None

        ticket.save(
            update_fields=[
                'estado_seguimiento',
                'notas_seguimiento',
                'atendido_por',
                'atendido_en',
                'resuelto_en',
                'actualizado_por',
                'actualizado_en',
            ]
        )

        return respuesta_estandar(
            data=TicketSoporteTecnicoAdminSerializer(ticket).data,
            mensaje='Ticket de soporte actualizado correctamente.',
        )

    def list(self, request):
        serializador = UsuarioListSerializer(Usuario.objects.all(), many=True, context={'request': request})
        return respuesta_estandar(data=serializador.data, mensaje="Usuarios obtenidos.")

    def create(self, request):
        s = UsuarioSerializer(data=request.data, context={'request': request})
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Usuario creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear usuario.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        serializador = UsuarioSerializer(get_object_or_404(Usuario, pk=pk), context={'request': request})
        return respuesta_estandar(data=serializador.data, mensaje="Usuario obtenido.")

    def update(self, request, pk=None):
        s = UsuarioSerializer(get_object_or_404(Usuario, pk=pk), data=request.data, context={'request': request})
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Usuario actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        s = UsuarioSerializer(get_object_or_404(Usuario, pk=pk), data=request.data, partial=True, context={'request': request})
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
# 1) Para qué sirve: administrar relaciones explícitas entre rol y permiso.
# 2) Cómo funciona: CRUD sobre la tabla intermedia RolPermiso.
# 3) Qué hace: ofrece control fino cuando se requiere operar la relación directamente.
# 4) Cómo editarla: agrega validaciones de duplicidad o auditoría adicional en create/destroy.
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
# 1) Para qué sirve: administrar asignaciones directas de roles a usuarios.
# 2) Cómo funciona: CRUD sobre UsuarioRol para alta/baja y consulta puntual.
# 3) Qué hace: complementa acciones del UsuarioViewSet para administración masiva.
# 4) Cómo editarla: agrega reglas de negocio por rol sensible antes de permitir create/destroy.
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

