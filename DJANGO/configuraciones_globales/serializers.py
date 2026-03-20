from rest_framework import serializers
from .models import ConfiguracionGlobal, RubroContable

class ConfiguracionGlobalSerializer(serializers.ModelSerializer):
    valor_tipado = serializers.ReadOnlyField()

    class Meta:
        model = ConfiguracionGlobal
        fields = '__all__'

class RubroContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubroContable
        fields = '__all__'
