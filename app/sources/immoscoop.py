"""Immoscoop source adapter — Tier 2."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmoScoopSource(BaseSource):
    """Scraper for Immoscoop.be — Tier 2 opportunity source."""

    name = "Immoscoop"
    tier = 2

    _SEARCH_URL = "https://www.immoscoop.be/fr/chercher/a-vendre/maison"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "max_price": MAX_PRICE,
            "min_rooms": MIN_BEDROOMS,
            "has_pool": 1,
            "sort": "date",
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
        # Cards are wrapped in <a href="/fr/a-vendre/..."> links
        cards = soup.select("a[href*='/fr/a-vendre/'] [class*='property-card'], [class*='property-card']")

        for card in cards:
            try:
                # Link is on the parent <a> element
                link_el = card.parent if card.parent and card.parent.name == "a" else card.select_one("a[href]")
                url = (link_el.get("href") or "") if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.immoscoop.be{url}"

                title_el = card.select_one("[class*='title'], h2, h3")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # City from card text: "Handelsstraat 43 2910 Essen" → postal + city
                text = card.get_text()
                pc_match = re.search(r"\b(\d{4})\s+([A-Za-zÀ-ÿ\s-]+)", text)
                postal_code = pc_match.group(1) if pc_match else ""
                city = pc_match.group(2).strip() if pc_match else ""

                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d+)/?(?:\?|$)", url)
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
