from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfiguracionGlobalCabinaViewSet,
    RolCabinaViewSet,
    RubroContableCabinaViewSet,
    SucursalCabinaViewSet,
    UsuarioCabinaViewSet,
)

router = DefaultRouter()
router.register(r'cabina-arquitectura/roles', RolCabinaViewSet, basename='cabina-roles')
router.register(r'cabina-arquitectura/usuarios', UsuarioCabinaViewSet, basename='cabina-usuarios')
router.register(r'cabina-arquitectura/sucursales', SucursalCabinaViewSet, basename='cabina-sucursales')
router.register(r'cabina-arquitectura/configuraciones-globales', ConfiguracionGlobalCabinaViewSet, basename='cabina-configuraciones-globales')
router.register(r'cabina-arquitectura/rubros-contables', RubroContableCabinaViewSet, basename='cabina-rubros-contables')

urlpatterns = [
    path('', include(router.urls)),
]
