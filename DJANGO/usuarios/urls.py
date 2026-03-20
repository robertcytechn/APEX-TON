from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RolViewSet, PermisoViewSet, UsuarioViewSet, RolPermisoViewSet, UsuarioRolViewSet

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='rol')
router.register(r'permisos', PermisoViewSet, basename='permiso')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'rol-permisos', RolPermisoViewSet, basename='rolpermiso')
router.register(r'usuario-roles', UsuarioRolViewSet, basename='usuariorol')

urlpatterns = [
    path('', include(router.urls)),
]
