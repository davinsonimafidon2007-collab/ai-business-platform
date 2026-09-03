"""
Verificación de migraciones Alembic.

Checks:
1. `alembic heads` devuelve exactamente 1 head (sin hardcodear el ID: el head
   cambia con cada migración nueva y un valor fijo rompía CI).
2. La cadena es lineal desde la raíz inicial hasta el head (sin ramas ni
   ciclos).

Uso:
    uv run python scripts/check_migrations.py

Exit codes:
    0 - OK
    1 - Heads múltiples detectados
    2 - Cadena no lineal / error de ejecución
"""

from __future__ import annotations

import re
import subprocess
import sys


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"ERROR ejecutando {' '.join(cmd)}:")
        print(result.stderr, file=sys.stderr)
        sys.exit(2)
    return result.stdout.strip()


def check_single_head() -> str:
    output = run([sys.executable, "-m", "alembic", "heads"])
    heads = [line.strip() for line in output.splitlines() if line.strip()]

    head_re = re.compile(r"^([0-9a-zA-Z]+)")
    ids = []
    for h in heads:
        m = head_re.match(h)
        if m:
            ids.append(m.group(1))

    if len(ids) == 0:
        print("ERROR: alembic heads no devolvió revisiones.")
        sys.exit(1)

    if len(ids) > 1:
        print(f"ERROR: Heads múltiples detectados: {ids}")
        sys.exit(1)

    return ids[0]


def check_linear_chain(head: str) -> None:
    output = run([sys.executable, "-m", "alembic", "history"])

    # Formato típico de `alembic history` (de head hacia base):
    #   p2q3r4s5t6u7 -> q3r4s5t6u7v8 (head), add opportunity_phases ...
    #   <base> -> 20260725_init_empty, Initial empty migration
    parents: list[str] = []
    children: list[str] = []
    roots: list[str] = []
    head_line = False
    for line in output.splitlines():
        m = re.match(r"(?:<base>|([0-9a-zA-Z]+))\s+->\s+([0-9a-zA-Z]+)", line)
        if not m:
            continue
        parent = m.group(1)
        child = m.group(2)
        if parent is not None:
            parents.append(parent)
        else:
            roots.append(child)
        children.append(child)
        if "(head)" in line:
            head_line = True
            if child != head:
                print(
                    f"ERROR: Head en history ({child}) no coincide con heads ({head})"
                )
                sys.exit(2)

    if not children:
        print("ERROR: No se pudo parsear la cadena de migraciones.")
        sys.exit(2)

    if not head_line:
        print("ERROR: No se encontró la línea de head en `alembic history`.")
        sys.exit(2)

    if len(roots) == 0:
        print("ERROR: No se encontró la migración raíz (<base>).")
        sys.exit(2)

    # Ramas / ciclos: ningún ID debe aparecer como parent más de una vez
    parent_counts: dict[str, int] = {}
    for p in parents:
        parent_counts[p] = parent_counts.get(p, 0) + 1

    branches = [rev for rev, count in parent_counts.items() if count > 1]
    if branches:
        print(f"ERROR: La cadena contiene ramas (parents repetidos): {branches}")
        sys.exit(2)

    if head in parent_counts:
        print("ERROR: El head aparece como parent de otra migración (cadena rota).")
        sys.exit(2)

    print(
        f"OK: Cadena lineal única desde {roots[0]} hasta {head} "
        f"({len(children)} migraciones)."
    )


def main() -> None:
    print("=== Verificación de migraciones Alembic ===")

    head = check_single_head()
    print(f"Head detectado: {head}")
    print("OK: Un único head (sin ramas abiertas).")

    try:
        check_linear_chain(head)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        print(f"ERROR verificando linearidad: {exc}")
        sys.exit(2)

    print("=== Verificación completada: OK ===")


if __name__ == "__main__":
    main()
