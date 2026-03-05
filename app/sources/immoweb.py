"""Immoweb source adapter — Tier 1."""

import json
import logging

from app.config import MAX_PRICE, MIN_BEDROOMS, TARGET_POSTAL_CODES
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)


class ImmowebSource(BaseSource):
    """Scraper for Immoweb.be — Belgium's largest property portal."""

    name = "Immoweb"
    tier = 1

    # Immoweb search API endpoint (returns JSON results)
    _SEARCH_URL = "https://www.immoweb.be/en/search/house/for-sale"

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []
        postal_codes_str = ",".join(f"BE-{pc}" for pc in TARGET_POSTAL_CODES[:20])  # API limit

        params = {
            "countries": "BE",
            "maxPrice": MAX_PRICE,
            "minBedroomCount": MIN_BEDROOMS,
            "hasSwimmingPool": "true",
            "postalCodes": postal_codes_str,
            "orderBy": "newest",
            "page": 1,
        }

        for page in range(1, 4):  # fetch up to 3 pages
            params["page"] = page
            resp = self._get(self._SEARCH_URL, params=params, headers={"Accept": "application/json"})
            if resp is None:
                break

            # Try to parse as JSON (Immoweb returns JSON when Accept: application/json)
            try:
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break
                for item in results:
                    listing = self._parse_item(item)
                    if listing:
                        listings.append(listing)
            except (json.JSONDecodeError, ValueError):
                # Fallback: parse HTML
                soup = self._parse_html(resp.text)
                page_listings = self._parse_html_results(soup)
                listings.extend(page_listings)
                if not page_listings:
                    break

        return listings

    def _parse_item(self, item: dict) -> Listing | None:
        """Parse a JSON result item from Immoweb API."""
        try:
            property_data = item.get("property", item)
            transaction = item.get("transaction", {})

            native_id = str(item.get("id", "") or property_data.get("id", ""))
            title = property_data.get("title", "") or item.get("title", "Maison à vendre")
            price_raw = transaction.get("sale", {}).get("price") or item.get("price", 0)
            price = int(price_raw) if price_raw else 0

            location = property_data.get("location", {})
            city = location.get("locality", "") or location.get("city", "")
            postal_code = str(location.get("postalCode", "") or location.get("zip", ""))
            address = location.get("street", "") or ""
            if location.get("number"):
                address += f" {location['number']}"

            bedrooms = int(property_data.get("bedroomCount", 0) or 0)
            area = property_data.get("netHabitableSurface") or property_data.get("livingArea")
            area = float(area) if area else None

            has_pool = bool(
                property_data.get("hasSwimmingPool")
                or property_data.get("swimmingPool")
                or "piscine" in title.lower()
                or "zwembad" in title.lower()
            )

            url = item.get("url", "") or f"https://www.immoweb.be/en/classified/{native_id}"
            if not url.startswith("http"):
                url = f"https://www.immoweb.be{url}"

            if not self._in_target_area(postal_code, city):
                return None

            listing_id = Listing.make_id(self.name, native_id, url, city, address, price, bedrooms)

            return Listing(
                id=listing_id,
                title=title,
                price=price,
                city=city,
                address=address,
                bedrooms=bedrooms,
                area=area,
                has_pool=has_pool,
                source=self.name,
                url=url,
                collected_at=self._now_iso(),
            )
        except Exception as exc:
            logger.debug("[%s] Failed to parse item: %s", self.name, exc)
            return None

    def _parse_html_results(self, soup) -> list[Listing]:
        """HTML fallback parser for Immoweb search results page."""
        listings = []
        for card in soup.select("article.card--result, [data-classified-id]"):
            try:
                native_id = card.get("data-classified-id", "")
                title_el = card.select_one("h2.card__title, .card--result__title")
                title = title_el.get_text(strip=True) if title_el else "Maison à vendre"

                price_el = card.select_one("[data-testid='price'], .card--result__price, p.card__price")
                price_str = price_el.get_text(strip=True) if price_el else "0"
                price = self._clean_price(price_str)

                city_el = card.select_one(".card--result__locality, [data-testid='locality']")
                city = city_el.get_text(strip=True) if city_el else ""

                rooms_el = card.select_one("[aria-label*='bedroom'], [data-testid='bedroom-count']")
                bedrooms = self._clean_int(rooms_el.get_text(strip=True) if rooms_el else "0")

                link_el = card.select_one("a[href*='/classified/']")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.immoweb.be{url}"

                text_lower = card.get_text().lower()
                has_pool = "piscine" in text_lower or "zwembad" in text_lower

                listing_id = Listing.make_id(self.name, native_id, url, city, "", price, bedrooms)
                listings.append(Listing(
                    id=listing_id,
                    title=title,
                    price=price,
                    city=city,
                    address="",
                    bedrooms=bedrooms,
                    area=None,
                    has_pool=has_pool,
                    source=self.name,
                    url=url,
                    collected_at=self._now_iso(),
                ))
            except Exception as exc:
                logger.debug("[%s] HTML parse error: %s", self.name, exc)
        return listings
