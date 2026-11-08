"""Minimal shared domain contracts; precise market/calendar contracts remain pending.

Canonical definitions must be implemented against Drive snapshots 01 §24 and 05 §2/18.
Do not treat these partial interfaces as acceptance of source parity or calibrated rules.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Sequence


class DecisionStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    NOT_DETECTED = "NOT_DETECTED"
    DETECTED = "DETECTED"


class Strategy(str, Enum):
    SHORT = "SHORT"
    SWING = "SWING"


ZONE_IDS = tuple([f"B{i}" for i in range(1, 9)] + [f"S{i}" for i in range(1, 9)])


@dataclass(frozen=True)
class Evidence:
    origin: str
    as_of_utc: datetime
    verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.as_of_utc, datetime):
            raise TypeError("as_of_utc must be a datetime")
        if self.as_of_utc.tzinfo is None or self.as_of_utc.utcoffset() != timezone.utc.utcoffset(self.as_of_utc):
            raise ValueError("as_of_utc must be timezone-aware UTC")
        if not isinstance(self.origin, str) or not self.origin:
            raise ValueError("origin is required")
        if type(self.verified) is not bool:
            raise TypeError("verified must be an explicit bool")


@dataclass(frozen=True)
class SignalDecision:
    zone_id: str
    strategy: Strategy
    status: DecisionStatus
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        if self.zone_id not in ZONE_IDS:
            raise ValueError("Unknown zone")
        if not isinstance(self.strategy, Strategy):
            raise TypeError("strategy must be a Strategy enum")
        if not isinstance(self.status, DecisionStatus):
            raise TypeError("status must be a DecisionStatus enum")
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(item, Evidence) for item in self.evidence
        ):
            raise TypeError("evidence must be a tuple of Evidence")
        if self.status is not DecisionStatus.UNVERIFIED:
            if not self.evidence or not all(item.verified for item in self.evidence):
                raise ValueError("Non-UNVERIFIED decisions need verified evidence")


class ZoneRuleRegistry(Protocol):
    def evaluate(self, zone_id: str, strategy: Strategy, as_of_utc: datetime) -> SignalDecision: ...


class MarketDataPort(Protocol):
    def available_events(self, as_of_utc: datetime) -> Sequence[object]: ...
