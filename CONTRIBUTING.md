# Guía de contribución

Gracias por tu interés en contribuir a AI Business Platform. Sigue estas pautas para que el proceso sea fluido.

## 🧑‍💻 Flujo de trabajo

1. **Fork** el repositorio (si eres externo) o crea una rama directamente.
2. **Crea una rama** con nombre descriptivo:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```
3. **Haz commits atómicos** (uno por cambio lógico):
   ```bash
   git commit -m "feat: añadir búsqueda por filtros"
   ```
4. **Asegura que los tests pasan** localmente:
   ```bash
   npm run test:coverage  # frontend
   pytest tests/          # backend
   ```
5. **Sube la rama** y crea un Pull Request contra `main`.

## 📝 Estándares de código

### Frontend
- TypeScript estricto (`strict: true` en `tsconfig.json`).
- Formato con Prettier (configuración por defecto).
- Linting con ESLint (reglas de Next.js).

### Backend
- Python 3.13.x.
- Formato con Black (línea máxima 88).
- Orden de imports con `isort`.

## 🧪 Tests obligatorios

- **Unitarios**: cada nueva funcionalidad debe tener tests (cobertura ≥85%).
- **E2E**: si afecta a flujos críticos (login, búsqueda, oportunidad), añade tests en Playwright.
- **Integración**: para cambios en la API, añade tests con `pytest` (mocks o base de datos de prueba).

## 🔍 Revisión de PRs

- Todos los tests deben pasar en CI.
- La cobertura no debe disminuir.
- El código debe pasar `tsc --noEmit` y `npm run build`.
- Se requiere al menos un revisor.

## 🐛 Reportar issues

Usa la plantilla de GitHub Issues. Incluye:
- Pasos para reproducir.
- Comportamiento esperado vs real.
- Capturas de pantalla/logs si aplica.

## 📬 Contacto

Para dudas, abre un issue o contacta al mantenedor principal.