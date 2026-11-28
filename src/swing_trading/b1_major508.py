"""§508 explicit W1 structural non-break after B1 D1 confirmation."""
from dataclasses import dataclass
from decimal import Decimal

from .b1_decline499 import B1Preview499
from .b1_market507 import B1MarketPlan507,inspect_b1_market507_preview
from .causal_structure_geometry import _eligible,_sequence,_source_identity,_cross_tf_identity
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1MajorPlan508:
    prior: B1MarketPlan507
    early_variant: str
    weekly_target_index: int


@dataclass(frozen=True)
class B1MajorIngredient508:
    state: S1State439
    reason: str
    private_rf: object
    private_weekly_floor: Decimal | None = None


def _validate508(p,variant_id):
    if type(p) is not B1MajorPlan508 or type(p.prior) is not B1MarketPlan507:
        raise ValueError("MST_508_EXACT_MAJOR_PLAN")
    if variant_id!="B1/F_MAJOR_REVERSAL_PENDING" or p.early_variant not in ("B1/E_RECLAIM","B1/E_BOS_UP"):
        raise ValueError("MST_508_EXPLICIT_MAJOR_AND_EARLY_VARIANT")
    if type(p.weekly_target_index) is not int or not 0<=p.weekly_target_index<512:
        raise ValueError("MST_508_EXACT_WEEKLY_TARGET")


def _weekly508(inputs,p,rf):
    g=p.prior.prior.prior.geometry
    context=g.early.context.context.context
    w=context.weekly
    rows=inputs.snapshots_for(Timeframe.W1)
    i=p.weekly_target_index
    if i>=len(rows):
        return B1MajorIngredient508(S1State439.MISSING,"MAJOR_W1_TARGET_MISSING",rf)
    if i<w.stop:
        return B1MajorIngredient508(S1State439.BLOCKED,"MAJOR_W1_NOT_LATER",rf)
    target=_eligible(rows[i],cutoff=inputs.as_of_utc)
    d1=inputs.snapshots_for(Timeframe.D1)[g.target_index].selected
    if target is None or target.market_bar_key.bar_start_utc<d1.verified_at_utc:
        return B1MajorIngredient508(S1State439.BLOCKED,"MAJOR_W1_NOT_CAUSAL_AFTER_D1",rf)
    prior=rows[w.start+w.low_indices[-1]].selected
    path,_=_sequence(rows[w.stop:i+1],cutoff=target.verified_at_utc)
    if not path or _source_identity(prior)!=_source_identity(target) or _cross_tf_identity(d1)!=_cross_tf_identity(target):
        return B1MajorIngredient508(S1State439.BLOCKED,"MAJOR_W1_SOURCE_OR_PATH",rf)
    floor=prior.low
    state=S1State439.NONMATCH if any(b.low<floor for b in path) else S1State439.MATCH
    return B1MajorIngredient508(state,"W1_NO_NEW_STRUCTURAL_LOW_CANDIDATE_ONLY",rf,floor)


def inspect_b1_major508_preview(inputs,*,strategy,variant_id,plan):
    _validate508(plan,variant_id)
    preview=inspect_b1_market507_preview(inputs,strategy=strategy,variant_id=plan.early_variant,plan=plan.prior)
    a=preview.assessments
    if len(a)==4 and all(p.state is S1State439.MATCH for _,p in a):
        a=a[:-1]+((a[-1][0],_weekly508(inputs,plan,a[-1][1])),)
    return B1Preview499(tuple((route_phase_inputs(inputs,zone_id="B1",strategy=strategy,
        variant_id=variant_id,phase=route.phase),proof) for route,proof in a))
