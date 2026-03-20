from rest_framework import viewsets
from .models import ConfiguracionGlobal, RubroContable
from .serializers import ConfiguracionGlobalSerializer, RubroContableSerializer

class ConfiguracionGlobalViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar configuraciones globales.
    """
    queryset = ConfiguracionGlobal.objects.all()
    serializer_class = ConfiguracionGlobalSerializer

class RubroContableViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar rubros contables.
    """
    queryset = RubroContable.objects.all()
    serializer_class = RubroContableSerializer
