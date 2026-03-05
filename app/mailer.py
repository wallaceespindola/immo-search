"""Gmail SMTP email notification for immo-search."""

import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import (
    EMAIL_TO,
    GMAIL_APP_PASSWORD,
    GMAIL_USER,
    MAX_PRICE,
    MIN_BEDROOMS,
    SMTP_HOST,
    SMTP_PORT,
    TARGET_CITIES,
)
from app.storage import Listing

logger = logging.getLogger(__name__)

_EMAIL_BODY_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: auto; padding: 20px; }}
  h1 {{ color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 8px; }}
  .summary {{ background: #eaf4fb; border-left: 4px solid #1a5276; padding: 12px 16px; margin: 16px 0; }}
  .filters {{ background: #fef9e7; border-left: 4px solid #f39c12; padding: 12px 16px; margin: 16px 0; font-size: 0.9em; }}
  .listing {{ border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 12px 0; }}
  .listing h3 {{ margin: 0 0 8px 0; color: #1a5276; }}
  .listing .price {{ font-size: 1.3em; font-weight: bold; color: #27ae60; }}
  .listing .details {{ color: #555; font-size: 0.9em; margin: 6px 0; }}
  .listing a {{ display: inline-block; margin-top: 8px; background: #1a5276; color: white;
                padding: 6px 14px; border-radius: 4px; text-decoration: none; font-size: 0.9em; }}
  .listing a:hover {{ background: #21618c; }}
  .source-badge {{ display: inline-block; background: #85c1e9; color: #1a5276;
                   padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 8px; }}
  .pool-badge {{ display: inline-block; background: #a9dfbf; color: #196f3d;
                 padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 4px; }}
  footer {{ margin-top: 30px; font-size: 0.8em; color: #999; text-align: center; }}
</style>
</head>
<body>
<h1>🏡 Immo Search — Nouvelles Propriétés</h1>

<div class="summary">
  <strong>{count} nouvelle(s) propriété(s) trouvée(s)</strong> dans le Brabant Wallon
  en date du {today}
</div>

<div class="filters">
  <strong>Filtres appliqués :</strong><br>
  • Type : Maison 4 façades (détachée)<br>
  • Chambres : {min_bedrooms}+<br>
  • Piscine : Requise<br>
  • Prix maximum : €{max_price:,}<br>
  • Zones : {cities}
</div>

<h2>Propriétés</h2>
{listings_html}

<footer>
  Généré par immo-search — Système de surveillance immobilière personnel<br>
  Brabant Wallon, Belgique
</footer>
</body>
</html>
"""

_LISTING_TEMPLATE = """
<div class="listing">
  <h3>{title} <span class="source-badge">{source}</span>{pool_badge}</h3>
  <div class="price">€{price:,}</div>
  <div class="details">
    📍 {city}{address_part}<br>
    🛏️ {bedrooms} chambres{area_part}
  </div>
  <a href="{url}" target="_blank">Voir l'annonce →</a>
</div>
"""


def _render_listing_html(listing: Listing) -> str:
    pool_badge = '<span class="pool-badge">🏊 Piscine</span>' if listing.has_pool else ""
    address_part = f" — {listing.address}" if listing.address else ""
    area_part = f" · {listing.area:.0f} m²" if listing.area else ""
    return _LISTING_TEMPLATE.format(
        title=listing.title,
        source=listing.source,
        pool_badge=pool_badge,
        price=listing.price,
        city=listing.city,
        address_part=address_part,
        bedrooms=listing.bedrooms,
        area_part=area_part,
        url=listing.url,
    )


def send_notification(listings: list[Listing]) -> bool:
    """Send email notification for new listings. Returns True on success."""
    if not listings:
        logger.info("No new listings to notify.")
        return False

    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not EMAIL_TO:
        logger.warning("Email credentials not configured — skipping notification.")
        return False

    count = len(listings)
    today = date.today().strftime("%d/%m/%Y")
    subject = f"{count} New {'Property' if count == 1 else 'Properties'} — Brabant Wallon"

    listings_html = "\n".join(_render_listing_html(l) for l in listings)
    cities_preview = ", ".join(TARGET_CITIES[:6]) + "..."

    body_html = _EMAIL_BODY_TEMPLATE.format(
        count=count,
        today=today,
        min_bedrooms=MIN_BEDROOMS,
        max_price=MAX_PRICE,
        cities=cities_preview,
        listings_html=listings_html,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())
        logger.info("Email sent: '%s' → %s", subject, EMAIL_TO)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check GMAIL_APP_PASSWORD.")
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
    except OSError as exc:
        logger.error("Network error sending email: %s", exc)
    return False
