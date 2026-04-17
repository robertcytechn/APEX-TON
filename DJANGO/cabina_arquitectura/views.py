import platform
import shutil
import socket
import time
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import connections
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from configuraciones_globales.models import ConfiguracionGlobal, PadreRubroContable, RubroContable
from core.permisos import EsAdministrador, EsDirector
from fondos_fijos.models import FondoFijo
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario
from usuarios.servicios_correo_credenciales import enviar_correo_credenciales_usuario

from .serializers import (
    CentroControlEjecucionTareaSerializer,
    CentroControlEstadoAplicacionSerializer,
    ConfiguracionGlobalCabinaSerializer,
    ConfiguracionGlobalDirectorCabinaSerializer,
    OPCIONES_ESTADO_APLICACION_CENTRO_CONTROL,
    OPCIONES_TAREA_CELERY_CENTRO_CONTROL,
    PadreRubroContableCabinaSerializer,
    RolCabinaSerializer,
    RubroContableCabinaSerializer,
    SucursalDirectorCabinaSerializer,
    SucursalCabinaSerializer,
    UsuarioDirectorCabinaSerializer,
    UsuarioCabinaSerializer,
)

try:
    import psutil
except Exception:  # pragma: no cover - fallback en entornos sin psutil
    psutil = None


def respuesta_estandar(data=None, mensaje='Operacion exitosa', estado='success', codigo=status.HTTP_200_OK):
    return Response({'status': estado, 'message': mensaje, 'data': data}, status=codigo)


class BaseCabinaAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, EsAdministrador]


class BaseCabinaDirectorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, EsDirector]


class RolCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = RolCabinaSerializer(Rol.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Roles obtenidos.')

    def create(self, request):
        serializer = RolCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        return respuesta_estandar(data=RolCabinaSerializer(obj).data, mensaje='Rol obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        serializer = RolCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        serializer = RolCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rol actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rol.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Rol, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Rol eliminado (baja logica).')


class UsuarioCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = UsuarioCabinaSerializer(Usuario.objects.select_related('sucursal').all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Usuarios obtenidos.')

    def create(self, request):
        serializer = UsuarioCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        return respuesta_estandar(data=UsuarioCabinaSerializer(obj).data, mensaje='Usuario obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        serializer = UsuarioCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Usuario, pk=pk)
        serializer = UsuarioCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        usuario = get_object_or_404(Usuario, pk=pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return respuesta_estandar(mensaje='Usuario desactivado correctamente.')


class SucursalCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = SucursalCabinaSerializer(Sucursal.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Sucursales obtenidas.')

    def create(self, request):
        serializer = SucursalCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal creada.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        return respuesta_estandar(data=SucursalCabinaSerializer(obj).data, mensaje='Sucursal obtenida.')

    def update(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal actualizada.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        serializer = SucursalCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal actualizada parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar sucursal.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Sucursal, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Sucursal eliminada (baja logica).')


class ConfiguracionGlobalCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = ConfiguracionGlobalCabinaSerializer(ConfiguracionGlobal.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Configuraciones globales obtenidas.')

    def create(self, request):
        serializer = ConfiguracionGlobalCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global creada.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        return respuesta_estandar(data=ConfiguracionGlobalCabinaSerializer(obj).data, mensaje='Configuracion global obtenida.')

    def update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global actualizada.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        serializer = ConfiguracionGlobalCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Configuracion global actualizada parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar configuracion global.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(ConfiguracionGlobal, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Configuracion global eliminada (baja logica).')


class CentroControlAdminViewSet(BaseCabinaAdminViewSet):
    CLAVES_CONFIG = {
        'estado_aplicacion': ['ESTADO_APLICACION', 'ESTADO_APPLICACION'],
        'titulo': ['TITULO_ESTADO_APLICACION_POR_ACTUALIZACION'],
        'mensaje': ['MENSAJE_APLICACION_POR_ACTUALIZACION'],
        'etiqueta': ['ETIQUETA_POR_ACTUALIZACION'],
        'icono': ['ICONO_ACTUALIZACION'],
        'decoradores': ['DECORADORES_ACTUALIZACION'],
        'recomendaciones': ['RECOMENDACIONES_ACTUALIZACION'],
        'inicio_actualizacion': ['INICIO_ACTUALIZACION'],
        'fin_actualizacion': ['FIN_ACTUALIZACION'],
    }

    METADATOS_CONFIG = {
        'estado_aplicacion': {'tipo_valor': 'STRING', 'descripcion': 'Estado operativo global de la aplicacion.'},
        'titulo': {'tipo_valor': 'STRING', 'descripcion': 'Titulo principal de mantenimiento mostrado en frontend.'},
        'mensaje': {'tipo_valor': 'STRING', 'descripcion': 'Mensaje principal de mantenimiento mostrado en frontend.'},
        'etiqueta': {'tipo_valor': 'STRING', 'descripcion': 'Etiqueta operativa para la pantalla de mantenimiento.'},
        'icono': {'tipo_valor': 'STRING', 'descripcion': 'Icono PrimeVue para la pantalla de mantenimiento.'},
        'decoradores': {'tipo_valor': 'STRING', 'descripcion': 'Decoradores de mantenimiento separados por coma.'},
        'recomendaciones': {'tipo_valor': 'STRING', 'descripcion': 'Recomendaciones de mantenimiento separadas por coma.'},
        'inicio_actualizacion': {'tipo_valor': 'DATETIME', 'descripcion': 'Fecha y hora de inicio de actualizacion.'},
        'fin_actualizacion': {'tipo_valor': 'DATETIME', 'descripcion': 'Fecha y hora de fin de actualizacion.'},
    }

    PLANTILLAS_RAPIDAS = [
        {
            'clave': 'operacion_normal',
            'nombre': 'Operacion normal',
            'estado_aplicacion': 'PRODUCCION',
            'titulo': 'Sistema en operacion normal',
            'mensaje': 'La plataforma esta disponible para captura y consulta en tiempo real.',
            'etiqueta': 'Operacion habilitada',
            'icono': 'pi pi-check-circle',
            'decoradores': ['Servicios activos', 'Sin incidencias criticas'],
            'recomendaciones': ['Puedes continuar con tu operacion habitual.'],
        },
        {
            'clave': 'mantenimiento_general',
            'nombre': 'Mantenimiento general',
            'estado_aplicacion': 'mantenimiento_general',
            'titulo': 'Mantenimiento general del sistema',
            'mensaje': 'Estamos aplicando ajustes preventivos para mejorar estabilidad y rendimiento.',
            'etiqueta': 'Intervencion preventiva',
            'icono': 'pi pi-wrench',
            'decoradores': ['Ajustes de rendimiento', 'Reinicio de servicios', 'Validacion final'],
            'recomendaciones': ['Espera la reactivacion programada.', 'Evita recargas continuas durante la intervencion.'],
        },
        {
            'clave': 'actualizacion_software',
            'nombre': 'Actualizacion de software',
            'estado_aplicacion': 'actualizacion_software',
            'titulo': 'Actualizacion de software en progreso',
            'mensaje': 'Se estan desplegando nuevas funciones y correcciones de seguridad en el sistema.',
            'etiqueta': 'Actualizacion programada de software',
            'icono': 'pi pi-cloud-upload',
            'decoradores': ['Actualizacion de UX', 'Parches de seguridad', 'Monitoreo post-despliegue'],
            'recomendaciones': ['Espera el tiempo determinado para la reactivacion.', 'Consulta soporte si la ventana se extiende.'],
        },
        {
            'clave': 'mantenimiento_infraestructura',
            'nombre': 'Mantenimiento de infraestructura',
            'estado_aplicacion': 'mantenimiento_infraestructura',
            'titulo': 'Mantenimiento de infraestructura',
            'mensaje': 'Se estan optimizando recursos de red y servidores para mantener continuidad operativa.',
            'etiqueta': 'Operacion de plataforma',
            'icono': 'pi pi-server',
            'decoradores': ['Ajuste de red', 'Balanceo de carga', 'Monitoreo de nodos'],
            'recomendaciones': ['Los servicios pueden responder de forma intermitente.', 'Reintenta acceso al finalizar la ventana.'],
        },
        {
            'clave': 'migracion_datos',
            'nombre': 'Migracion de datos',
            'estado_aplicacion': 'migracion_datos',
            'titulo': 'Migracion de datos en ejecucion',
            'mensaje': 'Estamos migrando informacion para mejorar consistencia y trazabilidad.',
            'etiqueta': 'Proceso critico de datos',
            'icono': 'pi pi-database',
            'decoradores': ['Respaldo incremental', 'Validacion de integridad', 'Sincronizacion de tablas'],
            'recomendaciones': ['No intentes modificar registros durante la migracion.', 'Escala a soporte si detectas datos faltantes.'],
        },
        {
            'clave': 'contingencia_operativa',
            'nombre': 'Contingencia operativa',
            'estado_aplicacion': 'contingencia_operativa',
            'titulo': 'Contingencia operativa temporal',
            'mensaje': 'Se detecto una incidencia tecnica y estamos aplicando acciones de estabilizacion.',
            'etiqueta': 'Atencion prioritaria',
            'icono': 'pi pi-exclamation-triangle',
            'decoradores': ['Diagnostico activo', 'Mitigacion de impacto', 'Recuperacion de servicio'],
            'recomendaciones': ['Mantente atento al tiempo estimado de recuperacion.', 'Reporta a administracion si persiste la incidencia.'],
        },
    ]

    TAREAS_DISPONIBLES = [
        {
            'clave': 'cerrar_dia_contable',
            'nombre': 'Cerrar dia contable',
            'descripcion': 'Cierra automaticamente reportes del dia contable para todas las sucursales activas.',
            'parametros': [],
        },
        {
            'clave': 'enviar_resumen_diario_ejecutivo',
            'nombre': 'Enviar resumen diario ejecutivo',
            'descripcion': 'Genera y envia correo diario ejecutivo; puede forzarse para una fecha contable.',
            'parametros': ['fecha_contable'],
        },
        {
            'clave': 'enviar_cierre_mensual_ejecutivo',
            'nombre': 'Enviar cierre mensual ejecutivo',
            'descripcion': 'Genera y envia correo de cierre mensual; acepta anio y mes opcionales.',
            'parametros': ['anio', 'mes'],
        },
        {
            'clave': 'sincronizar_horario_correo_diario',
            'nombre': 'Sincronizar horario de correo diario',
            'descripcion': 'Sincroniza en django_celery_beat la hora de envio diario desde HORARIO_CIERRE.',
            'parametros': [],
        },
        {
            'clave': 'ejecutar_backup_bd',
            'nombre': 'Ejecutar respaldo de base de datos',
            'descripcion': 'Genera respaldo MySQL comprimido y notifica resultado por correo.',
            'parametros': [],
        },
    ]

    @staticmethod
    def _normalizar_clave(valor):
        return str(valor or '').strip().upper()

    @staticmethod
    def _texto_a_lista(texto):
        valor = str(texto or '').strip()
        if not valor:
            return []
        return [item.strip() for item in valor.split(',') if item.strip()]

    @staticmethod
    def _lista_a_texto(valores):
        return ', '.join([str(valor).strip() for valor in (valores or []) if str(valor).strip()])

    @staticmethod
    def _formatear_datetime(valor):
        if not valor:
            return ''
        if timezone.is_naive(valor):
            valor = timezone.make_aware(valor, timezone.get_current_timezone())
        return timezone.localtime(valor).replace(microsecond=0).isoformat()

    @staticmethod
    def _bytes_a_mb(valor_bytes):
        return round(float(valor_bytes) / (1024 * 1024), 2)

    @staticmethod
    def _bytes_a_gb(valor_bytes):
        return round(float(valor_bytes) / (1024 * 1024 * 1024), 2)

    def _obtener_mapa_configuraciones(self):
        mapa = {}
        for configuracion in ConfiguracionGlobal.objects.all():
            mapa[self._normalizar_clave(configuracion.clave)] = configuracion
        return mapa

    def _buscar_configuracion(self, mapa, aliases):
        for alias in aliases:
            configuracion = mapa.get(self._normalizar_clave(alias))
            if configuracion:
                return configuracion
        return None

    def _leer_valor_configuracion(self, mapa, campo, valor_default=''):
        configuracion = self._buscar_configuracion(mapa, self.CLAVES_CONFIG[campo])
        if not configuracion or configuracion.valor is None:
            return valor_default
        return str(configuracion.valor)

    def _guardar_valor_configuracion(self, mapa, campo, valor, usuario):
        aliases = self.CLAVES_CONFIG[campo]
        metadatos = self.METADATOS_CONFIG[campo]
        configuracion = self._buscar_configuracion(mapa, aliases)
        valor_texto = '' if valor is None else str(valor)

        if configuracion:
            configuracion.valor = valor_texto
            configuracion.tipo_valor = metadatos['tipo_valor']
            configuracion.descripcion = metadatos['descripcion']
            configuracion.visible_para_director = False
            configuracion.actualizado_por = usuario
            configuracion.save(update_fields=['valor', 'tipo_valor', 'descripcion', 'visible_para_director', 'actualizado_por', 'actualizado_en'])
            return configuracion

        configuracion = ConfiguracionGlobal.objects.create(
            clave=aliases[0],
            valor=valor_texto,
            tipo_valor=metadatos['tipo_valor'],
            descripcion=metadatos['descripcion'],
            visible_para_director=False,
            creado_por=usuario,
            actualizado_por=usuario,
        )
        mapa[self._normalizar_clave(configuracion.clave)] = configuracion
        return configuracion

    def _plantilla_por_estado(self, estado):
        estado_normalizado = str(estado or '').strip().lower()
        for plantilla in self.PLANTILLAS_RAPIDAS:
            if str(plantilla.get('estado_aplicacion') or '').strip().lower() == estado_normalizado:
                return plantilla

        for plantilla in self.PLANTILLAS_RAPIDAS:
            if plantilla.get('estado_aplicacion') == 'actualizacion_software':
                return plantilla

        return self.PLANTILLAS_RAPIDAS[0]

    def _construir_catalogos_predefinidos(self):
        titulos = []
        mensajes = []
        etiquetas = []
        iconos = []
        decoradores = []
        recomendaciones = []

        for plantilla in self.PLANTILLAS_RAPIDAS:
            titulo = plantilla.get('titulo')
            mensaje = plantilla.get('mensaje')
            etiqueta = plantilla.get('etiqueta')
            icono = plantilla.get('icono')

            if titulo and titulo not in titulos:
                titulos.append(titulo)
            if mensaje and mensaje not in mensajes:
                mensajes.append(mensaje)
            if etiqueta and etiqueta not in etiquetas:
                etiquetas.append(etiqueta)
            if icono and icono not in iconos:
                iconos.append(icono)

            for decorador in plantilla.get('decoradores', []):
                if decorador and decorador not in decoradores:
                    decoradores.append(decorador)
            for recomendacion in plantilla.get('recomendaciones', []):
                if recomendacion and recomendacion not in recomendaciones:
                    recomendaciones.append(recomendacion)

        return {
            'estados': [
                {'value': valor, 'label': etiqueta}
                for valor, etiqueta in OPCIONES_ESTADO_APLICACION_CENTRO_CONTROL
            ],
            'titulos': titulos,
            'mensajes': mensajes,
            'etiquetas': etiquetas,
            'iconos': iconos,
            'decoradores': decoradores,
            'recomendaciones': recomendaciones,
            'plantillas': self.PLANTILLAS_RAPIDAS,
        }

    def _construir_payload_estado(self, mapa):
        estado_actual = self._leer_valor_configuracion(mapa, 'estado_aplicacion', 'PRODUCCION') or 'PRODUCCION'
        plantilla_default = self._plantilla_por_estado(estado_actual)

        valor_decoradores = self._texto_a_lista(
            self._leer_valor_configuracion(
                mapa,
                'decoradores',
                self._lista_a_texto(plantilla_default.get('decoradores', []))
            )
        )
        valor_recomendaciones = self._texto_a_lista(
            self._leer_valor_configuracion(
                mapa,
                'recomendaciones',
                self._lista_a_texto(plantilla_default.get('recomendaciones', []))
            )
        )

        return {
            'estado_aplicacion': estado_actual,
            'titulo': self._leer_valor_configuracion(mapa, 'titulo', plantilla_default.get('titulo') or ''),
            'mensaje': self._leer_valor_configuracion(mapa, 'mensaje', plantilla_default.get('mensaje') or ''),
            'etiqueta': self._leer_valor_configuracion(mapa, 'etiqueta', plantilla_default.get('etiqueta') or ''),
            'icono': self._leer_valor_configuracion(mapa, 'icono', plantilla_default.get('icono') or ''),
            'decoradores': valor_decoradores,
            'recomendaciones': valor_recomendaciones,
            'inicio_actualizacion': self._leer_valor_configuracion(mapa, 'inicio_actualizacion', ''),
            'fin_actualizacion': self._leer_valor_configuracion(mapa, 'fin_actualizacion', ''),
            'catalogos': self._construir_catalogos_predefinidos(),
        }

    @staticmethod
    def _encolar_tarea(clave_tarea, datos):
        from reportes_diarios.tareas import (
            cerrar_dia_contable,
            ejecutar_backup_bd,
            enviar_cierre_mensual_ejecutivo,
            enviar_resumen_diario_ejecutivo,
            sincronizar_horario_correo_diario,
        )

        if clave_tarea == 'cerrar_dia_contable':
            return cerrar_dia_contable.delay(), {}

        if clave_tarea == 'enviar_resumen_diario_ejecutivo':
            fecha_contable = datos.get('fecha_contable')
            parametros = {'fecha_contable': fecha_contable.isoformat()} if fecha_contable else {}
            if fecha_contable:
                return enviar_resumen_diario_ejecutivo.delay(fecha_contable.isoformat()), parametros
            return enviar_resumen_diario_ejecutivo.delay(), parametros

        if clave_tarea == 'enviar_cierre_mensual_ejecutivo':
            anio = datos.get('anio')
            mes = datos.get('mes')
            parametros = {'anio': anio, 'mes': mes} if anio is not None and mes is not None else {}
            if anio is not None and mes is not None:
                return enviar_cierre_mensual_ejecutivo.delay(int(anio), int(mes)), parametros
            return enviar_cierre_mensual_ejecutivo.delay(), parametros

        if clave_tarea == 'sincronizar_horario_correo_diario':
            return sincronizar_horario_correo_diario.delay(), {}

        if clave_tarea == 'ejecutar_backup_bd':
            return ejecutar_backup_bd.delay(), {}

        raise ValueError('La tarea solicitada no esta permitida en Centro de Control.')

    def list(self, request):
        data = {
            'modulo': 'Centro de Control',
            'acciones_disponibles': [
                'GET/PUT cabina-arquitectura/centro-control/estado-aplicacion/',
                'GET cabina-arquitectura/centro-control/tareas-disponibles/',
                'POST cabina-arquitectura/centro-control/ejecutar-tarea/',
                'GET cabina-arquitectura/centro-control/salud-servidor/',
            ],
        }
        return respuesta_estandar(data=data, mensaje='Centro de Control disponible para administracion.')

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='estado-aplicacion')
    def estado_aplicacion(self, request):
        if request.method == 'GET':
            data = self._construir_payload_estado(self._obtener_mapa_configuraciones())
            return respuesta_estandar(data=data, mensaje='Estado de aplicacion obtenido correctamente.')

        serializer = CentroControlEstadoAplicacionSerializer(data=request.data)
        if not serializer.is_valid():
            return respuesta_estandar(
                data=serializer.errors,
                mensaje='Error de validacion al guardar estado de aplicacion.',
                estado='error',
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        datos = serializer.validated_data
        estado_aplicacion = datos['estado_aplicacion']
        inicio_actualizacion = self._formatear_datetime(datos.get('inicio_actualizacion'))
        fin_actualizacion = self._formatear_datetime(datos.get('fin_actualizacion'))

        if estado_aplicacion == 'PRODUCCION':
            inicio_actualizacion = ''
            fin_actualizacion = ''

        mapa = self._obtener_mapa_configuraciones()
        self._guardar_valor_configuracion(mapa, 'estado_aplicacion', estado_aplicacion, request.user)
        self._guardar_valor_configuracion(mapa, 'titulo', datos['titulo'], request.user)
        self._guardar_valor_configuracion(mapa, 'mensaje', datos['mensaje'], request.user)
        self._guardar_valor_configuracion(mapa, 'etiqueta', datos['etiqueta'], request.user)
        self._guardar_valor_configuracion(mapa, 'icono', datos['icono'], request.user)
        self._guardar_valor_configuracion(mapa, 'decoradores', self._lista_a_texto(datos.get('decoradores')), request.user)
        self._guardar_valor_configuracion(mapa, 'recomendaciones', self._lista_a_texto(datos.get('recomendaciones')), request.user)
        self._guardar_valor_configuracion(mapa, 'inicio_actualizacion', inicio_actualizacion, request.user)
        self._guardar_valor_configuracion(mapa, 'fin_actualizacion', fin_actualizacion, request.user)

        payload_actualizado = self._construir_payload_estado(self._obtener_mapa_configuraciones())
        return respuesta_estandar(data=payload_actualizado, mensaje='Estado de aplicacion actualizado correctamente.')

    @action(detail=False, methods=['get'], url_path='tareas-disponibles')
    def tareas_disponibles(self, request):
        data = {
            'opciones': [
                {'value': valor, 'label': etiqueta}
                for valor, etiqueta in OPCIONES_TAREA_CELERY_CENTRO_CONTROL
            ],
            'tareas': self.TAREAS_DISPONIBLES,
        }
        return respuesta_estandar(data=data, mensaje='Tareas disponibles obtenidas correctamente.')

    @action(detail=False, methods=['post'], url_path='ejecutar-tarea')
    def ejecutar_tarea(self, request):
        serializer = CentroControlEjecucionTareaSerializer(data=request.data)
        if not serializer.is_valid():
            return respuesta_estandar(
                data=serializer.errors,
                mensaje='Error de validacion para ejecutar la tarea solicitada.',
                estado='error',
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        datos = serializer.validated_data
        clave_tarea = datos['tarea']

        try:
            resultado_tarea, parametros = self._encolar_tarea(clave_tarea, datos)
        except Exception as exc:
            return respuesta_estandar(
                data={'tarea': clave_tarea, 'error': str(exc)},
                mensaje='No fue posible encolar la tarea en Celery.',
                estado='error',
                codigo=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = {
            'tarea': clave_tarea,
            'task_id': str(getattr(resultado_tarea, 'id', '')),
            'parametros': parametros,
            'solicitado_por': request.user.username,
            'solicitado_en': timezone.localtime(timezone.now()).isoformat(),
        }
        return respuesta_estandar(
            data=data,
            mensaje='Tarea enviada a cola Celery correctamente.',
            codigo=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['get'], url_path='salud-servidor')
    def salud_servidor(self, request):
        ruta_disco = Path(settings.BASE_DIR).anchor or str(Path(settings.BASE_DIR))
        disco_total, disco_usado, disco_libre = shutil.disk_usage(ruta_disco)

        recursos = {
            'cpu_porcentaje': None,
            'memoria_total_mb': None,
            'memoria_disponible_mb': None,
            'memoria_usada_porcentaje': None,
            'disco_ruta': ruta_disco,
            'disco_total_gb': self._bytes_a_gb(disco_total),
            'disco_usado_gb': self._bytes_a_gb(disco_usado),
            'disco_libre_gb': self._bytes_a_gb(disco_libre),
            'disco_usado_porcentaje': round((disco_usado / disco_total) * 100, 2) if disco_total else 0,
            'psutil_disponible': bool(psutil),
        }

        if psutil:
            memoria = psutil.virtual_memory()
            recursos.update(
                {
                    'cpu_porcentaje': round(float(psutil.cpu_percent(interval=0.25)), 2),
                    'memoria_total_mb': self._bytes_a_mb(memoria.total),
                    'memoria_disponible_mb': self._bytes_a_mb(memoria.available),
                    'memoria_usada_porcentaje': round(float(memoria.percent), 2),
                }
            )

        db_config = settings.DATABASES.get('default', {})
        inicio_db = time.perf_counter()
        estado_bd = {
            'ok': False,
            'motor': db_config.get('ENGINE'),
            'nombre': db_config.get('NAME'),
            'host': db_config.get('HOST') or '127.0.0.1',
            'puerto': str(db_config.get('PORT') or ''),
            'latencia_ms': None,
            'mensaje': 'Sin verificar',
        }
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            estado_bd['ok'] = True
            estado_bd['latencia_ms'] = round((time.perf_counter() - inicio_db) * 1000, 2)
            estado_bd['mensaje'] = 'Conexion a base de datos establecida correctamente.'
        except Exception as exc:
            estado_bd['mensaje'] = f'Error de conexion a base de datos: {exc}'

        estado_celery = {
            'ok': False,
            'workers': [],
            'broker_host': None,
            'broker_puerto': None,
            'broker_alcanzable': False,
            'mensaje': 'Sin verificar',
        }
        try:
            from backend.celery import app as celery_app

            broker_url = str(getattr(settings, 'CELERY_BROKER_URL', '') or '')
            broker_parseado = urlparse(broker_url)
            broker_host = broker_parseado.hostname or '127.0.0.1'
            broker_puerto = int(broker_parseado.port or 5672)

            estado_celery['broker_host'] = broker_host
            estado_celery['broker_puerto'] = broker_puerto

            try:
                with socket.create_connection((broker_host, broker_puerto), timeout=1.0):
                    estado_celery['broker_alcanzable'] = True
            except OSError as exc_broker:
                estado_celery['mensaje'] = (
                    f'Broker Celery no disponible en {broker_host}:{broker_puerto}. '
                    f'Inicia RabbitMQ para habilitar workers y beat. Detalle: {exc_broker}'
                )

            if estado_celery['broker_alcanzable']:
                respuesta_ping = celery_app.control.ping(timeout=1.0)
                estado_celery['ok'] = bool(respuesta_ping)
                estado_celery['workers'] = respuesta_ping or []
                estado_celery['mensaje'] = (
                    'Workers Celery en linea.'
                    if respuesta_ping
                    else 'Broker disponible, pero no se detectaron workers Celery activos.'
                )
        except Exception as exc:
            estado_celery['mensaje'] = f'No fue posible consultar estado de Celery: {exc}'

        data = {
            'fecha_hora_servidor': timezone.localtime(timezone.now()).isoformat(),
            'servidor': {
                'hostname': socket.gethostname(),
                'plataforma': platform.platform(),
                'python_version': platform.python_version(),
            },
            'recursos': recursos,
            'base_datos': estado_bd,
            'celery': estado_celery,
            'estado_general': 'saludable' if estado_bd['ok'] and estado_celery['ok'] else 'atencion',
        }
        return respuesta_estandar(data=data, mensaje='Salud de servidor obtenida correctamente.')


class RubroContableCabinaViewSet(BaseCabinaAdminViewSet):
    @action(detail=False, methods=['get'], url_path='opciones')
    def opciones(self, request):
        campo_tipo = RubroContable._meta.get_field('tipo')

        opciones_padre = [
            {
                'id': padre.id,
                'label': padre.nombre,
                'value': padre.id,
                'clave': padre.clave,
                'nombre': padre.nombre,
            }
            for padre in PadreRubroContable.objects.all().order_by('nombre')
        ]
        opciones_tipo = [{'label': etiqueta, 'value': valor} for valor, etiqueta in campo_tipo.choices]

        data = {
            'padres': opciones_padre,
            'tipos': opciones_tipo,
        }
        return respuesta_estandar(data=data, mensaje='Opciones de rubro contable obtenidas.')

    def list(self, request):
        data = RubroContableCabinaSerializer(RubroContable.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Rubros contables obtenidos.')

    def create(self, request):
        serializer = RubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        return respuesta_estandar(data=RubroContableCabinaSerializer(obj).data, mensaje='Rubro contable obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Rubro contable eliminado (baja logica).')


class PadreRubroContableCabinaViewSet(BaseCabinaAdminViewSet):
    def list(self, request):
        data = PadreRubroContableCabinaSerializer(PadreRubroContable.objects.all().order_by('nombre'), many=True).data
        return respuesta_estandar(data=data, mensaje='Padres de rubro contable obtenidos.')

    def create(self, request):
        serializer = PadreRubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable creado.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        return respuesta_estandar(data=PadreRubroContableCabinaSerializer(obj).data, mensaje='Padre de rubro contable obtenido.')

    def update(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable actualizado.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        serializer = PadreRubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Padre de rubro contable actualizado parcialmente.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar padre de rubro contable.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        obj = get_object_or_404(PadreRubroContable, pk=pk)
        if obj.rubros_contables.exists():
            return respuesta_estandar(
                data={'rubros_asociados': obj.rubros_contables.count()},
                mensaje='No se puede eliminar el padre porque tiene rubros contables asociados.',
                estado='error',
                codigo=status.HTTP_400_BAD_REQUEST,
            )

        obj.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje='Padre de rubro contable eliminado (baja logica).')


class FondoFijoDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def list(self, request):
        data = [
            {
                'id': fondo.id,
                'nombre': fondo.nombre,
                'descripcion': fondo.descripcion,
            }
            for fondo in FondoFijo.objects.all().order_by('nombre')
        ]
        return respuesta_estandar(data=data, mensaje='Catalogo de fondos fijos obtenido.')


class SucursalDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def list(self, request):
        queryset = Sucursal.objects.all().prefetch_related('asignaciones_fondos_fijos__fondo_fijo')
        data = SucursalDirectorCabinaSerializer(queryset, many=True).data
        return respuesta_estandar(data=data, mensaje='Sucursales obtenidas para cabina de director.')

    def create(self, request):
        serializer = SucursalDirectorCabinaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Sucursal creada y fondos fijos asignados.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear sucursal para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Sucursal.objects.prefetch_related('asignaciones_fondos_fijos__fondo_fijo'), pk=pk)
        return respuesta_estandar(data=SucursalDirectorCabinaSerializer(obj).data, mensaje='Sucursal obtenida para cabina de director.')


class UsuarioDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def obtener_queryset_operativos(self):
        return Usuario.objects.select_related('sucursal').filter(
            Q(usuario_roles__rol__nombre__iexact='CONTADOR') | Q(usuario_roles__rol__nombre__iexact='GERENTE')
        ).distinct()

    @action(detail=False, methods=['get'], url_path='roles-disponibles')
    def roles_disponibles(self, request):
        roles = Rol.objects.filter(
            Q(nombre__iexact='CONTADOR') | Q(nombre__iexact='GERENTE')
        ).order_by('nombre')
        data = [{'id': rol.id, 'nombre': rol.nombre} for rol in roles]
        return respuesta_estandar(data=data, mensaje='Roles disponibles para director obtenidos.')

    def list(self, request):
        queryset = self.obtener_queryset_operativos()
        data = UsuarioDirectorCabinaSerializer(queryset, many=True).data
        return respuesta_estandar(data=data, mensaje='Usuarios de captura operativa obtenidos.')

    def create(self, request):
        serializer = UsuarioDirectorCabinaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            usuario = serializer.save()
            contrasena_generada = getattr(serializer, '_contrasena_generada', None)

            resultado_correo = enviar_correo_credenciales_usuario(
                usuario=usuario,
                contrasena_visible=contrasena_generada,
                es_reinicio=False,
            )

            data = UsuarioDirectorCabinaSerializer(
                usuario,
                context={'contrasena_generada': contrasena_generada}
            ).data
            data['correo_enviado'] = resultado_correo.get('enviado', False)
            data['detalle_correo'] = resultado_correo.get('error', '')

            mensaje = 'Usuario creado para captura operativa y correo enviado.'
            if not data['correo_enviado']:
                mensaje = 'Usuario creado para captura operativa, pero no se pudo enviar el correo.'

            return respuesta_estandar(data=data, mensaje=mensaje, codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear usuario para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        data = UsuarioDirectorCabinaSerializer(obj).data
        return respuesta_estandar(data=data, mensaje='Usuario operativo obtenido para director.')

    def update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        serializer = UsuarioDirectorCabinaSerializer(obj, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario operativo actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar usuario operativo.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)
        serializer = UsuarioDirectorCabinaSerializer(obj, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return respuesta_estandar(data=serializer.data, mensaje='Usuario operativo actualizado parcialmente para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar parcialmente usuario operativo.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reiniciar-password')
    def reiniciar_password(self, request, pk=None):
        usuario = get_object_or_404(self.obtener_queryset_operativos(), pk=pk)

        contrasena_generada = UsuarioDirectorCabinaSerializer.generar_contrasena_numerica()
        usuario.set_password(contrasena_generada)
        usuario.requiere_cambio_password = True
        usuario.actualizado_por = request.user
        usuario.save(update_fields=['password', 'requiere_cambio_password', 'actualizado_por', 'actualizado_en'])

        resultado_correo = enviar_correo_credenciales_usuario(
            usuario=usuario,
            contrasena_visible=contrasena_generada,
            es_reinicio=True,
        )

        data = UsuarioDirectorCabinaSerializer(
            usuario,
            context={'contrasena_generada': contrasena_generada}
        ).data
        data['correo_enviado'] = resultado_correo.get('enviado', False)
        data['detalle_correo'] = resultado_correo.get('error', '')

        mensaje = 'Contrasena reiniciada y correo enviado al usuario.'
        if not data['correo_enviado']:
            mensaje = 'Contrasena reiniciada, pero no se pudo enviar el correo al usuario.'

        return respuesta_estandar(data=data, mensaje=mensaje)


class ConfiguracionGlobalDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    def obtener_queryset_visible_director(self):
        return ConfiguracionGlobal.objects.filter(visible_para_director=True)

    def list(self, request):
        queryset = self.obtener_queryset_visible_director()
        data = ConfiguracionGlobalDirectorCabinaSerializer(queryset, many=True).data
        return respuesta_estandar(data=data, mensaje='Configuraciones globales obtenidas para director.')

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_visible_director(), pk=pk)
        return respuesta_estandar(data=ConfiguracionGlobalDirectorCabinaSerializer(obj).data, mensaje='Configuracion global obtenida para director.')

    def create(self, request):
        return respuesta_estandar(
            mensaje='No tienes permiso para crear variables globales.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )

    def update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_visible_director(), pk=pk)
        serializer = ConfiguracionGlobalDirectorCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Valor de configuracion global actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar valor de configuracion.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(self.obtener_queryset_visible_director(), pk=pk)
        serializer = ConfiguracionGlobalDirectorCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Valor de configuracion global actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar valor de configuracion.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        return respuesta_estandar(
            mensaje='No tienes permiso para eliminar variables globales.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )


class RubroContableDirectorCabinaViewSet(BaseCabinaDirectorViewSet):
    @action(detail=False, methods=['get'], url_path='opciones')
    def opciones(self, request):
        campo_tipo = RubroContable._meta.get_field('tipo')

        opciones_padre = [
            {
                'id': padre.id,
                'label': padre.nombre,
                'value': padre.id,
                'clave': padre.clave,
                'nombre': padre.nombre,
            }
            for padre in PadreRubroContable.objects.all().order_by('nombre')
        ]
        opciones_tipo = [{'label': etiqueta, 'value': valor} for valor, etiqueta in campo_tipo.choices]

        data = {
            'padres': opciones_padre,
            'tipos': opciones_tipo,
        }
        return respuesta_estandar(data=data, mensaje='Opciones de rubro contable obtenidas para director.')

    def list(self, request):
        data = RubroContableCabinaSerializer(RubroContable.objects.all(), many=True).data
        return respuesta_estandar(data=data, mensaje='Rubros contables obtenidos para director.')

    def create(self, request):
        serializer = RubroContableCabinaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable creado para director.', codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=serializer.errors, mensaje='Error al crear rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        return respuesta_estandar(data=RubroContableCabinaSerializer(obj).data, mensaje='Rubro contable obtenido para director.')

    def update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = get_object_or_404(RubroContable, pk=pk)
        serializer = RubroContableCabinaSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(actualizado_por=request.user)
            return respuesta_estandar(data=serializer.data, mensaje='Rubro contable actualizado para director.')
        return respuesta_estandar(data=serializer.errors, mensaje='Error al actualizar rubro contable para director.', estado='error', codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        return respuesta_estandar(
            mensaje='No tienes permiso para eliminar rubros contables desde cabina de director.',
            estado='error',
            codigo=status.HTTP_403_FORBIDDEN,
        )
