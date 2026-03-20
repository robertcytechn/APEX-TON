## proposito de este archivo ##
  * funcionar como guia para el agente de IA (copilot y gemini) para que pueda entender el proyecto y generar codigo que sea consistente con el resto del proyecto.


## reglas tecnicas y tecnologicas ##
  * usaremos python 3.13
  * usaremos django 5.2
  * usaremos drf
  * usaremos mysql
  * usaremos vue 3
  * usaremos pinia
  * usaremos primevue v4.0 o superior
  * usaremos tailwindcss
  * usaremos vite
  * usaremos typescript
  * usaremos axios
  * usaremos tema de primevue sakai

## reglas de desarrollo ##
  * usaremos git
  * usaremos github


## reglas de negocio y funcionamiento ##
  * todo debe de ir en español desde nombre de variables, funciones, clases, etc hasta comentarios y documentacion.
  * todo lo que el cliente final puede ver ira en español
  * intentemos separar cada modulo por su propia app de django para mantener el codigo organizado y modular.
      *> ejemplo: si vamos a crear un modulo de inventario, crearemos una app de django llamada inventario.
      *> todas las respuestas de django deben ser en español y no solo respuestas escuetas sino un json organizado, con estatus, mensaje y datos. en data puede venir un objeto o un array de objetos de la app que se esta consultando o de la operacion que se realizo.
      Ejemplo de respuesta: 
                            {
                              "status": "success",
                              "message": "Operación exitosa",
                              "data": {}
                            }
  * usaremos las sesiones nativas de django para el manejo de autenticacion y autorizacion [nunca usar jwt], pero usaremos nuestra propia app de usuarios para manejar los usuarios y sus permisos, esta app se llamara usuarios y tendra los siguientes modelos:
    * Usuario
    * Rol
    * Permiso
    * Usuario_Rol
    * Rol_Permiso
  * todas las apps o clases o modulos deberan de heredar un modelo base que contenga los campos, y con valor anterior y actual:
    * creado_en
    * actualizado_en
    * eliminado_en
    * creado_por
    * actualizado_por
    * eliminado_por
    * valor_anterior
    * valor_actual
  * todos los permisos deben ir en la app propia de permisos, donde se definen los permisos y un modelo conector para permisos y roles, usaremos permisos por rol y no por usuario individualmente. [nunca usar permisos por usuario individualmente]
  * en front end usaremos pinia para el manejo de estado global y axios para el manejo de peticiones http, usaremos axios interceptores para manejar las respuestas de django y manejar los errores de autenticacion y autorizacion. mantener todo en español. y guardaremos los permisos del rol del usuario en el localStorage para poder manejar los permisos del usuario en el front end.

## reglas de negocio ##
  * nuestro trabajo es asimilar el funcionamiento del archivo "CAJA MUESTRA.xlsx" y replicarlo en nuestro proyecto, automatizando y estandarizando conceptos y procesos que se realizan manualmente. ejemplo estado de resultados siempre debera ser de forma automatica sumando lo de los movimientos de caja y los movimientos de banco y de todas las pestañas que se relacionen con ingresos y egresos.


## reglas de relacion en base de datos ##
  * tablas globales = [configuraciones_globales, rubro_contable, roles, permisos, sucursales, modelobase, fondos_fijos] estas tablas no dependen de ninguna y pueden existir independientemente de las demas.
  * tabla de usuarios debe heredar de modelobase y debe tener una relacion con sucursal y roles
  * tabla de configuraciones_de_usuario debe heredar de modelobase y debe tener una relacion con usuarios (aqui guardaremos las configuraciones del front end, ejemplo el color que el usaurio decida ver o el tema que quiera usar, etc)
  * sucursales debe heredar de modelobase y debe tener una relacion con fondos_fijos


  ***** diccionarios y conceptos *****
  * rubro_contable son globales para todas las sucursales 
  * fondos_fijos son independientes por sucursal
  *  ------ pestañas ------   son las tablas que podemos agregar o quitar de nuesro registro, y su funcion es solo para grupar informacion "exactamente como las pestañas del archivo CAJA MUESTRA.xlsx"
  *  ------ conceptos ------ son los nombres que se le dan a los movimientos de cada pestaña, y deben de estar relacionados con el rubro_contable y pertenecen a una sola pestaña, por ejemplo si en la pestaña "CAJA MUESTRA" hay un concepto "VENTA DE CAFE" este debe estar relacionado con el rubro_contable "VENTAS_CAFE" o "VENTAS_BEBIDAS" o "VENTAS_COMIDA" etc.  para poder generar el estado de resultados de forma automatica.
  * ------- detalles_pestañas ------ son campos adicionales que deben de contener las pestañas, ejemplo pestaña de sobrantes, lo que nos interesa es el total de dinero sobrante pero nos interesa saber almenos en esta pestaña quien es el responsable y de donde proviene el dinero sobrante. otro ejemplo es la pestaña de "VENTAS" que nos interesa el total de dinero vendido pero nos interesa saber almenos en esta pestaña quien es el responsable y de donde proviene el dinero vendido [las pesta;as son el detalle de la transaccion diaria y se consolida todo en el estado de resultados de forma automatica] estos conceptos o detalles puedes ser de cualquier tipo float, integer, string, boolean, date, datetime, etc. usar siempre float para valores monetarios y siempre usar decimales para valores monetarios.

  ***--- este sistema no es un sistema contable en el sentido estricto de la palabra, es un sistema de registro de transacciones diarias, para llevar el control del dinero fisico de sala, si el dinero va a bancos se registra como egreso porque sale de sala, si el dinero viene de bancos se registra como ingreso porque entra a sala, etc.