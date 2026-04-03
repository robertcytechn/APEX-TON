Version del sistema: 2.3.0

## Historial de Versiones

- Fecha: 2026-04-02
- Version: 2.3.0
- Autor: Cy tamayo
- Descripcion: Se separo la gestion de padres de rubros en una vista propia de cabina de arquitectura, se elimino el filtro por dia del estado de resultados para trabajar solo por mes-anio-casino, y se agrego la bandera por padre para decidir si impacta o no los totales generales del estado de resultados manteniendo visibles todos los rubros.

- Fecha: 2026-04-02
- Version: 2.2.0
- Autor: Cy tamayo
- Descripcion: Se adapto backend y frontend para operar rubros con padres dinamicos por relacion, incluyendo cabina de arquitectura, gestion visual de padres de rubro, cierres historicos y estado de resultados con compatibilidad para snapshots legados.

- Fecha: 2026-04-02
- Version: 2.1.0
- Autor: Cy tamayo
- Descripcion: Se normalizo el campo padre de rubros contables a un catalogo dinamico con tabla propia, migracion de datos conservando relaciones existentes, nuevos endpoints CRUD de padres y ajuste de serializers/views para operar padres por id o clave sin perder compatibilidad de consumo.

## Cambios Menores

- Fecha: 2026-04-02
- Autor: Cy tamayo
- Descripcion: Se ajustaron mensajes y estructura de opciones en rubros contables para consumir padres dinamicos desde base de datos.