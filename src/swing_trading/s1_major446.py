"""§446 explicit major-cycle W1 candidate following selected D1 confirmation."""
from dataclasses import dataclass, replace
from decimal import Decimal

from .causal_structure_geometry import TiePolicy, _cross_tf_identity, _eligible, _sequence, _source_identity
from .market_data import Timeframe
from .s1_choch442 import _validate_pivots442, _rising442, _cross442
from .feature_engine460 import inspect_target_d1_atr as _atr441
from .s1_failed_break441 import validate_pair_atr442
from .s1_holdings445 import S1HoldingsPlan445, S1HoldingsResult445, inspect_holdings445, validate_holdings445


@dataclass(frozen=True)
class S1MajorPlan446:
    early_variant: str
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
    holdings: S1HoldingsPlan445 | None = None


@dataclass(frozen=True)
class S1MajorResult446:
    weekly_higher_low: Decimal
    weekly_atr_d1: Decimal
    candidate_match: bool
    weekly_holdings: S1HoldingsResult445 | None = None

    @property
    def action_eligible(self):
        return False


def select_early446(plan,variant):
    p=plan.major
    if p is None:
        return variant
    if type(p) is not S1MajorPlan446 or variant!="S1/F_MAJOR_CYCLE_TOP_PENDING":
        raise ValueError("MST_446_EXPLICIT_MAJOR_VARIANT")
    if p.early_variant not in ("S1/E_FAILED_BREAK","S1/E_CHOCH_DOWN") or plan.rf is None:
        raise ValueError("MST_446_EXPLICIT_EARLY_AND_RF")
    if (plan.failed is not None,plan.choch is not None)!=(p.early_variant=="S1/E_FAILED_BREAK",
                                                         p.early_variant=="S1/E_CHOCH_DOWN"):
        raise ValueError("MST_446_EXACT_SELECTED_EARLY")
    validate_pair_atr442(p,frames=(Timeframe.W1,))
    if type(p.history_start) is not int or not 0<=p.history_start<p.target_index-1:
        raise ValueError("MST_446_EXACT_WEEKLY_HISTORY")
    _validate_pivots442(p,p.target_index-1-p.history_start)
    if p.holdings is not None:
        validate_holdings445(p.holdings)
    return p.early_variant


def _weekly_pair446(inputs,p,d1):
    rows=inputs.snapshots_for(Timeframe.W1)
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return None,None
    cutoff=target.market_bar_key.bar_start_utc
    prior=_eligible(rows[p.target_index-1],cutoff=cutoff)
    if prior is None:
        return None,None
    if (cutoff<d1.verified_at_utc or _source_identity(prior)!=_source_identity(target)
            or _cross_tf_identity(target)!=_cross_tf_identity(d1)):
        return None,None
    return prior,target


def _weekly_shape446(inputs,p,prior,states,ingredient):
    rows=inputs.snapshots_for(Timeframe.W1)
    history=rows[p.history_start:p.target_index-1]
    cutoff=prior.market_bar_key.bar_start_utc
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _source_identity(bars[0])!=_source_identity(prior):
        return ingredient(states.BLOCKED,"W1_HISTORY_NOT_CAUSAL")
    return _rising442(history,p,cutoff,states,ingredient)


def inspect_major446(inputs,plan,proof,*,strategy,states,ingredient):
    p=plan.major
    if p is None or proof.state is not states.MATCH:
        return proof
    if proof.rvol is None:
        return replace(proof,state=states.MISSING,reason="MAJOR_REQUIRES_D1_VOLUME")
    if p.target_index>=len(inputs.snapshots_for(Timeframe.W1)):
        return replace(proof,state=states.MISSING,reason="EXACT_W1_CONFIRMATION_MISSING")
    d1=inputs.snapshots_for(Timeframe.D1)[plan.rf.target_index].selected
    prior,target=_weekly_pair446(inputs,p,d1)
    if prior is None:
        return replace(proof,state=states.BLOCKED,reason="W1_PAIR_NOT_CAUSAL_AFTER_D1")
    shape=_weekly_shape446(inputs,p,prior,states,ingredient)
    if shape.state is not states.MATCH:
        return replace(proof,state=shape.state,reason=shape.reason)
    atr=_atr441(inputs,p,target)
    if atr is None:
        return replace(proof,state=states.BLOCKED,reason="W1_BREAK_D1_ATR_UNRESOLVED")
    cross=_cross442(prior,target,shape,atr,p,states,ingredient)
    if cross.state is states.DISTANCE:
        return replace(proof,state=cross.state,reason="W1_EPSILON_UNCALIBRATED")
    result=S1MajorResult446(shape.private_higher_low,atr,cross.state is states.MATCH)
    result_proof=replace(proof,state=cross.state,reason="W1_CLOSED_HL_BREAK_CANDIDATE_ONLY",major=result)
    return _weekly_holdings447(target,p,result_proof,strategy=strategy,states=states)


def _weekly_holdings447(target,p,proof,*,strategy,states):
    if p.holdings is None or proof.state is not states.MATCH:
        return proof
    checked=inspect_holdings445(target,p.holdings,replace(proof,holdings=None),strategy=strategy,states=states)
    return replace(proof,state=checked.state,reason=checked.reason,
                   major=replace(proof.major,weekly_holdings=checked.holdings))
