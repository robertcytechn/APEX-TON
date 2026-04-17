from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfiguracionGlobalPublicaMantenimientoAPIView,
    ConfiguracionGlobalViewSet,
    PadreRubroContableViewSet,
    RubroContableViewSet,
)

router = DefaultRouter()
router.register(r'configuraciones', ConfiguracionGlobalViewSet, basename='configuracionglobal')
router.register(r'rubros', RubroContableViewSet, basename='rubrocontable')
router.register(r'padres-rubros', PadreRubroContableViewSet, basename='padrerubrocontable')

urlpatterns = [
    path('publicas/mantenimiento/', ConfiguracionGlobalPublicaMantenimientoAPIView.as_view(), name='configuraciones-publicas-mantenimiento'),
    path('', include(router.urls)),
]
