from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Rol, TicketSoporteTecnico, Usuario, UsuarioRol


class UsuariosSesionPublicaTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='usuario_login_publico',
            password='login1234',
            nombre='Usuario Login Publico',
            correo='login_publico@binsur.mx',
            is_active=True,
        )

    def test_csrf_publico_responde_sin_autenticacion(self):
        respuesta = self.client.get('/api/usuarios/csrf/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')
        self.assertIn('csrf_token', (respuesta.data.get('data') or {}))

    def test_login_publico_no_regresa_403_sin_sesion(self):
        payload = {'identificador': self.usuario.username, 'password': 'login1234'}
        respuesta = self.client.post('/api/usuarios/iniciar-sesion/', payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')
        self.assertIn('usuario', (respuesta.data.get('data') or {}))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UsuariosSoporteTecnicoTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='usuario_soporte',
            password='soporte1234',
            nombre='Usuario Soporte',
            correo='soporte_usuario@binsur.mx',
            is_active=True,
        )

    def test_requiere_sesion_para_enviar_solicitud_soporte(self):
        payload = {
            'problema_principal': 'RENDIMIENTO',
            'areas_afectadas': ['INICIO'],
            'comportamiento_observado': 'NO_CARGA',
            'descripcion_detallada': 'La pantalla de inicio tarda demasiado y no responde durante varios segundos.'
        }

        respuesta = self.client.post('/api/usuarios/soporte-tecnico/solicitudes/', payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_autenticado_envia_solicitud_soporte_y_registra_ticket(self):
        self.client.force_authenticate(user=self.usuario)

        payload = {
            'problema_principal': 'RENDIMIENTO',
            'areas_afectadas': ['INICIO', 'REPORTE_DIARIO'],
            'comportamiento_observado': 'NO_CARGA',
            'prioridad': 'ALTA',
            'dispositivo': 'ESCRITORIO',
            'pagina_afectada': '/reportes/reporte-diario',
            'descripcion_detallada': 'El reporte diario tarda en cargar y al intentar aplicar filtros se queda congelado en pantalla.',
            'pasos_reproduccion': 'Entrar al reporte diario, seleccionar rango de fechas y aplicar filtros por sucursal.',
            'bloqueo_operativo': True,
        }

        respuesta = self.client.post('/api/usuarios/soporte-tecnico/solicitudes/', payload, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data.get('status'), 'success')
        data = respuesta.data.get('data') or {}
        self.assertIn('folio', data)
        self.assertTrue(data.get('correo_soporte_enviado'))
        self.assertTrue(data.get('correo_confirmacion_enviado'))

        self.assertEqual(TicketSoporteTecnico.objects.count(), 1)
        ticket = TicketSoporteTecnico.objects.first()
        self.assertEqual(ticket.usuario_id, self.usuario.id)
        self.assertEqual(ticket.problema_principal, payload['problema_principal'])
        self.assertEqual(ticket.areas_afectadas, payload['areas_afectadas'])
        self.assertEqual(ticket.comportamiento_observado, payload['comportamiento_observado'])
        self.assertEqual(ticket.prioridad, payload['prioridad'])
        self.assertEqual(ticket.dispositivo, payload['dispositivo'])
        self.assertEqual(ticket.pagina_afectada, payload['pagina_afectada'])
        self.assertEqual(ticket.descripcion_detallada, payload['descripcion_detallada'])
        self.assertEqual(ticket.pasos_reproduccion, payload['pasos_reproduccion'])
        self.assertTrue(ticket.bloqueo_operativo)
        self.assertTrue(ticket.correo_soporte_enviado)
        self.assertTrue(ticket.correo_confirmacion_enviado)

        self.assertEqual(len(mail.outbox), 2)

        correo_soporte = mail.outbox[0]
        self.assertIn('robert-cyby@hotmail.com', correo_soporte.to)
        self.assertIn('robertot@gbentretenimiento.com', correo_soporte.cc)
        self.assertIn('Usuario Soporte', correo_soporte.body)
        self.assertIn('soporte_usuario@binsur.mx', correo_soporte.body)
        self.assertIn(payload['descripcion_detallada'], correo_soporte.body)

        correo_confirmacion = mail.outbox[1]
        self.assertIn('soporte_usuario@binsur.mx', correo_confirmacion.to)
        self.assertIn('Ticket recibido', correo_confirmacion.subject)
        self.assertIn(data.get('folio'), correo_confirmacion.body)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UsuariosSoporteTecnicoAdminEventosTests(APITestCase):
    def setUp(self):
        self.rol_admin = Rol.objects.create(nombre='ADMINISTRADOR', descripcion='Rol administrador de pruebas')

        self.admin = Usuario.objects.create_user(
            username='admin_soporte',
            password='admin1234',
            nombre='Administrador Soporte',
            correo='admin_soporte@binsur.mx',
            is_active=True,
        )
        UsuarioRol.objects.create(usuario=self.admin, rol=self.rol_admin)

        self.usuario_operativo = Usuario.objects.create_user(
            username='usuario_evento',
            password='evento1234',
            nombre='Usuario Evento',
            correo='usuario_evento@binsur.mx',
            is_active=True,
        )

        self.ticket = TicketSoporteTecnico.objects.create(
            folio='ST-PRUEBA-0001',
            usuario=self.usuario_operativo,
            usuario_nombre='Usuario Evento',
            usuario_username='usuario_evento',
            usuario_correo='usuario_evento@binsur.mx',
            usuario_sucursal='No asignada',
            usuario_roles=['CONTADOR'],
            problema_principal='RENDIMIENTO',
            problema_principal_etiqueta='Pantalla lenta o bloqueada',
            areas_afectadas=['INICIO'],
            areas_afectadas_etiquetas=['Panel de inicio'],
            comportamiento_observado='NO_CARGA',
            comportamiento_observado_etiqueta='No carga / se queda pensando',
            prioridad='MEDIA',
            prioridad_etiqueta='Media',
            dispositivo='ESCRITORIO',
            dispositivo_etiqueta='Equipo de escritorio',
            pagina_afectada='/reportes/reporte-diario',
            descripcion_detallada='La pantalla tarda demasiado en cargar información al abrir el reporte.',
            pasos_reproduccion='Entrar al reporte diario y esperar carga de métricas.',
            bloqueo_operativo=True,
            correo_soporte_enviado=True,
            correo_confirmacion_enviado=True,
        )

    def test_usuario_no_admin_no_puede_consultar_eventos(self):
        self.client.force_authenticate(user=self.usuario_operativo)

        respuesta = self.client.get('/api/usuarios/soporte-tecnico/eventos/')

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(respuesta.data.get('status'), 'error')

    def test_admin_lista_eventos_soporte(self):
        self.client.force_authenticate(user=self.admin)

        respuesta = self.client.get('/api/usuarios/soporte-tecnico/eventos/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')

        data = respuesta.data.get('data') or []
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0].get('folio'), self.ticket.folio)

    def test_admin_actualiza_estado_evento_soporte(self):
        self.client.force_authenticate(user=self.admin)

        payload = {
            'estado_seguimiento': 'COMPLETADO',
            'notas_seguimiento': 'Se aplicó ajuste de caché y la pantalla volvió a responder correctamente.'
        }

        respuesta = self.client.patch(
            f'/api/usuarios/soporte-tecnico/eventos/{self.ticket.id}/',
            payload,
            format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data.get('status'), 'success')

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado_seguimiento, 'COMPLETADO')
        self.assertEqual(self.ticket.notas_seguimiento, payload['notas_seguimiento'])
        self.assertEqual(self.ticket.atendido_por_id, self.admin.id)
        self.assertIsNotNone(self.ticket.atendido_en)
        self.assertIsNotNone(self.ticket.resuelto_en)
