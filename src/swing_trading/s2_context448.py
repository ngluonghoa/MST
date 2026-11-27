"""§448 explicit causal D1 descending trend and H1 lower-high resistance."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, _source_identity, inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .s1_failed_break441 import _atr441, _pair441, validate_pair_atr442
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs


@dataclass(frozen=True)
class S2Window448:
    start: int
    stop: int
    high_indices: tuple[int,int]
    low_indices: tuple[int,int] | None
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class S2RallyPlan449:
    target_index: int
    atr_start: int
    atr_stop: int
    candidate_k_near: Decimal | None


@dataclass(frozen=True)
class S2EarlyPlan450:
    target_index: int
    history_start: int
    high_indices: tuple[int,int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    candidate_k_rejection: Decimal | None


@dataclass(frozen=True)
class S2ConfirmPlan451:
    timeframe: Timeframe
    target_index: int
    history_start: int
    low_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    d1: S2Window448
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class S2ContextPlan448:
    anchor_index: int
    d1: S2Window448
    h1: S2Window448
    rally: S2RallyPlan449 | None = None
    early: S2EarlyPlan450 | None = None
    rf: S2ConfirmPlan451 | None = None


class S2State448(str,Enum):
    MISSING="MISSING_INPUT"
    BLOCKED="BLOCKED"
    DISTANCE="CAUSAL_DISTANCE_UNCALIBRATED"
    MATCH="GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH="GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class S2Ingredient448:
    state: S2State448
    reason: str
    private_d1_lh: Decimal | None=None
    private_d1_ll: Decimal | None=None
    private_resistance: Decimal | None=None
    private_atr: Decimal | None=None
    private_distance: Decimal | None=None
    private_micro_lh: Decimal | None=None
    private_micro_low: Decimal | None=None


@dataclass(frozen=True)
class S2Preview448:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _indices448(pair,count):
    if type(pair) is not tuple or len(pair)!=2:
        raise ValueError("MST_448_EXACT_PAIR")
    if any(type(i) is not int or not 0<=i<count for i in pair):
        raise ValueError("MST_448_EXACT_PIVOT_INDICES")


def _validate_window448(p,*,lows):
    if type(p) is not S2Window448:
        raise ValueError("MST_448_EXACT_WINDOW")
    if any(type(i) is not int for i in (p.start,p.stop,p.left_count,p.right_count)):
        raise ValueError("MST_448_EXACT_INTEGERS")
    if not 0<=p.start<p.stop<=512 or not 1<=p.left_count<=40 or not 1<=p.right_count<=40:
        raise ValueError("MST_448_BOUNDED_WINDOW")
    if type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_448_EXPLICIT_TIE_POLICY")
    _indices448(p.high_indices,p.stop-p.start)
    if lows:
        _indices448(p.low_indices,p.stop-p.start)
    elif p.low_indices is not None:
        raise ValueError("MST_448_H1_HIGH_PAIR_ONLY")


def _history448(rows,p,anchor):
    if len(rows)<p.stop:
        return None,S2State448.MISSING
    cutoff=anchor.market_bar_key.bar_start_utc
    history=rows[p.start:p.stop]
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _cross_tf_identity(bars[0])!=_cross_tf_identity(anchor):
        return None,S2State448.BLOCKED
    if any((s.selected is None and s.market_bar_key.bar_start_utc<cutoff)
           or (s.selected is not None and s.selected.bar_end_utc<=cutoff) for s in rows[p.stop:]):
        return None,S2State448.BLOCKED
    return history,S2State448.MATCH


def _pair448(history,p,indices,side,cutoff):
    first,second=indices
    if second<=first+p.right_count:
        return None,S2State448.NONMATCH
    values=tuple(inspect_causal_pivot(history,candidate_index=i,side=side,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=cutoff) for i in indices)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in values):
        return None,S2State448.BLOCKED
    if values[0].witness_known_at_utc>history[second].market_bar_key.bar_start_utc:
        return None,S2State448.BLOCKED
    if any(x.geometric_extremum is not True for x in values):
        return None,S2State448.NONMATCH
    if values[1].pivot_price>=values[0].pivot_price:
        return None,S2State448.NONMATCH
    return values[1].pivot_price,S2State448.MATCH


def _trend448(history,p,cutoff):
    h1,h2=p.high_indices
    l1,l2=p.low_indices
    if not (h1<l1<h2<l2 or l1<h1<l2<h2):
        return S2Ingredient448(S2State448.NONMATCH,"D1_PIVOTS_NOT_ALTERNATING")
    lh,state=_pair448(history,p,p.high_indices,StructureSide.HIGH,cutoff)
    if state is not S2State448.MATCH:
        return S2Ingredient448(state,"D1_LH_PAIR_UNRESOLVED_OR_NONMATCH")
    ll,state=_pair448(history,p,p.low_indices,StructureSide.LOW,cutoff)
    if state is not S2State448.MATCH:
        return S2Ingredient448(state,"D1_LL_PAIR_UNRESOLVED_OR_NONMATCH")
    if any(s.selected.close>lh for s in history[h2+1:]):
        return S2Ingredient448(S2State448.NONMATCH,"D1_CLOSED_ABOVE_CRITICAL_LH")
    return S2Ingredient448(S2State448.MATCH,"D1_LH_LL_CANDIDATE_ONLY",lh,ll)


def _r0448(inputs,plan):
    anchors=inputs.snapshots_for(Timeframe.M15)
    if plan.anchor_index>=len(anchors):
        return S2Ingredient448(S2State448.MISSING,"EXACT_M15_ANCHOR_MISSING")
    anchor=_eligible(anchors[plan.anchor_index],cutoff=inputs.as_of_utc)
    if anchor is None:
        return S2Ingredient448(S2State448.BLOCKED,"M15_ANCHOR_NOT_ELIGIBLE")
    cutoff=anchor.market_bar_key.bar_start_utc
    daily,state=_history448(inputs.snapshots_for(Timeframe.D1),plan.d1,anchor)
    if daily is None:
        return S2Ingredient448(state,"D1_CONTEXT_UNRESOLVED")
    trend=_trend448(daily,plan.d1,cutoff)
    if trend.state is not S2State448.MATCH:
        return trend
    hourly,state=_history448(inputs.snapshots_for(Timeframe.H1),plan.h1,anchor)
    if hourly is None:
        return S2Ingredient448(state,"H1_RESISTANCE_CONTEXT_UNRESOLVED")
    resistance,state=_pair448(hourly,plan.h1,plan.h1.high_indices,StructureSide.HIGH,cutoff)
    if state is not S2State448.MATCH:
        return S2Ingredient448(state,"H1_LH_PAIR_UNRESOLVED_OR_NONMATCH")
    if anchor.close>=trend.private_d1_lh or resistance>trend.private_d1_lh:
        return S2Ingredient448(S2State448.NONMATCH,"RALLY_NOT_BELOW_D1_CRITICAL_LH")
    return S2Ingredient448(S2State448.MATCH,"D1_BEARISH_H1_RESISTANCE_CANDIDATE_ONLY",
                           trend.private_d1_lh,trend.private_d1_ll,resistance)


def _validate_rally449(p,anchor_index):
    if type(p) is not S2RallyPlan449:
        raise ValueError("MST_449_EXACT_RALLY_PLAN")
    if any(type(i) is not int for i in (p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_449_EXACT_INDICES")
    if not anchor_index<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512:
        raise ValueError("MST_449_BOUNDED_RALLY")
    if p.atr_stop-p.atr_start<15:
        raise ValueError("MST_449_ATR_WARMUP")
    k=p.candidate_k_near
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_449_EXPLICIT_NEAR_THRESHOLD")


def _rally_geometry449(base,anchor,target,atr,p):
    resistance=base.private_resistance
    distance=resistance-target.close
    if target.close<=anchor.close or distance<0:
        state=S2State448.NONMATCH
    elif p.candidate_k_near is None:
        state=S2State448.DISTANCE
    else:
        state=S2State448.MATCH if distance<=p.candidate_k_near*atr else S2State448.NONMATCH
    return S2Ingredient448(state,"SAME_H1_RESISTANCE_RALLY_CANDIDATE_ONLY",
                           base.private_d1_lh,base.private_d1_ll,resistance,atr,distance)


def _rally449(inputs,plan,base):
    p=plan.rally
    _validate_rally449(p,plan.anchor_index)
    if base.state is not S2State448.MATCH:
        return S2Ingredient448(S2State448.BLOCKED,"R0_BEARISH_CONTEXT_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S2Ingredient448(S2State448.MISSING,"EXACT_RALLY_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S2Ingredient448(S2State448.BLOCKED,"RALLY_TARGET_NOT_ELIGIBLE")
    prior,_=_sequence(rows[plan.anchor_index:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return S2Ingredient448(S2State448.BLOCKED,"RALLY_HISTORY_NOT_CAUSAL")
    if any(x.close>base.private_resistance for x in prior):
        return S2Ingredient448(S2State448.NONMATCH,"RESISTANCE_ALREADY_BROKEN")
    for frame,window in ((Timeframe.D1,plan.d1),(Timeframe.H1,plan.h1)):
        history,state=_history448(inputs.snapshots_for(frame),window,target)
        if history is None:
            return S2Ingredient448(state,"BEARISH_CONTEXT_NO_LONGER_CURRENT")
    atr=_atr441(inputs,p,target)
    if atr is None or atr<=0:
        return S2Ingredient448(S2State448.BLOCKED,"CAUSAL_D1_ATR_UNRESOLVED")
    return _rally_geometry449(base,prior[0],target,atr,p)


def _validate_early450(p):
    if type(p) is not S2EarlyPlan450:
        raise ValueError("MST_450_EXACT_EARLY_PLAN")
    if any(type(i) is not int for i in (p.target_index,p.history_start,p.left_count,p.right_count)):
        raise ValueError("MST_450_EXACT_INDICES")
    if not 0<=p.history_start<p.target_index<512:
        raise ValueError("MST_450_BOUNDED_HISTORY")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_450_EXPLICIT_PIVOT_POLICY")
    _indices448(p.high_indices,p.target_index-p.history_start)
    k=p.candidate_k_rejection
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_450_EXPLICIT_REJECTION_THRESHOLD")


def _rejection450(rc,target,lh,atr,p):
    resistance=rc.private_resistance
    distance=abs(target.high-resistance)
    if not (target.high>=lh and target.close<min(lh,resistance) and target.close<target.open):
        state=S2State448.NONMATCH
    elif p.candidate_k_rejection is None:
        state=S2State448.DISTANCE
    else:
        state=S2State448.MATCH if distance<=p.candidate_k_rejection*atr else S2State448.NONMATCH
    return S2Ingredient448(state,"M15_MICRO_LH_AND_CLOSED_REJECTION_CANDIDATE_ONLY",
                           rc.private_d1_lh,rc.private_d1_ll,resistance,atr,distance,lh)


def _early450(inputs,plan,rc):
    p=plan.early
    _validate_early450(p)
    if rc is None or rc.state is not S2State448.MATCH:
        return S2Ingredient448(S2State448.BLOCKED,"R_C_RALLY_NOT_MATCHED")
    if p.history_start<plan.rally.target_index:
        raise ValueError("MST_450_HISTORY_PRECEDES_RALLY")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return S2Ingredient448(S2State448.MISSING,"EXACT_REJECTION_TARGET_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S2Ingredient448(S2State448.BLOCKED,"REJECTION_TARGET_NOT_ELIGIBLE")
    cutoff=target.market_bar_key.bar_start_utc
    prior,_=_sequence(rows[plan.rally.target_index:p.target_index],cutoff=cutoff)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return S2Ingredient448(S2State448.BLOCKED,"REJECTION_HISTORY_NOT_CAUSAL")
    if any(x.close>rc.private_resistance for x in prior):
        return S2Ingredient448(S2State448.NONMATCH,"RESISTANCE_ALREADY_BROKEN")
    history=rows[p.history_start:p.target_index]
    lh,state=_pair448(history,p,p.high_indices,StructureSide.HIGH,cutoff)
    if state is not S2State448.MATCH:
        return S2Ingredient448(state,"MICRO_LH_PAIR_UNRESOLVED_OR_NONMATCH")
    atr=_atr441(inputs,plan.rally,target)
    if atr is None or atr<=0:
        return S2Ingredient448(S2State448.BLOCKED,"CAUSAL_REJECTION_ATR_UNRESOLVED")
    return _rejection450(rc,target,lh,atr,p)


def _validate_rf451(p,plan):
    if type(p) is not S2ConfirmPlan451:
        raise ValueError("MST_451_EXPLICIT_CONFIRM_PLAN")
    validate_pair_atr442(p)
    _validate_window448(p.d1,lows=True)
    if type(p.history_start) is not int or not 0<=p.history_start<p.target_index-1:
        raise ValueError("MST_451_EXACT_HISTORY")
    if type(p.low_index) is not int or not 0<=p.low_index<p.target_index-1-p.history_start:
        raise ValueError("MST_451_EXACT_LOW_INDEX")
    if any(type(i) is not int or not 1<=i<=40 for i in (p.left_count,p.right_count)):
        raise ValueError("MST_451_BOUNDED_PIVOT_COUNTS")
    if type(p.tie_policy) is not TiePolicy or p.d1.stop<plan.d1.stop:
        raise ValueError("MST_451_EXPLICIT_POLICY_AND_NONREGRESSING_D1")


def _trend451(inputs,plan,p,early,target):
    daily=inputs.snapshots_for(Timeframe.D1)
    history,state=_history448(daily,p.d1,target)
    if history is None:
        return S2Ingredient448(state,"RF_D1_CONTEXT_UNRESOLVED")
    cutoff=target.market_bar_key.bar_start_utc
    updated,_=_sequence(daily[plan.d1.stop:p.d1.stop],cutoff=cutoff)
    if updated is None:
        return S2Ingredient448(S2State448.BLOCKED,"RF_D1_UPDATE_NOT_CAUSAL")
    trend=_trend448(history,p.d1,cutoff)
    if trend.state is not S2State448.MATCH:
        return trend
    if (trend.private_d1_lh>early.private_d1_lh or trend.private_d1_ll>early.private_d1_ll
            or target.close>=early.private_d1_lh
            or any(x.close>early.private_d1_lh for x in updated)):
        return S2Ingredient448(S2State448.NONMATCH,"RF_D1_BEARISH_CONTEXT_NOT_PRESERVED")
    return trend


def _micro451(rows,p,prior,early_bar):
    cutoff=prior.market_bar_key.bar_start_utc
    history=rows[p.history_start:p.target_index-1]
    bars,_=_sequence(history,cutoff=cutoff)
    if (not bars or bars[0].market_bar_key.bar_start_utc<early_bar.verified_at_utc
            or _source_identity(bars[0])!=_source_identity(prior)):
        return None,S2State448.BLOCKED
    pivot=inspect_causal_pivot(history,candidate_index=p.low_index,side=StructureSide.LOW,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,as_of_utc=cutoff)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return None,S2State448.BLOCKED
    if pivot.geometric_extremum is not True:
        return None,S2State448.NONMATCH
    return pivot.pivot_price,S2State448.MATCH


def _cross451(prior,target,low,atr,p,trend,early):
    if p.candidate_epsilon is None:
        state=S2State448.DISTANCE
    else:
        boundary=low-p.candidate_epsilon*atr
        match=boundary>=0 and prior.close>=low and target.close<boundary
        state=S2State448.MATCH if match else S2State448.NONMATCH
    return S2Ingredient448(state,"MICRO_LOW_CLOSED_CROSS_CANDIDATE_ONLY",
        trend.private_d1_lh,trend.private_d1_ll,early.private_resistance,atr,
        private_micro_lh=early.private_micro_lh,private_micro_low=low)


def _confirm451(inputs,plan,early):
    p=plan.rf
    _validate_rf451(p,plan)
    if early is None or early.state is not S2State448.MATCH:
        return S2Ingredient448(S2State448.BLOCKED,"R_E_NOT_MATCHED")
    rows=inputs.snapshots_for(p.timeframe)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S2Ingredient448(S2State448.MISSING,"EXACT_RF_TARGET_OR_ATR_MISSING")
    early_bar=inputs.snapshots_for(Timeframe.M15)[plan.early.target_index].selected
    prior,target=_pair441(inputs,p,early_bar)
    if prior is None:
        return S2Ingredient448(S2State448.BLOCKED,"RF_PAIR_NOT_CAUSAL_AFTER_R_E")
    low,state=_micro451(rows,p,prior,early_bar)
    if state is not S2State448.MATCH:
        return S2Ingredient448(state,"RF_MICRO_LOW_UNRESOLVED_OR_NONMATCH")
    if any(x.selected.close>early.private_resistance for x in rows[p.history_start:p.target_index]):
        return S2Ingredient448(S2State448.NONMATCH,"RF_RESISTANCE_ALREADY_BROKEN")
    trend=_trend451(inputs,plan,p,early,target)
    if trend.state is not S2State448.MATCH:
        return trend
    atr=_atr441(inputs,p,target)
    if atr is None or atr<=0:
        return S2Ingredient448(S2State448.BLOCKED,"RF_CAUSAL_D1_ATR_UNRESOLVED")
    return _cross451(prior,target,low,atr,p,trend,early)


def inspect_s2_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not S2ContextPlan448 or variant_id!="S2/BASE"):
        raise ValueError("MST_448_EXACT_SCOPE")
    if type(plan.anchor_index) is not int or not 0<=plan.anchor_index<512:
        raise ValueError("MST_448_EXACT_ANCHOR")
    _validate_window448(plan.d1,lows=True)
    _validate_window448(plan.h1,lows=False)
    route=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant_id,phase="R0")
    base=_r0448(inputs,plan)
    assessments=((route,base),)
    rc=None
    if plan.rally is not None:
        rc_route=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant_id,phase="R_C")
        rc=_rally449(inputs,plan,base)
        assessments+=((rc_route,rc),)
    early=None
    if plan.early is not None:
        re=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant_id,phase="R_E")
        early=_early450(inputs,plan,rc)
        assessments+=((re,early),)
    if plan.rf is not None:
        proof=_confirm451(inputs,plan,early)
        rf=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant_id,
                              phase="R_F",selected_frame=plan.rf.timeframe)
        assessments+=((rf,proof),)
    return S2Preview448(assessments)
