"""§467 S4 causal closed upper-boundary rejection candidate, not approval."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_structure_geometry import (
    GeometryState,StructureSide,TiePolicy,inspect_causal_pivot,
    _cross_tf_identity,_eligible,_sequence,_source_identity,
)
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .range_baseline_preview385 import (
    RangeEnginePlan385,RangeEnginePreview385,RangeIngredient385,RangeState385,
    inspect_routed_range_preview,
)
from .s1_context_preview439 import _tail439
from .s1_failed_break441 import _pair441,validate_pair_atr442
from .feature_engine460 import inspect_target_d1_atr


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


@dataclass(frozen=True)
class S4FalseBreakPlan468:
    context: S4RejectionPlan467
    timeframe: Timeframe
    breakout_index: int
    reentry_index: int
    candidate_epsilon: Decimal | None


def _validate468(p,variant):
    if type(p) is not S4FalseBreakPlan468 or variant!="S4/E_FALSE_BREAK":
        raise ValueError("MST_468_EXPLICIT_FALSE_BREAK_VARIANT")
    if type(p.context) is not S4RejectionPlan467:
        raise ValueError("MST_468_EXACT_REJECTION_CONTEXT")
    if type(p.timeframe) is not Timeframe or p.timeframe not in (Timeframe.H1,Timeframe.M15):
        raise ValueError("MST_468_EXPLICIT_FRAME")
    if any(type(i) is not int for i in (p.breakout_index,p.reentry_index)):
        raise ValueError("MST_468_EXACT_INDICES")
    if not 1<=p.breakout_index<p.reentry_index<512:
        raise ValueError("MST_468_DISTINCT_LATER_REENTRY")
    e=p.candidate_epsilon
    if e is not None and (type(e) is not Decimal or not e.is_finite() or e<0):
        raise ValueError("MST_468_EXPLICIT_EPSILON")


def _path468(inputs,p,target):
    rows=inputs.snapshots_for(p.timeframe)
    prior,_=_sequence(rows[p.breakout_index-1:p.reentry_index],
                      cutoff=target.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return None
    breakout=prior[1]
    if _eligible(rows[p.breakout_index-1],cutoff=breakout.market_bar_key.bar_start_utc) is None:
        return None
    rc=inputs.snapshots_for(p.context.context.target_tf)[p.context.rejection_index].selected
    if rc.verified_at_utc>breakout.market_bar_key.bar_start_utc:
        return None
    if _cross_tf_identity(rc)!=_cross_tf_identity(target):
        return None
    if prior[0].market_bar_key!=rc.market_bar_key and prior[0].market_bar_key.bar_start_utc<rc.verified_at_utc:
        return None
    if not _daily467(inputs,p.context,breakout) or not _daily467(inputs,p.context,target):
        return None
    return prior


def _geometry468(prior,target,r,e):
    valid=(r.lower<=prior[0].close<=r.upper
           and all(b.close>r.upper for b in prior[1:])
           and r.lower<=target.close<r.upper)
    distance=r.upper-target.close
    if not valid:
        state=RangeState385.NONMATCH
    elif e is None:
        state=RangeState385.DISTANCE
    else:
        state=RangeState385.MATCH if distance>e*r.atr else RangeState385.NONMATCH
    return RangeIngredient385(state,"CLOSED_UPPER_FALSE_BREAK_REENTRY_CANDIDATE_ONLY",r,distance)


def _false468(inputs,p,rc):
    if rc.state is not RangeState385.MATCH:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(p.timeframe)
    if p.reentry_index>=len(rows):
        return RangeIngredient385(RangeState385.MISSING,"S4_FALSE_BREAK_REENTRY_MISSING")
    target=_eligible(rows[p.reentry_index],cutoff=inputs.as_of_utc)
    if target is None:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_FALSE_BREAK_REENTRY_UNQUALIFIED")
    prior=_path468(inputs,p,target)
    if prior is None:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_FALSE_BREAK_PATH_NOT_CAUSAL")
    return _geometry468(prior,target,rc.private_range,p.candidate_epsilon)


def inspect_s4_false_break_preview(inputs,*,strategy,variant_id,plan):
    _validate468(plan,variant_id)
    preview=inspect_s4_rejection_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    rc=preview.assessments[1][1]
    route=route_phase_inputs(inputs,zone_id="S4",strategy=strategy,variant_id=variant_id,
                             phase="R_E",selected_frame=plan.timeframe)
    return RangeEnginePreview385(preview.assessments+((route,_false468(inputs,plan,rc)),))


@dataclass(frozen=True)
class S4BosDownPlan469:
    context: S4RejectionPlan467
    timeframe: Timeframe
    target_index: int
    history_start: int
    low_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


def _validate469(p,variant):
    if type(p) is not S4BosDownPlan469 or variant!="S4/E_BOS_DOWN":
        raise ValueError("MST_469_EXPLICIT_BOS_DOWN_VARIANT")
    if type(p.context) is not S4RejectionPlan467:
        raise ValueError("MST_469_EXACT_REJECTION_CONTEXT")
    validate_pair_atr442(p)
    if any(type(i) is not int for i in (p.history_start,p.low_index,p.left_count,p.right_count)):
        raise ValueError("MST_469_EXACT_PIVOT_INDICES")
    if not 0<=p.history_start<p.target_index-1 or not 0<=p.low_index<p.target_index-1-p.history_start:
        raise ValueError("MST_469_BOUNDED_PIVOT_HISTORY")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_469_EXPLICIT_PIVOT_POLICY")


def _path469(inputs,p,rc,prior,target):
    rows=inputs.snapshots_for(p.timeframe)
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    return (path if path and _source_identity(path[0])==_source_identity(target)
            and path[0].market_bar_key.bar_start_utc>=rc.verified_at_utc
            and _daily467(inputs,p.context,target) else None)


def _geometry469(p,prior,target,r,pivot,atr):
    distance=pivot.pivot_price-target.close
    if not r.lower<pivot.pivot_price<=r.upper or prior.close<pivot.pivot_price or distance<=0:
        state=RangeState385.NONMATCH
    elif p.candidate_epsilon is None:
        state=RangeState385.DISTANCE
    else:
        state=RangeState385.MATCH if distance>p.candidate_epsilon*atr else RangeState385.NONMATCH
    return RangeIngredient385(state,"CLOSED_MICRO_LOW_BOS_DOWN_CANDIDATE_ONLY",r,distance)


def _pivot469(inputs,p,prior,target,r):
    rows=inputs.snapshots_for(p.timeframe)
    history=rows[p.history_start:p.target_index-1]
    pivot=inspect_causal_pivot(history,candidate_index=p.low_index,side=StructureSide.LOW,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=prior.market_bar_key.bar_start_utc)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_BOS_PIVOT_UNRESOLVED")
    if pivot.geometric_extremum is not True:
        return RangeIngredient385(RangeState385.NONMATCH,"S4_BOS_LOW_NOT_EXTREMUM")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_BOS_D1_ATR_UNRESOLVED")
    return _geometry469(p,prior,target,r,pivot,atr)


def _bos469(inputs,p,rc):
    if rc.state is not RangeState385.MATCH:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_R_C_NOT_MATCHED")
    if p.target_index>=len(inputs.snapshots_for(p.timeframe)) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return RangeIngredient385(RangeState385.MISSING,"S4_BOS_BAR_OR_ATR_MISSING")
    rejection=inputs.snapshots_for(p.context.context.target_tf)[p.context.rejection_index].selected
    prior,target=_pair441(inputs,p,rejection)
    if prior is None:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_BOS_PAIR_NOT_CAUSAL")
    path=_path469(inputs,p,rejection,prior,target)
    if not path:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_BOS_PATH_OR_RANGE_NOT_CAUSAL")
    r=rc.private_range
    if any(not r.lower<=bar.close<=r.upper for bar in (*path,target)):
        return RangeIngredient385(RangeState385.NONMATCH,"S4_BOS_ORIGINAL_RANGE_INVALIDATED")
    return _pivot469(inputs,p,prior,target,r)


def inspect_s4_bos_down_preview(inputs,*,strategy,variant_id,plan):
    _validate469(plan,variant_id)
    preview=inspect_s4_rejection_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route=route_phase_inputs(inputs,zone_id="S4",strategy=strategy,variant_id=variant_id,
                             phase="R_E",selected_frame=plan.timeframe)
    return RangeEnginePreview385(preview.assessments+((route,_bos469(inputs,plan,preview.assessments[1][1])),))


@dataclass(frozen=True)
class S4ConfirmPlan470:
    early: S4FalseBreakPlan468 | S4BosDownPlan469
    timeframe: Timeframe
    target_index: int
    history_start: int
    low_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


def _validate470(p,variant):
    if type(p) is not S4ConfirmPlan470:
        raise ValueError("MST_470_EXPLICIT_CONFIRM_PLAN")
    if (type(p.early),variant) not in ((S4FalseBreakPlan468,"S4/E_FALSE_BREAK"),
                                      (S4BosDownPlan469,"S4/E_BOS_DOWN")):
        raise ValueError("MST_470_EXACT_EARLY_VARIANT")
    validate_pair_atr442(p,frames=(Timeframe.H1,Timeframe.D1))
    if any(type(i) is not int for i in (p.history_start,p.low_index,p.left_count,p.right_count)):
        raise ValueError("MST_470_EXACT_PIVOT_INDICES")
    if not 0<=p.history_start<p.target_index-1 or not 0<=p.low_index<p.target_index-1-p.history_start:
        raise ValueError("MST_470_BOUNDED_PIVOT_HISTORY")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_470_EXPLICIT_PIVOT_POLICY")


def _early470(inputs,p):
    e=p.early
    i=e.reentry_index if type(e) is S4FalseBreakPlan468 else e.target_index
    return inputs.snapshots_for(e.timeframe)[i].selected


def _daily470(inputs,p,target,r):
    w=p.early.context.context.range_slice
    rows=inputs.snapshots_for(Timeframe.D1)
    daily,_=_sequence(rows[w.start:p.atr_stop],cutoff=target.market_bar_key.bar_start_utc)
    if p.atr_stop<w.stop or not daily or _cross_tf_identity(daily[0])!=_cross_tf_identity(target):
        return RangeIngredient385(RangeState385.BLOCKED,"S4_RF_D1_PATH_UNRESOLVED")
    if any(not r.lower<=b.close<=r.upper for b in daily[w.stop-w.start:]):
        return RangeIngredient385(RangeState385.NONMATCH,"S4_RF_D1_RANGE_INVALIDATED")
    return None


def _intraday470(inputs,early,target,r):
    cutoff=target.market_bar_key.bar_start_utc
    for tf in (Timeframe.M15,Timeframe.H1):
        for snapshot in inputs.snapshots_for(tf):
            start=snapshot.market_bar_key.bar_start_utc
            if not early.verified_at_utc<=start<cutoff:
                continue
            if snapshot.selected is not None and snapshot.selected.bar_end_utc>cutoff:
                continue
            bar=_eligible(snapshot,cutoff=cutoff)
            if bar is None or _cross_tf_identity(bar)!=_cross_tf_identity(target):
                return RangeIngredient385(RangeState385.BLOCKED,"S4_RF_INTRADAY_PATH_UNRESOLVED")
            if not r.lower<=bar.close<=r.upper:
                return RangeIngredient385(RangeState385.NONMATCH,"S4_RF_INTRADAY_RANGE_INVALIDATED")
    return None


def _path470(inputs,p,early,target,r):
    rows=inputs.snapshots_for(p.timeframe)
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not path or _source_identity(path[0])!=_source_identity(target) or path[0].market_bar_key.bar_start_utc<early.verified_at_utc:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_RF_MICRO_PATH_NOT_CAUSAL")
    if any(not r.lower<=bar.close<=r.upper for bar in (*path,target)):
        return RangeIngredient385(RangeState385.NONMATCH,"S4_RF_ORIGINAL_RANGE_INVALIDATED")
    return _daily470(inputs,p,target,r) or _intraday470(inputs,early,target,r)


def _confirm470(inputs,p,re):
    if re.state is not RangeState385.MATCH:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_R_E_NOT_MATCHED")
    if p.target_index>=len(inputs.snapshots_for(p.timeframe)) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return RangeIngredient385(RangeState385.MISSING,"S4_RF_BAR_OR_ATR_MISSING")
    early=_early470(inputs,p)
    prior,target=_pair441(inputs,p,early)
    if prior is None:
        return RangeIngredient385(RangeState385.BLOCKED,"S4_RF_PAIR_NOT_CAUSAL")
    r=re.private_range
    gap=_path470(inputs,p,early,target,r)
    if gap is not None:
        return gap
    proof=_pivot469(inputs,p,prior,target,r)
    return RangeIngredient385(proof.state,"S4_RF_"+proof.reason,proof.private_range,proof.distance)


def inspect_s4_confirm_preview(inputs,*,strategy,variant_id,plan):
    _validate470(plan,variant_id)
    inspect=inspect_s4_false_break_preview if type(plan.early) is S4FalseBreakPlan468 else inspect_s4_bos_down_preview
    preview=inspect(inputs,strategy=strategy,variant_id=variant_id,plan=plan.early)
    route=route_phase_inputs(inputs,zone_id="S4",strategy=strategy,variant_id=variant_id,
                             phase="R_F",selected_frame=plan.timeframe)
    return RangeEnginePreview385(preview.assessments+((route,_confirm470(inputs,plan,preview.assessments[2][1])),))
