<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { listarCategoriasOperativas, listarMovimientosDiarios, obtenerSaldoInicialCategoriaMensual } from '@/service/capturaOperativaServicio';
import { listarSucursalesReporte } from '@/service/estadoResultadosServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargandoCatalogos = ref(false);
const cargandoConsulta = ref(false);
const mensaje = ref('');

const sucursales = ref([]);
const categorias = ref([]);
const movimientos = ref([]);

const hoy = new Date();
const diaContableBase = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);

const filtroSucursalId = ref(null);
const filtroFechaInicio = ref(new Date(diaContableBase));
const filtroFechaFin = ref(new Date(diaContableBase));
const filtroCategoriaId = ref(null);

const categoriaSeleccionada = computed(() => {
    return categorias.value.find((categoria) => Number(categoria.id) === Number(filtroCategoriaId.value)) || null;
});

const sucursalSeleccionada = computed(() => {
    return sucursales.value.find((sucursal) => Number(sucursal.id) === Number(filtroSucursalId.value)) || null;
});

const totalMovimientos = computed(() => movimientos.value.length);

const totalIngresos = computed(() => {
    return movimientos.value
        .filter((movimiento) => movimiento.tipoNormalizado === 'INGRESO')
        .reduce((acumulado, movimiento) => acumulado + Number(movimiento.montoNumerico || 0), 0);
});

const totalEgresos = computed(() => {
    return movimientos.value
        .filter((movimiento) => movimiento.tipoNormalizado === 'EGRESO')
        .reduce((acumulado, movimiento) => acumulado + Number(movimiento.montoNumerico || 0), 0);
});

const totalNeto = computed(() => Number(totalIngresos.value || 0) - Number(totalEgresos.value || 0));

const saldoInicialCategoria = ref(null);

const categoriaUsaSaldoInicial = computed(() => {
    return Boolean(saldoInicialCategoria.value?.categoria_usa_saldo_inicial);
});

const saldoFinalAcumulado = computed(() => {
    if (!categoriaUsaSaldoInicial.value || !saldoInicialCategoria.value) {
        return null;
    }
    return Number(saldoInicialCategoria.value.saldo_final_acumulado || 0);
});

const saldoInicialMes = computed(() => {
    if (!categoriaUsaSaldoInicial.value || !saldoInicialCategoria.value) {
        return null;
    }
    return Number(saldoInicialCategoria.value.saldo_inicial || 0);
});

// 1) Para qué sirve: formatear montos numéricos para mostrar en tarjetas de resumen.
// 2) Cómo funciona: usa Intl.NumberFormat con 2 decimales en locale es-MX.
// 3) Qué hace: devuelve string formateado para mostrar en celdas.
// 4) Cómo editarla: ajusta locale o decimales si se requiere.
function formatearMonto(valor) {
    return new Intl.NumberFormat('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number(valor || 0));
}

// 1) Para qué sirve: convertir Date local a formato ISO YYYY-MM-DD para filtros API.
// 2) Cómo funciona: serializa año, mes y día con padding.
// 3) Qué hace: garantiza formato de fecha esperado por backend.
// 4) Cómo editarla: centraliza aquí cambios de formato si la API se versiona.
function convertirFechaAISO(fecha) {
    if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) {
        return '';
    }

    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

// 1) Para qué sirve: formatear sello de tiempo de captura para la tabla.
// 2) Cómo funciona: transforma ISO a fecha/hora local en español.
// 3) Qué hace: muestra cuándo se capturó o actualizó cada movimiento.
// 4) Cómo editarla: ajusta formato corto/largo según preferencia de UX.
function formatearFechaHora(valor) {
    const texto = String(valor || '').trim();
    if (!texto) {
        return 'Sin sello de tiempo';
    }

    const fecha = new Date(texto);
    if (Number.isNaN(fecha.getTime())) {
        return 'Sin sello de tiempo';
    }

    return fecha.toLocaleString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 1) Para qué sirve: convertir detalles_snapshot a texto legible en una celda.
// 2) Cómo funciona: serializa pares clave/valor y concatena separadores visuales.
// 3) Qué hace: evita mostrar JSON crudo en la tabla de consulta.
// 4) Cómo editarla: reemplaza por modal expandible si se requiere mayor detalle.
function formatearDetallesSnapshot(detallesSnapshot) {
    if (!detallesSnapshot || typeof detallesSnapshot !== 'object') {
        return '-';
    }

    const entradas = Object.entries(detallesSnapshot)
        .filter(([clave]) => String(clave || '').trim().length > 0)
        .map(([clave, valor]) => `${clave}: ${valor ?? ''}`);

    return entradas.length ? entradas.join(' | ') : '-';
}

// 1) Para qué sirve: definir color de fila por naturaleza del movimiento.
// 2) Cómo funciona: evalúa tipo normalizado INGRESO/EGRESO.
// 3) Qué hace: mejora lectura estilo hoja de cálculo operativa.
// 4) Cómo editarla: ajusta paleta según lineamientos visuales del proyecto.
function claseFilaMovimiento(movimiento) {
    if (movimiento?.tipoNormalizado === 'INGRESO') {
        return 'bg-emerald-50/60';
    }
    if (movimiento?.tipoNormalizado === 'EGRESO') {
        return 'bg-rose-50/70';
    }
    return '';
}

// 1) Para qué sirve: preparar datos de movimientos para render y cálculos locales.
// 2) Cómo funciona: normaliza tipo, monto y sello de tiempo por fila.
// 3) Qué hace: evita lógica repetida dentro del template.
// 4) Cómo editarla: añade columnas derivadas nuevas aquí para mantener consistencia.
function normalizarMovimientos(listadoMovimientos) {
    return listadoMovimientos
        .map((movimiento) => {
            const selloTiempo = String(movimiento.actualizado_en || movimiento.creado_en || '').trim();
            return {
                ...movimiento,
                tipoNormalizado: String(movimiento.tipo || '').trim().toUpperCase(),
                montoNumerico: Number(movimiento.monto || 0),
                selloTiempo,
                selloTiempoTexto: formatearFechaHora(selloTiempo),
                detallesTexto: formatearDetallesSnapshot(movimiento.detalles_snapshot)
            };
        })
        .sort((a, b) => {
            const fechaA = new Date(String(a.selloTiempo || '')).getTime();
            const fechaB = new Date(String(b.selloTiempo || '')).getTime();
            return (Number.isNaN(fechaB) ? 0 : fechaB) - (Number.isNaN(fechaA) ? 0 : fechaA);
        });
}

// 1) Para qué sirve: cargar catálogo de sucursales y categorías para filtros de consulta.
// 2) Cómo funciona: consulta APIs en paralelo y define valores iniciales seguros.
// 3) Qué hace: deja lista la pantalla para ejecutar la primera búsqueda.
// 4) Cómo editarla: incorpora más catálogos aquí si el reporte agrega nuevos filtros.
async function cargarCatalogos() {
    cargandoCatalogos.value = true;
    mensaje.value = '';

    try {
        const [respuestaSucursales, respuestaCategorias] = await Promise.all([
            listarSucursalesReporte(),
            listarCategoriasOperativas()
        ]);

        const listadoSucursales = Array.isArray(respuestaSucursales?.data?.data) ? respuestaSucursales.data.data : [];
        const listadoCategorias = Array.isArray(respuestaCategorias?.data?.data) ? respuestaCategorias.data.data : [];

        sucursales.value = listadoSucursales
            .filter((sucursal) => String(sucursal?.estado || '').trim().toUpperCase() === 'ACTIVO')
            .sort((a, b) => String(a?.nombre || '').localeCompare(String(b?.nombre || ''), 'es-MX'));

        categorias.value = listadoCategorias
            .filter((categoria) => String(categoria?.estado || '').trim().toUpperCase() === 'ACTIVO')
            .sort((a, b) => Number(a?.orden || 0) - Number(b?.orden || 0));

        const sucursalUsuario = Number(sesionStore.usuario?.sucursal_id || 0);
        const sucursalDisponibleUsuario = sucursales.value.find((sucursal) => Number(sucursal.id) === sucursalUsuario);

        if (sucursalDisponibleUsuario) {
            filtroSucursalId.value = sucursalDisponibleUsuario.id;
        } else if (sucursales.value.length && !filtroSucursalId.value) {
            filtroSucursalId.value = sucursales.value[0].id;
        }

        if (!(filtroFechaInicio.value instanceof Date) || Number.isNaN(filtroFechaInicio.value.getTime())) {
            filtroFechaInicio.value = new Date(diaContableBase);
        }
        if (!(filtroFechaFin.value instanceof Date) || Number.isNaN(filtroFechaFin.value.getTime())) {
            filtroFechaFin.value = new Date(diaContableBase);
        }
    } catch (error) {
        mensaje.value = error?.response?.data?.message || 'No fue posible cargar catálogos para filtros de consulta.';
    } finally {
        cargandoCatalogos.value = false;
    }
}

// 1) Para qué sirve: consultar movimientos capturados en un rango de fechas y categoría de una sucursal.
// 2) Cómo funciona: lista movimientos filtrados directamente por sucursal y rango de fechas.
// 3) Qué hace: arma la tabla detallada de lectura para director/administrador.
// 4) Cómo editarla: agrega paginación o segmentaciones adicionales en params de consulta.
async function consultarMovimientos() {
    mensaje.value = '';
    movimientos.value = [];

    const fechaInicioIso = convertirFechaAISO(filtroFechaInicio.value);
    const fechaFinIso = convertirFechaAISO(filtroFechaFin.value);

    if (!filtroSucursalId.value) {
        mensaje.value = 'Selecciona un casino para consultar la captura operativa.';
        return;
    }

    if (!fechaInicioIso || !fechaFinIso) {
        mensaje.value = 'Selecciona fechas contables válidas.';
        return;
    }

    if (fechaInicioIso > fechaFinIso) {
        mensaje.value = 'La fecha de inicio no puede ser mayor que la fecha de fin.';
        return;
    }

    cargandoConsulta.value = true;
    try {
        // Consultar movimientos directamente por rango de fechas
        const parametrosMovimientos = {
            sucursal_id: filtroSucursalId.value,
            fecha_inicio: fechaInicioIso,
            fecha_fin: fechaFinIso
        };

        if (filtroCategoriaId.value) {
            parametrosMovimientos.categoria_id = filtroCategoriaId.value;
        }

        const { data: respuestaMovimientos } = await listarMovimientosDiarios(parametrosMovimientos);
        const listadoMovimientos = Array.isArray(respuestaMovimientos?.data) ? respuestaMovimientos.data : [];
        movimientos.value = normalizarMovimientos(listadoMovimientos);

        if (!movimientos.value.length) {
            mensaje.value = 'No hay movimientos capturados para los filtros seleccionados.';
        }

        // Consultar saldo inicial de la categoría seleccionada si aplica (usa fecha fin como referencia)
        saldoInicialCategoria.value = null;
        if (filtroCategoriaId.value && filtroSucursalId.value && fechaFinIso) {
            try {
                const { data: respuestaSaldo } = await obtenerSaldoInicialCategoriaMensual(
                    filtroSucursalId.value,
                    filtroCategoriaId.value,
                    fechaFinIso
                );
                saldoInicialCategoria.value = respuestaSaldo?.data || null;
            } catch {
                saldoInicialCategoria.value = null;
            }
        }
    } catch (error) {
        mensaje.value = error?.response?.data?.message || 'No fue posible consultar movimientos capturados.';
    } finally {
        cargandoConsulta.value = false;
    }
}

onMounted(async () => {
    await cargarCatalogos();
    await consultarMovimientos();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card space-y-4">
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Consulta de captura operativa por categoría</h1>
                    <p class="text-surface-500 mt-1">
                        Vista de solo lectura para revisar a detalle lo capturado por Contador o Gerente en un rango de fechas contables.
                    </p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <Tag value="Solo lectura" severity="contrast" />
                    <Tag value="Director / Administrador" severity="info" />
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-4 gap-3">
                <div>
                    <label class="block text-sm mb-2">Casino <span class="text-red-500">*</span></label>
                    <Select
                        v-model="filtroSucursalId"
                        :options="sucursales"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Selecciona casino"
                        filter
                        filterPlaceholder="Buscar opción..."
                        :loading="cargandoCatalogos"
                    />
                </div>

                <div>
                    <label class="block text-sm mb-2">Período contable <span class="text-red-500">*</span></label>
                    <div class="flex gap-2">
                        <DatePicker
                            v-model="filtroFechaInicio"
                            dateFormat="yy-mm-dd"
                            :manualInput="false"
                            class="w-full"
                            placeholder="Desde"
                        />
                        <DatePicker
                            v-model="filtroFechaFin"
                            dateFormat="yy-mm-dd"
                            :manualInput="false"
                            class="w-full"
                            placeholder="Hasta"
                        />
                    </div>
                </div>

                <div>
                    <label class="block text-sm mb-2">Categoría operativa</label>
                    <Select
                        v-model="filtroCategoriaId"
                        :options="categorias"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Todas las categorías"
                        filter
                        showClear
                        filterPlaceholder="Buscar categoría..."
                        :loading="cargandoCatalogos"
                    />
                </div>

                <div class="flex items-end">
                    <Button
                        icon="pi pi-search"
                        label="Consultar movimientos"
                        class="w-full"
                        :loading="cargandoConsulta"
                        :disabled="cargandoCatalogos"
                        @click="consultarMovimientos"
                    />
                </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
                <Tag v-if="sucursalSeleccionada" severity="info" :value="`Casino: ${sucursalSeleccionada.nombre}`" />
                <Tag
                    v-if="filtroFechaInicio && filtroFechaFin"
                    severity="contrast"
                    :value="`Período: ${convertirFechaAISO(filtroFechaInicio)} a ${convertirFechaAISO(filtroFechaFin)}`"
                />
                <Tag
                    v-if="categoriaSeleccionada"
                    severity="secondary"
                    :value="`Categoría filtrada: ${categoriaSeleccionada.nombre}`"
                />
                <Tag
                    v-if="movimientos.length > 0"
                    severity="success"
                    :value="`${movimientos.length} movimientos encontrados`"
                />
            </div>
        </div>

        <Message v-if="mensaje" severity="warn" :closable="false">{{ mensaje }}</Message>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="card space-y-1">
                <small class="text-surface-500">Total movimientos</small>
                <p class="text-2xl font-semibold">{{ totalMovimientos }}</p>
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Ingresos totales</small>
                <p class="font-semibold text-lg text-gray-900">$ {{ formatearMonto(totalIngresos) }}</p>
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Egresos totales</small>
                <p class="font-semibold text-lg text-red-600">$ {{ formatearMonto(totalEgresos) }}</p>
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Neto total</small>
                <p class="font-semibold text-lg" :class="totalNeto >= 0 ? 'text-blue-600' : 'text-red-600'">$ {{ formatearMonto(totalNeto) }}</p>
            </div>
        </div>

        <!-- Tarjetas de saldo acumulado (solo cuando hay categoría con saldo inicial) -->
        <div v-if="categoriaUsaSaldoInicial && saldoInicialCategoria" class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div class="card space-y-1 border-l-4 border-blue-400">
                <small class="text-surface-500">Saldo inicial del mes</small>
                <p class="font-semibold text-lg text-blue-600">$ {{ formatearMonto(saldoInicialMes) }}</p>
                <small class="text-xs text-surface-400">{{ saldoInicialCategoria?.categoria_nombre }} — inicio del mes</small>
            </div>
            <div class="card space-y-1 border-l-4 border-emerald-400">
                <small class="text-surface-500">Ingresos acumulados del mes</small>
                <p class="font-semibold text-lg text-gray-900">$ {{ formatearMonto(saldoInicialCategoria?.ingresos_acumulados_mes) }}</p>
            </div>
            <div class="card space-y-1 border-l-4 border-violet-400">
                <small class="text-surface-500">Saldo acumulado al día</small>
                <p class="font-semibold text-xl" :class="saldoFinalAcumulado >= 0 ? 'text-blue-700' : 'text-red-600'">$ {{ formatearMonto(saldoFinalAcumulado) }}</p>
                <small class="text-xs text-surface-400">Saldo inicial + acumulado mes hasta {{ saldoInicialCategoria?.fecha_contable_consulta }}</small>
            </div>
        </div>

        <div class="card">
            <DataTable
                :value="movimientos"
                :loading="cargandoConsulta"
                dataKey="id"
                size="small"
                stripedRows
                showGridlines
                responsiveLayout="scroll"
                :rowClass="claseFilaMovimiento"
            >
                <Column field="selloTiempoTexto" header="Capturado" style="min-width: 11rem" />

                <Column field="concepto_nombre" header="Concepto" style="min-width: 14rem">
                    <template #body="slotProps">
                        <div class="font-semibold">{{ slotProps.data.concepto_nombre || 'Sin concepto' }}</div>
                    </template>
                </Column>

                <Column field="categoria_nombre" header="Categoría" style="min-width: 12rem" />

                <Column field="tipoNormalizado" header="Tipo" style="min-width: 8rem">
                    <template #body="slotProps">
                        <Tag
                            :severity="slotProps.data.tipoNormalizado === 'INGRESO' ? 'success' : slotProps.data.tipoNormalizado === 'EGRESO' ? 'danger' : 'secondary'"
                            :value="slotProps.data.tipoNormalizado || 'N/D'"
                        />
                    </template>
                </Column>

                <Column field="montoNumerico" header="Monto" style="min-width: 10rem">
                    <template #body="slotProps">
                        <MontoMonedaColoreado :monto="slotProps.data.montoNumerico" />
                    </template>
                </Column>

                <Column field="monto_divisa" header="Monto divisa" style="min-width: 11rem">
                    <template #body="slotProps">
                        <span v-if="Number(slotProps.data.monto_divisa || 0) > 0">
                            {{ Number(slotProps.data.monto_divisa || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                            {{ String(slotProps.data.tipo_divisa || '').trim().toUpperCase() || '' }}
                        </span>
                        <span v-else class="text-surface-500">-</span>
                    </template>
                </Column>

                <Column field="medio_liquidez" header="Liquidez" style="min-width: 10rem">
                    <template #body="slotProps">
                        <span>{{ slotProps.data.medio_liquidez || 'N/D' }}</span>
                    </template>
                </Column>

                <Column field="detallesTexto" header="Detalle parametrizado" style="min-width: 20rem">
                    <template #body="slotProps">
                        <span>{{ slotProps.data.detallesTexto }}</span>
                    </template>
                </Column>

                <Column field="notas" header="Notas" style="min-width: 14rem">
                    <template #body="slotProps">
                        <span>{{ slotProps.data.notas || '-' }}</span>
                    </template>
                </Column>

                <Column header="Evidencia" style="min-width: 10rem">
                    <template #body="slotProps">
                        <a
                            v-if="slotProps.data.archivo_respaldo_url"
                            :href="slotProps.data.archivo_respaldo_url"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-primary-600 font-medium underline"
                        >
                            Abrir archivo
                        </a>
                        <span v-else class="text-surface-500">Sin archivo</span>
                    </template>
                </Column>

                <template #empty>
                    <div class="py-5 text-center text-surface-500">
                        No hay movimientos para los filtros seleccionados.
                    </div>
                </template>
            </DataTable>
        </div>
    </section>
</template>
