"""Unit tests for app/mailer.py."""

import smtplib
from unittest.mock import MagicMock, patch

from app.mailer import send_notification
from app.storage import Listing


def _make_listing(listing_id: str = "test:1") -> Listing:
    return Listing(
        id=listing_id,
        title="Villa avec piscine — 4 façades",
        price=495_000,
        city="Wavre",
        address="Avenue du Lac 12",
        bedrooms=5,
        area=280.0,
        has_pool=True,
        has_parking=True,
        source="Immoweb",
        url="https://www.immoweb.be/en/classified/12345",
        collected_at="2024-01-01T07:00:00+00:00",
    )


def test_send_notification_no_listings_returns_false_without_credentials():
    """With empty credentials, even a daily summary (0 listings) returns False."""
    with (
        patch("app.mailer.GMAIL_USER", ""),
        patch("app.mailer.GMAIL_APP_PASSWORD", ""),
        patch("app.mailer.EMAIL_TO", ""),
    ):
        result = send_notification([])
    assert result is False


def test_send_notification_missing_credentials():
    with (
        patch("app.mailer.GMAIL_USER", ""),
        patch("app.mailer.GMAIL_APP_PASSWORD", ""),
        patch("app.mailer.EMAIL_TO", ""),
    ):
        result = send_notification([_make_listing()])
    assert result is False


def test_send_notification_success(capsys):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.mailer.GMAIL_USER", "sender@gmail.com"),
        patch("app.mailer.GMAIL_APP_PASSWORD", "testpass"),
        patch("app.mailer.EMAIL_TO", "receiver@gmail.com"),
        patch("smtplib.SMTP", return_value=mock_smtp),
    ):
        result = send_notification([_make_listing()])

    assert result is True
    mock_smtp.sendmail.assert_called_once()


def test_send_notification_smtp_auth_failure():
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")

    with (
        patch("app.mailer.GMAIL_USER", "sender@gmail.com"),
        patch("app.mailer.GMAIL_APP_PASSWORD", "wrongpass"),
        patch("app.mailer.EMAIL_TO", "receiver@gmail.com"),
        patch("smtplib.SMTP", return_value=mock_smtp),
    ):
        result = send_notification([_make_listing()])

    assert result is False


def test_send_notification_multiple_listings():
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    listings = [_make_listing(f"test:{i}") for i in range(3)]

    with (
        patch("app.mailer.GMAIL_USER", "sender@gmail.com"),
        patch("app.mailer.GMAIL_APP_PASSWORD", "testpass"),
        patch("app.mailer.EMAIL_TO", "receiver@gmail.com"),
        patch("smtplib.SMTP", return_value=mock_smtp),
    ):
        result = send_notification(listings)

    assert result is True
    # Check subject includes count (encoded in UTF-8 quoted-printable in MIME header)
    call_args = mock_smtp.sendmail.call_args
    message_str = call_args[0][2]
    assert "3_New" in message_str or "3 New" in message_str
