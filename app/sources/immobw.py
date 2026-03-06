"""ImmoBW (Century 21 Immo BW) source adapter — Tier 2 (Wavre specialist)."""

import logging
import re

from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmoBWSource(BaseSource):
    """Scraper for ImmoBW.be — Century 21 franchise based in Wavre, Brabant Wallon."""

    name = "ImmoBW"
    tier = 2

    _SEARCH_URL = "https://www.immobw.be/fr/agence-immobiliere-wavre-maison-appartements-a-vendre"

    def _fetch(self) -> list[Listing]:
        resp = self._get(self._SEARCH_URL)
        if resp is None:
            return []

        soup = self._parse_html(resp.text)
        return self._parse_results(soup)

    def _parse_results(self, soup) -> list[Listing]:
        listings = []
        cards = soup.select("div.property, div.vm-col.vm-col-3, .product")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.immobw.be{url}"
                if not url:
                    continue

                title_el = card.select_one(".vmproduct_name, h2, h3")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one(".PricesalesPrice, .product-price, [class*='price']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # City/postal from card text: "3090 OVERIJSE" or "1301 Bierges"
                text = card.get_text()
                # Stop city capture at newline or non-alpha characters
                pc_match = re.search(r"\b(\d{4})\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ -]{1,30}?)(?=\s*[\n\r\d€]|$)", text)
                postal_code = pc_match.group(1) if pc_match else ""
                city = pc_match.group(2).strip().title() if pc_match else ""

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
                    m = re.search(r"/(\d{4,})/?(?:\?|$)", url)
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
