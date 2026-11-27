"""§441 explicit S1 failed-break close-cross candidate, never sell authority."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import _cross_tf_identity, _eligible, _source_identity
from .market_data import Timeframe


@dataclass(frozen=True)
class S1FailedBreakPlan441:
    timeframe: Timeframe
    target_index: int
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


def validate_failed441(p,variant):
    if type(p) is not S1FailedBreakPlan441 or variant!="S1/E_FAILED_BREAK":
        raise ValueError("MST_441_EXPLICIT_FAILED_BREAK_VARIANT")
    if type(p.timeframe) is not Timeframe or p.timeframe not in (Timeframe.H1,Timeframe.M15):
        raise ValueError("MST_441_EXPLICIT_FRAME")
    if any(type(i) is not int for i in (p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_441_EXACT_INDICES")
    if not 1<=p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512:
        raise ValueError("MST_441_BOUNDED_WINDOW")
    if p.atr_stop-p.atr_start<15:
        raise ValueError("MST_441_ATR_WARMUP")
    e=p.candidate_epsilon
    if e is not None and (type(e) is not Decimal or not e.is_finite() or e<0):
        raise ValueError("MST_441_EXPLICIT_EPSILON")


def _pair441(inputs,p,distribution):
    rows=inputs.snapshots_for(p.timeframe)
    if p.target_index>=len(rows):
        return None,None
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return None,None
    prior=_eligible(rows[p.target_index-1],cutoff=target.market_bar_key.bar_start_utc)
    if prior is None:
        return None,None
    if (_source_identity(prior)!=_source_identity(target)
            or _cross_tf_identity(prior)!=_cross_tf_identity(distribution)
            or prior.market_bar_key.bar_start_utc<distribution.verified_at_utc):
        return None,None
    return prior,target


def _atr441(inputs,p,target):
    daily=inputs.snapshots_for(Timeframe.D1)
    cutoff=target.market_bar_key.bar_start_utc
    if p.atr_stop>len(daily):
        return None
    atr=calculate_wilder_atr14(daily[p.atr_start:p.atr_stop],
                as_of_utc=inputs.as_of_utc,known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return None
    if _cross_tf_identity(daily[p.atr_start].selected)!=_cross_tf_identity(target):
        return None
    for snap in daily[p.atr_stop:]:
        if snap.selected is None and snap.market_bar_key.bar_start_utc<cutoff:
            return None
        if snap.selected is not None and snap.selected.bar_end_utc<=cutoff:
            return None
    return atr.value


def inspect_failed441(inputs,plan,base,rc,*,variant,states,ingredient):
    p=plan.failed
    validate_failed441(p,variant)
    if rc is None or rc.state is not states.MATCH:
        return ingredient(states.BLOCKED,"R_C_DISTRIBUTION_NOT_MATCHED")
    rows=inputs.snapshots_for(p.timeframe)
    daily=inputs.snapshots_for(Timeframe.D1)
    if p.target_index>=len(rows) or p.atr_stop>len(daily):
        return ingredient(states.MISSING,"EXACT_FAILED_BREAK_OR_ATR_MISSING")
    distribution=daily[plan.distribution.target_index].selected
    prior,target=_pair441(inputs,p,distribution)
    if prior is None:
        return ingredient(states.BLOCKED,"FAILED_BREAK_PAIR_NOT_CAUSAL")
    atr=_atr441(inputs,p,target)
    if atr is None:
        return ingredient(states.BLOCKED,"FAILED_BREAK_ATR_UNRESOLVED")
    return _cross441(prior,target,base.private_resistance,atr,p,states,ingredient)


def _cross441(prior,target,resistance,atr,p,states,ingredient):
    if p.candidate_epsilon is None:
        return ingredient(states.DISTANCE,"FAILED_BREAK_EPSILON_UNCALIBRATED",private_atr=atr)
    match=prior.close>resistance and target.close<resistance-p.candidate_epsilon*atr
    state=states.MATCH if match else states.NONMATCH
    return ingredient(state,"SAME_RESISTANCE_CLOSED_FAILED_BREAK_CANDIDATE_ONLY",
                      private_atr=atr)
