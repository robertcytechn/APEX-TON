<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSesionStore } from '@/stores/sesion';

const identificador = ref('');
const contrasena = ref('');
const errorLogin = ref('');

const ruta = useRoute();
const enrutador = useRouter();
const sesionStore = useSesionStore();

identificador.value = sesionStore.ultimoIdentificador || '';

const enviarFormulario = async () => {
    errorLogin.value = '';
    const resultado = await sesionStore.iniciarSesion({
        identificador: identificador.value,
        password: contrasena.value
    });

    if (!resultado.ok) {
        errorLogin.value = resultado.mensaje || 'No se pudo iniciar sesión.';
        return;
    }

    await enrutador.push(ruta.query.redirect || '/');
};
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 min-h-screen w-full flex items-center justify-center p-4">
        <div
            class="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 overflow-hidden rounded-3xl border border-surface-200 dark:border-surface-800 shadow-2xl">
            <aside
                class="bg-gradient-to-br from-primary-500 to-primary-700 p-8 lg:p-10 text-white flex flex-col justify-between">
                <div>
                    <span class="inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-1 text-sm">
                        <i class="pi pi-wallet"></i>
                        Plataforma de tesorería
                    </span>
                    <h1 class="text-3xl lg:text-4xl font-bold mt-6">BinsurMX</h1>
                    <p class="mt-4 text-white/90 leading-relaxed">
                        Gestión centralizada de tesorería con control de acceso por rol, trazabilidad operativa y
                        análisis financiero en tiempo real.
                    </p>
                </div>
                <ul class="space-y-3 text-sm mt-8">
                    <li class="flex items-center gap-2"><i class="pi pi-shield"></i> Control de acceso seguro</li>
                    <li class="flex items-center gap-2"><i class="pi pi-wallet"></i> Control de operaciones diarias</li>
                    <li class="flex items-center gap-2"><i class="pi pi-chart-line"></i> Reportes financieros en tiempo
                        real</li>
                </ul>
            </aside>

            <section class="bg-surface-0 dark:bg-surface-900 p-8 lg:p-10">
                <div class="flex items-center gap-2 text-primary mb-4">
                    <i class="pi pi-shield text-xl"></i>
                    <span class="font-semibold">Acceso institucional</span>
                </div>
                <h2 class="text-2xl font-semibold text-surface-900 dark:text-surface-0">Iniciar sesión</h2>
                <p class="text-surface-600 dark:text-surface-300 mt-2 mb-8">Ingresa tus credenciales de acceso para
                    continuar.</p>

                <form class="space-y-5" @submit.prevent="enviarFormulario">
                    <div>
                        <label for="identificador" class="block text-sm font-medium mb-2">
                            <i class="pi pi-user mr-1 text-primary"></i>
                            Usuario o correo electrónico <span class="text-red-500">*</span>
                        </label>
                        <IconField>
                            <InputIcon class="pi pi-user" />
                            <InputText id="identificador" v-model="identificador" type="text" class="w-full"
                                placeholder="Usuario o correo electrónico" />
                        </IconField>
                    </div>

                    <div>
                        <label for="contrasena" class="block text-sm font-medium mb-2">
                            <i class="pi pi-lock mr-1 text-primary"></i>
                            Contraseña <span class="text-red-500">*</span>
                        </label>
                        <Password id="contrasena" v-model="contrasena" :feedback="false" toggleMask fluid
                            placeholder="Contraseña de acceso" />
                    </div>

                    <small v-if="errorLogin" class="block text-red-500">{{ errorLogin }}</small>

                    <Button :loading="sesionStore.cargandoSesion" type="submit" label="Iniciar sesión"
                        icon="pi pi-sign-in" class="w-full" />
                </form>
            </section>
        </div>
    </div>
</template>
