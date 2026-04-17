"""
Puente de compatibilidad para Celery.

Celery autodiscover busca por defecto `tasks.py`.
En este proyecto la implementación principal está en `tareas.py`,
por lo que este módulo asegura el registro de tareas en todos los entornos.
"""

from .tareas import *  # noqa: F401,F403
