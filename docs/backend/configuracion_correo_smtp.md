# Configuracion de correo saliente en Django (SMTP)

Esta guia deja preparado el backend para enviar emails con la cuenta:

- Usuario SMTP: robertot@gbentretenimiento.com

## 1) Archivo de entorno

En la carpeta DJANGO ya existe un archivo de ejemplo:

- DJANGO/.env.example

Crear un archivo DJANGO/.env con ese mismo contenido y completar la clave real cuando se entregue:

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USE_TLS=true
DJANGO_EMAIL_USE_SSL=false
DJANGO_EMAIL_HOST_USER=robertot@gbentretenimiento.com
DJANGO_EMAIL_HOST_PASSWORD=CLAVE_DE_APLICACION_DE_GOOGLE
DJANGO_EMAIL_TIMEOUT=20
DJANGO_DEFAULT_FROM_EMAIL=robertot@gbentretenimiento.com
DJANGO_SERVER_EMAIL=robertot@gbentretenimiento.com
```

Notas:
- Para Google Workspace / Gmail, usar clave de aplicacion de 16 caracteres (sin espacios).
- El archivo DJANGO/.env se ignora en git para no exponer secretos.
- El backend carga automaticamente DJANGO/.env al iniciar Django.

## 2) Reiniciar backend

Despues de guardar la clave, reiniciar el servidor Django para recargar variables.

## 3) Prueba rapida de envio

Desde la carpeta DJANGO, ejecutar:

```powershell
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Prueba SMTP APEX-TON', 'Correo de prueba enviado desde Django.', None, ['robertot@gbentretenimiento.com'], fail_silently=False)"
```

Si no hay error, la configuracion esta activa.
