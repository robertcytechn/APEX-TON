from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfiguracionGlobalViewSet, RubroContableViewSet

router = DefaultRouter()
router.register(r'configuraciones', ConfiguracionGlobalViewSet, basename='configuracionglobal')
router.register(r'rubros', RubroContableViewSet, basename='rubrocontable')

urlpatterns = [
    path('', include(router.urls)),
]
