from rest_framework import status
from rest_framework.test import APITestCase

from configuraciones_globales.models import ConfiguracionGlobal
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
