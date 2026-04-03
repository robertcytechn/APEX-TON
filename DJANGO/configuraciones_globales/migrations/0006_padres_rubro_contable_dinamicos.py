from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


PADRES_BASE = [
    ('NINGUNO', 'Ninguno'),
    ('INGRESOS', 'Ingresos'),
    ('GASTOS', 'Gastos'),
    ('CARGAR_FISCALES', 'Cargar Fiscales'),
    ('COCINA', 'Cocina'),
    ('JUEGO_VIVO', 'Juego Vivo'),
    ('PAGO_MAQUINAS', 'Pago Maquinas'),
    ('OTROS_INGRESOS', 'Otros Ingresos'),
    ('OTROS_GASTOS', 'Otros Gastos'),
]


def migrar_padres_a_catalogo(apps, schema_editor):
    PadreRubroContable = apps.get_model('configuraciones_globales', 'PadreRubroContable')
    RubroContable = apps.get_model('configuraciones_globales', 'RubroContable')

    for clave, nombre in PADRES_BASE:
        PadreRubroContable.objects.update_or_create(
            clave=clave,
            defaults={
                'nombre': nombre,
                'descripcion': 'Padre de rubro creado durante normalizacion de catalogo dinamico.',
                'estado': 'ACTIVO',
                'eliminado_en': None,
                'eliminado_por': None,
            },
        )

    for rubro in RubroContable._base_manager.all():
        clave_padre = (getattr(rubro, 'padre', None) or 'NINGUNO').strip()
        padre = PadreRubroContable.objects.filter(clave=clave_padre).first()

        if padre is None:
            nombre_generado = clave_padre.replace('_', ' ').title()
            padre = PadreRubroContable.objects.create(
                clave=clave_padre,
                nombre=nombre_generado,
                descripcion='Padre de rubro creado automaticamente desde datos historicos.',
                estado='ACTIVO',
            )

        rubro.padre_nuevo_id = padre.id
        rubro.save(update_fields=['padre_nuevo'])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('configuraciones_globales', '0005_cargar_rubros_gastos_base'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PadreRubroContable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo'), ('BLOQUEADO', 'Bloqueado'), ('ELIMINADO', 'Eliminado')], default='ACTIVO', help_text='Estado actual del registro dentro del ciclo de vida: ACTIVO, INACTIVO, BLOQUEADO o ELIMINADO.', max_length=20, verbose_name='Estado')),
                ('creado_en', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora de creacion del registro.', verbose_name='Creado en')),
                ('actualizado_en', models.DateTimeField(auto_now=True, help_text='Fecha y hora de la ultima actualizacion del registro.', verbose_name='Actualizado en')),
                ('eliminado_en', models.DateTimeField(blank=True, help_text='Fecha y hora en que el registro fue marcado como eliminado (Soft Delete). Si es nulo, el registro esta vigente.', null=True, verbose_name='Eliminado en')),
                ('valor_anterior', models.JSONField(blank=True, help_text='Estado del registro antes de la ultima modificacion (Auditoria).', null=True, verbose_name='Valor anterior')),
                ('valor_actual', models.JSONField(blank=True, help_text='Estado del registro despues de la ultima modificacion (Auditoria).', null=True, verbose_name='Valor actual')),
                ('clave', models.CharField(help_text='Identificador unico del padre de rubro en formato tecnico (ej. GASTOS).', max_length=150, unique=True, verbose_name='Clave del Padre')),
                ('nombre', models.CharField(help_text='Nombre visible del padre de rubro para uso en catalogos y formularios.', max_length=150, unique=True, verbose_name='Nombre del Padre')),
                ('descripcion', models.TextField(blank=True, help_text='Descripcion opcional del padre de rubro contable.', null=True, verbose_name='Descripcion')),
                ('actualizado_por', models.ForeignKey(blank=True, help_text='Usuario que realizo la ultima actualizacion.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_actualizado_por', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
                ('creado_por', models.ForeignKey(blank=True, help_text='Usuario que creo el registro.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_creado_por', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('eliminado_por', models.ForeignKey(blank=True, help_text='Usuario que elimino el registro.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_eliminado_por', to=settings.AUTH_USER_MODEL, verbose_name='Eliminado por')),
            ],
            options={
                'verbose_name': 'Padre de Rubro Contable',
                'verbose_name_plural': 'Padres de Rubros Contables',
                'db_table': 'padre_rubro_contable',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='rubrocontable',
            name='padre_nuevo',
            field=models.ForeignKey(blank=True, help_text='Padre temporal de rubro usado durante migracion de datos.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='rubros_contables_temporales', to='configuraciones_globales.padrerubrocontable', verbose_name='Padre del Rubro (Temporal)'),
        ),
        migrations.RunPython(migrar_padres_a_catalogo, noop_reverse),
        migrations.RemoveField(
            model_name='rubrocontable',
            name='padre',
        ),
        migrations.RenameField(
            model_name='rubrocontable',
            old_name='padre_nuevo',
            new_name='padre',
        ),
        migrations.AlterField(
            model_name='rubrocontable',
            name='padre',
            field=models.ForeignKey(help_text='Padre de rubro al que pertenece este rubro para su agrupacion contable.', on_delete=django.db.models.deletion.PROTECT, related_name='rubros_contables', to='configuraciones_globales.padrerubrocontable', verbose_name='Padre del Rubro'),
        ),
    ]
