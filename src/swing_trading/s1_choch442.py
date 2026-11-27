"""§442 explicit causal prior rising microstructure and closed CHoCH down."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _sequence, _source_identity,
    inspect_causal_pivot,
)
from .market_data import Timeframe
from .s1_failed_break441 import _atr441, _pair441, validate_pair_atr442


@dataclass(frozen=True)
class S1ChochPlan442:
    timeframe: Timeframe
    target_index: int
    history_start: int
    high_indices: tuple[int, int]
    low_indices: tuple[int, int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


def _validate_pivots442(p,count):
    for pair in (p.high_indices,p.low_indices):
        if type(pair) is not tuple or len(pair)!=2:
            raise ValueError("MST_442_EXACT_PAIR")
        if any(type(i) is not int or not 0<=i<count for i in pair):
            raise ValueError("MST_442_EXACT_PIVOT_INDICES")
    if (type(p.left_count) is not int or not 1<=p.left_count<=40
            or type(p.right_count) is not int or not 1<=p.right_count<=40
            or type(p.tie_policy) is not TiePolicy):
        raise ValueError("MST_442_EXPLICIT_PIVOT_POLICY")


def validate_choch442(p,variant):
    if type(p) is not S1ChochPlan442 or variant!="S1/E_CHOCH_DOWN":
        raise ValueError("MST_442_EXPLICIT_CHOCH_VARIANT")
    validate_pair_atr442(p)
    if type(p.history_start) is not int or not 0<=p.history_start<p.target_index-1:
        raise ValueError("MST_442_EXACT_PRE_PRIOR_WINDOW")
    _validate_pivots442(p,p.target_index-1-p.history_start)


def _pivots442(history,p,cutoff):
    def pair(indices,side):
        return tuple(inspect_causal_pivot(history,candidate_index=i,side=side,
                    left_count=p.left_count,right_count=p.right_count,
                    tie_policy=p.tie_policy,as_of_utc=cutoff) for i in indices)
    return pair(p.high_indices,StructureSide.HIGH),pair(p.low_indices,StructureSide.LOW)


def _rising442(history,p,cutoff,states,ingredient):
    h1,h2=p.high_indices
    l1,l2=p.low_indices
    if not (h1<l1<h2<l2 or l1<h1<l2<h2):
        return ingredient(states.NONMATCH,"MICRO_PAIRS_NOT_ALTERNATING")
    highs,lows=_pivots442(history,p,cutoff)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in highs+lows):
        return ingredient(states.BLOCKED,"MICRO_PIVOT_WITNESS_UNAVAILABLE")
    if any(x.geometric_extremum is not True for x in highs+lows):
        return ingredient(states.NONMATCH,"MICRO_PIVOT_NOT_EXTREMUM")
    rising=highs[1].pivot_price>highs[0].pivot_price and lows[1].pivot_price>lows[0].pivot_price
    state=states.MATCH if rising else states.NONMATCH
    return ingredient(state,"PRIOR_MICRO_HH_HL_CANDIDATE_ONLY",
                      private_higher_low=lows[1].pivot_price)


def _history442(rows,p,prior,distribution):
    history=rows[p.history_start:p.target_index-1]
    cutoff=prior.market_bar_key.bar_start_utc
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars:
        return None
    if (bars[0].market_bar_key.bar_start_utc<distribution.verified_at_utc
            or _source_identity(bars[0])!=_source_identity(prior)):
        return None
    return history


def _cross442(prior,target,shape,atr,p,states,ingredient):
    low=shape.private_higher_low
    if p.candidate_epsilon is None:
        return ingredient(states.DISTANCE,"CHOCH_EPSILON_UNCALIBRATED",
                          private_higher_low=low,private_atr=atr)
    match=prior.close>=low and target.close<low-p.candidate_epsilon*atr
    state=states.MATCH if match else states.NONMATCH
    return ingredient(state,"PRIOR_MICRO_HH_HL_CLOSED_BREAK_DOWN_ONLY",
                      private_higher_low=low,private_atr=atr)


def inspect_choch442(inputs,plan,rc,*,variant,states,ingredient):
    p=plan.choch
    validate_choch442(p,variant)
    if rc is None or rc.state is not states.MATCH:
        return ingredient(states.BLOCKED,"R_C_DISTRIBUTION_NOT_MATCHED")
    rows=inputs.snapshots_for(p.timeframe)
    daily=inputs.snapshots_for(Timeframe.D1)
    if p.target_index>=len(rows) or p.atr_stop>len(daily):
        return ingredient(states.MISSING,"EXACT_CHOCH_OR_ATR_MISSING")
    distribution=daily[plan.distribution.target_index].selected
    prior,target=_pair441(inputs,p,distribution)
    if prior is None:
        return ingredient(states.BLOCKED,"CHOCH_PAIR_NOT_CAUSAL")
    history=_history442(rows,p,prior,distribution)
    if history is None:
        return ingredient(states.BLOCKED,"MICRO_HISTORY_NOT_CAUSAL")
    shape=_rising442(history,p,prior.market_bar_key.bar_start_utc,states,ingredient)
    if shape.state is not states.MATCH:
        return shape
    atr=_atr441(inputs,p,target)
    if atr is None:
        return ingredient(states.BLOCKED,"CHOCH_ATR_UNRESOLVED")
    return _cross442(prior,target,shape,atr,p,states,ingredient)
