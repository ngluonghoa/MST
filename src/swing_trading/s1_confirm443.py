"""§443 explicit later D1 structural higher-low break, candidate only."""
from dataclasses import dataclass, replace
from decimal import Decimal

from .causal_structure_geometry import TiePolicy
from .market_data import Timeframe
from .s1_choch442 import _validate_pivots442, _history442, _rising442, _cross442
from .s1_failed_break441 import _atr441, _pair441, validate_pair_atr442
from .s1_rf_volume444 import S1RFVolumePlan444, inspect_volume444, validate_volume444


@dataclass(frozen=True)
class S1ConfirmPlan443:
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
    volume: S1RFVolumePlan444 | None = None


def validate_rf443(p,variant):
    if type(p) is not S1ConfirmPlan443 or variant not in ("S1/E_FAILED_BREAK","S1/E_CHOCH_DOWN"):
        raise ValueError("MST_443_EXPLICIT_RF_VARIANT")
    validate_pair_atr442(p,frames=(Timeframe.D1,))
    if type(p.history_start) is not int or not 0<=p.history_start<p.target_index-1:
        raise ValueError("MST_443_EXACT_PRE_PRIOR_WINDOW")
    _validate_pivots442(p,p.target_index-1-p.history_start)
    if p.volume is not None:
        validate_volume444(p.volume)


def _shape443(inputs,plan,p,prior,states,ingredient):
    rows=inputs.snapshots_for(Timeframe.D1)
    distribution=rows[plan.distribution.target_index].selected
    history=_history442(rows,p,prior,distribution)
    if history is None:
        return ingredient(states.BLOCKED,"D1_STRUCTURAL_HISTORY_NOT_CAUSAL")
    return _rising442(history,p,prior.market_bar_key.bar_start_utc,states,ingredient)


def inspect_rf443(inputs,plan,early,*,variant,states,ingredient):
    p=plan.rf
    validate_rf443(p,variant)
    if early is None or early.state is not states.MATCH:
        return ingredient(states.BLOCKED,"R_E_SELECTED_BRANCH_NOT_MATCHED")
    daily=inputs.snapshots_for(Timeframe.D1)
    if p.target_index>=len(daily) or p.atr_stop>len(daily):
        return ingredient(states.MISSING,"EXACT_D1_BREAK_OR_ATR_MISSING")
    early_plan=plan.failed if variant=="S1/E_FAILED_BREAK" else plan.choch
    early_bar=inputs.snapshots_for(early_plan.timeframe)[early_plan.target_index].selected
    prior,target=_pair441(inputs,p,early_bar)
    if prior is None:
        return ingredient(states.BLOCKED,"D1_PAIR_NOT_CAUSAL_AFTER_R_E")
    shape=_shape443(inputs,plan,p,prior,states,ingredient)
    if shape.state is not states.MATCH:
        return shape
    atr=_atr441(inputs,p,target)
    if atr is None:
        return ingredient(states.BLOCKED,"D1_BREAK_ATR_UNRESOLVED")
    result=_cross442(prior,target,shape,atr,p,states,ingredient)
    geometry=replace(result,reason="D1_STRUCTURAL_HL_CLOSED_BREAK_CANDIDATE_ONLY")
    return inspect_volume444(inputs,plan,geometry,states=states)
