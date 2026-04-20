# Hallazgos

- El menú lateral en AppMenu enlaza Soporte a /pages/notfound y muestra "Plantilla vacía" en Principal.
- La ruta / usa views/pages/Empty.vue: hoy tiene tablero de contador/gerente y fallback vacío para otros roles.
- El endpoint GET /estado-resultados/estadisticas ya entrega series por sucursal (ingresos/egresos/neto/movimientos).
- El endpoint de estadísticas permite rango con fecha_inicio/fecha_fin y autorización para DIRECTOR/ADMINISTRADOR.
- El listado de sucursales del dominio representa casinos/salas, por lo que puede usarse para gráficas por casino.
