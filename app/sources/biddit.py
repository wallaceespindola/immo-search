"""Biddit source adapter — Tier 2 (Belgian online property auctions)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class BidditSource(BaseSource):
    """Scraper for Biddit.be — Belgian online property auction platform."""

    name = "Biddit"
    tier = 2

    _SEARCH_URL = "https://biddit.be/catalog"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "type": "house",
            "max_price": MAX_PRICE,
            "region": "brabant-wallon",
            "sort": "date_desc",
        }

        resp = self._get(self._SEARCH_URL, params=params)
        if resp is None:
            return listings

        soup = self._parse_html(resp.text)
        listings.extend(self._parse_results(soup))
        return listings

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select("div.lot-card, article.property, div.auction-item")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://biddit.be{url}"

                title_el = card.select_one("h2, h3, .lot-title")
                title = title_el.get_text(strip=True) if title_el else "Propriété à enchérir"

                # Biddit shows estimate or starting price
                price_el = card.select_one("[class*='price'], [class*='estimate']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one("[class*='city'], [class*='location']")
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower
                has_parking = self._detect_parking(text)

                if bedrooms < MIN_BEDROOMS:
                    continue
                if not self._in_target_area(None, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/lot/(\d+)", url)
                    native_id = m.group(1) if m else ""

                listing_id = Listing.make_id(self.name, native_id, url, city, "", price, bedrooms)
                listings.append(Listing(
                    id=listing_id,
                    title=title,
                    price=price,
                    city=city,
                    address="",
                    bedrooms=bedrooms,
                    area=None,
                    has_pool=has_pool,
                    has_parking=has_parking,
                    source=self.name,
                    url=url,
                    collected_at=self._now_iso(),
                ))
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings
