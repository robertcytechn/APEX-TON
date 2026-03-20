from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaOperativaViewSet, ConceptoViewSet, DetalleParametrizadoViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaOperativaViewSet, basename='categoriaoperativa')
router.register(r'conceptos', ConceptoViewSet, basename='concepto')
router.register(r'detalles-parametrizados', DetalleParametrizadoViewSet, basename='detalleparametrizado')

urlpatterns = [
    path('', include(router.urls)),
]
