"""Opt-in MST v2 engineering domain guards, isolated from legacy v1 APIs.

The inherited swing_trading.replay and swing_trading.contracts modules stay
byte-for-byte untouched. This module grants NO provider rights, market truth,
detector calibration, live-trade authorization or production release approval.

Untrusted wire input is intentionally limited to UNVERIFIED + empty evidence.
A separately approved source-attested boundary is necessary before any real
market decision may be consumed from an external feed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from .contracts import DecisionStatus, SignalDecision, Strategy, ZONE_IDS
from .replay import require_utc

WIRE_SCHEMA_V2 = "mst.signal_decision.v2"
_WIRE_FIELDS = frozenset(("schema", "zone_id", "strategy", "status", "evidence"))
_MAX_WIRE_BYTES = 4096


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("Expected a datetime")
    return require_utc(value)


@dataclass
class StrictReplayClockV2:
    """Independent monotonic UTC clock; no mutation of legacy ReplayClock."""

    as_of_utc: datetime

    def __setattr__(self, name: str, value: object) -> None:
        if name == "as_of_utc":
            _utc(value)
            previous = self.__dict__.get("as_of_utc")
            if previous is not None and value < previous:
                raise ValueError("Replay clock cannot go backwards")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        _utc(self.as_of_utc)

    def advance_to(self, next_time_utc: datetime) -> None:
        self.as_of_utc = _utc(next_time_utc)

    def known(self, first_known_time_utc: datetime) -> bool:
        return _utc(first_known_time_utc) <= self.as_of_utc


@dataclass(frozen=True)
class StrictEvidenceV2:
    """A typed caller claim, NOT an independently authenticated source fact."""

    origin: str
    as_of_utc: datetime
    verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.origin, str) or not self.origin.strip():
            raise ValueError("Nonempty string origin required")
        _utc(self.as_of_utc)
        if type(self.verified) is not bool:
            raise TypeError("verified must be a boolean")


@dataclass(frozen=True)
class StrictSignalDecisionV2:
    """Strict typed decision record, with unchanged inherited enum taxonomy."""

    zone_id: str
    strategy: Strategy
    status: DecisionStatus
    evidence: tuple[StrictEvidenceV2, ...] = ()

    def __post_init__(self) -> None:
        if type(self.zone_id) is not str or self.zone_id not in ZONE_IDS:
            raise ValueError("Unknown zone")
        if type(self.strategy) is not Strategy:
            raise TypeError("Strategy enum required")
        if type(self.status) is not DecisionStatus:
            raise TypeError("DecisionStatus enum required")
        if type(self.evidence) is not tuple or any(
            type(item) is not StrictEvidenceV2 for item in self.evidence
        ):
            raise TypeError("Tuple of StrictEvidenceV2 required")
        if self.status is not DecisionStatus.UNVERIFIED and (
            not self.evidence or not all(item.verified for item in self.evidence)
        ):
            raise ValueError("Non-UNVERIFIED needs verified typed evidence")


def legacy_to_v2_unverified(decision: SignalDecision) -> StrictSignalDecisionV2:
    """Explicit fail-closed migration of only empty-evidence legacy records."""
    if type(decision) is not SignalDecision:
        raise TypeError("Legacy SignalDecision required")
    if type(decision.strategy) is not Strategy:
        raise TypeError("Invalid legacy strategy type")
    if decision.status is not DecisionStatus.UNVERIFIED or decision.evidence != ():
        raise PermissionError("Only empty-evidence UNVERIFIED legacy records allowed")
    return StrictSignalDecisionV2(
        decision.zone_id, decision.strategy, DecisionStatus.UNVERIFIED
    )


def v2_to_legacy_unverified(decision: StrictSignalDecisionV2) -> SignalDecision:
    """Explicit rollback adapter for safe synthetic UNVERIFIED records only."""
    if type(decision) is not StrictSignalDecisionV2:
        raise TypeError("StrictSignalDecisionV2 required")
    if decision.status is not DecisionStatus.UNVERIFIED or decision.evidence:
        raise PermissionError("Only empty-evidence UNVERIFIED records allowed")
    return SignalDecision(decision.zone_id, decision.strategy, decision.status)


def _unique_object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError("Non-finite JSON number prohibited")


def decode_untrusted_v2_json(raw_json: str) -> StrictSignalDecisionV2:
    """Never convert untrusted wire input to DETECTED/NOT_DETECTED/rights."""
    if type(raw_json) is not str:
        raise TypeError("JSON text required")
    if len(raw_json.encode("utf-8")) > _MAX_WIRE_BYTES:
        raise ValueError("JSON document too large")
    wire = json.loads(
        raw_json,
        object_pairs_hook=_unique_object_pairs,
        parse_constant=_reject_json_constant,
    )
    if type(wire) is not dict or wire.keys() != _WIRE_FIELDS:
        raise ValueError("Versioned canonical JSON object required")
    if wire["schema"] != WIRE_SCHEMA_V2:
        raise ValueError("Unknown or legacy schema version")
    if type(wire["zone_id"]) is not str or wire["zone_id"] not in ZONE_IDS:
        raise ValueError("Unknown zone")
    if type(wire["strategy"]) is not str:
        raise TypeError("String strategy required in JSON")
    strategy = Strategy(wire["strategy"])
    if type(wire["status"]) is not str:
        raise TypeError("String status required in JSON")
    if wire["status"] != DecisionStatus.UNVERIFIED.value:
        raise PermissionError("Untrusted wire cannot assert a classified signal")
    if type(wire["evidence"]) is not list or wire["evidence"]:
        raise PermissionError("Untrusted wire cannot attest source evidence")
    return StrictSignalDecisionV2(
        wire["zone_id"], strategy, DecisionStatus.UNVERIFIED
    )


def encode_unverified_v2_json(decision: StrictSignalDecisionV2) -> str:
    """Deterministic synthetic wire form; not an authorized source receipt."""
    if type(decision) is not StrictSignalDecisionV2:
        raise TypeError("StrictSignalDecisionV2 required")
    if decision.status is not DecisionStatus.UNVERIFIED or decision.evidence:
        raise PermissionError("Only unverified evidence-free output allowed")
    return json.dumps(
        {
            "schema": WIRE_SCHEMA_V2,
            "zone_id": decision.zone_id,
            "strategy": decision.strategy.value,
            "status": decision.status.value,
            "evidence": [],
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
