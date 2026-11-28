"""§499 B1 dual-frame prior decline ingredient, not a complete R0."""
from dataclasses import dataclass

from .causal_structure_geometry import TiePolicy, _eligible, _sequence, _cross_tf_identity
from .causal_trend_candidate382 import _structure_state, _validate_plan
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .s1_context_preview439 import S1State439, _tail439


@dataclass(frozen=True)
class B1DeclineWindow499:
    start: int
    stop: int
    high_indices: tuple[int, int]
    low_indices: tuple[int, int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    candidate_min_span_bars: int | None


@dataclass(frozen=True)
class B1DeclinePlan499:
    anchor_index: int
    weekly: B1DeclineWindow499
    daily: B1DeclineWindow499


@dataclass(frozen=True)
class B1DeclineIngredient499:
    state: S1State439
    reason: str
    private_frame_states: tuple = ()


@dataclass(frozen=True)
class B1Preview499:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _validate499(p):
    if type(p) is not B1DeclineWindow499:
        raise ValueError("MST_499_EXACT_DECLINE_WINDOW")
    if any(type(i) is not int for i in (p.start,p.stop)) or not 0<=p.start<p.stop<=512:
        raise ValueError("MST_499_BOUNDED_WINDOW")
    _validate_plan(p.high_indices,p.low_indices,p.left_count,p.right_count,p.tie_policy)
    if any(len(pair)!=2 or any(i>=p.stop-p.start for i in pair) for pair in (p.high_indices,p.low_indices)):
        raise ValueError("MST_499_EXACT_PIVOT_PAIRS")
    k=p.candidate_min_span_bars
    if k is not None and (type(k) is not int or not 1<=k<=512):
        raise ValueError("MST_499_EXPLICIT_SPAN")


def _frame499(rows,p,anchor):
    if len(rows)<p.stop:
        return S1State439.MISSING,"EXACT_DECLINE_HISTORY_MISSING"
    cutoff=anchor.market_bar_key.bar_start_utc
    history=rows[p.start:p.stop]
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _tail439(rows,p.stop,cutoff):
        return S1State439.BLOCKED,"DECLINE_NOT_CAUSAL_OR_LATEST_SUPPLIED"
    if _cross_tf_identity(bars[0])!=_cross_tf_identity(anchor):
        return S1State439.BLOCKED,"DECLINE_SOURCE_MISMATCH"
    policy=dict(left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy)
    shape=_structure_state(history,p.high_indices,p.low_indices,policy,cutoff)
    if shape=="BLOCKED_PIVOT":
        return S1State439.BLOCKED,shape
    if shape!="LH_LL_GEOMETRY":
        return S1State439.NONMATCH,shape
    span=max(p.high_indices+p.low_indices)-min(p.high_indices+p.low_indices)+1
    k=p.candidate_min_span_bars
    return (S1State439.DISTANCE if k is None else S1State439.MATCH if span>=k else S1State439.NONMATCH),shape


def _decline499(inputs,p):
    rows=inputs.snapshots_for(Timeframe.M15)
    if len(rows)<=p.anchor_index:
        return B1DeclineIngredient499(S1State439.MISSING,"EXACT_ANCHOR_MISSING")
    anchor=_eligible(rows[p.anchor_index],cutoff=inputs.as_of_utc)
    if anchor is None:
        return B1DeclineIngredient499(S1State439.BLOCKED,"ANCHOR_NOT_ELIGIBLE")
    proof=tuple((tf,*_frame499(inputs.snapshots_for(tf),window,anchor))
                for tf,window in ((Timeframe.W1,p.weekly),(Timeframe.D1,p.daily)))
    for state in (S1State439.BLOCKED,S1State439.MISSING,S1State439.NONMATCH,S1State439.DISTANCE):
        if any(x[1] is state for x in proof):
            return B1DeclineIngredient499(state,"DUAL_DECLINE_INCOMPLETE",proof)
    return B1DeclineIngredient499(S1State439.MATCH,"DUAL_DECLINE_ONLY_BOTTOM_AND_MARKET_PENDING",proof)


def inspect_b1_decline499_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not B1DeclinePlan499 or variant_id not in
            ("B1/E_RECLAIM","B1/E_BOS_UP","B1/F_MAJOR_REVERSAL_PENDING")):
        raise ValueError("MST_499_EXACT_SCOPE")
    if type(plan.anchor_index) is not int or not 0<=plan.anchor_index<512:
        raise ValueError("MST_499_EXACT_ANCHOR")
    _validate499(plan.weekly)
    _validate499(plan.daily)
    route=route_phase_inputs(inputs,zone_id="B1",strategy=strategy,variant_id=variant_id,phase="R0")
    return B1Preview499(((route,_decline499(inputs,plan)),))
