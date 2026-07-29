# FastAPI CI/CD Pipeline API

API REST construida con **FastAPI**, **PostgreSQL**, **Redis**, **SQLAlchemy**, **Alembic**, **Docker** e **Infobip**.

Cubre gestión completa de usuarios con autenticación JWT, gestión de repositorios Git, ejecución de tests en contenedores Docker aislados, análisis de resultados JUnit y envío automático de reportes HTML por correo electrónico.

---

## Funcionalidades

### 👤 Identidad y Autenticación
- Registro de usuarios
- Login con JWT (access token + refresh token)
- Refresh y rotación de tokens
- Logout y logout de todos los dispositivos
- Perfil del usuario autenticado (lectura y actualización)
- Cambio de contraseña autenticado
- Recuperación de contraseña por email
- Eliminación lógica de cuenta
- Auditoría de eventos

### 📁 Gestión de Repositorios
- Crear, listar, actualizar, eliminar repositorios
- Clonar repositorios remotos (credenciales cifradas con Fernet)
- Actualizar un repositorio desde el remoto
- Clonar hacia una ruta diferente (clone alternativo)

### 🔁 Verificación de Cambios y Tests
- Detectar cambios locales y remotos en el repositorio clonado
- Ejecutar tests unitarios automáticamente cuando hay cambios
- Ejecución aislada en un contenedor Docker efímero
- Detección automática del gestor de paquetes del repo (`install-deps`: Poetry / pip / pyproject.toml)
- Generación y parseo de reporte **JUnit XML** (`pytest --junitxml`)
- Almacenamiento de resultados estructurados por ejecución

### 📧 Reportes por Email (Infobip)
- Envío automático de reporte HTML tras cada ejecución de tests
- Reporte con diseño premium en modo oscuro:
  - Información del commit (rama, autor, mensaje, ID)
  - Contadores: Total · Exitosos · Fallidos · Errores · Omitidos · Duración
  - Tabla detallada por test con estado coloreado
  - Sección de stderr si hay errores
- Rate limiting configurable para no saturar el dominio
- Soporte para múltiples destinatarios

---

## Requisitos

- Python 3.12+
- Docker Desktop
- Git

```powershell
python --version
docker --version
git --version
```

---

## Instalación

```powershell
git clone https://github.com/ericperezz/fastapi.git
cd fastapi
```

Crear entorno virtual e instalar dependencias:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Variables de entorno

Copiar el ejemplo:

```powershell
copy .env.example .env
```

Editar `.env` con los valores de tu entorno. Referencia completa:

```env
# ── Aplicación ──────────────────────────────────────────
APP_NAME=FastAPI Users API
APP_ENV=development
DEBUG=true

# ── Base de datos ────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://fastapi_user:fastapi_password@127.0.0.1:5433/fastapi_db
DB_REQUIRED_ON_STARTUP=false

# ── JWT ──────────────────────────────────────────────────
JWT_SECRET_KEY=change_this_super_secret_key_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Contraseñas ──────────────────────────────────────────
PASSWORD_MIN_LENGTH=8
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30

# ── Rate Limiting (Redis) ────────────────────────────────
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
RATE_LIMIT_REGISTER=5/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_FORGOT_PASSWORD=3/hour

# ── CORS ─────────────────────────────────────────────────
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ── Repositorios ─────────────────────────────────────────
FERNET_SECRET_KEY=your_fernet_key_here
REPOSITORIES_BASE_PATH=./cloned_repositories

# ── Docker CI Runner ─────────────────────────────────────
REPOSITORY_TEST_DOCKER_IMAGE=repository-test-runner:python3.12
REPOSITORY_TEST_COMMAND=python -m pytest -q --tb=short --disable-warnings
# 'install-deps' detecta automáticamente Poetry / requirements.txt / pyproject.toml
REPOSITORY_TEST_INSTALL_COMMAND=install-deps
REPOSITORY_TEST_TIMEOUT_SECONDS=300
REPOSITORY_TEST_DOCKER_NETWORK_DISABLED=true
REPOSITORY_TEST_OUTPUT_MAX_CHARS=8000

# ── Infobip Email ────────────────────────────────────────
INFO_MAIL=info@tudominio.com
INFOBIP_BASE_URL=https://xxxxx.api.infobip.com
INFOBIP_API_KEY=TU_API_KEY
REPORT_EMAIL_RATE_LIMIT_PER_MINUTE=10
REPORT_RECIPIENTS=correo1@dominio.com,correo2@dominio.com
```

> ⚠️ **Nunca subas `.env` al repositorio.** Está incluido en `.gitignore`.

Para generar una clave Fernet:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## Levantar servicios (PostgreSQL + Redis)

```powershell
docker compose up -d
docker ps
```

Puertos esperados:

| Servicio   | Puerto host | Puerto contenedor |
|------------|-------------|-------------------|
| PostgreSQL | 5433        | 5432              |
| Redis      | 6379        | 6379              |

Verificar:

```powershell
# PostgreSQL
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db -c "SELECT 1;"

# Redis
docker exec -it redis_cache redis-cli ping
# → PONG
```

---

## Imagen Docker del CI Runner

La imagen `repository-test-runner:python3.12` se usa para ejecutar los tests de los repositorios clonados en un entorno aislado. Incluye:

- Python 3.12
- pytest, pytest-cov, pytest-asyncio, httpx
- FastAPI, SQLAlchemy, asyncpg, bcrypt, pydantic-settings…
- **Poetry 2.x** (para repos que usen `pyproject.toml`)
- Node.js 20 + corepack
- Script `install-deps`: detecta automáticamente el gestor de paquetes

### Construir la imagen

Desde la raíz del proyecto:

```powershell
docker build -f docker/test-runner/Dockerfile -t repository-test-runner:python3.12 .
```

> Reconstruir la imagen si cambias `docker/test-runner/requirements.txt`, el `Dockerfile` o `install-deps.sh`.

### Cómo funciona `install-deps`

El script `/usr/local/bin/install-deps` (incluido en la imagen) detecta el gestor de paquetes del repositorio clonado y lo instala automáticamente:

| Condición                                  | Acción                          |
|--------------------------------------------|---------------------------------|
| `pyproject.toml` con `[tool.poetry]`       | `poetry install --no-root`      |
| `requirements.txt`                         | `pip install -r requirements.txt` |
| `pyproject.toml` genérico                  | `pip install -e .`              |

---

## Migraciones

```powershell
# Aplicar todas las migraciones
python -m alembic upgrade head

# Crear una nueva migración (tras cambiar modelos)
python -m alembic revision --autogenerate -m "descripcion"
```

Tablas esperadas tras las migraciones:

```
users
refresh_tokens
password_reset_tokens
audit_logs
repositories
repository_test_runs
alembic_version
```

---

## Ejecutar servidor

```powershell
python -m uvicorn app.main:app --reload
```

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

## Endpoints

### 🔐 Auth

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout-all
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

### 👤 Usuario autenticado

```http
GET    /api/v1/users/me
PATCH  /api/v1/users/me
PATCH  /api/v1/users/me/password
DELETE /api/v1/users/me
```

### 📁 Repositorios

```http
POST   /api/v1/repositories                    # Crear repositorio
GET    /api/v1/repositories                    # Listar repositorios del usuario
GET    /api/v1/repositories/{id}               # Obtener repositorio
PATCH  /api/v1/repositories/{id}               # Actualizar repositorio
DELETE /api/v1/repositories/{id}               # Eliminar repositorio
POST   /api/v1/repositories/{id}/clone         # Clonar repositorio
POST   /api/v1/repositories/{id}/pull          # Actualizar desde remoto
POST   /api/v1/repositories/run-tests          # Verificar cambios y ejecutar tests
```

---

## Flujo de CI/CD automático

```
POST /api/v1/repositories/run-tests
         │
         ▼
  Detectar cambios (git fetch + diff local/remoto)
         │
   ¿Hay cambios?
    No → guardar resultado SKIPPED
    Sí ↓
  Copiar repo a directorio temporal
  Docker run (install-deps + pytest --junitxml)
         │
  Extraer report.xml del contenedor
  Parsear JUnit XML → { total, passed, failed, test_cases[] }
         │
  Guardar RepositoryTestRun en BD
         │
  Enviar email HTML a destinatarios (Infobip)
         │
  Devolver response con resultado y junit
```

---

## Ejemplo de response de run-tests

```json
{
  "tests_ran": true,
  "success": true,
  "status": "PASSED",
  "exit_code": 0,
  "duration_seconds": 12.4,
  "stdout": "{\"git\": {\"branch\": \"main\", \"commit_author\": \"Juan\", ...}, \"junit\": {...}}",
  "stderr": "",
  "junit": {
    "total": 15,
    "passed": 14,
    "failed": 1,
    "errors": 0,
    "skipped": 0,
    "total_time": 11.8,
    "test_cases": [
      {"name": "tests/test_auth.py::test_login", "status": "PASSED", "time": 0.42, "message": ""},
      {"name": "tests/test_users.py::test_delete", "status": "FAILED", "time": 1.1, "message": "AssertionError: ..."}
    ]
  }
}
```

---

## Auditoría

Eventos registrados automáticamente en la tabla `audit_logs`:

```
user.created         user.updated         user.deleted
auth.login.success   auth.login.failed
password.changed     password.reset.requested   password.reset.completed
role.changed
```

Consultar desde PostgreSQL:

```sql
SELECT event_type, metadata, created_at
FROM audit_logs
ORDER BY created_at DESC;
```

---

## Comandos útiles

```powershell
# Servicios
docker compose up -d
docker compose down
docker compose down -v        # Borrar datos de desarrollo

# Servidor
python -m uvicorn app.main:app --reload

# Migraciones
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "mensaje"

# Tests locales
pytest
pytest -v

# Imagen Docker CI
docker build -f docker/test-runner/Dockerfile -t repository-test-runner:python3.12 .
docker run --rm repository-test-runner:python3.12 poetry --version

# Redis
docker exec -it redis_cache redis-cli ping
docker exec -it redis_cache redis-cli FLUSHDB

# PostgreSQL
docker exec -it postgres_db psql -U fastapi_user -d fastapi_db
```

---

## Seguridad

- No subir `.env` al repositorio
- Cambiar `JWT_SECRET_KEY` y `FERNET_SECRET_KEY` en producción
- Usar HTTPS en producción
- No usar CORS con `*` en producción
- Desactivar `DEBUG=false` en producción
- Las contraseñas se almacenan con **bcrypt**
- Los tokens Git se cifran con **Fernet (AES-128-CBC)**
- Los refresh tokens y reset tokens **no se guardan en texto plano**