"""
immo-search — Personal Real Estate Hunter
Main orchestrator: fetch → deduplicate → persist → report → notify
"""

import csv
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from app.config import IMMO_SITES_ACTIVE, LOGS_DIR, MAX_PRICE, MIN_BEDROOMS, OUTPUT_DIR, TARGET_CITIES
from app.mailer import send_notification
from app.sources import ALL_SOURCES
from app.storage import Listing, get_unnotified, init_db, mark_notified, save_listing

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("immo-search")

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

_HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Immo Search — {date}</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #333; max-width: 1100px; margin: auto; padding: 20px; }}
  h1 {{ color: #1a5276; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th {{ background: #1a5276; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  .pool {{ color: #27ae60; font-weight: bold; }}
  .price {{ font-weight: bold; color: #1a5276; }}
  a {{ color: #1a5276; }}
  .summary {{ background: #eaf4fb; border-left: 4px solid #1a5276; padding: 12px 16px; margin: 16px 0; }}
  .filters {{ background: #fef9e7; border-left: 4px solid #f39c12; padding: 12px 16px;
             margin: 16px 0; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>🏡 Immo Search — Résultats du {date}</h1>
<div class="summary"><strong>{count} propriété(s) trouvée(s)</strong> dans le Brabant Wallon</div>
<div class="filters">
  <strong>Filtres :</strong> Maison 4 façades &nbsp;|&nbsp;
  {min_bedrooms} chambres &nbsp;|&nbsp;
  Piscine requise &nbsp;|&nbsp;
  Prix max €{max_price}
</div>
<table>
  <thead>
    <tr>
      <th>Titre</th>
      <th>Prix</th>
      <th>Ville</th>
      <th>Chambres</th>
      <th>Surface</th>
      <th>Piscine</th>
      <th>Parking</th>
      <th>Source</th>
      <th>Lien</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
<p style="margin-top:30px; font-size:0.8em; color:#999;">
  Généré le {datetime_str} — immo-search
</p>
</body>
</html>
"""

_ROW_TEMPLATE = """
    <tr>
      <td>{title}</td>
      <td class="price">€{price:,}</td>
      <td>{city}</td>
      <td>{bedrooms}</td>
      <td>{area}</td>
      <td class="pool">{pool}</td>
      <td>{parking}</td>
      <td>{source}</td>
      <td><a href="{url}" target="_blank">Voir →</a></td>
    </tr>
"""


def _generate_html_report(listings: list[Listing], report_date: date) -> Path:
    rows = ""
    for item in listings:
        rows += _ROW_TEMPLATE.format(
            title=item.title,
            price=item.price,
            city=item.city,
            bedrooms=item.bedrooms,
            area=f"{item.area:.0f} m²" if item.area else "—",
            pool="🏊 Oui" if item.has_pool else "Non",
            parking="🚗 Oui" if item.has_parking else "Non",
            source=item.source,
            url=item.url,
        )

    html = _HTML_REPORT_TEMPLATE.format(
        date=report_date.strftime("%d/%m/%Y"),
        count=len(listings),
        min_bedrooms=MIN_BEDROOMS if MIN_BEDROOMS is not None else "—",
        max_price=f"{MAX_PRICE:,}" if MAX_PRICE is not None else "—",
        rows=rows,
        datetime_str=datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC"),
    )

    path = OUTPUT_DIR / f"resultado_{report_date.isoformat()}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("HTML report written: %s", path)
    return path


def _generate_csv_report(listings: list[Listing], report_date: date) -> Path:
    path = OUTPUT_DIR / f"resultado_{report_date.isoformat()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "title",
                "price",
                "city",
                "address",
                "bedrooms",
                "area",
                "has_pool",
                "has_parking",
                "source",
                "url",
                "collected_at",
            ],
        )
        writer.writeheader()
        for item in listings:
            writer.writerow(
                {
                    "id": item.id,
                    "title": item.title,
                    "price": item.price,
                    "city": item.city,
                    "address": item.address,
                    "bedrooms": item.bedrooms,
                    "area": item.area or "",
                    "has_pool": "yes" if item.has_pool else "no",
                    "has_parking": "yes" if item.has_parking else "no",
                    "source": item.source,
                    "url": item.url,
                    "collected_at": item.collected_at,
                }
            )
    logger.info("CSV report written: %s", path)
    return path


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def run() -> None:
    today = date.today()
    logger.info("=" * 60)
    logger.info("immo-search — run started: %s", today.isoformat())
    bedrooms_str = f"{MIN_BEDROOMS}+" if MIN_BEDROOMS is not None else "any"
    price_str = f"≤€{MAX_PRICE:,}" if MAX_PRICE is not None else "no limit"
    logger.info("Criteria: 4-façades house, %s bedrooms, pool, %s", bedrooms_str, price_str)
    logger.info("Target area: %s", ", ".join(TARGET_CITIES[:6]) + "...")
    logger.info("=" * 60)

    # 1. Initialize database
    init_db()

    # 2. Run all source adapters
    all_raw: list[Listing] = []
    source_stats: dict[str, int] = {}

    active_sources = [S for S in ALL_SOURCES if not IMMO_SITES_ACTIVE or S.name in IMMO_SITES_ACTIVE]
    logger.info("Active sources: %s", [S.name for S in active_sources])

    for SourceClass in active_sources:
        source = SourceClass()
        try:
            listings = source.fetch_listings()
            source_stats[source.name] = len(listings)
            all_raw.extend(listings)
        except Exception as exc:
            logger.error("Source %s failed (skipping): %s", source.name, exc)
            source_stats[source.name] = 0

    logger.info("Total raw listings collected: %d", len(all_raw))

    # 3. Deduplicate and persist new listings
    new_count = 0
    for listing in all_raw:
        if save_listing(listing):
            new_count += 1
            logger.info("  NEW: [%s] %s — %s €%d", listing.source, listing.title[:60], listing.city, listing.price)

    logger.info("New listings saved: %d", new_count)

    # 4. Generate reports (always, even if no new listings)
    all_unnotified = get_unnotified()
    if all_unnotified:
        _generate_html_report(all_unnotified, today)
        _generate_csv_report(all_unnotified, today)
    else:
        logger.info("No new listings to report today.")

    # 5. Send email notification
    if all_unnotified:
        success = send_notification(all_unnotified)
        if success:
            mark_notified([item.id for item in all_unnotified])
            logger.info("Email sent and %d listings marked as notified.", len(all_unnotified))
        else:
            logger.warning("Email notification failed — listings will be retried next run.")
    else:
        # Always send a daily summary so you know the agent ran, even with 0 results
        send_notification([])
        logger.info("Daily summary email sent (0 new listings).")

    # 6. Summary
    logger.info("-" * 60)
    logger.info("Source summary:")
    for src_name, count in source_stats.items():
        logger.info("  %-20s %d listings", src_name, count)
    logger.info("Run completed. New: %d | Pending notification: %d", new_count, len(all_unnotified))
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
