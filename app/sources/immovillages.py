"""ImmoVillages source adapter — Tier 3 (rural/village properties)."""

import logging
import re

from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmoVillagesSource(BaseSource):
    """Scraper for ImmoVillages.com — Belgian rural and village property portal.

    Specializes in properties in Belgian villages and countryside,
    relevant for Brabant Wallon and Namur regions.
    """

    name = "ImmoVillages"
    tier = 3

    _SEARCH_URL = "https://immovillages.com/fr/sale"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        resp = self._get(self._SEARCH_URL)
        if resp is None:
            return listings

        soup = self._parse_html(resp.text)
        listings.extend(self._parse_results(soup))
        return listings

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select(
            "div.property-card, article.property, li.listing, div.card, "
            "div[class*='property'], article[class*='listing']"
        )

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://immovillages.com{url}"
                if not url:
                    continue

                title_el = card.select_one("h2, h3, .property-title, .card-title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(
                    "[class*='city'], [class*='location'], [class*='locality'], [class*='commune']"
                )
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                pc_match = re.search(r"\b(1[3-9]\d{2}|5\d{3}|3\d{3})\b", text)
                postal_code = pc_match.group(1) if pc_match else ""

                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?|bedrooms?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d{3,})/?(?:\?|$|-)", url)
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
