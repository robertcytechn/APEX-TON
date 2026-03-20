from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LibroEstadoResultadosViewSet

router = DefaultRouter()
router.register(r'libro-estado-resultados', LibroEstadoResultadosViewSet, basename='libroestadoresultados')

urlpatterns = [
    path('', include(router.urls)),
]
