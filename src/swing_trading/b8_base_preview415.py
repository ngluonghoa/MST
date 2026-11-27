"""§415 B8 explicit prior base and resistance candidate; not an approved base."""
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from .causal_indicators import CausalIndicatorResult, IndicatorState, calculate_wilder_atr14
from .b6_rf_volume405 import (
    B6RFVolumePlan389, B6H1VolumePlan394, _check_volume389, _check_h1_volume394,
    _volume389, _h1_volume394,
)
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, inspect_causal_pivot, _source_identity,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .zone_manifest_v03 import inspect_near_zone_arithmetic
from .b8_portfolio429 import B8PortfolioPlan429, B8PortfolioResult429
from .b8_execution_preview430 import inspect_b8_execution430
from .b8_liquidity428 import B8LiquidityPlan428, B8LiquidityResult428
from .b8_settlement427 import B8SettlementPlan427, B8SettlementResult427
from .b8_price_band426 import B8PriceBand426, B8PriceBandResult426
from .b8_risk_geometry424 import B8MeasuredBaseRisk424, B8RiskResult424
from .relative_strength421 import (RSPlan421, RSResult421, inspect_rs421, validate_rs421,
                                   inspect_rs_confirmation422)
from .rvol_tod_contract import TODCumulativeObservation, TODRawPrefix
from .b8_tod_preview432 import validate_tod432, inspect_early_tod432


@dataclass(frozen=True)
class B8NearPlan416:
    candidate_k_near: Decimal | None


@dataclass(frozen=True)
class B8TODPlan420:
    target: TODCumulativeObservation
    prior_sessions: tuple[TODCumulativeObservation, ...]
    target_prefix: TODRawPrefix
    prior_prefixes: tuple[TODRawPrefix, ...]


@dataclass(frozen=True)
class B8EarlyPlan417:
    candidate_epsilon: Decimal
    tod: B8TODPlan420 | None = None
    candidate_min_rvol_tod: Decimal | None = None


@dataclass(frozen=True)
class B8ExtensionPlan423:
    candidate_max_extension_atr: Decimal | None


@dataclass(frozen=True)
class B8ConfirmPlan418:
    timeframe: Timeframe
    breakout_index: int
    candidate_epsilon: Decimal
    volume: B6RFVolumePlan389 | B6H1VolumePlan394 | None = None
    rs: RSPlan421 | None = None
    extension: B8ExtensionPlan423 | None = None
    risk: B8MeasuredBaseRisk424 | None = None
    band: B8PriceBand426 | None = None
    settlement: B8SettlementPlan427 | None = None
    liquidity: B8LiquidityPlan428 | None = None
    portfolio: B8PortfolioPlan429 | None = None
    candidate_min_rvol: Decimal | None = None


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
    rf: B8ConfirmPlan418 | None = None
    rs: RSPlan421 | None = None


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
    volume_state: str = "NOT_REQUESTED"
    rvol: CausalIndicatorResult | None = None
    rs: RSResult421 | None = None
    extension_atr: Decimal | None = None
    extension_candidate_match: bool | None = None
    risk: B8RiskResult424 | None = None
    band: B8PriceBandResult426 | None = None
    settlement: B8SettlementResult427 | None = None
    liquidity: B8LiquidityResult428 | None = None
    portfolio: B8PortfolioResult429 | None = None
    rvol_candidate_match: bool | None = None
    tod_candidate_match: bool | None = None


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


def _validate_rvol431(k):
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<=0):
        raise ValueError("MST_431_EXPLICIT_POSITIVE_RVOL_THRESHOLD")


def _validate_rf418(p):
    if type(p) is not B8ConfirmPlan418 or type(p.timeframe) is not Timeframe:
        raise ValueError("MST_418_EXPLICIT_RF_PLAN")
    if p.timeframe not in (Timeframe.H1, Timeframe.D1):
        raise ValueError("MST_418_EXPLICIT_RF_FRAME")
    if type(p.breakout_index) is not int or not 1 <= p.breakout_index < 512:
        raise ValueError("MST_418_EXPLICIT_RF_INDEX")
    e = p.candidate_epsilon
    if type(e) is not Decimal or not e.is_finite() or e < 0:
        raise ValueError("MST_418_EXPLICIT_EPSILON")
    _validate_rvol431(p.candidate_min_rvol)
    if p.volume is not None:
        if p.timeframe is Timeframe.D1:
            _check_volume389(p.volume)
        else:
            _check_h1_volume394(p.volume)


def _rf_pair418(inputs, p, rows, m15):
    index = p.rf.breakout_index
    target = _eligible(rows[index], cutoff=inputs.as_of_utc)
    if target is None:
        return None
    cutoff = target.market_bar_key.bar_start_utc
    prior = _eligible(rows[index-1], cutoff=cutoff)
    early = _eligible(m15[p.target_index+2], cutoff=cutoff)
    if prior is None or early is None:
        return None
    if (_source_identity(prior) != _source_identity(target)
            or _cross_tf_identity(early) != _cross_tf_identity(target)):
        return None
    if prior.market_bar_key == target.market_bar_key:
        return None
    if p.early.tod is not None and p.early.tod.target.cumulative_verified_utc > cutoff:
        return None
    return prior, target


def _rf418(inputs, p, base, early):
    rows = inputs.snapshots_for(p.rf.timeframe)
    m15 = inputs.snapshots_for(Timeframe.M15)
    if early is None or early.state is B8State415.MISSING or p.rf.breakout_index >= len(rows):
        return B8Ingredient415(B8State415.MISSING, "EXPLICIT_EARLY_OR_RF_PAIR_MISSING")
    if early.state is not B8State415.MATCH:
        return B8Ingredient415(B8State415.BLOCKED, "EARLY_CANDIDATE_NOT_MATCHED")
    pair = _rf_pair418(inputs, p, rows, m15)
    if pair is None:
        return B8Ingredient415(B8State415.BLOCKED, "RF_PAIR_OR_EARLY_NOT_CAUSALLY_AVAILABLE")
    prior, target = pair
    boundary = base.private_resistance + p.rf.candidate_epsilon * base.private_atr
    match = prior.close <= base.private_resistance and target.close > boundary
    state = B8State415.MATCH if match else B8State415.NONMATCH
    return B8Ingredient415(state, "LATER_HIGHER_FRAME_SAME_RESISTANCE_CROSS_ONLY")


def _rf_volume419(inputs, p, geometry):
    if geometry.state is not B8State415.MATCH:
        return geometry
    if p.rf.volume is None:
        if p.rf.candidate_min_rvol is not None:
            return replace(geometry,state=B8State415.MISSING,reason="RF_EXPLICIT_RVOL_WITNESS_REQUIRED")
        return geometry
    bound = (_volume389(inputs, p.rf, geometry) if p.rf.timeframe is Timeframe.D1
             else _h1_volume394(inputs, p.rf, geometry))
    if bound.volume_state == "EXACT_TARGET_OR_PRIOR20_MISSING":
        return replace(bound, state=B8State415.MISSING, reason="RF_VOLUME_HISTORY_MISSING")
    if bound.volume_state != "RVOL_COMPUTED_UNCALIBRATED":
        return replace(bound, state=B8State415.BLOCKED, reason="RF_VOLUME_WITNESS_BLOCKED")
    return _rf_rvol_threshold431(inputs,p,bound)


def _rf_rvol_threshold431(inputs,p,bound):
    k=p.rf.candidate_min_rvol
    if k is None:
        return replace(bound,reason="RF_CROSS_AND_RAW_RVOL_ARITHMETIC_ONLY")
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    if p.rf.volume.witnesses[-1].verified_at_utc>target.verified_at_utc:
        return replace(bound,state=B8State415.BLOCKED,reason="RF_VOLUME_WITNESS_AFTER_TARGET_VERIFICATION")
    match=bound.rvol.value>=k
    state=B8State415.MATCH if match else B8State415.NONMATCH
    return replace(bound,state=state,reason="RF_EXPLICIT_RAW_RVOL_THRESHOLD_CANDIDATE_ONLY",
                   rvol_candidate_match=match)


def _r0_rs421(inputs, p, base):
    if p.rs is None:
        return base
    validate_rs421(p.rs)
    if base.state is not B8State415.MATCH:
        return base
    target = inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    result = inspect_rs421(inputs.snapshots_for(Timeframe.D1), p.rs,
                           cutoff=target.market_bar_key.bar_start_utc)
    if result.state == "MISSING_INPUT":
        return replace(base,state=B8State415.MISSING,reason="RS_HISTORY_MISSING",rs=result)
    if result.state != "COMPUTED_UNCALIBRATED":
        return replace(base,state=B8State415.BLOCKED,reason="RS_WINDOW_BLOCKED",rs=result)
    if result.candidate_match is False:
        return replace(base,state=B8State415.NONMATCH,reason="RS_SLOPE_CANDIDATE_NONMATCH",rs=result)
    return replace(base,reason="BASE_AND_LOG_RS_CANDIDATE_ONLY",rs=result)


def _rf_rs422(inputs, p, base, geometry):
    if p.rf.rs is None:
        return geometry
    validate_rs421(p.rf.rs)
    if geometry.state is not B8State415.MATCH:
        return geometry
    if base.rs is None or base.rs.candidate_match is not True:
        return replace(geometry,state=B8State415.BLOCKED,reason="R0_RS_CANDIDATE_NOT_MATCHED")
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    if p.rf.timeframe is Timeframe.D1 and p.rf.rs.stock_stop!=p.rf.breakout_index+1:
        return replace(geometry,state=B8State415.BLOCKED,reason="RF_RS_NOT_BOUND_TO_D1_TARGET")
    cutoff=(target.verified_at_utc if p.rf.timeframe is Timeframe.D1
            else target.market_bar_key.bar_start_utc)
    result=inspect_rs_confirmation422(inputs.snapshots_for(Timeframe.D1),p.rs,p.rf.rs,
                                      cutoff=cutoff)
    return _rf_rs_result422(geometry,result)


def _rf_rs_result422(geometry, result):
    if result.state=="MISSING_INPUT":
        return replace(geometry,state=B8State415.MISSING,reason="RF_RS_HISTORY_MISSING",rs=result)
    if result.state!="COMPUTED_UNCALIBRATED":
        return replace(geometry,state=B8State415.BLOCKED,reason="RF_RS_WINDOW_BLOCKED",rs=result)
    if result.candidate_match is False:
        return replace(geometry,state=B8State415.NONMATCH,reason="RF_RS_SLOPE_NONMATCH",rs=result)
    return replace(geometry,reason="RF_CROSS_AND_LOG_RS_CANDIDATE_ONLY",rs=result)


def _validate_extension423(p):
    if p is None:
        return
    if type(p) is not B8ExtensionPlan423:
        raise ValueError("MST_423_EXPLICIT_EXTENSION_PLAN")
    k=p.candidate_max_extension_atr
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k < 0):
        raise ValueError("MST_423_EXPLICIT_MAX_EXTENSION")


def _rf_extension423(inputs, p, base, geometry):
    plan=p.rf.extension
    _validate_extension423(plan)
    if plan is None or geometry.state is not B8State415.MATCH:
        return geometry
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    result=inspect_near_zone_arithmetic(price=target.close,
        zone_lower=base.private_resistance,zone_upper=base.private_resistance,
        atr_d1=base.private_atr,candidate_k_near=plan.candidate_max_extension_atr)
    state=geometry.state
    if result.in_candidate_band is None:
        state=B8State415.DISTANCE
    elif result.in_candidate_band is False:
        state=B8State415.NONMATCH
    return replace(geometry,state=state,reason="RF_SAME_PIVOT_EXTENSION_CANDIDATE_ONLY",
                   extension_atr=result.normalized_by_atr,
                   extension_candidate_match=result.in_candidate_band)


def inspect_b8_preview(inputs, *, strategy, variant_id, plan):
    """Explicit prior base width and upper-pivot geometry, no RS or price-limit approval."""
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not B8BasePlan415
            or variant_id not in ("B8/BASE", "B8/INTRADAY_RVOL_TOD_PENDING")):
        raise ValueError("MST_415_EXACT_SCOPE")
    _validate415(plan)
    route = route_phase_inputs(inputs, zone_id="B8", strategy=strategy, variant_id=variant_id,
                               phase="R0", selected_frame=plan.timeframe)
    base = _r0_rs421(inputs, plan, _r0415(inputs, plan))
    assessments = ((route, base),)
    near = early = None
    if plan.near is not None:
        _validate_near416(plan.near)
        rc = route_phase_inputs(inputs, zone_id="B8", strategy=strategy,
                                variant_id=variant_id, phase="R_C")
        near = _near416(inputs, plan, base)
        assessments += ((rc, near),)
    if plan.early is not None:
        _validate_early417(plan.early)
        validate_tod432(plan.early.tod, variant_id, plan.early.candidate_min_rvol_tod,
                        plan_type=B8TODPlan420)
        re = route_phase_inputs(inputs, zone_id="B8", strategy=strategy,
                                variant_id=variant_id, phase="R_E")
        early = inspect_early_tod432(inputs, plan, _early417(inputs, plan, base, near),
                                     states=B8State415)
        assessments += ((re, early),)
    if plan.rf is not None:
        _validate_rf418(plan.rf)
        rf = route_phase_inputs(inputs, zone_id="B8", strategy=strategy,
            variant_id=variant_id, phase="R_F", selected_frame=plan.rf.timeframe)
        geometry = _rf418(inputs, plan, base, early)
        volume = _rf_volume419(inputs, plan, geometry)
        rs = _rf_rs422(inputs, plan, base, volume)
        extension = _rf_extension423(inputs, plan, base, rs)
        execution = inspect_b8_execution430(inputs, plan, base, extension, strategy,
                                            states=B8State415)
        assessments += ((rf, execution),)
    return B8Preview415(assessments)
