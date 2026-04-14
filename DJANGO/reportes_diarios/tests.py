from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categoria_operativa.models import CategoriaOperativa, Concepto, DetalleParametrizado
from reportes_diarios.models import ReporteDiario
from sucursales.models import Sucursal
from usuarios.models import Usuario


# 1) Para qué sirve: validar flujo de cierre manual de día contable en API.
# 2) Cómo funciona: usa cliente autenticado contra endpoint cerrar-actual.
# 3) Qué hace: garantiza fecha obligatoria y cierre puntual sin afectar otros días.
# 4) Cómo editarla: agrega aquí escenarios de permisos/horarios conforme crezcan reglas.
class ReporteDiarioCierreActualTests(APITestCase):
	def setUp(self):
		self.sucursal = Sucursal.objects.create(
			nombre='Sucursal Pruebas Cierre',
			clave='SUC-PRUEBA-CIERRE'
		)
		self.usuario = Usuario.objects.create_user(
			username='staff_cierre',
			password='password_seguro_123',
			nombre='Usuario Staff Cierre',
			is_staff=True,
			sucursal=self.sucursal,
		)
		self.client.force_authenticate(user=self.usuario)
		self.url_cerrar_actual = reverse('reportediario-cerrar-actual')
		if settings.FORCE_SCRIPT_NAME and self.url_cerrar_actual.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_cerrar_actual = self.url_cerrar_actual[len(settings.FORCE_SCRIPT_NAME):] or '/'

	def _crear_reporte_abierto(self, fecha_contable):
		return ReporteDiario.objects.create(
			sucursal=self.sucursal,
			fecha_contable=fecha_contable,
			estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
		)

	# 1) Para qué sirve: asegurar contrato API que obliga fecha explícita en cierre.
	# 2) Cómo funciona: envía payload sin fecha_contable y valida HTTP 400.
	# 3) Qué hace: evita cierres implícitos por fallback que puedan confundir operación.
	# 4) Cómo editarla: ajusta texto esperado si cambia mensaje de validación.
	def test_cerrar_actual_exige_fecha_contable_explicita(self):
		respuesta = self.client.post(
			self.url_cerrar_actual,
			{'sucursal_id': self.sucursal.id},
			format='json'
		)

		self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(respuesta.data.get('status'), 'error')
		self.assertIn('fecha_contable', str(respuesta.data.get('message', '')).lower())

	# 1) Para qué sirve: garantizar que cierre manual afecte solo la fecha solicitada.
	# 2) Cómo funciona: crea dos reportes abiertos y cierra uno con fecha_contable explícita.
	# 3) Qué hace: valida que el otro reporte permanezca ABIERTO para seguir editable.
	# 4) Cómo editarla: incorpora más fechas vecinas si deseas cobertura ampliada.
	def test_cerrar_actual_solo_cierra_la_fecha_enviada(self):
		dia_contable_actual = timezone.localdate() - timedelta(days=1)
		fecha_a_cerrar = dia_contable_actual - timedelta(days=1)
		fecha_que_permanece_abierta = dia_contable_actual - timedelta(days=2)

		reporte_objetivo = self._crear_reporte_abierto(fecha_a_cerrar)
		reporte_no_objetivo = self._crear_reporte_abierto(fecha_que_permanece_abierta)

		respuesta = self.client.post(
			self.url_cerrar_actual,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': fecha_a_cerrar.isoformat(),
			},
			format='json'
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

		reporte_objetivo.refresh_from_db()
		reporte_no_objetivo.refresh_from_db()

		self.assertEqual(reporte_objetivo.estado_reporte, ReporteDiario.EstadoReporte.CERRADO)
		self.assertEqual(reporte_no_objetivo.estado_reporte, ReporteDiario.EstadoReporte.ABIERTO)
		self.assertEqual(str(respuesta.data.get('data', {}).get('fecha_contable')), fecha_a_cerrar.isoformat())


# 1) Para qué sirve: validar comportamiento de captura rápida con conceptos repetibles.
# 2) Cómo funciona: prueba creación múltiple por detalles parametrizados y update por movimiento_id.
# 3) Qué hace: garantiza múltiples capturas del mismo concepto cuando la categoría lo requiere.
# 4) Cómo editarla: agrega escenarios por archivos o tipos de detalle adicionales.
class MovimientoDiarioCapturaRapidaConDetallesTests(APITestCase):
	def setUp(self):
		self.sucursal = Sucursal.objects.create(
			nombre='Sucursal Captura Rapida',
			clave='SUC-CAPT-RAPIDA'
		)
		self.usuario = Usuario.objects.create_user(
			username='staff_captura_rapida',
			password='password_seguro_123',
			nombre='Usuario Captura Rapida',
			is_staff=True,
			sucursal=self.sucursal,
		)
		self.client.force_authenticate(user=self.usuario)

		self.fecha_contable = timezone.localdate() - timedelta(days=1)
		self.url_captura_rapida = reverse('movimientodiario-captura-rapida')
		if settings.FORCE_SCRIPT_NAME and self.url_captura_rapida.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_captura_rapida = self.url_captura_rapida[len(settings.FORCE_SCRIPT_NAME):] or '/'

		self.categoria_con_detalles = CategoriaOperativa.objects.create(
			nombre='CAJA CHICA TEST',
			clave='CAJA_CHICA_TEST',
			tipo='MIXTO',
			orden=1,
		)
		DetalleParametrizado.objects.create(
			categoria=self.categoria_con_detalles,
			nombre='Responsable',
			clave='responsable',
			tipo_valor='TEXT',
			requerido=False,
		)

		self.concepto_con_detalles = Concepto.objects.create(
			categoria=self.categoria_con_detalles,
			nombre='Gasto Caja Chica Test',
			clave='GASTO_CAJA_CHICA_TEST',
			tipo='EGRESO',
			es_recurrente=True,
		)

		self.categoria_sin_detalles = CategoriaOperativa.objects.create(
			nombre='ADMIN SIN DETALLES TEST',
			clave='ADMIN_SIN_DETALLES_TEST',
			tipo='MIXTO',
			orden=2,
		)
		self.concepto_sin_detalles = Concepto.objects.create(
			categoria=self.categoria_sin_detalles,
			nombre='Ingreso Sin Detalles Test',
			clave='INGRESO_SIN_DETALLES_TEST',
			tipo='INGRESO',
		)

	def test_captura_rapida_crea_movimientos_multiples_con_detalles_parametrizados(self):
		payload_base = {
			'sucursal_id': self.sucursal.id,
			'fecha_contable': self.fecha_contable.isoformat(),
			'concepto': self.concepto_con_detalles.id,
		}

		respuesta_uno = self.client.post(
			self.url_captura_rapida,
			{
				**payload_base,
				'monto': '1200.00',
				'detalles_snapshot': {'responsable': 'Operador A'},
			},
			format='json'
		)

		respuesta_dos = self.client.post(
			self.url_captura_rapida,
			{
				**payload_base,
				'monto': '850.00',
				'detalles_snapshot': {'responsable': 'Operador B'},
			},
			format='json'
		)

		self.assertEqual(respuesta_uno.status_code, status.HTTP_201_CREATED)
		self.assertEqual(respuesta_dos.status_code, status.HTTP_201_CREATED)

		reporte = ReporteDiario.objects.get(sucursal=self.sucursal, fecha_contable=self.fecha_contable)
		movimientos = reporte.movimientos.filter(concepto=self.concepto_con_detalles)
		self.assertEqual(movimientos.count(), 2)

	def test_captura_rapida_actualiza_movimiento_existente_con_movimiento_id(self):
		respuesta_creacion = self.client.post(
			self.url_captura_rapida,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': self.fecha_contable.isoformat(),
				'concepto': self.concepto_con_detalles.id,
				'monto': '1000.00',
				'detalles_snapshot': {'responsable': 'Inicial'},
			},
			format='json'
		)
		self.assertEqual(respuesta_creacion.status_code, status.HTTP_201_CREATED)

		movimiento_id = respuesta_creacion.data.get('data', {}).get('id')
		respuesta_actualizacion = self.client.post(
			self.url_captura_rapida,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': self.fecha_contable.isoformat(),
				'concepto': self.concepto_con_detalles.id,
				'movimiento_id': movimiento_id,
				'monto': '1450.00',
				'detalles_snapshot': {'responsable': 'Editado'},
			},
			format='json'
		)

		self.assertEqual(respuesta_actualizacion.status_code, status.HTTP_200_OK)

		reporte = ReporteDiario.objects.get(sucursal=self.sucursal, fecha_contable=self.fecha_contable)
		movimientos = reporte.movimientos.filter(concepto=self.concepto_con_detalles)
		self.assertEqual(movimientos.count(), 1)

		movimiento = movimientos.first()
		self.assertEqual(float(movimiento.monto), 1450.00)
		self.assertEqual(movimiento.detalles_snapshot.get('responsable'), 'Editado')

	def test_captura_rapida_sin_detalles_mantiene_upsert_por_concepto(self):
		payload = {
			'sucursal_id': self.sucursal.id,
			'fecha_contable': self.fecha_contable.isoformat(),
			'concepto': self.concepto_sin_detalles.id,
		}

		respuesta_uno = self.client.post(
			self.url_captura_rapida,
			{**payload, 'monto': '2000.00'},
			format='json'
		)
		respuesta_dos = self.client.post(
			self.url_captura_rapida,
			{**payload, 'monto': '2300.00'},
			format='json'
		)

		self.assertEqual(respuesta_uno.status_code, status.HTTP_201_CREATED)
		self.assertEqual(respuesta_dos.status_code, status.HTTP_200_OK)

		reporte = ReporteDiario.objects.get(sucursal=self.sucursal, fecha_contable=self.fecha_contable)
		movimientos = reporte.movimientos.filter(concepto=self.concepto_sin_detalles)
		self.assertEqual(movimientos.count(), 1)
		self.assertEqual(float(movimientos.first().monto), 2300.00)
