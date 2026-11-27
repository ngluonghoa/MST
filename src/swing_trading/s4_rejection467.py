"""§467 S4 causal closed upper-boundary rejection candidate, not approval."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_structure_geometry import _cross_tf_identity,_eligible,_sequence,_source_identity
from .market_data import Timeframe
from .range_baseline_preview385 import (
    RangeEnginePlan385,RangeEnginePreview385,RangeIngredient385,RangeState385,
    inspect_routed_range_preview,
)
from .s1_context_preview439 import _tail439


@dataclass(frozen=True)
class S4RejectionPlan467:
    context: RangeEnginePlan385
    rejection_index: int
    candidate_k_reject: Decimal | None


def _validate467(p,variant):
    if type(p) is not S4RejectionPlan467 or type(p.context) is not RangeEnginePlan385:
        raise ValueError("MST_467_EXACT_REJECTION_PLAN")
    if variant not in ("S4/E_FALSE_BREAK","S4/E_BOS_DOWN"):
        raise ValueError("MST_467_EXACT_VARIANT")
    if type(p.context.target_tf) is not Timeframe or p.context.target_tf not in (Timeframe.M15,Timeframe.H1):
        raise ValueError("MST_467_EXPLICIT_INTRADAY_FRAME")
    if any(type(i) is not int for i in (p.context.target_index,p.rejection_index)):
        raise ValueError("MST_467_EXACT_INDICES")
    if not 0<=p.context.target_index<p.rejection_index<512:
        raise ValueError("MST_467_DISTINCT_LATER_REJECTION")
    k=p.candidate_k_reject
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_467_EXPLICIT_THRESHOLD")


def _daily467(inputs,p,target):
    rows=inputs.snapshots_for(Timeframe.D1)
    w=p.context.range_slice
    cutoff=target.market_bar_key.bar_start_utc
    daily,_=_sequence(rows[w.start:w.stop],cutoff=cutoff)
    return (bool(daily) and not _tail439(rows,w.stop,cutoff)
            and _cross_tf_identity(daily[0])==_cross_tf_identity(target))


def _geometry467(prior,target,r,k):
    distance=prior[0].close-target.close
    if any(not r.lower<=bar.close<=r.upper for bar in (*prior,target)):
        state=RangeState385.NONMATCH
    elif distance<=0 or target.close>=prior[-1].close:
        state=RangeState385.NONMATCH
    elif k is None:
        state=RangeState385.DISTANCE
    else:
        state=RangeState385.MATCH if distance>=k*r.atr else RangeState385.NONMATCH
    return RangeIngredient385(state,"CLOSED_UPPER_BOUNDARY_REJECTION_CANDIDATE_ONLY",
                              r,distance,True)


def _reject467(inputs,p,base,near):
    if base.state is not RangeState385.MATCH or near.state is not RangeState385.DISTANCE:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_PRIOR_RANGE_OR_NEAR_UNRESOLVED")
    if near.near_candidate is not True:
        return RangeIngredient385(RangeState385.NONMATCH,"S4_NOT_NEAR_UPPER_BOUNDARY",near.private_range)
    rows=inputs.snapshots_for(p.context.target_tf)
    if p.rejection_index>=len(rows):
        return RangeIngredient385(RangeState385.MISSING,"S4_REJECTION_BAR_MISSING")
    target=_eligible(rows[p.rejection_index],cutoff=inputs.as_of_utc)
    if target is None:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_REJECTION_BAR_UNQUALIFIED")
    prior,_=_sequence(rows[p.context.target_index:p.rejection_index],cutoff=target.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return RangeIngredient385(RangeState385.BLOCKED,"S4_REJECTION_PATH_NOT_CAUSAL")
    if not _daily467(inputs,p,target):
        return RangeIngredient385(RangeState385.BLOCKED,"S4_RANGE_NOT_CURRENT_OR_CAUSAL")
    return _geometry467(prior,target,near.private_range,p.candidate_k_reject)


def inspect_s4_rejection_preview(inputs,*,strategy,variant_id,plan):
    _validate467(plan,variant_id)
    preview=inspect_routed_range_preview(inputs,zone_id="S4",strategy=strategy,
                                         variant_id=variant_id,plan=plan.context)
    r0,rc=preview.assessments
    return RangeEnginePreview385((r0,(rc[0],_reject467(inputs,plan,r0[1],rc[1]))))
