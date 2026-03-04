
# IMMO SEARCH — Personal Real Estate Hunter

## 1. Project Overview

Immo Search is a local automated real-estate monitoring system running on macOS.

The system monitors Belgian property websites and notifies the owner when new houses
matching strict criteria appear on the market.

It behaves as a personal acquisition agent designed to detect opportunities before
the general market reacts.

Execution modes:
- Manual (on-demand)
- Scheduled daily execution
- Email notification
- Local report generation

Project location:

~/git/immo-search

---

## 2. Mission Statement

The agent’s mission is:

Detect newly published properties matching predefined criteria faster than manual searching.

Success means:
- discovering listings early
- avoiding duplicate alerts
- minimizing noise
- requiring zero daily supervision

---

## 3. Target Geographic Area

Country: Belgium

Primary Region:
Brabant Wallon

Priority cities:
- Wavre
- Limal
- Ottignies-Louvain-la-Neuve
- Rixensart
- La Hulpe
- Waterloo
- Braine-l’Alleud
- Nivelles
- Genappe
- Nearby Brabant Wallon municipalities

---

## 4. Property Search Criteria

Mandatory filters:

Property Type:
Detached house (4 façades only)

Bedrooms:
4 or more

Swimming Pool:
Required

Maximum Price:
€600,000

Sorting priority:
Newest listings first

---

## 4.1 Property Type Restriction — 4 Façades Houses Only

The agent must search exclusively for detached houses (4 façades).

Apartments and attached housing types must be excluded.

Definition:
A 4 façades house is a property with:
- no shared walls
- standalone construction
- private surrounding land

Accepted equivalents:
- Detached house
- Standalone house
- Free-standing house

### REQUIRED Inclusion Keywords

French:
- maison 4 façades
- villa
- maison individuelle
- maison isolée
- propriété
- villa indépendante

Dutch / Flemish:
- open bebouwing
- vrijstaande woning
- alleenstaande woning
- villa
- open huis

### STRICT Exclusion Keywords

French exclusions:
- appartement
- studio
- duplex
- triplex
- penthouse
- rez-de-chaussée
- immeuble à appartements
- maison mitoyenne
- 2 façades
- 3 façades
- maison de rangée

Dutch exclusions:
- appartement
- studio
- duplex
- penthouse
- rijwoning
- gesloten bebouwing
- halfopen bebouwing
- 2 gevels
- 3 gevels

---

## 4.2 Multilingual Search Keywords

Belgian real estate listings appear in multiple languages.

The agent must support French and Dutch (Flemish) keywords.

### Bedrooms

French:
- 4 chambres
- 5 chambres
- 6 chambres
- quatre chambres

Dutch:
- 4 slaapkamers
- 5 slaapkamers
- 6 slaapkamers
- vier slaapkamers

### Swimming Pool

French:
- piscine
- piscine extérieure
- piscine chauffée
- piscine privée
- avec piscine

Dutch:
- zwembad
- verwarmd zwembad
- privé zwembad
- met zwembad

### Garden / Outdoor Signals

French:
- jardin
- grand terrain
- terrasse
- espace extérieur

Dutch:
- tuin
- groot perceel
- terras
- buitenruimte

---

## 5. Monitored Real Estate Sources

Tier 1 — Core Market Coverage
1. Immoweb
2. Zimmo
3. Immovlan

Tier 2 — Opportunity Sources
4. Immoscoop
5. Logic-Immo Belgium
6. Biddit

Tier 3 — Aggregators
7. Realo
8. Trovit
9. eRowz
10. Century21 Belgium

---

## 6. System Architecture

Runtime Environment:
- macOS
- Python 3
- Local execution only
- No cloud dependency

Directory structure:

immo-search/
    .env
    run.sh
    state.sqlite
    CONTEXT.md

    app/
        main.py
        config.py
        mailer.py
        storage.py
        sources/

    output/
    logs/

---

## 7. Execution Flow

1. Scheduler or manual trigger executes run.sh
2. Environment variables loaded from .env
3. Python application starts
4. Each source adapter performs search
5. Listings normalized into unified model
6. Duplicate detection executed
7. New listings persisted locally
8. HTML and CSV reports generated
9. Email notification sent if new listings exist
10. Logs written

---

## 8. Listing Data Model

Each property listing must contain:

- id
- title
- price
- city
- address (if available)
- bedrooms
- area (optional)
- has_pool
- source
- url
- collected_at

---

## 9. Deduplication Rules

Duplicate prevention priority:

1. Native listing ID
2. Canonical URL
3. Hash of:
   city + address + price + bedrooms

Persistence database:

state.sqlite

Previously sent listings must never be emailed again.

---

## 10. Email Notification Specification

Email transport:
Gmail SMTP

Environment variables:

SMTP_HOST
SMTP_PORT
GMAIL_USER
GMAIL_APP_PASSWORD
EMAIL_TO

Email rules:

Send email only when new listings exist.

Subject format:

"X New Properties — Brabant Wallon"

Email body must include:
- summary count
- applied filters
- list of properties
- direct links

---

## 11. Output Artifacts

Daily generated files:

output/
    resultado_YYYY-MM-DD.html
    resultado_YYYY-MM-DD.csv

Logs:

logs/run.log

Persistent state:

state.sqlite

---

## 12. Scheduling

Execution scheduler:
macOS launchd

Default schedule:
Daily at 07:30

Manual execution:

~/git/immo-search/run.sh

---

## 13. Reliability Requirements

The agent must:

- continue execution if a source fails
- log errors without stopping execution
- avoid aggressive scraping
- respect rate limits
- behave deterministically

Failure of one website must not abort the run.

---

## 14. Security Principles

Credentials must never be hardcoded.

Secrets stored in .env.

Recommended .gitignore:

.env
state.sqlite
logs/
output/

---

## 15. AI Agent Operational Prompt

You are a Personal Real Estate Hunter Agent.

Your objective is to discover newly published detached houses with swimming pools
in Brabant Wallon that match the predefined filters.

You must:
- prioritize newest listings
- minimize duplicate notifications
- surface meaningful opportunities
- operate reliably without supervision
- behave like an intelligent acquisition assistant

Success metric:

Finding valuable properties before the market reacts.

---

## 16. Future Enhancements

Phase 2:
- Playwright support for JavaScript sites
- Parallel scraping
- Retry strategies
- Price history tracking
- Change detection

Phase 3:
- Underpriced property detection
- Market value estimation
- Renovation opportunity scoring
- Investment ROI estimation
- Smart email prioritization

---

## 17. Success Criteria

The system is successful when:

- it runs daily without manual intervention
- emails remain high signal and low noise
- no duplicate alerts occur
- maintenance effort is minimal
- early property opportunities are consistently detected

END OF DOCUMENT
