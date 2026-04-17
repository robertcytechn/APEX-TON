import { defineStore } from 'pinia';
import { actualizarMiConfiguracionUsuario, obtenerMiConfiguracionUsuario } from '@/service/configuracionUsuarioServicio';
import { aplicarTemaPrime } from '@/layout/composables/temaPrime';

// 1) Para qué sirve: traducir colores Prime a una etiqueta de acento simplificada.
// 2) Cómo funciona: mapea familias de color a etiquetas de negocio en español.
// 3) Qué hace: guarda una preferencia legible para auditoría/configuración de UI.
// 4) Cómo editarla: agrega nuevos colores conforme se expandan presets del tema.
function mapearColorAcento(colorPrime) {
    if (['emerald', 'green', 'lime', 'teal'].includes(colorPrime)) return 'verde';
    if (['orange', 'amber', 'yellow'].includes(colorPrime)) return 'naranja';
    if (['red', 'rose', 'pink', 'fuchsia'].includes(colorPrime)) return 'rojo';
    if (['cyan'].includes(colorPrime)) return 'cyan';
    if (['violet', 'purple'].includes(colorPrime)) return 'morado';
    return 'azul';
}

// 1) Para qué sirve: construir payload visual persistible a nivel usuario.
// 2) Cómo funciona: toma layoutConfig y empaqueta tema, acento y preferencias extra.
// 3) Qué hace: define la estructura enviada al backend en cada guardado visual.
// 4) Cómo editarla: añade nuevos campos visuales en este payload cuando la UI crezca.
function obtenerPayloadVisual(layoutConfig) {
    return {
        tema: layoutConfig.darkTheme ? 'oscuro' : 'claro',
        color_acento: mapearColorAcento(layoutConfig.primary),
        preferencias_extra: {
            ui_prime: {
                preset: layoutConfig.preset,
                primary: layoutConfig.primary,
                surface: layoutConfig.surface,
                menu_mode: layoutConfig.menuMode,
                dark_theme: layoutConfig.darkTheme
            }
        }
    };
}

// 1) Para qué sirve: sincronizar preferencias visuales entre backend, layout y pinia.
// 2) Cómo funciona: carga config, aplica tema y programa guardado con debounce.
// 3) Qué hace: mantiene experiencia consistente entre sesiones del usuario.
// 4) Cómo editarla: ajusta temporizador y acciones al incorporar nuevas preferencias.
export const usePreferenciasUsuarioStore = defineStore('preferenciasUsuario', {
    state: () => ({
        configuracion: null,
        guardando: false,
        temporizadorGuardado: null
    }),
    actions: {
        aplicarConfiguracionVisual(layoutConfig) {
            const uiPrime = this.configuracion?.preferencias_extra?.ui_prime;
            if (!uiPrime) {
                return;
            }

            if (uiPrime.preset) layoutConfig.preset = uiPrime.preset;
            if (uiPrime.primary) layoutConfig.primary = uiPrime.primary;
            if (Object.prototype.hasOwnProperty.call(uiPrime, 'surface')) layoutConfig.surface = uiPrime.surface;
            if (uiPrime.menu_mode) layoutConfig.menuMode = uiPrime.menu_mode;
            if (typeof uiPrime.dark_theme === 'boolean') {
                layoutConfig.darkTheme = uiPrime.dark_theme;
            }

            aplicarTemaPrime(layoutConfig);
        },
        async cargarConfiguracionUsuario(layoutConfig) {
            const { data } = await obtenerMiConfiguracionUsuario();
            this.configuracion = data.data;
            this.aplicarConfiguracionVisual(layoutConfig);
        },
        async guardarConfiguracionVisual(layoutConfig) {
            this.guardando = true;
            try {
                const payload = obtenerPayloadVisual(layoutConfig);
                const { data } = await actualizarMiConfiguracionUsuario(payload);
                this.configuracion = data.data;
            } finally {
                this.guardando = false;
            }
        },
        programarGuardadoVisual(layoutConfig) {
            if (this.temporizadorGuardado) {
                clearTimeout(this.temporizadorGuardado);
            }
            this.temporizadorGuardado = setTimeout(() => {
                this.guardarConfiguracionVisual(layoutConfig);
            }, 450);
        }
    }
});
