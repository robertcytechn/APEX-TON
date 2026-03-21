from django.db import migrations


NOMBRES_RUBROS_GASTOS_BASE = [
    'nomina',
    'Aguinaldos',
    'Seguro Social',
    'Sorteos PNR',
    'Finiquitos',
    'Renta casa Gerente',
    'Paqueteria y Fletes',
    'RH',
    'CFE',
    'PSA',
    'Renta Local',
    'Poliza/fianza',
    'Musica',
    'Comisiones bancarias',
    'honorarios contables',
    'Licencia funcionamiento',
    'Fonacot',
    'Seguridad sala',
    'cctv',
    'Agua Potable',
    'uniformes',
    'Telmex',
    'Eventos/decoracion',
    'gasolina',
    'refacciones',
    'limpieza',
    'Fumigacion',
    'sindicato',
    'Papeleria',
    'Mantenimiento',
    'Lavanderia',
    'Posada Navidena',
    'Mobiliario. Equipo',
    'PTU',
    'Refrescador aire',
    'Publicidad',
    'Adm. de nomina',
    'viaticos',
    'Proteccion civil',
    'Transporte',
    'Cigarros',
    'Varios/Sala',
]

NOMBRES_RUBROS_CARGAS_FISCALES_BASE = [
    'Impuestos',
    'Impuestos erogaciones',
    'PSA',
    'Pago Permiso',
    'Segob',
]

NOMBRES_RUBROS_COCINA_BASE = [
    'Cafe nescafe',
    'Gas tanque',
    'Lacteos y carnes frias',
    'Equipo cocina',
    'Carnicos',
    'Tortilleria y panaderia',
    'Ingredientes',
    'frutas verduras',
    'Barra Abarrotes',
    'Vinos y cerveza',
    'Garrafones Y botellitas',
    'Agua',
    'Refrescos y jugos',
    'Utensilios',
    'Hielo',
    'abarrotes',
    'postres',
    'Buffet',
]

NOMBRES_RUBROS_JUEGO_VIVO_BASE = [
    'Renta',
    'TRANSPORTE',
    'IMSS',
    'monitoreo CCTV',
    'Honorarios',
    'Nomina',
    'impuestos varios',
    'Finiquitos',
    'Jugos , refrescos',
    'BOTANA',
    'Rh vacantes',
    'Telmex',
    'Paqueteria',
    'Admon nominas',
    'Limpieza',
    'Vinos, cerveza',
    'Barra',
    'Uniformes',
    'papeleria',
    'Sinatras retiro',
    'Publicidad',
    'Sala',
    'Cortesias alimentos',
    'Aguinaldos',
]

NOMBRES_RUBROS_PAGO_MAQUINAS_BASE = [
    'Merkur',
    'Ainsworth compra',
    'Fbm',
    'zitro regalias',
    'Aurora',
    'Gold Club',
    'Ainsworth regalias greats',
    'bb2 /ainsworth y 8% juego',
    'igt',
    'Novomatic',
    'Betstone',
    'AGS',
    'EGT',
]


def crear_rubros_gastos_base(apps, schema_editor):
    RubroContable = apps.get_model('configuraciones_globales', 'RubroContable')

    for nombre in NOMBRES_RUBROS_GASTOS_BASE:
        RubroContable.objects.update_or_create(
            nombre=nombre,
            defaults={
                'padre': 'GASTOS',
                'tipo': 'EGRESO',
                'descripcion': 'Rubro de gasto base cargado desde catalogo inicial de egresos.',
            },
        )

    for nombre in NOMBRES_RUBROS_CARGAS_FISCALES_BASE:
        RubroContable.objects.update_or_create(
            nombre=nombre,
            defaults={
                'padre': 'CARGAR_FISCALES',
                'tipo': 'EGRESO',
                'descripcion': 'Rubro de carga fiscal base cargado desde catalogo inicial de egresos.',
            },
        )

    for nombre in NOMBRES_RUBROS_COCINA_BASE:
        RubroContable.objects.update_or_create(
            nombre=nombre,
            defaults={
                'padre': 'COCINA',
                'tipo': 'EGRESO',
                'descripcion': 'Rubro de cocina base cargado desde catalogo inicial de egresos.',
            },
        )

    for nombre in NOMBRES_RUBROS_JUEGO_VIVO_BASE:
        RubroContable.objects.update_or_create(
            nombre=nombre,
            defaults={
                'padre': 'JUEGO_VIVO',
                'tipo': 'EGRESO',
                'descripcion': 'Rubro de juego vivo base cargado desde catalogo inicial de egresos.',
            },
        )

    for nombre in NOMBRES_RUBROS_PAGO_MAQUINAS_BASE:
        RubroContable.objects.update_or_create(
            nombre=nombre,
            defaults={
                'padre': 'PAGO_MAQUINAS',
                'tipo': 'EGRESO',
                'descripcion': 'Rubro de pago de maquinas base cargado desde catalogo inicial de egresos.',
            },
        )


def revertir_rubros_gastos_base(apps, schema_editor):
    # Reversa no destructiva para evitar borrar catalogos si ya tuvieron uso operativo.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('configuraciones_globales', '0004_configuracionglobal_estado_rubrocontable_estado_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_rubros_gastos_base, revertir_rubros_gastos_base),
    ]
