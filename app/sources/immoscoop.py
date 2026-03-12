"""Immoscoop source adapter — Tier 2."""

import json
import logging

from app.config import MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmoScoopSource(BaseSource):
    """Scraper for Immoscoop.be — Next.js SPA; listings extracted from __NEXT_DATA__ JSON."""

    name = "Immoscoop"
    tier = 2
    pool_filtered_in_url = True  # URL sends hasPool=true when REQUIRE_POOL

    _SEARCH_URL = "https://www.immoscoop.be/fr/chercher/a-vendre/maison"
    _BASE_URL = "https://www.immoscoop.be"
    _PROVINCES = ["brabant-wallon", "namur", "brabant-flamand"]

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        params: dict = {
            "maxPrice": MAX_PRICE,
            "minBedrooms": MIN_BEDROOMS,
        }
        if REQUIRE_POOL:
            params["hasPool"] = "true"

        for province in self._PROVINCES:
            province_params = {**params, "province": province}
            for page in range(1, 3):
                province_params["page"] = page
                resp = self._get(self._SEARCH_URL, params=province_params)
                if resp is None:
                    break

                soup = self._parse_html(resp.text)
                page_listings = self._parse_next_data(soup)
                if not page_listings:
                    break
                listings.extend(page_listings)

        return listings

    def _parse_next_data(self, soup) -> list[Listing]:
        listings = []
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            return []

        try:
            page_data = json.loads(script_tag.string)
        except Exception:
            return []

        # Listings are in dehydratedState.queries[-1].state.data.data
        queries = page_data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
        items = []
        for q in queries:
            data = q.get("state", {}).get("data", {})
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                items = data["data"]
                break

        for item in items:
            try:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.debug("[%s] Parse error: %s", self.name, exc)

        return listings

    def _parse_item(self, item: dict) -> Listing | None:
        native_id = str(item.get("id", "") or item.get("canonicalId", ""))
        price_raw = item.get("price", {}).get("slug", "0")
        price = int(price_raw) if str(price_raw).isdigit() else self._clean_price(str(price_raw))

        addr = item.get("address", {})
        postal_code = str(addr.get("postalCode", "") or "")
        city = (addr.get("city", {}) or {}).get("label", "") or (addr.get("municipality", {}) or {}).get("label", "")
        city = city.strip().title()

        features = {f["id"]: f.get("value", "") for f in item.get("features", [])}
        bedrooms = self._clean_int(str(features.get("BedroomNumber", "") or ""))
        area_raw = features.get("livableSurfaceArea") or features.get("LivableSurfaceArea")
        area = float(area_raw) if area_raw else None

        title = (item.get("title") or "Maison à vendre") if isinstance(item.get("title"), str) else "Maison à vendre"
        has_pool = self._detect_pool(title)
        has_parking = self._detect_parking(title)

        if not self._in_target_area(postal_code, city):
            return None

        # Build URL from city slug and id
        city_slug = (addr.get("city", {}) or {}).get("slug", "") or city.lower().replace(" ", "-")
        path = f"{city_slug}/{native_id}" if city_slug else native_id
        url = f"{self._BASE_URL}/fr/a-vendre/{path}"

        listing_id = Listing.make_id(self.name, native_id, url, city, "", price, bedrooms)
        return Listing(
            id=listing_id,
            title=title,
            price=price,
            city=city,
            address=f"{addr.get('street', '')} {(addr.get('houseNumber') or {}).get('number', '')}".strip(),
            bedrooms=bedrooms,
            area=area,
            has_pool=has_pool,
            has_parking=has_parking,
            source=self.name,
            url=url,
            collected_at=self._now_iso(),
        )
