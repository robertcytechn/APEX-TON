<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { listarCategoriasOperativas, listarMovimientosDiarios } from '@/service/capturaOperativaServicio';
import { listarSucursalesReporte } from '@/service/estadoResultadosServicio';
import { listarReportesDiarios } from '@/service/reporteDiarioServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargandoCatalogos = ref(false);
const cargandoConsulta = ref(false);
const mensaje = ref('');

const sucursales = ref([]);
const categorias = ref([]);
const movimientos = ref([]);
const reporteSeleccionado = ref(null);

const hoy = new Date();
const diaContableBase = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);

const filtroSucursalId = ref(null);
const filtroFecha = ref(new Date(diaContableBase));
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

        if (!(filtroFecha.value instanceof Date) || Number.isNaN(filtroFecha.value.getTime())) {
            filtroFecha.value = new Date(diaContableBase);
        }
    } catch (error) {
        mensaje.value = error?.response?.data?.message || 'No fue posible cargar catálogos para filtros de consulta.';
    } finally {
        cargandoCatalogos.value = false;
    }
}

// 1) Para qué sirve: consultar movimientos capturados en un día y categoría de una sucursal.
// 2) Cómo funciona: resuelve reporte por fecha y luego lista movimientos filtrados.
// 3) Qué hace: arma la tabla detallada de lectura para director/administrador.
// 4) Cómo editarla: agrega paginación o segmentaciones adicionales en params de consulta.
async function consultarMovimientos() {
    mensaje.value = '';
    movimientos.value = [];
    reporteSeleccionado.value = null;

    const fechaIso = convertirFechaAISO(filtroFecha.value);
    if (!filtroSucursalId.value) {
        mensaje.value = 'Selecciona un casino para consultar la captura operativa.';
        return;
    }

    if (!fechaIso) {
        mensaje.value = 'Selecciona una fecha contable válida.';
        return;
    }

    cargandoConsulta.value = true;
    try {
        const { data: respuestaReportes } = await listarReportesDiarios({
            sucursal_id: filtroSucursalId.value,
            fecha_inicio: fechaIso,
            fecha_fin: fechaIso
        });

        const reportes = Array.isArray(respuestaReportes?.data) ? respuestaReportes.data : [];
        const reporteDia = reportes.find((reporte) => String(reporte?.fecha_contable || '') === fechaIso) || null;

        if (!reporteDia) {
            mensaje.value = 'No existe reporte diario para el casino y fecha seleccionados.';
            return;
        }

        reporteSeleccionado.value = reporteDia;

        const parametrosMovimientos = {
            reporte_id: reporteDia.id
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
                        Vista de solo lectura para revisar a detalle lo capturado por Contador o Gerente en un día contable.
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
                    <label class="block text-sm mb-2">Día contable <span class="text-red-500">*</span></label>
                    <DatePicker
                        v-model="filtroFecha"
                        dateFormat="yy-mm-dd"
                        :manualInput="false"
                        class="w-full"
                    />
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
                <Tag v-if="reporteSeleccionado" severity="contrast" :value="`Reporte: ${reporteSeleccionado.fecha_contable}`" />
                <Tag
                    v-if="reporteSeleccionado"
                    :severity="String(reporteSeleccionado.estado_reporte || '').toUpperCase() === 'CERRADO' ? 'danger' : 'success'"
                    :value="`Estado: ${reporteSeleccionado.estado_reporte}`"
                />
                <Tag
                    v-if="categoriaSeleccionada"
                    severity="secondary"
                    :value="`Categoría filtrada: ${categoriaSeleccionada.nombre}`"
                />
            </div>
        </div>

        <Message v-if="mensaje" severity="warn" :closable="false">{{ mensaje }}</Message>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="card space-y-1">
                <small class="text-surface-500">Movimientos</small>
                <p class="text-2xl font-semibold">{{ totalMovimientos }}</p>
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Ingresos</small>
                <MontoMonedaColoreado :monto="totalIngresos" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Egresos</small>
                <MontoMonedaColoreado :monto="totalEgresos" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Neto</small>
                <MontoMonedaColoreado :monto="totalNeto" />
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
