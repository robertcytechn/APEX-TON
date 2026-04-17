<script setup>
import { useToast } from 'primevue/usetoast';
import { registrarInstanciaToastApi } from '@/service/notificacionesApi';

const toast = useToast();
registrarInstanciaToastApi(toast);
</script>

<template>
    <Toast />
    <router-view />
</template>

<style scoped></style>
