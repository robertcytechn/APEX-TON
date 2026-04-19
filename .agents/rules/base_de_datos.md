# Reglas de base de datos (MySQL)

## 1) Entidades base del dominio

- Configuracion global: `configuraciones_globales`
- Catalogos contables: `rubro_contable`
- Seguridad: `usuarios`, `roles`, `permisos`, `usuarios_roles`, `roles_permisos`
- Operacion: `sucursales`, `fondos_fijos`, `categorias_operativas`, `conceptos`, `movimientos_diarios`, `reportes_diarios`
- Historico mensual: `libro_estado_resultados`

## 2) Relaciones que no deben romperse

- `Sucursal` -> `FondoFijo`: 1:1 operativo.
- `Usuario` -> `Sucursal`: pertenencia operativa por sucursal (cuando aplica).
- `Usuario` -> `Rol`: via tabla pivote `usuarios_roles`.
- `Rol` -> `Permiso`: via tabla pivote `roles_permisos`.
- `Concepto` -> `CategoriaOperativa` y `RubroContable`.

## 3) Reglas de integridad

- Valores monetarios siempre en decimal (precision fija, nunca float para persistencia).
- No modificar snapshots historicos cerrados por cambios posteriores de configuracion.
- El estado de cierre diario/mensual debe conservar inmutabilidad historica.

## 4) Regla para cambios de esquema

Si se modifica estructura de datos:

1. Crear/ajustar migraciones Django.
2. Revisar impacto en serializers y endpoints.
3. Revisar impacto en reportes y agregaciones de estado de resultados.
4. Actualizar documentacion de API/flujo cuando cambie el contrato funcional.
