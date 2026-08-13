import os
import secrets
import sys
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent.parent
    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"

    print("=== AI Business Platform - Setup Inicial de Entorno ===")

    # 1. Copiar .env.example si no existe
    if not env_file.exists():
        if not env_example.exists():
            print(f"Error: No se encontró {env_example}")
            sys.exit(1)
        print("Copiando .env.example a .env...")
        env_content = env_example.read_text(encoding="utf-8")
        env_file.write_text(env_content, encoding="utf-8")
    else:
        print("El archivo .env ya existe.")

    # 2. Verificar/generar JWT_SECRET_KEY
    env_content = env_file.read_text(encoding="utf-8")
    lines = env_content.splitlines()
    key_found = False
    needs_update = False
    updated_lines = []

    for line in lines:
        if line.strip().startswith("JWT_SECRET_KEY="):
            key_found = True
            parts = line.split("=", 1)
            current_val = parts[1].strip()
            if not current_val or len(current_val) < 32:
                print("Generando una nueva JWT_SECRET_KEY segura de 48 caracteres...")
                new_secret = secrets.token_urlsafe(48)
                updated_lines.append(f"JWT_SECRET_KEY={new_secret}")
                needs_update = True
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    if not key_found:
        print("Agregando JWT_SECRET_KEY al archivo .env...")
        new_secret = secrets.token_urlsafe(48)
        updated_lines.append(f"JWT_SECRET_KEY={new_secret}")
        needs_update = True

    if needs_update:
        env_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        print("¡JWT_SECRET_KEY configurada con éxito en .env!")
    else:
        print("JWT_SECRET_KEY ya está configurada correctamente.")

    print("\n¡Setup completado con éxito!")
    print("Para iniciar el proyecto:")
    print("  1. Inicia Postgres y Redis (o usa 'docker compose up --build')")
    print("  2. Corre las migraciones con: 'uv run alembic upgrade head'")
    print("  3. Levanta la API con: 'uv run uvicorn app.main:app --reload'")
    print("======================================================")


if __name__ == "__main__":
    main()
