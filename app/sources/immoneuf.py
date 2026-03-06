"""ImmoNeuf source adapter — Tier 3 (new construction portal)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmoNeufSource(BaseSource):
    """Scraper for ImmoNeuf.be — Belgian new-build property portal.

    Covers new construction houses (VEFA / off-plan and new builds)
    across Belgium, including Brabant Wallon developments.
    """

    name = "ImmoNeuf"
    tier = 3

    # immoneuf.be has SSL certificate issues — use zimmo new construction search as alternative
    _SEARCH_URL = "https://www.zimmo.be/fr/maisons-a-vendre/?filter=neuf"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
            "propertyType": "house",
            "transaction": "sale",
            "sort": "newest",
        }

        for page in range(1, 3):
            params["page"] = page
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
        cards = soup.select(
            "div.property-card, article.project-card, li.listing, div.result-item"
        )

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.zimmo.be{url}"

                title_el = card.select_one("h2, h3, .property-title, .project-title")
                title = title_el.get_text(strip=True) if title_el else "Maison neuve à vendre"

                price_el = card.select_one("[class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(
                    "[class*='city'], [class*='location'], [class*='locality'], [class*='commune']"
                )
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?|bedrooms?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower or "pool" in text_lower
                has_parking = self._detect_parking(text)

                if not self._in_target_area(None, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d{4,})/?(?:\?|$|-)", url)
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
