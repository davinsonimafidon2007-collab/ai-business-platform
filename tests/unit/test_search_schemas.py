import pytest
from pydantic import ValidationError

from app.schemas.search import SearchCreate, SearchRead, SearchUpdate


def test_search_create_accepts_valid_data() -> None:
    search = SearchCreate(name="BMW en Alemania", country="DE")

    assert search.name == "BMW en Alemania"
    assert search.country == "DE"


def test_search_create_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        SearchCreate()


def test_search_read_allows_model_attributes() -> None:
    search = SearchRead(
        id="123e4567-e89b-12d3-a456-426614174000",
        user_id="123e4567-e89b-12d3-a456-426614174001",  # requerido desde SEARCH.OWN
        name="Audi en Alemania",
        country="DE",
        created_at="2024-01-01T00:00:00",
    )

    assert search.id == "123e4567-e89b-12d3-a456-426614174000"
    assert search.name == "Audi en Alemania"
    assert search.country == "DE"
    # Alias de compatibilidad: timestamp refleja created_at
    assert search.timestamp is not None


def test_search_update_allows_partial_updates() -> None:
    search = SearchUpdate(name="Updated Search")

    assert search.name == "Updated Search"
    assert search.country is None