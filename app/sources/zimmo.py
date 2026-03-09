"""Zimmo source adapter — Tier 1 (JSON extraction from embedded script)."""

import json
import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS, REQUIRE_POOL
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ZimmoSource(BaseSource):
    """Scraper for Zimmo.be — major Belgian property portal.

    Extracts property data from the JSON embedded in the page's app.start() script.
    Uses separate regional search URLs for Brabant Wallon (city-level) and Namur.
    """

    name = "Zimmo"
    tier = 1
    pool_filtered_in_url = True  # URL includes ?features=has_swimming_pool:true

    # Region slugs that return results: city-level for BW, province-level for Namur + VBR
    _REGION_URLS = [
        "https://www.zimmo.be/fr/wavre-1300/a-vendre/maison/",
        "https://www.zimmo.be/fr/ottignies-louvain-la-neuve-1340/a-vendre/maison/",
        "https://www.zimmo.be/fr/rixensart-1330/a-vendre/maison/",
        "https://www.zimmo.be/fr/la-hulpe-1310/a-vendre/maison/",
        "https://www.zimmo.be/fr/genval-1332/a-vendre/maison/",
        "https://www.zimmo.be/fr/namur/a-vendre/maison/",
        "https://www.zimmo.be/fr/province-du-brabant-flamand/a-vendre/maison/",
    ]

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []
        seen_codes: set[str] = set()

        qs_parts = [f"min_bedrooms={MIN_BEDROOMS}", f"max_price={MAX_PRICE}"]
        if REQUIRE_POOL:
            qs_parts.append("features=has_swimming_pool:true")
        filter_qs = "&".join(qs_parts)

        for base_url in self._REGION_URLS:
            url = base_url + "?" + filter_qs
            resp = self._get(url)
            if resp is None:
                continue

            page_listings = self._parse_script(resp.text, seen_codes)
            listings.extend(page_listings)

        return listings

    def _parse_script(self, html: str, seen_codes: set[str]) -> list[Listing]:
        """Extract properties from the embedded app.start() JSON script."""
        listings = []

        # Find the app.start({...properties: [...]...}) script
        m_start = re.search(r"properties:\s*\[", html)
        if not m_start:
            return listings

        start = m_start.end() - 1  # position of '['
        depth = 0
        end = start
        for i in range(start, min(start + 300_000, len(html))):
            c = html[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        try:
            props = json.loads(html[start:end])
        except (json.JSONDecodeError, ValueError):
            return listings

        for item in props:
            try:
                code = item.get("code", "")
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)

                url_path = item.get("url", "") or item.get("pand_url", "")
                url = f"https://www.zimmo.be{url_path}" if url_path and not url_path.startswith("http") else url_path
                if not url:
                    continue

                price = int(item.get("prijs") or item.get("zprijs") or 0)
                city = (item.get("gemeente") or "").strip()
                postal_code = str(item.get("postcode") or "")
                bedrooms = int(item.get("slaapkamers") or 0)
                area_raw = item.get("b_woonopp")
                area = float(area_raw) if area_raw else None
                title = item.get("type", "Maison à vendre")

                # Pool/parking detection: use any available text
                description = str(item.get("a_beschrijf") or item.get("html") or "")
                has_pool = self._detect_pool(description)
                has_parking = self._detect_parking(description)

                if not self._in_target_area(postal_code, city):
                    continue

                listing_id = Listing.make_id(self.name, code, url, city, "", price, bedrooms)
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
