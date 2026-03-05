"""SQLite-based persistent state management with deduplication."""

import hashlib
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.config import STATE_DB

logger = logging.getLogger(__name__)


@dataclass
class Listing:
    """Unified property listing model."""

    id: str  # unique identifier (source-specific ID or generated hash)
    title: str
    price: int  # in EUR
    city: str
    address: str
    bedrooms: int
    area: float | None  # in m², optional
    has_pool: bool
    source: str  # source site name
    url: str
    collected_at: str  # ISO 8601 datetime string

    @classmethod
    def make_id(  # noqa: PLR0913
        cls, source: str, native_id: str | None, url: str | None,
        city: str, address: str, price: int, bedrooms: int,
    ) -> str:
        """Generate a deterministic ID using deduplication priority rules."""
        if native_id:
            return f"{source}:{native_id}"
        if url:
            return f"url:{hashlib.sha256(url.encode()).hexdigest()[:16]}"
        # Fallback: hash of key fields
        key = f"{city}|{address}|{price}|{bedrooms}"
        return f"hash:{hashlib.sha256(key.encode()).hexdigest()[:16]}"


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the SQLite database schema."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price INTEGER NOT NULL,
                city TEXT NOT NULL,
                address TEXT,
                bedrooms INTEGER NOT NULL,
                area REAL,
                has_pool INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL,
                url TEXT,
                collected_at TEXT NOT NULL,
                notified INTEGER NOT NULL DEFAULT 0,
                notified_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_listings_notified ON listings(notified)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_listings_collected_at ON listings(collected_at)")
        conn.commit()
    logger.debug("Database initialized at %s", STATE_DB)


def is_known(listing_id: str) -> bool:
    """Return True if the listing ID already exists in the database."""
    with _get_conn() as conn:
        row = conn.execute("SELECT id FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return row is not None


def save_listing(listing: Listing) -> bool:
    """Persist a new listing. Returns True if inserted, False if already existed."""
    if is_known(listing.id):
        return False
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO listings
                (id, title, price, city, address, bedrooms, area, has_pool, source, url, collected_at, notified)
            VALUES
                (:id, :title, :price, :city, :address, :bedrooms, :area, :has_pool, :source, :url, :collected_at, 0)
            """,
            {**asdict(listing), "has_pool": int(listing.has_pool)},
        )
        conn.commit()
    logger.debug("Saved new listing: %s from %s", listing.id, listing.source)
    return True


def get_unnotified() -> list[Listing]:
    """Return listings that have not yet been emailed."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM listings WHERE notified = 0 ORDER BY collected_at DESC"
        ).fetchall()
    return [_row_to_listing(r) for r in rows]


def mark_notified(listing_ids: list[str]) -> None:
    """Mark the given listings as notified."""
    if not listing_ids:
        return
    notified_at = datetime.now(UTC).isoformat()
    with _get_conn() as conn:
        conn.executemany(
            "UPDATE listings SET notified = 1, notified_at = ? WHERE id = ?",
            [(notified_at, lid) for lid in listing_ids],
        )
        conn.commit()
    logger.debug("Marked %d listings as notified", len(listing_ids))


def count_all() -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM listings").fetchone()
        return int(row[0])


def _row_to_listing(row: sqlite3.Row) -> Listing:
    return Listing(
        id=row["id"],
        title=row["title"],
        price=row["price"],
        city=row["city"],
        address=row["address"] or "",
        bedrooms=row["bedrooms"],
        area=row["area"],
        has_pool=bool(row["has_pool"]),
        source=row["source"],
        url=row["url"] or "",
        collected_at=row["collected_at"],
    )
