from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfiguracionUsuarioViewSet

router = DefaultRouter()
router.register(r'configuracion-usuario', ConfiguracionUsuarioViewSet, basename='configuracionusuario')

urlpatterns = [
    path('', include(router.urls)),
]
