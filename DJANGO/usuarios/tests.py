from rest_framework import status
from rest_framework.test import APITestCase

from .models import Usuario


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
