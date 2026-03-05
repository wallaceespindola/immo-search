"""Immovlan source adapter — Tier 1."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmovlanSource(BaseSource):
    """Scraper for Immovlan.be — major Belgian property portal."""

    name = "Immovlan"
    tier = 1

    _SEARCH_URL = "https://immo.vlan.be/fr/search"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params = {
            "transactiontype": "for-sale",
            "propertytype": "house",
            "maxprice": MAX_PRICE,
            "minrooms": MIN_BEDROOMS,
            "amenities": "swimming-pool",
            "postalcodes": ",".join(["1300", "1310", "1330", "1340", "1348", "1380", "1410", "1420", "1400", "1470"]),
            "orderby": "date_desc",
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
        cards = soup.select("div.property-card, article.result, li[data-id]")

        for card in cards:
            try:
                native_id = card.get("data-id", "")
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://immo.vlan.be{url}"

                title_el = card.select_one("h2, h3, .title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one("[class*='city'], [class*='location'], [class*='locality']")
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                text_lower = text.lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower

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
                    area=area,
                    has_pool=has_pool,
                    source=self.name,
                    url=url,
                    collected_at=self._now_iso(),
                ))
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings
