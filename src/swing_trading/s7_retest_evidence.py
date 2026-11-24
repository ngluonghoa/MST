"""§264 S7 R0/R_C geometry, not a detector. Frozen spec §§16.7,24.4/5.
Reuse causal LOW pivot/BOS and prior ATR; no inferred expiry, thresholds,
calendar, source entitlement, trade or approved S7 phase.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, inspect_causal_pivot,
    inspect_closed_bos_geometry, _eligible, _cross_tf_identity, _source_identity,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .replay import require_utc
from .structural_phase_evidence import _bar_identity, _digest


@dataclass(frozen=True)
class S7RetestEvidence:
    strategy: Strategy
    as_of_utc: datetime
    reason: str
    origin_preview_id: str | None = None
    retest_preview_id: str | None = None
    close_distance_atr: Decimal | None = None
    range_distance_atr: Decimal | None = None
    close_above_pivot: bool | None = None
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    action_eligible: bool = False
    parameter_approved: bool = False
    detector_approved: bool = False

    def __post_init__(self):
        require_utc(self.as_of_utc)
        if (not isinstance(self.strategy, Strategy) or not self.reason
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False
                or self.parameter_approved is not False
                or self.detector_approved is not False):
            raise ValueError("S7_PREVIEW_AUTHORITY_FORBIDDEN")
        fields = (self.origin_preview_id, self.retest_preview_id,
                  self.close_distance_atr, self.range_distance_atr,
                  self.close_above_pivot)
        if any(x is not None for x in fields):
            if (any(x is None for x in fields)
                    or self.reason != "EXACT_PIVOT_GEOMETRY_UNCALIBRATED"
                    or type(self.close_above_pivot) is not bool
                    or any(type(x) is not Decimal or not x.is_finite() or x < 0
                           for x in fields[2:4])
                    or any(type(x) is not str or len(x) != 64
                           or any(c not in "0123456789abcdef" for c in x)
                           for x in fields[:2])):
                raise ValueError("S7_PREVIEW_SHAPE_INVALID")
        elif self.reason == "EXACT_PIVOT_GEOMETRY_UNCALIBRATED":
            raise ValueError("S7_PREVIEW_MISSING_GEOMETRY")


def inspect_s7_retest_evidence(
    pivot_history, *, pivot_index, left_count, right_count, tie_policy,
    previous, breakdown, prior_retest, retest, atr_d1_history,
    retest_atr_d1_history, candidate_epsilon, strategy, as_of_utc,
):
    """One original support break, then one later M15 observation from below.
    No declaration that the supplied prior bars are exchange-adjacent;
    no window policy or approved NEAR predicate. All outputs UNVERIFIED.
    """
    require_utc(as_of_utc)

    def blocked(reason):
        return S7RetestEvidence(strategy, as_of_utc, reason)

    a = _eligible(breakdown, cutoff=as_of_utc)
    b = _eligible(retest, cutoff=as_of_utc)
    if a is None or b is None:
        return blocked("SOURCE_OR_ASOF_UNVERIFIED")
    ka, kb = a.market_bar_key, b.market_bar_key
    if ka.timeframe not in (Timeframe.D1, Timeframe.H1) or kb.timeframe is not Timeframe.M15:
        return blocked("S7_REQUIRES_D1_H1_ORIGIN_AND_M15_REFERENCE")
    if _cross_tf_identity(a) != _cross_tf_identity(b):
        return blocked("MIXED_SOURCE_OR_BASIS")
    cutoff = kb.bar_start_utc
    prior = _eligible(prior_retest, cutoff=cutoff)
    if (prior is None or prior.market_bar_key.timeframe is not Timeframe.M15
            or _source_identity(prior) != _source_identity(b)
            or prior.bar_end_utc > cutoff or prior.market_bar_key == kb
            or _eligible(breakdown, cutoff=prior.market_bar_key.bar_start_utc) is None):
        return blocked("RETEST_SEQUENCE_OR_PRIOR_NOT_KNOWN")
    bos = inspect_closed_bos_geometry(
        pivot_history, pivot_index=pivot_index, left_count=left_count,
        right_count=right_count, previous=previous, breakout=breakdown,
        atr_d1_history=atr_d1_history, side=StructureSide.LOW,
        tie_policy=tie_policy, candidate_epsilon=candidate_epsilon,
        as_of_utc=prior.market_bar_key.bar_start_utc,
    )
    if bos.state is not GeometryState.DESCRIPTIVE_ONLY or bos.candidate_cross is not True:
        return blocked("NO_CAUSAL_LOW_PIVOT_CROSS")
    pivot = inspect_causal_pivot(
        pivot_history, candidate_index=pivot_index, left_count=left_count,
        right_count=right_count, side=StructureSide.LOW, tie_policy=tie_policy,
        as_of_utc=ka.bar_start_utc,
    )
    if pivot.pivot_price is None or prior.close >= pivot.pivot_price:
        return blocked("NO_APPROACH_FROM_BELOW")
    atr = calculate_wilder_atr14(
        retest_atr_d1_history, as_of_utc=as_of_utc, known_before_utc=cutoff,
    )
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None or atr.value <= 0:
        return blocked("RETEST_ATR_UNAVAILABLE")
    if _cross_tf_identity(retest_atr_d1_history[0].selected) != _cross_tf_identity(b):
        return blocked("RETEST_ATR_SOURCE_MISMATCH")
    price = pivot.pivot_price
    origin = _digest({"version": "S7_ORIGIN_PREVIEW_264", "pivot_history":
                      [_bar_identity(x) for x in pivot_history],
                      "index": pivot_index, "left": left_count, "right": right_count,
                      "tie": tie_policy.value, "epsilon": str(candidate_epsilon),
                      "previous": _bar_identity(previous),
                      "breakdown": _bar_identity(breakdown),
                      "atr": [_bar_identity(x) for x in atr_d1_history]})
    evidence = _digest({"version": "S7_RETEST_PREVIEW_264", "origin": origin,
                        "prior": _bar_identity(prior_retest),
                        "retest": _bar_identity(retest),
                        "atr": [_bar_identity(x) for x in retest_atr_d1_history]})
    return S7RetestEvidence(
        strategy, as_of_utc, "EXACT_PIVOT_GEOMETRY_UNCALIBRATED",
        origin, evidence, abs(b.close-price)/atr.value,
        max(b.low-price, Decimal(0), price-b.high)/atr.value, b.close > price,
    )
