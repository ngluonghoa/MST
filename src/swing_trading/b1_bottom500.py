"""§500 B1 exact two post-decline D1 bottom tests, candidate only."""
from dataclasses import dataclass
from decimal import Decimal

from .b1_decline499 import B1DeclinePlan499,B1Preview499,inspect_b1_decline499_preview
from .causal_structure_geometry import GeometryState,StructureSide,TiePolicy,inspect_causal_pivot,_eligible,_sequence,_cross_tf_identity
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .s1_context_preview439 import S1State439,_tail439


@dataclass(frozen=True)
class B1BottomPlan500:
    context: B1DeclinePlan499
    evaluation_index: int
    start: int
    stop: int
    first_index: int
    second_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_k_touch: Decimal | None


@dataclass(frozen=True)
class B1BottomIngredient500:
    state: S1State439
    reason: str
    private_decline: object
    private_support: Decimal | None = None
    private_atr: Decimal | None = None


def _validate500(p):
    if type(p) is not B1BottomPlan500 or type(p.context) is not B1DeclinePlan499:
        raise ValueError("MST_500_EXACT_BOTTOM_PLAN")
    indices=(p.evaluation_index,p.start,p.stop,p.first_index,p.second_index,p.atr_start,p.atr_stop)
    if any(type(i) is not int for i in indices):
        raise ValueError("MST_500_EXACT_INDICES")
    if not 0<=p.start<p.stop<=512 or not 0<=p.first_index<p.second_index<p.stop-p.start:
        raise ValueError("MST_500_DISTINCT_BOTTOM_TESTS")
    if not 0<=p.atr_start<p.atr_stop==p.start+p.second_index or p.atr_stop-p.atr_start<15:
        raise ValueError("MST_500_ATR_PREFIX_BEFORE_SECOND_TEST")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.left_count) is not int or type(p.right_count) is not int or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_500_EXPLICIT_PIVOT_POLICY")
    k=p.candidate_k_touch
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_500_EXPLICIT_TOLERANCE")


def _pivots500(inputs,p,history,bars,proof,cutoff):
    policy=dict(left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy)
    first,second=tuple(inspect_causal_pivot(history,candidate_index=i,side=StructureSide.LOW,
                        as_of_utc=cutoff,**policy) for i in (p.first_index,p.second_index))
    target=bars[p.second_index]
    if any(x.state is not GeometryState.DESCRIPTIVE_ONLY for x in (first,second)):
        return B1BottomIngredient500(S1State439.BLOCKED,"BOTTOM_PIVOT_NOT_CAUSAL",proof)
    if first.witness_known_at_utc>target.market_bar_key.bar_start_utc:
        return B1BottomIngredient500(S1State439.BLOCKED,"FIRST_BOTTOM_NOT_KNOWN_BEFORE_RETEST",proof)
    if any(x.geometric_extremum is not True for x in (first,second)):
        return B1BottomIngredient500(S1State439.NONMATCH,"BOTTOM_NOT_EXTREMUM",proof)
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None:
        return B1BottomIngredient500(S1State439.BLOCKED,"BOTTOM_ATR_UNRESOLVED",proof)
    support=first.pivot_price
    if any(x.close<support for x in bars[p.first_index:]):
        state=S1State439.NONMATCH
    elif p.candidate_k_touch is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if abs(second.pivot_price-support)<=p.candidate_k_touch*atr else S1State439.NONMATCH
    return B1BottomIngredient500(state,"TWO_BOTTOM_TESTS_ONLY_MARKET_CONTEXT_PENDING",proof,support,atr)


def _bottom500(inputs,p,proof):
    daily=inputs.snapshots_for(Timeframe.D1)
    anchors=inputs.snapshots_for(Timeframe.M15)
    if len(daily)<p.stop or len(anchors)<=p.evaluation_index:
        return B1BottomIngredient500(S1State439.MISSING,"EXACT_BOTTOM_OR_EVALUATION_MISSING",proof)
    prior=anchors[p.context.anchor_index].selected
    anchor=_eligible(anchors[p.evaluation_index],cutoff=inputs.as_of_utc)
    if anchor is None or prior.verified_at_utc>anchor.market_bar_key.bar_start_utc:
        return B1BottomIngredient500(S1State439.BLOCKED,"BOTTOM_EVALUATION_NOT_CAUSAL",proof)
    cutoff=anchor.market_bar_key.bar_start_utc
    history=daily[p.start:p.stop]
    bars,_=_sequence(history,cutoff=cutoff)
    if not bars or _tail439(daily,p.stop,cutoff):
        return B1BottomIngredient500(S1State439.BLOCKED,"BOTTOM_HISTORY_NOT_CAUSAL_OR_LATEST",proof)
    if bars[0].market_bar_key.bar_start_utc<prior.verified_at_utc or not _cross_tf_identity(bars[0])==_cross_tf_identity(prior)==_cross_tf_identity(anchor):
        return B1BottomIngredient500(S1State439.BLOCKED,"BOTTOM_POST_DECLINE_SCOPE",proof)
    return _pivots500(inputs,p,history,bars,proof,cutoff)


def inspect_b1_bottom500_preview(inputs,*,strategy,variant_id,plan):
    _validate500(plan)
    if not plan.context.anchor_index<plan.evaluation_index<512:
        raise ValueError("MST_500_DISTINCT_LATER_ANCHOR")
    preview=inspect_b1_decline499_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route,proof=preview.assessments[0]
    if proof.state is not S1State439.MATCH:
        return preview
    return B1Preview499(((route,_bottom500(inputs,plan,proof)),))
