# Normativas generales de trabajo (APEX-TON)

## 1) Idioma y comunicacion

- Idioma principal del proyecto: Espanol de Mexico.
- Todo texto visible al usuario final debe estar en espanol.
- Mantener consistencia con el estilo ya existente del modulo (nombres de entidades de dominio en espanol, nombres tecnicos de librerias segun estandar del framework).

## 2) Regla de analisis previo

Antes de modificar codigo:

1. Identificar que capa toca el cambio (`DJANGO\`, `Vue\`, o ambas).
2. Revisar el impacto en rutas, permisos, contratos API y vistas.
3. No proponer cambios aislados que rompan el flujo entre backend y frontend.

## 3) Regla de coherencia por capa

- Si cambia modelo/contrato API: revisar serializers, viewsets, rutas y consumo en frontend.
- Si cambia UI/flujo frontend: revisar llamadas Axios, permisos de rol y estados de sesion.
- Si cambia una regla de negocio: alinear backend, frontend y documentacion funcional.

## 4) Regla de documentacion

Actualizar documentacion solo cuando el comportamiento cambie:

- Backend: `docs\backend\*.md`
- Frontend: `docs\frontend\*.md`
- Reglas de agentes: `.agents\rules\*.md` y `.agents\workFlows\*.md`
