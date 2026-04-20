import api from '@/service/api';

// 1) Para qué sirve: enviar tickets de soporte técnico capturados por usuarios autenticados.
// 2) Cómo funciona: hace POST al endpoint de solicitudes de soporte del módulo usuarios.
// 3) Qué hace: dispara el correo con detalle de incidencia y metadatos de sesión.
// 4) Cómo editarla: agrega o transforma campos del payload si backend amplía el contrato.
export function enviarSolicitudSoporteTecnico(payload = {}) {
    return api.post('/usuarios/soporte-tecnico/solicitudes/', payload);
}

// 1) Para qué sirve: consultar tickets de soporte para gestión administrativa.
// 2) Cómo funciona: hace GET al endpoint de eventos de soporte con filtros opcionales.
// 3) Qué hace: devuelve el historial de tickets con estado y detalle de seguimiento.
// 4) Cómo editarla: ajusta query params si backend agrega filtros adicionales.
export function listarEventosSoporteTecnico(params = {}) {
    return api.get('/usuarios/soporte-tecnico/eventos/', { params });
}

// 1) Para qué sirve: actualizar estado y notas de seguimiento de un ticket de soporte.
// 2) Cómo funciona: envía PATCH con estado y notas al endpoint administrativo por id.
// 3) Qué hace: permite marcar tickets como en proceso, completados o descartados.
// 4) Cómo editarla: agrega campos de cierre si backend amplía el workflow de seguimiento.
export function actualizarEventoSoporteTecnico(ticketId, payload = {}) {
    return api.patch(`/usuarios/soporte-tecnico/eventos/${ticketId}/`, payload);
}
