"""Immovlan source adapter — Tier 1."""

import logging
import re

from app.config import EPC_RATINGS, MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL, TARGET_POSTAL_CODES
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)

_POSTAL_CODES_STR = ",".join(TARGET_POSTAL_CODES[:30])


class ImmovlanSource(BaseSource):
    """Scraper for Immovlan.be — major Belgian property portal."""

    name = "Immovlan"
    tier = 1

    _SEARCH_URL = "https://immovlan.be/fr/immobilier"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        tags = "hasgarage"
        if REQUIRE_POOL:
            tags = "hasswimmingpool,hasgarage"

        params: dict = {
            "transactiontypes": "a-vendre,en-vente-publique",
            "propertytypes": "maison,garage",
            "propertysubtypes": "maison,villa,bungalow,chalet,fermette,maison-de-maitre,chateau",
            "provinces": "brabant-flamand,brabant-wallon,namur",
            "tags": tags,
            "maxprice": MAX_PRICE,
            "minbedrooms": MIN_BEDROOMS,
            "orderby": "date_desc",
        }
        if EPC_RATINGS:
            params["epcratings"] = ",".join(EPC_RATINGS)

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
                    url = f"https://immovlan.be{url}"

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
                has_parking = self._detect_parking(text)

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
                    has_parking=has_parking,
                    source=self.name,
                    url=url,
                    collected_at=self._now_iso(),
                ))
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings
