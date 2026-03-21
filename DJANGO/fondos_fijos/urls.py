from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FondoFijoViewSet, SucursalFondoFijoViewSet

router = DefaultRouter()
router.register(r'fondos-fijos', FondoFijoViewSet, basename='fondofijo')
router.register(r'sucursales-fondos-fijos', SucursalFondoFijoViewSet, basename='sucursalfondofijo')

urlpatterns = [
    path('', include(router.urls)),
]
