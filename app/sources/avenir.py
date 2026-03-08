"""Avenir Immobilier source adapter — Tier 2 (Wavre & Namur region)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class AvenirSource(BaseSource):
    """Scraper for avenir-immobilier.be — 25-year Wavre specialist."""

    name = "Avenir"
    tier = 2

    _SEARCH_URL = "https://avenir-immobilier.be/fr/acheter/maison"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
            "order": "date_desc",
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
        cards = soup.select("div.property-card, div.property-details")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://avenir-immobilier.be{url}"
                if not url:
                    continue

                title_el = card.select_one("h2, h3, [class*='title']")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one("[class*='city'], [class*='location'], [class*='locality']")
                city_raw = city_el.get_text(strip=True) if city_el else ""
                pc_match = re.search(r"\b(\d{4})\b", city_raw)
                postal_code = pc_match.group(1) if pc_match else ""
                # Also try to extract from URL: /fr/detail/7597114/vente/maison/floreffe
                if not city_raw:
                    url_city = re.search(r"/maison/([^/?#]+)$", url)
                    city_raw = url_city.group(1).replace("-", " ").title() if url_city else ""
                city = re.sub(r"\b\d{4}\b", "", city_raw).strip(" -,")

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m(?:²|2)\b", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
                has_parking = self._detect_parking(text)

                if postal_code and not self._in_target_area(postal_code, city):
                    continue
                if not postal_code and not self._in_target_area(None, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d{5,})/?", url)
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
