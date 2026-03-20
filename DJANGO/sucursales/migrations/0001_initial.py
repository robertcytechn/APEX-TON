# Migración inicial de sucursales. Los FK a AUTH_USER_MODEL se agregan en 0002
# para evitar dependencia circular con la app usuarios.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo'), ('BLOQUEADO', 'Bloqueado'), ('ELIMINADO', 'Eliminado')], default='ACTIVO', help_text='Estado actual del registro.', max_length=20, verbose_name='Estado')),
                ('creado_en', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora de creación.', verbose_name='Creado en')),
                ('actualizado_en', models.DateTimeField(auto_now=True, help_text='Fecha y hora de última actualización.', verbose_name='Actualizado en')),
                ('eliminado_en', models.DateTimeField(blank=True, null=True, help_text='Fecha de eliminación lógica.', verbose_name='Eliminado en')),
                ('valor_anterior', models.JSONField(blank=True, null=True, help_text='Valor anterior del registro.', verbose_name='Valor anterior')),
                ('valor_actual', models.JSONField(blank=True, null=True, help_text='Valor actual del registro.', verbose_name='Valor actual')),
                ('nombre', models.CharField(max_length=150, unique=True, help_text="Nombre comercial único de la sucursal.", verbose_name='Nombre de la Sucursal')),
                ('clave', models.CharField(max_length=30, unique=True, help_text="Código corto de identificación interna.", verbose_name='Clave Interna')),
                ('direccion', models.TextField(blank=True, null=True, help_text='Domicilio completo.', verbose_name='Dirección')),
                ('ciudad', models.CharField(blank=True, null=True, max_length=100, help_text='Ciudad o municipio.', verbose_name='Ciudad')),
                ('estado_republica', models.CharField(blank=True, null=True, max_length=100, help_text='Entidad federativa.', verbose_name='Estado (República)')),
                ('telefono', models.CharField(blank=True, null=True, max_length=20, help_text='Teléfono de contacto.', verbose_name='Teléfono')),
                ('correo', models.EmailField(blank=True, null=True, help_text='Correo institucional.', verbose_name='Correo Electrónico')),
                ('encargado', models.CharField(blank=True, null=True, max_length=150, help_text='Responsable operativo.', verbose_name='Responsable / Encargado')),
                ('fondo_inicial', models.DecimalField(decimal_places=2, default=0.0, max_digits=18, help_text='Monto inicial del fondo fijo en MXN.', verbose_name='Fondo Inicial')),
            ],
            options={
                'verbose_name': 'Sucursal',
                'verbose_name_plural': 'Sucursales',
                'db_table': 'sucursales',
                'ordering': ['nombre'],
            },
        ),
    ]

