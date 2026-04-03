from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfiguracionGlobalViewSet, PadreRubroContableViewSet, RubroContableViewSet

router = DefaultRouter()
router.register(r'configuraciones', ConfiguracionGlobalViewSet, basename='configuracionglobal')
router.register(r'rubros', RubroContableViewSet, basename='rubrocontable')
router.register(r'padres-rubros', PadreRubroContableViewSet, basename='padrerubrocontable')

urlpatterns = [
    path('', include(router.urls)),
]
