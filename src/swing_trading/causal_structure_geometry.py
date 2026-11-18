"""§206 causal pivot/right-bar + BOS closed-cross GEOMETRY ONLY.

Source: frozen Swing Trading 1.8 MASTER_SPEC §§24.5,24.10 and original
causal_indicators.calculate_wilder_atr14. All results are synthetic-safe,
unpublished, never a B/S predicate, a provider attestation, or trade advice.
A successful local data-contract check does not establish vendor provenance.

Pivot: explicit k-left/k-right and explicit tie policy, candidate bar must
be verified ONLY at/after the final right bar becomes causally available.
BOS: caller specifies an unapproved epsilon; previous CLOSED price and
new CLOSED price must actually cross a causally known structural pivot.
ATR14 is reused (not reimplemented), seeded from 15 qualified D1 bars;
it must have been known by the breakout bar START, not inferred later.
No automatic threshold, window, price basis conversion, calendar proof or
BOS event-ID authority is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .causal_indicators import (
    IndicatorState, calculate_wilder_atr14,
)
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import CoverageState, ResolvedBarSnapshotV12


class StructureSide(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class TiePolicy(str, Enum):
    STRICT_V1 = "STRICT_V1"
    ALLOW_EQUAL_V1 = "ALLOW_EQUAL_V1"


class GeometryState(str, Enum):
    BLOCKED = "BLOCKED"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"


@dataclass(frozen=True)
class PivotGeometry:
    side: StructureSide
    tie_policy: TiePolicy
    left_count: int
    right_count: int
    state: GeometryState
    reason: str
    pivot_price: Decimal | None
    witness_known_at_utc: datetime | None
    candidate_bar_end_utc: datetime | None
    geometric_extremum: bool | None
    detector_approved: bool = False
    source_independently_attested: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.side, StructureSide)
                or not isinstance(self.tie_policy, TiePolicy)
                or type(self.left_count) is not int or self.left_count < 1
                or type(self.right_count) is not int or self.right_count < 1
                or not isinstance(self.state, GeometryState)
                or not isinstance(self.reason, str) or not self.reason
                or (self.state is GeometryState.BLOCKED) !=
                   (self.pivot_price is None)
                or (self.state is GeometryState.BLOCKED) !=
                   (self.witness_known_at_utc is None)
                or (self.state is GeometryState.BLOCKED) !=
                   (self.candidate_bar_end_utc is None)
                or (self.state is GeometryState.BLOCKED) !=
                   (self.geometric_extremum is None)
                or self.detector_approved is not False
                or self.source_independently_attested is not False
                or self.action_eligible is not False):
            raise ValueError("MST_206_PIVOT_AUTHORITY_OR_SHAPE_INVALID")
        if self.pivot_price is not None:
            if (type(self.pivot_price) is not Decimal
                    or not self.pivot_price.is_finite()
                    or type(self.geometric_extremum) is not bool):
                raise ValueError("MST_206_PIVOT_PRICE_INVALID")
            require_utc(self.witness_known_at_utc)
            require_utc(self.candidate_bar_end_utc)
            if self.witness_known_at_utc < self.candidate_bar_end_utc:
                raise ValueError("MST_206_PIVOT_BACKDATED")


@dataclass(frozen=True)
class BosGeometry:
    side: StructureSide
    state: GeometryState
    reason: str
    boundary: Decimal | None
    previous_close: Decimal | None
    breakout_close: Decimal | None
    candidate_cross: bool | None
    witness_known_at_utc: datetime | None
    source_independently_attested: bool = False
    parameter_approved: bool = False
    detector_approved: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.side, StructureSide)
                or not isinstance(self.state, GeometryState)
                or not isinstance(self.reason, str) or not self.reason
                or self.source_independently_attested is not False
                or self.parameter_approved is not False
                or self.detector_approved is not False
                or self.action_eligible is not False):
            raise ValueError("MST_206_BOS_AUTHORITY_FORBIDDEN")
        details = (self.boundary, self.previous_close, self.breakout_close,
                   self.witness_known_at_utc)
        if self.state is GeometryState.BLOCKED:
            if any(x is not None for x in details) or self.candidate_cross is not None:
                raise ValueError("MST_206_BOS_BLOCKED_HAS_OUTPUT")
        elif (any(x is None for x in details)
              or type(self.candidate_cross) is not bool
              or any(type(x) is not Decimal or not x.is_finite()
                     for x in details[:3])):
            raise ValueError("MST_206_BOS_GEOMETRY_INCOMPLETE")
        else:
            require_utc(self.witness_known_at_utc)


def _source_identity(row):
    key, obs, rev = row.market_bar_key, row.observation_key, row.observation_revision
    return (key.instrument_id, key.exchange, key.instrument_class,
            key.price_basis, key.calendar_version, key.aggregation_policy_version,
            obs.project_id, obs.provider_id, obs.origin, obs.source_stream_id,
            rev.adjustment_revision)


def _cross_tf_identity(row):
    key, obs, rev = row.market_bar_key, row.observation_key, row.observation_revision
    return (key.instrument_id, key.exchange, key.instrument_class,
            key.price_basis, key.calendar_version,
            obs.project_id, obs.provider_id, obs.origin, rev.adjustment_revision)


def _eligible(snap: ResolvedBarSnapshotV12, *, cutoff: datetime):
    if not isinstance(snap, ResolvedBarSnapshotV12):
        return None
    bar = snap.selected
    if (bar is None or not snap.confirmation_prerequisites(cutoff)
            or bar.coverage_state is not CoverageState.COMPLETE
            or bar.verified_at_utc is None
            or bar.verified_at_utc > cutoff
            or bar.observation_revision.first_known_time_utc > cutoff
            or bar.bar_end_utc > cutoff):
        return None
    return bar


def _sequence(
    history: tuple[ResolvedBarSnapshotV12, ...], *, cutoff: datetime,
):
    if type(history) is not tuple or len(history) > 512:
        return None, "INVALID_OR_OVERSIZED_HISTORY"
    seen = set()
    rows = []
    context = None
    previous_end = None
    for snapshot in history:
        bar = _eligible(snapshot, cutoff=cutoff)
        if bar is None:
            return None, "UNQUALIFIED_OR_NOT_YET_KNOWN_BAR"
        key = bar.market_bar_key
        if key.timeframe is Timeframe.H4:
            return None, "H4_DERIVED_SESSION_NOT_ATTESTED"
        signature = _source_identity(bar)
        if context is not None and signature != context:
            return None, "MIXED_SOURCE_BASIS_OR_POLICY"
        if (key in seen or previous_end is not None
                and key.bar_start_utc < previous_end):
            return None, "DUPLICATE_OVERLAPPED_OR_REORDERED"
        seen.add(key)
        previous_end = bar.bar_end_utc
        context = signature
        rows.append(bar)
    return rows, ""


def inspect_causal_pivot(
    history: tuple[ResolvedBarSnapshotV12, ...], *,
    candidate_index: int, left_count: int, right_count: int,
    side: StructureSide, tie_policy: TiePolicy, as_of_utc: datetime,
) -> PivotGeometry:
    """Pure pivot extrema preview; right-bar witness cannot be backdated."""
    require_utc(as_of_utc)
    if (not isinstance(side, StructureSide)
            or not isinstance(tie_policy, TiePolicy)
            or type(candidate_index) is not int or candidate_index < 0
            or type(left_count) is not int or not 1 <= left_count <= 40
            or type(right_count) is not int or not 1 <= right_count <= 40):
        raise ValueError("MST_206_PIVOT_CONFIG_INVALID")

    def blocked(reason: str):
        return PivotGeometry(side, tie_policy, left_count, right_count,
                             GeometryState.BLOCKED, reason, None, None, None, None)

    if type(history) is not tuple or len(history) > 512:
        return blocked("INVALID_OR_OVERSIZED_HISTORY")
    if (candidate_index < left_count
            or candidate_index + right_count >= len(history)):
        return blocked("INSUFFICIENT_CAUSAL_LEFT_OR_RIGHT_BARS")
    # Reject ALL supplied history if it mixes revisions/source/TF or has future
    # data, never inspect only the convenient window and ignore a conflict.
    rows, reason = _sequence(history, cutoff=as_of_utc)
    if rows is None:
        return blocked(reason)
    pivot = rows[candidate_index]
    value = pivot.high if side is StructureSide.HIGH else pivot.low
    others = rows[candidate_index-left_count:candidate_index] + rows[
        candidate_index+1:candidate_index+right_count+1
    ]
    if side is StructureSide.HIGH:
        geometric = all(
            value > x.high if tie_policy is TiePolicy.STRICT_V1
            else value >= x.high for x in others
        )
    else:
        geometric = all(
            value < x.low if tie_policy is TiePolicy.STRICT_V1
            else value <= x.low for x in others
        )
    witness = max(
        max(x.bar_end_utc, x.verified_at_utc,
            x.observation_revision.first_known_time_utc)
        for x in rows[candidate_index-left_count:candidate_index+right_count+1]
    )
    if witness > as_of_utc:
        return blocked("RIGHT_BARS_NOT_YET_CAUSALLY_KNOWN")
    return PivotGeometry(
        side, tie_policy, left_count, right_count,
        GeometryState.DESCRIPTIVE_ONLY, "PIVOT_MATH_ONLY_NO_PROVIDER_ATTESTATION",
        value, witness, pivot.bar_end_utc, geometric,
    )


def inspect_closed_bos_geometry(
    pivot_history: tuple[ResolvedBarSnapshotV12, ...], *,
    pivot_index: int, left_count: int, right_count: int,
    previous: ResolvedBarSnapshotV12,
    breakout: ResolvedBarSnapshotV12,
    atr_d1_history: tuple[ResolvedBarSnapshotV12, ...],
    side: StructureSide, tie_policy: TiePolicy,
    candidate_epsilon: Decimal | None,
    as_of_utc: datetime,
) -> BosGeometry:
    """Causal breakout cross with unapproved epsilon, not a detected zone.

    Previous+structural pivot+ATR must ALL be known by breakout bar START.
    Breakout itself must be a distinct verified CLOSED bar by as_of_utc.
    No candle wick-only crossing. No implicit default to 0 ATR buffer.
    """
    require_utc(as_of_utc)
    if not isinstance(side, StructureSide) or not isinstance(tie_policy, TiePolicy):
        raise ValueError("MST_206_BOS_CONFIG_INVALID")
    if (candidate_epsilon is not None
            and (type(candidate_epsilon) is not Decimal
                 or not candidate_epsilon.is_finite()
                 or candidate_epsilon < 0)):
        raise ValueError("MST_206_BOS_EPSILON_INVALID")

    def blocked(reason: str):
        return BosGeometry(side, GeometryState.BLOCKED, reason,
                           None, None, None, None, None)

    target = _eligible(breakout, cutoff=as_of_utc)
    if target is None:
        return blocked("BREAKOUT_NOT_CLOSED_OR_CAUSALLY_KNOWN")
    if target.market_bar_key.timeframe is Timeframe.H4:
        return blocked("H4_DERIVED_SESSION_NOT_ATTESTED")
    cutoff = target.market_bar_key.bar_start_utc
    prior = _eligible(previous, cutoff=cutoff)
    if prior is None:
        return blocked("PREVIOUS_BAR_NOT_KNOWN_BEFORE_BREAKOUT")
    if (prior.bar_end_utc > cutoff
            or _source_identity(prior) != _source_identity(target)
            or prior.market_bar_key.timeframe != target.market_bar_key.timeframe
            or prior.market_bar_key == target.market_bar_key):
        return blocked("PREVIOUS_BAR_IDENTITY_OR_CLOCK_MISMATCH")
    pivot = inspect_causal_pivot(
        pivot_history, candidate_index=pivot_index,
        left_count=left_count, right_count=right_count,
        side=side, tie_policy=tie_policy, as_of_utc=cutoff,
    )
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return blocked("PIVOT_" + pivot.reason)
    if not pivot.geometric_extremum:
        return blocked("PIVOT_NOT_STRUCTURAL_EXTREMUM")
    right_bar = pivot_history[pivot_index+right_count].selected
    if (right_bar is None
            or right_bar.bar_end_utc > prior.bar_end_utc
            or _source_identity(right_bar) != _source_identity(target)):
        return blocked("PIVOT_NOT_AVAILABLE_BEFORE_PREVIOUS_CLOSE")
    if candidate_epsilon is None:
        return blocked("UNAPPROVED_EPSILON_NOT_SUPPLIED")
    if type(atr_d1_history) is not tuple or not atr_d1_history:
        return blocked("ATR14_D1_HISTORY_MISSING")
    atr = calculate_wilder_atr14(
        atr_d1_history, as_of_utc=as_of_utc, known_before_utc=cutoff,
    )
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None:
        return blocked("ATR14_" + atr.reason)
    atr_sample = atr_d1_history[0].selected
    if (atr_sample is None
            or _cross_tf_identity(atr_sample) != _cross_tf_identity(target)):
        return blocked("ATR14_CROSS_TF_PROVIDER_BASIS_MISMATCH")
    buffer = candidate_epsilon * atr.value
    boundary = (pivot.pivot_price + buffer if side is StructureSide.HIGH
                else pivot.pivot_price - buffer)
    if not boundary.is_finite() or boundary < 0:
        return blocked("BUFFER_BOUNDARY_NOT_FINITE_OR_NEGATIVE")
    crossed = (
        prior.close <= boundary and target.close > boundary
        if side is StructureSide.HIGH
        else prior.close >= boundary and target.close < boundary
    )
    witness = max(
        pivot.witness_known_at_utc, prior.verified_at_utc,
        target.verified_at_utc, target.bar_end_utc,
    )
    return BosGeometry(
        side, GeometryState.DESCRIPTIVE_ONLY,
        "CLOSED_CROSS_MATH_ONLY_NOT_A_APPROVED_BOS_EVENT",
        boundary, prior.close, target.close, crossed, witness,
    )
