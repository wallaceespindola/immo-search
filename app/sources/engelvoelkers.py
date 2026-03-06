"""Engel & Völkers Belgium source adapter — Tier 3 (luxury segment)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class EngelVolkersSource(BaseSource):
    """Scraper for Engel & Völkers Belgium — international luxury real estate network.

    Covers premium properties in Brussels, Brabant Wallon and surrounding areas.
    Uses the French-language Belgium search page.
    """

    name = "EngelVolkers"
    tier = 3

    _SEARCH_URL = "https://www.engelvoelkers.com/be/fr/proprietes/"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "transactionType": "buy",
            "realEstateType": "HOUSE",
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
            "country": "BE",
            "pageIndex": 0,
            "pageSize": 24,
        }

        resp = self._get(self._SEARCH_URL, params=params)
        if resp is None:
            return listings

        soup = self._parse_html(resp.text)
        listings.extend(self._parse_results(soup))
        return listings

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select(
            "article.ev-property-card, div.property-card, li.property-item, "
            "div[data-property-id], article.listing"
        )

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.engelvoelkers.com{url}"
                if not url:
                    continue

                title_el = card.select_one("h2, h3, .property-title, .ev-property-card__title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price'], [class*='prix'], .ev-property-card__price")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(
                    "[class*='city'], [class*='location'], [class*='locality'], .ev-property-card__location"
                )
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                pc_match = re.search(r"\b(1[3-9]\d{2}|5\d{3}|3\d{3})\b", text)
                postal_code = pc_match.group(1) if pc_match else ""

                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?|bedrooms?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower or "pool" in text_lower
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

                native_id = card.get("data-property-id", "")
                if not native_id and url:
                    m = re.search(r"/([A-Z0-9-]{5,})/?(?:\?|$)", url, re.I)
                    native_id = m.group(1) if m else ""

                listing_id = Listing.make_id(self.name, native_id, url, city, "", price, bedrooms)
                listings.append(
                    Listing(
                        id=listing_id,
                        title=title,
                        price=price,
                        city=city,
                        address="",
                        bedrooms=bedrooms,
                        area=area,
                        has_pool=has_pool,
                        has_parking=has_parking,
                        source=self.name,
                        url=url,
                        collected_at=self._now_iso(),
                    )
                )
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings
