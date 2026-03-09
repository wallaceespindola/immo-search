"""Altis Immobilier source adapter — Tier 2 (Brabant Wallon since 2002)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class AltisSource(BaseSource):
    """Scraper for altis.be — Brabant Wallon agency since 2002."""

    name = "Altis"
    tier = 2
    pool_filtered_in_url = True  # Pool info not shown in listing cards; rely on area/city filtering

    _SEARCH_URL = "https://www.altis.be/a-vendre/"

    def _fetch(self) -> list[Listing]:
        params: dict = {"prix_max": MAX_PRICE, "chambres_min": MIN_BEDROOMS}
        if REQUIRE_POOL:
            params["piscine"] = 1
        resp = self._get(self._SEARCH_URL, params=params)
        if resp is None:
            return []

        soup = self._parse_html(resp.text)
        return self._parse_results(soup)

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        # Each card is wrapped in <a class="bien" href="...">
        cards = soup.select("a.bien")

        for card in cards:
            try:
                url = card.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://www.altis.be{url}"
                if not url:
                    continue

                title = "Maison à vendre"  # Altis cards don't include title in listing grid

                price_el = card.select_one(".bien_price")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(".bien_city")
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
                has_parking = self._detect_parking(text)

                if not self._in_target_area(None, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"code=(\w+)", url)
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
