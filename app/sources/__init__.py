# Real estate source adapters — 25 Belgian sites across 3 tiers
from app.sources.athena import AthenaSource
from app.sources.base import BaseSource
from app.sources.biddit import BidditSource
from app.sources.capsud import CapSudSource
from app.sources.century21 import Century21Source
from app.sources.dewaele import DewaeleSource
from app.sources.engelvoelkers import EngelVolkersSource
from app.sources.era import ERASource
from app.sources.erowz import ErowzSource
from app.sources.homeavenue import HomeAvenueSource
from app.sources.immoneuf import ImmoNeufSource
from app.sources.immoscoop import ImmoScoopSource
from app.sources.immovillages import ImmoVillagesSource
from app.sources.immovlan import ImmovlanSource
from app.sources.immoweb import ImmowebSource
from app.sources.latouretpetit import LatourEtPetitSource
from app.sources.logicimmo import LogicImmoSource
from app.sources.notaris import NotarisSource
from app.sources.promimo import PromimoSource
from app.sources.realo import RealoSource
from app.sources.remax import RemaxSource
from app.sources.sothebys import SothebysSource
from app.sources.trevi import TreviSource
from app.sources.trovit import TrovitSource
from app.sources.vlan import VlanSource
from app.sources.zimmo import ZimmoSource

ALL_SOURCES: list[type[BaseSource]] = [
    # Tier 1 — Core market coverage
    ImmowebSource,
    ZimmoSource,
    ImmovlanSource,
    # Tier 2 — Agencies and opportunity sources
    ImmoScoopSource,
    LogicImmoSource,
    BidditSource,
    ERASource,
    RemaxSource,
    DewaeleSource,
    LatourEtPetitSource,
    NotarisSource,
    TreviSource,
    PromimoSource,
    CapSudSource,
    # Tier 3 — Aggregators, luxury, classifieds
    RealoSource,
    TrovitSource,
    ErowzSource,
    Century21Source,
    SothebysSource,
    HomeAvenueSource,
    VlanSource,
    AthenaSource,
    ImmoNeufSource,
    EngelVolkersSource,
    ImmoVillagesSource,
]

__all__ = [
    "BaseSource",
    "ALL_SOURCES",
    "ImmowebSource",
    "ZimmoSource",
    "ImmovlanSource",
    "ImmoScoopSource",
    "LogicImmoSource",
    "BidditSource",
    "ERASource",
    "RemaxSource",
    "DewaeleSource",
    "LatourEtPetitSource",
    "NotarisSource",
    "TreviSource",
    "PromimoSource",
    "CapSudSource",
    "RealoSource",
    "TrovitSource",
    "ErowzSource",
    "Century21Source",
    "SothebysSource",
    "HomeAvenueSource",
    "VlanSource",
    "AthenaSource",
    "ImmoNeufSource",
    "EngelVolkersSource",
    "ImmoVillagesSource",
]
