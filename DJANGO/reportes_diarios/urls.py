from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReporteDiarioViewSet, MovimientoDiarioViewSet

router = DefaultRouter()
router.register(r'reportes-diarios', ReporteDiarioViewSet, basename='reportediario')
router.register(r'movimientos-diarios', MovimientoDiarioViewSet, basename='movimientodiario')

urlpatterns = [
    path('', include(router.urls)),
]
