"""Configuration and search criteria for immo-search — loaded from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")

# === Paths ===
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
STATE_DB = BASE_DIR / "state.sqlite"


# === Helpers ===


def _csv(key: str, default: str = "") -> list[str]:
    """Parse comma-separated env var. Returns [] if key is missing or empty."""
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _opt_int(key: str) -> int | None:
    """Parse optional int env var. Returns None if key is missing or empty (= no limit)."""
    raw = os.getenv(key, "").strip()
    return int(raw) if raw else None


def _opt_bool(key: str, default: bool = False) -> bool:
    """Parse optional bool env var. Returns default if key is missing or empty (= disabled)."""
    raw = os.getenv(key, "").strip()
    return raw.lower() == "true" if raw else default


# === Email configuration ===
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
GMAIL_USER: str = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
EMAIL_TO: str = os.getenv("EMAIL_TO", "")

# === Search criteria ===
# Removing or emptying any of these in .env disables that filter entirely.
MAX_PRICE: int | None = _opt_int("MAX_PRICE")  # None = no price limit
MIN_BEDROOMS: int | None = _opt_int("MIN_BEDROOMS")  # None = any bedroom count
REQUIRE_POOL: bool = _opt_bool("REQUIRE_POOL")  # empty/missing = pool not required
REQUIRE_PARKING: bool = _opt_bool("REQUIRE_PARKING")  # empty/missing = parking not required

# PEB / EPC energy ratings filter (A=excellent, B=good, C=poor, D=bad)
# Comma-separated list. Empty/missing = no EPC filter applied.
_EPC_DEFAULT = "excellent,good,poor,bad"  # A, B, C, D
EPC_RATINGS: list[str] = _csv("EPC_RATINGS", _EPC_DEFAULT)

# === Active sites ===
IMMO_SITES_ACTIVE: list[str] = _csv(
    "IMMO_SITES_ACTIVE",
    "Immoweb,Zimmo,Immovlan,Immoscoop,Logic-Immo,Biddit,"
    "ERA,REMAX,Dewaele,LatourPetit,Notaris,Trevi,Promimo,CapSud,PPR,ImmoBW,Avenir,Altis,"
    "Realo,Trovit,eRowz,Century21,Sothebys,HomeAvenue,Vlan,Athena,ImmoNeuf,"
    "EngelVolkers,ImmoVillages,LesViviers",
)

# === Target cities ===
_CITIES_BW_DEFAULT = (
    "Wavre,Limal,Ottignies,Louvain-la-Neuve,Rixensart,La Hulpe,Waterloo,"
    "Braine-l'Alleud,Nivelles,Genappe,Genval,Lasne,Court-Saint-Étienne,"
    "Villers-la-Ville,Chastre,Mont-Saint-Guibert,Walhain,Perwez"
)
_CITIES_NAMUR_DEFAULT = (
    "Namur,Jambes,Gembloux,Floreffe,Profondeville,Andenne,Sambreville,"
    "Fosses-la-Ville,Mettet,Ciney,Dinant,Rochefort,Philippeville,Couvin,"
    "Walcourt,Florennes,Eghezée,Fernelmont"
)
_CITIES_VBR_DEFAULT = (
    "Leuven,Tervuren,Overijse,Hoeilaart,Huldenberg,Oud-Heverlee,Ottenburg,"
    "Sint-Genesius-Rode,Rhode-Saint-Genèse,Linkebeek,Beersel,Drogenbos,Wemmel"
)

TARGET_CITIES_BW: list[str] = _csv("TARGET_CITIES_BW", _CITIES_BW_DEFAULT)
TARGET_CITIES_NAMUR: list[str] = _csv("TARGET_CITIES_NAMUR", _CITIES_NAMUR_DEFAULT)
TARGET_CITIES_VBR: list[str] = _csv("TARGET_CITIES_VBR", _CITIES_VBR_DEFAULT)

# Combined list used across the application
TARGET_CITIES: list[str] = TARGET_CITIES_BW + TARGET_CITIES_NAMUR + TARGET_CITIES_VBR

# === Target postal codes ===
_PC_BW_DEFAULT = (
    "1300,1301,1325,1330,1331,1332,1340,1341,1342,1348,"
    "1310,1380,1390,1400,1401,1402,1410,1420,1421,1428,"
    "1470,1471,1473,1490,1495,1450,1454,1360,1370"
)
_PC_NAMUR_DEFAULT = (
    "5000,5001,5002,5003,5004,5010,5020,5030,5031,5032,"
    "5060,5070,5080,5100,5101,5140,5150,5170,5190,5300,"
    "5310,5330,5340,5350,5360,5370,5380"
)
_PC_VBR_DEFAULT = (
    "3001,3010,3018,3050,3053,3054,3060,3061,3070,3080,3090," "1560,1600,1620,1630,1640,1650,1654,1670,1500,1501,1502"
)

TARGET_POSTAL_CODES_BW: list[str] = _csv("POSTAL_CODES_BW", _PC_BW_DEFAULT)
TARGET_POSTAL_CODES_NAMUR: list[str] = _csv("POSTAL_CODES_NAMUR", _PC_NAMUR_DEFAULT)
TARGET_POSTAL_CODES_VBR: list[str] = _csv("POSTAL_CODES_VBR", _PC_VBR_DEFAULT)

# Combined list used across the application
TARGET_POSTAL_CODES: list[str] = TARGET_POSTAL_CODES_BW + TARGET_POSTAL_CODES_NAMUR + TARGET_POSTAL_CODES_VBR

# === Property type keywords ===
_INCLUDE_FR_DEFAULT = (
    "maison 4 façades,maison 4 facades,villa,maison individuelle,"
    "maison isolée,maison isolee,propriété,propriete,"
    "villa indépendante,villa independante,4 façades,4 facades"
)
_INCLUDE_NL_DEFAULT = "open bebouwing,vrijstaande woning,alleenstaande woning,villa,open huis,4 gevels"
_INCLUDE_EN_DEFAULT = "detached house,detached villa,villa,4 facades,4-facade,single-family home,standalone house"
_EXCLUDE_FR_DEFAULT = (
    "appartement,studio,duplex,triplex,penthouse,rez-de-chaussée,rez-de-chaussee,"
    "immeuble à appartements,immeuble a appartements,maison mitoyenne,"
    "2 façades,2 facades,3 façades,3 facades,maison de rangée,maison de rangee"
)
_EXCLUDE_NL_DEFAULT = (
    "appartement,studio,duplex,penthouse,rijwoning," "gesloten bebouwing,halfopen bebouwing,2 gevels,3 gevels"
)
_EXCLUDE_EN_DEFAULT = "apartment,studio,duplex,penthouse,townhouse,terraced house,semi-detached,semi detached"
_POOL_FR_DEFAULT = "piscine,piscine extérieure,piscine chauffée,piscine privée,avec piscine"
_POOL_NL_DEFAULT = "zwembad,verwarmd zwembad,privé zwembad,met zwembad"
_POOL_EN_DEFAULT = "swimming pool,private pool,heated pool,outdoor pool,pool"

INCLUSION_KEYWORDS_FR: list[str] = _csv("KEYWORDS_INCLUDE_FR", _INCLUDE_FR_DEFAULT)
INCLUSION_KEYWORDS_NL: list[str] = _csv("KEYWORDS_INCLUDE_NL", _INCLUDE_NL_DEFAULT)
INCLUSION_KEYWORDS_EN: list[str] = _csv("KEYWORDS_INCLUDE_EN", _INCLUDE_EN_DEFAULT)
EXCLUSION_KEYWORDS_FR: list[str] = _csv("KEYWORDS_EXCLUDE_FR", _EXCLUDE_FR_DEFAULT)
EXCLUSION_KEYWORDS_NL: list[str] = _csv("KEYWORDS_EXCLUDE_NL", _EXCLUDE_NL_DEFAULT)
EXCLUSION_KEYWORDS_EN: list[str] = _csv("KEYWORDS_EXCLUDE_EN", _EXCLUDE_EN_DEFAULT)

ALL_EXCLUSION_KEYWORDS: list[str] = EXCLUSION_KEYWORDS_FR + EXCLUSION_KEYWORDS_NL + EXCLUSION_KEYWORDS_EN

POOL_KEYWORDS_FR: list[str] = _csv("KEYWORDS_POOL_FR", _POOL_FR_DEFAULT)
POOL_KEYWORDS_NL: list[str] = _csv("KEYWORDS_POOL_NL", _POOL_NL_DEFAULT)
POOL_KEYWORDS_EN: list[str] = _csv("KEYWORDS_POOL_EN", _POOL_EN_DEFAULT)
ALL_POOL_KEYWORDS: list[str] = POOL_KEYWORDS_FR + POOL_KEYWORDS_NL + POOL_KEYWORDS_EN

# Parking / garage keywords
_PARKING_FR_DEFAULT = "garage,garage fermé,box,parking privé,parking couvert,carport,double garage"
_PARKING_NL_DEFAULT = "garage,gesloten garage,carport,privé parking,overdekte parking,dubbele garage"
_PARKING_EN_DEFAULT = "garage,parking,carport,private parking,indoor parking,double garage"

PARKING_KEYWORDS_FR: list[str] = _csv("KEYWORDS_PARKING_FR", _PARKING_FR_DEFAULT)
PARKING_KEYWORDS_NL: list[str] = _csv("KEYWORDS_PARKING_NL", _PARKING_NL_DEFAULT)
PARKING_KEYWORDS_EN: list[str] = _csv("KEYWORDS_PARKING_EN", _PARKING_EN_DEFAULT)
ALL_PARKING_KEYWORDS: list[str] = PARKING_KEYWORDS_FR + PARKING_KEYWORDS_NL + PARKING_KEYWORDS_EN

# Garden keywords
GARDEN_KEYWORDS_FR: list[str] = ["jardin", "grand terrain", "terrasse", "espace extérieur"]
GARDEN_KEYWORDS_NL: list[str] = ["tuin", "groot perceel", "terras", "buitenruimte"]
GARDEN_KEYWORDS_EN: list[str] = ["garden", "large plot", "terrace", "outdoor space"]

# === HTTP request settings ===
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
REQUEST_DELAY_MIN: float = float(os.getenv("REQUEST_DELAY_MIN", "1.5"))
REQUEST_DELAY_MAX: float = float(os.getenv("REQUEST_DELAY_MAX", "3.5"))

# Common browser headers for requests
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,nl-BE;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
