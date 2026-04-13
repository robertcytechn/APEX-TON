from django.urls import path
from .views import EstadoResultadosAPIView, EstadisticasOperativasAPIView

urlpatterns = [
    path('estado-resultados/', EstadoResultadosAPIView.as_view(), name='estado-resultados'),
    path('estado-resultados/estadisticas/', EstadisticasOperativasAPIView.as_view(), name='estado-resultados-estadisticas'),
]
