<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    crearSucursalDirector,
    listarFondosFijosDirector,
    listarSucursalesDirector
} from '@/service/cabinaArquitecturaServicio';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';

const cargando = ref(false);
const guardando = ref(false);
const sucursales = ref([]);
const catalogoFondos = ref([]);
const fondosCaptura = ref([]);

const pasoActual = ref(1);
const mensaje = ref('');
const severidadMensaje = ref('info');

const pasosAsistente = [
    { numero: 1, titulo: 'Datos de sucursal', icono: 'pi pi-building' },
    { numero: 2, titulo: 'Fondos fijos', icono: 'pi pi-wallet' },
    { numero: 3, titulo: 'Vista previa', icono: 'pi pi-eye' }
];

const formulario = reactive({
    nombre: '',
    clave: '',
    direccion: '',
    ciudad: '',
    estado_republica: '',
    telefono: '',
    correo: '',
    encargado: ''
});

const totalFondosAsignados = computed(() => {
    return fondosCaptura.value.reduce((acumulado, item) => acumulado + Number(item.monto_asignado || 0), 0);
});

const columnasFondosCompletas = computed(() => fondosCaptura.value.every((item) => item.monto_asignado !== null && item.monto_asignado !== undefined));

const limpiarMontoEnFoco = (item) => {
    const valorActual = Number(item.monto_asignado || 0);
    if (Number.isFinite(valorActual) && valorActual === 0) {
        item.monto_asignado = null;
    }
};

const reiniciarFormulario = () => {
    formulario.nombre = '';
    formulario.clave = '';
    formulario.direccion = '';
    formulario.ciudad = '';
    formulario.estado_republica = '';
    formulario.telefono = '';
    formulario.correo = '';
    formulario.encargado = '';
};

const reiniciarAsistente = () => {
    reiniciarFormulario();
    fondosCaptura.value = catalogoFondos.value.map((fondo) => ({
        fondo_fijo: fondo.id,
        nombre: fondo.nombre,
        monto_asignado: 0
    }));
    pasoActual.value = 1;
    mensaje.value = '';
    severidadMensaje.value = 'info';
};

const validarPasoUno = () => {
    if (!formulario.nombre.trim()) {
        mensaje.value = 'Debes capturar el nombre de la sucursal.';
        severidadMensaje.value = 'error';
        return false;
    }
    if (!formulario.clave.trim()) {
        mensaje.value = 'Debes capturar la clave interna de la sucursal.';
        severidadMensaje.value = 'error';
        return false;
    }
    mensaje.value = '';
    return true;
};

const validarPasoDos = () => {
    if (!columnasFondosCompletas.value) {
        mensaje.value = 'Debes capturar un monto para cada fondo fijo. Puedes usar 0.00 si no aplica.';
        severidadMensaje.value = 'error';
        return false;
    }
    mensaje.value = '';
    return true;
};

const avanzarPaso = () => {
    if (pasoActual.value === 1 && !validarPasoUno()) {
        return;
    }

    if (pasoActual.value === 2 && !validarPasoDos()) {
        return;
    }

    pasoActual.value = Math.min(3, pasoActual.value + 1);
};

const retrocederPaso = () => {
    pasoActual.value = Math.max(1, pasoActual.value - 1);
    mensaje.value = '';
};

const cargarSucursales = async () => {
    const { data } = await listarSucursalesDirector();
    sucursales.value = data.data || [];
};

const cargarCatalogoFondos = async () => {
    const { data } = await listarFondosFijosDirector();
    catalogoFondos.value = data.data || [];
};

const finalizarAltaSucursal = async () => {
    if (!validarPasoUno() || !validarPasoDos()) {
        return;
    }

    guardando.value = true;
    try {
        const payload = {
            ...formulario,
            fondos_asignados: fondosCaptura.value.map((item) => ({
                fondo_fijo: item.fondo_fijo,
                monto_asignado: Number(item.monto_asignado || 0)
            }))
        };

        await crearSucursalDirector(payload);
        await cargarSucursales();
        reiniciarAsistente();
        severidadMensaje.value = 'success';
        mensaje.value = 'Sucursal creada correctamente con fondos fijos asignados.';
    } finally {
        guardando.value = false;
    }
};

onMounted(async () => {
    cargando.value = true;
    try {
        await Promise.all([cargarSucursales(), cargarCatalogoFondos()]);
        reiniciarAsistente();
    } finally {
        cargando.value = false;
    }
});
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-5">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Cabina Director: Alta de Sucursales</h1>
                    <p class="text-sm text-surface-500 mt-1">Crea una sucursal en tres pasos: datos generales, montos de fondos fijos y confirmación final.</p>
                </div>
                <Button label="Nueva captura" icon="pi pi-refresh" severity="secondary" @click="reiniciarAsistente" />
            </div>

            <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
                <button
                    v-for="paso in pasosAsistente"
                    :key="paso.numero"
                    type="button"
                    class="rounded-xl border p-3 text-left transition-all"
                    :class="pasoActual >= paso.numero
                        ? 'border-primary bg-primary-50 dark:bg-primary-900/20'
                        : 'border-surface-200 bg-surface-0'"
                    @click="paso.numero <= pasoActual ? (pasoActual = paso.numero) : null"
                >
                    <div class="flex items-center gap-2">
                        <i :class="[paso.icono, pasoActual >= paso.numero ? 'text-primary' : 'text-surface-500']" />
                        <span class="text-xs uppercase tracking-wide text-surface-500">Paso {{ paso.numero }}</span>
                    </div>
                    <p class="mt-1 font-medium">{{ paso.titulo }}</p>
                </button>
            </div>

            <Message v-if="mensaje" :severity="severidadMensaje" :closable="false">{{ mensaje }}</Message>

            <div v-if="pasoActual === 1" class="space-y-4">
                <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-building mr-1 text-primary" />
                            Nombre de sucursal <span class="text-red-500">*</span>
                            <small class="text-surface-500 ml-1">(obligatorio)</small>
                        </label>
                        <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. Sala Morelia Centro" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-hashtag mr-1 text-primary" />
                            Clave interna <span class="text-red-500">*</span>
                            <small class="text-surface-500 ml-1">(obligatorio)</small>
                        </label>
                        <InputText v-model="formulario.clave" class="w-full" placeholder="Ej. MOR-01" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-map-marker mr-1 text-primary" />
                            Ciudad <small class="text-surface-500">(opcional)</small>
                        </label>
                        <InputText v-model="formulario.ciudad" class="w-full" placeholder="Ej. Morelia" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-globe mr-1 text-primary" />
                            Estado <small class="text-surface-500">(opcional)</small>
                        </label>
                        <InputText v-model="formulario.estado_republica" class="w-full" placeholder="Ej. Michoacan" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-phone mr-1 text-primary" />
                            Teléfono <small class="text-surface-500">(opcional)</small>
                        </label>
                        <InputText v-model="formulario.telefono" class="w-full" placeholder="Ej. 4431234567" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-envelope mr-1 text-primary" />
                            Correo sucursal <small class="text-surface-500">(opcional)</small>
                        </label>
                        <InputText v-model="formulario.correo" class="w-full" placeholder="sucursal@empresa.com" />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">
                            <i class="pi pi-user mr-1 text-primary" />
                            Encargado <small class="text-surface-500">(opcional)</small>
                        </label>
                        <InputText v-model="formulario.encargado" class="w-full" placeholder="Nombre del responsable" />
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm mb-2">
                            <i class="pi pi-map mr-1 text-primary" />
                            Dirección <small class="text-surface-500">(opcional)</small>
                        </label>
                        <Textarea v-model="formulario.direccion" class="w-full" rows="3" placeholder="Calle, colonia, CP y referencias" />
                    </div>
                </div>
            </div>

            <div v-if="pasoActual === 2" class="space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h2 class="text-lg font-semibold">Asignación automática de fondos fijos</h2>
                        <p class="text-sm text-surface-500">Todos los fondos del catálogo se asignan a la sucursal; captura sus montos iniciales.</p>
                    </div>
                    <Tag :value="`${fondosCaptura.length} fondos`" severity="contrast" />
                </div>

                <DataTable :value="fondosCaptura" responsiveLayout="scroll" dataKey="fondo_fijo">
                    <Column field="nombre" header="Fondo fijo" />
                    <Column header="Monto asignado">
                        <template #body="slotProps">
                            <div class="space-y-2">
                                <InputNumber
                                    v-model="slotProps.data.monto_asignado"
                                    class="w-full"
                                    mode="decimal"
                                    :minFractionDigits="2"
                                    :maxFractionDigits="2"
                                    :useGrouping="true"
                                    placeholder="0.00"
                                    @focus="limpiarMontoEnFoco(slotProps.data)"
                                />
                                <MontoMonedaColoreado :monto="slotProps.data.monto_asignado || 0" />
                            </div>
                        </template>
                    </Column>
                </DataTable>

                <div class="rounded-lg border border-surface-200 p-3">
                    <small class="text-surface-500 block mb-1">Total fondos asignados</small>
                    <MontoMonedaColoreado :monto="totalFondosAsignados" />
                </div>
            </div>

            <div v-if="pasoActual === 3" class="space-y-5">
                <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div class="rounded-lg border border-surface-200 p-4 space-y-2">
                        <h3 class="font-semibold">Resumen sucursal</h3>
                        <p><strong>Nombre:</strong> {{ formulario.nombre }}</p>
                        <p><strong>Clave:</strong> {{ formulario.clave }}</p>
                        <p><strong>Ciudad:</strong> {{ formulario.ciudad || 'Sin dato' }}</p>
                        <p><strong>Estado:</strong> {{ formulario.estado_republica || 'Sin dato' }}</p>
                        <p><strong>Encargado:</strong> {{ formulario.encargado || 'Sin dato' }}</p>
                    </div>
                    <div class="rounded-lg border border-surface-200 p-4 space-y-2">
                        <h3 class="font-semibold">Resumen financiero</h3>
                        <div>
                            <small class="text-surface-500 block">Total fondos fijos</small>
                            <MontoMonedaColoreado :monto="totalFondosAsignados" />
                        </div>
                    </div>
                </div>

                <DataTable :value="fondosCaptura" responsiveLayout="scroll" size="small" dataKey="fondo_fijo">
                    <Column field="nombre" header="Fondo fijo" />
                    <Column header="Monto">
                        <template #body="slotProps">
                            <MontoMonedaColoreado :monto="slotProps.data.monto_asignado || 0" />
                        </template>
                    </Column>
                </DataTable>
            </div>

            <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
                <Button label="Anterior" icon="pi pi-arrow-left" severity="secondary" :disabled="pasoActual === 1 || guardando" @click="retrocederPaso" />
                <Button v-if="pasoActual < 3" label="Siguiente" icon="pi pi-arrow-right" iconPos="right" :disabled="guardando" @click="avanzarPaso" />
                <Button v-else label="Finalizar alta" icon="pi pi-check" :loading="guardando" @click="finalizarAltaSucursal" />
            </div>
        </div>

        <div class="card space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold">Sucursales registradas</h2>
                <Tag :value="`${sucursales.length} registradas`" severity="info" />
            </div>

            <DataTable
                :value="sucursales"
                :loading="cargando"
                paginator
                :rows="10"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column field="clave" header="Clave" sortable />
                <Column field="nombre" header="Sucursal" sortable />
                <Column field="ciudad" header="Ciudad" sortable />
                <Column field="encargado" header="Encargado" sortable />
                <Column header="Fondos asignados">
                    <template #body="slotProps">
                        {{ Array.isArray(slotProps.data.fondos_asignados_detalle) ? slotProps.data.fondos_asignados_detalle.length : 0 }}
                    </template>
                </Column>
            </DataTable>
        </div>
    </section>
</template>
