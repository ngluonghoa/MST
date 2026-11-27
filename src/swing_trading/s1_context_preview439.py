"""§439 S1 explicit prior rising structure and resistance candidate."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    _sequence, inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .causal_indicators import CausalIndicatorResult
from .s1_distribution440 import S1DistributionPlan440, inspect_distribution440
from .s1_failed_break441 import S1FailedBreakPlan441, inspect_failed441
from .s1_choch442 import S1ChochPlan442, inspect_choch442
from .s1_confirm443 import S1ConfirmPlan443, inspect_rf443
from .s1_holdings445 import S1HoldingsResult445
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs


@dataclass(frozen=True)
class S1ContextPlan439:
    timeframe: Timeframe
    target_index: int
    start: int
    stop: int
    high_indices: tuple[int, int]
    low_indices: tuple[int, int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    candidate_min_span_bars: int | None
    distribution: S1DistributionPlan440 | None = None
    failed: S1FailedBreakPlan441 | None = None
    choch: S1ChochPlan442 | None = None
    rf: S1ConfirmPlan443 | None = None


class S1State439(str, Enum):
    MISSING = "MISSING_INPUT"
    BLOCKED = "BLOCKED"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"


@dataclass(frozen=True)
class S1Ingredient439:
    state: S1State439
    reason: str
    private_resistance: Decimal | None = None
    private_higher_low: Decimal | None = None
    observed_span_bars: int | None = None
    rvol: CausalIndicatorResult | None = None
    close_location: Decimal | None = None
    private_atr: Decimal | None = None
    holdings: S1HoldingsResult445 | None = None


@dataclass(frozen=True)
class S1Preview439:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _indices439(pair, count):
    if type(pair) is not tuple or len(pair)!=2:
        raise ValueError("MST_439_EXACT_PAIR")
    if any(type(i) is not int or not 0<=i<count for i in pair):
        raise ValueError("MST_439_EXACT_PIVOT_INDICES")


def _validate439(p):
    if type(p.timeframe) is not Timeframe or p.timeframe not in (Timeframe.W1,Timeframe.D1):
        raise ValueError("MST_439_EXPLICIT_CONTEXT_FRAME")
    if any(type(i) is not int for i in (p.start,p.stop,p.target_index)):
        raise ValueError("MST_439_EXACT_WINDOW")
    if not 0<=p.start<p.stop<=512 or not 0<=p.target_index<512:
        raise ValueError("MST_439_BOUNDED_WINDOW")
    for pair in (p.high_indices,p.low_indices):
        _indices439(pair,p.stop-p.start)
    _policy439(p)


def _policy439(p):
    if (type(p.left_count) is not int or not 1<=p.left_count<=40
            or type(p.right_count) is not int or not 1<=p.right_count<=40
            or type(p.tie_policy) is not TiePolicy):
        raise ValueError("MST_439_EXPLICIT_PIVOT_POLICY")
    k=p.candidate_min_span_bars
    if k is not None and (type(k) is not int or not 1<=k<=512):
        raise ValueError("MST_439_EXPLICIT_OBSERVED_SPAN")


def _tail439(rows,stop,cutoff):
    return any((x.selected is None and x.market_bar_key.bar_start_utc<cutoff)
               or (x.selected is not None and x.selected.bar_end_utc<=cutoff)
               for x in rows[stop:])


def _pairs439(history,p,cutoff):
    def pair(indices,side):
        return tuple(inspect_causal_pivot(history,candidate_index=i,side=side,
                    left_count=p.left_count,right_count=p.right_count,
                    tie_policy=p.tie_policy,as_of_utc=cutoff) for i in indices)
    return pair(p.high_indices,StructureSide.HIGH),pair(p.low_indices,StructureSide.LOW)


def _geometry439(history,p,cutoff):
    h1,h2=p.high_indices
    l1,l2=p.low_indices
    if not (h1<l1<h2<l2 or l1<h1<l2<h2):
        return S1Ingredient439(S1State439.NONMATCH,"PIVOTS_NOT_ALTERNATING")
    highs,lows=_pairs439(history,p,cutoff)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in highs+lows):
        return S1Ingredient439(S1State439.BLOCKED,"PIVOT_WITNESS_UNAVAILABLE")
    if any(x.geometric_extremum is not True for x in highs+lows):
        return S1Ingredient439(S1State439.NONMATCH,"PIVOT_NOT_EXTREMUM")
    if not (highs[1].pivot_price>highs[0].pivot_price and lows[1].pivot_price>lows[0].pivot_price):
        return S1Ingredient439(S1State439.NONMATCH,"HH_HL_NOT_RISING")
    span=max(h2,l2)-min(h1,l1)+1
    k=p.candidate_min_span_bars
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if span>=k else S1State439.NONMATCH
    return S1Ingredient439(state,"PRIOR_HH_HL_AND_RESISTANCE_CANDIDATE_ONLY",
                           highs[1].pivot_price,lows[1].pivot_price,span)


def _r0439(inputs,p):
    rows=inputs.snapshots_for(p.timeframe)
    targets=inputs.snapshots_for(Timeframe.M15)
    if len(rows)<p.stop or len(targets)<=p.target_index:
        return S1Ingredient439(S1State439.MISSING,"EXACT_CONTEXT_OR_ANCHOR_MISSING")
    target=_eligible(targets[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S1Ingredient439(S1State439.BLOCKED,"ANCHOR_NOT_ELIGIBLE")
    cutoff=target.market_bar_key.bar_start_utc
    history=rows[p.start:p.stop]
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _tail439(rows,p.stop,cutoff):
        return S1Ingredient439(S1State439.BLOCKED,"CONTEXT_NOT_CAUSAL_OR_LATEST_SUPPLIED")
    if _cross_tf_identity(bars[0])!=_cross_tf_identity(target):
        return S1Ingredient439(S1State439.BLOCKED,"CONTEXT_SOURCE_MISMATCH")
    return _geometry439(history,p,cutoff)


def inspect_s1_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not S1ContextPlan439 or variant_id not in
            ("S1/E_FAILED_BREAK","S1/E_CHOCH_DOWN","S1/F_MAJOR_CYCLE_TOP_PENDING")):
        raise ValueError("MST_439_EXACT_SCOPE")
    _validate439(plan)
    route=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant_id,
                             phase="R0",selected_frame=plan.timeframe)
    base=_r0439(inputs,plan)
    assessments=((route,base),)
    result=early=None
    if plan.distribution is not None:
        rc=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant_id,phase="R_C")
        result=inspect_distribution440(inputs,plan,base,states=S1State439,ingredient=S1Ingredient439)
        assessments+=((rc,result),)
    if plan.failed is not None:
        early=inspect_failed441(inputs,plan,base,result,variant=variant_id,
                                states=S1State439,ingredient=S1Ingredient439)
        re=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant_id,
                              phase="R_E",selected_frame=plan.failed.timeframe)
        assessments+=((re,early),)
    if plan.choch is not None:
        early=inspect_choch442(inputs,plan,result,variant=variant_id,
                               states=S1State439,ingredient=S1Ingredient439)
        re=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant_id,
                              phase="R_E",selected_frame=plan.choch.timeframe)
        assessments+=((re,early),)
    if plan.rf is not None:
        proof=inspect_rf443(inputs,plan,early,variant=variant_id,strategy=strategy,
                            states=S1State439,ingredient=S1Ingredient439)
        rf=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant_id,phase="R_F")
        assessments+=((rf,proof),)
    return S1Preview439(assessments)
