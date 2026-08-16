from app.models.search import Search


def test_search_model_has_expected_columns() -> None:
    columns = {column.name for column in Search.__table__.columns}

    expected = {"id", "name", "country", "brands", "models", "filters", "created_at"}
    assert expected.issubset(columns)


def test_search_model_defaults() -> None:
    search = Search(name="BMW X5 en Alemania", country="DE")

    assert search.id is not None
    assert search.name == "BMW X5 en Alemania"
    assert search.country == "DE"
    assert search.created_at is not None