"""Promimo source adapter — Tier 2 (Brabant Wallon specialist)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class PromimoSource(BaseSource):
    """Scraper for Promimo.be — real estate agency specialized in Brabant Wallon.

    One of the most relevant local agencies for the primary target area.
    """

    name = "Promimo"
    tier = 2
    pool_filtered_in_url = True  # URL sends piscine=1 when REQUIRE_POOL

    _SEARCH_URL = "https://www.promimo.be/biens-a-vendre"

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
        # Promimo uses <a class="estate teaser"> inside .properties-list
        cards = soup.select("a.estate.teaser")

        for card in cards:
            try:
                url = card.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://www.promimo.be{url}"
                if not url:
                    continue

                # City is in the URL: /biens-a-vendre/maison/{city}/{id}
                city = ""
                native_id = ""
                m_url = re.search(r"/maison/([^/]+)/(\d+)", url)
                if m_url:
                    city = m_url.group(1).replace("-", " ").title()
                    native_id = m_url.group(2)

                text = card.get_text()

                price_el = card.select_one(".priceshow, [class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # Postal code: try from text
                pc_match = re.search(r"\b(1[3-9]\d{2}|5\d{3}|3\d{3})\b", text)
                postal_code = pc_match.group(1) if pc_match else ""

                # Title from description text (after city header)
                title_el = card.select_one("h2, h3, p")
                title = title_el.get_text(strip=True) if title_el else f"Maison à vendre - {city}"

                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

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
