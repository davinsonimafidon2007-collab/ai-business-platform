"""Tests del parser puro de AutoScout24 (P2): contrato ``(results, status)``.

``parse_listings_from_next_data`` distingue "0 resultados legítimos" de
"AutoScout24 cambió la estructura" para que el provider no produzca 0
resultados silenciosos.
"""

from __future__ import annotations

from app.providers.parsers import autoscout24_parser
from app.providers.parsers.autoscout24_parser import (
    NEXT_DATA_ABSENT,
    NEXT_DATA_INVALID,
    NEXT_DATA_MISSING_KEY,
    NEXT_DATA_OK,
    NEXT_DATA_UNPARSED,
    parse_listings_from_next_data,
)

BASE_URL = "https://www.autoscout24.de"


def _html(payload: str) -> str:
    return (
        "<html><head>"
        f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'
        "</head><body></body></html>"
    )


def test_absent_when_no_script() -> None:
    results, status = parse_listings_from_next_data(
        "<html><body></body></html>", BASE_URL, "autoscout24"
    )
    assert results == []
    assert status == NEXT_DATA_ABSENT


def test_invalid_when_json_broken() -> None:
    results, status = parse_listings_from_next_data(
        _html("NOT_VALID_JSON"), BASE_URL, "autoscout24"
    )
    assert results == []
    assert status == NEXT_DATA_INVALID


def test_missing_key_when_listings_absent() -> None:
    results, status = parse_listings_from_next_data(
        _html('{"props":{"pageProps":{}}}'), BASE_URL, "autoscout24"
    )
    assert results == []
    assert status == NEXT_DATA_MISSING_KEY


def test_ok_with_empty_listings_is_valid() -> None:
    results, status = parse_listings_from_next_data(
        _html('{"props":{"pageProps":{"listings":[]}}}'), BASE_URL, "autoscout24"
    )
    assert results == []
    assert status == NEXT_DATA_OK


def test_ok_parses_listings() -> None:
    payload = (
        '{"props":{"pageProps":{"listings":[{"id":"100","url":"/angebote/x-100",'
        '"vehicle":{"make":"BMW","model":"320d","fuel":"diesel"}}]}}}'
    )
    results, status = parse_listings_from_next_data(
        _html(payload), BASE_URL, "autoscout24"
    )
    assert status == NEXT_DATA_OK
    assert [r.external_id for r in results] == ["100"]


def test_unparsed_when_items_not_convertible() -> None:
    payload = (
        '{"props":{"pageProps":{"listings":[{"unexpected":"shape"},'
        '{"unexpected":"shape2"}]}}}'
    )
    results, status = parse_listings_from_next_data(
        _html(payload), BASE_URL, "autoscout24"
    )
    assert results == []
    assert status == NEXT_DATA_UNPARSED


def test_constants_are_str_for_backwards_logging() -> None:
    for const in (
        NEXT_DATA_OK,
        NEXT_DATA_ABSENT,
        NEXT_DATA_INVALID,
        NEXT_DATA_MISSING_KEY,
        NEXT_DATA_UNPARSED,
    ):
        assert isinstance(const, str)


def test_module_exports() -> None:
    assert hasattr(autoscout24_parser, "parse_listings_from_next_data")
