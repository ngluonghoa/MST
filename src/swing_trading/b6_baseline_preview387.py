"""§387 B6 causal contraction and M15 upper-pivot approach ingredients."""
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from enum import Enum

from .causal_compression_candidate395 import AtrPercentilePlan395, inspect_atr_percentile_candidate
from .causal_contraction_candidate386 import ContractionPlan386, inspect_d1_contraction_candidate
from .causal_cross_tf_candidate392 import inspect_h1_cross_of_d1_upper_pivot
from .causal_indicators import (
    CausalIndicatorResult, IndicatorState, VolumeBasisWitness, VolumeComparisonBar,
    VolumeSessionClass, calculate_rvol_tf20_raw_matched, calculate_wilder_atr14,
)
from .causal_range_percentile397 import RangePercentilePlan397, inspect_range_percentile_candidate
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _source_identity,
    inspect_closed_bos_geometry,
)
from .causal_trend_candidate382 import inspect_d1_paired_trend_candidate
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .source_quality import CoverageState


@dataclass(frozen=True)
class B6RFVolumePlan389:
    comparison_policy_version: str
    witnesses: tuple[VolumeBasisWitness, ...]


@dataclass(frozen=True)
class B6RFPlan388:
    breakout_index: int
    candidate_epsilon: Decimal
    volume: B6RFVolumePlan389 | None = None


@dataclass(frozen=True)
class B6H1VolumePlan394:
    comparison_policy_version: str
    session_classes: tuple[VolumeSessionClass, ...]
    witnesses: tuple[VolumeBasisWitness, ...]


@dataclass(frozen=True)
class B6H1RFPlan393:
    breakout_index: int
    candidate_epsilon: Decimal
    volume: B6H1VolumePlan394 | None = None


@dataclass(frozen=True)
class B6TrendPlan390:
    lookback: int
    high_indices: tuple[int, ...]
    low_indices: tuple[int, ...]
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class B6CompressionPlan396:
    target_index: int
    percentile: AtrPercentilePlan395 | RangePercentilePlan397


@dataclass(frozen=True)
class B6EnginePlan387:
    d1_start: int
    d1_stop: int
    contraction: ContractionPlan386
    atr_start: int
    atr_stop: int
    target_index: int
    candidate_k_near: Decimal
    rf: B6RFPlan388 | B6H1RFPlan393 | None = None
    r0: B6TrendPlan390 | None = None


class B6State387(str, Enum):
    BLOCKED = "BLOCKED"
    MISSING = "MISSING_INPUT"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"


@dataclass(frozen=True)
class B6Ingredient387:
    state: B6State387
    reason: str
    contraction: object | None = None
    distance: Decimal | None = None
    approach: bool | None = None
    volume_state: str = "NOT_REQUESTED"
    rvol: CausalIndicatorResult | None = None
    compression: object | None = None

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


@dataclass(frozen=True)
class B6EnginePreview387:
    assessments: tuple

    def safe_rf_volume_summary(self):
        rf = next((e for r,e in self.assessments if r.phase == "R_F"), None)
        return {"schema": "mst.private.b6_rf_volume.v0.1",
                "volume_state": "NOT_REQUESTED" if rf is None else rf.volume_state,
                "volume_approved": False, "source_qualified": False,
                "risk_approved": False, "action_eligible": False}

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _slice387(rows, start, stop):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop:
        raise ValueError("MST_387_INVALID_SLICE")
    if rows and stop > len(rows):
        raise ValueError("MST_387_SLICE_OUTSIDE_SCOPE")
    return rows[start:stop]


def _check_plan387(plan):
    if type(plan) is not B6EnginePlan387 or type(plan.contraction) is not ContractionPlan386:
        raise ValueError("MST_387_EXPLICIT_PLAN")
    if type(plan.target_index) is not int or plan.target_index < 1:
        raise ValueError("MST_387_REQUIRE_PRIOR_M15_INDEX")
    k = plan.candidate_k_near
    if type(k) is not Decimal or not k.is_finite() or k < 0:
        raise ValueError("MST_387_EXPLICIT_NEAR_MULTIPLIER")


def _rc387(history, plan, cutoff):
    if not history:
        return B6Ingredient387(B6State387.MISSING, "CONTRACTION_HISTORY_MISSING")
    result = inspect_d1_contraction_candidate(history, plan=plan.contraction, as_of_utc=cutoff)
    state = B6State387.BLOCKED
    if result.reason == "PULLBACK_DEPTH_GEOMETRY_ONLY":
        state = B6State387.MATCH if result.trailing_contractions >= 2 else B6State387.NONMATCH
    return B6Ingredient387(state, result.reason, result)


def _m15_pair387(inputs, index):
    rows = inputs.snapshots_for(Timeframe.M15)
    if not rows:
        return None
    if index >= len(rows):
        raise ValueError("MST_387_TARGET_OUTSIDE_SCOPE")
    return rows[index-1], rows[index]


def _pair_ok387(pair, cutoff):
    previous, target = pair
    if not target.confirmation_prerequisites(cutoff):
        return False
    bar = target.selected
    if not previous.confirmation_prerequisites(bar.market_bar_key.bar_start_utc):
        return False
    prior = previous.selected
    return (prior.coverage_state is bar.coverage_state is CoverageState.COMPLETE
            and prior.bar_end_utc <= bar.market_bar_key.bar_start_utc
            and _source_identity(prior) == _source_identity(bar))


def _distance387(pair, history, atr_rows, plan, atr):
    target = pair[1].selected
    previous = pair[0].selected
    if not all(_cross_tf_identity(x.selected) == _cross_tf_identity(target)
               for x in (history[0], atr_rows[0])):
        return B6Ingredient387(B6State387.BLOCKED, "CROSS_TF_SOURCE_MISMATCH")
    # Explicit last selected high, not an inferred highest/most recent pivot.
    high = history[plan.contraction.swings[-1][0]].selected.high
    distance = abs(high - target.close)
    approach = previous.close < target.close <= high and distance <= plan.candidate_k_near * atr.value
    return B6Ingredient387(B6State387.DISTANCE, "CLOSED_RISE_AND_NEAR_GEOMETRY_ONLY",
                           distance=distance, approach=approach)


def _re387(inputs, history, atr_rows, plan):
    pair = _m15_pair387(inputs, plan.target_index)
    if pair is None or not history or not atr_rows:
        return B6Ingredient387(B6State387.MISSING, "CONTRACTION_ATR_OR_M15_MISSING")
    if not _pair_ok387(pair, inputs.as_of_utc):
        return B6Ingredient387(B6State387.BLOCKED, "M15_PAIR_NOT_CAUSALLY_AVAILABLE")
    cutoff = pair[1].selected.market_bar_key.bar_start_utc
    rc = _rc387(history, plan, cutoff)
    if rc.state is not B6State387.MATCH:
        return B6Ingredient387(B6State387.BLOCKED, "TWO_CONTRACTIONS_NOT_AVAILABLE_BEFORE_TARGET")
    # ATR must be validated before inspecting its selected row.
    atr = calculate_wilder_atr14(atr_rows, as_of_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return B6Ingredient387(B6State387.BLOCKED, "ATR_PREFIX_BLOCKED")
    return _distance387(pair, history, atr_rows, plan, atr)



def _rf_plan388(plan):
    rf = plan.rf
    if type(rf) is not B6RFPlan388 or type(rf.breakout_index) is not int:
        raise ValueError("MST_388_EXPLICIT_D1_BREAKOUT_PLAN")
    if rf.breakout_index <= plan.d1_stop:
        raise ValueError("MST_388_BREAKOUT_AND_PRIOR_MUST_FOLLOW_CONTRACTION_SLICE")
    eps = rf.candidate_epsilon
    if type(eps) is not Decimal or not eps.is_finite() or eps < 0:
        raise ValueError("MST_388_EXPLICIT_EPSILON")


def _rf_rows388(inputs, plan):
    rows = inputs.snapshots_for(Timeframe.D1)
    if not rows:
        return None
    index = plan.rf.breakout_index
    if index >= len(rows):
        return None
    return rows[index-1], rows[index]


def _rf_order388(inputs, pair, plan):
    m15 = _m15_pair387(inputs, plan.target_index)
    if m15 is None or pair[1].selected is None:
        return False
    cutoff = pair[1].selected.market_bar_key.bar_start_utc
    return m15[1].confirmation_prerequisites(cutoff)


def _cross388(history, atr_rows, pair, plan, cutoff):
    p = plan.contraction
    return inspect_closed_bos_geometry(
        history, pivot_index=p.swings[-1][0], left_count=p.left_count,
        right_count=p.right_count, side=StructureSide.HIGH, tie_policy=p.tie_policy,
        previous=pair[0], breakout=pair[1], atr_d1_history=atr_rows,
        candidate_epsilon=plan.rf.candidate_epsilon, as_of_utc=cutoff,
    )


def _rf388(inputs, history, atr_rows, plan, early):
    _rf_plan388(plan)
    pair = _rf_rows388(inputs, plan)
    if pair is None:
        return B6Ingredient387(B6State387.MISSING, "D1_BREAKOUT_OR_PREVIOUS_MISSING")
    if early.state is not B6State387.DISTANCE or early.approach is not True:
        return B6Ingredient387(B6State387.BLOCKED, "M15_APPROACH_GEOMETRY_MISSING")
    if not _rf_order388(inputs, pair, plan):
        return B6Ingredient387(B6State387.BLOCKED, "M15_APPROACH_NOT_KNOWN_BEFORE_BREAKOUT")
    geom = _cross388(history, atr_rows, pair, plan, inputs.as_of_utc)
    if geom.state is GeometryState.BLOCKED:
        return B6Ingredient387(B6State387.BLOCKED, "D1_CLOSED_CROSS_" + geom.reason)
    state = B6State387.MATCH if geom.candidate_cross else B6State387.NONMATCH
    return B6Ingredient387(state, "SAME_PIVOT_D1_CROSS_ONLY_VOLUME_RISK_PENDING")



def _check_volume389(plan):
    if (type(plan) is not B6RFVolumePlan389
            or type(plan.comparison_policy_version) is not str
            or not plan.comparison_policy_version.strip()
            or type(plan.witnesses) is not tuple or len(plan.witnesses) != 21
            or any(type(w) is not VolumeBasisWitness for w in plan.witnesses)):
        raise ValueError("MST_389_EXACT_RAW_MATCHED_WITNESS_PLAN")


def _volume389(inputs, rf, geometry):
    if rf.volume is None:
        return replace(geometry, volume_state="RAW_MATCHED_WITNESS_MISSING")
    plan = rf.volume
    _check_volume389(plan)
    rows = inputs.snapshots_for(Timeframe.D1)
    index = rf.breakout_index
    if index < 20 or index >= len(rows):
        return replace(geometry, volume_state="EXACT_TARGET_OR_PRIOR20_MISSING")
    tagged = tuple(VolumeComparisonBar(row, VolumeSessionClass.DAILY,
                                      plan.comparison_policy_version)
                   for row in rows[index-20:index+1])
    rvol = calculate_rvol_tf20_raw_matched(
        tagged[-1], tagged[:-1], target_witness=plan.witnesses[-1],
        prior_witnesses=plan.witnesses[:-1], as_of_utc=inputs.as_of_utc,
    )
    state = ("RVOL_COMPUTED_UNCALIBRATED" if rvol.state is IndicatorState.COMPUTED_UNCALIBRATED
             else "RVOL_BLOCKED")
    return replace(geometry, volume_state=state, rvol=rvol)



def _trend390(rows, history, plan):
    trend = plan.r0
    if type(trend) is not B6TrendPlan390:
        raise ValueError("MST_390_EXPLICIT_TREND_PLAN")
    if type(trend.lookback) is not int or not 1 <= trend.lookback <= 462:
        raise ValueError("MST_390_BOUNDED_LOOKBACK")
    if not history or plan.d1_start < 50 + trend.lookback:
        return None
    prefix = rows[plan.d1_start - 50 - trend.lookback:plan.d1_start]
    # Exact preceding window, no skipping unresolved rows, no later trend.
    return inspect_d1_paired_trend_candidate(
        prefix, as_of_utc=history[0].market_bar_key.bar_start_utc, **asdict(trend))


def _r0390(rows, history, plan, rc):
    trend = _trend390(rows, history, plan)
    if trend is None:
        return B6Ingredient387(B6State387.MISSING, "PRIOR_D1_TREND_WINDOW_MISSING")
    if trend["relation"] == "BLOCKED_INPUT" or trend["structure"] in (
            "MISSING_PAIR", "BLOCKED_PIVOT", "INCONSISTENT_ORDER", "NON_EXTREMUM"):
        return B6Ingredient387(B6State387.BLOCKED, "PRIOR_D1_TREND_GEOMETRY_UNRESOLVED")
    if rc.contraction is None or rc.contraction.reason != "PULLBACK_DEPTH_GEOMETRY_ONLY":
        return B6Ingredient387(B6State387.BLOCKED, "CONTRACTION_PIVOTS_UNRESOLVED")
    if trend["relation"] == "ALIGNED_GEOMETRY_ONLY":
        if trend["structure"] == "HH_HL_GEOMETRY":
            return B6Ingredient387(B6State387.MATCH, "PRIOR_D1_RISE_AND_CONTRACTION_PIVOTS_ONLY")
        return B6Ingredient387(B6State387.NONMATCH, "PRIOR_D1_OPPOSITE_GEOMETRY_ONLY")
    return B6Ingredient387(B6State387.BLOCKED, "PRIOR_D1_DIRECTION_UNRESOLVED")



def _h1_pair393(inputs, rf):
    if type(rf.breakout_index) is not int or rf.breakout_index < 1:
        raise ValueError("MST_393_EXPLICIT_H1_BREAKOUT_INDEX")
    eps = rf.candidate_epsilon
    if type(eps) is not Decimal or not eps.is_finite() or eps < 0:
        raise ValueError("MST_393_EXPLICIT_H1_EPSILON")
    rows = inputs.snapshots_for(Timeframe.H1)
    if rf.breakout_index >= len(rows):
        return None
    return rows[rf.breakout_index-1], rows[rf.breakout_index]


def _h1_cross393(inputs, history, atr_rows, plan, pair):
    p = plan.contraction
    geom = inspect_h1_cross_of_d1_upper_pivot(
        history, pivot_index=p.swings[-1][0], left_count=p.left_count,
        right_count=p.right_count, tie_policy=p.tie_policy,
        previous=pair[0], breakout=pair[1], atr_d1_history=atr_rows,
        candidate_epsilon=plan.rf.candidate_epsilon, as_of_utc=inputs.as_of_utc,
    )
    if geom.state is GeometryState.BLOCKED:
        return B6Ingredient387(B6State387.BLOCKED, "H1_CLOSED_CROSS_" + geom.reason)
    state = B6State387.MATCH if geom.candidate_cross else B6State387.NONMATCH
    return B6Ingredient387(state, "SAME_PIVOT_H1_CROSS_ONLY_VOLUME_RISK_PENDING")


def _rf_h1393(inputs, history, atr_rows, plan, early):
    pair = _h1_pair393(inputs, plan.rf)
    if pair is None:
        return B6Ingredient387(B6State387.MISSING, "H1_BREAKOUT_OR_PREVIOUS_MISSING")
    if early.state is not B6State387.DISTANCE or early.approach is not True:
        return B6Ingredient387(B6State387.BLOCKED, "M15_APPROACH_GEOMETRY_MISSING")
    if not _rf_order388(inputs, pair, plan):
        return B6Ingredient387(B6State387.BLOCKED, "M15_APPROACH_NOT_KNOWN_BEFORE_BREAKOUT")
    return _h1_cross393(inputs, history, atr_rows, plan, pair)



def _check_h1_volume394(plan):
    if (type(plan) is not B6H1VolumePlan394
            or type(plan.comparison_policy_version) is not str
            or not plan.comparison_policy_version.strip()
            or type(plan.session_classes) is not tuple or len(plan.session_classes) != 21
            or any(type(c) is not VolumeSessionClass for c in plan.session_classes)
            or type(plan.witnesses) is not tuple or len(plan.witnesses) != 21
            or any(type(w) is not VolumeBasisWitness for w in plan.witnesses)):
        raise ValueError("MST_394_EXPLICIT_H1_VOLUME_PLAN")


def _h1_volume394(inputs, rf, geometry):
    if rf.volume is None:
        return replace(geometry, volume_state="H1_VOLUME_SPEC_PENDING")
    plan = rf.volume
    _check_h1_volume394(plan)
    rows = inputs.snapshots_for(Timeframe.H1)
    index = rf.breakout_index
    if index < 20 or index >= len(rows):
        return replace(geometry, volume_state="EXACT_TARGET_OR_PRIOR20_MISSING")
    tagged = tuple(VolumeComparisonBar(row, session, plan.comparison_policy_version)
                   for row, session in zip(rows[index-20:index+1], plan.session_classes))
    rvol = calculate_rvol_tf20_raw_matched(
        tagged[-1], tagged[:-1], target_witness=plan.witnesses[-1],
        prior_witnesses=plan.witnesses[:-1], as_of_utc=inputs.as_of_utc,
    )
    state = ("RVOL_COMPUTED_UNCALIBRATED" if rvol.state is IndicatorState.COMPUTED_UNCALIBRATED
             else "RVOL_BLOCKED")
    return replace(geometry, volume_state=state, rvol=rvol)


def _routed_rf393(inputs, history, atr_rows, plan, early, scope):
    if type(plan.rf) is B6H1RFPlan393:
        route = route_phase_inputs(inputs, phase="R_F", selected_frame=Timeframe.H1, **scope)
        result = _rf_h1393(inputs, history, atr_rows, plan, early)
        return route, _h1_volume394(inputs, plan.rf, result)
    route = route_phase_inputs(inputs, phase="R_F", selected_frame=Timeframe.D1, **scope)
    geometry = _rf388(inputs, history, atr_rows, plan, early)
    return route, _volume389(inputs, plan.rf, geometry)


def inspect_b6_baseline_preview(inputs, *, strategy, variant_id, plan):
    """Only explicit two-contraction branch; not an approved R0 or R_F.

    No alternate compression fallback, no claimed volume dry-up or ATR approval.
    Target must be M15 and both D1 histories causally known at target start.
    """
    if type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy:
        raise ValueError("MST_387_BASELINE_SCOPE")
    if variant_id != "B6/C_TWO_CONTRACTIONS":
        raise ValueError("MST_387_EXACT_CONTRACTION_VARIANT")
    _check_plan387(plan)
    rows = inputs.snapshots_for(Timeframe.D1)
    history = _slice387(rows, plan.d1_start, plan.d1_stop)
    atr_rows = _slice387(rows, plan.atr_start, plan.atr_stop)
    scope = dict(zone_id="B6", strategy=strategy, variant_id=variant_id)
    rc = route_phase_inputs(inputs, phase="R_C", **scope)
    re = route_phase_inputs(inputs, phase="R_E", **scope)
    early = _re387(inputs, history, atr_rows, plan)
    contraction = _rc387(history, plan, inputs.as_of_utc)
    assessments = ((rc, contraction), (re, early))
    if plan.r0 is not None:
        r0 = route_phase_inputs(inputs, phase="R0", selected_frame=Timeframe.D1, **scope)
        assessments = ((r0, _r0390(rows, history, plan, contraction)),) + assessments
    if plan.rf is not None:
        assessments += (_routed_rf393(inputs, history, atr_rows, plan, early, scope),)
    return B6EnginePreview387(assessments)


def _compression_method398(p):
    if type(p) is AtrPercentilePlan395:
        return inspect_atr_percentile_candidate, 14, "EXACT_ATR_WINDOW_MISSING"
    if type(p) is RangePercentilePlan397:
        return inspect_range_percentile_candidate, 0, "EXACT_RANGE_WINDOW_MISSING"
    raise ValueError("MST_398_EXPLICIT_COMPRESSION_METHOD")


def inspect_b6_compression_preview(inputs, *, strategy, variant_id, plan):
    """Explicit alternate R_C candidate only; never infer R0/RE/RF."""
    if type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy:
        raise ValueError("MST_396_BASELINE_SCOPE")
    if variant_id != "B6/C_COMPRESSION" or type(plan) is not B6CompressionPlan396:
        raise ValueError("MST_396_EXACT_COMPRESSION_VARIANT")
    if type(plan.target_index) is not int or plan.target_index < 0:
        raise ValueError("MST_396_EXPLICIT_TARGET_INDEX")
    p = plan.percentile
    # Validate the explicit parameters even if the exact window is missing.
    method, warmup, missing = _compression_method398(p)
    method((), plan=p, as_of_utc=inputs.as_of_utc)
    rows = inputs.snapshots_for(Timeframe.D1)
    start = plan.target_index - (warmup + p.reference_count)
    if start < 0 or plan.target_index >= len(rows):
        result = B6Ingredient387(B6State387.MISSING, missing)
    else:
        proof = method(
            rows[start:plan.target_index+1], plan=p, as_of_utc=inputs.as_of_utc)
        state = B6State387.BLOCKED
        if proof.at_or_below is not None:
            state = B6State387.MATCH if proof.at_or_below else B6State387.NONMATCH
        result = B6Ingredient387(state, proof.reason, compression=proof)
    route = route_phase_inputs(inputs, zone_id="B6", strategy=strategy,
                               variant_id=variant_id, phase="R_C")
    return B6EnginePreview387(((route, result),))
