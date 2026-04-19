# Estandares backend API (Django/DRF)

## 1) Activacion obligatoria de skill

Si la tarea modifica backend (`DJANGO\`), usar skill: `django-pro`.

## 2) Alcance de esta regla

Aplica a modelos, serializers, viewsets, permisos, rutas, tareas Celery y contratos de API.

## 3) Contrato de respuesta API

Toda respuesta JSON debe mantener el envelope estandar:

```json
{
  "status": "success",
  "message": "Operacion exitosa",
  "data": {}
}
```

## 4) Autenticacion y permisos

- Autenticacion oficial: `SessionAuthentication`.
- No introducir JWT salvo requerimiento explicito de arquitectura.
- Permisos por rol (`Rol`, `Permiso`, `RolPermiso`, `UsuarioRol`), no por usuario directo.

## 5) Trazabilidad y modelo base

- Los modelos transaccionales deben seguir el patron de auditoria de `ModeloBase`.
- Conservar consistencia de campos de auditoria y snapshots de cambios (`valor_anterior`, `valor_actual`).
- Mantener compatibilidad con `django-simple-history`.

## 6) Regla de implementacion DRF

Cuando cambia una entidad de dominio, revisar en conjunto:

1. Modelo
2. Serializer
3. ViewSet / vista
4. URL router
5. Permisos
6. Consumo frontend (si aplica)

## 7) Regla de documentacion backend

Si cambia contrato de endpoint o comportamiento funcional:

- Actualizar `docs\backend\api_reference.md`
- Actualizar `docs\backend\flujo_de_informacion.md` cuando cambie el flujo operativo
