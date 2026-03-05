# 🏡 immo-search

> **Personal Real Estate Hunter — Brabant Wallon, Belgium**
>
> Automated daily monitoring of 20 Belgian property websites.
> Detects newly published detached houses with swimming pools matching strict criteria —
> before the general market reacts.

---

[![CI](https://github.com/wallaceespindola/immo-search/actions/workflows/ci.yml/badge.svg)](https://github.com/wallaceespindola/immo-search/actions/workflows/ci.yml)
[![CodeQL](https://github.com/wallaceespindola/immo-search/actions/workflows/codeql.yml/badge.svg)](https://github.com/wallaceespindola/immo-search/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/Ruff-linting-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Black](https://img.shields.io/badge/Black-formatter-000000?logo=python&logoColor=white)](https://black.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/SQLite-state%20store-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## Overview

**immo-search** is a local macOS automation tool that monitors **20 Belgian real estate websites** daily
and sends an email alert when new properties matching your exact criteria appear on the market.

| Feature | Details |
|---|---|
| **Target area** | Brabant Wallon · Province de Namur · Brabant Flamand |
| **Property type** | 4-façades detached house only |
| **Minimum bedrooms** | 4+ |
| **Swimming pool** | Required |
| **Max price** | €600,000 |
| **Notification** | HTML email via Gmail SMTP |
| **Deduplication** | SQLite — no duplicate alerts |
| **Scheduling** | macOS launchd at 07:30 daily |

---

## Monitored Sources — 20 Belgian Sites

### Tier 1 — Core market coverage

| Site | Description | Method |
|---|---|---|
| **Immoweb** | Belgium's largest property portal | Playwright (headed Chrome) |
| **Zimmo** | Major Belgian portal | HTML scraping |
| **Immovlan** | Major Belgian portal | HTML scraping |

### Tier 2 — Agencies and opportunity sources

| Site | Description | Method |
|---|---|---|
| **Immoscoop** | Opportunity aggregator | HTML scraping |
| **Logic-Immo** | French-Belgian portal | HTML scraping |
| **Biddit** | Online property auctions | HTML scraping |
| **ERA Belgium** | Major international agency network | HTML scraping |
| **RE/MAX Belgium** | International franchise network | HTML scraping |
| **Dewaele** | One of Belgium's largest groups | HTML scraping |
| **Latour & Petit** | Premium Wallonia agency (BW focus) | HTML scraping |
| **Notaris** | Belgian Notary Federation (official) | JSON API + HTML |
| **Trevi** | Belgian agency active in Wallonia | HTML scraping |

### Tier 3 — Aggregators, luxury & classifieds

| Site | Description | Method |
|---|---|---|
| **Realo** | National property aggregator | HTML scraping |
| **Trovit** | Pan-European aggregator | HTML scraping |
| **eRowz** | Belgian classifieds aggregator | HTML scraping |
| **Century21** | National agency network | HTML scraping |
| **Sotheby's** | Luxury segment | HTML scraping |
| **HomeAvenue** | Belgian property portal | HTML scraping |
| **Vlan** | Belgian classifieds platform | HTML scraping |
| **Athena Immo** | Premium Wallonia agency | HTML scraping |
| **ImmoNeuf** | New-build / VEFA portal | HTML scraping |

---

## Architecture

```
immo-search/
├── app/
│   ├── main.py          # Orchestrator: fetch → dedup → persist → report → notify
│   ├── config.py        # All settings loaded from .env
│   ├── storage.py       # SQLite deduplication and state
│   ├── mailer.py        # Gmail SMTP notification
│   └── sources/
│       ├── base.py           # Abstract base scraper
│       ├── immoweb.py        # Tier 1 — Playwright SPA scraper
│       ├── zimmo.py          # Tier 1
│       ├── immovlan.py       # Tier 1
│       ├── immoscoop.py      # Tier 2
│       ├── logicimmo.py      # Tier 2
│       ├── biddit.py         # Tier 2
│       ├── era.py            # Tier 2
│       ├── remax.py          # Tier 2
│       ├── dewaele.py        # Tier 2
│       ├── latouretpetit.py  # Tier 2
│       ├── notaris.py        # Tier 2 — JSON API preferred
│       ├── trevi.py          # Tier 2
│       ├── realo.py          # Tier 3
│       ├── trovit.py         # Tier 3
│       ├── erowz.py          # Tier 3
│       ├── century21.py      # Tier 3
│       ├── sothebys.py       # Tier 3
│       ├── homeavenue.py     # Tier 3
│       ├── vlan.py           # Tier 3
│       ├── athena.py         # Tier 3
│       └── immoneuf.py       # Tier 3
├── tests/
│   ├── test_config.py
│   ├── test_storage.py
│   ├── test_mailer.py
│   ├── test_sources.py
│   └── test_email_live.py   # Manual live email test
├── output/              # Daily HTML + CSV reports (gitignored)
├── logs/                # Run logs (gitignored)
├── state.sqlite         # Dedup database (gitignored)
├── .env                 # Credentials and config (gitignored)
├── run.sh               # Execution entry point
├── com.immo-search.plist # macOS launchd scheduler
├── Makefile
└── pyproject.toml
```

### Execution Flow

```
launchd (07:30) → run.sh → app/main.py
    │
    ├── init_db()                    # Ensure SQLite schema
    ├── [for each of 20 sources]
    │   └── source.fetch_listings()  # HTTP → parse → validate
    ├── dedup + save_listing()       # Skip known IDs
    ├── generate_html_report()       # output/resultado_YYYY-MM-DD.html
    ├── generate_csv_report()        # output/resultado_YYYY-MM-DD.csv
    ├── send_notification()          # Gmail SMTP
    └── mark_notified()              # Prevent re-sending
```

---

## Scheduling — macOS launchd

The app runs automatically every day at **07:30** via macOS launchd (the macOS equivalent of cron).

### Schedule

```
Every day at 07:30 local time
→ run.sh → uv run python -m app.main
→ logs written to logs/launchd.log + logs/run.log
```

### Install the scheduler

```bash
# Install (copies plist to ~/Library/LaunchAgents and loads it)
make install-scheduler

# Verify it's loaded
launchctl list | grep immo

# Uninstall
make uninstall-scheduler
```

### Manual trigger (run now)

```bash
launchctl start com.immo-search
```

### Check scheduler status

```bash
# Is it loaded?
launchctl list | grep immo

# Check output logs
tail -f logs/launchd.log
tail -f logs/launchd.error.log
```

### How launchd differs from cron

| Feature | cron | launchd |
|---|---|---|
| Configuration | crontab syntax | XML plist file |
| Missed runs | Skipped | Retried at next opportunity |
| Log redirection | Manual | Built into plist |
| macOS integration | Legacy | Native (Apple recommended) |
| GUI | None | Activity Monitor + `launchctl` |

The plist is at `com.immo-search.plist` and installed to `~/Library/LaunchAgents/`.

---

## Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.12+ | Core application |
| **Package manager** | [uv](https://docs.astral.sh/uv/) | Fast dependency management and venv |
| **Web scraping** | [requests](https://requests.readthedocs.io/) | HTTP client for standard sites |
| **HTML parsing** | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + lxml | Parse HTML responses |
| **SPA scraping** | [Playwright](https://playwright.dev/python/) | Headless/headed browser for JS-rendered sites |
| **Bot evasion** | [playwright-stealth](https://pypi.org/project/playwright-stealth/) | Bypass DataDome/CloudFront on Immoweb |
| **Storage** | [SQLite](https://www.sqlite.org/) | Persistent deduplication state |
| **Email** | [smtplib](https://docs.python.org/3/library/smtplib.html) (Gmail SMTP) | HTML email notifications |
| **Config** | [python-dotenv](https://pypi.org/project/python-dotenv/) | `.env` based configuration |
| **Scheduling** | macOS launchd | Daily cron-equivalent at 07:30 |
| **Linting** | [Ruff](https://docs.astral.sh/ruff/) | Fast Python linter |
| **Formatting** | [Black](https://black.readthedocs.io/) | Code formatter |
| **Type checking** | [mypy](https://mypy.readthedocs.io/) | Static type analysis |
| **Testing** | [pytest](https://pytest.org/) | Unit and integration tests |
| **CI/CD** | GitHub Actions | Automated testing on push/PR |
| **Security** | CodeQL + Dependabot | Vulnerability scanning |

---

## Installation

### Prerequisites

- macOS (Monterey or later)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

```bash
# Clone the repository
git clone https://github.com/wallaceespindola/immo-search.git
cd immo-search

# Install dependencies
make setup

# Install Playwright browsers (required for Immoweb)
uv run playwright install chromium

# Configure credentials
cp .env.example .env
nano .env  # fill in your Gmail app password and target email

# Install the daily scheduler
make install-scheduler
```

### Gmail App Password

1. Enable 2-Step Verification at [myaccount.google.com/security](https://myaccount.google.com/security)
2. Generate an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Set it in `.env` as `GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx`

---

## Configuration

All search criteria and credentials are loaded from `.env`:

```dotenv
# Gmail SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
GMAIL_USER=your.alerts@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_TO=your.email@gmail.com

# Search criteria
MAX_PRICE=600000
MIN_BEDROOMS=4
REQUIRE_POOL=true
REQUIRE_PARKING=false   # set true to only show listings with garage/parking

# Active sites (comma-separated — remove any to disable)
IMMO_SITES_ACTIVE=Immoweb,Zimmo,Immovlan,Immoscoop,Logic-Immo,Biddit,ERA,REMAX,...

# Target cities and postal codes
TARGET_CITIES_BW=Wavre,Limal,Waterloo,...
TARGET_CITIES_NAMUR=Namur,Gembloux,...
TARGET_CITIES_VBR=Tervuren,Overijse,...

POSTAL_CODES_BW=1300,1310,1340,...
POSTAL_CODES_NAMUR=5000,5030,...
POSTAL_CODES_VBR=3001,3010,...

# Inclusion / exclusion keywords (FR + NL + EN)
KEYWORDS_INCLUDE_FR=villa,maison 4 façades,...
KEYWORDS_INCLUDE_NL=open bebouwing,vrijstaande woning,...
KEYWORDS_INCLUDE_EN=detached house,villa,4 facades,...
KEYWORDS_EXCLUDE_FR=appartement,maison mitoyenne,...
KEYWORDS_EXCLUDE_NL=appartement,rijwoning,...
KEYWORDS_EXCLUDE_EN=apartment,semi-detached,...
KEYWORDS_POOL_FR=piscine,piscine privée,...
KEYWORDS_POOL_NL=zwembad,privé zwembad,...
KEYWORDS_POOL_EN=swimming pool,private pool,...
KEYWORDS_PARKING_FR=garage,carport,...
KEYWORDS_PARKING_NL=garage,privé parking,...
KEYWORDS_PARKING_EN=garage,parking,carport,...
```

---

## Usage

### Manual run

```bash
make run         # or: bash run.sh
make dev         # run directly via uv
```

### Tests

```bash
make test              # run all tests
make test-coverage     # with coverage report
```

### Live email test

```bash
uv run python tests/test_email_live.py
```

### Install scheduler (macOS launchd — daily at 07:30)

```bash
make install-scheduler

# Uninstall
make uninstall-scheduler
```

### Lint & format

```bash
make lint      # ruff check
make format    # black + ruff --fix
make typecheck # mypy
```

---

## Output

Every run produces:

| File | Description |
|---|---|
| `output/resultado_YYYY-MM-DD.html` | Visual HTML report with all new listings |
| `output/resultado_YYYY-MM-DD.csv` | CSV export for spreadsheet analysis |
| `logs/run.log` | Full execution log |
| `logs/launchd.log` | Scheduler stdout |
| `logs/launchd.error.log` | Scheduler stderr |
| `state.sqlite` | Persistent dedup database |

---

## Deduplication Strategy

Duplicates are prevented in priority order:

1. **Native listing ID** — `source:native_id`
2. **Canonical URL hash** — SHA-256 of the URL
3. **Field hash** — SHA-256 of `city + address + price + bedrooms`

Previously notified listings are **never emailed again**.

---

## Security

- Credentials are stored exclusively in `.env` (gitignored)
- CodeQL security scanning runs weekly and on every PR
- Dependabot keeps all dependencies up to date
- Pre-commit hooks prevent accidental credential commits (`detect-private-key`)

---

## Author

**Wallace Espindola**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Wallace%20Espindola-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/wallaceespindola/)
[![GitHub](https://img.shields.io/badge/GitHub-wallaceespindola-181717?logo=github&logoColor=white)](https://github.com/wallaceespindola/)
[![Email](https://img.shields.io/badge/Email-wallace.espindola%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:wallace.espindola@gmail.com)

---

## License

Licensed under the [Apache License 2.0](LICENSE).
