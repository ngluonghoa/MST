"""§504 B1 D1 causal higher-low and closed BOS_UP candidate."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .b1_bos_up503 import B1BosUpPlan503,B1BosUpIngredient503,inspect_b1_bos_up503_preview
from .b1_reclaim502 import B1ReclaimPlan502,B1ReclaimIngredient502,inspect_b1_reclaim502_preview
from .b1_decline499 import B1Preview499
from .causal_structure_geometry import GeometryState,StructureSide,TiePolicy,inspect_causal_pivot,_eligible,_sequence,_source_identity,_cross_tf_identity
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1ConfirmPlan504:
    early: B1ReclaimPlan502 | B1BosUpPlan503
    history_start: int
    target_index: int
    high_index: int
    low_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class B1ConfirmIngredient504:
    state: S1State439
    reason: str
    private_event_id: str | None = None
    private_support: Decimal | None = None
    private_higher_low: Decimal | None = None
    private_key_high: Decimal | None = None
    private_rf_known: datetime | None = None


def _validate504(p):
    if type(p) is not B1ConfirmPlan504 or type(p.early) not in (B1ReclaimPlan502,B1BosUpPlan503):
        raise ValueError("MST_504_EXACT_EARLY_PLAN")
    if any(type(i) is not int for i in (p.history_start,p.target_index,p.high_index,p.low_index,p.left_count,p.right_count,p.atr_start,p.atr_stop)):
        raise ValueError("MST_504_EXACT_INDICES")
    if not 0<=p.history_start<p.target_index<512 or not 0<=p.atr_start<p.atr_stop==p.target_index or p.atr_stop-p.atr_start<15:
        raise ValueError("MST_504_EXACT_WINDOWS")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_504_EXACT_PIVOT_POLICY")
    if not p.left_count<=p.high_index<p.low_index or p.history_start+p.low_index+p.right_count>=p.target_index-1:
        raise ValueError("MST_504_DISTINCT_HIGH_LOW_WITNESSES")
    k=p.candidate_epsilon
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_504_EXPLICIT_EPSILON")


def _path504(inputs,p,target,re):
    rows=inputs.snapshots_for(Timeframe.D1)
    if any(s.market_bar_key.bar_start_utc>=re.private_early_known for s in rows[:p.history_start]):
        return None
    bars,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    early=inputs.snapshots_for(Timeframe.M15)[p.early.target_index].selected
    if not bars or bars[0].market_bar_key.bar_start_utc<re.private_early_known:
        return None
    if _source_identity(bars[0])!=_source_identity(target) or _cross_tf_identity(early)!=_cross_tf_identity(target):
        return None
    if any(a.verified_at_utc>b.market_bar_key.bar_start_utc for a,b in zip(bars,bars[1:])):
        return None
    return bars


def _invalidate504(inputs,target,re):
    for s in inputs.snapshots_for(Timeframe.M15):
        if not re.private_early_known<=s.market_bar_key.bar_start_utc<target.bar_end_utc:
            continue
        if s.selected is not None and s.selected.bar_end_utc>target.bar_end_utc:
            continue
        b=_eligible(s,cutoff=target.verified_at_utc)
        if b is None or _cross_tf_identity(b)!=_cross_tf_identity(target):
            return S1State439.BLOCKED
        if b.close<re.private_support:
            return S1State439.NONMATCH
    return None


def _cross504(inputs,p,target,bars,re,high,low):
    if any(b.close<re.private_support for b in (*bars,target)):
        return B1ConfirmIngredient504(S1State439.NONMATCH,"RF_SUPPORT_INVALIDATED")
    if any(b.close>high for b in bars[p.high_index+p.right_count+1:]) or target.close<=high or target.close<=target.open:
        return B1ConfirmIngredient504(S1State439.NONMATCH,"RF_NO_FIRST_LATER_BULLISH_CLOSED_CROSS")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return B1ConfirmIngredient504(S1State439.BLOCKED,"RF_ATR_UNRESOLVED")
    k=p.candidate_epsilon
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if target.close>high+k*atr else S1State439.NONMATCH
    return B1ConfirmIngredient504(state,"D1_CONFIRMED_HL_BOS_UP_CANDIDATE_ONLY",
        re.private_event_id,re.private_support,low,high,target.verified_at_utc)


def _shape504(inputs,p,target,bars,re):
    denial=_invalidate504(inputs,target,re)
    if denial is not None:
        return B1ConfirmIngredient504(denial,"RF_M15_INVALIDATION_OR_UNRESOLVED")
    rows=inputs.snapshots_for(Timeframe.D1)[p.history_start:p.target_index-1]
    policy=dict(left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
                as_of_utc=bars[-1].market_bar_key.bar_start_utc)
    high=inspect_causal_pivot(rows,candidate_index=p.high_index,side=StructureSide.HIGH,**policy)
    low=inspect_causal_pivot(rows,candidate_index=p.low_index,side=StructureSide.LOW,**policy)
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in (high,low)):
        return B1ConfirmIngredient504(S1State439.BLOCKED,"RF_PIVOTS_NOT_CAUSAL")
    if any(x.geometric_extremum is not True for x in (high,low)) or not re.private_support<low.pivot_price<high.pivot_price:
        return B1ConfirmIngredient504(S1State439.NONMATCH,"RF_HIGHER_LOW_NOT_CONFIRMED")
    return _cross504(inputs,p,target,bars,re,high.pivot_price,low.pivot_price)


def _confirm504(inputs,p,re):
    if type(re) not in (B1ReclaimIngredient502,B1BosUpIngredient503) or re.state is not S1State439.MATCH:
        return B1ConfirmIngredient504(S1State439.BLOCKED,"R_E_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.D1)
    if p.target_index>=len(rows):
        return B1ConfirmIngredient504(S1State439.MISSING,"RF_TARGET_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or target.verified_at_utc>p.early.expires_at_utc:
        return B1ConfirmIngredient504(S1State439.BLOCKED,"RF_TARGET_OR_EXPIRY_UNRESOLVED")
    bars=_path504(inputs,p,target,re)
    if bars is None:
        return B1ConfirmIngredient504(S1State439.BLOCKED,"RF_PATH_NOT_CAUSAL")
    return _shape504(inputs,p,target,bars,re)


def inspect_b1_confirm504_preview(inputs,*,strategy,variant_id,plan):
    _validate504(plan)
    fn=inspect_b1_reclaim502_preview if type(plan.early) is B1ReclaimPlan502 else inspect_b1_bos_up503_preview
    preview=fn(inputs,strategy=strategy,variant_id=variant_id,plan=plan.early)
    route=route_phase_inputs(inputs,zone_id="B1",strategy=strategy,variant_id=variant_id,phase="R_F")
    return B1Preview499(preview.assessments+((route,_confirm504(inputs,plan,preview.assessments[-1][1])),))
