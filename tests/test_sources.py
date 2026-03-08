"""Unit tests for source adapters."""

from unittest.mock import patch

from app.sources.base import BaseSource
from app.storage import Listing


def _make_mock_listing(
    source: str = "Test",
    price: int = 450_000,
    bedrooms: int = 4,
    has_pool: bool = True,
    has_parking: bool = True,
) -> Listing:
    return Listing(
        id=f"{source}:1",
        title="Belle villa avec piscine 4 façades",
        price=price,
        city="Wavre",
        address="",
        bedrooms=bedrooms,
        area=None,
        has_pool=has_pool,
        has_parking=has_parking,
        source=source,
        url="https://example.com/1",
        collected_at="2024-01-01T07:00:00+00:00",
    )


class ConcreteSource(BaseSource):
    """Concrete implementation of BaseSource for testing."""

    name = "TestSource"
    tier = 1

    def _fetch(self) -> list[Listing]:
        return [_make_mock_listing()]


def test_base_source_validation_price_too_high():
    source = ConcreteSource()
    listing = _make_mock_listing(price=700_000)
    with patch("app.sources.base.MAX_PRICE", 600_000), patch("app.sources.base.MIN_PRICE", None):
        assert source._is_valid(listing) is False


def test_base_source_validation_price_zero():
    source = ConcreteSource()
    listing = _make_mock_listing(price=0)
    with patch("app.sources.base.MAX_PRICE", None), patch("app.sources.base.MIN_PRICE", None):
        assert source._is_valid(listing) is False


def test_base_source_validation_price_too_low():
    source = ConcreteSource()
    listing = _make_mock_listing(price=50_000)
    with patch("app.sources.base.MAX_PRICE", None), patch("app.sources.base.MIN_PRICE", 100_000):
        assert source._is_valid(listing) is False


def test_base_source_validation_too_few_bedrooms():
    source = ConcreteSource()
    listing = _make_mock_listing(bedrooms=2)
    with patch("app.sources.base.MIN_BEDROOMS", 4), patch("app.sources.base.MIN_PRICE", None):
        assert source._is_valid(listing) is False


def test_base_source_validation_exclusion_keyword():
    source = ConcreteSource()
    listing = _make_mock_listing()
    listing = Listing(
        id="test:excl",
        title="Appartement 4 chambres avec piscine",  # "appartement" excluded
        price=400_000,
        city="Wavre",
        address="",
        bedrooms=4,
        area=None,
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/2",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    assert source._is_valid(listing) is False


def test_base_source_validation_valid_listing():
    source = ConcreteSource()
    listing = _make_mock_listing()
    assert source._is_valid(listing) is True


def test_base_source_fetch_listings_returns_valid():
    source = ConcreteSource()
    with patch.object(source, "_rate_limit"):  # skip actual delay
        listings = source.fetch_listings()
    assert len(listings) == 1
    assert listings[0].source == "Test"


def test_base_source_fetch_listings_handles_exception():
    source = ConcreteSource()

    def bad_fetch():
        raise ConnectionError("Network unreachable")

    source._fetch = bad_fetch  # type: ignore[method-assign]
    listings = source.fetch_listings()
    assert listings == []


def test_in_target_area_by_postal_code():
    source = ConcreteSource()
    assert source._in_target_area("1300", None) is True  # Wavre
    assert source._in_target_area("1410", None) is True  # Waterloo
    assert source._in_target_area("1000", None) is False  # Brussels


def test_in_target_area_by_city():
    source = ConcreteSource()
    assert source._in_target_area(None, "Wavre") is True
    assert source._in_target_area(None, "waterloo") is True
    assert source._in_target_area(None, "Brussels") is False


def test_clean_price():
    source = ConcreteSource()
    assert source._clean_price("€ 450.000") == 450000
    assert source._clean_price("500 000 €") == 500000
    assert source._clean_price("600000") == 600000


def test_clean_int():
    source = ConcreteSource()
    assert source._clean_int("4 chambres") == 4
    assert source._clean_int("5") == 5
    assert source._clean_int(None) == 0
    assert source._clean_int("") == 0


def test_base_source_validation_area_too_small():
    source = ConcreteSource()
    listing = _make_mock_listing()
    listing = Listing(
        id="test:area",
        title="Belle villa avec piscine 4 façades",
        price=400_000,
        city="Wavre",
        address="",
        bedrooms=4,
        area=35.0,  # parking space or studio — too small
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/area",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    with patch("app.sources.base.MIN_AREA", 80):
        assert source._is_valid(listing) is False


def test_base_source_validation_area_unknown_passes():
    source = ConcreteSource()
    listing = Listing(
        id="test:area-none",
        title="Belle villa avec piscine 4 façades",
        price=400_000,
        city="Wavre",
        address="",
        bedrooms=4,
        area=None,  # area unknown — should pass through
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/area2",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    with patch("app.sources.base.MIN_AREA", 80):
        assert source._is_valid(listing) is True


def test_base_source_validation_no_pool_rejected():
    source = ConcreteSource()
    listing = _make_mock_listing(has_pool=False)
    with patch("app.sources.base.REQUIRE_POOL", True):
        assert source._is_valid(listing) is False


def test_base_source_validation_pool_passes():
    source = ConcreteSource()
    listing = _make_mock_listing(has_pool=True)
    with patch("app.sources.base.REQUIRE_POOL", True):
        assert source._is_valid(listing) is True


def test_base_source_validation_vendu_rejected():
    source = ConcreteSource()
    listing = Listing(
        id="test:vendu",
        title="VENDU — Villa avec piscine 4 façades",
        price=500_000,
        city="Wavre",
        address="",
        bedrooms=4,
        area=200.0,
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/vendu",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    assert source._is_valid(listing) is False


def test_base_source_validation_sous_option_rejected():
    source = ConcreteSource()
    listing = Listing(
        id="test:option",
        title="Sous option — Belle villa 4 chambres",
        price=480_000,
        city="Waterloo",
        address="",
        bedrooms=4,
        area=180.0,
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/option",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    assert source._is_valid(listing) is False


def test_base_source_validation_verkocht_rejected():
    source = ConcreteSource()
    listing = Listing(
        id="test:verkocht",
        title="Verkocht — Villa met zwembad",
        price=550_000,
        city="Overijse",
        address="",
        bedrooms=4,
        area=220.0,
        has_pool=True,
        has_parking=True,
        source="Test",
        url="https://example.com/verkocht",
        collected_at="2024-01-01T07:00:00+00:00",
    )
    assert source._is_valid(listing) is False
