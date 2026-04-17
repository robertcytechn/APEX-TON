<script setup>
import { computed, onMounted, ref } from 'vue';
import {
    actualizarConfiguracionGlobalDirector,
    listarConfiguracionesGlobalesDirector
} from '@/service/cabinaArquitecturaServicio';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';

const cargando = ref(false);
const guardando = ref(false);
const registros = ref([]);
const filasPorPagina = ref(10);

const mostrarDialogo = ref(false);
const configuracionSeleccionada = ref(null);

const valorTexto = ref('');
const valorEntero = ref(null);
const valorDecimal = ref(null);
const valorBooleano = ref('true');
const valorFecha = ref(null);
const valorHora = ref(null);
const valorFechaHora = ref(null);
const valorJson = ref('');

const mensaje = ref('');
const severidadMensaje = ref('info');

const patronesClaveMonetaria = ['MONTO', 'IMPORTE', 'FONDO', 'SALDO', 'TOTAL', 'INGRESO', 'EGRESO', 'COSTO', 'PRECIO'];

const esClaveMonetaria = (clave) => {
    const texto = String(clave || '').toUpperCase();
    return patronesClaveMonetaria.some((patron) => texto.includes(patron));
};

const puedeEditarVariable = (registro) => registro?.visible_para_director !== false;

const opcionesFilas = computed(() => {
    const total = registros.value.length;
    const opciones = [
        { label: '10', value: 10 },
        { label: '20', value: 20 },
        { label: '50', value: 50 }
    ];
    if (total > 0 && !opciones.some((opcion) => opcion.value === total)) {
        opciones.push({ label: 'Todos', value: total });
    }
    return opciones;
});

const tipoActual = computed(() => configuracionSeleccionada.value?.tipo_valor || 'STRING');

const formatearDos = (numero) => String(numero).padStart(2, '0');

const aFecha = (valor) => {
    if (!valor) {
        return null;
    }
    const fecha = new Date(valor);
    return Number.isNaN(fecha.getTime()) ? null : fecha;
};

const aHora = (valor) => {
    if (!valor || typeof valor !== 'string') {
        return null;
    }
    const partes = valor.split(':');
    if (partes.length < 2) {
        return null;
    }
    const fecha = new Date();
    fecha.setHours(Number(partes[0]) || 0, Number(partes[1]) || 0, Number(partes[2]) || 0, 0);
    return fecha;
};

const aIsoFecha = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${fecha.getFullYear()}-${formatearDos(fecha.getMonth() + 1)}-${formatearDos(fecha.getDate())}`;
};

const aIsoHora = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${formatearDos(fecha.getHours())}:${formatearDos(fecha.getMinutes())}:${formatearDos(fecha.getSeconds())}`;
};

const aIsoFechaHora = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${aIsoFecha(fecha)}T${aIsoHora(fecha)}`;
};

const cargar = async () => {
    cargando.value = true;
    try {
        const { data } = await listarConfiguracionesGlobalesDirector();
        registros.value = data.data || [];
    } finally {
        cargando.value = false;
    }
};

const abrirDialogo = (registro) => {
    configuracionSeleccionada.value = registro;

    valorTexto.value = registro.valor || '';
    valorEntero.value = registro.valor === '' || registro.valor === null ? null : Number.parseInt(registro.valor, 10);
    valorDecimal.value = registro.valor === '' || registro.valor === null ? null : Number.parseFloat(registro.valor);
    valorBooleano.value = String(registro.valor).toLowerCase() === 'false' ? 'false' : 'true';
    valorFecha.value = aFecha(registro.valor);
    valorHora.value = aHora(registro.valor);
    valorFechaHora.value = aFecha(registro.valor);
    valorJson.value = registro.valor || '';

    mostrarDialogo.value = true;
};

const construirValor = () => {
    if (tipoActual.value === 'INT') {
        return valorEntero.value === null || valorEntero.value === undefined ? '' : String(valorEntero.value);
    }
    if (tipoActual.value === 'FLOAT') {
        return valorDecimal.value === null || valorDecimal.value === undefined ? '' : String(valorDecimal.value);
    }
    if (tipoActual.value === 'BOOLEAN') {
        return valorBooleano.value;
    }
    if (tipoActual.value === 'DATE') {
        return aIsoFecha(valorFecha.value);
    }
    if (tipoActual.value === 'TIME') {
        return aIsoHora(valorHora.value);
    }
    if (tipoActual.value === 'DATETIME') {
        return aIsoFechaHora(valorFechaHora.value);
    }
    if (tipoActual.value === 'JSON') {
        return valorJson.value;
    }
    return valorTexto.value;
};

const guardar = async () => {
    if (!configuracionSeleccionada.value) {
        return;
    }

    if (!puedeEditarVariable(configuracionSeleccionada.value)) {
        severidadMensaje.value = 'error';
        mensaje.value = 'Esta variable global no está habilitada para edición por director.';
        return;
    }

    guardando.value = true;
    try {
        const payload = { valor: construirValor() };
        await actualizarConfiguracionGlobalDirector(configuracionSeleccionada.value.id, payload);

        severidadMensaje.value = 'success';
        mensaje.value = `Valor actualizado para la variable ${configuracionSeleccionada.value.clave}.`;

        mostrarDialogo.value = false;
        configuracionSeleccionada.value = null;
        await cargar();
    } finally {
        guardando.value = false;
    }
};

onMounted(cargar);
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-4">
            <div>
                <h1 class="text-2xl font-semibold">Cabina Director: Configuraciones Globales</h1>
                <p class="text-sm text-surface-500 mt-1">En esta sección solo puedes modificar el valor de variables habilitadas por administrador. Clave y tipo están bloqueados.</p>
            </div>

            <Message v-if="mensaje" :severity="severidadMensaje" :closable="false">{{ mensaje }}</Message>
            <Message v-if="!cargando && registros.length === 0" severity="info" :closable="false">
                No hay variables globales habilitadas para director en este momento.
            </Message>

            <DataTable
                :value="registros"
                :loading="cargando"
                paginator
                :rows="filasPorPagina"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <template #paginatorstart>
                    <Select v-model="filasPorPagina" :options="opcionesFilas" optionLabel="label" optionValue="value" class="w-32" />
                </template>

                <Column field="clave" header="Clave" sortable />
                <Column field="tipo_valor" header="Tipo" sortable />
                <Column header="Valor" sortable sortField="valor">
                    <template #body="slotProps">
                        <MontoMonedaColoreado
                            v-if="slotProps.data.tipo_valor === 'FLOAT' && esClaveMonetaria(slotProps.data.clave)"
                            :monto="slotProps.data.valor"
                        />
                        <span v-else>{{ slotProps.data.valor }}</span>
                    </template>
                </Column>
                <Column field="visible_para_director" header="Habilitada" sortable>
                    <template #body="slotProps">
                        <Tag
                            :value="puedeEditarVariable(slotProps.data) ? 'Si' : 'No'"
                            :severity="puedeEditarVariable(slotProps.data) ? 'success' : 'danger'"
                        />
                    </template>
                </Column>
                <Column field="descripcion" header="Descripción" />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <Button
                            size="small"
                            icon="pi pi-pencil"
                            label="Editar valor"
                            :disabled="!puedeEditarVariable(slotProps.data)"
                            @click="abrirDialogo(slotProps.data)"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialogo" modal header="Editar valor de configuración" :style="{ width: '44rem' }">
            <div v-if="configuracionSeleccionada" class="space-y-4">
                <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <label class="block text-sm mb-2">Clave de variable</label>
                        <InputText :modelValue="configuracionSeleccionada.clave" class="w-full" readonly />
                    </div>
                    <div>
                        <label class="block text-sm mb-2">Tipo de valor</label>
                        <InputText :modelValue="configuracionSeleccionada.tipo_valor" class="w-full" readonly />
                    </div>
                </div>

                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-pencil mr-1 text-primary" />
                        Nuevo valor <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>

                    <InputText v-if="tipoActual === 'STRING'" v-model="valorTexto" class="w-full" placeholder="Captura valor" />
                    <InputNumber v-else-if="tipoActual === 'INT'" v-model="valorEntero" class="w-full" :minFractionDigits="0" :maxFractionDigits="0" :useGrouping="false" placeholder="0" />
                    <InputNumber
                        v-else-if="tipoActual === 'FLOAT'"
                        v-model="valorDecimal"
                        class="w-full"
                        :minFractionDigits="esClaveMonetaria(configuracionSeleccionada.clave) ? 2 : 0"
                        :maxFractionDigits="esClaveMonetaria(configuracionSeleccionada.clave) ? 2 : 6"
                        :useGrouping="true"
                        placeholder="0.00"
                    />
                    <Select
                        v-else-if="tipoActual === 'BOOLEAN'"
                        v-model="valorBooleano"
                        :options="[
                            { label: 'Verdadero', value: 'true' },
                            { label: 'Falso', value: 'false' }
                        ]"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        filter
                        filterPlaceholder="Buscar opción..."
                    />
                    <DatePicker v-else-if="tipoActual === 'DATE'" v-model="valorFecha" class="w-full" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DD" />
                    <DatePicker v-else-if="tipoActual === 'TIME'" v-model="valorHora" class="w-full" timeOnly hourFormat="24" showIcon placeholder="HH:MM:SS" />
                    <DatePicker v-else-if="tipoActual === 'DATETIME'" v-model="valorFechaHora" class="w-full" showTime hourFormat="24" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DDTHH:MM:SS" />
                    <Textarea v-else v-model="valorJson" rows="4" class="w-full font-mono" placeholder='{"clave": "valor"}' />

                    <div v-if="tipoActual === 'FLOAT' && esClaveMonetaria(configuracionSeleccionada.clave)" class="mt-2">
                        <small class="block text-surface-500 mb-1">Vista previa monetaria coloreada</small>
                        <MontoMonedaColoreado :monto="Number(valorDecimal || 0)" />
                    </div>
                </div>

                <div class="rounded-lg border border-surface-200 p-3">
                    <small class="text-surface-500 block mb-1">Descripción (solo lectura)</small>
                    <p class="text-sm">{{ configuracionSeleccionada.descripcion || 'Sin descripción' }}</p>
                </div>
            </div>

            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar valor" icon="pi pi-check" @click="guardar" />
            </div>
        </Dialog>
    </section>
</template>
