# FastAPI Users API

API REST construida con FastAPI, PostgreSQL, Redis, SQLAlchemy, Alembic, JWT, refresh tokens, recuperación de contraseña, auditoría, rate limiting y CORS.

## Funcionalidades principales

- Registro de usuarios.
- Login con JWT.
- Refresh tokens.
- Logout.
- Logout de todos los dispositivos.
- Perfil del usuario autenticado.
- Actualización de perfil.
- Cambio de contraseña.
- Eliminación lógica de cuenta.
- Recuperación de contraseña.
- Auditoría de eventos.
- Rate limiting.
- CORS para frontend.

---

## Requisitos

Antes de iniciar, necesitas tener instalado:

- Python
- Docker
- Docker Compose
- Git

Verificar versiones:

```powershell
python --version
docker --version
docker compose version
git --version
```

---

## Instalación

Clonar el proyecto:

```powershell
git clone URL_DEL_REPOSITORIO
cd fastapi
```

Crear entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

---

## Variables de entorno

Crear el archivo `.env` copiando el ejemplo:

```powershell
copy .env.example .env
```

El archivo `.env` debe contener valores como estos:

```env
APP_NAME=FastAPI Users API
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://fastapi_user:fastapi_password@127.0.0.1:5433/fastapi_db

JWT_SECRET_KEY=change_this_super_secret_key_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

PASSWORD_MIN_LENGTH=8
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30

DB_REQUIRED_ON_STARTUP=false

RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
RATE_LIMIT_REGISTER=5/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_FORGOT_PASSWORD=3/hour

BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

Importante:

No subir `.env` al repositorio.

---

## Levantar PostgreSQL y Redis

Levantar los contenedores:

```powershell
docker compose up -d
```

Ver contenedores activos:

```powershell
docker ps
```

Debes ver algo parecido a:

```txt
postgres_db
redis_cache
```

PostgreSQL debe estar expuesto en:

```txt
5433 -> 5432
```

Redis debe estar expuesto en:

```txt
6379 -> 6379
```

---

## Verificar PostgreSQL

Entrar a PostgreSQL:

```powershell
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db
```

Dentro de PostgreSQL:

```sql
SELECT 1;
\q
```

---

## Verificar Redis

```powershell
docker exec -it redis_cache redis-cli ping
```

Debe responder:

```txt
PONG
```

---

## Ejecutar migraciones

Crear una migración nueva, solo si cambiaste modelos:

```powershell
python -m alembic revision --autogenerate -m "mensaje de migracion"
```

Aplicar migraciones:

```powershell
python -m alembic upgrade head
```

Verificar tablas:

```powershell
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db
```

Dentro:

```sql
\dt
\q
```

Tablas esperadas:

```txt
users
password_reset_tokens
refresh_tokens
audit_logs
alembic_version
```

---

## Ejecutar servidor

```powershell
python -m uvicorn app.main:app --reload
```

Abrir documentación Swagger:

```txt
http://localhost:8000/docs
```

Health check:

```txt
http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "environment": "development"
}
```

---

## Endpoints principales

### Auth

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout-all
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

### Usuario autenticado

```http
GET    /api/v1/users/me
PATCH  /api/v1/users/me
PATCH  /api/v1/users/me/password
DELETE /api/v1/users/me
```

---

## Uso básico de la API

### Register

```http
POST /api/v1/auth/register
```

Body:

```json
{
  "email": "user@example.com",
  "username": "userdemo",
  "first_name": "Demo",
  "last_name": "User",
  "password": "Password123!"
}
```

Respuesta esperada:

```json
{
  "id": "...",
  "email": "user@example.com",
  "username": "userdemo",
  "first_name": "Demo",
  "last_name": "User",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "..."
}
```

---

### Login

El login usa formulario OAuth2.

En Swagger, pulsa `Authorize` o usa el endpoint `/login`.

Campos:

```txt
username = user@example.com
password = Password123!
```

Respuesta esperada:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

---

### Obtener perfil

```http
GET /api/v1/users/me
```

Header:

```http
Authorization: Bearer ACCESS_TOKEN
```

Respuesta esperada:

```json
{
  "id": "...",
  "email": "user@example.com",
  "username": "userdemo",
  "first_name": "Demo",
  "last_name": "User",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "..."
}
```

---

### Actualizar perfil

```http
PATCH /api/v1/users/me
```

Header:

```http
Authorization: Bearer ACCESS_TOKEN
```

Body:

```json
{
  "first_name": "Eric",
  "last_name": "Prueba"
}
```

---

### Cambiar contraseña

```http
PATCH /api/v1/users/me/password
```

Header:

```http
Authorization: Bearer ACCESS_TOKEN
```

Body:

```json
{
  "current_password": "Password123!",
  "new_password": "NewPassword123!"
}
```

Después del cambio, el login con la contraseña anterior debe fallar.

---

### Eliminar cuenta

```http
DELETE /api/v1/users/me
```

Header:

```http
Authorization: Bearer ACCESS_TOKEN
```

Respuesta esperada:

```http
204 No Content
```

---

## Refresh token

```http
POST /api/v1/auth/refresh
```

Body:

```json
{
  "refresh_token": "REFRESH_TOKEN"
}
```

Respuesta esperada:

```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "refresh_token": "NEW_REFRESH_TOKEN",
  "token_type": "bearer"
}
```

Importante:

Al usar `/refresh`, el refresh token anterior queda revocado y debes usar el nuevo.

---

## Logout

```http
POST /api/v1/auth/logout
```

Body:

```json
{
  "refresh_token": "REFRESH_TOKEN"
}
```

Respuesta esperada:

```json
{
  "message": "Sesión cerrada correctamente"
}
```

---

## Logout all

```http
POST /api/v1/auth/logout-all
```

Header:

```http
Authorization: Bearer ACCESS_TOKEN
```

Respuesta esperada:

```json
{
  "message": "Todas las sesiones fueron cerradas correctamente"
}
```

---

## Forgot password

```http
POST /api/v1/auth/forgot-password
```

Body:

```json
{
  "email": "user@example.com"
}
```

Respuesta esperada siempre igual:

```json
{
  "message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"
}
```

En desarrollo, el token puede aparecer en la consola del servidor.

---

## Reset password

```http
POST /api/v1/auth/reset-password
```

Body:

```json
{
  "token": "TOKEN_DE_RECUPERACION",
  "new_password": "NewPassword123!"
}
```

Respuesta esperada:

```json
{
  "message": "Contraseña actualizada correctamente"
}
```

---

## Ejecutar tests

```powershell
pytest
```

Con más detalle:

```powershell
pytest -v
```

---

## Rate limiting

Endpoints protegidos:

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/forgot-password
```

Configuración:

```env
RATE_LIMIT_REGISTER=5/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_FORGOT_PASSWORD=3/hour
```

Si se supera el límite:

```http
429 Too Many Requests
```

Para limpiar Redis en desarrollo:

```powershell
docker exec -it redis_cache redis-cli FLUSHDB
```

---

## CORS

Origins permitidos:

```env
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

Para probar CORS sin frontend real puedes crear un HTML simple y servirlo con:

```powershell
python -m http.server 5173
```

---

## Auditoría

Eventos registrados:

```txt
user.created
user.updated
user.deleted
auth.login.success
auth.login.failed
password.changed
password.reset.requested
password.reset.completed
role.changed
```

Consultar auditoría:

```powershell
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db
```

```sql
SELECT event_type, metadata, created_at
FROM audit_logs
ORDER BY created_at DESC;
```

---

## Comandos útiles

Levantar servicios:

```powershell
docker compose up -d
```

Apagar servicios:

```powershell
docker compose down
```

Apagar y borrar datos de desarrollo:

```powershell
docker compose down -v
```

Ejecutar servidor:

```powershell
python -m uvicorn app.main:app --reload
```

Crear migración:

```powershell
python -m alembic revision --autogenerate -m "mensaje"
```

Aplicar migraciones:

```powershell
python -m alembic upgrade head
```

Ejecutar tests:

```powershell
pytest
```

Limpiar Redis:

```powershell
docker exec -it redis_cache redis-cli FLUSHDB
```

Entrar a PostgreSQL:

```powershell
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db
```

---

## Seguridad

- No subir `.env`.
- Cambiar `JWT_SECRET_KEY` en producción.
- No guardar contraseñas en texto plano.
- No devolver `hashed_password`.
- No guardar refresh tokens en texto plano.
- No guardar reset tokens en texto plano.
- Usar HTTPS en producción.
- No usar CORS con `*` en producción.
- Desactivar `DEBUG` en producción.