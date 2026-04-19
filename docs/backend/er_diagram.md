# Diagrama Entidad-Relación (ER) - APEX-TON Backend

El siguiente diagrama muestra las entidades principales del sistema y sus relaciones. 

> **Nota**: Casi todos los modelos del sistema heredan de `ModeloBase`, el cual incluye campos de auditoría (`creado_por`, `actualizado_por`, `eliminado_por` relacionados al modelo `Usuario`), campos de fecha (`creado_en`, `actualizado_en`, `eliminado_en`) y un estado lógico (`estado`). Por simplicidad visual, estas relaciones de auditoría hacia `Usuario` se omiten en la mayoría de las entidades, enfocándose en las reglas del negocio.

```mermaid
erDiagram
    %% Core / Abstract
    ModeloBase {
        UUID id PK
        string estado
        datetime creado_en
        datetime actualizado_en
        datetime eliminado_en
        UUID creado_por FK
        UUID actualizado_por FK
        UUID eliminado_por FK
    }

    %% Usuarios
    Usuario {
        UUID id PK
        string email
        string password
        UUID sucursal_id FK
    }
    Rol {
        UUID id PK
        string nombre
    }
    Permiso {
        UUID id PK
        string codename
    }
    RolPermiso {
        UUID id PK
        UUID rol_id FK
        UUID permiso_id FK
    }
    UsuarioRol {
        UUID id PK
        UUID usuario_id FK
        UUID rol_id FK
    }
    ConfiguracionUsuario {
        UUID id PK
        UUID usuario_id FK "OneToOne"
        string tema
        string color_acento
    }

    %% Sucursales y Fondos Fijos
    Sucursal {
        UUID id PK
        string nombre
    }
    FondoFijo {
        UUID id PK
        string nombre
        decimal monto
    }
    SucursalFondoFijo {
        UUID id PK
        UUID sucursal_id FK
        UUID fondo_fijo_id FK
    }

    %% Configuraciones Globales
    PadreRubroContable {
        UUID id PK
        string nombre
    }
    RubroContable {
        UUID id PK
        string nombre
        UUID padre_id FK
    }
    ConfiguracionGlobal {
        UUID id PK
        string clave
        string valor
    }

    %% Categorías Operativas
    CategoriaOperativa {
        UUID id PK
        string nombre
    }
    Concepto {
        UUID id PK
        string nombre
        UUID categoria_id FK
        UUID rubro_contable_id FK
    }
    DetalleParametrizado {
        UUID id PK
        string descripcion
        UUID categoria_id FK
    }
    SaldoInicialCategoriaMensual {
        UUID id PK
        decimal monto
        UUID sucursal_id FK
        UUID categoria_id FK
    }

    %% Reportes y Estados de Resultados
    ReporteDiario {
        UUID id PK
        date fecha
        string estado_reporte
        UUID sucursal_id FK
        UUID cerrado_por FK
    }
    MovimientoDiario {
        UUID id PK
        decimal monto
        string tipo
        UUID reporte_id FK
        UUID concepto_id FK
    }
    LibroEstadoResultados {
        UUID id PK
        int mes
        int anio
        string estado_mes
        UUID sucursal_id FK
        UUID cerrado_por FK
    }

    %% Relaciones
    Usuario }|--|| Sucursal : "pertenece a"
    Usuario ||--|| ConfiguracionUsuario : "tiene"
    Usuario ||--|{ UsuarioRol : "tiene"
    Rol ||--|{ UsuarioRol : "asignado a"
    Rol ||--|{ RolPermiso : "incluye"
    Permiso ||--|{ RolPermiso : "asignado a"
    
    Sucursal ||--|{ SucursalFondoFijo : "posee"
    FondoFijo ||--|{ SucursalFondoFijo : "asignado a"
    
    PadreRubroContable ||--|{ RubroContable : "agrupa"
    
    CategoriaOperativa ||--|{ Concepto : "contiene"
    CategoriaOperativa ||--|{ DetalleParametrizado : "parametrizado por"
    RubroContable ||--|{ Concepto : "clasifica"
    
    Sucursal ||--|{ SaldoInicialCategoriaMensual : "registra"
    CategoriaOperativa ||--|{ SaldoInicialCategoriaMensual : "tiene"

    Sucursal ||--|{ ReporteDiario : "genera"
    Usuario ||--o{ ReporteDiario : "cierra"
    ReporteDiario ||--|{ MovimientoDiario : "contiene"
    Concepto ||--|{ MovimientoDiario : "categoriza"
    
    Sucursal ||--|{ LibroEstadoResultados : "genera"
    Usuario ||--o{ LibroEstadoResultados : "cierra"
```
