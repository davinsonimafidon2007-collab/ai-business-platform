# TODO — Fix requirements.txt y test de conexión Postgres

- [x] Añadir `aiosmtplib>=3.0.0,<4.0.0` a `requirements.txt` (UTF-16 LE con BOM)
- [x] Añadir `firebase-admin>=6.0.0,<7.0.0` a `requirements.txt` (UTF-16 LE con BOM)
- [x] Corregir `tests/integration/test_postgres_connection.py`:
  - `from app.db.session import engine` → `from app.db.session import db_manager`
  - `async with engine.connect() as connection:` → `async with db_manager.engine.connect() as connection:`
- [x] Verificar BOM/líneas de `requirements.txt` (63 → 65 líneas, BOM `fffe`)
- [x] Verificar que `python -c "from app.main import app"` no lance `ModuleNotFoundError`
- [x] `pip install -r requirements.txt` en un venv limpio para confirmar que UTF-16 no se corrompió

