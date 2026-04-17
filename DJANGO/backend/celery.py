"""
Configuración de Celery para el proyecto APEX-TON.
Los workers de Celery se encargan de ejecutar tareas asíncronas y programadas,
como el cierre automático del día contable.
"""
import os
from celery import Celery

# Establecer el módulo de configuración de Django por defecto para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# Leer la configuración desde settings.py usando el namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas con convención estándar (tasks.py).
app.autodiscover_tasks(force=True)

# Compatibilidad con este proyecto: algunos módulos usan `tareas.py`.
app.autodiscover_tasks(related_name='tareas', force=True)


@app.task(bind=True, ignore_result=True)
def debug_tarea(self):
    """Tarea de depuración para verificar que Celery funciona correctamente."""
    print(f'Solicitud: {self.request!r}')
