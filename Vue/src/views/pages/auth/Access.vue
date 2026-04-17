<script setup>
import FloatingConfigurator from '@/components/FloatingConfigurator.vue';
</script>

<template>
    <FloatingConfigurator />
    <div class="bg-surface-50 dark:bg-surface-950 min-h-screen flex items-center justify-center p-4">
        <section class="w-full max-w-xl rounded-3xl border border-orange-200 dark:border-orange-900 bg-surface-0 dark:bg-surface-900 p-8 text-center shadow-xl">
            <div class="mx-auto mb-5 h-16 w-16 rounded-full bg-orange-100 dark:bg-orange-950 flex items-center justify-center">
                <i class="pi pi-lock text-3xl text-orange-500"></i>
            </div>
            <h1 class="text-3xl font-bold text-surface-900 dark:text-surface-0">Acceso no autorizado</h1>
            <p class="mt-3 text-surface-600 dark:text-surface-300">
                Tu rol actual no cuenta con permisos para entrar a esta seccion.
            </p>

            <div class="mt-6 grid gap-3 text-left text-sm">
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-3 flex items-center gap-3">
                    <i class="pi pi-user text-primary"></i>
                    <span>Solicita acceso con un administrador del sistema.</span>
                </div>
                <div class="rounded-xl border border-surface-200 dark:border-surface-700 p-3 flex items-center gap-3">
                    <i class="pi pi-shield text-primary"></i>
                    <span>Verifica tu rol y los permisos asignados.</span>
                </div>
            </div>

            <Button class="mt-8" label="Volver al inicio" icon="pi pi-home" as="router-link" to="/" severity="warn" />
        </section>
    </div>
</template>

