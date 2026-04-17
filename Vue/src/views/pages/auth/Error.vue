<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 min-h-screen flex items-center justify-center p-4">
        <section class="w-full max-w-xl rounded-3xl border border-red-200 dark:border-red-900 bg-surface-0 dark:bg-surface-900 p-8 text-center shadow-xl">
            <div class="mx-auto mb-5 h-16 w-16 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center">
                <i class="pi pi-exclamation-triangle text-3xl text-red-500"></i>
            </div>
            <h1 class="text-3xl font-bold text-surface-900 dark:text-surface-0">Error del sistema</h1>
            <p class="mt-3 text-surface-600 dark:text-surface-300">
                Ocurrió un problema inesperado. Intenta nuevamente o reporta el incidente.
            </p>

            <div class="mt-6 rounded-xl border border-surface-200 dark:border-surface-700 p-4 text-left text-sm">
                <p class="font-medium mb-2">Sugerencias rápidas:</p>
                <ul class="space-y-2 text-surface-600 dark:text-surface-300">
                    <li class="flex items-center gap-2"><i class="pi pi-refresh"></i> Recarga la página y vuelve a intentar.</li>
                    <li class="flex items-center gap-2"><i class="pi pi-clock"></i> Verifica si fue fuera de horario operativo.</li>
                    <li class="flex items-center gap-2"><i class="pi pi-send"></i> Contacta soporte si persiste.</li>
                </ul>
            </div>

            <Button class="mt-8" label="Ir al inicio" icon="pi pi-home" as="router-link" to="/" severity="danger" />
        </section>
    </div>
</template>

