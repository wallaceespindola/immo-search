"""Cap Sud source adapter — Tier 2 (Brussels & Wallonia agency network)."""

import logging
import re

from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class CapSudSource(BaseSource):
    """Scraper for Cap-Sud.com — real estate agency network in Brussels and Wallonia.

    Network of agencies active since 1994, covering Brabant Wallon and surrounding areas.
    """

    name = "CapSud"
    tier = 2

    _SEARCH_URL = "https://cap-sud.com/recherche/"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        # estate_purposes:1978 = vente (for sale) on this WordPress/JetEngine site
        params = {
            "jsf": "epro-loop-builder:wa_biens",
            "tax": "estate_purposes:1978",
        }

        resp = self._get(self._SEARCH_URL, params=params)
        if resp is None:
            return listings

        soup = self._parse_html(resp.text)
        listings.extend(self._parse_results(soup))
        return listings

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select(
            "div.property-card, article.jet-listing-grid__item, div.listing-item, "
            "article.elementor-post, div.well, li.property"
        )

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://cap-sud.com{url}"
                if not url:
                    continue

                title_el = card.select_one("h2, h3, .property-title, .entry-title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                city_el = card.select_one(
                    "[class*='city'], [class*='location'], [class*='locality'], [class*='commune']"
                )
                city = city_el.get_text(strip=True) if city_el else ""

                text = card.get_text()
                pc_match = re.search(r"\b(1[3-9]\d{2}|5\d{3}|3\d{3})\b", text)
                postal_code = pc_match.group(1) if pc_match else ""

                bed_match = re.search(r"(\d+)\s*(?:ch(?:ambres?)?|slaapkamers?)", text, re.I)
                bedrooms = int(bed_match.group(1)) if bed_match else 0

                area_match = re.search(r"(\d+)\s*m²", text, re.I)
                area = float(area_match.group(1)) if area_match else None

                has_pool = self._detect_pool(text)
                has_parking = self._detect_parking(text)

                if not self._in_target_area(postal_code, city):
                    continue

                native_id = ""
                if url:
                    m = re.search(r"/(\d{3,})/?(?:\?|$|-)", url)
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
