"""§409 B7 causal support distance, not an approved rebound predicate."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    inspect_causal_pivot, inspect_closed_bos_geometry, _source_identity,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .zone_manifest_v03 import inspect_near_zone_arithmetic


@dataclass(frozen=True)
class B7ReclaimPlan410:
    candidate_epsilon: Decimal


@dataclass(frozen=True)
class B7ChochPlan411:
    history_start: int
    history_stop: int
    high_indices: tuple[int, int]
    low_indices: tuple[int, int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    candidate_epsilon: Decimal


@dataclass(frozen=True)
class B7ConfirmPlan412:
    timeframe: Timeframe
    breakout_index: int
    history_start: int
    history_stop: int
    pivot_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    candidate_epsilon: Decimal


@dataclass(frozen=True)
class B7SupportPlan409:
    target_index: int
    pivot_tf: Timeframe
    pivot_start: int
    pivot_stop: int
    candidate_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_k_near: Decimal | None
    reclaim: B7ReclaimPlan410 | None = None
    choch: B7ChochPlan411 | None = None
    rf: B7ConfirmPlan412 | None = None


class B7SupportState409(str, Enum):
    BLOCKED = "BLOCKED"
    MISSING = "MISSING_INPUT"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class B7SupportIngredient409:
    state: B7SupportState409
    reason: str
    distance_atr: Decimal | None = None
    near_candidate: bool | None = None
    private_support: Decimal | None = None
    private_atr: Decimal | None = None


@dataclass(frozen=True)
class B7SupportPreview409:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _window409(rows, start, stop):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= 512:
        raise ValueError("MST_409_EXPLICIT_WINDOW")
    if stop > len(rows):
        return ()
    return rows[start:stop]


def _validate409(plan):
    if type(plan.pivot_tf) is not Timeframe or plan.pivot_tf not in (Timeframe.D1, Timeframe.H1):
        raise ValueError("MST_409_EXPLICIT_PIVOT_FRAME")
    if type(plan.target_index) is not int or not 0 <= plan.target_index < 512:
        raise ValueError("MST_409_EXPLICIT_TARGET")
    k = plan.candidate_k_near
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k < 0):
        raise ValueError("MST_409_EXPLICIT_K")
    if (type(plan.candidate_index) is not int or plan.candidate_index < 0
            or type(plan.left_count) is not int or not 1 <= plan.left_count <= 40
            or type(plan.right_count) is not int or not 1 <= plan.right_count <= 40
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_409_EXPLICIT_PIVOT")


def _rc409(inputs, plan):
    targets = inputs.snapshots_for(Timeframe.M15)
    history = _window409(inputs.snapshots_for(plan.pivot_tf), plan.pivot_start, plan.pivot_stop)
    daily = _window409(inputs.snapshots_for(Timeframe.D1), plan.atr_start, plan.atr_stop)
    if plan.target_index >= len(targets) or not history or len(daily) < 15:
        return B7SupportIngredient409(B7SupportState409.MISSING, "EXACT_INPUT_MISSING")
    target = _eligible(targets[plan.target_index], cutoff=inputs.as_of_utc)
    if target is None:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "TARGET_NOT_ELIGIBLE")
    cutoff = target.market_bar_key.bar_start_utc
    pivot = inspect_causal_pivot(history, candidate_index=plan.candidate_index,
        left_count=plan.left_count, right_count=plan.right_count, side=StructureSide.LOW,
        tie_policy=plan.tie_policy, as_of_utc=cutoff)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY or pivot.geometric_extremum is not True:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "SUPPORT_NOT_CAUSALLY_AVAILABLE")
    atr = calculate_wilder_atr14(daily, as_of_utc=inputs.as_of_utc, known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "ATR_NOT_CAUSALLY_AVAILABLE")
    if not (_cross_tf_identity(history[0].selected) == _cross_tf_identity(daily[0].selected)
            == _cross_tf_identity(target)):
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "CROSS_FRAME_SOURCE_MISMATCH")
    near = inspect_near_zone_arithmetic(price=target.low, zone_lower=pivot.pivot_price,
        zone_upper=pivot.pivot_price, atr_d1=atr.value, candidate_k_near=plan.candidate_k_near)
    return B7SupportIngredient409(B7SupportState409.DISTANCE,
        "SUPPORT_DISTANCE_ONLY_NO_REVERSAL_OR_RISK_APPROVAL",
        near.normalized_by_atr, near.in_candidate_band, pivot.pivot_price, atr.value)


def _validate_reclaim410(plan, variant_id):
    if type(plan) is not B7ReclaimPlan410 or variant_id != "B7/E_RECLAIM":
        raise ValueError("MST_410_EXPLICIT_RECLAIM_VARIANT")
    epsilon = plan.candidate_epsilon
    if type(epsilon) is not Decimal or not epsilon.is_finite() or epsilon < 0:
        raise ValueError("MST_410_EXPLICIT_EPSILON")


def _reclaim410(inputs, plan, rc):
    rows = inputs.snapshots_for(Timeframe.M15)
    index = plan.target_index + 1
    if index >= len(rows) or rc.state is B7SupportState409.MISSING:
        return B7SupportIngredient409(B7SupportState409.MISSING, "RECLAIM_PAIR_OR_SUPPORT_MISSING")
    if rc.state is not B7SupportState409.DISTANCE:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "PRIOR_SUPPORT_UNRESOLVED")
    target = _eligible(rows[index], cutoff=inputs.as_of_utc)
    if target is None:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "RECLAIM_TARGET_NOT_ELIGIBLE")
    prior = _eligible(rows[index-1], cutoff=target.market_bar_key.bar_start_utc)
    if prior is None or _source_identity(prior) != _source_identity(target):
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "PRIOR_SIDE_NOT_CAUSALLY_AVAILABLE")
    boundary = rc.private_support + plan.reclaim.candidate_epsilon * rc.private_atr
    crossed = prior.close < rc.private_support and target.close > boundary
    state = B7SupportState409.MATCH if crossed else B7SupportState409.NONMATCH
    return B7SupportIngredient409(state, "SAME_SUPPORT_CLOSED_RECLAIM_GEOMETRY_ONLY")


def _validate_micro_pair411(pair):
    if type(pair) is not tuple or len(pair) != 2 or any(type(i) is not int or i < 0 for i in pair):
        raise ValueError("MST_411_EXPLICIT_MICRO_PAIR")


def _validate_choch411(plan, variant_id, prior_index):
    if type(plan) is not B7ChochPlan411 or variant_id != "B7/E_CHOCH":
        raise ValueError("MST_411_EXPLICIT_CHOCH_VARIANT")
    if (type(plan.history_start) is not int or type(plan.history_stop) is not int
            or not 0 <= plan.history_start < plan.history_stop <= prior_index):
        raise ValueError("MST_411_PRE_PRIOR_HISTORY")
    _validate_micro_pair411(plan.high_indices)
    _validate_micro_pair411(plan.low_indices)
    h1,h2 = plan.high_indices
    l1,l2 = plan.low_indices
    if not (h1 < l1 < h2 < l2 or l1 < h1 < l2 < h2):
        raise ValueError("MST_411_ALTERNATING_MICRO_PAIRS")
    _validate_micro_policy411(plan)


def _validate_micro_policy411(plan):
    if (type(plan.left_count) is not int or not 1 <= plan.left_count <= 40
            or type(plan.right_count) is not int or not 1 <= plan.right_count <= 40
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_411_EXPLICIT_MICRO_POLICY")
    epsilon = plan.candidate_epsilon
    if type(epsilon) is not Decimal or not epsilon.is_finite() or epsilon < 0:
        raise ValueError("MST_411_EXPLICIT_EPSILON")


def _micro_shape411(history, p, cutoff):
    def pair(indices, side):
        return tuple(inspect_causal_pivot(history, candidate_index=i,
            left_count=p.left_count, right_count=p.right_count, side=side,
            tie_policy=p.tie_policy, as_of_utc=cutoff) for i in indices)
    highs, lows = pair(p.high_indices, StructureSide.HIGH), pair(p.low_indices, StructureSide.LOW)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY or x.geometric_extremum is not True
           for x in highs+lows):
        return None, None
    falling = highs[1].pivot_price < highs[0].pivot_price and lows[1].pivot_price < lows[0].pivot_price
    return falling, highs[1].pivot_price


def _choch411(inputs, plan):
    p = plan.choch
    rows = inputs.snapshots_for(Timeframe.M15)
    index = plan.target_index + 1
    history = _window409(rows, p.history_start, p.history_stop)
    daily = _window409(inputs.snapshots_for(Timeframe.D1), plan.atr_start, plan.atr_stop)
    if index >= len(rows) or not history or len(daily) < 15:
        return B7SupportIngredient409(B7SupportState409.MISSING, "MICRO_PAIR_OR_ATR_MISSING")
    cutoff = rows[index-1].market_bar_key.bar_start_utc
    falling, upper = _micro_shape411(history, p, cutoff)
    if falling is None:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "MICRO_PIVOTS_UNRESOLVED")
    bos = inspect_closed_bos_geometry(history, pivot_index=p.high_indices[1],
        left_count=p.left_count, right_count=p.right_count, previous=rows[index-1],
        breakout=rows[index], atr_d1_history=daily, side=StructureSide.HIGH,
        tie_policy=p.tie_policy, candidate_epsilon=p.candidate_epsilon, as_of_utc=inputs.as_of_utc)
    if bos.state is GeometryState.BLOCKED:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "MICRO_CROSS_BLOCKED")
    match = falling and bos.candidate_cross is True and bos.previous_close <= upper
    state = B7SupportState409.MATCH if match else B7SupportState409.NONMATCH
    return B7SupportIngredient409(state, "PRIOR_LH_LL_AND_CLOSED_MICRO_HIGH_CROSS_ONLY")


def _validate_rf412(p):
    if type(p) is not B7ConfirmPlan412 or type(p.timeframe) is not Timeframe:
        raise ValueError("MST_412_EXPLICIT_RF_PLAN")
    if p.timeframe not in (Timeframe.M15, Timeframe.H1):
        raise ValueError("MST_412_EXPLICIT_RF_FRAME")
    if (type(p.breakout_index) is not int or not 1 <= p.breakout_index < 512
            or type(p.history_start) is not int or type(p.history_stop) is not int
            or not 0 <= p.history_start < p.history_stop < p.breakout_index):
        raise ValueError("MST_412_EXPLICIT_PRIOR_WINDOW")
    if type(p.pivot_index) is not int or p.pivot_index < 0:
        raise ValueError("MST_412_EXPLICIT_PIVOT")
    _validate_micro_policy411(p)


def _early_before_rf412(inputs, plan, prior, target):
    early_rows = inputs.snapshots_for(Timeframe.M15)
    index = plan.target_index + 1
    if index >= len(early_rows):
        return False
    early = _eligible(early_rows[index], cutoff=prior.market_bar_key.bar_start_utc)
    return (early is not None and _cross_tf_identity(early) == _cross_tf_identity(target)
            and (plan.rf.timeframe is not Timeframe.M15
                 or _source_identity(early) == _source_identity(target)))


def _rf_cross412(inputs, plan, rows, history, daily):
    p = plan.rf
    index = p.breakout_index
    target = _eligible(rows[index], cutoff=inputs.as_of_utc)
    if target is None:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "RF_TARGET_NOT_ELIGIBLE")
    prior = _eligible(rows[index-1], cutoff=target.market_bar_key.bar_start_utc)
    if prior is None or not _early_before_rf412(inputs, plan, prior, target):
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "EARLY_NOT_KNOWN_BEFORE_RF_PRIOR")
    bos = inspect_closed_bos_geometry(history, pivot_index=p.pivot_index,
        left_count=p.left_count, right_count=p.right_count, previous=rows[index-1],
        breakout=rows[index], atr_d1_history=daily, side=StructureSide.HIGH,
        tie_policy=p.tie_policy, candidate_epsilon=p.candidate_epsilon, as_of_utc=inputs.as_of_utc)
    if bos.state is GeometryState.BLOCKED:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "RF_MICRO_CROSS_BLOCKED")
    match = bos.candidate_cross is True and bos.previous_close <= history[p.pivot_index].selected.high
    state = B7SupportState409.MATCH if match else B7SupportState409.NONMATCH
    return B7SupportIngredient409(state, "LATER_CLOSED_MICRO_HIGH_CROSS_ONLY")


def _rf412(inputs, plan, early):
    if early is None or early.state is B7SupportState409.MISSING:
        return B7SupportIngredient409(B7SupportState409.MISSING, "EXPLICIT_EARLY_GEOMETRY_MISSING")
    if early.state is not B7SupportState409.MATCH:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "EARLY_GEOMETRY_NOT_MATCHED")
    p = plan.rf
    rows = inputs.snapshots_for(p.timeframe)
    history = _window409(rows, p.history_start, p.history_stop)
    daily = _window409(inputs.snapshots_for(Timeframe.D1), plan.atr_start, plan.atr_stop)
    if p.breakout_index >= len(rows) or not history or len(daily) < 15:
        return B7SupportIngredient409(B7SupportState409.MISSING, "RF_PAIR_PIVOT_OR_ATR_MISSING")
    return _rf_cross412(inputs, plan, rows, history, daily)


def inspect_b7_support_preview(inputs, *, strategy, variant_id, plan):
    """Explicit M15 low and D1/H1 pivot diagnostic; RC timeframe remains pending."""
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not B7SupportPlan409
            or variant_id not in ("B7/E_RECLAIM", "B7/E_CHOCH")):
        raise ValueError("MST_409_EXACT_SCOPE")
    _validate409(plan)
    route = route_phase_inputs(inputs, zone_id="B7", strategy=strategy,
                               variant_id=variant_id, phase="R_C")
    rc = _rc409(inputs, plan)
    assessments = ((route, rc),)
    if plan.reclaim is not None:
        _validate_reclaim410(plan.reclaim, variant_id)
        early = route_phase_inputs(inputs, zone_id="B7", strategy=strategy,
                                   variant_id=variant_id, phase="R_E")
        assessments += ((early, _reclaim410(inputs, plan, rc)),)
    if plan.choch is not None:
        _validate_choch411(plan.choch, variant_id, plan.target_index)
        early = route_phase_inputs(inputs, zone_id="B7", strategy=strategy,
                                   variant_id=variant_id, phase="R_E")
        assessments += ((early, _choch411(inputs, plan)),)
    if plan.rf is not None:
        _validate_rf412(plan.rf)
        route = route_phase_inputs(inputs, zone_id="B7", strategy=strategy,
            variant_id=variant_id, phase="R_F", selected_frame=plan.rf.timeframe)
        early_proof = assessments[-1][1] if len(assessments) > 1 else None
        assessments += ((route, _rf412(inputs, plan, early_proof)),)
    return B7SupportPreview409(assessments)
