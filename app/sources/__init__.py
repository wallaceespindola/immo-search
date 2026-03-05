# Real estate source adapters
from app.sources.base import BaseSource
from app.sources.immoweb import ImmowebSource
from app.sources.zimmo import ZimmoSource
from app.sources.immovlan import ImmovlanSource
from app.sources.immoscoop import ImmoScoopSource
from app.sources.logicimmo import LogicImmoSource
from app.sources.biddit import BidditSource
from app.sources.realo import RealoSource
from app.sources.trovit import TrovitSource
from app.sources.erowz import ErowzSource
from app.sources.century21 import Century21Source

ALL_SOURCES: list[type[BaseSource]] = [
    ImmowebSource,
    ZimmoSource,
    ImmovlanSource,
    ImmoScoopSource,
    LogicImmoSource,
    BidditSource,
    RealoSource,
    TrovitSource,
    ErowzSource,
    Century21Source,
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
    "RealoSource",
    "TrovitSource",
    "ErowzSource",
    "Century21Source",
]
