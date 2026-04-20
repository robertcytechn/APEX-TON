from django.contrib import admin
from .models import TicketSoporteTecnico


@admin.register(TicketSoporteTecnico)
class TicketSoporteTecnicoAdmin(admin.ModelAdmin):
	list_display = (
		'folio',
		'usuario_nombre',
		'problema_principal_etiqueta',
		'prioridad_etiqueta',
		'estado_seguimiento',
		'correo_soporte_enviado',
		'correo_confirmacion_enviado',
		'creado_en',
	)
	list_filter = ('estado_seguimiento', 'prioridad', 'bloqueo_operativo', 'correo_soporte_enviado', 'correo_confirmacion_enviado')
	search_fields = ('folio', 'usuario_nombre', 'usuario_username', 'usuario_correo', 'problema_principal_etiqueta', 'descripcion_detallada')
	readonly_fields = ('folio', 'creado_en', 'actualizado_en', 'atendido_en', 'resuelto_en')
