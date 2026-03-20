from django.urls import path
from .views import EstadoResultadosAPIView

urlpatterns = [
    path('estado-resultados/', EstadoResultadosAPIView.as_view(), name='estado-resultados'),
]
