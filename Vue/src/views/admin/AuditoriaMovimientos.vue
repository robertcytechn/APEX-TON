<script setup>
import { obtenerHistorialAuditoriaMovimientos } from '@/service/capturaOperativaServicio';
import { listarSucursalesReporte } from '@/service/estadoResultadosServicio';
import { listarCategoriasOperativas } from '@/service/capturaOperativaServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, reactive, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const mensajeError = ref('');
const mensajeExito = ref('');
const historial = ref([]);
const sucursales = ref([]);
const categorias = ref([]);
const usuariosUnicos = ref([]);

const paginacion = reactive({
    page: 1,
    page_size: 50,
    total_registros: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
});

const filtros = reactive({
    usuario_id: null,
    sucursal_id: null,
    categoria_id: null,
    concepto_id: null,
    fecha_contable: null,
    fecha_desde: null,
    fecha_hasta: null,
    tipo_cambio: null
});

const registrosExpandidos = ref(new Set());

const puedeVerAuditoria = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));

const opcionesTipoCambio = [
    { label: 'Creación', value: '+' },
    { label: 'Modificación', value: '~' },
    { label: 'Eliminación', value: '-' }
];

const colorTipoCambio = {
    '+': 'bg-emerald-100 text-emerald-800 border-emerald-200',
    '~': 'bg-amber-100 text-amber-800 border-amber-200',
    '-': 'bg-red-100 text-red-800 border-red-200'
};

const etiquetaTipoCambio = {
    '+': 'Creación',
    '~': 'Modificación',
    '-': 'Eliminación'
};

const iconoTipoCambio = {
    '+': 'pi pi-plus-circle',
    '~': 'pi pi-pencil',
    '-': 'pi pi-trash'
};

function formatearMonto(valor) {
    if (valor === null || valor === undefined) return '-';
    const num = Number(valor);
    if (Number.isNaN(num)) return '-';
    return num.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatearFecha(fechaStr) {
    if (!fechaStr) return '-';
    const fecha = new Date(fechaStr);
    if (Number.isNaN(fecha.getTime())) return fechaStr;
    return fecha.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function formatearFechaHora(fechaStr) {
    if (!fechaStr) return '-';
    const fecha = new Date(fechaStr);
    if (Number.isNaN(fecha.getTime())) return fechaStr;
    return fecha.toLocaleString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function toggleExpandirRegistro(historyId) {
    if (registrosExpandidos.value.has(historyId)) {
        registrosExpandidos.value.delete(historyId);
    } else {
        registrosExpandidos.value.add(historyId);
    }
}

function estaExpandido(historyId) {
    return registrosExpandidos.value.has(historyId);
}

async function cargarCatalogos() {
    try {
        const [respSucursales, respCategorias] = await Promise.all([
            listarSucursalesReporte(),
            listarCategoriasOperativas()
        ]);
        sucursales.value = (respSucursales.data?.data || [])
            .filter(s => s.estado === 'ACTIVO')
            .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es-MX'));
        categorias.value = (respCategorias.data?.data || [])
            .sort((a, b) => a.orden - b.orden || a.nombre.localeCompare(b.nombre, 'es-MX'));
    } catch (error) {
        console.error('Error cargando catálogos:', error);
    }
}

async function consultarHistorial(nuevaPagina = 1) {
    if (!puedeVerAuditoria.value) {
        mensajeError.value = 'No tienes permisos para acceder a la auditoría de movimientos.';
        return;
    }

    mensajeError.value = '';
    mensajeExito.value = '';
    cargando.value = true;
    historial.value = [];

    try {
        const params = {
            page: nuevaPagina,
            page_size: paginacion.page_size,
            ...Object.fromEntries(
                Object.entries(filtros).filter(([, v]) => v !== null && v !== '' && v !== undefined)
            )
        };

        const { data } = await obtenerHistorialAuditoriaMovimientos(params);
        const respuesta = data?.data;

        if (respuesta) {
            historial.value = respuesta.resultados || [];
            Object.assign(paginacion, respuesta.paginacion || {});

            // Extraer usuarios únicos para el filtro
            const usuariosMap = new Map();
            historial.value.forEach(reg => {
                if (reg.usuario_id && !usuariosMap.has(reg.usuario_id)) {
                    usuariosMap.set(reg.usuario_id, {
                        id: reg.usuario_id,
                        nombre: reg.usuario_nombre,
                        email: reg.usuario_email
                    });
                }
            });
            usuariosUnicos.value = Array.from(usuariosMap.values()).sort((a, b) => a.nombre.localeCompare(b.nombre));
        }
    } catch (error) {
        historial.value = [];
        mensajeError.value = error?.response?.data?.message || 'No se pudo cargar el historial de auditoría.';
    } finally {
        cargando.value = false;
    }
}

function cambiarPagina(nuevaPagina) {
    if (nuevaPagina >= 1 && nuevaPagina <= paginacion.total_pages) {
        consultarHistorial(nuevaPagina);
    }
}

function limpiarFiltros() {
    Object.keys(filtros).forEach(key => {
        filtros[key] = null;
    });
    paginacion.page = 1;
    consultarHistorial(1);
}

onMounted(async () => {
    if (puedeVerAuditoria.value) {
        await cargarCatalogos();
        await consultarHistorial();
    }
});
</script>

<template>
    <section class="space-y-4">
        <Message v-if="!puedeVerAuditoria" severity="error" :closable="false">
            No tienes permisos para acceder a este módulo. Solo Administradores y Directores pueden consultar la auditoría.
        </Message>

        <template v-else>
            <div class="card space-y-4">
                <div>
                    <h1 class="text-2xl font-semibold">Auditoría de Movimientos</h1>
                    <p class="text-surface-500 mt-1">
                        Historial de cambios con trazabilidad completa: quién modificó qué, cuándo y cuál fue el valor anterior.
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-building mr-1 text-primary"></i>Casino
                        </label>
                        <Select
                            v-model="filtros.sucursal_id"
                            :options="sucursales"
                            optionLabel="nombre"
                            optionValue="id"
                            class="w-full"
                            placeholder="Todas las sucursales"
                            filter
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-folder mr-1 text-primary"></i>Categoría Operativa
                        </label>
                        <Select
                            v-model="filtros.categoria_id"
                            :options="categorias"
                            optionLabel="nombre"
                            optionValue="id"
                            class="w-full"
                            placeholder="Todas las categorías"
                            filter
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-user mr-1 text-primary"></i>Usuario
                        </label>
                        <Select
                            v-model="filtros.usuario_id"
                            :options="usuariosUnicos"
                            optionLabel="nombre"
                            optionValue="id"
                            class="w-full"
                            placeholder="Todos los usuarios"
                            filter
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-tag mr-1 text-primary"></i>Tipo de Cambio
                        </label>
                        <Select
                            v-model="filtros.tipo_cambio"
                            :options="opcionesTipoCambio"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Todos los tipos"
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-calendar mr-1 text-primary"></i>Fecha Contable Específica
                        </label>
                        <DatePicker
                            v-model="filtros.fecha_contable"
                            dateFormat="yy-mm-dd"
                            class="w-full"
                            placeholder="YYYY-MM-DD"
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-calendar-clock mr-1 text-primary"></i>Fecha Desde
                        </label>
                        <DatePicker
                            v-model="filtros.fecha_desde"
                            dateFormat="yy-mm-dd"
                            class="w-full"
                            placeholder="YYYY-MM-DD"
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-calendar-clock mr-1 text-primary"></i>Fecha Hasta
                        </label>
                        <DatePicker
                            v-model="filtros.fecha_hasta"
                            dateFormat="yy-mm-dd"
                            class="w-full"
                            placeholder="YYYY-MM-DD"
                        />
                    </div>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                    <Button
                        icon="pi pi-search"
                        label="Consultar historial"
                        :loading="cargando"
                        @click="consultarHistorial(1)"
                    />
                    <Button
                        icon="pi pi-refresh"
                        label="Limpiar filtros"
                        severity="secondary"
                        outlined
                        @click="limpiarFiltros"
                    />
                </div>
            </div>

            <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>
            <Message v-if="mensajeExito" severity="success" :closable="false">{{ mensajeExito }}</Message>

            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold">Resultados</h2>
                    <div class="text-sm text-surface-500">
                        Mostrando {{ historial.length }} de {{ paginacion.total_registros }} registros
                    </div>
                </div>

                <DataTable
                    :value="historial"
                    :loading="cargando"
                    responsiveLayout="scroll"
                    class="text-sm"
                >
                    <Column field="history_date" header="Fecha/Hora" style="min-width: 10rem">
                        <template #body="slotProps">
                            <div class="font-medium">{{ formatearFechaHora(slotProps.data.history_date) }}</div>
                            <div class="text-xs text-surface-500">ID Hist: {{ slotProps.data.history_id }}</div>
                        </template>
                    </Column>

                    <Column field="history_type" header="Tipo" style="min-width: 7rem">
                        <template #body="slotProps">
                            <Tag
                                :value="etiquetaTipoCambio[slotProps.data.history_type]"
                                :icon="iconoTipoCambio[slotProps.data.history_type]"
                                :class="colorTipoCambio[slotProps.data.history_type]"
                                class="border"
                            />
                        </template>
                    </Column>

                    <Column field="sucursal_nombre" header="Casino" style="min-width: 10rem" />

                    <Column field="categoria_nombre" header="Categoría" style="min-width: 8rem">
                        <template #body="slotProps">
                            <Tag
                                :value="slotProps.data.categoria_nombre || 'N/A'"
                                severity="info"
                                class="text-xs"
                            />
                        </template>
                    </Column>

                    <Column field="concepto_nombre" header="Concepto" style="min-width: 12rem">
                        <template #body="slotProps">
                            <div class="font-medium">{{ slotProps.data.concepto_nombre || 'N/A' }}</div>
                            <div class="text-xs text-surface-500">{{ slotProps.data.concepto_clave }}</div>
                        </template>
                    </Column>

                    <Column field="monto" header="Monto" style="min-width: 8rem">
                        <template #body="slotProps">
                            <div class="font-semibold text-right">
                                $ {{ formatearMonto(slotProps.data.monto) }}
                            </div>
                            <div v-if="slotProps.data.monto_divisa" class="text-xs text-surface-500 text-right">
                                {{ slotProps.data.tipo_divisa }} {{ formatearMonto(slotProps.data.monto_divisa) }}
                            </div>
                        </template>
                    </Column>

                    <Column field="usuario_nombre" header="Usuario" style="min-width: 10rem">
                        <template #body="slotProps">
                            <div class="font-medium">{{ slotProps.data.usuario_nombre }}</div>
                            <div class="text-xs text-surface-500">{{ slotProps.data.usuario_email }}</div>
                        </template>
                    </Column>

                    <Column header="Acciones" style="min-width: 6rem">
                        <template #body="slotProps">
                            <Button
                                :icon="estaExpandido(slotProps.data.history_id) ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
                                text
                                rounded
                                :severity="slotProps.data.diff?.cantidad_cambios > 0 ? 'warn' : 'secondary'"
                                @click="toggleExpandirRegistro(slotProps.data.history_id)"
                                :disabled="slotProps.data.history_type === '+' || slotProps.data.history_type === '-'"
                                v-tooltip="slotProps.data.diff?.cantidad_cambios > 0 ? `${slotProps.data.diff.cantidad_cambios} cambios` : 'Sin cambios detectados'"
                            />
                        </template>
                    </Column>

                    <template #expansion="slotProps">
                        <div v-if="estaExpandido(slotProps.data.history_id)" class="p-3 bg-surface-50 rounded-lg">
                            <div class="mb-3">
                                <h4 class="font-semibold mb-2">Detalles del Movimiento</h4>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                                    <div>
                                        <span class="text-surface-500">Fecha contable:</span>
                                        <span class="font-medium ml-1">{{ formatearFecha(slotProps.data.fecha_contable) }}</span>
                                    </div>
                                    <div>
                                        <span class="text-surface-500">Reporte ID:</span>
                                        <span class="font-medium ml-1">{{ slotProps.data.reporte_id }}</span>
                                    </div>
                                    <div>
                                        <span class="text-surface-500">Movimiento ID:</span>
                                        <span class="font-medium ml-1">{{ slotProps.data.movimiento_id }}</span>
                                    </div>
                                </div>
                            </div>

                            <div v-if="slotProps.data.diff?.tipo === 'modificacion' && slotProps.data.diff?.cambios?.length" class="space-y-2">
                                <h4 class="font-semibold text-amber-700">
                                    <i class="pi pi-pencil mr-1"></i>Cambios Detectados ({{ slotProps.data.diff.cantidad_cambios }})
                                </h4>
                                <div class="space-y-2">
                                    <div
                                        v-for="(cambio, idx) in slotProps.data.diff.cambios"
                                        :key="idx"
                                        class="p-2 rounded border bg-white"
                                    >
                                        <div class="font-medium text-sm mb-1">{{ cambio.etiqueta }}</div>
                                        <div class="grid grid-cols-2 gap-2 text-sm">
                                            <div class="p-2 bg-red-50 rounded">
                                                <div class="text-xs text-red-600 mb-1">Valor Anterior</div>
                                                <div class="font-medium">
                                                    <span v-if="cambio.campo === 'monto' || cambio.campo === 'monto_divisa'">
                                                        $ {{ formatearMonto(cambio.valor_anterior) }}
                                                    </span>
                                                    <span v-else-if="cambio.campo === 'detalles_snapshot'">
                                                        {{ JSON.stringify(cambio.valor_anterior, null, 2) }}
                                                    </span>
                                                    <span v-else>{{ cambio.valor_anterior ?? '(vacío)' }}</span>
                                                </div>
                                            </div>
                                            <div class="p-2 bg-emerald-50 rounded">
                                                <div class="text-xs text-emerald-600 mb-1">Valor Nuevo</div>
                                                <div class="font-medium">
                                                    <span v-if="cambio.campo === 'monto' || cambio.campo === 'monto_divisa'">
                                                        $ {{ formatearMonto(cambio.valor_nuevo) }}
                                                    </span>
                                                    <span v-else-if="cambio.campo === 'detalles_snapshot'">
                                                        {{ JSON.stringify(cambio.valor_nuevo, null, 2) }}
                                                    </span>
                                                    <span v-else>{{ cambio.valor_nuevo ?? '(vacío)' }}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div v-else-if="slotProps.data.history_type === '+'" class="text-emerald-600">
                                <i class="pi pi-info-circle mr-1"></i>Este es un registro de creación. No hay versión anterior para comparar.
                            </div>

                            <div v-else-if="slotProps.data.history_type === '-'" class="text-red-600">
                                <i class="pi pi-info-circle mr-1"></i>Este es un registro de eliminación.
                            </div>

                            <div v-if="slotProps.data.notas" class="mt-3 p-2 bg-blue-50 rounded">
                                <div class="text-xs text-blue-600 mb-1">Notas del movimiento</div>
                                <div class="text-sm">{{ slotProps.data.notas }}</div>
                            </div>

                            <div v-if="slotProps.data.detalles_snapshot && Object.keys(slotProps.data.detalles_snapshot).length" class="mt-3">
                                <div class="text-xs text-surface-500 mb-1">Detalles parametrizados</div>
                                <pre class="text-xs bg-white p-2 rounded border overflow-auto">{{ JSON.stringify(slotProps.data.detalles_snapshot, null, 2) }}</pre>
                            </div>
                        </div>
                    </template>

                    <template #empty>
                        <div class="p-4 text-center text-surface-500">
                            <i class="pi pi-inbox text-4xl mb-2"></i>
                            <p>No hay registros de auditoría para los filtros seleccionados.</p>
                        </div>
                    </template>
                </DataTable>

                <div v-if="paginacion.total_pages > 1" class="flex items-center justify-between mt-4 pt-4 border-t">
                    <div class="text-sm text-surface-500">
                        Página {{ paginacion.page }} de {{ paginacion.total_pages }}
                    </div>
                    <div class="flex items-center gap-2">
                        <Button
                            icon="pi pi-chevron-left"
                            text
                            :disabled="!paginacion.has_prev || cargando"
                            @click="cambiarPagina(paginacion.page - 1)"
                        />
                        <div class="flex items-center gap-1">
                            <Button
                                v-for="pagina in Array.from({length: Math.min(5, paginacion.total_pages)}, (_, i) => {
                                    const start = Math.max(1, Math.min(paginacion.page - 2, paginacion.total_pages - 4));
                                    return start + i;
                                }).filter(p => p <= paginacion.total_pages)"
                                :key="pagina"
                                :label="String(pagina)"
                                :severity="pagina === paginacion.page ? 'primary' : 'secondary'"
                                text
                                @click="cambiarPagina(pagina)"
                            />
                        </div>
                        <Button
                            icon="pi pi-chevron-right"
                            text
                            :disabled="!paginacion.has_next || cargando"
                            @click="cambiarPagina(paginacion.page + 1)"
                        />
                    </div>
                </div>
            </div>
        </template>
    </section>
</template>

<style scoped>
:deep(.p-datatable-tbody > tr.p-datatable-row-expansion > td) {
    padding: 0;
}
</style>
