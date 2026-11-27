"""§415 B8 explicit prior base and resistance candidate; not an approved base."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, inspect_causal_pivot, _source_identity,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .zone_manifest_v03 import inspect_near_zone_arithmetic


@dataclass(frozen=True)
class B8NearPlan416:
    candidate_k_near: Decimal | None


@dataclass(frozen=True)
class B8EarlyPlan417:
    candidate_epsilon: Decimal


@dataclass(frozen=True)
class B8BasePlan415:
    timeframe: Timeframe
    target_index: int
    base_start: int
    base_stop: int
    pivot_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_max_width_atr: Decimal | None
    near: B8NearPlan416 | None = None
    early: B8EarlyPlan417 | None = None


class B8State415(str, Enum):
    MISSING = "MISSING_INPUT"
    BLOCKED = "BLOCKED"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class B8Ingredient415:
    state: B8State415
    reason: str
    width_atr: Decimal | None = None
    private_resistance: Decimal | None = None
    private_atr: Decimal | None = None
    distance_atr: Decimal | None = None


@dataclass(frozen=True)
class B8Preview415:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _check_bounds415(start, stop, minimum):
    if (type(start) is not int or type(stop) is not int
            or not 0 <= start < stop <= 512 or stop-start < minimum):
        raise ValueError("MST_415_EXACT_BOUNDED_WINDOW")


def _validate415(p):
    if type(p.timeframe) is not Timeframe or p.timeframe not in (Timeframe.D1, Timeframe.H1):
        raise ValueError("MST_415_EXPLICIT_BASE_FRAME")
    if type(p.target_index) is not int or not 0 <= p.target_index < 512:
        raise ValueError("MST_415_EXPLICIT_M15_TARGET")
    _check_bounds415(p.base_start,p.base_stop,3)
    _check_bounds415(p.atr_start,p.atr_stop,15)
    _validate_pivot415(p)


def _validate_pivot415(p):
    if (type(p.pivot_index) is not int or not 0 <= p.pivot_index < p.base_stop-p.base_start
            or type(p.left_count) is not int or not 1 <= p.left_count <= 40
            or type(p.right_count) is not int or not 1 <= p.right_count <= 40
            or type(p.tie_policy) is not TiePolicy):
        raise ValueError("MST_415_EXPLICIT_PIVOT_POLICY")
    k = p.candidate_max_width_atr
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k < 0):
        raise ValueError("MST_415_EXPLICIT_WIDTH_MULTIPLIER")


def _base_geometry415(history, daily, target, p):
    cutoff = target.market_bar_key.bar_start_utc
    bars, _ = _sequence(history, cutoff=cutoff)
    if bars is None:
        return B8Ingredient415(B8State415.BLOCKED, "BASE_NOT_CAUSALLY_AVAILABLE")
    pivot = inspect_causal_pivot(history, candidate_index=p.pivot_index,
        left_count=p.left_count, right_count=p.right_count, side=StructureSide.HIGH,
        tie_policy=p.tie_policy, as_of_utc=cutoff)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return B8Ingredient415(B8State415.BLOCKED, "RESISTANCE_PIVOT_UNRESOLVED")
    atr = calculate_wilder_atr14(daily, as_of_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None or atr.value <= 0:
        return B8Ingredient415(B8State415.BLOCKED, "D1_ATR_NOT_CAUSALLY_AVAILABLE")
    if not (_cross_tf_identity(bars[0]) == _cross_tf_identity(daily[0].selected)
            == _cross_tf_identity(target)):
        return B8Ingredient415(B8State415.BLOCKED, "BASE_ATR_TARGET_SOURCE_MISMATCH")
    return _width415(bars, pivot, atr.value, p.candidate_max_width_atr)


def _width415(bars, pivot, atr, k):
    upper = max(b.high for b in bars)
    lower = min(b.low for b in bars)
    if pivot.geometric_extremum is not True or pivot.pivot_price != upper or upper <= lower:
        return B8Ingredient415(B8State415.NONMATCH, "PIVOT_NOT_UPPER_BASE_BOUNDARY")
    width = (upper-lower)/atr
    if k is None:
        return B8Ingredient415(B8State415.DISTANCE, "BASE_WIDTH_UNCALIBRATED", width, upper, atr)
    state = B8State415.MATCH if width <= k else B8State415.NONMATCH
    return B8Ingredient415(state, "BASE_WIDTH_AND_RESISTANCE_GEOMETRY_ONLY", width, upper, atr)


def _r0415(inputs, p):
    rows = inputs.snapshots_for(p.timeframe)
    d1 = inputs.snapshots_for(Timeframe.D1)
    m15 = inputs.snapshots_for(Timeframe.M15)
    if p.base_stop > len(rows) or p.atr_stop > len(d1) or p.target_index >= len(m15):
        return B8Ingredient415(B8State415.MISSING, "EXACT_BASE_ATR_OR_TARGET_MISSING")
    target = _eligible(m15[p.target_index], cutoff=inputs.as_of_utc)
    if target is None:
        return B8Ingredient415(B8State415.BLOCKED, "M15_TARGET_NOT_ELIGIBLE")
    return _base_geometry415(rows[p.base_start:p.base_stop], d1[p.atr_start:p.atr_stop], target, p)


def _validate_near416(p):
    if type(p) is not B8NearPlan416:
        raise ValueError("MST_416_EXPLICIT_NEAR_PLAN")
    k = p.candidate_k_near
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k < 0):
        raise ValueError("MST_416_EXPLICIT_NEAR_THRESHOLD")


def _near416(inputs, p, base):
    rows = inputs.snapshots_for(Timeframe.M15)
    index = p.target_index
    if index+1 >= len(rows) or base.state is B8State415.MISSING:
        return B8Ingredient415(B8State415.MISSING, "BASE_OR_APPROACH_PAIR_MISSING")
    if base.state is not B8State415.MATCH:
        return B8Ingredient415(B8State415.BLOCKED, "BASE_WIDTH_CANDIDATE_NOT_MATCHED")
    target = _eligible(rows[index+1], cutoff=inputs.as_of_utc)
    if target is None:
        return B8Ingredient415(B8State415.BLOCKED, "APPROACH_TARGET_NOT_ELIGIBLE")
    prior = _eligible(rows[index], cutoff=target.market_bar_key.bar_start_utc)
    if prior is None or _source_identity(prior) != _source_identity(target):
        return B8Ingredient415(B8State415.BLOCKED, "APPROACH_PRIOR_NOT_KNOWN")
    near = inspect_near_zone_arithmetic(price=target.close,
        zone_lower=base.private_resistance, zone_upper=base.private_resistance,
        atr_d1=base.private_atr, candidate_k_near=p.near.candidate_k_near)
    if near.in_candidate_band is None:
        return B8Ingredient415(B8State415.DISTANCE, "NEAR_DISTANCE_UNCALIBRATED",
                               distance_atr=near.normalized_by_atr)
    match = prior.close < target.close <= base.private_resistance and near.in_candidate_band
    state = B8State415.MATCH if match else B8State415.NONMATCH
    return B8Ingredient415(state, "SAME_RESISTANCE_CLOSED_APPROACH_ONLY",
                           distance_atr=near.normalized_by_atr)


def _validate_early417(p):
    if type(p) is not B8EarlyPlan417:
        raise ValueError("MST_417_EXPLICIT_EARLY_PLAN")
    e = p.candidate_epsilon
    if type(e) is not Decimal or not e.is_finite() or e < 0:
        raise ValueError("MST_417_EXPLICIT_EPSILON")


def _early417(inputs, p, base, near):
    rows = inputs.snapshots_for(Timeframe.M15)
    index = p.target_index + 2
    if near is None or near.state is B8State415.MISSING or index >= len(rows):
        return B8Ingredient415(B8State415.MISSING, "EXPLICIT_APPROACH_OR_EARLY_BAR_MISSING")
    if near.state is not B8State415.MATCH:
        return B8Ingredient415(B8State415.BLOCKED, "APPROACH_CANDIDATE_NOT_MATCHED")
    target = _eligible(rows[index], cutoff=inputs.as_of_utc)
    if target is None:
        return B8Ingredient415(B8State415.BLOCKED, "EARLY_TARGET_NOT_ELIGIBLE")
    prior = _eligible(rows[index-1], cutoff=target.market_bar_key.bar_start_utc)
    if prior is None or _source_identity(prior) != _source_identity(target):
        return B8Ingredient415(B8State415.BLOCKED, "APPROACH_NOT_KNOWN_BEFORE_CROSS")
    boundary = base.private_resistance + p.early.candidate_epsilon * base.private_atr
    match = prior.close <= base.private_resistance and target.close > boundary
    state = B8State415.MATCH if match else B8State415.NONMATCH
    return B8Ingredient415(state, "SAME_RESISTANCE_CLOSED_CROSS_ONLY")


def inspect_b8_preview(inputs, *, strategy, variant_id, plan):
    """Explicit prior base width and upper-pivot geometry, no RS or price-limit approval."""
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not B8BasePlan415
            or variant_id not in ("B8/BASE", "B8/INTRADAY_RVOL_TOD_PENDING")):
        raise ValueError("MST_415_EXACT_SCOPE")
    _validate415(plan)
    route = route_phase_inputs(inputs, zone_id="B8", strategy=strategy, variant_id=variant_id,
                               phase="R0", selected_frame=plan.timeframe)
    base = _r0415(inputs, plan)
    assessments = ((route, base),)
    near = None
    if plan.near is not None:
        _validate_near416(plan.near)
        rc = route_phase_inputs(inputs, zone_id="B8", strategy=strategy,
                                variant_id=variant_id, phase="R_C")
        near = _near416(inputs, plan, base)
        assessments += ((rc, near),)
    if plan.early is not None:
        _validate_early417(plan.early)
        re = route_phase_inputs(inputs, zone_id="B8", strategy=strategy,
                                variant_id=variant_id, phase="R_E")
        assessments += ((re, _early417(inputs, plan, base, near)),)
    return B8Preview415(assessments)
