import { defineStore } from 'pinia';
import { cerrarSesion, iniciarSesion, obtenerCsrf, obtenerSesionActual } from '@/service/autenticacionServicio';

const CLAVE_IDENTIFICADOR = 'binsurmx_ultimo_identificador';
const CLAVE_SESION = 'binsurmx_sesion';

// 1) Para qué sirve: extraer un mensaje entendible desde errores HTTP.
// 2) Cómo funciona: intenta leer response.data.message y usa un fallback.
// 3) Qué hace: unifica mensajes de error mostrados en UI.
// 4) Cómo editarla: ajusta prioridad de campos si backend cambia su estructura de error.
function obtenerError(error, mensajeDefault) {
    return error?.response?.data?.message || mensajeDefault;
}

// 1) Para qué sirve: estandarizar textos para comparaciones de seguridad por rol.
// 2) Cómo funciona: remueve acentos y espacios sobrantes, luego mayúsculas.
// 3) Qué hace: evita falsos negativos al evaluar permisos.
// 4) Cómo editarla: incorpora reglas de transliteración extra si aparecen caracteres especiales.
function normalizarTexto(texto) {
    return (texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .toUpperCase();
}

// 1) Para qué sirve: comparar roles de usuario contra un rol objetivo con tolerancia.
// 2) Cómo funciona: normaliza ambos valores y permite igualdad o inclusión textual.
// 3) Qué hace: mejora robustez cuando los nombres de rol no son idénticos.
// 4) Cómo editarla: endurece la comparación a igualdad exacta si negocio lo requiere.
function contieneRolObjetivo(nombreRolUsuario, nombreRolObjetivo) {
    const rolUsuario = normalizarTexto(nombreRolUsuario);
    const rolObjetivo = normalizarTexto(nombreRolObjetivo);
    return rolUsuario === rolObjetivo || rolUsuario.includes(rolObjetivo);
}

// 1) Para qué sirve: decidir acceso según lista de roles/meta-reglas solicitadas.
// 2) Cómo funciona: evalúa roles especiales y roles nominales contra el estado de sesión.
// 3) Qué hace: retorna true si cumple al menos una condición de acceso requerida.
// 4) Cómo editarla: agrega nuevas palabras clave (ej. AUDITOR) en este evaluador central.
function evaluarAccesoPorRol(state, rolesRequeridos = []) {
    if (!Array.isArray(rolesRequeridos) || rolesRequeridos.length === 0) {
        return true;
    }

    const rolUsuario = state.roles.map((rol) => rol.nombre || '');

    return rolesRequeridos.some((rolRequerido) => {
        const rol = normalizarTexto(rolRequerido);

        if (rol === 'AUTENTICADO') {
            return !!state.estaAutenticado;
        }
        if (rol === 'SUPERUSUARIO') {
            return !!state.usuario?.is_superuser;
        }
        if (rol === 'STAFF') {
            return !!state.usuario?.is_staff;
        }
        if (rol === 'ADMINISTRADOR') {
            const tieneRolAdministrador = rolUsuario.some((nombreRol) => contieneRolObjetivo(nombreRol, 'ADMINISTRADOR'));
            return tieneRolAdministrador || !!state.usuario?.is_superuser || !!state.usuario?.is_staff;
        }

        return rolUsuario.some((nombreRol) => contieneRolObjetivo(nombreRol, rol));
    });
}

// 1) Para qué sirve: centralizar estado y flujo de autenticación por sesión en frontend.
// 2) Cómo funciona: guarda/carga sesión local, consulta backend y expone getters de autorización.
// 3) Qué hace: mantiene usuario, roles, permisos y utilidades de acceso para toda la app.
// 4) Cómo editarla: extiende acciones/getters aquí al agregar nuevas políticas de seguridad.
export const useSesionStore = defineStore('sesion', {
    state: () => ({
        usuario: null,
        roles: [],
        permisos: [],
        estaAutenticado: false,
        sesionVerificada: false,
        verificandoSesion: false,
        promesaVerificacion: null,
        cargandoSesion: false,
        errorSesion: null,
        ultimoIdentificador: localStorage.getItem(CLAVE_IDENTIFICADOR) || ''
    }),
    actions: {
        _guardarSesionLocal() {
            const payload = {
                usuario: this.usuario,
                roles: this.roles,
                permisos: this.permisos,
                estaAutenticado: this.estaAutenticado
            };
            localStorage.setItem(CLAVE_SESION, JSON.stringify(payload));
        },
        _cargarSesionLocal() {
            const sesion = localStorage.getItem(CLAVE_SESION);
            if (!sesion) {
                return;
            }
            try {
                const data = JSON.parse(sesion);
                this.usuario = data.usuario || null;
                this.roles = data.roles || [];
                this.permisos = data.permisos || [];
                this.estaAutenticado = !!data.estaAutenticado;
            } catch {
                this.limpiarSesionLocal();
            }
        },
        limpiarSesionLocal() {
            this.usuario = null;
            this.roles = [];
            this.permisos = [];
            this.estaAutenticado = false;
            localStorage.removeItem(CLAVE_SESION);
        },
        guardarUltimoIdentificador(identificador) {
            if (!identificador) {
                return;
            }
            this.ultimoIdentificador = identificador;
            localStorage.setItem(CLAVE_IDENTIFICADOR, identificador);
        },
        async iniciarSesion(payload) {
            this.cargandoSesion = true;
            this.errorSesion = null;
            try {
                await obtenerCsrf();
                const { data } = await iniciarSesion(payload);
                this.usuario = data.data.usuario;
                this.roles = data.data.roles || [];
                this.permisos = data.data.permisos || [];
                this.estaAutenticado = true;
                this.sesionVerificada = true;
                this.guardarUltimoIdentificador(payload.identificador);
                this._guardarSesionLocal();
                return { ok: true };
            } catch (error) {
                this.limpiarSesionLocal();
                this.errorSesion = obtenerError(error, 'No se pudo iniciar sesión.');
                return { ok: false, mensaje: this.errorSesion };
            } finally {
                this.cargandoSesion = false;
            }
        },
        async verificarSesionActual() {
            if (this.promesaVerificacion) {
                await this.promesaVerificacion;
                return this.estaAutenticado;
            }

            if (!this.sesionVerificada) {
                this._cargarSesionLocal();
            }

            this.verificandoSesion = true;
            this.promesaVerificacion = (async () => {
                try {
                    const { data } = await obtenerSesionActual();
                    this.usuario = data.data.usuario;
                    this.roles = data.data.roles || [];
                    this.permisos = data.data.permisos || [];
                    this.estaAutenticado = true;
                    this.sesionVerificada = true;
                    this._guardarSesionLocal();
                } catch {
                    this.limpiarSesionLocal();
                    this.sesionVerificada = true;
                } finally {
                    this.verificandoSesion = false;
                    this.promesaVerificacion = null;
                }
            })();

            await this.promesaVerificacion;
            return this.estaAutenticado;
        },
        async cerrarSesion() {
            try {
                await cerrarSesion();
            } catch {
                // Ignoramos error de red para permitir cierre local.
            }
            this.limpiarSesionLocal();
            this.sesionVerificada = true;
        },
        actualizarUsuarioSesion(datosUsuario = {}) {
            if (!this.usuario) {
                this.usuario = {};
            }
            this.usuario = {
                ...this.usuario,
                ...datosUsuario
            };
            this._guardarSesionLocal();
        }
    },
    getters: {
        tienePermiso: (state) => (codigoPermiso) => state.permisos.some((permiso) => permiso.codigo === codigoPermiso),
        cumpleAlgunoRoles: (state) => (rolesRequeridos = []) => evaluarAccesoPorRol(state, rolesRequeridos),
        tieneRol: (state) => (nombreRol) => {
            return state.roles.some((rol) => contieneRolObjetivo(rol.nombre, nombreRol));
        },
        requiereCambioPassword: (state) => {
            return !!state.usuario?.requiere_cambio_password;
        },
        esContadorOGerente: (state) => {
            return evaluarAccesoPorRol(state, ['CONTADOR', 'GERENTE']);
        },
        esAdministrador: (state) => {
            return evaluarAccesoPorRol(state, ['ADMINISTRADOR']);
        }
    }
});
