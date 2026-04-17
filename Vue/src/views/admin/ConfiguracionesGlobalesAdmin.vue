<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    crearConfiguracionGlobalAdmin,
    eliminarConfiguracionGlobalAdmin,
    listarConfiguracionesGlobalesAdmin,
    actualizarConfiguracionGlobalAdmin
} from '@/service/cabinaArquitecturaServicio';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';

const tiposValor = [
    { label: 'Texto', value: 'STRING' },
    { label: 'Entero', value: 'INT' },
    { label: 'Decimal', value: 'FLOAT' },
    { label: 'Booleano', value: 'BOOLEAN' },
    { label: 'Fecha', value: 'DATE' },
    { label: 'Hora', value: 'TIME' },
    { label: 'Fecha y Hora', value: 'DATETIME' },
    { label: 'JSON', value: 'JSON' }
];

const cargando = ref(false);
const guardando = ref(false);
const registros = ref([]);
const mostrarDialogo = ref(false);
const editandoId = ref(null);
const columnasDisponibles = [
    { label: 'ID', value: 'id' },
    { label: 'Clave', value: 'clave' },
    { label: 'Valor', value: 'valor' },
    { label: 'Tipo', value: 'tipo_valor' },
    { label: 'Visible Director', value: 'visible_para_director' }
];
const columnasVisibles = ref([...columnasDisponibles]);
const filasPorPagina = ref(10);
const valorEntero = ref(null);
const valorDecimal = ref(null);
const valorBooleano = ref('true');
const valorFecha = ref(null);
const valorHora = ref(null);
const valorFechaHora = ref(null);

const formulario = reactive({
    clave: '',
    valor: '',
    tipo_valor: 'STRING',
    descripcion: '',
    visible_para_director: true
});

const patronesClaveMonetaria = ['MONTO', 'IMPORTE', 'FONDO', 'SALDO', 'TOTAL', 'INGRESO', 'EGRESO', 'COSTO', 'PRECIO'];

// 1) Para qué sirve: identificar claves de configuración con semántica monetaria.
// 2) Cómo funciona: normaliza la clave y busca coincidencias por patrón.
// 3) Qué hace: habilita formato y vista previa de monto en UI.
// 4) Cómo editarla: agrega/remueve patrones al evolucionar nomenclatura de claves.
const esClaveMonetaria = (clave) => {
    const claveNormalizada = String(clave || '').toUpperCase();
    return patronesClaveMonetaria.some((patron) => claveNormalizada.includes(patron));
};

const esConfiguracionMonetaria = computed(() => formulario.tipo_valor === 'FLOAT' && esClaveMonetaria(formulario.clave));

const valorMonetarioVistaPrevia = computed(() => {
    const numero = Number(formulario.valor);
    return Number.isFinite(numero) ? numero : 0;
});

// 1) Para qué sirve: limpiar valor monetario al enfocar el input decimal.
// 2) Cómo funciona: cuando el valor actual es 0 lo pasa a null.
// 3) Qué hace: permite capturar monto directamente sin borrar 0.00 manualmente.
// 4) Cómo editarla: extiéndela si se agregan más inputs monetarios en este módulo.
const limpiarDecimalMonetarioEnFoco = () => {
    if (!esConfiguracionMonetaria.value) {
        return;
    }
    const valorActual = Number(valorDecimal.value);
    if (Number.isFinite(valorActual) && valorActual === 0) {
        valorDecimal.value = null;
    }
};

const opcionesFilasMostrar = computed(() => {
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

// 1) Para qué sirve: controlar visibilidad dinámica de columnas.
// 2) Cómo funciona: verifica si columna existe en columnasVisibles.
// 3) Qué hace: permite personalización del DataTable sin recargar vista.
// 4) Cómo editarla: integra reglas por rol para ocultar columnas sensibles.
const esColumnaVisible = (columna) => columnasVisibles.value.some((item) => item.value === columna);

// 1) Para qué sirve: formatear números a dos dígitos para fechas/horas ISO.
// 2) Cómo funciona: aplica padStart con cero a la izquierda.
// 3) Qué hace: evita formatos inválidos en conversiones de fecha/hora.
// 4) Cómo editarla: ajusta longitud si se usa otro formato temporal.
const formatearDos = (numero) => String(numero).padStart(2, '0');

// 1) Para qué sirve: convertir valor serializado en Date utilizable para picker.
// 2) Cómo funciona: construye Date y valida que sea fecha válida.
// 3) Qué hace: sincroniza valor backend con componente visual.
// 4) Cómo editarla: incorpora parser custom si backend cambia formato.
const aFecha = (valor) => {
    if (!valor) {
        return null;
    }
    const fecha = new Date(valor);
    return Number.isNaN(fecha.getTime()) ? null : fecha;
};

// 1) Para qué sirve: convertir texto HH:mm:ss a objeto Date para picker de hora.
// 2) Cómo funciona: separa partes por ':' y asigna hora/minuto/segundo al día actual.
// 3) Qué hace: permite editar tiempos guardados como string.
// 4) Cómo editarla: adapta parser si backend empieza a enviar zona horaria.
const aHora = (valor) => {
    if (!valor || typeof valor !== 'string') {
        return null;
    }
    const partes = valor.split(':');
    if (partes.length < 2) {
        return null;
    }
    const hoy = new Date();
    hoy.setHours(Number(partes[0]) || 0, Number(partes[1]) || 0, Number(partes[2]) || 0, 0);
    return hoy;
};

// 1) Para qué sirve: serializar Date a cadena ISO solo fecha.
// 2) Cómo funciona: concatena año, mes y día con padding.
// 3) Qué hace: prepara payload compatible con tipo DATE.
// 4) Cómo editarla: cambia formato si la API exige otra convención.
const aIsoFecha = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${fecha.getFullYear()}-${formatearDos(fecha.getMonth() + 1)}-${formatearDos(fecha.getDate())}`;
};

// 1) Para qué sirve: serializar Date a cadena de hora HH:mm:ss.
// 2) Cómo funciona: extrae componentes de hora y aplica padding.
// 3) Qué hace: genera payload para configuraciones tipo TIME.
// 4) Cómo editarla: agrega milisegundos si backend llega a requerir precisión extra.
const aIsoHora = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${formatearDos(fecha.getHours())}:${formatearDos(fecha.getMinutes())}:${formatearDos(fecha.getSeconds())}`;
};

// 1) Para qué sirve: serializar Date completa a formato local ISO fecha-hora.
// 2) Cómo funciona: concatena resultados de aIsoFecha y aIsoHora.
// 3) Qué hace: construye payload para tipo DATETIME.
// 4) Cómo editarla: reemplaza separador si el contrato API lo modifica.
const aIsoFechaHora = (fecha) => {
    if (!fecha) {
        return '';
    }
    return `${aIsoFecha(fecha)}T${aIsoHora(fecha)}`;
};

// 1) Para qué sirve: alinear controles UI auxiliares con valor principal del formulario.
// 2) Cómo funciona: según tipo_valor rellena refs para número, booleano, fecha u hora.
// 3) Qué hace: evita desincronización entre input especializado y `formulario.valor`.
// 4) Cómo editarla: agrega ramas para nuevos tipos de dato configurables.
const sincronizarValorUI = () => {
    const tipo = formulario.tipo_valor;
    if (tipo === 'INT') {
        valorEntero.value = formulario.valor === '' ? null : Number.parseInt(formulario.valor, 10);
    }
    if (tipo === 'FLOAT') {
        valorDecimal.value = formulario.valor === '' ? null : Number.parseFloat(formulario.valor);
    }
    if (tipo === 'BOOLEAN') {
        valorBooleano.value = formulario.valor === 'false' ? 'false' : 'true';
    }
    if (tipo === 'DATE') {
        valorFecha.value = aFecha(formulario.valor);
    }
    if (tipo === 'TIME') {
        valorHora.value = aHora(formulario.valor);
    }
    if (tipo === 'DATETIME') {
        valorFechaHora.value = aFecha(formulario.valor);
    }
};

// 1) Para qué sirve: resetear la captura al cambiar tipo de dato.
// 2) Cómo funciona: limpia valor principal y refs auxiliares mediante watch.
// 3) Qué hace: previene persistencia de valores incompatibles entre tipos.
// 4) Cómo editarla: conserva ciertos valores si negocio requiere migración automática.
watch(
    () => formulario.tipo_valor,
    () => {
        formulario.valor = '';
        valorEntero.value = null;
        valorDecimal.value = null;
        valorBooleano.value = 'true';
        valorFecha.value = null;
        valorHora.value = null;
        valorFechaHora.value = null;
    }
);

// 1) Para qué sirve: sincronizar entero de UI hacia `formulario.valor`.
// 2) Cómo funciona: observa valorEntero y actualiza string cuando tipo es INT.
// 3) Qué hace: garantiza payload consistente para backend.
// 4) Cómo editarla: cambia casting si se requiere enviar número nativo en lugar de string.
watch(valorEntero, (valor) => {
    if (formulario.tipo_valor === 'INT') {
        formulario.valor = valor === null || valor === undefined ? '' : String(valor);
    }
});

// 1) Para qué sirve: sincronizar decimal de UI hacia `formulario.valor`.
// 2) Cómo funciona: observa valorDecimal y serializa cuando tipo es FLOAT.
// 3) Qué hace: mantiene correcto el valor enviado para configuraciones decimales.
// 4) Cómo editarla: agrega redondeo fijo si negocio exige precisión específica.
watch(valorDecimal, (valor) => {
    if (formulario.tipo_valor === 'FLOAT') {
        formulario.valor = valor === null || valor === undefined ? '' : String(valor);
    }
});

// 1) Para qué sirve: sincronizar selector booleano hacia valor de formulario.
// 2) Cómo funciona: observa valorBooleano y copia string true/false.
// 3) Qué hace: homologa representación booleana para backend.
// 4) Cómo editarla: convierte a boolean nativo si la API deja de usar strings.
watch(valorBooleano, (valor) => {
    if (formulario.tipo_valor === 'BOOLEAN') {
        formulario.valor = valor;
    }
});

// 1) Para qué sirve: sincronizar DatePicker de fecha hacia cadena ISO.
// 2) Cómo funciona: observa valorFecha y aplica aIsoFecha.
// 3) Qué hace: genera payload válido para tipo DATE.
// 4) Cómo editarla: adapta formato si cambia convención del backend.
watch(valorFecha, (valor) => {
    if (formulario.tipo_valor === 'DATE') {
        formulario.valor = aIsoFecha(valor);
    }
});

// 1) Para qué sirve: sincronizar picker de hora hacia cadena HH:mm:ss.
// 2) Cómo funciona: observa valorHora y aplica aIsoHora.
// 3) Qué hace: mantiene formato estable para tipo TIME.
// 4) Cómo editarla: añade zona horaria si se vuelve obligatoria.
watch(valorHora, (valor) => {
    if (formulario.tipo_valor === 'TIME') {
        formulario.valor = aIsoHora(valor);
    }
});

// 1) Para qué sirve: sincronizar picker datetime hacia cadena ISO local.
// 2) Cómo funciona: observa valorFechaHora y aplica aIsoFechaHora.
// 3) Qué hace: prepara payload compatible con tipo DATETIME.
// 4) Cómo editarla: reemplaza formato por UTC si negocio lo solicita.
watch(valorFechaHora, (valor) => {
    if (formulario.tipo_valor === 'DATETIME') {
        formulario.valor = aIsoFechaHora(valor);
    }
});

// 1) Para qué sirve: limpiar formulario y estado auxiliar de edición.
// 2) Cómo funciona: restablece campos base y refs de control por tipo.
// 3) Qué hace: deja modal listo para nueva captura.
// 4) Cómo editarla: incorpora cualquier nuevo campo del formulario.
const limpiarFormulario = () => {
    formulario.clave = '';
    formulario.valor = '';
    formulario.tipo_valor = 'STRING';
    formulario.descripcion = '';
    formulario.visible_para_director = true;
    editandoId.value = null;
    valorEntero.value = null;
    valorDecimal.value = null;
    valorBooleano.value = 'true';
    valorFecha.value = null;
    valorHora.value = null;
    valorFechaHora.value = null;
};

// 1) Para qué sirve: cargar listado de configuraciones globales.
// 2) Cómo funciona: consulta API y asigna colección a `registros`.
// 3) Qué hace: alimenta tabla principal del módulo.
// 4) Cómo editarla: agrega paginación remota o filtros al crecer el catálogo.
const cargar = async () => {
    cargando.value = true;
    try {
        const { data } = await listarConfiguracionesGlobalesAdmin();
        registros.value = data.data || [];
    } finally {
        cargando.value = false;
    }
};

// 1) Para qué sirve: abrir diálogo para alta de configuración.
// 2) Cómo funciona: limpia estado y habilita modal.
// 3) Qué hace: inicia flujo de nueva configuración global.
// 4) Cómo editarla: precarga tipo/clave por defecto si deseas plantillas.
const nuevo = () => {
    limpiarFormulario();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: abrir diálogo en modo edición de configuración.
// 2) Cómo funciona: mapea registro al formulario y sincroniza controles de UI.
// 3) Qué hace: permite modificar valor con componente correcto según tipo.
// 4) Cómo editarla: agrega parseo adicional para tipos complejos.
const editar = (registro) => {
    formulario.clave = registro.clave || '';
    formulario.tipo_valor = registro.tipo_valor || 'STRING';
    formulario.valor = registro.valor || '';
    formulario.descripcion = registro.descripcion || '';
    formulario.visible_para_director = registro.visible_para_director !== false;
    editandoId.value = registro.id;
    sincronizarValorUI();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: persistir alta o edición de configuración global.
// 2) Cómo funciona: decide create/update y luego refresca tabla.
// 3) Qué hace: mantiene datos en backend y UI sincronizados.
// 4) Cómo editarla: agrega validaciones previas por clave/tipo antes de enviar.
const guardar = async () => {
    guardando.value = true;
    try {
        if (editandoId.value) {
            await actualizarConfiguracionGlobalAdmin(editandoId.value, formulario);
        } else {
            await crearConfiguracionGlobalAdmin(formulario);
        }
        mostrarDialogo.value = false;
        limpiarFormulario();
        await cargar();
    } finally {
        guardando.value = false;
    }
};

// 1) Para qué sirve: eliminar configuración seleccionada.
// 2) Cómo funciona: ejecuta endpoint de borrado y recarga registros.
// 3) Qué hace: remueve la entrada del listado visible.
// 4) Cómo editarla: incorpora confirmación obligatoria si es configuración crítica.
const eliminar = async (registro) => {
    await eliminarConfiguracionGlobalAdmin(registro.id);
    await cargar();
};

// 1) Para qué sirve: lanzar carga inicial del módulo al montar componente.
// 2) Cómo funciona: invoca `cargar` en lifecycle onMounted.
// 3) Qué hace: muestra configuraciones desde el primer render.
// 4) Cómo editarla: añade bootstrap de catálogos auxiliares si se requieren.
onMounted(cargar);
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h1 class="text-2xl font-semibold">Configuraciones Globales</h1>
            <Button label="Nueva configuracion" icon="pi pi-plus" @click="nuevo" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
                <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                <MultiSelect v-model="columnasVisibles" :options="columnasDisponibles" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
            </div>
            <div>
                <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                <Select v-model="filasPorPagina" :options="opcionesFilasMostrar" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
            </div>
        </div>

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
            <Column v-if="esColumnaVisible('id')" field="id" header="ID" sortable />
            <Column v-if="esColumnaVisible('clave')" field="clave" header="Clave" sortable />
            <Column v-if="esColumnaVisible('valor')" field="valor" header="Valor" sortable>
                <template #body="slotProps">
                    <MontoMonedaColoreado
                        v-if="slotProps.data.tipo_valor === 'FLOAT' && esClaveMonetaria(slotProps.data.clave)"
                        :monto="slotProps.data.valor"
                    />
                    <span v-else>{{ slotProps.data.valor }}</span>
                </template>
            </Column>
            <Column v-if="esColumnaVisible('tipo_valor')" field="tipo_valor" header="Tipo" sortable />
            <Column v-if="esColumnaVisible('visible_para_director')" field="visible_para_director" header="Visible Director" sortable>
                <template #body="slotProps">
                    <Tag
                        :value="slotProps.data.visible_para_director ? 'Si' : 'No'"
                        :severity="slotProps.data.visible_para_director ? 'success' : 'contrast'"
                    />
                </template>
            </Column>
            <Column header="Acciones">
                <template #body="slotProps">
                    <div class="flex gap-2">
                        <Button size="small" icon="pi pi-pencil" severity="info" @click="editar(slotProps.data)" />
                        <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminar(slotProps.data)" />
                    </div>
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar configuracion' : 'Nueva configuracion'" :style="{ width: '40rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-key mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formulario.clave" class="w-full" placeholder="Ej. HORARIO_APERTURA" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sliders-h mr-1 text-primary"></i>Tipo de valor <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formulario.tipo_valor" :options="tiposValor" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona el tipo" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-dollar mr-1 text-primary"></i>Valor <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-if="formulario.tipo_valor === 'STRING'" v-model="formulario.valor" class="w-full" placeholder="Texto libre" />
                    <InputNumber v-else-if="formulario.tipo_valor === 'INT'" v-model="valorEntero" class="w-full" :minFractionDigits="0" :maxFractionDigits="0" :useGrouping="false" placeholder="Ej. 10" />
                    <InputNumber
                        v-else-if="formulario.tipo_valor === 'FLOAT'"
                        v-model="valorDecimal"
                        class="w-full"
                        :minFractionDigits="esConfiguracionMonetaria ? 2 : 0"
                        :maxFractionDigits="esConfiguracionMonetaria ? 2 : 6"
                        :useGrouping="esConfiguracionMonetaria"
                        :placeholder="esConfiguracionMonetaria ? '0.00' : 'Ej. 19.95'"
                        @focus="limpiarDecimalMonetarioEnFoco"
                    />
                    <Select v-else-if="formulario.tipo_valor === 'BOOLEAN'" v-model="valorBooleano" class="w-full" :options="[ { label: 'Verdadero', value: 'true' }, { label: 'Falso', value: 'false' } ]" optionLabel="label" optionValue="value" filter filterPlaceholder="Buscar opcion..." />
                    <DatePicker v-else-if="formulario.tipo_valor === 'DATE'" v-model="valorFecha" class="w-full" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DD" />
                    <DatePicker v-else-if="formulario.tipo_valor === 'TIME'" v-model="valorHora" class="w-full" timeOnly hourFormat="24" showIcon placeholder="HH:MM:SS" />
                    <DatePicker v-else-if="formulario.tipo_valor === 'DATETIME'" v-model="valorFechaHora" class="w-full" showTime hourFormat="24" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DDTHH:MM:SS" />
                    <Textarea v-else v-model="formulario.valor" rows="4" class="w-full font-mono" placeholder='{"clave": "valor"}' />
                    <div v-if="esConfiguracionMonetaria" class="mt-2">
                        <small class="block text-surface-500 mb-1">Vista previa monetaria coloreada</small>
                        <MontoMonedaColoreado :monto="valorMonetarioVistaPrevia" />
                    </div>
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formulario.descripcion" rows="3" class="w-full" placeholder="Explica para que sirve esta configuracion" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-eye mr-1 text-primary"></i>Acceso para Director</label>
                    <div class="border border-surface-200 rounded-lg p-3">
                        <div class="flex items-center gap-2">
                            <Checkbox v-model="formulario.visible_para_director" binary inputId="visible_para_director_cfg" />
                            <label for="visible_para_director_cfg">Permitir que el director vea y edite el valor de esta variable.</label>
                        </div>
                        <small class="text-surface-500 block mt-2">Si desactivas esta opción, solo administrador podrá verla y modificarla.</small>
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar" @click="guardar" />
            </div>
        </Dialog>
    </section>
</template>





