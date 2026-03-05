"""Zimmo source adapter — Tier 1."""

import logging

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ZimmoSource(BaseSource):
    """Scraper for Zimmo.be — major Belgian property portal."""

    name = "Zimmo"
    tier = 1

    _SEARCH_URL = "https://www.zimmo.be/fr/rechercher/"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []
        params = {
            "search": json.dumps({
                "type": {"or": ["HOUSE"]},
                "price": {"max": MAX_PRICE},
                "bedrooms": {"min": MIN_BEDROOMS},
                "features": {"has_swimming_pool": True},
                "status": {"or": ["NORMAL", "ON_FUNDA"]},
            }),
            "sort": "date_desc",
            "page": 1,
        }

        for page in range(1, 4):
            params["page"] = page
            resp = self._get(self._SEARCH_URL, params={"page": page})
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
        cards = soup.select("article.property-item, div.property-list__item, li.search-result")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.zimmo.be{url}"

                title_el = card.select_one("h2, h3, .property-title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one(".property-price, [class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(".property-city, .location, [class*='locality']")
                city = city_el.get_text(strip=True) if city_el else ""

                bed_el = card.select_one("[class*='bedroom'], [class*='slaapkamer'], [class*='chambre']")
                bedrooms = self._clean_int(bed_el.get_text(strip=True) if bed_el else "0")
                if bedrooms == 0:
                    import re
                    bed_match = re.search(r"(\d+)\s*(?:chambres?|slaapkamers?|ch\.)", card.get_text(), re.I)
                    bedrooms = int(bed_match.group(1)) if bed_match else 0

                text_lower = card.get_text().lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower

                native_id = ""
                if url:
                    import re
                    m = re.search(r"/(\d+)/?$", url)
                    native_id = m.group(1) if m else ""

                if not self._in_target_area(None, city):
                    continue

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
                    source=self.name,
                    url=url,
                    collected_at=self._now_iso(),
                ))
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings


# Fix missing import at module level
import json  # noqa: E402 — needed for params dict above
