from __future__ import annotations

import uuid

from app.utils.correlation import (
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


def test_generate_correlation_id_returns_uuid() -> None:
    """Verifica que generate_correlation_id devuelve un UUID v4."""
    cid = generate_correlation_id()
    assert isinstance(cid, str)
    # UUID v4 tiene formato 8-4-4-4-12
    parts = cid.split("-")
    assert len(parts) == 5
    assert len(parts[0]) == 8
    assert len(parts[1]) == 4
    assert len(parts[2]) == 4
    assert len(parts[3]) == 4
    assert len(parts[4]) == 12
    # Verificar que es un UUID válido
    uuid_obj = uuid.UUID(cid)
    assert uuid_obj.version == 4


def test_generate_correlation_id_is_unique() -> None:
    """Verifica que generate_correlation_id genera IDs únicos."""
    ids = {generate_correlation_id() for _ in range(100)}
    assert len(ids) == 100


def test_correlation_id_context_default_none() -> None:
    """Verifica que por defecto get_correlation_id devuelve None."""
    reset_correlation_id()
    assert get_correlation_id() is None


def test_set_and_get_correlation_id() -> None:
    """Verifica que set_correlation_id almacena y get_correlation_id recupera."""
    test_id = "test-correlation-123"
    set_correlation_id(test_id)
    assert get_correlation_id() == test_id


def test_reset_correlation_id() -> None:
    """Verifica que reset_correlation_id limpia el contexto."""
    set_correlation_id("some-id")
    assert get_correlation_id() == "some-id"
    reset_correlation_id()
    assert get_correlation_id() is None


def test_correlation_id_context_isolation() -> None:
    """Verifica que diferentes contextos no interfieren."""
    import asyncio

    async def task(task_id: str) -> str:
        cid = generate_correlation_id()
        set_correlation_id(cid)
        # Simular trabajo
        await asyncio.sleep(0.01)
        retrieved = get_correlation_id()
        assert retrieved == cid, f"Task {task_id} esperaba {cid} pero obtuvo {retrieved}"
        return retrieved

    async def run_tasks() -> None:
        results = await asyncio.gather(*[task(str(i)) for i in range(10)])
        # Todos los IDs deben ser únicos
        assert len(set(results)) == 10

    asyncio.run(run_tasks())


def test_correlation_id_empty_string() -> None:
    """Verifica que set_correlation_id acepta string vacío."""
    set_correlation_id("")
    assert get_correlation_id() == ""


def test_correlation_id_uniqueness_via_context() -> None:
    """Verifica que dos contextos secuenciales no se solapan."""
    id1 = generate_correlation_id()
    set_correlation_id(id1)
    assert get_correlation_id() == id1

    id2 = generate_correlation_id()
    set_correlation_id(id2)
    assert get_correlation_id() == id2
    # id1 ya no debe estar disponible
    assert get_correlation_id() != id1


def test_correlation_id_with_none_reset() -> None:
    """Verifica que reset seguido de set funciona correctamente."""
    reset_correlation_id()
    assert get_correlation_id() is None

    cid = generate_correlation_id()
    set_correlation_id(cid)
    assert get_correlation_id() == cid

