import random
import unicodedata
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from categoria_operativa.models import Concepto
from reportes_diarios.models import MovimientoDiario, ReporteDiario
from sucursales.models import Sucursal
from usuarios.models import Usuario


# 1) Para que sirve: normalizar texto para busquedas robustas por clave/nombre.
# 2) Como funciona: quita acentos, espacios y simbolos para comparar de forma flexible.
# 3) Que hace: permite localizar conceptos aun con variaciones ortograficas.
# 4) Como editarla: agrega reglas nuevas si cambian los formatos de captura en catalogos.
def _normalizar_texto(valor):
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")
    for simbolo in (" ", "_", "-", "/", "."):
        texto = texto.replace(simbolo, "")
    return texto


# 1) Para que sirve: convertir cualquier numero a decimal monetario de 2 decimales.
# 2) Como funciona: transforma a Decimal desde string y redondea a centavos.
# 3) Que hace: garantiza montos consistentes para el modelo de movimientos.
# 4) Como editarla: ajusta precision si la politica monetaria cambia.
def _a_monto(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# 1) Para que sirve: obtener primer dia habil de un mes (lunes-viernes).
# 2) Como funciona: inicia en dia 1 y avanza si cae en sabado o domingo.
# 3) Que hace: permite calendarizar renta y otros pagos mensuales realistas.
# 4) Como editarla: incorpora feriados si despues se requiere calendario laboral completo.
def _primer_dia_habil(anio, mes):
    fecha = date(anio, mes, 1)
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha


class Command(BaseCommand):
    help = (
        "Simula un ano completo de operacion del casino para una sucursal. "
        "Genera reportes diarios cerrados y movimientos con patrones realistas "
        "(nomina quincenal, renta mensual, IMSS/INFONAVIT bimestral y consumo operativo)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--anio",
            type=int,
            default=timezone.localdate().year - 1,
            help="Ano a simular completo (por defecto: ano anterior).",
        )
        parser.add_argument(
            "--sucursal",
            type=str,
            default="prueba",
            help="Nombre, clave o ID de la sucursal objetivo (por defecto: prueba).",
        )
        parser.add_argument(
            "--usuario",
            type=str,
            default="conta",
            help="Username del usuario que quedara como creador/cierre (por defecto: conta).",
        )
        parser.add_argument(
            "--semilla",
            type=int,
            default=20260413,
            help="Semilla pseudoaleatoria para resultados reproducibles.",
        )
        parser.add_argument(
            "--saldo-inicial",
            type=str,
            default="250000.00",
            help="Saldo de arrastre inicial al 1 de enero.",
        )
        parser.add_argument(
            "--no-reemplazar",
            action="store_true",
            help="No elimina reportes previos del ano (salta dias que ya existan).",
        )

    # 1) Para que sirve: ubicar un concepto activo por fragmentos de texto.
    # 2) Como funciona: compara tokens normalizados contra clave y nombre del concepto.
    # 3) Que hace: facilita mapear catalogos sin depender de IDs fijos.
    # 4) Como editarla: agrega prioridad por categoria si se crean conceptos homonimos.
    def _buscar_concepto(self, conceptos, *fragmentos):
        tokens = [_normalizar_texto(fragmento) for fragmento in fragmentos if fragmento]
        for concepto in conceptos:
            huella = _normalizar_texto(concepto.clave) + _normalizar_texto(concepto.nombre)
            if all(token in huella for token in tokens):
                return concepto
        return None

    # 1) Para que sirve: generar tipo de cambio diario con estacionalidad leve.
    # 2) Como funciona: parte de una base mensual y agrega variacion pseudoaleatoria.
    # 3) Que hace: entrega snapshots historicos consistentes por reporte diario.
    # 4) Como editarla: ajusta rangos para reflejar escenarios macroeconomicos distintos.
    def _tasas_del_dia(self, fecha, aleatorio):
        base_usd_mes = {
            1: 17.20,
            2: 17.05,
            3: 16.95,
            4: 17.10,
            5: 17.35,
            6: 17.50,
            7: 17.65,
            8: 17.80,
            9: 17.55,
            10: 17.40,
            11: 17.70,
            12: 18.05,
        }
        usd = _a_monto(base_usd_mes.get(fecha.month, 17.50) + aleatorio.uniform(-0.22, 0.22)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        eur = _a_monto(float(usd) + 1.05 + aleatorio.uniform(-0.30, 0.30)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        return usd, eur

    # 1) Para que sirve: resolver fecha de cierre historico por cada dia contable simulado.
    # 2) Como funciona: crea datetime local del mismo dia a una hora nocturna fija.
    # 3) Que hace: deja trazabilidad coherente de cierres diarios pasados.
    # 4) Como editarla: mueve la hora de cierre segun reglas operativas reales.
    def _fecha_cierre(self, fecha):
        zona = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(fecha, time(23, 35)), zona)

    # 1) Para que sirve: agregar un movimiento a la lista con monto seguro y metadatos.
    # 2) Como funciona: valida concepto/monto y construye instancia MovimientoDiario.
    # 3) Que hace: centraliza alta de movimientos para evitar codigo repetido.
    # 4) Como editarla: incorpora aqui nuevos campos de captura si se habilitan en modelo.
    def _agregar_movimiento(self, lista, reporte, concepto, monto, usuario, notas=""):
        if concepto is None:
            return
        monto_decimal = _a_monto(monto)
        if monto_decimal <= 0:
            return

        lista.append(
            MovimientoDiario(
                reporte=reporte,
                concepto=concepto,
                monto=monto_decimal,
                notas=notas,
                detalles_snapshot={},
                creado_por=usuario,
                actualizado_por=usuario,
            )
        )

    # 1) Para que sirve: asignar probabilidad y rango por concepto de cocina.
    # 2) Como funciona: interpreta nombre/clave del concepto y devuelve configuracion base.
    # 3) Que hace: modela consumo de insumos con patrones mas cercanos a operacion real.
    # 4) Como editarla: calibra probabilidades y montos segun historico del casino.
    def _perfil_cocina(self, concepto):
        huella = _normalizar_texto(concepto.clave) + _normalizar_texto(concepto.nombre)

        if "gas" in huella:
            return 0.20, 4200, 11200
        if "frutas" in huella or "verduras" in huella:
            return 0.62, 1800, 7200
        if "carnicos" in huella or "carnesfrias" in huella:
            return 0.44, 2600, 9800
        if "lacteos" in huella:
            return 0.52, 1400, 5600
        if "ingredientes" in huella:
            return 0.58, 2200, 8600
        if "refrescos" in huella or "jugos" in huella:
            return 0.48, 1800, 6700
        if "vinos" in huella or "cerveza" in huella:
            return 0.28, 1600, 10500
        if "garrafones" in huella or "agua" in huella:
            return 0.42, 900, 3600
        if "hielo" in huella:
            return 0.45, 700, 2800
        if "tortilleria" in huella or "panaderia" in huella:
            return 0.50, 1200, 4700
        if "utensilios" in huella or "equipo" in huella:
            return 0.15, 900, 6400
        if "postres" in huella:
            return 0.22, 1100, 4400
        if "buffet" in huella:
            return 0.18, 2000, 8800
        if "barra" in huella or "abarrotes" in huella:
            return 0.36, 1500, 6900
        if "cafe" in huella or "nescafe" in huella:
            return 0.40, 900, 3300

        return 0.22, 1200, 5000

    # 1) Para que sirve: construir movimientos diarios con reglas operativas del negocio.
    # 2) Como funciona: combina ingresos base, pagos periodicos y gasto de cocina por probabilidad.
    # 3) Que hace: produce una jornada completa con eventos realistas y montos monetarios.
    # 4) Como editarla: agrega nuevos eventos recurrentes conforme crezca el catalogo.
    def _generar_movimientos_dia(self, reporte, fecha, mapa, cocina_egresos, usuario, aleatorio):
        movimientos = []

        dia_semana = fecha.weekday()  # 0=lunes, 6=domingo
        ultimo_dia_mes = monthrange(fecha.year, fecha.month)[1]
        es_fin_semana_largo = dia_semana in (4, 5, 6)

        factor_mes = {
            1: 0.95,
            2: 0.92,
            3: 0.98,
            4: 1.04,
            5: 1.08,
            6: 1.02,
            7: 1.10,
            8: 1.12,
            9: 1.01,
            10: 1.06,
            11: 1.20,
            12: 1.33,
        }.get(fecha.month, 1.00)
        factor_dia = 1.14 if es_fin_semana_largo else (1.05 if dia_semana == 3 else 1.00)
        factor_operativo = factor_mes * factor_dia

        # Ingresos diarios base
        self._agregar_movimiento(
            movimientos,
            reporte,
            mapa.get("recaudacion"),
            aleatorio.uniform(165000, 295000) * factor_operativo,
            usuario,
            "Ingreso base diario de juego y sala.",
        )
        self._agregar_movimiento(
            movimientos,
            reporte,
            mapa.get("gastronomico"),
            aleatorio.uniform(12000, 42000) * factor_operativo,
            usuario,
            "Ingreso diario de alimentos y bebidas.",
        )
        self._agregar_movimiento(
            movimientos,
            reporte,
            mapa.get("kiosko"),
            aleatorio.uniform(4500, 17000) * factor_operativo,
            usuario,
            "Ingreso diario de kiosko.",
        )

        # Ingresos por cambio de divisa
        prob_dolares = 0.30 if not es_fin_semana_largo else 0.68
        if mapa.get("dolares") and aleatorio.random() < prob_dolares:
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("dolares"),
                aleatorio.uniform(2500, 19000) * (1.12 if es_fin_semana_largo else 1.0),
                usuario,
                "Cambio de dolares en caja.",
            )

        # Ingreso bancario recurrente
        if mapa.get("billpocket") and (dia_semana in (1, 4) or aleatorio.random() < 0.14):
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("billpocket"),
                aleatorio.uniform(28000, 92000),
                usuario,
                "Deposito operativo en cuenta Bill POKET.",
            )

        # Aportes extraordinarios trimestrales
        if mapa.get("aporte") and fecha.month in (3, 6, 9, 12) and fecha.day in (11, 24):
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("aporte"),
                aleatorio.uniform(18000, 50000),
                usuario,
                "Aporte extraordinario trimestral.",
            )

        # Reserva de impuestos quincenal
        if mapa.get("reserva_impuesto") and fecha.day in (5, 20):
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("reserva_impuesto"),
                aleatorio.uniform(9000, 27000),
                usuario,
                "Provision quincenal de reserva para impuestos.",
            )

        # Nomina quincenal (15 y ultimo dia del mes)
        if mapa.get("nomina") and (fecha.day == 15 or fecha.day == ultimo_dia_mes):
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("nomina"),
                aleatorio.uniform(175000, 275000),
                usuario,
                "Pago de nomina quincenal.",
            )

        # Renta mensual (primer dia habil)
        primer_habil = _primer_dia_habil(fecha.year, fecha.month)
        if mapa.get("caja_chica") and fecha == primer_habil:
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("caja_chica"),
                aleatorio.uniform(95000, 150000),
                usuario,
                "Pago mensual de renta del inmueble.",
            )

        # IMSS e INFONAVIT cada dos meses
        if mapa.get("caja_chica") and fecha.month % 2 == 0 and fecha.day == 17:
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("caja_chica"),
                aleatorio.uniform(65000, 125000),
                usuario,
                "Pago bimestral de IMSS e INFONAVIT.",
            )

        # Servicios fijos mensuales
        if mapa.get("caja_chica") and fecha.day == 10:
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("caja_chica"),
                aleatorio.uniform(18000, 42000),
                usuario,
                "Pago mensual de servicios (luz, agua, internet).",
            )

        # Reposicion operativa de caja chica semanal
        if mapa.get("caja_chica") and dia_semana in (0, 3):
            self._agregar_movimiento(
                movimientos,
                reporte,
                mapa.get("caja_chica"),
                aleatorio.uniform(3500, 14500),
                usuario,
                "Reposicion operativa semanal de caja chica.",
            )

        # Egresos de cocina con consumo diario variable
        for concepto_cocina in cocina_egresos:
            probabilidad, minimo, maximo = self._perfil_cocina(concepto_cocina)
            ajuste_fin_semana = 1.18 if es_fin_semana_largo else 1.0
            if aleatorio.random() < probabilidad:
                self._agregar_movimiento(
                    movimientos,
                    reporte,
                    concepto_cocina,
                    aleatorio.uniform(minimo, maximo) * ajuste_fin_semana,
                    usuario,
                    "Compra operativa de insumos de cocina.",
                )

        return movimientos

    def handle(self, *args, **options):
        anio = int(options["anio"])
        if anio < 2000 or anio > 2100:
            raise CommandError("El anio debe estar entre 2000 y 2100.")

        semilla = int(options["semilla"])
        reemplazar = not bool(options["no_reemplazar"])
        aleatorio = random.Random(semilla)

        try:
            saldo_arrastre = _a_monto(options["saldo_inicial"])
        except Exception as error:
            raise CommandError(f"Saldo inicial invalido: {error}") from error

        selector_sucursal = str(options["sucursal"] or "").strip()
        sucursal = None
        if selector_sucursal.isdigit():
            sucursal = Sucursal.todos.filter(id=int(selector_sucursal)).first()
        if not sucursal:
            sucursal = Sucursal.todos.filter(clave__iexact=selector_sucursal).first()
        if not sucursal:
            sucursal = Sucursal.todos.filter(nombre__iexact=selector_sucursal).first()
        if not sucursal:
            sucursal = Sucursal.todos.filter(nombre__icontains=selector_sucursal).first()
        if not sucursal:
            raise CommandError(f"No se encontro sucursal con selector: {selector_sucursal}")

        usuario = Usuario.objects.filter(username=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"No existe usuario con username: {options['usuario']}")

        if usuario.sucursal_id and usuario.sucursal_id != sucursal.id:
            raise CommandError(
                "El usuario seleccionado pertenece a otra sucursal. "
                f"Usuario.sucursal_id={usuario.sucursal_id}, sucursal objetivo={sucursal.id}."
            )

        conceptos = list(
            Concepto.todos.filter(estado="ACTIVO", eliminado_en__isnull=True)
            .select_related("categoria")
            .order_by("categoria__orden", "nombre")
        )
        if not conceptos:
            raise CommandError("No hay conceptos activos para simular movimientos.")

        mapa = {
            "recaudacion": self._buscar_concepto(conceptos, "recaudacion"),
            "gastronomico": self._buscar_concepto(conceptos, "gastronomico"),
            "kiosko": self._buscar_concepto(conceptos, "kiosko"),
            "dolares": self._buscar_concepto(conceptos, "dolar"),
            "billpocket": self._buscar_concepto(conceptos, "bill", "poket") or self._buscar_concepto(conceptos, "bill", "pocket"),
            "reserva_impuesto": self._buscar_concepto(conceptos, "reserva", "impuesto"),
            "nomina": self._buscar_concepto(conceptos, "nomina"),
            "caja_chica": self._buscar_concepto(conceptos, "caja", "chica"),
            "aporte": self._buscar_concepto(conceptos, "aporte", "sinatras"),
        }

        faltantes_esenciales = [
            clave for clave in ("recaudacion", "gastronomico", "kiosko", "nomina", "caja_chica") if mapa.get(clave) is None
        ]
        if faltantes_esenciales:
            raise CommandError(
                "No se encontraron conceptos esenciales para simular: "
                + ", ".join(faltantes_esenciales)
            )

        cocina_egresos = [
            concepto
            for concepto in conceptos
            if concepto.tipo == "EGRESO" and _normalizar_texto(getattr(concepto.categoria, "clave", "")) == "cocina"
        ]
        if not cocina_egresos:
            raise CommandError("No hay conceptos de egreso en la categoria Cocina para simular consumo diario.")

        fecha_inicio = date(anio, 1, 1)
        fecha_fin = date(anio, 12, 31)

        total_reportes = 0
        total_movimientos = 0
        total_ingresos_anuales = Decimal("0.00")
        total_egresos_anuales = Decimal("0.00")

        if reemplazar:
            borrados = ReporteDiario.todos.filter(sucursal=sucursal, fecha_contable__year=anio).count()
            if borrados:
                ReporteDiario.todos.filter(sucursal=sucursal, fecha_contable__year=anio).delete()
            self.stdout.write(self.style.WARNING(f"Reportes previos eliminados del ano {anio}: {borrados}"))

        with transaction.atomic():
            fecha_cursor = fecha_inicio
            while fecha_cursor <= fecha_fin:
                reporte_existente = ReporteDiario.todos.filter(
                    sucursal=sucursal,
                    fecha_contable=fecha_cursor,
                ).first()

                if reporte_existente and not reemplazar:
                    saldo_arrastre = reporte_existente.saldo_arrastre_fin
                    fecha_cursor += timedelta(days=1)
                    continue

                tasa_usd, tasa_eur = self._tasas_del_dia(fecha_cursor, aleatorio)

                reporte = ReporteDiario.todos.create(
                    sucursal=sucursal,
                    fecha_contable=fecha_cursor,
                    estado_reporte=ReporteDiario.EstadoReporte.CERRADO,
                    saldo_arrastre_inicio=saldo_arrastre,
                    saldo_arrastre_fin=saldo_arrastre,
                    tipo_cambio_usd_snapshot=tasa_usd,
                    tipo_cambio_eur_snapshot=tasa_eur,
                    total_ingresos=Decimal("0.00"),
                    total_egresos=Decimal("0.00"),
                    resultado_neto=Decimal("0.00"),
                    cerrado_en=self._fecha_cierre(fecha_cursor),
                    cerrado_por=usuario,
                    observaciones=(
                        f"Simulacion automatica del ano {anio}. "
                        "Niveles aproximados de operacion para analitica y pruebas."
                    ),
                    creado_por=usuario,
                    actualizado_por=usuario,
                )

                movimientos = self._generar_movimientos_dia(
                    reporte=reporte,
                    fecha=fecha_cursor,
                    mapa=mapa,
                    cocina_egresos=cocina_egresos,
                    usuario=usuario,
                    aleatorio=aleatorio,
                )

                if not movimientos:
                    self._agregar_movimiento(
                        movimientos,
                        reporte,
                        mapa["recaudacion"],
                        aleatorio.uniform(180000, 230000),
                        usuario,
                        "Ingreso minimo de seguridad para dia sin eventos.",
                    )

                MovimientoDiario.todos.bulk_create(movimientos, batch_size=500)

                total_ingresos_dia = sum(
                    (mov.monto for mov in movimientos if mov.concepto.tipo == "INGRESO"),
                    Decimal("0.00"),
                )
                total_egresos_dia = sum(
                    (mov.monto for mov in movimientos if mov.concepto.tipo == "EGRESO"),
                    Decimal("0.00"),
                )
                neto_dia = total_ingresos_dia - total_egresos_dia
                saldo_fin_dia = _a_monto(Decimal(saldo_arrastre) + neto_dia)

                reporte.total_ingresos = _a_monto(total_ingresos_dia)
                reporte.total_egresos = _a_monto(total_egresos_dia)
                reporte.resultado_neto = _a_monto(neto_dia)
                reporte.saldo_arrastre_fin = saldo_fin_dia
                reporte.save(
                    update_fields=[
                        "total_ingresos",
                        "total_egresos",
                        "resultado_neto",
                        "saldo_arrastre_fin",
                        "actualizado_en",
                        "actualizado_por",
                    ]
                )

                saldo_arrastre = saldo_fin_dia
                total_reportes += 1
                total_movimientos += len(movimientos)
                total_ingresos_anuales += reporte.total_ingresos
                total_egresos_anuales += reporte.total_egresos

                fecha_cursor += timedelta(days=1)

        resultado_neto_anual = total_ingresos_anuales - total_egresos_anuales
        self.stdout.write(self.style.SUCCESS("Simulacion anual completada exitosamente."))
        self.stdout.write(f"Sucursal: {sucursal.id} - {sucursal.nombre}")
        self.stdout.write(f"Usuario creador: {usuario.username}")
        self.stdout.write(f"Ano simulado: {anio}")
        self.stdout.write(f"Reportes creados/actualizados: {total_reportes}")
        self.stdout.write(f"Movimientos creados: {total_movimientos}")
        self.stdout.write(f"Total ingresos anual: ${_a_monto(total_ingresos_anuales):,.2f}")
        self.stdout.write(f"Total egresos anual: ${_a_monto(total_egresos_anuales):,.2f}")
        self.stdout.write(f"Resultado neto anual: ${_a_monto(resultado_neto_anual):,.2f}")
        self.stdout.write(f"Saldo de arrastre final: ${_a_monto(saldo_arrastre):,.2f}")
