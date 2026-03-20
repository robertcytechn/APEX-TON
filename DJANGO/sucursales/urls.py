from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SucursalViewSet

router = DefaultRouter()
router.register(r'sucursales', SucursalViewSet, basename='sucursal')

urlpatterns = [
    path('', include(router.urls)),
]
