from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categoria_operativa.models import CategoriaOperativa, Concepto, DetalleParametrizado
from configuraciones_globales.models import ConfiguracionGlobal
from reportes_diarios.models import ReporteDiario, MovimientoDiario
from reportes_diarios.tareas import (
	auto_cerrar_dias_con_gracia,
	_obtener_ruta_log_respaldo_bd,
	_registrar_bitacora_respaldo_bd,
	_resolver_ruta_log_respaldo_bd_segura,
	_resolver_destinatarios_respaldo_bd,
)
from sucursales.models import Sucursal
from usuarios.models import Usuario, Rol, UsuarioRol


# 1) Para qué sirve: forzar una ventana horaria que deje bloqueada la escritura en pruebas.
# 2) Cómo funciona: configura apertura y cierre en el minuto siguiente exacto al momento actual.
# 3) Qué hace: garantiza que las operaciones de escritura caigan fuera de horario en los tests.
# 4) Cómo editarla: cambia la estrategia si negocio redefine el manejo de límites horarios.
def _configurar_horario_bloqueado_para_pruebas():
	hora_bloqueada = (timezone.localtime() + timedelta(minutes=1)).replace(second=0, microsecond=0).time()
	valor_hora = hora_bloqueada.strftime('%H:%M:%S')

	ConfiguracionGlobal.objects.update_or_create(
		clave='HORARIO_APERTURA',
		defaults={
			'valor': valor_hora,
			'tipo_valor': 'TIME',
			'descripcion': 'Prueba automatizada de bloqueo horario.',
		}
	)
	ConfiguracionGlobal.objects.update_or_create(
		clave='HORARIO_CIERRE',
		defaults={
			'valor': valor_hora,
			'tipo_valor': 'TIME',
			'descripcion': 'Prueba automatizada de bloqueo horario.',
		}
	)


# 1) Para qué sirve: asociar de forma explícita un rol de negocio a un usuario de prueba.
# 2) Cómo funciona: crea/recupera rol por nombre y registra relación usuario-rol.
# 3) Qué hace: habilita validaciones reales de permisos por rol en endpoints.
# 4) Cómo editarla: añade descripción por entorno si se requiere trazabilidad adicional.
def _asignar_rol_usuario(usuario, nombre_rol):
	rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
	UsuarioRol.objects.get_or_create(usuario=usuario, rol=rol)


# 1) Para qué sirve: evitar regresión donde un horario inválido se normaliza silenciosamente a 23:59.
# 2) Cómo funciona: define HORARIO_CIERRE inválido y ejecuta la tarea auto_cerrar_dias_con_gracia.
# 3) Qué hace: valida que la tarea se omita explícitamente sin forzar una hora distinta.
# 4) Cómo editarla: agrega más casos de formato cuando se admitan nuevos tipos para HORARIO_CIERRE.
class AutoCerrarDiasConGraciaHorarioTests(APITestCase):
	def test_horario_cierre_invalido_no_aplica_fallback_2359(self):
		ConfiguracionGlobal.objects.update_or_create(
			clave='HORARIO_CIERRE',
			defaults={
				'valor': 'valor_invalido',
				'tipo_valor': 'TIME',
				'descripcion': 'Prueba de horario de cierre inválido.',
			},
		)

		resultado = auto_cerrar_dias_con_gracia.run()

		self.assertEqual(resultado.get('status'), 'omitido')
		self.assertEqual(resultado.get('razon'), 'horario_cierre_invalido')


# 1) Para que sirve: validar que respaldo BD resuelva destinatarios sin bloquear ejecucion por configuracion incompleta.
# 2) Como funciona: prueba clave legacy de destinatarios y fallback a SMTP configurado.
# 3) Que hace: previene fallos silenciosos cuando no existe DESTINATARIO_BACKUP.
# 4) Como editarla: amplia escenarios al agregar nuevas claves globales de notificacion.
class RespaldoDestinatariosTests(APITestCase):
	def test_resuelve_destinatarios_desde_clave_legacy_plural(self):
		ConfiguracionGlobal.objects.create(
			clave='DESTINATARIOS_RESPALDO_BD',
			valor='respaldo1@binsur.mx, respaldo2@binsur.mx',
			tipo_valor='STRING',
		)

		destinatarios = _resolver_destinatarios_respaldo_bd()
		self.assertEqual(destinatarios, ['respaldo1@binsur.mx', 'respaldo2@binsur.mx'])

	@override_settings(EMAIL_HOST_USER='respaldos_fallback@binsur.mx', DEFAULT_FROM_EMAIL='')
	def test_resuelve_destinatarios_desde_fallback_smtp(self):
		destinatarios = _resolver_destinatarios_respaldo_bd()
		self.assertEqual(destinatarios, ['respaldos_fallback@binsur.mx'])


# 1) Para que sirve: validar la bitacora tecnica local del respaldo en carpeta media.
# 2) Como funciona: fuerza BASE_DIR temporal y registra eventos con y sin excepcion.
# 3) Que hace: asegura evidencia persistente para diagnosticar fallos silenciosos.
# 4) Como editarla: amplia aserciones si cambias formato de bitacora.
class RespaldoBitacoraTests(SimpleTestCase):
	def test_resuelve_ruta_segura_en_fallback_runtime(self):
		with TemporaryDirectory() as carpeta_temporal:
			with self.settings(BASE_DIR=carpeta_temporal):
				ruta_bitacora = _resolver_ruta_log_respaldo_bd_segura(timezone.localtime(timezone.now()))
				self.assertTrue(Path(ruta_bitacora).exists())

	def test_bitacora_respaldo_crea_archivo_en_media_logs(self):
		with TemporaryDirectory() as carpeta_temporal:
			with self.settings(BASE_DIR=carpeta_temporal):
				ruta_bitacora = _obtener_ruta_log_respaldo_bd(timezone.localtime(timezone.now()))
				_registrar_bitacora_respaldo_bd(
					ruta_log=ruta_bitacora,
					nivel='INFO',
					evento='PRUEBA_BITACORA_RESPALDO',
					contexto={'paso': 'inicio'},
				)

				self.assertTrue(Path(ruta_bitacora).exists())
				self.assertIn('media/logs/backups_bd', str(ruta_bitacora).replace('\\', '/').lower())
				contenido = Path(ruta_bitacora).read_text(encoding='utf-8')
				self.assertIn('PRUEBA_BITACORA_RESPALDO', contenido)
				self.assertIn('Contexto:', contenido)

	def test_bitacora_respaldo_guarda_traza_de_excepcion(self):
		with TemporaryDirectory() as carpeta_temporal:
			with self.settings(BASE_DIR=carpeta_temporal):
				ruta_bitacora = _obtener_ruta_log_respaldo_bd(timezone.localtime(timezone.now()))
				try:
					raise ValueError('fallo_controlado_bitacora')
				except Exception as exc:
					_registrar_bitacora_respaldo_bd(
						ruta_log=ruta_bitacora,
						nivel='ERROR',
						evento='PRUEBA_EXCEPCION_BITACORA',
						contexto={'paso': 'error'},
						excepcion=exc,
					)

				contenido = Path(ruta_bitacora).read_text(encoding='utf-8')
				self.assertIn('ValueError: fallo_controlado_bitacora', contenido)
				self.assertIn('Traceback', contenido)

	def test_bitacora_respaldo_sin_ruta_local_no_falla(self):
		_registrar_bitacora_respaldo_bd(
			ruta_log=None,
			nivel='INFO',
			evento='PRUEBA_BITACORA_SIN_RUTA',
			contexto={'paso': 'sin_ruta_local'},
		)


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

	# 1) Para qué sirve: asegurar blindaje de cierre de día cuando la operación está fuera de horario.
	# 2) Cómo funciona: define horario bloqueado y ejecuta POST cerrar-actual.
	# 3) Qué hace: valida rechazo con HTTP 403 y mensaje de horario de captura.
	# 4) Cómo editarla: ajusta texto esperado si cambia mensaje de permiso.
	def test_cerrar_actual_fuera_de_horario_no_permite_modificar(self):
		_configurar_horario_bloqueado_para_pruebas()
		fecha_objetivo = timezone.localdate() - timedelta(days=1)
		self._crear_reporte_abierto(fecha_objetivo)

		respuesta = self.client.post(
			self.url_cerrar_actual,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': fecha_objetivo.isoformat(),
			},
			format='json'
		)

		self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
		mensaje = str(respuesta.data.get('message') or respuesta.data.get('detail') or '').lower()
		self.assertIn('horario de captura', mensaje)


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

	# 1) Para qué sirve: validar que captura-rapida queda bloqueada fuera de horario operativo.
	# 2) Cómo funciona: define horario bloqueado y envía payload válido de captura.
	# 3) Qué hace: asegura rechazo con HTTP 403 antes de crear o editar movimientos.
	# 4) Cómo editarla: amplía con multipart si deseas cubrir evidencia adjunta.
	def test_captura_rapida_fuera_de_horario_no_permite_modificar(self):
		_configurar_horario_bloqueado_para_pruebas()

		respuesta = self.client.post(
			self.url_captura_rapida,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': self.fecha_contable.isoformat(),
				'concepto': self.concepto_con_detalles.id,
				'monto': '500.00',
			},
			format='json'
		)

		self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
		mensaje = str(respuesta.data.get('message') or respuesta.data.get('detail') or '').lower()
		self.assertIn('horario de captura', mensaje)


# 1) Para qué sirve: validar reporte diario tipo libro con restricciones por rol y arrastre encadenado.
# 2) Cómo funciona: consulta endpoint libro-operativo con usuarios de rol operativo/directivo.
# 3) Qué hace: asegura día forzado para contador y rango habilitado para director.
# 4) Cómo editarla: agrega escenarios multi-sucursal si se amplía cobertura funcional.
class ReporteDiarioLibroOperativoTests(APITestCase):
	def setUp(self):
		self.sucursal = Sucursal.objects.create(
			nombre='Sucursal Libro Operativo',
			clave='SUC-LIBRO-OPERATIVO'
		)

		self.categoria = CategoriaOperativa.objects.create(
			nombre='ADMINISTRACION LIBRO',
			clave='ADMIN_LIBRO',
			tipo='MIXTO',
			orden=1,
		)
		self.concepto_ingreso = Concepto.objects.create(
			categoria=self.categoria,
			nombre='Ingreso Libro',
			clave='INGRESO_LIBRO_TEST',
			tipo='INGRESO',
		)
		self.concepto_egreso = Concepto.objects.create(
			categoria=self.categoria,
			nombre='Egreso Libro',
			clave='EGRESO_LIBRO_TEST',
			tipo='EGRESO',
		)

		self.url_libro_operativo = reverse('reportediario-libro-operativo')
		self.url_reporte_actual = reverse('reportediario-actual')
		if settings.FORCE_SCRIPT_NAME and self.url_libro_operativo.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_libro_operativo = self.url_libro_operativo[len(settings.FORCE_SCRIPT_NAME):] or '/'
		if settings.FORCE_SCRIPT_NAME and self.url_reporte_actual.startswith(settings.FORCE_SCRIPT_NAME):
			self.url_reporte_actual = self.url_reporte_actual[len(settings.FORCE_SCRIPT_NAME):] or '/'

	def _crear_usuario_con_rol(self, username, rol):
		usuario = Usuario.objects.create_user(
			username=username,
			password='password_seguro_123',
			nombre=f'Usuario {rol}',
			sucursal=self.sucursal,
		)
		_asignar_rol_usuario(usuario, rol)
		return usuario

	def _crear_reporte_con_movimientos(self, fecha_contable, saldo_inicio='0.00', ingreso='0.00', egreso='0.00'):
		reporte = ReporteDiario.objects.create(
			sucursal=self.sucursal,
			fecha_contable=fecha_contable,
			estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
			saldo_arrastre_inicio=Decimal(str(saldo_inicio)),
		)

		if Decimal(str(ingreso)) > 0:
			MovimientoDiario.objects.create(
				reporte=reporte,
				concepto=self.concepto_ingreso,
				monto=Decimal(str(ingreso)),
			)

		if Decimal(str(egreso)) > 0:
			MovimientoDiario.objects.create(
				reporte=reporte,
				concepto=self.concepto_egreso,
				monto=Decimal(str(egreso)),
			)

		return reporte

	def test_libro_operativo_contador_forza_dia_actual(self):
		fecha_actual = timezone.localdate() - timedelta(days=1)
		fecha_anterior = fecha_actual - timedelta(days=1)

		self._crear_reporte_con_movimientos(fecha_anterior, saldo_inicio='1000.00', ingreso='200.00', egreso='50.00')
		self._crear_reporte_con_movimientos(fecha_actual, saldo_inicio='1200.00', ingreso='300.00', egreso='100.00')

		usuario_contador = self._crear_usuario_con_rol('contador_libro', 'CONTADOR')
		self.client.force_authenticate(user=usuario_contador)

		respuesta = self.client.get(
			self.url_libro_operativo,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_inicio': fecha_anterior.isoformat(),
				'fecha_fin': fecha_actual.isoformat(),
			}
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		filtro = respuesta.data.get('data', {}).get('filtro_aplicado', {})
		self.assertEqual(filtro.get('fecha_inicio'), fecha_actual.isoformat())
		self.assertEqual(filtro.get('fecha_fin'), fecha_actual.isoformat())
		self.assertTrue(filtro.get('filtro_forzado'))

		filas = respuesta.data.get('data', {}).get('filas', [])
		fila_total = next((fila for fila in filas if fila.get('tipo_fila') == 'TOTAL_PERIODO'), None)
		self.assertIsNotNone(fila_total)
		self.assertEqual(float(fila_total.get('ingreso') or 0), 300.0)
		self.assertEqual(float(fila_total.get('egreso') or 0), 100.0)
		fila_efectivo = next((fila for fila in filas if fila.get('tipo_fila') == 'EFECTIVO_FISICO'), None)
		self.assertIsNotNone(fila_efectivo)
		self.assertIsNone(fila_efectivo.get('ingreso'))
		self.assertIsNone(fila_efectivo.get('egreso'))
		self.assertEqual(float(fila_efectivo.get('saldo') or 0), float(fila_total.get('saldo') or 0))

	def test_libro_operativo_director_permite_rango(self):
		fecha_actual = timezone.localdate() - timedelta(days=1)
		fecha_inicio = fecha_actual - timedelta(days=1)

		self._crear_reporte_con_movimientos(fecha_inicio, saldo_inicio='1000.00', ingreso='500.00', egreso='100.00')
		self._crear_reporte_con_movimientos(fecha_actual, saldo_inicio='1400.00', ingreso='700.00', egreso='200.00')

		usuario_director = self._crear_usuario_con_rol('director_libro', 'DIRECTOR')
		self.client.force_authenticate(user=usuario_director)

		respuesta = self.client.get(
			self.url_libro_operativo,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_inicio': fecha_inicio.isoformat(),
				'fecha_fin': fecha_actual.isoformat(),
			}
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		filtro = respuesta.data.get('data', {}).get('filtro_aplicado', {})
		self.assertEqual(filtro.get('fecha_inicio'), fecha_inicio.isoformat())
		self.assertEqual(filtro.get('fecha_fin'), fecha_actual.isoformat())
		self.assertFalse(filtro.get('filtro_forzado'))

		resumen = respuesta.data.get('data', {}).get('resumen', {})
		self.assertEqual(resumen.get('dias_consultados'), 2)

		filas = respuesta.data.get('data', {}).get('filas', [])
		fila_categoria = next((fila for fila in filas if fila.get('partida') == 'ADMIN_LIBRO'), None)
		self.assertIsNotNone(fila_categoria)
		self.assertEqual(float(fila_categoria.get('ingreso') or 0), 1200.0)
		self.assertEqual(float(fila_categoria.get('egreso') or 0), 300.0)
		fila_total = next((fila for fila in filas if fila.get('tipo_fila') == 'TOTAL_PERIODO'), None)
		fila_efectivo = next((fila for fila in filas if fila.get('tipo_fila') == 'EFECTIVO_FISICO'), None)
		self.assertIsNotNone(fila_total)
		self.assertIsNotNone(fila_efectivo)
		self.assertEqual(float(fila_efectivo.get('saldo') or 0), float(fila_total.get('saldo') or 0))

	def test_arrastre_se_traslada_al_siguiente_dia_al_crear_reporte(self):
		fecha_actual = timezone.localdate() - timedelta(days=1)
		fecha_anterior = fecha_actual - timedelta(days=1)

		self._crear_reporte_con_movimientos(fecha_anterior, saldo_inicio='40000.00', ingreso='2000.00', egreso='500.00')

		usuario_staff = Usuario.objects.create_user(
			username='staff_arrastre',
			password='password_seguro_123',
			nombre='Usuario Staff Arrastre',
			is_staff=True,
			sucursal=self.sucursal,
		)
		self.client.force_authenticate(user=usuario_staff)

		respuesta = self.client.get(
			self.url_reporte_actual,
			{
				'sucursal_id': self.sucursal.id,
				'fecha_contable': fecha_actual.isoformat(),
			}
		)

		self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
		saldo_arrastre_inicio = Decimal(str(respuesta.data.get('data', {}).get('saldo_arrastre_inicio', '0')))
		self.assertEqual(saldo_arrastre_inicio, Decimal('41500.00'))
