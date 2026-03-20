# Migración 0002: Agrega los FK de auditoría (creado_por, actualizado_por, eliminado_por)
# a Sucursal una vez que el modelo Usuario (AUTH_USER_MODEL) ya existe.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sucursales', '0001_initial'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sucursal',
            name='creado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sucursales_sucursal_creado_por',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Creado por',
                help_text='Usuario que creó el registro.'
            ),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='actualizado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sucursales_sucursal_actualizado_por',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Actualizado por',
                help_text='Usuario que realizó la última actualización.'
            ),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='eliminado_por',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sucursales_sucursal_eliminado_por',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Eliminado por',
                help_text='Usuario que eliminó el registro (Soft Delete).'
            ),
        ),
    ]
