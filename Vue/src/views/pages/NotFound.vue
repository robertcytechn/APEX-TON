<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 min-h-screen flex items-center justify-center p-4">
        <section class="w-full max-w-2xl rounded-3xl border border-surface-200 dark:border-surface-800 bg-surface-0 dark:bg-surface-900 p-8 shadow-xl text-center">
            <div class="inline-flex items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/40 px-4 py-1 text-primary text-sm font-medium mb-4">
                <i class="pi pi-map"></i>
                Error 404
            </div>
            <h1 class="text-3xl lg:text-4xl font-bold text-surface-900 dark:text-surface-0">Página no encontrada</h1>
            <p class="mt-3 text-surface-600 dark:text-surface-300">
                La ruta que intentas abrir no existe o fue movida.
            </p>

            <div class="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4">
                    <i class="pi pi-home text-primary text-xl mb-2"></i>
                    <p>Volver al inicio</p>
                </div>
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4">
                    <i class="pi pi-search text-primary text-xl mb-2"></i>
                    <p>Revisar la URL</p>
                </div>
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-4">
                    <i class="pi pi-phone text-primary text-xl mb-2"></i>
                    <p>Contactar soporte</p>
                </div>
            </div>

            <Button class="mt-8" label="Regresar al inicio" icon="pi pi-arrow-left" as="router-link" to="/" />
        </section>
    </div>
</template>

