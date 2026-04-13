from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categoria_operativa.models import CategoriaOperativa, Concepto
from configuraciones_globales.models import PadreRubroContable, RubroContable
from reportes_diarios.models import MovimientoDiario, ReporteDiario
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario, UsuarioRol


# 1) Para qué sirve: validar acceso y estructura base del endpoint de estadísticas.
# 2) Cómo funciona: crea datos mínimos y consulta con roles permitidos/no permitidos.
# 3) Qué hace: protege módulo ejecutivo y previene regresiones en filtros clave.
# 4) Cómo editarla: agrega escenarios adicionales cuando crezcan dimensiones analíticas.
class EstadisticasOperativasAPIViewTests(APITestCase):
	def setUp(self):
		self.sucursal = Sucursal.objects.create(nombre='Sucursal Test Estadisticas', clave='SUC-EST-01')

		self.padre_rubro = PadreRubroContable.objects.create(clave='INGRESOS_OPERATIVOS', nombre='Ingresos Operativos')
		self.rubro = RubroContable.objects.create(nombre='Ventas Maquinas', padre=self.padre_rubro, tipo='INGRESO')

		self.categoria = CategoriaOperativa.objects.create(
			nombre='MAQUINAS TEST',
			clave='MAQ_TEST',
			tipo='INGRESO',
			orden=1,
		)
		self.concepto = Concepto.objects.create(
			categoria=self.categoria,
			rubro_contable=self.rubro,
			nombre='VENTA MAQUINAS TEST',
			clave='VENTA_MAQ_TEST',
			tipo='INGRESO',
		)

		fecha_contable = timezone.localdate() - timedelta(days=1)
		self.reporte = ReporteDiario.objects.create(
			sucursal=self.sucursal,
			fecha_contable=fecha_contable,
			estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
		)
		MovimientoDiario.objects.create(reporte=self.reporte, concepto=self.concepto, monto=1500)

		self.rol_director = Rol.objects.create(nombre='DIRECTOR')
		self.rol_contador = Rol.objects.create(nombre='CONTADOR')

		self.usuario_director = Usuario.objects.create_user(
			username='director_estadisticas',
			password='password_seguro_123',
			nombre='Director Estadisticas',
			sucursal=self.sucursal,
		)
		UsuarioRol.objects.create(usuario=self.usuario_director, rol=self.rol_director)

		self.usuario_contador = Usuario.objects.create_user(
			username='contador_estadisticas',
			password='password_seguro_123',
			nombre='Contador Estadisticas',
			sucursal=self.sucursal,
		)
		UsuarioRol.objects.create(usuario=self.usuario_contador, rol=self.rol_contador)

		self.url_estadisticas = reverse('estado-resultados-estadisticas')
		if settings.FORCE_SCRIPT_NAME and self.url_estadisticas.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_estadisticas = self.url_estadisticas[len(settings.FORCE_SCRIPT_NAME):] or '/'

	# 1) Para qué sirve: asegurar que roles no autorizados no entren al módulo ejecutivo.
	# 2) Cómo funciona: autentica como CONTADOR y consulta endpoint.
	# 3) Qué hace: espera rechazo 403 por política de acceso.
	# 4) Cómo editarla: añade más roles no permitidos cuando existan.
	def test_estadisticas_restringidas_para_rol_no_autorizado(self):
		self.client.force_authenticate(user=self.usuario_contador)

		respuesta = self.client.get(self.url_estadisticas)

		self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(respuesta.data.get('status'), 'error')

	# 1) Para qué sirve: validar que DIRECTOR obtiene estructura y métricas esperadas.
	# 2) Cómo funciona: consulta con filtros de fecha y categoría del dato sembrado.
	# 3) Qué hace: comprueba totales, series y presencia de catálogos de filtros.
	# 4) Cómo editarla: incrementa asserts al agregar nuevas métricas del endpoint.
	def test_estadisticas_director_obtiene_resumen_y_series(self):
		self.client.force_authenticate(user=self.usuario_director)

		respuesta = self.client.get(
			self.url_estadisticas,
			{
				'fecha_inicio': self.reporte.fecha_contable.isoformat(),
				'fecha_fin': self.reporte.fecha_contable.isoformat(),
				'sucursal_id': self.sucursal.id,
				'categoria_id': self.categoria.id,
			},
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		self.assertEqual(respuesta.data.get('status'), 'success')

		data = respuesta.data.get('data') or {}
		resumen = data.get('resumen_general') or {}
		series = data.get('series') or {}

		self.assertEqual(int(resumen.get('total_movimientos') or 0), 1)
		self.assertEqual(float(resumen.get('total_ingresos') or 0), 1500.0)
		self.assertTrue(isinstance(series.get('por_dia'), list))
		self.assertTrue(isinstance(data.get('catalogos', {}).get('sucursales'), list))
