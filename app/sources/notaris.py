"""notaris.be source adapter — Tier 2 (JSON API)."""

import logging
import re

from app.config import MAX_PRICE, MIN_BEDROOMS, TARGET_POSTAL_CODES
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class NotarisSource(BaseSource):
    """Scraper for notaris.be — Official Belgian Notary Federation property listings.

    The notary federation publishes properties sold at public auction and private sale.
    Uses their JSON search API when available, falling back to HTML parsing.
    """

    name = "Notaris"
    tier = 2
    pool_filtered_in_url = True  # URL already filters by pool

    _API_URL = "https://immo.notaris.be/api/properties"
    _BASE_SEARCH_URL = "https://immo.notaris.be/fr/biens-a-vendre-dans-la-province"
    # Province codes: WBR=Brabant Wallon, NAM=Namur, VBR=Brabant Flamand
    _PROVINCES = [
        ("brabant-wallon", "WBR"),
        ("namur", "NAM"),
        ("brabant-flamand", "VBR"),
    ]

    def _fetch(self) -> list[Listing]:
        # Try JSON API first
        listings = self._fetch_api()
        if listings:
            return listings
        # Fallback to HTML
        return self._fetch_html()

    def _fetch_api(self) -> list[Listing]:
        """Attempt to fetch via notaris.be JSON API."""
        listings: list[Listing] = []
        postal_codes = TARGET_POSTAL_CODES[:20]

        for page in range(1, 3):
            params = {
                "type": "house",
                "transaction": "sale",
                "maxPrice": MAX_PRICE,
                "minBedrooms": MIN_BEDROOMS,
                "postalCodes": ",".join(postal_codes),
                "page": page,
                "limit": 30,
                "sort": "date_desc",
            }
            resp = self._get(self._API_URL, params=params)
            if resp is None:
                break

            try:
                data = resp.json()
            except Exception:
                break

            items = data.get("items", data.get("results", data.get("properties", [])))
            if not items:
                break

            for item in items:
                listing = self._parse_api_item(item)
                if listing:
                    listings.append(listing)

        return listings

    def _fetch_html(self) -> list[Listing]:
        """Fall back to HTML scraping of notaris.be search results across all three provinces."""
        listings: list[Listing] = []

        base_params: dict = {
            "type": "maison",
            "transaction": "vente",
            "prix_max": MAX_PRICE,
            "chambres_min": MIN_BEDROOMS,
            "piscine": 1,
            "order": "date_desc",
        }

        for province_slug, province_code in self._PROVINCES:
            url = f"{self._BASE_SEARCH_URL}/{province_slug}?province={province_code}"
            for page in range(1, 3):
                params = {**base_params, "page": page}
                resp = self._get(url, params=params)
                if resp is None:
                    break

                soup = self._parse_html(resp.text)
                page_listings = self._parse_html_results(soup)
                if not page_listings:
                    break
                listings.extend(page_listings)

        return listings

    def _parse_api_item(self, item: dict) -> Listing | None:
        """Parse a JSON item from the notaris.be API."""
        try:
            native_id = str(item.get("id", "") or item.get("reference", ""))
            title = item.get("title", item.get("type", "Maison à vendre"))
            price = int(item.get("price", item.get("askingPrice", 0)) or 0)

            loc = item.get("location", item.get("address", {}))
            city = loc.get("city", loc.get("locality", loc.get("municipality", "")))
            postal_code = str(loc.get("postalCode", loc.get("zip", "")))
            address = loc.get("street", "")
            if loc.get("number"):
                address += f" {loc['number']}"

            bedrooms = int(item.get("bedrooms", item.get("bedroomCount", 0)) or 0)
            area_raw = item.get("livingArea", item.get("surface", item.get("area")))
            area = float(area_raw) if area_raw else None

            text = f"{title} {item.get('description', '')}".lower()
            has_pool = bool(item.get("hasPool") or item.get("swimmingPool")) or self._detect_pool(text)
            has_parking = bool(item.get("hasGarage") or item.get("parking")) or self._detect_parking(text)

            url = item.get("url", item.get("link", ""))
            if url and not url.startswith("http"):
                url = f"https://www.notaris.be{url}"
            if not url and native_id:
                url = f"https://immo.notaris.be/fr/bien/{native_id}"

            if not self._in_target_area(postal_code, city):
                return None

            lid = Listing.make_id(self.name, native_id, url, city, address, price, bedrooms)
            return Listing(
                id=lid,
                title=title,
                price=price,
                city=city,
                address=address,
                bedrooms=bedrooms,
                area=area,
                has_pool=has_pool,
                has_parking=has_parking,
                source=self.name,
                url=url,
                collected_at=self._now_iso(),
            )
        except Exception as exc:
            logger.debug("[%s] API parse error: %s", self.name, exc)
            return None

    def _parse_html_results(self, soup) -> list[Listing]:
        """Parse HTML search results from notaris.be."""
        listings = []
        # Notaris uses <li class="property__item"> with link on the <a> wrapper
        cards = soup.select("li.property__item, div.property-card, article.property")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://immo.notaris.be{url}"

                title_el = card.select_one("h2, h3, .h3, .property-title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one(".property__item--price, [class*='price'], [class*='prix']")
                price = self._clean_price(price_el.get_text(strip=True) if price_el else "0")

                # URL contains postal code and city: /fr/title/a-vendre/27-rue-X-1473-glabais/178300
                postal_code = ""
                city = ""
                if url:
                    pc_match = re.search(r"-(\d{4})-([a-z-]+)/\d+$", url)
                    if pc_match:
                        postal_code = pc_match.group(1)
                        city = pc_match.group(2).replace("-", " ").title()

                text = card.get_text()
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
                logger.debug("[%s] HTML parse error: %s", self.name, exc)

        return listings
