# Frontend React - Login Sprint 1

## Objetivo
Levantar un frontend React para login de usuarios SIPAR (admin y operador) conectado al backend principal.

## Rutas
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Vehicle Exit Service: http://localhost:8010
- Vehicle Entry Service: http://localhost:8011
- Endpoint login: POST /api/users/login

## Levantar con Docker
Desde `src` ejecutar:

```bash
docker compose up --build db backend frontend vehicle-exit-service vehicle-entry-service
```

Luego abrir:
- http://localhost:5173

## Credenciales de prueba
El backend crea o reconcilia automaticamente 2 usuarios al iniciar:

- Admin:
	- usuario: `admin`
	- password: `Admin1234`
- Operador (rol `vigilante`):
	- usuario: `operador`
	- password: `Operador1234`

Variables opcionales para personalizar:
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_NOMBRE`
- `OPERATOR_USERNAME`, `OPERATOR_PASSWORD`, `OPERATOR_NOMBRE`
- `DEFAULT_USERS_BOOTSTRAP_ENABLED` (default `true`)
- `DEFAULT_USERS_FORCE_PASSWORD_RESET` (default `true`)

## Criterios cubiertos
- Inicio de sesion exitoso con rol administrador.
- Inicio de sesion exitoso con rol operador (rol vigilante mostrado como Operador).
- Bloqueo de acceso ante credenciales incorrectas (mensaje de error en UI).

## Nota tecnica
El frontend no consume URL absoluta del backend. Usa `/api/*` y Nginx hace proxy interno a `backend:8000`.
