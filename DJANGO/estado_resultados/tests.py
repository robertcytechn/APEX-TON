from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categoria_operativa.models import CategoriaOperativa, Concepto
from configuraciones_globales.models import PadreRubroContable, RubroContable
from libro_estado_resultados.models import LibroEstadoResultados
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


# 1) Para qué sirve: proteger cálculo contable de estado de resultados ante rubros no válidos.
# 2) Cómo funciona: valida modo tiempo real y modo snapshot cerrado con datos no contables.
# 3) Qué hace: asegura que SIN_RUBRO y NO_CONTABLE no alteren ingresos/egresos/neto.
# 4) Cómo editarla: agrega nuevos escenarios cuando se amplíe taxonomía de rubros.
class EstadoResultadosContablesExclusionTests(APITestCase):
	def setUp(self):
		self.sucursal = Sucursal.objects.create(nombre='Sucursal Test Estado Resultados', clave='SUC-ER-01')

		self.padre_contable = PadreRubroContable.objects.create(
			clave='INGRESOS_OPERATIVOS_CONTABLES',
			nombre='Ingresos Operativos Contables',
			considerar_en_estado_resultados=True,
		)
		self.padre_no_contable = PadreRubroContable.objects.create(
			clave='SIN_GRUPO_NO_CONTABLE',
			nombre='Sin Grupo No Contable',
			considerar_en_estado_resultados=True,
		)

		self.rubro_contable = RubroContable.objects.create(
			nombre='Ventas Contables',
			padre=self.padre_contable,
			tipo='INGRESO',
		)
		self.rubro_no_contable = RubroContable.objects.create(
			nombre='Registro No Contable',
			padre=self.padre_no_contable,
			tipo='INGRESO',
		)

		self.categoria = CategoriaOperativa.objects.create(
			nombre='ADMIN TEST CONTABLE',
			clave='ADMIN_TEST_CONTABLE',
			tipo='MIXTO',
			orden=1,
		)

		self.concepto_contable = Concepto.objects.create(
			categoria=self.categoria,
			rubro_contable=self.rubro_contable,
			nombre='INGRESO CONTABLE TEST',
			clave='INGRESO_CONTABLE_TEST',
			tipo='INGRESO',
		)
		self.concepto_sin_rubro = Concepto.objects.create(
			categoria=self.categoria,
			rubro_contable=None,
			nombre='INGRESO SIN RUBRO TEST',
			clave='INGRESO_SIN_RUBRO_TEST',
			tipo='INGRESO',
		)
		self.concepto_no_contable = Concepto.objects.create(
			categoria=self.categoria,
			rubro_contable=self.rubro_no_contable,
			nombre='INGRESO NO CONTABLE TEST',
			clave='INGRESO_NO_CONTABLE_TEST',
			tipo='INGRESO',
		)

		self.usuario_admin = Usuario.objects.create_user(
			username='admin_estado_resultados',
			password='password_seguro_123',
			nombre='Admin Estado Resultados',
			sucursal=self.sucursal,
		)

		self.reporte = ReporteDiario.objects.create(
			sucursal=self.sucursal,
			fecha_contable=timezone.localdate() - timedelta(days=1),
			estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
		)
		MovimientoDiario.objects.create(reporte=self.reporte, concepto=self.concepto_contable, monto=1000)
		MovimientoDiario.objects.create(reporte=self.reporte, concepto=self.concepto_sin_rubro, monto=900)
		MovimientoDiario.objects.create(reporte=self.reporte, concepto=self.concepto_no_contable, monto=800)

		self.url_estado_resultados = reverse('estado-resultados')
		if settings.FORCE_SCRIPT_NAME and self.url_estado_resultados.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_estado_resultados = self.url_estado_resultados[len(settings.FORCE_SCRIPT_NAME):] or '/'

	def test_tiempo_real_excluye_conceptos_sin_rubro_y_no_contables(self):
		self.client.force_authenticate(user=self.usuario_admin)

		respuesta = self.client.get(
			self.url_estado_resultados,
			{
				'sucursal_id': self.sucursal.id,
				'mes': self.reporte.fecha_contable.month,
				'anio': self.reporte.fecha_contable.year,
			},
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		self.assertEqual(respuesta.data.get('status'), 'success')

		data = respuesta.data.get('data') or {}
		self.assertEqual(float(data.get('total_ingresos') or 0), 1000.0)
		self.assertEqual(float(data.get('total_ingresos_no_considerados') or 0), 1700.0)

		por_rubro = data.get('por_rubro') or []
		rubro_sin = next((item for item in por_rubro if str(item.get('rubro_id')) == 'SIN_RUBRO_CONTABLE'), None)
		self.assertIsNotNone(rubro_sin)
		self.assertFalse(bool(rubro_sin.get('rubro_padre_considerar_en_estado_resultados')))

	def test_snapshot_historico_excluye_no_contables_legacy(self):
		self.client.force_authenticate(user=self.usuario_admin)

		libro = LibroEstadoResultados.objects.create(
			sucursal=self.sucursal,
			anio=self.reporte.fecha_contable.year,
			mes=self.reporte.fecha_contable.month,
			estado_mes=LibroEstadoResultados.EstadoMes.CERRADO,
			tipo_cambio_usd_snapshot=17.5000,
			tipo_cambio_eur_snapshot=18.9000,
			saldo_arrastre_inicio=0,
			desglose_por_rubro=[
				{
					'rubro_id': self.rubro_contable.id,
					'rubro_nombre': self.rubro_contable.nombre,
					'rubro_tipo': 'INGRESO',
					'rubro_padre': self.padre_contable.nombre,
					'rubro_padre_clave': self.padre_contable.clave,
					'rubro_padre_considerar_en_estado_resultados': True,
					'total_ingresos': 2200,
					'total_egresos': 0,
					'resultado_neto': 2200,
				},
				{
					'rubro_id': 'SIN_RUBRO_CONTABLE',
					'rubro_nombre': 'SIN RUBRO CONTABLE',
					'rubro_tipo': 'NO_CONTABLE',
					'rubro_padre': 'SIN GRUPO',
					'rubro_padre_clave': None,
					'rubro_padre_considerar_en_estado_resultados': True,
					'total_ingresos': 500,
					'total_egresos': 0,
					'resultado_neto': 500,
				},
			],
		)

		respuesta = self.client.get(
			self.url_estado_resultados,
			{
				'sucursal_id': self.sucursal.id,
				'mes': libro.mes,
				'anio': libro.anio,
			},
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		self.assertEqual(respuesta.data.get('status'), 'success')

		data = respuesta.data.get('data') or {}
		self.assertEqual(data.get('fuente'), 'snapshot_historico')
		self.assertEqual(float(data.get('total_ingresos') or 0), 2200.0)
		self.assertEqual(float(data.get('total_ingresos_no_considerados') or 0), 500.0)
