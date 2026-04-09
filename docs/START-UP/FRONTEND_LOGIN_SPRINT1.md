# Frontend React - Login Sprint 1

## Objetivo
Levantar un frontend React para login de usuarios SIPAR (admin y operador) conectado al backend principal.

## Rutas
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Endpoint login: POST /api/users/login

## Levantar con Docker
Desde `src` ejecutar:

```bash
docker compose up --build db backend frontend
```

Luego abrir:
- http://localhost:5173

## Credenciales de prueba
### Admin bootstrap
Definir variable de entorno antes de levantar:
- `ADMIN_PASSWORD=tu_clave_segura`

Usuario por defecto:
- usuario: `admin`
- password: valor de `ADMIN_PASSWORD`

### Operador (vigilante)
Crear desde backend con un admin autenticado usando POST /api/users con rol `vigilante`.

## Criterios cubiertos
- Inicio de sesion exitoso con rol administrador.
- Inicio de sesion exitoso con rol operador (rol vigilante mostrado como Operador).
- Bloqueo de acceso ante credenciales incorrectas (mensaje de error en UI).

## Nota tecnica
El frontend no consume URL absoluta del backend. Usa `/api/*` y Nginx hace proxy interno a `backend:8000`.
