"""Abstract base class for all real estate source adapters."""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup

from app.config import (
    ALL_EXCLUSION_KEYWORDS,
    ALL_PARKING_KEYWORDS,
    DEFAULT_HEADERS,
    MAX_PRICE,
    MIN_AREA,
    MIN_BEDROOMS,
    MIN_PRICE,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    REQUEST_TIMEOUT,
    REQUIRE_PARKING,
    REQUIRE_POOL,
    TARGET_POSTAL_CODES,
)
from app.storage import Listing

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """Base class for all property listing scrapers.

    Subclasses may set ``pool_filtered_in_url = True`` when the search URL
    already restricts results to properties with a pool.  In that case the
    ``_is_valid`` helper skips the pool card-text check to avoid double-filtering.
    For all other sources, REQUIRE_POOL is enforced strictly: a listing must
    explicitly mention pool keywords in its card text to be included.
    """

    name: str = "unknown"
    tier: int = 3
    pool_filtered_in_url: bool = False  # set True when URL already filters by pool

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_listings(self) -> list[Listing]:
        """Fetch and return new listings matching the search criteria."""
        try:
            logger.info("[%s] Starting search...", self.name)
            listings = self._fetch()
            valid = [item for item in listings if self._is_valid(item)]
            if listings and not valid:
                sample_cities = list({item.city for item in listings[:5]})
                logger.debug(
                    "[%s] Filtered out all %d listings. Sample cities: %s",
                    self.name,
                    len(listings),
                    sample_cities,
                )
            logger.info("[%s] Found %d matching listings (from %d raw)", self.name, len(valid), len(listings))
            return valid
        except Exception as exc:
            logger.error("[%s] Error during fetch: %s", self.name, exc, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # To be implemented by each source
    # ------------------------------------------------------------------

    @abstractmethod
    def _fetch(self) -> list[Listing]:
        """Perform the actual search and return raw listings (before validation)."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict | None = None, headers: dict | None = None) -> requests.Response | None:
        """Perform a GET request with error handling and rate limiting."""
        self._rate_limit()
        try:
            # Strip None values from params so they are not sent as "None" strings
            if params:
                params = {k: v for k, v in params.items() if v is not None}
            h = {**DEFAULT_HEADERS, **(headers or {})}
            resp = self._session.get(url, params=params, headers=h, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            logger.warning("[%s] Timeout on %s", self.name, url)
        except requests.exceptions.HTTPError as exc:
            logger.warning("[%s] HTTP %s on %s", self.name, exc.response.status_code, url)
        except requests.exceptions.RequestException as exc:
            logger.warning("[%s] Request error: %s", self.name, exc)
        return None

    def _parse_html(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _is_valid(self, listing: Listing) -> bool:
        """Validate listing against core criteria (strict mode).

        All filters are hard-enforced:
        - price > 0 and within [MIN_PRICE, MAX_PRICE]
        - area >= MIN_AREA when both are known
        - bedrooms >= MIN_BEDROOMS when bedrooms > 0 (0 means unknown, pass through)
        - REQUIRE_POOL: listing must have has_pool=True (detected from card/description text)
        - REQUIRE_PARKING: listing must have has_parking=True
        - no exclusion keywords in title/address/city
        """
        if listing.price == 0:
            return False  # price=0 means "OPTION", "Prix sur demande", or parse error
        if MIN_PRICE is not None and listing.price < MIN_PRICE:
            return False
        if MAX_PRICE is not None and listing.price > MAX_PRICE:
            return False
        if MIN_AREA is not None and listing.area is not None and listing.area < MIN_AREA:
            return False
        # bedrooms=0 means "unknown" (card didn't show count) — pass through
        if MIN_BEDROOMS is not None and listing.bedrooms > 0 and listing.bedrooms < MIN_BEDROOMS:
            return False
        # Pool: strict for all sources — listing must explicitly mention pool keywords.
        # Sources with pool_filtered_in_url=True get pool guaranteed by the search URL,
        # so has_pool will be True from card text. Agency scrapers without card-level pool
        # info will yield 0 results, which is correct (no false positives).
        if REQUIRE_POOL and not listing.has_pool:
            return False
        if REQUIRE_PARKING and not listing.has_parking:
            return False
        text = (listing.title + " " + listing.address + " " + listing.city).lower()
        return all(kw.lower() not in text for kw in ALL_EXCLUSION_KEYWORDS)

    def _detect_parking(self, text: str) -> bool:
        """Return True if parking/garage keywords are found in the text."""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in ALL_PARKING_KEYWORDS)

    def _in_target_area(self, postal_code: str | None, city: str | None) -> bool:
        """Check if the property is in the target geographic area."""
        if postal_code and any(postal_code.startswith(p) for p in TARGET_POSTAL_CODES):
            return True
        if city:
            from app.config import TARGET_CITIES

            city_lower = city.lower()
            return any(tc.lower() in city_lower or city_lower in tc.lower() for tc in TARGET_CITIES)
        return False

    @staticmethod
    def _rate_limit() -> None:
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def _clean_price(self, raw: str) -> int:
        """Parse price string to integer EUR."""
        import re

        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else 0

    def _clean_int(self, raw: str | None) -> int:
        """Parse string to int safely."""
        if not raw:
            return 0
        import re

        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else 0
