<script setup>
import CatalogoOperativoAdmin from '@/views/admin/CatalogoOperativoAdmin.vue';
</script>

<template>
    <section class="space-y-6">
        <div class="card border-0 bg-gradient-to-r from-slate-50 to-cyan-50">
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Cabina Director: Catálogo Operativo</h1>
                    <p class="text-sm text-surface-600 mt-1">
                        Gestión integral de categorías, conceptos y detalles parametrizados con enfoque más claro para captura y seguimiento operativo.
                    </p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <Tag value="Director" severity="info" />
                    <Tag value="Ingreso/Egreso" severity="success" />
                    <Tag value="Móvil primero" severity="contrast" />
                </div>
            </div>
        </div>

        <CatalogoOperativoAdmin />
    </section>
</template>
