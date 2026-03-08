"""Dewaele source adapter — Tier 2 (major Flemish agency)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class DewaeleSource(BaseSource):
    """Scraper for Dewaele — one of Belgium's largest real estate groups."""

    name = "Dewaele"
    tier = 2
    pool_filtered_in_url = True  # URL already filters by pool

    _SEARCH_URL = "https://www.dewaele.com/fr/a-vendre/tout/maisons"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
            "propertyType": "house",
            "transaction": "buy",
            "pool": "true",
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
        cards = soup.select("div.property-card, article.property, li.result, div.listing-card")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.dewaele.com{url}"

                title_el = card.select_one("h2, h3, .property-title, .card-title")
                title = title_el.get_text(strip=True) if title_el else "Woning te koop"

                price_el = card.select_one("[class*='price'], [class*='prijs']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(
                    "[class*='city'], [class*='location'], [class*='locality'], [class*='gemeente']"
                )
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:slaapkamers?|ch(?:ambres?)?|bedrooms?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
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
