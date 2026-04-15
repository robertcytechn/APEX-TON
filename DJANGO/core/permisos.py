"""
Permisos personalizados de DRF para el sistema APEX-TON.
Centraliza la lógica de autorización reutilizable en todos los ViewSets.
"""
from django.utils import timezone
from rest_framework.permissions import BasePermission


# 1) Para qué sirve: centraliza la lectura de horarios de operación desde configuración global.
# 2) Cómo funciona: consulta las claves HORARIO_APERTURA y HORARIO_CIERRE y devuelve objetos time.
# 3) Qué hace: entrega una tupla (hora_apertura, hora_cierre) o (None, None) si faltan datos.
# 4) Cómo editarla: si cambian las claves de configuración, actualiza los filtros por clave en esta función.
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


# 1) Para qué sirve: validar si el sistema está dentro de la ventana permitida para capturas.
# 2) Cómo funciona: compara la hora local actual del servidor contra apertura y cierre configurados.
# 3) Qué hace: retorna (esta_dentro, hora_apertura, hora_cierre) para reutilizar en permisos.
# 4) Cómo editarla: modifica la regla de comparación si en el futuro se requiere horario cruzado (noche-madrugada).
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

    # Soporta ventanas normales (ej. 08:00-20:00) y cruzadas (ej. 22:00-05:00).
    if hora_apertura <= hora_cierre:
        dentro = hora_apertura <= ahora <= hora_cierre
    else:
        dentro = ahora >= hora_apertura or ahora <= hora_cierre

    return dentro, hora_apertura, hora_cierre


# 1) Para qué sirve: impedir escrituras fuera del horario operativo definido por negocio.
# 2) Cómo funciona: permite lectura siempre y evalúa horario solo para POST/PUT/PATCH/DELETE.
# 3) Qué hace: bloquea la petición con mensaje claro cuando está fuera de horario.
# 4) Cómo editarla: agrega/quita métodos en METODOS_ESCRITURA o ajusta el texto de self.message.
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


# 1) Para qué sirve: reservar acciones sensibles únicamente para rol ADMINISTRADOR.
# 2) Cómo funciona: valida autenticación y consulta relación usuario_roles contra nombre de rol.
# 3) Qué hace: devuelve True para administradores o superusuarios; False para cualquier otro caso.
# 4) Cómo editarla: si cambia el nombre del rol maestro, actualiza el filtro rol__nombre__iexact.
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
