from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FondoFijoViewSet

router = DefaultRouter()
router.register(r'fondos-fijos', FondoFijoViewSet, basename='fondofijo')

urlpatterns = [
    path('', include(router.urls)),
]
