"""§454 S3 causal D1 rising structure and explicit D1/W1 resistance candidate."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, _source_identity, inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .s1_choch442 import _pivots442, _validate_pivots442
from .s1_context_preview439 import _tail439
from .s1_failed_break441 import _atr441


@dataclass(frozen=True)
class S3TrendWindow454:
    start: int
    stop: int
    high_indices: tuple[int,int]
    low_indices: tuple[int,int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class S3Resistance454:
    timeframe: Timeframe
    start: int
    stop: int
    pivot_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class S3NearPlan455:
    target_index: int
    atr_start: int
    atr_stop: int
    candidate_k_near: Decimal | None
    candidate_min_extension: Decimal | None


@dataclass(frozen=True)
class S3ContextPlan454:
    anchor_index: int
    d1: S3TrendWindow454
    resistance: S3Resistance454
    near: S3NearPlan455 | None=None


class S3State454(str,Enum):
    MISSING="MISSING_INPUT"
    BLOCKED="BLOCKED"
    DISTANCE="CAUSAL_DISTANCE_UNCALIBRATED"
    MATCH="GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH="GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class S3Ingredient454:
    state: S3State454
    reason: str
    private_d1_hh: Decimal | None=None
    private_higher_low: Decimal | None=None
    private_resistance: Decimal | None=None
    private_atr: Decimal | None=None
    private_distance: Decimal | None=None
    private_extension_atr: Decimal | None=None


@dataclass(frozen=True)
class S3Preview454:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _window454(p):
    if any(type(i) is not int for i in (p.start,p.stop,p.left_count,p.right_count)):
        raise ValueError("MST_454_EXACT_WINDOW")
    if not 0<=p.start<p.stop<=512 or not 1<=p.left_count<=40 or not 1<=p.right_count<=40:
        raise ValueError("MST_454_BOUNDED_WINDOW")
    if type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_454_EXPLICIT_TIE_POLICY")


def _validate454(p):
    if type(p.anchor_index) is not int or not 0<=p.anchor_index<512:
        raise ValueError("MST_454_EXACT_ANCHOR")
    if type(p.d1) is not S3TrendWindow454 or type(p.resistance) is not S3Resistance454:
        raise ValueError("MST_454_EXPLICIT_TREND_AND_TARGET")
    _window454(p.d1)
    _validate_pivots442(p.d1,p.d1.stop-p.d1.start)
    r=p.resistance
    _window454(r)
    if type(r.timeframe) is not Timeframe or r.timeframe not in (Timeframe.D1,Timeframe.W1):
        raise ValueError("MST_454_EXPLICIT_RESISTANCE_FRAME")
    if type(r.pivot_index) is not int or not 0<=r.pivot_index<r.stop-r.start:
        raise ValueError("MST_454_EXACT_RESISTANCE_PIVOT")


    if p.near is not None:
        _validate_near455(p.near,p.anchor_index)


def _validate_near455(p,anchor):
    if type(p) is not S3NearPlan455:
        raise ValueError("MST_455_EXACT_NEAR_PLAN")
    if any(type(i) is not int for i in (p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_455_EXACT_INDICES")
    if not anchor<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512:
        raise ValueError("MST_455_BOUNDED_WINDOW")
    if p.atr_stop-p.atr_start<15:
        raise ValueError("MST_455_ATR_WARMUP")
    for k in (p.candidate_k_near,p.candidate_min_extension):
        if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
            raise ValueError("MST_455_EXPLICIT_THRESHOLDS")


def _history454(rows,p,anchor):
    if len(rows)<p.stop:
        return None,S3State454.MISSING
    cutoff=anchor.market_bar_key.bar_start_utc
    history=rows[p.start:p.stop]
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _tail439(rows,p.stop,cutoff):
        return None,S3State454.BLOCKED
    if _cross_tf_identity(bars[0])!=_cross_tf_identity(anchor):
        return None,S3State454.BLOCKED
    return history,S3State454.MATCH


def _trend454(history,p,cutoff):
    h1,h2=p.high_indices
    l1,l2=p.low_indices
    if not (h1<l1<h2<l2 or l1<h1<l2<h2):
        return S3Ingredient454(S3State454.NONMATCH,"D1_PIVOTS_NOT_ALTERNATING")
    highs,lows=_pivots442(history,p,cutoff)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in highs+lows):
        return S3Ingredient454(S3State454.BLOCKED,"D1_PIVOT_WITNESS_UNAVAILABLE")
    if any(x.geometric_extremum is not True for x in highs+lows):
        return S3Ingredient454(S3State454.NONMATCH,"D1_PIVOT_NOT_EXTREMUM")
    if (highs[0].witness_known_at_utc>history[h2].market_bar_key.bar_start_utc
            or lows[0].witness_known_at_utc>history[l2].market_bar_key.bar_start_utc):
        return S3Ingredient454(S3State454.BLOCKED,"D1_FIRST_PIVOT_NOT_KNOWN_BEFORE_SECOND")
    hh,hl=highs[1].pivot_price,lows[1].pivot_price
    if hh<=highs[0].pivot_price or hl<=lows[0].pivot_price:
        return S3Ingredient454(S3State454.NONMATCH,"D1_HH_HL_NOT_RISING")
    if any(s.selected.close<hl for s in history[l2+1:]):
        return S3Ingredient454(S3State454.NONMATCH,"D1_CRITICAL_HL_LOST")
    return S3Ingredient454(S3State454.MATCH,"D1_RISING_STRUCTURE_CANDIDATE_ONLY",hh,hl)


def _resistance454(inputs,p,anchor,trend):
    history,state=_history454(inputs.snapshots_for(p.timeframe),p,anchor)
    if history is None:
        return S3Ingredient454(state,"EXACT_RESISTANCE_CONTEXT_UNRESOLVED")
    pivot=inspect_causal_pivot(history,candidate_index=p.pivot_index,side=StructureSide.HIGH,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=anchor.market_bar_key.bar_start_utc)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return S3Ingredient454(S3State454.BLOCKED,"RESISTANCE_PIVOT_WITNESS_UNAVAILABLE")
    if pivot.geometric_extremum is not True:
        return S3Ingredient454(S3State454.NONMATCH,"RESISTANCE_NOT_STRUCTURAL_PIVOT")
    r=pivot.pivot_price
    if anchor.close>r or anchor.close<trend.private_higher_low:
        return S3Ingredient454(S3State454.NONMATCH,"ANCHOR_OUTSIDE_RISING_TARGET_CONTEXT")
    if any(s.selected.close>r for s in history[p.pivot_index+1:]):
        return S3Ingredient454(S3State454.NONMATCH,"STRUCTURAL_TARGET_ALREADY_BROKEN")
    return S3Ingredient454(S3State454.MATCH,"D1_UPTREND_STRUCTURAL_TARGET_CANDIDATE_ONLY",
                           trend.private_d1_hh,trend.private_higher_low,r)


def _r0454(inputs,plan):
    rows=inputs.snapshots_for(Timeframe.M15)
    if plan.anchor_index>=len(rows):
        return S3Ingredient454(S3State454.MISSING,"EXACT_M15_ANCHOR_MISSING")
    anchor=_eligible(rows[plan.anchor_index],cutoff=inputs.as_of_utc)
    if anchor is None:
        return S3Ingredient454(S3State454.BLOCKED,"M15_ANCHOR_NOT_ELIGIBLE")
    history,state=_history454(inputs.snapshots_for(Timeframe.D1),plan.d1,anchor)
    if history is None:
        return S3Ingredient454(state,"D1_CONTEXT_UNRESOLVED")
    trend=_trend454(history,plan.d1,anchor.market_bar_key.bar_start_utc)
    if trend.state is not S3State454.MATCH:
        return trend
    return _resistance454(inputs,plan.resistance,anchor,trend)


def _near_geometry455(base,anchor,target,prior,atr,p):
    distance=base.private_resistance-target.close
    extension=(target.close-base.private_higher_low)/atr
    if target.close<=anchor.close or distance<0 or extension<0:
        state=S3State454.NONMATCH
    elif any(not base.private_higher_low<=b.close<=base.private_resistance for b in prior):
        state=S3State454.NONMATCH
    elif p.candidate_k_near is None or p.candidate_min_extension is None:
        state=S3State454.DISTANCE
    elif distance<=p.candidate_k_near*atr and extension>=p.candidate_min_extension:
        state=S3State454.MATCH
    else:
        state=S3State454.NONMATCH
    return S3Ingredient454(state,"NEAR_STRUCTURAL_TARGET_EXTENSION_CANDIDATE_ONLY",
        base.private_d1_hh,base.private_higher_low,base.private_resistance,atr,distance,extension)


def _near455(inputs,plan,base):
    p=plan.near
    if base.state is not S3State454.MATCH:
        return S3Ingredient454(S3State454.BLOCKED,"R0_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S3Ingredient454(S3State454.MISSING,"NEAR_TARGET_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S3Ingredient454(S3State454.BLOCKED,"NEAR_TARGET_NOT_ELIGIBLE")
    prior,_=_sequence(rows[plan.anchor_index:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return S3Ingredient454(S3State454.BLOCKED,"NEAR_PRIOR_NOT_CAUSAL")
    for frame,window in ((Timeframe.D1,plan.d1),(plan.resistance.timeframe,plan.resistance)):
        history,state=_history454(inputs.snapshots_for(frame),window,target)
        if history is None:
            return S3Ingredient454(state,"NEAR_CONTEXT_NOT_CURRENT")
    atr=_atr441(inputs,p,target)
    if atr is None or atr<=0:
        return S3Ingredient454(S3State454.BLOCKED,"NEAR_ATR_UNRESOLVED")
    return _near_geometry455(base,prior[0],target,prior,atr,p)


def inspect_s3_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not S3ContextPlan454 or variant_id not in
            ("S3/E_MICRO_CHOCH","S3/E_TP","S3/F_MICRO_BREAK","S3/F_TP")):
        raise ValueError("MST_454_EXACT_SCOPE")
    _validate454(plan)
    route=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R0")
    base=_r0454(inputs,plan)
    assessments=((route,base),)
    if plan.near is not None:
        rc=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R_C")
        assessments+=((rc,_near455(inputs,plan,base)),)
    return S3Preview454(assessments)
