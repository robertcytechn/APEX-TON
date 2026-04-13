from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

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
