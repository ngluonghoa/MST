"""§448 explicit causal D1 descending trend and H1 lower-high resistance."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
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
class S2ContextPlan448:
    anchor_index: int
    d1: S2Window448
    h1: S2Window448


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


def inspect_s2_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not S2ContextPlan448 or variant_id!="S2/BASE"):
        raise ValueError("MST_448_EXACT_SCOPE")
    if type(plan.anchor_index) is not int or not 0<=plan.anchor_index<512:
        raise ValueError("MST_448_EXACT_ANCHOR")
    _validate_window448(plan.d1,lows=True)
    _validate_window448(plan.h1,lows=False)
    route=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant_id,phase="R0")
    return S2Preview448(((route,_r0448(inputs,plan)),))
