# ai-business-platform

## Bootstrap local

### Requisitos

- Python 3.13+
- PostgreSQL 15+ (o 14+)
- Node 20+ (solo si levantas el frontend)
- [uv](https://github.com/astral-sh/uv) recomendado

### 1. Clonar / abrir el proyecto

```bash
cd "ruta/al/proyecto"
```

### 2. Entorno Python

```bash
uv sync --group dev
# o: python -m venv .venv && .venv/Scripts/activate  # Windows
#    pip install -e ".[dev]"
```

### 3. Archivo .env

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegar el valor generado en `.env`:

```env
JWT_SECRET_KEY=<el_valor_generado>
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/ai_business_platform
ENVIRONMENT=development
```

Crear la base si no existe:

```bash
# psql como superuser
createdb ai_business_platform
# o: CREATE DATABASE ai_business_platform;
```

### 4. Migraciones (OBLIGATORIO)

Head actual esperado: `f8a9b0c1d2e3`

```bash
alembic upgrade head
alembic heads
alembic current
```

Si `upgrade` falla por huérfanos / FK:

- Leer el mensaje de la migración `f8a9b0c1d2e3` / `d6e7f8a9b0c1`
- En dev es aceptable vaciar tablas de tokens/keys/vehicles huérfanos y reintentar

Migraciones recientes que deben aplicarse si vienes de un schema viejo:

- `d6e7f8a9b0c1` — vehicles.user_id NOT NULL + índices
- `e7f8a9b0c1d2` — search_history.user_id
- `f8a9b0c1d2e3` — FK api_keys / refresh_tokens → users

### 5. Arrancar API

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Smoke:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/v1/health
```

Ambos deben responder 200.

### 6. Registro de prueba

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"demo@example.com\",\"password\":\"password123\"}"
```

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"demo@example.com\",\"password\":\"password123\"}"
```

Guardar `access_token` y llamar:

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### 7. Frontend (opcional)

```bash
cd frontend
cp .env.example .env.local   # si existe; si no, NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Abrir `http://localhost:3000`.

### 8. Scheduler

Con `ENABLE_SCHEDULER=true` los jobs arrancan con la API (cleanup diario, refresh opportunities paginado). Para desactivar en debug:

```env
ENABLE_SCHEDULER=false
```

### Problemas frecuentes

| Síntoma | Causa | Acción |
|---------|--------|--------|
| `JWT_SECRET_KEY must be set and at least 32 characters` | `.env` vacío o corto | Generar secreto ≥32 |
| Error al importar settings | JWT / env | Revisar `ENVIRONMENT` y `.env` cargado desde el cwd |
| Tablas no existen | Migraciones no corridas | `alembic upgrade head` |
| Login 401 inactive | User desactivado | Admin reactiva o nuevo registro |
| 429 en login | Rate limit login=5/min | Esperar o reiniciar proceso API (límites en memoria) |
| Scrapers vacíos | HTML de mobile.de/AS24 cambió | Revisar logs del provider; no es fallo de bootstrap |

### Fuera de este bootstrap

- Tests (`TODO.md`, sesión paralela)
- Redis como backend de rate limit
- CRUD HTTP de API keys
- Verificación en vivo de parsers HTML
