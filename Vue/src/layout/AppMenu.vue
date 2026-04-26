<script setup>
import { useCategoriasOperativasStore } from '@/stores/categoriasOperativas';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted } from 'vue';
import AppMenuItem from './AppMenuItem.vue';

const sesionStore = useSesionStore();
const categoriasOperativasStore = useCategoriasOperativasStore();

onMounted(async () => {
    if (sesionStore.estaAutenticado && sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE'])) {
        await categoriasOperativasStore.cargarCategoriasActivas();
    }
});

const model = computed(() => {
    const itemsPrincipal = [
        {
            label: 'Inicio',
            icon: 'pi pi-fw pi-home',
            to: '/'
        },
        {
            label: 'Estado de resultados',
            icon: 'pi pi-fw pi-chart-line',
            to: '/reportes/estado-resultados'
        },
        {
            label: 'Reporte diario',
            icon: 'pi pi-fw pi-calendar',
            to: '/reportes/reporte-diario'
        },
        {
            label: 'Días contables',
            icon: 'pi pi-fw pi-calendar-plus',
            to: '/reportes/dias-contables'
        }
    ];

    if (sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO'])) {
        itemsPrincipal.push({
            label: 'Estadísticas',
            icon: 'pi pi-fw pi-chart-bar',
            to: '/reportes/estadisticas'
        });

        itemsPrincipal.push({
            label: 'Captura operativa detallada',
            icon: 'pi pi-fw pi-table',
            to: '/director/consulta-captura-operativa'
        });
    }

    const menuBase = [
        {
            label: 'Principal',
            visiblePara: ['AUTENTICADO'],
            items: itemsPrincipal
        },
        {
            label: 'Soporte',
            path: '/pages',
            visiblePara: ['AUTENTICADO'],
            items: [
                {
                    label: 'Soporte técnico',
                    icon: 'pi pi-fw pi-headphones',
                    to: '/pages/soporte-tecnico'
                }
            ]
        }
    ];

    if (sesionStore.cumpleAlgunoRoles(['ADMINISTRADOR', 'DIRECTOR'])) {
        const itemsAuditoria = [];

        if (sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR'])) {
            itemsAuditoria.push({
                label: 'Auditoría de movimientos',
                icon: 'pi pi-fw pi-history',
                to: '/admin/auditoria-movimientos'
            });
        }

        if (itemsAuditoria.length > 0) {
            menuBase.splice(1, 0, {
                label: 'Auditoría y Control',
                path: '/admin',
                visiblePara: ['DIRECTOR', 'ADMINISTRADOR'],
                items: itemsAuditoria
            });
        }
    }

    if (sesionStore.cumpleAlgunoRoles(['ADMINISTRADOR'])) {
        menuBase.splice(2, 0, {
            label: 'Administración del sistema',
            path: '/admin',
            visiblePara: ['ADMINISTRADOR'],
            items: [
                {
                    label: 'Usuarios',
                    icon: 'pi pi-fw pi-users',
                    to: '/admin/usuarios'
                },
                {
                    label: 'Roles',
                    icon: 'pi pi-fw pi-shield',
                    to: '/admin/roles'
                },
                {
                    label: 'Sucursales',
                    icon: 'pi pi-fw pi-building',
                    to: '/admin/sucursales'
                },
                {
                    label: 'Config. globales',
                    icon: 'pi pi-fw pi-cog',
                    to: '/admin/configuraciones-globales'
                },
                {
                    label: 'Centro de control',
                    icon: 'pi pi-fw pi-bolt',
                    to: '/admin/centro-control'
                },
                {
                    label: 'Tickets de soporte',
                    icon: 'pi pi-fw pi-ticket',
                    to: '/admin/soporte-tecnico'
                },
                {
                    label: 'Rubros contables',
                    icon: 'pi pi-fw pi-list-check',
                    to: '/admin/rubros-contables'
                },
                {
                    label: 'Padres de rubros',
                    icon: 'pi pi-fw pi-sitemap',
                    to: '/admin/padres-rubros-contables'
                },
                {
                    label: 'Catálogo operativo',
                    icon: 'pi pi-fw pi-table',
                    to: '/admin/catalogo-operativo'
                }
            ]
        });
    }

    if (sesionStore.cumpleAlgunoRoles(['DIRECTOR'])) {
        menuBase.splice(1, 0, {
            label: 'Panel directivo',
            path: '/director',
            visiblePara: ['DIRECTOR'],
            items: [
                {
                    label: 'Sucursales',
                    icon: 'pi pi-fw pi-building',
                    to: '/director/sucursales'
                },
                {
                    label: 'Usuarios operativos',
                    icon: 'pi pi-fw pi-users',
                    to: '/director/usuarios'
                },
                {
                    label: 'Config. globales',
                    icon: 'pi pi-fw pi-cog',
                    to: '/director/configuraciones-globales'
                },
                {
                    label: 'Rubros contables',
                    icon: 'pi pi-fw pi-list-check',
                    to: '/director/rubros-contables'
                },
                {
                    label: 'Catálogo operativo',
                    icon: 'pi pi-fw pi-table',
                    to: '/director/catalogo-operativo'
                }
            ]
        });
    }

    if (sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE'])) {
        const itemsCategorias = categoriasOperativasStore.rutasCapturaOperativa.map((ruta) => ({
            label: ruta.etiqueta,
            icon: ruta.icono,
            to: ruta.ruta
        }));

        menuBase.splice(1, 0, {
            label: 'Captura operativa',
            path: '/operativo',
            visiblePara: ['CONTADOR', 'GERENTE'],
            items: itemsCategorias.length
                ? itemsCategorias
                : [{ label: 'Sin categorías activas', icon: 'pi pi-info-circle', to: '/operativo' }]
        });
    }

    return menuBase.filter((item) => sesionStore.cumpleAlgunoRoles(item.visiblePara || ['AUTENTICADO']));
});

// Menu corto de referencia para altas o bajas rapidas:
// const menuCorto = [
//     { label: 'Principal', items: [{ label: 'Inicio', icon: 'pi pi-home', to: '/' }] },
//     { label: 'Acceso', items: [{ label: 'Iniciar sesión', icon: 'pi pi-sign-in', to: '/auth/login' }] }
// ];

// Menu completo de referencia:
// const menuCompleto = [
//     {
//         label: 'Tesoreria',
//         items: [
//             { label: 'Estado de resultados', icon: 'pi pi-chart-line', to: '/admin/estado-resultados' },
//             { label: 'Fondos fijos', icon: 'pi pi-wallet', to: '/admin/fondos-fijos' },
//             { label: 'Rubro contable', icon: 'pi pi-list-check', to: '/admin/rubro-contable' }
//         ]
//     },
//     {
//         label: 'Seguridad',
//         items: [
//             { label: 'Usuarios', icon: 'pi pi-users', to: '/admin/usuarios' },
//             { label: 'Roles y permisos', icon: 'pi pi-shield', to: '/admin/roles' }
//         ]
//     }
// ];
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item.label">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>
