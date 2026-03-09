"""Les Viviers Immobilier source adapter — Tier 3 (Brabant Wallon & Namur)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class LesViviersSource(BaseSource):
    """Scraper for lesviviers.be — Brabant Wallon & Namur agency."""

    name = "LesViviers"
    tier = 3

    _SEARCH_URL = "https://www.lesviviers.be/biens/acheter/"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        base_params: dict = {
            "type": "maison",
            "prix_max": MAX_PRICE,
            "chambres_min": MIN_BEDROOMS,
        }
        if REQUIRE_POOL:
            base_params["piscine"] = 1

        for page in range(1, 3):
            params = {**base_params, "page": page}
            resp = self._get(self._SEARCH_URL, params=params)
            if resp is None:
                break

            soup = self._parse_html(resp.text)
            page_listings = self._parse_results(soup)
            if not page_listings:
                break
            listings.extend(page_listings)

        return listings

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select(".property-list-item, .property-link")

        for card in cards:
            try:
                link_el = card.select_one("a[href]") or (card if card.name == "a" else None)
                url = link_el["href"] if link_el and link_el.get("href") else ""
                if url and not url.startswith("http"):
                    url = f"https://www.lesviviers.be{url}"
                if not url:
                    continue

                title_el = card.select_one("h2, h3, [class*='title']")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one(".priceshow, [class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # Text format: "Nouveau Maison 1950 - KRAAINEM 2600m² 385m² 4 1.495.000€"
                text = card.get_text(" ", strip=True)
                # City appears after " - " (e.g. "Maison 1950 - KRAAINEM 2600m²")
                city = ""
                postal_code = ""
                city_match = re.search(
                    r" - ([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜ][A-ZÀ-Úa-zà-ú\s-]+?)(?:\s+\d|\s+m²|$)",
                    text,
                )
                if city_match:
                    city = city_match.group(1).strip().title()
                pc_match = re.search(r"\b(\d{4})\b", text)
                if pc_match:
                    postal_code = pc_match.group(1)

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
                    m = re.search(r"/(\d{4,})-", url)
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
