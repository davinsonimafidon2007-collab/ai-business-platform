# AI Business Platform

Plataforma de inteligencia de negocio para vehículos, con autenticación, búsqueda en tiempo real, oportunidades de compra y análisis de costes de importación.

## 🚀 Tecnologías

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand
- **Backend**: Python 3.13, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis
- **Mobile**: Capacitor 6 (Android/iOS)
- **Testing**: Vitest (unit), Playwright (E2E), pytest (backend)
- **DevOps**: Docker Compose, GitHub Actions

## 📦 Requisitos

- Node.js 20.x
- Python 3.13.x
- Docker y Docker Compose
- Git

## 🔧 Instalación y despliegue

### 1. Clonar el repositorio
```bash
git clone https://github.com/davinsonimafidon2007-collab/ai-business-platform.git
cd ai-business-platform
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env con tus credenciales (Google OAuth, base de datos, etc.)
```

### 3. Levantar con Docker Compose (recomendado)
```bash
docker compose up -d
```
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 4. Desarrollo local (sin Docker)
#### Backend
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
uv sync
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🧪 Tests

### Frontend
```bash
cd frontend
npm run test           # unit tests (Vitest)
npm run test:coverage  # cobertura (requiere ≥85%)
npm run test:e2e       # Playwright E2E (requiere servicios levantados)
```

### Backend
```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term  # con cobertura
```

### Release check
```bash
python scripts/release_check.py
```

## 📊 Estado del proyecto

| Área | Cobertura | Estado |
| :--- | :--- | :--- |
| Frontend | ≥85% (statements, branches, functions, lines) | ✅ |
| Backend | ~97% | ✅ |
| Build (tsc) | 0 errores | ✅ |
| PWA | Configurada | ✅ |
| E2E | Playwright integrado | ✅ |

## 🤝 Contribuir

Lee [CONTRIBUTING.md](./CONTRIBUTING.md) para guías de estilo, flujo de trabajo y cómo reportar issues.

## 📄 Licencia

MIT (o la que tengas definida).
﻿# AI Business Platform...
