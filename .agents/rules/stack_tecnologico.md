# Stack tecnologico oficial (APEX-TON)

## 1) Estructura por carpeta

- Backend: `DJANGO\`
- Frontend: `Vue\`
- Documentacion tecnica/funcional: `docs\backend\`
- Configuracion de agentes: `.agents\`

## 2) Backend actual

- Python: 3.13 (objetivo del proyecto y docs tecnicas)
- Django: rama 6.x (el proyecto fue generado con Django 6.0.3)
- API: Django REST Framework
- Base de datos: MySQL
- Tareas programadas y asincronas: Celery + django-celery-beat
- Historial/auditoria: django-simple-history
- Auth de API: SessionAuthentication (sin JWT)

## 3) Frontend actual

- Vue: 3.4.x
- Build tool: Vite 8.x
- Estado global: Pinia 3.x
- HTTP client: Axios 1.x
- UI: PrimeVue 4.x + PrimeIcons + tema Sakai
- CSS utility: Tailwind CSS 4.x

## 4) Reglas de actualizacion de stack

- No fijar versiones inventadas en reglas; usar versiones reales del repo.
- Si cambia una version mayor del stack, actualizar este archivo y los workflows afectados.
