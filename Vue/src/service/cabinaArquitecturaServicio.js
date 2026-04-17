import api from '@/service/api';


// 1) Para qué sirve: centralizar llamadas CRUD de la cabina administrativa (roles, usuarios, sucursales, catálogos y fondos).
// 2) Cómo funciona: cada función es un wrapper del cliente `api` hacia un endpoint REST específico.
// 3) Qué hace: separa capa HTTP de las vistas para mantener componentes limpios y reutilizables.
// 4) Cómo editarla: cuando cambie un endpoint, actualiza únicamente la función correspondiente sin tocar las vistas.
export function listarRolesAdmin() {
    return api.get('/cabina-arquitectura/roles/');
}

export function crearRolAdmin(payload) {
    return api.post('/cabina-arquitectura/roles/', payload);
}

export function actualizarRolAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/roles/${id}/`, payload);
}

export function eliminarRolAdmin(id) {
    return api.delete(`/cabina-arquitectura/roles/${id}/`);
}

// 1) Para qué sirve: listar usuarios administrativos.
// 2) Cómo funciona: GET al endpoint de usuarios de cabina.
// 3) Qué hace: provee datos para grilla de usuarios.
// 4) Cómo editarla: incorpora filtros si backend añade búsqueda por texto/rol.
export function listarUsuariosAdmin() {
    return api.get('/cabina-arquitectura/usuarios/');
}

export function crearUsuarioAdmin(payload) {
    return api.post('/cabina-arquitectura/usuarios/', payload);
}

export function actualizarUsuarioAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/usuarios/${id}/`, payload);
}

export function eliminarUsuarioAdmin(id) {
    return api.delete(`/cabina-arquitectura/usuarios/${id}/`);
}

// 1) Para qué sirve: listar sucursales del catálogo administrativo.
// 2) Cómo funciona: GET al endpoint de sucursales en cabina.
// 3) Qué hace: alimenta mantenimiento de sucursales.
// 4) Cómo editarla: agrega params si se habilitan filtros por estado.
export function listarSucursalesAdmin() {
    return api.get('/cabina-arquitectura/sucursales/');
}

export function crearSucursalAdmin(payload) {
    return api.post('/cabina-arquitectura/sucursales/', payload);
}

export function actualizarSucursalAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/sucursales/${id}/`, payload);
}

export function eliminarSucursalAdmin(id) {
    return api.delete(`/cabina-arquitectura/sucursales/${id}/`);
}

// 1) Para qué sirve: listar variables de configuración global.
// 2) Cómo funciona: GET sobre colección de configuraciones en cabina.
// 3) Qué hace: suministra datos para administración de parámetros globales.
// 4) Cómo editarla: ajusta ruta si backend separa configuración por módulos.
export function listarConfiguracionesGlobalesAdmin() {
    return api.get('/cabina-arquitectura/configuraciones-globales/');
}

export function crearConfiguracionGlobalAdmin(payload) {
    return api.post('/cabina-arquitectura/configuraciones-globales/', payload);
}

export function actualizarConfiguracionGlobalAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/configuraciones-globales/${id}/`, payload);
}

export function eliminarConfiguracionGlobalAdmin(id) {
    return api.delete(`/cabina-arquitectura/configuraciones-globales/${id}/`);
}

// 1) Para qué sirve: consumir endpoints operativos del Centro de Control administrativo.
// 2) Cómo funciona: wrappers GET/PUT/POST sobre /cabina-arquitectura/centro-control/*.
// 3) Qué hace: habilita UI para estado de app, tareas Celery y salud del servidor.
// 4) Cómo editarla: agrega nuevas operaciones aquí cuando crezcan endpoints del Centro de Control.
export function obtenerEstadoCentroControlAdmin() {
    return api.get('/cabina-arquitectura/centro-control/estado-aplicacion/');
}

export function guardarEstadoCentroControlAdmin(payload) {
    return api.put('/cabina-arquitectura/centro-control/estado-aplicacion/', payload);
}

export function listarTareasCentroControlAdmin() {
    return api.get('/cabina-arquitectura/centro-control/tareas-disponibles/');
}

export function ejecutarTareaCentroControlAdmin(payload) {
    return api.post('/cabina-arquitectura/centro-control/ejecutar-tarea/', payload);
}

export function obtenerSaludServidorCentroControlAdmin() {
    return api.get('/cabina-arquitectura/centro-control/salud-servidor/');
}

// 1) Para qué sirve: listar rubros contables y opciones relacionadas.
// 2) Cómo funciona: GET a endpoints de colección y opciones.
// 3) Qué hace: soporta catálogos contables usados por conceptos operativos.
// 4) Cómo editarla: agrega transformación local si backend cambia estructura de opciones.
export function listarRubrosContablesAdmin() {
    return api.get('/cabina-arquitectura/rubros-contables/');
}

export function obtenerOpcionesRubroContableAdmin() {
    return api.get('/cabina-arquitectura/rubros-contables/opciones/');
}

export function listarPadresRubrosContablesAdmin() {
    return api.get('/cabina-arquitectura/padres-rubros-contables/');
}

export function crearPadreRubroContableAdmin(payload) {
    return api.post('/cabina-arquitectura/padres-rubros-contables/', payload);
}

export function actualizarPadreRubroContableAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/padres-rubros-contables/${id}/`, payload);
}

export function eliminarPadreRubroContableAdmin(id) {
    return api.delete(`/cabina-arquitectura/padres-rubros-contables/${id}/`);
}

export function crearRubroContableAdmin(payload) {
    return api.post('/cabina-arquitectura/rubros-contables/', payload);
}

export function actualizarRubroContableAdmin(id, payload) {
    return api.put(`/cabina-arquitectura/rubros-contables/${id}/`, payload);
}

export function eliminarRubroContableAdmin(id) {
    return api.delete(`/cabina-arquitectura/rubros-contables/${id}/`);
}

// 1) Para qué sirve: administrar categorías operativas del sistema.
// 2) Cómo funciona: wrappers CRUD sobre endpoints de categorías.
// 3) Qué hace: mantiene pestañas operativas consumidas en captura.
// 4) Cómo editarla: incorpora query params o validaciones client-side según nuevas reglas.
export function listarCategoriasOperativasAdmin() {
    return api.get('/categorias/');
}

export function crearCategoriaOperativaAdmin(payload) {
    return api.post('/categorias/', payload);
}

export function actualizarCategoriaOperativaAdmin(id, payload) {
    return api.put(`/categorias/${id}/`, payload);
}

export function eliminarCategoriaOperativaAdmin(id) {
    return api.delete(`/categorias/${id}/`);
}

// 1) Para qué sirve: administrar conceptos por categoría operativa.
// 2) Cómo funciona: lista con filtro opcional categoria_id y CRUD REST.
// 3) Qué hace: mantiene nomenclaturas de movimientos.
// 4) Cómo editarla: cambia filtro en params al modificar contrato backend.
export function listarConceptosAdmin(categoriaId = null) {
    const params = categoriaId ? { params: { categoria_id: categoriaId } } : undefined;
    return api.get('/conceptos/', params);
}

export function crearConceptoAdmin(payload) {
    return api.post('/conceptos/', payload);
}

export function actualizarConceptoAdmin(id, payload) {
    return api.put(`/conceptos/${id}/`, payload);
}

export function eliminarConceptoAdmin(id) {
    return api.delete(`/conceptos/${id}/`);
}

// 1) Para qué sirve: administrar detalles parametrizados por categoría.
// 2) Cómo funciona: filtra opcionalmente por categoria_id y usa CRUD estándar.
// 3) Qué hace: define campos dinámicos para captura de movimientos.
// 4) Cómo editarla: adapta params/payload al evolucionar tipos de detalle.
export function listarDetallesParametrizadosAdmin(categoriaId = null) {
    const params = categoriaId ? { params: { categoria_id: categoriaId } } : undefined;
    return api.get('/detalles-parametrizados/', params);
}

export function crearDetalleParametrizadoAdmin(payload) {
    return api.post('/detalles-parametrizados/', payload);
}

export function actualizarDetalleParametrizadoAdmin(id, payload) {
    return api.put(`/detalles-parametrizados/${id}/`, payload);
}

export function eliminarDetalleParametrizadoAdmin(id) {
    return api.delete(`/detalles-parametrizados/${id}/`);
}

// 1) Para qué sirve: administrar fondos fijos y sus asignaciones por sucursal.
// 2) Cómo funciona: usa endpoints dedicados para catálogo y relación sucursal-fondo.
// 3) Qué hace: mantiene configuración financiera base por sala.
// 4) Cómo editarla: separa por submódulo adicional si backend divide fondos y asignaciones.
export function listarFondosFijosAdmin() {
    return api.get('/fondos-fijos/');
}

export function crearFondoFijoAdmin(payload) {
    return api.post('/fondos-fijos/', payload);
}

export function actualizarFondoFijoAdmin(id, payload) {
    return api.put(`/fondos-fijos/${id}/`, payload);
}

export function eliminarFondoFijoAdmin(id) {
    return api.delete(`/fondos-fijos/${id}/`);
}

export function listarAsignacionesFondosFijosAdmin() {
    return api.get('/sucursales-fondos-fijos/');
}

export function crearAsignacionFondoFijoAdmin(payload) {
    return api.post('/sucursales-fondos-fijos/', payload);
}

export function actualizarAsignacionFondoFijoAdmin(id, payload) {
    return api.put(`/sucursales-fondos-fijos/${id}/`, payload);
}

export function eliminarAsignacionFondoFijoAdmin(id) {
    return api.delete(`/sucursales-fondos-fijos/${id}/`);
}

// 1) Para qué sirve: consumir endpoints exclusivos de cabina para rol DIRECTOR.
// 2) Cómo funciona: encapsula llamadas REST bajo /cabina-arquitectura/director/*.
// 3) Qué hace: separa explícitamente operaciones de director de la cabina de administrador.
// 4) Cómo editarla: agrega aquí nuevas funciones cuando se creen endpoints dedicados de director.
export function listarFondosFijosDirector() {
    return api.get('/cabina-arquitectura/director/fondos-fijos/');
}

export function listarSucursalesDirector() {
    return api.get('/cabina-arquitectura/director/sucursales/');
}

export function crearSucursalDirector(payload) {
    return api.post('/cabina-arquitectura/director/sucursales/', payload);
}

export function listarUsuariosDirector() {
    return api.get('/cabina-arquitectura/director/usuarios/');
}

export function crearUsuarioDirector(payload) {
    return api.post('/cabina-arquitectura/director/usuarios/', payload);
}

export function actualizarUsuarioDirector(id, payload) {
    return api.put(`/cabina-arquitectura/director/usuarios/${id}/`, payload);
}

export function reiniciarPasswordUsuarioDirector(id) {
    return api.post(`/cabina-arquitectura/director/usuarios/${id}/reiniciar-password/`);
}

export function listarRolesDisponiblesDirector() {
    return api.get('/cabina-arquitectura/director/usuarios/roles-disponibles/');
}

export function listarConfiguracionesGlobalesDirector() {
    return api.get('/cabina-arquitectura/director/configuraciones-globales/');
}

export function actualizarConfiguracionGlobalDirector(id, payload) {
    return api.patch(`/cabina-arquitectura/director/configuraciones-globales/${id}/`, payload);
}

export function listarRubrosContablesDirector() {
    return api.get('/cabina-arquitectura/director/rubros-contables/');
}

export function obtenerOpcionesRubroContableDirector() {
    return api.get('/cabina-arquitectura/director/rubros-contables/opciones/');
}

export function crearRubroContableDirector(payload) {
    return api.post('/cabina-arquitectura/director/rubros-contables/', payload);
}

export function actualizarRubroContableDirector(id, payload) {
    return api.put(`/cabina-arquitectura/director/rubros-contables/${id}/`, payload);
}
