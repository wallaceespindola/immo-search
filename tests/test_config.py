"""Unit tests for app/config.py."""

from app.config import (
    ALL_EXCLUSION_KEYWORDS,
    ALL_POOL_KEYWORDS,
    MAX_PRICE,
    MIN_BEDROOMS,
    TARGET_CITIES,
    TARGET_POSTAL_CODES,
)


def test_max_price():
    assert MAX_PRICE == 600_000


def test_min_bedrooms():
    assert MIN_BEDROOMS == 4


def test_target_cities_not_empty():
    assert len(TARGET_CITIES) > 0
    assert "Wavre" in TARGET_CITIES
    assert "Waterloo" in TARGET_CITIES


def test_target_postal_codes_not_empty():
    assert len(TARGET_POSTAL_CODES) > 0
    assert "1300" in TARGET_POSTAL_CODES  # Wavre
    assert "1410" in TARGET_POSTAL_CODES  # Waterloo


def test_exclusion_keywords_contain_apartments():
    lower = [k.lower() for k in ALL_EXCLUSION_KEYWORDS]
    assert "appartement" in lower


def test_exclusion_keywords_contain_attached_house_types():
    lower = [k.lower() for k in ALL_EXCLUSION_KEYWORDS]
    assert any("mitoyenne" in k for k in lower)
    assert any("2 fa" in k for k in lower)


def test_pool_keywords_fr_and_nl():
    lower = [k.lower() for k in ALL_POOL_KEYWORDS]
    assert any("piscine" in k for k in lower)
    assert any("zwembad" in k for k in lower)
