"""
Permisos personalizados de DRF para el sistema APEX-TON.
Centraliza la lógica de autorización reutilizable en todos los ViewSets.
"""
from django.utils import timezone
from rest_framework.permissions import BasePermission


def obtener_ventana_horaria():
    """
    Lee HORARIO_APERTURA y HORARIO_CIERRE desde ConfiguracionGlobal.
    Retorna (hora_apertura, hora_cierre) como objetos datetime.time o (None, None)
    si no están configurados.
    """
    try:
        from configuraciones_globales.models import ConfiguracionGlobal
        apertura = ConfiguracionGlobal.objects.filter(clave='HORARIO_APERTURA').first()
        cierre   = ConfiguracionGlobal.objects.filter(clave='HORARIO_CIERRE').first()
        hora_apertura = apertura.valor_tipado if apertura else None
        hora_cierre   = cierre.valor_tipado   if cierre   else None
        return hora_apertura, hora_cierre
    except Exception:
        return None, None


def sistema_dentro_de_horario():
    """
    Verifica si la hora actual del servidor está dentro de la ventana de operación.
    Retorna (bool, hora_apertura, hora_cierre).
    """
    hora_apertura, hora_cierre = obtener_ventana_horaria()
    if not hora_apertura or not hora_cierre:
        # Sin configuración: el sistema no restringe por horario
        return True, hora_apertura, hora_cierre
    ahora = timezone.localtime(timezone.now()).time()
    dentro = hora_apertura <= ahora <= hora_cierre
    return dentro, hora_apertura, hora_cierre


class VentanaHorariaPermiso(BasePermission):
    """
    Permission DRF que bloquea operaciones de ESCRITURA (POST, PUT, PATCH, DELETE)
    cuando la hora del servidor está fuera del rango HORARIO_APERTURA – HORARIO_CIERRE
    configurado en ConfiguracionGlobal.

    Las operaciones de LECTURA (GET, HEAD, OPTIONS) siempre están permitidas.
    """

    METODOS_ESCRITURA = ('POST', 'PUT', 'PATCH', 'DELETE')

    def has_permission(self, request, view):
        # Lectura siempre permitida
        if request.method not in self.METODOS_ESCRITURA:
            return True

        dentro, apertura, cierre = sistema_dentro_de_horario()
        if not dentro:
            if apertura and cierre:
                self.message = (
                    f"El sistema operativo está cerrado. "
                    f"El horario de captura es de {apertura.strftime('%H:%M')} "
                    f"a {cierre.strftime('%H:%M')} hrs. "
                    f"Fuera de este rango no se permiten modificaciones."
                )
            else:
                self.message = "El sistema está temporalmente cerrado para modificaciones."
            return False

        return True


class EsAdministrador(BasePermission):
    """
    Permiso que valida que el usuario autenticado tenga el rol ADMINISTRADOR.
    Se usa para acciones excepcionales como la reapertura de un día cerrado.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Verificar por rol asignado en la tabla UsuarioRol
        try:
            return request.user.usuario_roles.filter(
                rol__nombre__iexact='ADMINISTRADOR'
            ).exists() or request.user.is_superuser
        except Exception:
            return request.user.is_superuser
