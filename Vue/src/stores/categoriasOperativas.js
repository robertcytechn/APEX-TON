import { defineStore } from 'pinia';
import { listarCategoriasOperativas } from '@/service/capturaOperativaServicio';

// 1) Para qué sirve: normalizar tipo de categoría para escoger iconografía consistente.
// 2) Cómo funciona: limpia y convierte a mayúsculas el texto recibido.
// 3) Qué hace: evita errores de comparación al construir rutas del menú operativo.
// 4) Cómo editarla: amplía normalización si backend comienza a mandar variantes de tipo.
function normalizarRol(nombreRol) {
    return (nombreRol || '').trim().toUpperCase();
}

// 1) Para qué sirve: administrar categorías operativas activas disponibles para captura.
// 2) Cómo funciona: carga desde API, filtra por estado ACTIVO y genera rutas derivadas.
// 3) Qué hace: alimenta menú y redirección inicial del flujo operativo.
// 4) Cómo editarla: cambia criterios de orden/filtro en cargarCategoriasActivas.
export const useCategoriasOperativasStore = defineStore('categoriasOperativas', {
    state: () => ({
        categoriasActivas: [],
        cargando: false,
        cargadas: false
    }),
    actions: {
        async cargarCategoriasActivas(forzar = false) {
            if (this.cargando) {
                return;
            }
            if (this.cargadas && !forzar) {
                return;
            }

            this.cargando = true;
            try {
                const { data } = await listarCategoriasOperativas();
                const categorias = Array.isArray(data?.data) ? data.data : [];
                this.categoriasActivas = categorias
                    .filter((categoria) => categoria.estado === 'ACTIVO')
                    .sort((a, b) => (a.orden || 0) - (b.orden || 0));
                this.cargadas = true;
            } finally {
                this.cargando = false;
            }
        },
        limpiar() {
            this.categoriasActivas = [];
            this.cargadas = false;
            this.cargando = false;
        }
    },
    getters: {
        rutasCapturaOperativa: (state) => state.categoriasActivas.map((categoria) => ({
            id: categoria.id,
            nombreRuta: `operativo-categoria-${categoria.id}`,
            ruta: `/operativo/${categoria.id}`,
            etiqueta: categoria.nombre,
            icono: normalizarRol(categoria.tipo) === 'INGRESO' ? 'pi pi-arrow-down-left' : normalizarRol(categoria.tipo) === 'EGRESO' ? 'pi pi-arrow-up-right' : 'pi pi-arrows-v'
        }))
    }
});
