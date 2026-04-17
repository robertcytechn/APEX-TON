from types import SimpleNamespace
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from configuraciones_globales.models import ConfiguracionGlobal
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario, UsuarioRol


class CabinaArquitecturaTests(APITestCase):
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='ADMINISTRADOR')
        self.rol_director = Rol.objects.create(nombre='DIRECTOR')

        self.usuario_admin = Usuario.objects.create_user(
            username='admin_cfg',
            password='admin1234',
            nombre='Administrador Configuraciones',
            correo='admin_cfg@binsur.mx',
            is_active=True,
        )
        UsuarioRol.objects.create(usuario=self.usuario_admin, rol=self.rol_admin)

        self.usuario_director = Usuario.objects.create_user(
            username='director_cfg',
            password='director1234',
            nombre='Director Configuraciones',
            correo='director_cfg@binsur.mx',
            is_active=True,
        )
        UsuarioRol.objects.create(usuario=self.usuario_director, rol=self.rol_director)

        self.sucursal_centro_control = Sucursal.objects.create(
            nombre='Casino Centro Control',
            clave='CCC-001',
        )

    def test_director_solo_lista_variables_visibles(self):
        ConfiguracionGlobal.objects.create(
            clave='CFG_VISIBLE_DIRECTOR',
            valor='valor_visible',
            tipo_valor='STRING',
            visible_para_director=True,
        )
        ConfiguracionGlobal.objects.create(
            clave='CFG_SOLO_ADMIN',
            valor='valor_oculto',
            tipo_valor='STRING',
            visible_para_director=False,
        )

        self.client.force_authenticate(user=self.usuario_director)
        url = '/api/cabina-arquitectura/director/configuraciones-globales/'
        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')
        data = respuesta.data.get('data') or []
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get('clave'), 'CFG_VISIBLE_DIRECTOR')

    def test_director_no_puede_modificar_variable_oculta(self):
        configuracion_oculta = ConfiguracionGlobal.objects.create(
            clave='CFG_OCULTA_DIRECTOR',
            valor='inicial',
            tipo_valor='STRING',
            visible_para_director=False,
        )

        self.client.force_authenticate(user=self.usuario_director)
        url = f'/api/cabina-arquitectura/director/configuraciones-globales/{configuracion_oculta.id}/'
        respuesta = self.client.patch(url, {'valor': 'nuevo_valor'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

        configuracion_oculta.refresh_from_db()
        self.assertEqual(configuracion_oculta.valor, 'inicial')

    def test_admin_puede_crear_variable_solo_admin(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/configuraciones-globales/'
        payload = {
            'clave': 'CFG_MANTENIMIENTO_PRIVADO',
            'valor': 'true',
            'tipo_valor': 'BOOLEAN',
            'descripcion': 'Bandera sensible visible solo para administracion.',
            'visible_para_director': False,
        }

        respuesta = self.client.post(url, payload, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data.get('status'), 'success')

        configuracion = ConfiguracionGlobal.objects.get(clave='CFG_MANTENIMIENTO_PRIVADO')
        self.assertFalse(configuracion.visible_para_director)

    def test_director_no_puede_acceder_centro_control(self):
        self.client.force_authenticate(user=self.usuario_director)
        url = '/api/cabina-arquitectura/centro-control/estado-aplicacion/'
        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_consulta_estado_centro_control(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/estado-aplicacion/'
        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')
        data = respuesta.data.get('data') or {}
        self.assertIn('estado_aplicacion', data)
        self.assertIn('catalogos', data)
        self.assertIn('plantillas', data.get('catalogos', {}))

    def test_admin_actualiza_estado_centro_control(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/estado-aplicacion/'
        payload = {
            'estado_aplicacion': 'actualizacion_software',
            'titulo': 'Actualizacion controlada',
            'mensaje': 'Se aplican mejoras para reforzar estabilidad.',
            'etiqueta': 'Ventana tecnica',
            'icono': 'pi pi-cloud-upload',
            'decoradores': ['Parches', 'Monitoreo'],
            'recomendaciones': ['Espera reactivacion', 'No recargar pestañas'],
            'inicio_actualizacion': '2026-04-16T10:00:00',
            'fin_actualizacion': '2026-04-16T12:00:00',
        }

        respuesta = self.client.put(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')

        cfg_estado = ConfiguracionGlobal.objects.get(clave='ESTADO_APLICACION')
        cfg_decoradores = ConfiguracionGlobal.objects.get(clave='DECORADORES_ACTUALIZACION')
        self.assertEqual(cfg_estado.valor, 'actualizacion_software')
        self.assertEqual(cfg_decoradores.valor, 'Parches, Monitoreo')
        self.assertFalse(cfg_estado.visible_para_director)

    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._obtener_diagnostico_celery_basico')
    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._encolar_tarea')
    def test_admin_ejecuta_tarea_manual_centro_control(self, mock_encolar_tarea, mock_diagnostico_celery):
        mock_encolar_tarea.return_value = (SimpleNamespace(id='task-123'), {'anio': 2026, 'mes': 4})
        mock_diagnostico_celery.return_value = {
            'ok': True,
            'workers': ['worker@binsur'],
            'workers_detectados': 1,
            'broker_url': 'amqp://usuario:***@127.0.0.1:5672//',
            'broker_host': '127.0.0.1',
            'broker_puerto': 5672,
            'broker_alcanzable': True,
            'mensaje': 'Workers Celery en linea.',
        }

        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/ejecutar-tarea/'
        payload = {
            'tarea': 'enviar_cierre_mensual_ejecutivo',
            'anio': 2026,
            'mes': 4,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(respuesta.data.get('status'), 'success')
        self.assertEqual((respuesta.data.get('data') or {}).get('task_id'), 'task-123')
        mock_encolar_tarea.assert_called_once()

    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._obtener_diagnostico_celery_basico')
    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._encolar_tarea')
    def test_rol_admin_compatible_puede_ejecutar_tarea_manual(self, mock_encolar_tarea, mock_diagnostico_celery):
        mock_encolar_tarea.return_value = (SimpleNamespace(id='task-456'), {})
        mock_diagnostico_celery.return_value = {
            'ok': True,
            'workers': ['worker@binsur'],
            'workers_detectados': 1,
            'broker_url': 'amqp://usuario:***@127.0.0.1:5672//',
            'broker_host': '127.0.0.1',
            'broker_puerto': 5672,
            'broker_alcanzable': True,
            'mensaje': 'Workers Celery en linea.',
        }

        rol_admin_compatible = Rol.objects.create(nombre='ADMIN')
        usuario_admin_compatible = Usuario.objects.create_user(
            username='admin_alias_cfg',
            password='admin1234',
            nombre='Administrador Compatible',
            correo='admin_alias_cfg@binsur.mx',
            is_active=True,
        )
        UsuarioRol.objects.create(usuario=usuario_admin_compatible, rol=rol_admin_compatible)

        self.client.force_authenticate(user=usuario_admin_compatible)
        url = '/api/cabina-arquitectura/centro-control/ejecutar-tarea/'
        payload = {'tarea': 'sincronizar_horario_correo_diario'}

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual((respuesta.data.get('data') or {}).get('task_id'), 'task-456')

    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._obtener_diagnostico_celery_basico')
    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._encolar_tarea')
    def test_staff_puede_ejecutar_tarea_manual_centro_control(self, mock_encolar_tarea, mock_diagnostico_celery):
        mock_encolar_tarea.return_value = (SimpleNamespace(id='task-789'), {})
        mock_diagnostico_celery.return_value = {
            'ok': True,
            'workers': ['worker@binsur'],
            'workers_detectados': 1,
            'broker_url': 'amqp://usuario:***@127.0.0.1:5672//',
            'broker_host': '127.0.0.1',
            'broker_puerto': 5672,
            'broker_alcanzable': True,
            'mensaje': 'Workers Celery en linea.',
        }

        usuario_staff = Usuario.objects.create_user(
            username='staff_cfg',
            password='staff1234',
            nombre='Staff Centro Control',
            correo='staff_cfg@binsur.mx',
            is_active=True,
            is_staff=True,
        )

        self.client.force_authenticate(user=usuario_staff)
        url = '/api/cabina-arquitectura/centro-control/ejecutar-tarea/'
        payload = {'tarea': 'ejecutar_backup_bd'}

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual((respuesta.data.get('data') or {}).get('task_id'), 'task-789')

    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._obtener_diagnostico_celery_basico')
    @patch('cabina_arquitectura.views.CentroControlAdminViewSet._encolar_tarea')
    def test_admin_ejecuta_tarea_manual_con_filtro_casino(self, mock_encolar_tarea, mock_diagnostico_celery):
        mock_encolar_tarea.return_value = (
            SimpleNamespace(id='task-casino-001'),
            {
                'fecha_contable': '2026-04-16',
                'sucursal_id': self.sucursal_centro_control.id,
            }
        )
        mock_diagnostico_celery.return_value = {
            'ok': True,
            'workers': ['worker@binsur'],
            'workers_detectados': 1,
            'broker_url': 'amqp://usuario:***@127.0.0.1:5672//',
            'broker_host': '127.0.0.1',
            'broker_puerto': 5672,
            'broker_alcanzable': True,
            'mensaje': 'Workers Celery en linea.',
        }

        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/ejecutar-tarea/'
        payload = {
            'tarea': 'enviar_resumen_diario_ejecutivo',
            'fecha_contable': '2026-04-16',
            'sucursal_id': self.sucursal_centro_control.id,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(respuesta.data.get('status'), 'success')
        parametros = (respuesta.data.get('data') or {}).get('parametros') or {}
        self.assertEqual(parametros.get('sucursal_id'), self.sucursal_centro_control.id)

        mock_encolar_tarea.assert_called_once()
        llamada_args = mock_encolar_tarea.call_args[0]
        self.assertEqual(llamada_args[0], 'enviar_resumen_diario_ejecutivo')
        self.assertEqual(llamada_args[1].get('sucursal_id'), self.sucursal_centro_control.id)

    def test_admin_rechaza_filtro_casino_en_tarea_no_compatible(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/ejecutar-tarea/'
        payload = {
            'tarea': 'ejecutar_backup_bd',
            'sucursal_id': self.sucursal_centro_control.id,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data.get('status'), 'error')
        self.assertIn('sucursal_id', (respuesta.data.get('data') or {}))

    @patch('cabina_arquitectura.views.enviar_correo_credenciales_usuario')
    def test_director_crea_usuario_y_envia_correo_con_respaldo(self, mock_enviar_correo):
        mock_enviar_correo.return_value = {'enviado': True, 'error': ''}

        rol_contador = Rol.objects.create(nombre='CONTADOR')
        self.client.force_authenticate(user=self.usuario_director)

        url = '/api/cabina-arquitectura/director/usuarios/'
        payload = {
            'username': 'conta_prueba_mail',
            'nombre': 'Contador Prueba Mail',
            'correo': 'conta_prueba_mail@binsur.mx',
            'sucursal': self.sucursal_centro_control.id,
            'rol': rol_contador.id,
            'is_active': True,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data.get('status'), 'success')
        self.assertTrue((respuesta.data.get('data') or {}).get('correo_enviado'))

        mock_enviar_correo.assert_called_once()
        kwargs = mock_enviar_correo.call_args.kwargs
        self.assertTrue(kwargs.get('incluir_destinatarios_respaldo'))
        self.assertFalse(kwargs.get('es_reinicio'))

    @patch('cabina_arquitectura.views.enviar_correo_credenciales_usuario')
    def test_admin_crea_usuario_y_envia_correo_con_respaldo(self, mock_enviar_correo):
        mock_enviar_correo.return_value = {'enviado': True, 'error': ''}

        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/usuarios/'
        payload = {
            'username': 'admin_alta_mail',
            'nombre': 'Administrador Alta Mail',
            'correo': 'admin_alta_mail@binsur.mx',
            'roles_ids': [self.rol_director.id],
            'is_active': True,
            'is_staff': True,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data.get('status'), 'success')

        data = respuesta.data.get('data') or {}
        self.assertTrue(data.get('correo_enviado'))
        self.assertTrue(str(data.get('contrasena_generada') or '').strip())

        mock_enviar_correo.assert_called_once()
        kwargs = mock_enviar_correo.call_args.kwargs
        self.assertTrue(kwargs.get('incluir_destinatarios_respaldo'))
        self.assertFalse(kwargs.get('es_reinicio'))

    def test_admin_no_puede_crear_usuario_sin_correo(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/usuarios/'
        payload = {
            'username': 'admin_sin_correo',
            'nombre': 'Administrador Sin Correo',
            'roles_ids': [self.rol_director.id],
            'is_active': True,
            'is_staff': False,
        }

        respuesta = self.client.post(url, payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data.get('status'), 'error')
        self.assertIn('correo', (respuesta.data.get('data') or {}))

    @patch('cabina_arquitectura.views.enviar_correo_credenciales_usuario')
    def test_director_reinicia_password_y_envia_correo_con_respaldo(self, mock_enviar_correo):
        mock_enviar_correo.return_value = {'enviado': True, 'error': ''}

        rol_contador = Rol.objects.create(nombre='CONTADOR')
        usuario_operativo = Usuario.objects.create_user(
            username='operativo_reinicio_mail',
            password='temporal1234',
            nombre='Operativo Reinicio Mail',
            correo='operativo_reinicio_mail@binsur.mx',
            is_active=True,
            sucursal=self.sucursal_centro_control,
        )
        UsuarioRol.objects.create(usuario=usuario_operativo, rol=rol_contador)

        self.client.force_authenticate(user=self.usuario_director)
        url = f'/api/cabina-arquitectura/director/usuarios/{usuario_operativo.id}/reiniciar-password/'

        respuesta = self.client.post(url, {}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')

        data = respuesta.data.get('data') or {}
        self.assertTrue(data.get('correo_enviado'))
        self.assertTrue(str(data.get('contrasena_generada') or '').strip())

        mock_enviar_correo.assert_called_once()
        kwargs = mock_enviar_correo.call_args.kwargs
        self.assertTrue(kwargs.get('incluir_destinatarios_respaldo'))
        self.assertTrue(kwargs.get('es_reinicio'))

    def test_admin_consulta_estado_tarea_sin_task_id(self):
        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/estado-tarea/'

        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data.get('status'), 'error')

    @patch('cabina_arquitectura.views.AsyncResult')
    def test_admin_consulta_estado_tarea_pendiente(self, mock_async_result):
        resultado_mock = SimpleNamespace(
            state='PENDING',
            ready=lambda: False,
            successful=lambda: False,
            failed=lambda: False,
            result=None,
            traceback='',
        )
        mock_async_result.return_value = resultado_mock

        self.client.force_authenticate(user=self.usuario_admin)
        url = '/api/cabina-arquitectura/centro-control/estado-tarea/?task_id=task-pendiente-001'

        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')
        data = respuesta.data.get('data') or {}
        self.assertEqual(data.get('estado'), 'PENDING')
        self.assertFalse(data.get('listo'))
