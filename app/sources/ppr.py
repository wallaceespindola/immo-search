"""PPR Immo (Le Parcours du Propriétaire) source adapter — Tier 2 (Brabant Wallon specialist)."""

import logging

from app.sources.base import BaseSource
from app.storage import Listing

logger = logging.getLogger(__name__)

# OmniCasa tenant ID for PPR (extracted from page source)
_TENANT_ID = "66cf15a21a9db1a1cfbf8569"
_API_URL = "https://www.ppr.be/api/properties"
_BASE_URL = "https://www.ppr.be/fr/a-vendre"


class PPRSource(BaseSource):
    """Scraper for PPR.be — Le Parcours du Propriétaire, based in Bierges/Wavre.

    Specialised Brabant Wallon agency since 1986.
    Uses OmniCasa JSON API (tenant-scoped) — much more reliable than HTML scraping.
    """

    name = "PPR"
    tier = 2

    def _fetch(self) -> list[Listing]:
        listings: list[Listing] = []

        for page in range(1, 4):
            resp = self._get(
                _API_URL,
                params={"tenantId": _TENANT_ID, "language": "fr", "purpose": "sale", "limit": 50, "page": page},
                headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            )
            if resp is None:
                break

            try:
                data = resp.json()
            except Exception:
                break

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)

            # Stop if we got fewer items than requested (last page)
            if len(items) < 50:
                break

        return listings

    def _parse_item(self, item: dict) -> Listing | None:
        try:
            # Goal=0 = for sale, Goal=1 = for rent — skip rentals
            if item.get("Goal", 0) != 0:
                return None
            # Only detached houses — skip studios, land, investment properties
            if item.get("WebIDName", "") != "Villa/Woning/Hoeve":
                return None

            native_id = str(item.get("ID", ""))
            city = item.get("City", "").strip().title()
            postal_code = str(item.get("Zip", "") or "")
            price = int(item.get("Price") or item.get("SalePrice") or 0)
            bedrooms = int(item.get("NumberOfBedRooms") or 0)
            area_raw = item.get("SurfaceLiving") or item.get("SurfaceTotal")
            area = float(area_raw) if area_raw else None

            # Pool: check description fields
            descriptions = " ".join(str(item.get(f"Description{c}", "") or "") for c in ["A", "B", "C", "D"]).lower()
            has_pool = self._detect_pool(descriptions)

            # Parking
            has_parking = bool(
                item.get("NumberOfGarages") or item.get("NumberOfParkings") or self._detect_parking(descriptions)
            )

            if not self._in_target_area(postal_code, city):
                return None

            url = f"{_BASE_URL}/{native_id}/"
            title = f"Maison à vendre — {city}" if city else "Maison à vendre"
            listing_id = Listing.make_id(self.name, native_id, url, city, "", price, bedrooms)
            return Listing(
                id=listing_id,
                title=title,
                price=price,
                city=city,
                address=f"{item.get('Street', '')} {item.get('HouseNumber', '')}".strip(),
                bedrooms=bedrooms,
                area=area,
                has_pool=has_pool,
                has_parking=has_parking,
                source=self.name,
                url=url,
                collected_at=self._now_iso(),
            )
        except Exception as exc:
            logger.debug("[%s] Parse error: %s", self.name, exc)
            return None
