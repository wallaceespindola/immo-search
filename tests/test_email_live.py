"""
Live email test — sends a real test email via Gmail SMTP.
Run manually: uv run python tests/test_email_live.py

Requires .env with valid GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO.
"""

import sys
from pathlib import Path

# Ensure the project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import UTC, datetime

from app.config import EMAIL_TO, GMAIL_APP_PASSWORD, GMAIL_USER
from app.mailer import send_notification
from app.storage import Listing


def _make_test_listing() -> Listing:
    return Listing(
        id="test:live-email-001",
        title="[TEST] Villa avec piscine 4 façades — Wavre",
        price=495_000,
        city="Wavre",
        address="Avenue du Test 12",
        bedrooms=5,
        area=280.0,
        has_pool=True,
        source="Immoweb [TEST]",
        url="https://www.immoweb.be",
        collected_at=datetime.now(UTC).isoformat(),
    )


def main() -> None:
    print("=" * 60)
    print("immo-search — Live Email Test")
    print("=" * 60)
    print(f"  From:    {GMAIL_USER}")
    print(f"  To:      {EMAIL_TO}")
    print(f"  Config:  {'✓ OK' if GMAIL_USER and GMAIL_APP_PASSWORD and EMAIL_TO else '✗ MISSING CREDENTIALS'}")
    print()

    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not EMAIL_TO:
        print("ERROR: Email credentials not configured. Check your .env file.")
        print("Required: GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO")
        sys.exit(1)

    listing = _make_test_listing()
    print("Sending test email with 1 mock listing...")
    success = send_notification([listing])

    if success:
        print()
        print("✓ Email sent successfully!")
        print(f"  Check your inbox at: {EMAIL_TO}")
        sys.exit(0)
    else:
        print()
        print("✗ Email failed. Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
