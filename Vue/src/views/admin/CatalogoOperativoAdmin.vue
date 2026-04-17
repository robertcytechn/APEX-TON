<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    actualizarCategoriaOperativaAdmin,
    actualizarConceptoAdmin,
    actualizarDetalleParametrizadoAdmin,
    crearCategoriaOperativaAdmin,
    crearConceptoAdmin,
    crearDetalleParametrizadoAdmin,
    eliminarCategoriaOperativaAdmin,
    eliminarConceptoAdmin,
    eliminarDetalleParametrizadoAdmin,
    listarCategoriasOperativasAdmin,
    listarConceptosAdmin,
    listarDetallesParametrizadosAdmin,
    listarRubrosContablesAdmin
} from '@/service/cabinaArquitecturaServicio';

const cargandoCategorias = ref(false);
const cargandoConceptos = ref(false);
const cargandoDetalles = ref(false);

const guardandoCategoria = ref(false);
const guardandoConcepto = ref(false);
const guardandoDetalle = ref(false);

const categorias = ref([]);
const conceptos = ref([]);
const detalles = ref([]);
const rubros = ref([]);

const categoriaSeleccionadaId = ref(null);

const mostrarDialogoCategoria = ref(false);
const mostrarDialogoConcepto = ref(false);
const mostrarDialogoDetalle = ref(false);

const editandoCategoriaId = ref(null);
const editandoConceptoId = ref(null);
const editandoDetalleId = ref(null);

const columnasDisponiblesCategorias = [
    { label: 'Clave', value: 'clave' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Tipo', value: 'tipo' },
    { label: 'Orden', value: 'orden' },
    { label: 'Usa saldo inicial', value: 'usa_saldo_inicial' },
    { label: 'Estado', value: 'estado' }
];
const columnasVisiblesCategorias = ref([...columnasDisponiblesCategorias]);

const columnasDisponiblesConceptos = [
    { label: 'Clave', value: 'clave' },
    { label: 'Concepto', value: 'nombre' },
    { label: 'Rubro', value: 'rubro_nombre' },
    { label: 'Requiere imagen', value: 'requiere_imagen' },
    { label: 'Tipo', value: 'tipo' },
    { label: 'Estado', value: 'estado' }
];
const columnasVisiblesConceptos = ref([...columnasDisponiblesConceptos]);

const columnasDisponiblesDetalles = [
    { label: 'Campo', value: 'nombre' },
    { label: 'Clave', value: 'clave' },
    { label: 'Tipo', value: 'tipo_valor' },
    { label: 'Requerido', value: 'requerido' },
    { label: 'Estado', value: 'estado' }
];
const columnasVisiblesDetalles = ref([...columnasDisponiblesDetalles]);

const filasPorPaginaCategorias = ref(10);
const filasPorPaginaConceptos = ref(10);
const filasPorPaginaDetalles = ref(10);

const opcionesTipoCategoria = [
    { label: 'Ingreso', value: 'INGRESO' },
    { label: 'Egreso', value: 'EGRESO' },
    { label: 'Mixto', value: 'MIXTO' }
];

const opcionesTipoConcepto = [
    { label: 'Ingreso', value: 'INGRESO' },
    { label: 'Egreso', value: 'EGRESO' }
];

const opcionesTipoValorDetalle = [
    { label: 'Texto', value: 'TEXT' },
    { label: 'Decimal', value: 'DECIMAL' },
    { label: 'Entero', value: 'INT' },
    { label: 'Booleano', value: 'BOOLEAN' },
    { label: 'Fecha', value: 'DATE' },
    { label: 'Fecha y hora', value: 'DATETIME' }
];

const opcionesFilasCategorias = computed(() => {
    const total = categorias.value.length;
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

const opcionesFilasConceptos = computed(() => {
    const total = conceptos.value.length;
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

const opcionesFilasDetalles = computed(() => {
    const total = detalles.value.length;
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

// 1) Para qué sirve: verificar visibilidad de columnas por bloque de tabla.
// 2) Cómo funciona: revisa si la clave de columna está seleccionada.
// 3) Qué hace: habilita personalización de columnas en categorías/conceptos/detalles.
// 4) Cómo editarla: agrega reglas de permisos si algunas columnas deben ocultarse.
const esColumnaVisible = (columnas, columna) => columnas.some((item) => item.value === columna);

const opcionesCategoriasSelect = computed(() =>
    categorias.value.map((item) => ({
        label: `${item.clave} - ${item.nombre}`,
        value: item.id
    }))
);

const categoriaSeleccionada = computed(() =>
    categorias.value.find((item) => item.id === categoriaSeleccionadaId.value) || null
);

const tipoCategoriaEnFormularioConcepto = computed(() => {
    const categoriaId = formularioConcepto.categoria || categoriaSeleccionadaId.value;
    const categoria = categorias.value.find((item) => item.id === categoriaId);
    return categoria?.tipo || 'MIXTO';
});

const tipoConceptoBloqueadoPorCategoria = computed(() => tipoCategoriaEnFormularioConcepto.value === 'INGRESO' || tipoCategoriaEnFormularioConcepto.value === 'EGRESO');

const textoReglaTipoConcepto = computed(() => {
    if (tipoCategoriaEnFormularioConcepto.value === 'INGRESO') {
        return 'Esta categoría es de ingreso. El concepto se guardará como INGRESO.';
    }
    if (tipoCategoriaEnFormularioConcepto.value === 'EGRESO') {
        return 'Esta categoría es de egreso. El concepto se guardará como EGRESO.';
    }
    return 'Esta categoría es mixta. Puedes elegir si el concepto es ingreso o egreso.';
});

const formularioCategoria = reactive({
    nombre: '',
    clave: '',
    tipo: 'MIXTO',
    orden: 0,
    usa_saldo_inicial: false,
    descripcion: ''
});

const formularioConcepto = reactive({
    categoria: null,
    rubro_contable: null,
    nombre: '',
    clave: '',
    tipo: 'INGRESO',
    es_recurrente: false,
    requiere_imagen: false,
    descripcion: ''
});

const formularioDetalle = reactive({
    categoria: null,
    nombre: '',
    clave: '',
    tipo_valor: 'TEXT',
    requerido: false,
    valor_defecto: '',
    descripcion: ''
});

// 1) Para qué sirve: normalizar textos para validación semántica de rubros.
// 2) Cómo funciona: unifica mayúsculas y separadores para comparaciones robustas.
// 3) Qué hace: facilita detectar patrones como NO_CONTABLE o SIN_GRUPO.
// 4) Cómo editarla: agrega más reemplazos si cambian claves/nombres de catálogo.
const normalizarTextoContable = (valor) => String(valor || '').trim().replace(/[-\s]+/g, '_').toUpperCase();

// 1) Para qué sirve: identificar rubros no contables por padre o nomenclatura.
// 2) Cómo funciona: evalúa clave/nombre del padre y nombre del rubro con reglas semánticas.
// 3) Qué hace: marca rubros que no impactan en el estado de resultados.
// 4) Cómo editarla: amplía expresiones cuando se incorporen nuevas nomenclaturas no contables.
const rubroEsNoContablePorSemantica = ({ padreClave = '', padreNombre = '', nombreRubro = '' } = {}) => {
    const clavePadre = normalizarTextoContable(padreClave);
    const nombrePadre = normalizarTextoContable(padreNombre);
    const nombre = normalizarTextoContable(nombreRubro);
    const huella = `${clavePadre} ${nombrePadre} ${nombre}`;

    return huella.includes('NO_CONTABLE') || huella.includes('SIN_GRUPO');
};

const opcionRubroSeleccionada = computed(() => rubros.value.find((item) => item.value === formularioConcepto.rubro_contable) || null);

const rubroNoContableSeleccionado = computed(() => {
    if (formularioConcepto.rubro_contable === null || formularioConcepto.rubro_contable === undefined || formularioConcepto.rubro_contable === '') {
        return true;
    }
    return !!opcionRubroSeleccionada.value?.esNoContable;
});

const mensajeRubroNoContable = computed(() => {
    if (formularioConcepto.rubro_contable === null || formularioConcepto.rubro_contable === undefined || formularioConcepto.rubro_contable === '') {
        return 'Sin rubro contable: este concepto se registrará como no contable y no impactará en el Estado de Resultados.';
    }

    if (rubroNoContableSeleccionado.value) {
        return 'Rubro no contable detectado: este concepto no se considerará en ingresos/egresos netos del Estado de Resultados.';
    }

    return '';
});

// 1) Para qué sirve: limpiar formulario de categoría operativa.
// 2) Cómo funciona: restablece campos y editandoCategoriaId.
// 3) Qué hace: prepara modal para alta o cancelación.
// 4) Cómo editarla: agrega nuevos campos del formulario conforme crezca el modelo.
const limpiarFormularioCategoria = () => {
    formularioCategoria.nombre = '';
    formularioCategoria.clave = '';
    formularioCategoria.tipo = 'MIXTO';
    formularioCategoria.orden = 0;
    formularioCategoria.usa_saldo_inicial = false;
    formularioCategoria.descripcion = '';
    editandoCategoriaId.value = null;
};

// 1) Para qué sirve: limpiar formulario de concepto y sincronizar su tipo.
// 2) Cómo funciona: reinicia valores, enlaza categoría actual y aplica regla de tipo.
// 3) Qué hace: evita inconsistencias entre categoría seleccionada y tipo de concepto.
// 4) Cómo editarla: integra nuevos atributos del concepto dentro del reset.
const limpiarFormularioConcepto = () => {
    formularioConcepto.categoria = categoriaSeleccionadaId.value;
    formularioConcepto.rubro_contable = null;
    formularioConcepto.nombre = '';
    formularioConcepto.clave = '';
    formularioConcepto.tipo = 'INGRESO';
    formularioConcepto.es_recurrente = false;
    formularioConcepto.requiere_imagen = false;
    formularioConcepto.descripcion = '';
    editandoConceptoId.value = null;
    sincronizarTipoConceptoConCategoria();
};

// 1) Para qué sirve: forzar tipo de concepto cuando categoría no es MIXTO.
// 2) Cómo funciona: inspecciona tipo de categoría y fija INGRESO o EGRESO.
// 3) Qué hace: mantiene integridad entre clasificación de categoría y concepto.
// 4) Cómo editarla: ajusta la regla si se agregan nuevos tipos de categoría.
const sincronizarTipoConceptoConCategoria = () => {
    if (tipoCategoriaEnFormularioConcepto.value === 'INGRESO') {
        formularioConcepto.tipo = 'INGRESO';
        return;
    }
    if (tipoCategoriaEnFormularioConcepto.value === 'EGRESO') {
        formularioConcepto.tipo = 'EGRESO';
    }
};

// 1) Para qué sirve: limpiar formulario de detalle parametrizado.
// 2) Cómo funciona: restablece categoría, tipo, flags y edición.
// 3) Qué hace: deja modal listo para nueva captura de detalle.
// 4) Cómo editarla: incluye campos extra si se amplía el esquema de detalle.
const limpiarFormularioDetalle = () => {
    formularioDetalle.categoria = categoriaSeleccionadaId.value;
    formularioDetalle.nombre = '';
    formularioDetalle.clave = '';
    formularioDetalle.tipo_valor = 'TEXT';
    formularioDetalle.requerido = false;
    formularioDetalle.valor_defecto = '';
    formularioDetalle.descripcion = '';
    editandoDetalleId.value = null;
};

// 1) Para qué sirve: cargar catálogo de rubros contables para selector de conceptos.
// 2) Cómo funciona: consulta API y construye opciones label/value.
// 3) Qué hace: permite vincular conceptos con rubro o dejarlos sin rubro.
// 4) Cómo editarla: modifica etiqueta de opciones según requerimientos de UX.
const cargarRubros = async () => {
    const { data } = await listarRubrosContablesAdmin();
    rubros.value = [
        {
            label: 'Sin rubro contable (no contable)',
            value: null,
            esNoContable: true,
            padreClave: 'SIN_GRUPO_NO_CONTABLE',
            padreNombre: 'SIN GRUPO NO CONTABLE'
        },
        ...(data.data || []).map((item) => ({
            label: `${item.nombre || 'SIN NOMBRE'} - ${item.padre_nombre || item.padre_info?.nombre || 'SIN PADRE'}`,
            value: item.id,
            padreClave: item.padre_clave || item.padre_info?.clave || '',
            padreNombre: item.padre_nombre || item.padre_info?.nombre || 'SIN PADRE',
            esNoContable: rubroEsNoContablePorSemantica({
                padreClave: item.padre_clave || item.padre_info?.clave || '',
                padreNombre: item.padre_nombre || item.padre_info?.nombre || '',
                nombreRubro: item.nombre || ''
            })
        }))
    ];
};

// 1) Para qué sirve: cargar categorías operativas disponibles.
// 2) Cómo funciona: consulta API, actualiza lista y valida categoría seleccionada.
// 3) Qué hace: mantiene contexto activo para gestionar conceptos y detalles.
// 4) Cómo editarla: incorpora ordenamientos/filtros si backend no los provee.
const cargarCategorias = async () => {
    cargandoCategorias.value = true;
    try {
        const { data } = await listarCategoriasOperativasAdmin();
        categorias.value = data.data || [];

        if (!categoriaSeleccionadaId.value && categorias.value.length > 0) {
            categoriaSeleccionadaId.value = categorias.value[0].id;
        }

        if (categoriaSeleccionadaId.value && !categorias.value.some((item) => item.id === categoriaSeleccionadaId.value)) {
            categoriaSeleccionadaId.value = categorias.value[0]?.id || null;
        }
    } finally {
        cargandoCategorias.value = false;
    }
};

// 1) Para qué sirve: cargar conceptos de la categoría activa.
// 2) Cómo funciona: consulta API filtrando por categoriaSeleccionadaId.
// 3) Qué hace: rellena la tabla de conceptos contextual.
// 4) Cómo editarla: agrega parámetros adicionales cuando existan nuevos filtros.
const cargarConceptos = async () => {
    if (!categoriaSeleccionadaId.value) {
        conceptos.value = [];
        return;
    }
    cargandoConceptos.value = true;
    try {
        const { data } = await listarConceptosAdmin(categoriaSeleccionadaId.value);
        conceptos.value = data.data || [];
    } finally {
        cargandoConceptos.value = false;
    }
};

// 1) Para qué sirve: cargar detalles parametrizados de la categoría activa.
// 2) Cómo funciona: solicita datos por categoriaSeleccionadaId.
// 3) Qué hace: alimenta tabla de campos dinámicos por categoría.
// 4) Cómo editarla: añade transformaciones si backend amplía metadatos.
const cargarDetalles = async () => {
    if (!categoriaSeleccionadaId.value) {
        detalles.value = [];
        return;
    }
    cargandoDetalles.value = true;
    try {
        const { data } = await listarDetallesParametrizadosAdmin(categoriaSeleccionadaId.value);
        detalles.value = data.data || [];
    } finally {
        cargandoDetalles.value = false;
    }
};

// 1) Para qué sirve: abrir modal para alta de categoría.
// 2) Cómo funciona: limpia formulario y activa diálogo.
// 3) Qué hace: inicia flujo de creación de pestaña operativa.
// 4) Cómo editarla: predefine tipo/orden inicial según política interna.
const nuevaCategoria = () => {
    limpiarFormularioCategoria();
    mostrarDialogoCategoria.value = true;
};

// 1) Para qué sirve: abrir edición de categoría seleccionada.
// 2) Cómo funciona: mapea registro a formulario reactivo.
// 3) Qué hace: permite modificar metadatos de la categoría.
// 4) Cómo editarla: sincroniza campos nuevos del modelo aquí.
const editarCategoria = (registro) => {
    formularioCategoria.nombre = registro.nombre || '';
    formularioCategoria.clave = registro.clave || '';
    formularioCategoria.tipo = registro.tipo || 'MIXTO';
    formularioCategoria.orden = Number(registro.orden || 0);
    formularioCategoria.usa_saldo_inicial = !!registro.usa_saldo_inicial;
    formularioCategoria.descripcion = registro.descripcion || '';
    editandoCategoriaId.value = registro.id;
    mostrarDialogoCategoria.value = true;
};

// 1) Para qué sirve: guardar alta o edición de categoría operativa.
// 2) Cómo funciona: decide create/update y recarga lista de categorías.
// 3) Qué hace: persiste cambios estructurales del catálogo.
// 4) Cómo editarla: agrega validaciones de clave única antes de enviar.
const guardarCategoria = async () => {
    guardandoCategoria.value = true;
    try {
        if (editandoCategoriaId.value) {
            await actualizarCategoriaOperativaAdmin(editandoCategoriaId.value, formularioCategoria);
        } else {
            await crearCategoriaOperativaAdmin(formularioCategoria);
        }
        mostrarDialogoCategoria.value = false;
        limpiarFormularioCategoria();
        await cargarCategorias();
    } finally {
        guardandoCategoria.value = false;
    }
};

// 1) Para qué sirve: eliminar categoría del catálogo.
// 2) Cómo funciona: llama servicio de baja y refresca categorías/conceptos/detalles.
// 3) Qué hace: mantiene estado de las tres tablas consistente.
// 4) Cómo editarla: agrega confirmación y bloqueo si hay dependencias activas.
const eliminarCategoria = async (registro) => {
    await eliminarCategoriaOperativaAdmin(registro.id);
    await cargarCategorias();
    await Promise.all([cargarConceptos(), cargarDetalles()]);
};

// 1) Para qué sirve: abrir modal para nuevo concepto de la categoría activa.
// 2) Cómo funciona: valida existencia de categoría, limpia formulario y muestra diálogo.
// 3) Qué hace: inicia alta de concepto contextual.
// 4) Cómo editarla: agrega comportamiento para categorías predeterminadas si aplica.
const nuevoConcepto = () => {
    if (!categoriaSeleccionadaId.value) {
        return;
    }
    limpiarFormularioConcepto();
    mostrarDialogoConcepto.value = true;
};

// 1) Para qué sirve: abrir edición de concepto existente.
// 2) Cómo funciona: hidrata formulario desde registro y sincroniza regla de tipo.
// 3) Qué hace: permite ajustes de rubro, recurrencia y evidencia.
// 4) Cómo editarla: incorpora nuevos flags del concepto al mapeo.
const editarConcepto = (registro) => {
    formularioConcepto.categoria = registro.categoria || categoriaSeleccionadaId.value;
    formularioConcepto.rubro_contable = registro.rubro_contable || null;
    formularioConcepto.nombre = registro.nombre || '';
    formularioConcepto.clave = registro.clave || '';
    formularioConcepto.tipo = registro.tipo || 'INGRESO';
    formularioConcepto.es_recurrente = !!registro.es_recurrente;
    formularioConcepto.requiere_imagen = !!registro.requiere_imagen;
    formularioConcepto.descripcion = registro.descripcion || '';
    editandoConceptoId.value = registro.id;
    sincronizarTipoConceptoConCategoria();
    mostrarDialogoConcepto.value = true;
};

// 1) Para qué sirve: guardar alta/edición de concepto con reglas por tipo de categoría.
// 2) Cómo funciona: construye payload y fuerza tipo si categoría no es MIXTO.
// 3) Qué hace: preserva integridad semántica entre categoría y concepto.
// 4) Cómo editarla: modifica la construcción del payload al cambiar contrato API.
const guardarConcepto = async () => {
    guardandoConcepto.value = true;
    try {
        const payload = {
            ...formularioConcepto,
            categoria: formularioConcepto.categoria || categoriaSeleccionadaId.value,
            rubro_contable: formularioConcepto.rubro_contable || null,
            tipo:
                tipoCategoriaEnFormularioConcepto.value === 'MIXTO'
                    ? formularioConcepto.tipo
                    : tipoCategoriaEnFormularioConcepto.value
        };
        if (editandoConceptoId.value) {
            await actualizarConceptoAdmin(editandoConceptoId.value, payload);
        } else {
            await crearConceptoAdmin(payload);
        }
        mostrarDialogoConcepto.value = false;
        limpiarFormularioConcepto();
        await cargarConceptos();
    } finally {
        guardandoConcepto.value = false;
    }
};

// 1) Para qué sirve: eliminar concepto de la categoría actual.
// 2) Cómo funciona: invoca endpoint de eliminación y recarga conceptos.
// 3) Qué hace: actualiza listado de conceptos sin recargar toda la vista.
// 4) Cómo editarla: agrega confirmación previa o validación de uso histórico.
const eliminarConcepto = async (registro) => {
    await eliminarConceptoAdmin(registro.id);
    await cargarConceptos();
};

// 1) Para qué sirve: abrir modal para nuevo detalle parametrizado.
// 2) Cómo funciona: valida categoría activa, limpia formulario y muestra diálogo.
// 3) Qué hace: inicia captura de campos dinámicos por categoría.
// 4) Cómo editarla: preselecciona tipo de valor según reglas del módulo.
const nuevoDetalle = () => {
    if (!categoriaSeleccionadaId.value) {
        return;
    }
    limpiarFormularioDetalle();
    mostrarDialogoDetalle.value = true;
};

// 1) Para qué sirve: abrir edición de detalle parametrizado.
// 2) Cómo funciona: mapea registro al formulario de detalle.
// 3) Qué hace: permite ajustar tipo, obligatoriedad y valor por defecto.
// 4) Cómo editarla: añade campos adicionales cuando el modelo evolucione.
const editarDetalle = (registro) => {
    formularioDetalle.categoria = registro.categoria || categoriaSeleccionadaId.value;
    formularioDetalle.nombre = registro.nombre || '';
    formularioDetalle.clave = registro.clave || '';
    formularioDetalle.tipo_valor = registro.tipo_valor || 'TEXT';
    formularioDetalle.requerido = !!registro.requerido;
    formularioDetalle.valor_defecto = registro.valor_defecto || '';
    formularioDetalle.descripcion = registro.descripcion || '';
    editandoDetalleId.value = registro.id;
    mostrarDialogoDetalle.value = true;
};

// 1) Para qué sirve: guardar alta o edición de detalle parametrizado.
// 2) Cómo funciona: arma payload con categoría y decide create/update.
// 3) Qué hace: persiste estructura de campos dinámicos operativos.
// 4) Cómo editarla: agrega validación por tipo_valor antes de guardar.
const guardarDetalle = async () => {
    guardandoDetalle.value = true;
    try {
        const payload = {
            ...formularioDetalle,
            categoria: formularioDetalle.categoria || categoriaSeleccionadaId.value
        };
        if (editandoDetalleId.value) {
            await actualizarDetalleParametrizadoAdmin(editandoDetalleId.value, payload);
        } else {
            await crearDetalleParametrizadoAdmin(payload);
        }
        mostrarDialogoDetalle.value = false;
        limpiarFormularioDetalle();
        await cargarDetalles();
    } finally {
        guardandoDetalle.value = false;
    }
};

// 1) Para qué sirve: eliminar detalle parametrizado existente.
// 2) Cómo funciona: llama servicio de baja y recarga lista de detalles.
// 3) Qué hace: actualiza tabla de detalles de forma inmediata.
// 4) Cómo editarla: protege eliminación si detalle está en uso activo.
const eliminarDetalle = async (registro) => {
    await eliminarDetalleParametrizadoAdmin(registro.id);
    await cargarDetalles();
};

// 1) Para qué sirve: recargar conceptos y detalles al cambiar de categoría activa.
// 2) Cómo funciona: watcher sobre categoriaSeleccionadaId con carga paralela.
// 3) Qué hace: mantiene tablas hijas sincronizadas con contexto actual.
// 4) Cómo editarla: agrega más cargas dependientes si sumas nuevas secciones.
watch(categoriaSeleccionadaId, async () => {
    await Promise.all([cargarConceptos(), cargarDetalles()]);
});

// 1) Para qué sirve: sincronizar tipo de concepto cuando cambia categoría en formulario.
// 2) Cómo funciona: watcher sobre formularioConcepto.categoria.
// 3) Qué hace: aplica automáticamente reglas INGRESO/EGRESO/MIXTO.
// 4) Cómo editarla: modifica esta reacción si se permite sobreescritura manual.
watch(
    () => formularioConcepto.categoria,
    () => {
        sincronizarTipoConceptoConCategoria();
    }
);

// 1) Para qué sirve: inicializar catálogos y datos contextuales al abrir la vista.
// 2) Cómo funciona: carga rubros/categorías y después conceptos/detalles en paralelo.
// 3) Qué hace: deja completo el módulo unificado al primer render.
// 4) Cómo editarla: agrega inicializaciones extra si aparece otra subsección.
onMounted(async () => {
    await Promise.all([cargarRubros(), cargarCategorias()]);
    await Promise.all([cargarConceptos(), cargarDetalles()]);
});
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h1 class="text-2xl font-semibold">Catalogo Operativo Unificado</h1>
                <Button label="Nueva categoria" icon="pi pi-plus" @click="nuevaCategoria" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sitemap mr-1 text-primary"></i>Categoria operativa activa</label>
                    <Select v-model="categoriaSeleccionadaId" :options="opcionesCategoriasSelect" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona categoria" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-info-circle mr-1 text-primary"></i>Contexto actual</label>
                    <div class="border border-surface-200 rounded-lg p-3 min-h-[2.75rem] flex items-center">
                        <span v-if="categoriaSeleccionada" class="text-sm">
                            {{ categoriaSeleccionada.clave }} - {{ categoriaSeleccionada.nombre }}
                        </span>
                        <span v-else class="text-sm text-surface-500">Selecciona una categoria para gestionar conceptos y detalles</span>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesCategorias" :options="columnasDisponiblesCategorias" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaCategorias" :options="opcionesFilasCategorias" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="categorias"
                :loading="cargandoCategorias"
                paginator
                :rows="filasPorPaginaCategorias"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
                selectionMode="single"
                dataKey="id"
                :selection="categoriaSeleccionada"
                @row-click="categoriaSeleccionadaId = $event.data.id"
            >
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'clave')" field="clave" header="Clave" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'nombre')" field="nombre" header="Nombre" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'tipo')" field="tipo" header="Tipo" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'orden')" field="orden" header="Orden" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'usa_saldo_inicial')" field="usa_saldo_inicial" header="Usa saldo inicial" sortable>
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.usa_saldo_inicial ? 'Si' : 'No'" :severity="slotProps.data.usa_saldo_inicial ? 'success' : 'secondary'" />
                    </template>
                </Column>
                <Column v-if="esColumnaVisible(columnasVisiblesCategorias, 'estado')" field="estado" header="Estado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-eye" severity="secondary" @click="categoriaSeleccionadaId = slotProps.data.id" />
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarCategoria(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarCategoria(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h2 class="text-xl font-semibold">Conceptos de la categoria seleccionada</h2>
                <Button label="Nuevo concepto" icon="pi pi-plus" :disabled="!categoriaSeleccionadaId" @click="nuevoConcepto" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesConceptos" :options="columnasDisponiblesConceptos" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaConceptos" :options="opcionesFilasConceptos" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="conceptos"
                :loading="cargandoConceptos"
                paginator
                :rows="filasPorPaginaConceptos"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'clave')" field="clave" header="Clave" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'nombre')" field="nombre" header="Concepto" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'rubro_nombre')" field="rubro_nombre_con_padre" header="Rubro contable" sortable>
                    <template #body="slotProps">
                        <span>{{ slotProps.data.rubro_nombre_con_padre || 'SIN RUBRO CONTABLE' }}</span>
                    </template>
                </Column>
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'requiere_imagen')" field="requiere_imagen" header="Requiere imagen" sortable>
                    <template #body="slotProps">
                        <Tag :severity="slotProps.data.requiere_imagen ? 'warn' : 'secondary'" :value="slotProps.data.requiere_imagen ? 'Si' : 'No'" />
                    </template>
                </Column>
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'tipo')" field="tipo" header="Tipo" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesConceptos, 'estado')" field="estado" header="Estado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarConcepto(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarConcepto(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h2 class="text-xl font-semibold">Detalles parametrizados de la categoria seleccionada</h2>
                <Button label="Nuevo detalle" icon="pi pi-plus" severity="contrast" :disabled="!categoriaSeleccionadaId" @click="nuevoDetalle" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesDetalles" :options="columnasDisponiblesDetalles" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaDetalles" :options="opcionesFilasDetalles" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="detalles"
                :loading="cargandoDetalles"
                paginator
                :rows="filasPorPaginaDetalles"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'nombre')" field="nombre" header="Campo" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'clave')" field="clave" header="Clave" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'tipo_valor')" field="tipo_valor" header="Tipo" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'requerido')" field="requerido" header="Requerido" sortable>
                    <template #body="slotProps">
                        <Tag :severity="slotProps.data.requerido ? 'danger' : 'secondary'" :value="slotProps.data.requerido ? 'Si' : 'No'" />
                    </template>
                </Column>
                <Column v-if="esColumnaVisible(columnasVisiblesDetalles, 'estado')" field="estado" header="Estado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarDetalle(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarDetalle(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialogoCategoria" modal :header="editandoCategoriaId ? 'Editar categoria operativa' : 'Nueva categoria operativa'" :style="{ width: '42rem' }">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-tag mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioCategoria.nombre" class="w-full" placeholder="Ej. ADMINISTRACION" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-hashtag mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioCategoria.clave" class="w-full" placeholder="Ej. ADMIN" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-arrows-v mr-1 text-primary"></i>Tipo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioCategoria.tipo" :options="opcionesTipoCategoria" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona tipo" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sort-numeric-up mr-1 text-primary"></i>Orden <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputNumber v-model="formularioCategoria.orden" class="w-full" :useGrouping="false" :min="0" placeholder="0" />
                </div>
                <div class="md:col-span-2">
                    <div class="w-full border border-surface-200 rounded-lg p-3">
                        <label class="block text-sm mb-2"><i class="pi pi-wallet mr-1 text-primary"></i>Saldo inicial mensual por categoría</label>
                        <div class="flex items-center gap-2">
                            <Checkbox v-model="formularioCategoria.usa_saldo_inicial" binary inputId="usa_saldo_inicial_categoria" />
                            <label for="usa_saldo_inicial_categoria">Esta categoría usa saldo inicial mensual con arrastre automático.</label>
                        </div>
                    </div>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioCategoria.descripcion" rows="3" class="w-full" placeholder="Describe el tipo de flujo que agrupa esta pestana" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoCategoria = false" />
                <Button :loading="guardandoCategoria" label="Guardar" @click="guardarCategoria" />
            </div>
        </Dialog>

        <Dialog v-model:visible="mostrarDialogoConcepto" modal :header="editandoConceptoId ? 'Editar concepto' : 'Nuevo concepto'" :style="{ width: '48rem' }">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-table mr-1 text-primary"></i>Categoria operativa <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioConcepto.categoria" :options="opcionesCategoriasSelect" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona categoria" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-bookmark mr-1 text-primary"></i>Rubro contable <small class="text-surface-500">(opcional)</small></label>
                    <Select v-model="formularioConcepto.rubro_contable" :options="rubros" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona rubro" filter filterPlaceholder="Buscar opcion..." />
                    <Message v-if="rubroNoContableSeleccionado" severity="warn" :closable="false" class="mt-2">
                        {{ mensajeRubroNoContable }}
                    </Message>
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-file-edit mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioConcepto.nombre" class="w-full" placeholder="Ej. VENTA DE CAFE" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-hashtag mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioConcepto.clave" class="w-full" placeholder="Ej. ADMIN_VENTA_CAFE" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-arrows-v mr-1 text-primary"></i>Tipo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select
                        v-model="formularioConcepto.tipo"
                        :options="opcionesTipoConcepto"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona tipo"
                        filter
                        filterPlaceholder="Buscar opcion..."
                        :disabled="tipoConceptoBloqueadoPorCategoria"
                    />
                    <small class="text-surface-500 block mt-2">{{ textoReglaTipoConcepto }}</small>
                </div>
                <div class="space-y-3">
                    <div class="w-full border border-surface-200 rounded-lg p-3">
                        <label class="block text-sm mb-2"><i class="pi pi-refresh mr-1 text-primary"></i>Frecuencia <small class="text-surface-500">(opcional)</small></label>
                        <div class="flex items-center gap-2">
                            <Checkbox v-model="formularioConcepto.es_recurrente" binary inputId="es_recurrente_unificado" />
                            <label for="es_recurrente_unificado">Es recurrente</label>
                        </div>
                    </div>
                    <div class="w-full border border-surface-200 rounded-lg p-3">
                        <label class="block text-sm mb-2"><i class="pi pi-image mr-1 text-primary"></i>Evidencia <small class="text-surface-500">(opcional)</small></label>
                        <div class="flex items-center gap-2">
                            <Checkbox v-model="formularioConcepto.requiere_imagen" binary inputId="requiere_imagen_unificado" />
                            <label for="requiere_imagen_unificado">Solicitar imagen o archivo de respaldo</label>
                        </div>
                    </div>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioConcepto.descripcion" rows="3" class="w-full" placeholder="Describe cuando aplica este concepto" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoConcepto = false" />
                <Button :loading="guardandoConcepto" label="Guardar" @click="guardarConcepto" />
            </div>
        </Dialog>

        <Dialog v-model:visible="mostrarDialogoDetalle" modal :header="editandoDetalleId ? 'Editar detalle parametrizado' : 'Nuevo detalle parametrizado'" :style="{ width: '48rem' }">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-table mr-1 text-primary"></i>Categoria operativa <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioDetalle.categoria" :options="opcionesCategoriasSelect" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona categoria" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-file mr-1 text-primary"></i>Nombre del campo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioDetalle.nombre" class="w-full" placeholder="Ej. Responsable" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-code mr-1 text-primary"></i>Clave tecnica <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioDetalle.clave" class="w-full" placeholder="Ej. responsable" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sliders-h mr-1 text-primary"></i>Tipo de valor <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioDetalle.tipo_valor" :options="opcionesTipoValorDetalle" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona tipo" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-key mr-1 text-primary"></i>Valor por defecto <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioDetalle.valor_defecto" class="w-full" placeholder="Ej. N/A" />
                </div>
                <div class="flex items-end">
                    <div class="w-full border border-surface-200 rounded-lg p-3">
                        <label class="block text-sm mb-2"><i class="pi pi-asterisk mr-1 text-primary"></i>Regla del campo</label>
                        <div class="flex items-center gap-2">
                            <Checkbox v-model="formularioDetalle.requerido" binary inputId="requerido_unificado" />
                            <label for="requerido_unificado">Campo obligatorio</label>
                        </div>
                    </div>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioDetalle.descripcion" rows="3" class="w-full" placeholder="Describe como se captura o interpreta este dato" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoDetalle = false" />
                <Button :loading="guardandoDetalle" label="Guardar" @click="guardarDetalle" />
            </div>
        </Dialog>
    </section>
</template>





