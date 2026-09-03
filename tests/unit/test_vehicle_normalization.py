"""Tests for vehicle normalization and quality system."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.normalization.pipeline import VehicleNormalizer
from app.normalization.schema import (
    NormalizedVehicle,
    clean_vehicle_string,
    clean_version_string,
    convert_to_eur,
    deduplicate_vehicles,
    detect_corrupt_listing,
    extract_country_from_location,
    normalize_color,
    normalize_fuel,
    normalize_image_url,
    normalize_transmission,
    parse_price_text,
    select_preferred_vehicle,
    validate_vin,
)
from app.providers.dto import VehicleSearchResult


# Fixtures for real provider data
@pytest.fixture
def autoscout24_dto() -> VehicleSearchResult:
    """Real AutoScout24 listing from fixture."""
    return VehicleSearchResult(
        source="autoscout24",
        external_id="31000001",
        url="https://www.autoscout24.de/angebote/bmw-3er-320d-31000001",
        brand="BMW",
        model="3er 320d",
        version="320d",
        year=2020,
        mileage=20000,
        fuel_type="Diesel",
        transmission="Automática",
        power_hp=190,
        displacement_cc=1995,
        location="Berlin 10115 DE",
        seller_type="Dealer",
        first_registration="03-2020",
        price=28500.0,
        currency="EUR",
        vin="WBA3A510XLF123456",
        description="BMW 3er 320d, muy buen estado, histórico completo",
        images=[
            "https://img.autoscout24.de/bmw1.jpg",
            "https://img.autoscout24.de/bmw2.jpg",
        ],
        equipment=["Navi", "Ledersitze", "Klimaautomatik"],
        raw_data={"id": "31000001", "vehicle": {"make": "BMW"}},
    )


@pytest.fixture
def coches_net_dto() -> VehicleSearchResult:
    """Real Coches.net listing format."""
    return VehicleSearchResult(
        source="coches_net",
        external_id="71266436",
        url="https://www.coches.net/volkswagen-tiguan-71266436-covo.aspx",
        brand="VOLKSWAGEN",
        model="Tiguan",
        version="1.5 TSI eHybrid",
        year=2023,
        mileage=47980,
        fuel_type="Híbrido enchufable",
        transmission="Automática (DSG)",
        power_hp=245,
        displacement_cc=1498,
        location="Barcelona",
        seller_type="Particular",
        price=26990.0,
        currency="EUR",
        images=["https://a.ccdn.es/cnet/vehicles/20586415/816a7673-91bb-437f-9112-760cef4e4e5b.jpg"],
        equipment=["GPS", "Cuero", "Sensor aparcamiento"],
    )


@pytest.fixture
def mobile_de_dto() -> VehicleSearchResult:
    """Real mobile.de listing format."""
    return VehicleSearchResult(
        source="mobile_de",
        external_id="345678901",
        url="https://suchen.mobile.de/fahrzeuge/details.html?id=345678901",
        brand="Audi",
        model="A4",
        version="40 TDI quattro S tronic",
        year=2021,
        mileage=35000,
        fuel_type="Diesel",
        transmission="Automática",
        power_hp=204,
        displacement_cc=1968,
        location="München, 80331, DE",
        seller_type="Händler",
        first_registration="06/2021",
        price=38900.0,
        currency="EUR",
        vin="WAUZZZF48MA123456",
        description="Audi A4 Avant 40 TDI, S-Line, Virtual Cockpit",
        images=[
            "https://img.mobile.de/audi1.jpg",
            "https://img.mobile.de/audi2.jpg",
        ],
        equipment=["S-Line", "Virtual Cockpit", "Matrix LED"],
    )


class TestStringCleaning:
    """Tests for string normalization functions."""

    def test_clean_brand_model_basic(self) -> None:
        assert clean_vehicle_string("  BMW  ") == "BMW"
        assert clean_vehicle_string("Mercedes-Benz") == "Mercedes-Benz"
        assert clean_vehicle_string("  VW  ") == "Volkswagen"
        assert clean_vehicle_string("vw") == "Volkswagen"
        assert clean_vehicle_string("MERCEDES") == "Mercedes-Benz"
        assert clean_vehicle_string("alfa romeo") == "Alfa Romeo"
        assert clean_vehicle_string("land rover") == "Land Rover"

    def test_clean_version_string(self) -> None:
        assert clean_version_string("  320d  ") == "320d"
        assert clean_version_string("1.5 TSI eHybrid") == "1.5 TSI eHybrid"
        assert clean_version_string("  40 TDI quattro  ") == "40 TDI quattro"

    def test_normalize_fuel(self) -> None:
        assert normalize_fuel("Diesel") == "Diesel"
        assert normalize_fuel("diesel") == "Diesel"
        assert normalize_fuel("D") == "Diesel"
        assert normalize_fuel("Benzin") == "Gasolina"
        assert normalize_fuel("gasolina") == "Gasolina"
        assert normalize_fuel("B") == "Gasolina"
        assert normalize_fuel("Eléctrico") == "Eléctrico"
        assert normalize_fuel("electric") == "Eléctrico"
        assert normalize_fuel("Híbrido") == "Híbrido"
        assert normalize_fuel("hybrid") == "Híbrido"
        assert normalize_fuel("Enchufable") == "Híbrido Enchufable"
        assert normalize_fuel("GLP") == "GLP"
        assert normalize_fuel("GNC") == "GNC"
        assert normalize_fuel("Hidrógeno") == "Hidrógeno"

    def test_normalize_transmission(self) -> None:
        assert normalize_transmission("Manual") == "Manual"
        assert normalize_transmission("manual") == "Manual"
        assert normalize_transmission("Automática") == "Automática"
        assert normalize_transmission("automatic") == "Automática"
        assert normalize_transmission("DSG") == "Automática (DSG)"
        assert normalize_transmission("Tiptronic") == "Automática (Tiptronic)"
        assert normalize_transmission("CVT") == "Automática (CVT)"
        assert normalize_transmission("Semiautomática") == "Semiautomática"

    def test_normalize_color(self) -> None:
        assert normalize_color("Negro") == "Negro"
        assert normalize_color("black") == "Negro"
        assert normalize_color("Blanco") == "Blanco"
        assert normalize_color("Gris") == "Gris"
        assert normalize_color("Plata") == "Plata"
        assert normalize_color("Azul") == "Azul"
        assert normalize_color("Rojo") == "Rojo"

    def test_extract_country_from_location(self) -> None:
        assert extract_country_from_location("Berlin, DE") == "DE"
        assert extract_country_from_location("Madrid, ES") == "ES"
        assert extract_country_from_location("Munich, Germany") == "DE"
        assert extract_country_from_location("Paris, FR") == "FR"
        assert extract_country_from_location("Barcelona") == "ES"
        assert extract_country_from_location(None) is None

    def test_parse_price_text(self) -> None:
        assert parse_price_text("28.500 €") == 28500.0
        assert parse_price_text("32.990,- €") == 32990.0
        assert parse_price_text("12.345,50 €") == 12345.50
        assert parse_price_text("€ 28.500") == 28500.0
        assert parse_price_text("28500") == 28500.0
        assert parse_price_text("9.000,-") == 9000.0
        assert parse_price_text("cuota 200 €/mes") is None
        assert parse_price_text("financiación 150 €/mth") is None

    def test_normalize_image_url(self) -> None:
        assert normalize_image_url("//img.example.com/photo.jpg") == "https://img.example.com/photo.jpg"
        assert normalize_image_url("/photo.jpg") == "/photo.jpg"
        assert normalize_image_url("https://example.com/photo.jpg") == "https://example.com/photo.jpg"
        assert normalize_image_url("") == ""

    def test_validate_vin(self) -> None:
        assert validate_vin("WBA3A510XLF123456") is True
        assert validate_vin("WAUZZZF48MA123456") is True
        assert validate_vin("VSSZZZ6JZER123456") is True
        assert validate_vin("WBA3A510XLF12345") is False  # too short
        assert validate_vin("WBA3A510XLF1234567") is False  # too long
        assert validate_vin("WBA3A510XLF12345O") is False  # contains O
        assert validate_vin("WBA3A510XLF12345I") is False  # contains I
        assert validate_vin("") is False
        assert validate_vin(None) is False


class TestCurrencyConversion:
    """Tests for currency conversion."""

    def test_convert_eur_to_eur(self) -> None:
        result = convert_to_eur(Decimal("10000"), "EUR")
        assert result == Decimal("10000.00")

    def test_convert_usd_to_eur(self) -> None:
        result = convert_to_eur(Decimal("10000"), "USD")
        assert result == Decimal("9200.00")

    def test_convert_gbp_to_eur(self) -> None:
        result = convert_to_eur(Decimal("10000"), "GBP")
        assert result == Decimal("11700.00")

    def test_convert_unknown_currency_defaults_to_eur(self) -> None:
        result = convert_to_eur(Decimal("10000"), "XYZ")
        assert result == Decimal("10000.00")


class TestNormalizedVehicleSchema:
    """Tests for NormalizedVehicle Pydantic schema."""

    def test_from_autoscout24_dto(self, autoscout24_dto: VehicleSearchResult) -> None:
        norm = NormalizedVehicle.from_provider_dto(autoscout24_dto)

        assert norm.source == "autoscout24"
        assert norm.external_id == "31000001"
        assert norm.brand == "BMW"
        assert norm.model == "3er 320d"
        assert norm.version == "320d"
        assert norm.year == 2020
        assert norm.mileage == 20000
        assert norm.fuel_type == "Diesel"
        assert norm.transmission == "Automática"
        assert norm.power_hp == 190
        assert norm.displacement_cc == 1995
        assert norm.location == "Berlin 10115 DE"
        assert norm.country == "DE"
        assert norm.price == Decimal("28500.00")
        assert norm.currency == "EUR"
        assert norm.price_eur == Decimal("28500.00")
        assert norm.vin == "WBA3A510XLF123456"
        assert len(norm.images) == 2
        assert len(norm.equipment) == 3
        assert norm.quality_score > 0.5
        assert norm.raw_data is not None

    def test_from_coches_net_dto(self, coches_net_dto: VehicleSearchResult) -> None:
        norm = NormalizedVehicle.from_provider_dto(coches_net_dto)

        assert norm.source == "coches_net"
        assert norm.brand == "Volkswagen"
        assert norm.model == "Tiguan"
        assert norm.fuel_type == "Híbrido Enchufable"
        assert norm.transmission == "Automática (DSG)"
        assert norm.country == "ES"
        assert norm.price == Decimal("26990.00")

    def test_from_mobile_de_dto(self, mobile_de_dto: VehicleSearchResult) -> None:
        norm = NormalizedVehicle.from_provider_dto(mobile_de_dto)

        assert norm.source == "mobile_de"
        assert norm.brand == "Audi"
        assert norm.model == "A4"
        assert norm.country == "DE"
        assert norm.price == Decimal("38900.00")

    def test_power_conversion_kw_to_hp(self) -> None:
        # VehicleSearchResult only has power_hp, but NormalizedVehicle has both
        # Test via model validator conversion
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            power_hp=150,
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        # 150 HP ≈ 110 kW
        assert norm.power_kw == 110

    def test_power_conversion_hp_to_kw(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            power_hp=150,
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.power_kw == 110  # 150 / 1.35962 ≈ 110.3 → 110

    def test_missing_required_fields_lowers_quality(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.quality_score < 0.7
        assert "missing_year" in norm.quality_flags
        assert "missing_price" in norm.quality_flags
        assert "missing_mileage" in norm.quality_flags

    def test_price_out_of_range_flags(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=50.0,  # Too low
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert "price_out_of_range" in norm.quality_flags

    def test_high_mileage_for_age_flag(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=400000,  # Very high for 6 years (exceeds 350k threshold)
            price=10000.0,
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert "high_mileage_for_age" in norm.quality_flags

    def test_invalid_vin_format_flag(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=10000.0,
            vin="INVALID_VIN",  # Too short, will fail validation
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert "invalid_vin_format" in norm.quality_flags

    def test_to_sqlalchemy_dict(self, autoscout24_dto: VehicleSearchResult) -> None:
        norm = NormalizedVehicle.from_provider_dto(autoscout24_dto)
        data = norm.to_sqlalchemy_dict()

        assert data["source"] == "autoscout24"
        assert data["brand"] == "BMW"
        assert data["price"] == 28500.0
        assert data["images"] == [
            "https://img.autoscout24.de/bmw1.jpg",
            "https://img.autoscout24.de/bmw2.jpg",
        ]
        assert data["equipment"] == "Navi,Ledersitze,Klimaautomatik"


class TestQualityScore:
    """Tests for quality scoring."""

    def test_complete_vehicle_high_score(self, autoscout24_dto: VehicleSearchResult) -> None:
        norm = NormalizedVehicle.from_provider_dto(autoscout24_dto)
        assert norm.quality_score >= 0.8

    def test_minimal_vehicle_low_score(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.quality_score < 0.5

    def test_no_images_penalty(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=10000.0,
            images=[],
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert "no_images" in norm.quality_flags

    def test_no_equipment_penalty(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=10000.0,
            equipment=[],
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert "no_equipment" in norm.quality_flags


class TestCorruptListingDetection:
    """Tests for corrupt/scam listing detection."""

    def test_price_too_low(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2022,
            mileage=10000,
            price=500.0,  # Suspiciously low
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        flags = detect_corrupt_listing(norm)
        assert "price_too_low" in flags

    def test_recent_car_price_too_low(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Audi",
            model="A4",
            year=2023,
            mileage=5000,
            price=3000.0,  # Too low for 2023 car
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        flags = detect_corrupt_listing(norm)
        assert "recent_car_price_too_low" in flags

    def test_mileage_suspiciously_low(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="VW",
            model="Golf",
            year=2015,
            mileage=5000,  # Too low for 9-year-old car
            price=12000.0,
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        flags = detect_corrupt_listing(norm)
        assert "mileage_suspiciously_low" in flags

    def test_power_to_displacement_ratio_extreme(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=20000.0,
            power_hp=1000,  # 1000 HP from 1.0L = 1000 HP/L (extreme)
            displacement_cc=1000,
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        flags = detect_corrupt_listing(norm)
        assert "power_to_displacement_ratio_extreme" in flags

    def test_placeholder_images_flag(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            year=2020,
            mileage=50000,
            price=10000.0,
            images=["https://example.com/placeholder.jpg"],
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        flags = detect_corrupt_listing(norm)
        assert "placeholder_images" in flags


class TestDeduplication:
    """Tests for vehicle deduplication."""

    def test_deduplicate_by_vin(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
            vin="WBA3A510XLF123456",
        )
        dto2 = VehicleSearchResult(
            source="mobile_de",
            external_id="2",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=36000.0,
            vin="WBA3A510XLF123456",  # Same VIN
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        result = deduplicate_vehicles([norm1, norm2])
        assert len(result) == 1
        assert result[0].source == "autoscout24"  # Preferred source
        assert "deduped_by_vin" in result[0].quality_flags

    def test_deduplicate_by_source_external_id(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="123",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
        )
        dto2 = VehicleSearchResult(
            source="autoscout24",
            external_id="123",  # Same source + external_id
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=36000.0,
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        result = deduplicate_vehicles([norm1, norm2])
        assert len(result) == 1
        assert "deduped_by_source_ext" in result[0].quality_flags

    def test_fuzzy_deduplication(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
        )
        dto2 = VehicleSearchResult(
            source="mobile_de",
            external_id="2",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=51000,  # Within 5%
            price=36000.0,
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        result = deduplicate_vehicles([norm1, norm2])
        assert len(result) == 1
        assert "deduped_fuzzy" in result[0].quality_flags

    def test_no_deduplication_different_cars(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
        )
        dto2 = VehicleSearchResult(
            source="autoscout24",
            external_id="2",
            brand="Audi",
            model="Q7",
            year=2020,
            mileage=50000,
            price=36000.0,
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        result = deduplicate_vehicles([norm1, norm2])
        assert len(result) == 2


class TestVehicleNormalizer:
    """Tests for VehicleNormalizer class."""

    def test_normalize_single(self, autoscout24_dto: VehicleSearchResult) -> None:
        normalizer = VehicleNormalizer()
        norm = normalizer.normalize(autoscout24_dto)

        assert isinstance(norm, NormalizedVehicle)
        assert norm.source == "autoscout24"
        assert norm.brand == "BMW"

    def test_normalize_batch(self, autoscout24_dto: VehicleSearchResult, coches_net_dto: VehicleSearchResult) -> None:
        normalizer = VehicleNormalizer()
        norms = normalizer.normalize_batch([autoscout24_dto, coches_net_dto])

        assert len(norms) == 2
        assert all(isinstance(n, NormalizedVehicle) for n in norms)

    def test_normalize_batch_with_deduplication(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
            vin="WBA3A510XLF123456",
        )
        dto2 = VehicleSearchResult(
            source="mobile_de",
            external_id="2",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=36000.0,
            vin="WBA3A510XLF123456",
        )
        normalizer = VehicleNormalizer()
        norms = normalizer.normalize_batch([dto1, dto2], deduplicate=True)

        assert len(norms) == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_equipment_list(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            equipment=[],
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.equipment == []

    def test_equipment_as_csv_string(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            equipment="GPS, Cuero, Sensor",  # CSV string
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert len(norm.equipment) == 3
        assert norm.equipment[0].name == "GPS"

    def test_images_deduplication(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            images=["img1.jpg", "img1.jpg", "img2.jpg"],
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert len(norm.images) == 2

    def test_vin_normalization_uppercase(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            vin="wba3a510xlf123456",
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.vin == "WBA3A510XLF123456"

    def test_year_from_first_registration(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            first_registration="03/2020",
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.year == 2020

    def test_mileage_with_dots_and_commas(self) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            mileage="47.980",  # European format
        )
        norm = NormalizedVehicle.from_provider_dto(dto)
        assert norm.mileage == 47980


class TestSelectPreferredVehicle:
    """Tests for duplicate selection logic."""

    def test_prefers_higher_quality(self) -> None:
        dto1 = VehicleSearchResult(
            source="autoscout24",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
            images=[],
            equipment=[],
            description="",
        )
        dto2 = VehicleSearchResult(
            source="mobile_de",
            external_id="2",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=36000.0,
            images=["img1.jpg", "img2.jpg", "img3.jpg"],
            equipment=["GPS", "Leather", "Sunroof", "Navi"],
            description="Full description with many details about the vehicle condition and history.",
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        # dto2 has much higher quality score
        assert norm2.quality_score > norm1.quality_score
        preferred = select_preferred_vehicle([norm1, norm2], ["autoscout24", "mobile_de"])
        assert preferred.source == "mobile_de"  # Better quality

    def test_prefers_source_order_when_quality_equal(self) -> None:
        dto1 = VehicleSearchResult(
            source="mobile_de",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
        )
        dto2 = VehicleSearchResult(
            source="autoscout24",
            external_id="2",
            brand="BMW",
            model="X5",
            year=2020,
            mileage=50000,
            price=35000.0,
        )
        norm1 = NormalizedVehicle.from_provider_dto(dto1)
        norm2 = NormalizedVehicle.from_provider_dto(dto2)

        preferred = select_preferred_vehicle([norm1, norm2], ["autoscout24", "mobile_de"])
        assert preferred.source == "autoscout24"  # Preferred source order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])