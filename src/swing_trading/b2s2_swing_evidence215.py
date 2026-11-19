"""§215: source-locked B2/S2 two-pivot D1 context / M15 trigger ingredient.

Works exclusively with caller-supplied resolved v1.2 closed bars and §206
causal pivot detection, never native SSI/DNSE/VCBS rows or licensed attestations.
This implements only structure geometry in 01_MASTER_SPEC §24.4:
 B2 R0 D1 confirmed support/higher-low context (NOT whole D1 uptrend);
 B2 R_E M15 confirmed higher-low (NOT an entire reclaim event);
 S2 R0 D1 lower-high resistance context (NOT whole D1 downtrend);
 S2 R_E M15 confirmed lower-high (NOT an entire rejection event).
The original requires additional trend, H1/SR, risk, position, calibrated
lookbacks/near and trigger evidence. The result MUST remain UNVERIFIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12
from .zone_manifest_v03 import MANIFESTS


SCHEMA = "mst.b2s2.causal_two_pivot.v0.1"
MAX_HISTORY = 512
_SOURCE_PHASES = {
    ("B2", "R0"): (StructureSide.LOW, Timeframe.D1, "B2/BASE"),
    ("B2", "R_E"): (StructureSide.LOW, Timeframe.M15, "B2/BASE"),
    ("S2", "R0"): (StructureSide.HIGH, Timeframe.D1, "S2/BASE"),
    ("S2", "R_E"): (StructureSide.HIGH, Timeframe.M15, "S2/BASE"),
}


class B2S2PivotDenied215(ValueError):
    """No market prices, provider secret, or raw rows in rejection messages."""


class PivotPairState215(str, Enum):
    BLOCKED = "BLOCKED"
    GEOMETRY_MATCH_UNVERIFIED = "GEOMETRY_MATCH_UNVERIFIED"
    GEOMETRY_NONMATCH_UNVERIFIED = "GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class B2S2PivotPair215:
    zone_id: str
    strategy: Strategy
    phase: str
    predicate_ref: str
    side: StructureSide
    timeframe: Timeframe
    as_of_utc: datetime
    state: PivotPairState215
    reason: str
    preview_id: str | None
    first_known_at_utc: datetime | None
    second_known_at_utc: datetime | None
    schema: str = SCHEMA
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    source_independently_attested: bool = False
    chosen_lookback_approved: bool = False
    detector_approved: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)
        expected = _SOURCE_PHASES.get((self.zone_id, self.phase))
        if (expected is None
                or not isinstance(self.strategy, Strategy)
                or self.predicate_ref != MANIFESTS[self.zone_id].predicate_for(self.phase)
                or self.side is not expected[0]
                or self.timeframe is not expected[1]
                or not isinstance(self.state, PivotPairState215)
                or not isinstance(self.reason, str) or not self.reason
                or self.schema != SCHEMA
                or self.status is not DecisionStatus.UNVERIFIED
                or self.source_independently_attested is not False
                or self.chosen_lookback_approved is not False
                or self.detector_approved is not False
                or self.action_eligible is not False):
            raise B2S2PivotDenied215("MST_215_PHASE_AUTHORITY_FORBIDDEN")
        if self.state is PivotPairState215.BLOCKED:
            if (self.preview_id is not None or self.first_known_at_utc is not None
                    or self.second_known_at_utc is not None):
                raise B2S2PivotDenied215("MST_215_BLOCKED_CANNOT_CLAIM_PIVOT")
        elif (type(self.preview_id) is not str
              or not self.preview_id.startswith("MST_B2S2_PAIR215:")
              or len(self.preview_id) != len("MST_B2S2_PAIR215:") + 64
              or any(ch not in "0123456789abcdef" for ch in self.preview_id.rsplit(":", 1)[1])
              or self.first_known_at_utc is None
              or self.second_known_at_utc is None):
            raise B2S2PivotDenied215("MST_215_PIVOT_PREVIEW_INCOMPLETE")
        else:
            require_utc(self.first_known_at_utc)
            require_utc(self.second_known_at_utc)
            if (self.first_known_at_utc > self.second_known_at_utc
                    or self.second_known_at_utc > self.as_of_utc):
                raise B2S2PivotDenied215("MST_215_CAUSAL_WITNESS_INVALID")


def _source_scope215(row):
    key, obs, rev = row.market_bar_key, row.observation_key, row.observation_revision
    return (key.instrument_id, key.exchange, key.instrument_class.value,
            key.price_basis.value, key.calendar_version,
            key.aggregation_policy_version, obs.project_id, obs.provider_id,
            obs.origin.value, obs.source_stream_id, rev.adjustment_revision)


def _lineage215(row):
    key, obs, rev = row.market_bar_key, row.observation_key, row.observation_revision
    return {
        "start": key.bar_start_utc.isoformat(),
        "end": row.bar_end_utc.isoformat(),
        "session": key.session_period_id,
        "source_revision": rev.source_revision_or_payload_digest,
        "adjustment_revision": rev.adjustment_revision,
        "ingestion_revision": rev.ingestion_revision,
        "first_known": rev.first_known_time_utc.isoformat(),
        "verified": row.verified_at_utc.isoformat() if row.verified_at_utc else None,
        "normalized_sha256": row.normalized_digest_sha256,
        "raw_sha256": row.raw_digest_sha256,
    }


def inspect_b2s2_two_pivot215(
    *, zone_id: str, strategy: Strategy, phase: str,
    history: tuple[ResolvedBarSnapshotV12, ...],
    first_index: int, second_index: int,
    left_count: int, right_count: int,
    tie_policy: TiePolicy, as_of_utc: datetime,
) -> B2S2PivotPair215:
    """Check only the causal low→higher low or high→lower high geometry.

    Two pivot candidates must be historical, same declared source/session
    policy/adjustment and first must be known BEFORE the second pivot starts.
    A negative geometric candidate is *not* a source-qualified NOT_DETECTED.
    D1 is one R0 ingredient; M15 is one R_E ingredient. Never decide a zone.
    """
    require_utc(as_of_utc)
    scope = _SOURCE_PHASES.get((zone_id, phase))
    if scope is None or not isinstance(strategy, Strategy):
        raise B2S2PivotDenied215("MST_215_UNKNOWN_ZONE_PHASE_OR_STRATEGY")
    side, timeframe, _variant = scope
    predicate = MANIFESTS[zone_id].predicate_for(phase)

    def blocked(reason):
        return B2S2PivotPair215(
            zone_id, strategy, phase, predicate, side, timeframe, as_of_utc,
            PivotPairState215.BLOCKED, reason, None, None, None,
        )

    if (type(history) is not tuple or len(history) > MAX_HISTORY
            or not history
            or type(first_index) is not int or type(second_index) is not int
            or type(left_count) is not int or type(right_count) is not int
            or left_count < 1 or right_count < 1
            or left_count > 40 or right_count > 40
            or not isinstance(tie_policy, TiePolicy)):
        raise B2S2PivotDenied215("MST_215_INVALID_PIVOT_CONFIG")
    if (first_index < left_count or second_index < left_count
            or first_index + right_count >= len(history)
            or second_index + right_count >= len(history)
            or second_index <= first_index + right_count):
        return blocked("INSUFFICIENT_DISTINCT_HISTORICAL_PIVOT_WINDOWS")
    if (any(not isinstance(item, ResolvedBarSnapshotV12)
            or item.market_bar_key.timeframe is not timeframe
            for item in history)):
        return blocked("PIVOT_BAR_TIMEFRAME_OR_TYPE_MISMATCH")
    # The same source/price basis/calendar/adjustment must apply to ALL bars.
    # Source quality itself is checked by inspect_causal_pivot for ALL rows.
    bars = [item.selected for item in history]
    if any(bar is None for bar in bars):
        return blocked("PIVOT_UNRESOLVED_SOURCE_REVISION")
    identity = _source_scope215(bars[0])
    if any(_source_scope215(bar) != identity for bar in bars[1:]):
        return blocked("PIVOT_MIXED_SOURCE_OR_ADJUSTMENT")
    first = inspect_causal_pivot(
        history, candidate_index=first_index,
        left_count=left_count, right_count=right_count,
        side=side, tie_policy=tie_policy, as_of_utc=as_of_utc,
    )
    if first.state is GeometryState.BLOCKED:
        return blocked("FIRST_" + first.reason)
    second = inspect_causal_pivot(
        history, candidate_index=second_index,
        left_count=left_count, right_count=right_count,
        side=side, tie_policy=tie_policy, as_of_utc=as_of_utc,
    )
    if second.state is GeometryState.BLOCKED:
        return blocked("SECOND_" + second.reason)
    second_start = bars[second_index].market_bar_key.bar_start_utc
    if (first.witness_known_at_utc > second_start
            or first.candidate_bar_end_utc >= bars[second_index].bar_end_utc):
        return blocked("EARLIER_PIVOT_NOT_KNOWN_BEFORE_LATER_CANDIDATE")
    if first.geometric_extremum is not True or second.geometric_extremum is not True:
        return blocked("REQUIRE_TWO_CAUSALLY_CONFIRMED_LOCAL_EXTREMA")
    is_pattern = (second.pivot_price > first.pivot_price if side is StructureSide.LOW
                  else second.pivot_price < first.pivot_price)
    wire = json.dumps({
        "schema": SCHEMA, "zone": zone_id, "phase": phase,
        "predicate": predicate, "strategy": strategy.value,
        "side": side.value, "tf": timeframe.value,
        "first": first_index, "second": second_index,
        "left": left_count, "right": right_count,
        "tie_policy": tie_policy.value,
        "source_scope": identity,
        "rows": [_lineage215(bar) for bar in bars],
        "witness_first": first.witness_known_at_utc.isoformat(),
        "witness_second": second.witness_known_at_utc.isoformat(),
        "pattern": is_pattern,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
       allow_nan=False).encode("utf-8")
    return B2S2PivotPair215(
        zone_id, strategy, phase, predicate, side, timeframe, as_of_utc,
        (PivotPairState215.GEOMETRY_MATCH_UNVERIFIED if is_pattern
         else PivotPairState215.GEOMETRY_NONMATCH_UNVERIFIED),
        ("CAUSAL_SWING_GEOMETRY_ONLY_MISSING_CONTEXT_AND_TRIGGER"
         if is_pattern else "CAUSAL_SWING_NONMATCH_NOT_ZONE_NOT_DETECTED"),
        "MST_B2S2_PAIR215:" + sha256(wire).hexdigest(),
        first.witness_known_at_utc,
        second.witness_known_at_utc,
    )
