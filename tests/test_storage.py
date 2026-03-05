"""Unit tests for app/storage.py."""

from unittest.mock import patch

import pytest

from app.storage import Listing, get_unnotified, init_db, is_known, mark_notified, save_listing


def _make_listing(
    listing_id: str = "test:1",
    price: int = 450_000,
    city: str = "Wavre",
    bedrooms: int = 4,
    has_pool: bool = True,
    has_parking: bool = True,
) -> Listing:
    return Listing(
        id=listing_id,
        title="Belle villa avec piscine",
        price=price,
        city=city,
        address="Rue du Test 1",
        bedrooms=bedrooms,
        area=250.0,
        has_pool=has_pool,
        has_parking=has_parking,
        source="TestSource",
        url="https://example.com/1",
        collected_at="2024-01-01T07:00:00+00:00",
    )


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Redirect STATE_DB to a temp file for each test."""
    db_path = tmp_path / "state_test.sqlite"
    with patch("app.storage.STATE_DB", db_path):
        yield db_path


def test_init_db_creates_table(temp_db):
    init_db()
    assert temp_db.exists()


def test_save_and_retrieve_new_listing(temp_db):
    init_db()
    listing = _make_listing()
    result = save_listing(listing)
    assert result is True


def test_duplicate_listing_not_saved(temp_db):
    init_db()
    listing = _make_listing()
    save_listing(listing)
    result = save_listing(listing)
    assert result is False


def test_is_known_returns_true_after_save(temp_db):
    init_db()
    listing = _make_listing()
    save_listing(listing)
    assert is_known(listing.id) is True


def test_is_known_returns_false_for_unknown(temp_db):
    init_db()
    assert is_known("nonexistent:999") is False


def test_get_unnotified_returns_saved_listings(temp_db):
    init_db()
    listing = _make_listing()
    save_listing(listing)
    unnotified = get_unnotified()
    assert len(unnotified) == 1
    assert unnotified[0].id == listing.id


def test_mark_notified_clears_pending(temp_db):
    init_db()
    listing = _make_listing()
    save_listing(listing)
    mark_notified([listing.id])
    unnotified = get_unnotified()
    assert len(unnotified) == 0


def test_listing_make_id_with_native_id():
    lid = Listing.make_id("Immoweb", "12345", None, "Wavre", "", 450000, 4)
    assert lid == "Immoweb:12345"


def test_listing_make_id_with_url():
    lid = Listing.make_id("Zimmo", None, "https://example.com/property/99", "Wavre", "", 400000, 4)
    assert lid.startswith("url:")


def test_listing_make_id_hash_fallback():
    lid = Listing.make_id("Test", None, None, "Waterloo", "Rue A 1", 500000, 5)
    assert lid.startswith("hash:")


def test_multiple_listings_saved(temp_db):
    init_db()
    for i in range(5):
        listing = _make_listing(listing_id=f"test:{i}", city=f"City{i}")
        save_listing(listing)
    unnotified = get_unnotified()
    assert len(unnotified) == 5
