from .celery import app as celery_app

# Compatibilidad con resolucion de Celery via `-A backend`.
app = celery_app
celery = celery_app

__all__ = ('celery_app', 'app', 'celery')
