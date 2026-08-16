"""Tests unitarios para canary_state (Task G.1).

Verifica que set → get devuelve los campos almacenados y que el
holder es proceso-local (no persiste entre tests si se resetea).
"""

from __future__ import annotations

from app.jobs import canary_state


def test_set_then_get_returns_all_fields():
    canary_state._last = None  # reset estado previo
    data = {
        "autoscout24": {"count": 5},
        "mobile_de": {"count": 3},
        "strict_mobile": True,
        "mobile_status": "ok",
    }
    canary_state.set_last_canary_result(
        success=True,
        message="Canary OK",
        data=data,
    )

    result = canary_state.get_last_canary_result()
    assert result is not None
    assert result["success"] is True
    assert result["message"] == "Canary OK"
    assert result["data"] == data
    assert "finished_at" in result
    assert isinstance(result["finished_at"], str)


def test_get_returns_none_when_no_result():
    canary_state._last = None
    assert canary_state.get_last_canary_result() is None