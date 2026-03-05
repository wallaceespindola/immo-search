"""Immoweb source adapter — Tier 1 (Playwright-based SPA scraper)."""

import contextlib
import json
import logging
import re
import time

from app.config import MAX_PRICE, MIN_BEDROOMS, TARGET_POSTAL_CODES
from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)

# Postal codes to include in the Immoweb search URL (max ~20 for URL length)
_SEARCH_POSTAL_CODES = ",".join(f"BE-{pc}" for pc in TARGET_POSTAL_CODES[:25])

_SEARCH_URL = (
    "https://www.immoweb.be/en/search/house/for-sale"
    f"?countries=BE"
    f"&maxPrice={MAX_PRICE}"
    f"&minBedroomCount={MIN_BEDROOMS}"
    f"&hasSwimmingPool=true"
    f"&postalCodes={_SEARCH_POSTAL_CODES}"
    f"&orderBy=newest"
)


class ImmowebSource(BaseSource):
    """Scraper for Immoweb.be — Belgium's largest property portal.

    Immoweb is a React SPA — content is rendered client-side via XHR.
    Uses Playwright (headless Chromium) to intercept the JSON API responses
    made by the browser's JavaScript engine.
    """

    name = "Immoweb"
    tier = 1

    def _fetch(self) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("[Immoweb] playwright not installed. Run: uv run playwright install chromium")
            return []

        listings: list[Listing] = []
        intercepted: list[dict] = []

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="fr-BE",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/121.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()

                def _on_response(response):
                    """Intercept XHR responses that contain listing data."""
                    url = response.url
                    is_api = "api/classifieds/search" in url
                    is_search = "search" in url and "immoweb" in url and response.status == 200
                    if is_api or is_search:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            try:
                                body = response.json()
                                if isinstance(body, dict) and ("results" in body or "classifieds" in body):
                                    intercepted.append(body)
                                    logger.debug("[Immoweb] Intercepted API response from %s", url)
                            except Exception:
                                pass

                page.on("response", _on_response)

                for page_num in range(1, 4):
                    page_url = f"{_SEARCH_URL}&page={page_num}"
                    logger.debug("[Immoweb] Loading page %d: %s", page_num, page_url)
                    try:
                        page.goto(page_url, wait_until="networkidle", timeout=30_000)
                        time.sleep(2)  # let XHR settle
                    except Exception as exc:
                        logger.warning("[Immoweb] Page load timeout on page %d: %s", page_num, exc)

                    # Also try to extract data from page's DOM
                    dom_listings = self._extract_from_dom(page)
                    listings.extend(dom_listings)

                    if not dom_listings and page_num > 1:
                        break

                browser.close()

            # Parse intercepted API responses
            for data in intercepted:
                results = data.get("results", data.get("classifieds", []))
                for item in results:
                    listing = self._parse_api_item(item)
                    if listing:
                        listings.append(listing)

        except Exception as exc:
            logger.error("[Immoweb] Playwright error: %s", exc, exc_info=True)

        # Deduplicate by URL within this batch
        seen: set[str] = set()
        unique: list[Listing] = []
        for item in listings:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        return unique

    def _extract_from_dom(self, page) -> list[Listing]:
        """Extract listings from the rendered DOM via Playwright page evaluation."""
        listings: list[Listing] = []
        try:
            cards = page.query_selector_all("article.card--result, [data-classified-id]")
            if not cards:
                # Try to extract from embedded JSON in page scripts
                json_data = page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script');
                    for (const s of scripts) {
                        const t = s.textContent || '';
                        if (t.includes('"results"') && t.includes('"classified"')) {
                            try { return JSON.parse(t); } catch(e) {}
                        }
                    }
                    return null;
                }""")
                if json_data and "results" in json_data:
                    for result in json_data["results"]:
                        parsed = self._parse_api_item(result)
                        if parsed:
                            listings.append(parsed)
                return listings

            for card in cards:
                try:
                    native_id = card.get_attribute("data-classified-id") or ""
                    title_el = card.query_selector("h2, .card__title, .card--result__title")
                    title = title_el.inner_text().strip() if title_el else "Maison à vendre"

                    # Price: look for iw-price component's :price JSON attribute
                    iw_price = card.query_selector("iw-price")
                    price = 0
                    if iw_price:
                        price_json = iw_price.get_attribute(":price") or "{}"
                        with contextlib.suppress(Exception):
                            price = json.loads(price_json).get("mainValue", 0) or 0
                    if not price:
                        price_el = card.query_selector("[class*=price]")
                        price = self._clean_price(price_el.inner_text() if price_el else "0")

                    locality_el = card.query_selector(".card--results__information--locality, [class*=locality]")
                    locality_raw = locality_el.inner_text().strip() if locality_el else ""
                    # Locality format: "1300 Wavre" or "Wavre 1300"
                    pc_match = re.search(r"\b(\d{4})\b", locality_raw)
                    postal_code = pc_match.group(1) if pc_match else ""
                    city = re.sub(r"\b\d{4}\b", "", locality_raw).strip(" -,")

                    text = card.inner_text()
                    bed_m = re.search(r"(\d+)\s*(?:bedroom|bed|ch(?:ambre)?)", text, re.I)
                    bedrooms = int(bed_m.group(1)) if bed_m else 0

                    area_m = re.search(r"(\d+)\s*m²", text, re.I)
                    area = float(area_m.group(1)) if area_m else None

                    text_lower = text.lower()
                    has_pool = "piscine" in text_lower or "zwembad" in text_lower or "swimming" in text_lower

                    link_el = card.query_selector("a[href*='/classified/']")
                    href = link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = f"https://www.immoweb.be{href}"
                    if not native_id and href:
                        id_m = re.search(r"/(\d+)/?$", href)
                        native_id = id_m.group(1) if id_m else ""

                    if not self._in_target_area(postal_code, city):
                        continue

                    lid = Listing.make_id(self.name, native_id, href, city, "", price, bedrooms)
                    listings.append(Listing(
                        id=lid,
                        title=title,
                        price=price,
                        city=city,
                        address="",
                        bedrooms=bedrooms,
                        area=area,
                        has_pool=has_pool,
                        source=self.name,
                        url=href,
                        collected_at=self._now_iso(),
                    ))
                except Exception as exc:
                    logger.debug("[Immoweb] DOM card parse error: %s", exc)

        except Exception as exc:
            logger.warning("[Immoweb] DOM extraction error: %s", exc)
        return listings

    def _parse_api_item(self, item: dict) -> Listing | None:
        """Parse a JSON classified item from Immoweb's intercepted API response."""
        try:
            prop = item.get("property", item)
            trans = item.get("transaction", {})

            native_id = str(item.get("id", "") or prop.get("id", ""))
            title = prop.get("title", "") or item.get("title", "Maison à vendre")
            price_raw = trans.get("sale", {}).get("price") or item.get("price", 0)
            price = int(price_raw) if price_raw else 0

            loc = prop.get("location", {})
            city = loc.get("locality", "") or loc.get("city", "")
            postal_code = str(loc.get("postalCode", "") or loc.get("zip", ""))
            address = loc.get("street", "")
            if loc.get("number"):
                address += f" {loc['number']}"

            bedrooms = int(prop.get("bedroomCount", 0) or 0)
            area_raw = prop.get("netHabitableSurface") or prop.get("livingArea")
            area = float(area_raw) if area_raw else None

            has_pool = bool(
                prop.get("hasSwimmingPool")
                or prop.get("swimmingPool")
                or "piscine" in title.lower()
                or "zwembad" in title.lower()
            )

            url = item.get("url", "") or f"https://www.immoweb.be/en/classified/{native_id}"
            if url and not url.startswith("http"):
                url = f"https://www.immoweb.be{url}"

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
                source=self.name,
                url=url,
                collected_at=self._now_iso(),
            )
        except Exception as exc:
            logger.debug("[Immoweb] API item parse error: %s", exc)
            return None
