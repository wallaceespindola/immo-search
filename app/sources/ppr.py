"""PPR Immo (Le Parcours du Propriétaire) source adapter — Tier 2 (Brabant Wallon specialist)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class PPRSource(BaseSource):
    """Scraper for PPR.be — Le Parcours du Propriétaire, based in Bierges/Wavre.

    Specialised Brabant Wallon agency since 1986.
    Uses OmniCasa Next.js platform — listings are server-rendered in HTML.
    """

    name = "PPR"
    tier = 2

    _SEARCH_URL = "https://www.ppr.be/fr/a-vendre/"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "type": "maison",
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
        }

        for page in range(1, 4):
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
        cards = soup.select("div.property-card")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.ppr.be{url}"
                if not url:
                    continue

                title_el = card.select_one("[class*='text-md'], [class*='text-lg'], [class*='line-clamp'], h2, h3")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one(".price, [class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # Location: "rue des lilas 9, 1474 genappe (ref. 2712)"
                location_el = card.select_one(".capitalize, [class*='locality'], [class*='city']")
                location_raw = location_el.get_text(strip=True) if location_el else ""
                pc_match = re.search(r"\b(\d{4})\b", location_raw)
                postal_code = pc_match.group(1) if pc_match else ""
                city = re.sub(r"\b\d{4}\b", "", location_raw).strip(" -,()").split(",")[-1].strip()

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?|bedrooms?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower or "pool" in text_lower
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d{3,})/?(?:\?|$|#)", url)
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
