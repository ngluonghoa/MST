"""§503 B1 explicit M15 BOS_UP candidate, separate from reclaim."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .b1_bottom500 import B1SupportPlan501,inspect_b1_support501_preview
from .b1_decline499 import B1Preview499
from .causal_structure_geometry import GeometryState,StructureSide,TiePolicy,inspect_causal_pivot,_eligible,_sequence,_source_identity,_cross_tf_identity
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1BosUpPlan503:
    context: B1SupportPlan501
    history_start: int
    target_index: int
    high_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    event_id: str
    event_revision: str
    event_known_at_utc: datetime
    expires_at_utc: datetime
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class B1BosUpIngredient503:
    state: S1State439
    reason: str
    private_support: Decimal | None = None
    private_event_id: str | None = None
    private_early_known: datetime | None = None
    private_micro_high: Decimal | None = None


def _validate_geometry503(p):
    indices=(p.history_start,p.target_index,p.high_index,p.left_count,p.right_count,p.atr_start,p.atr_stop)
    if any(type(i) is not int for i in indices):
        raise ValueError("MST_503_EXACT_INDICES")
    if not 0<=p.history_start<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512 or p.atr_stop-p.atr_start<15:
        raise ValueError("MST_503_EXPLICIT_WINDOWS")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_503_EXPLICIT_PIVOT_POLICY")
    if not p.left_count<=p.high_index or p.history_start+p.high_index+p.right_count>=p.target_index-1:
        raise ValueError("MST_503_DISTINCT_PIVOT_WITNESS")
    k=p.candidate_epsilon
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_503_EXPLICIT_EPSILON")


def _validate503(p,variant):
    if type(p) is not B1BosUpPlan503 or type(p.context) is not B1SupportPlan501 or variant!="B1/E_BOS_UP":
        raise ValueError("MST_503_EXACT_BOS_PLAN_AND_VARIANT")
    _validate_geometry503(p)
    if any(type(v) is not str or not v.strip() for v in (p.event_id,p.event_revision)):
        raise ValueError("MST_503_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.event_known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_503_EXPLICIT_UTC_CLOCKS")
    require_utc(p.event_known_at_utc)
    require_utc(p.expires_at_utc)
    if p.event_known_at_utc>=p.expires_at_utc:
        raise ValueError("MST_503_EXPIRY_ORDER")


def _path503(inputs,p,target,origin):
    rows=inputs.snapshots_for(Timeframe.M15)
    if any(s.market_bar_key.bar_start_utc>=origin.verified_at_utc for s in rows[:p.history_start]):
        return None
    bars,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not bars or bars[0].market_bar_key.bar_start_utc<origin.verified_at_utc:
        return None
    if _source_identity(bars[0])!=_source_identity(target) or _cross_tf_identity(origin)!=_cross_tf_identity(target):
        return None
    if any(a.verified_at_utc>b.market_bar_key.bar_start_utc for a,b in zip(bars,bars[1:])):
        return None
    return bars


def _cross503(inputs,p,target,path,rc,high):
    support=rc.private_support
    if any(b.close<support for b in (*path,target)):
        return B1BosUpIngredient503(S1State439.NONMATCH,"SUPPORT_CLOSED_BREAK_INVALIDATION")
    if any(b.close>high for b in path[p.high_index+p.right_count+1:]) or target.close<=high:
        return B1BosUpIngredient503(S1State439.NONMATCH,"NO_FIRST_LATER_CLOSED_HIGH_CROSS")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return B1BosUpIngredient503(S1State439.BLOCKED,"BOS_ATR_UNRESOLVED")
    k=p.candidate_epsilon
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if target.close>high+k*atr else S1State439.NONMATCH
    return B1BosUpIngredient503(state,"M15_CLOSED_BOS_UP_CANDIDATE_ONLY",
        support,p.event_id,target.verified_at_utc,high)


def _shape503(inputs,p,target,path,rc):
    if (p.event_id not in target.source_event_ids
            or p.event_revision!=target.observation_revision.source_revision_or_payload_digest
            or p.event_known_at_utc!=target.verified_at_utc
            or target.verified_at_utc>p.expires_at_utc):
        return B1BosUpIngredient503(S1State439.BLOCKED,"BOS_EVENT_ID_REVISION_OR_CLOCK")
    rows=inputs.snapshots_for(Timeframe.M15)
    pivot=inspect_causal_pivot(rows[p.history_start:p.target_index-1],candidate_index=p.high_index,
        side=StructureSide.HIGH,left_count=p.left_count,right_count=p.right_count,
        tie_policy=p.tie_policy,as_of_utc=path[-1].market_bar_key.bar_start_utc)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return B1BosUpIngredient503(S1State439.BLOCKED,"BOS_HIGH_NOT_CAUSAL")
    if pivot.geometric_extremum is not True or pivot.pivot_price<=rc.private_support:
        return B1BosUpIngredient503(S1State439.NONMATCH,"BOS_HIGH_NOT_STRUCTURAL")
    return _cross503(inputs,p,target,path,rc,pivot.pivot_price)


def _early503(inputs,p,rc):
    if rc.state is not S1State439.MATCH:
        return B1BosUpIngredient503(S1State439.BLOCKED,"R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return B1BosUpIngredient503(S1State439.MISSING,"BOS_TARGET_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return B1BosUpIngredient503(S1State439.BLOCKED,"BOS_TARGET_UNQUALIFIED")
    origin=inputs.snapshots_for(Timeframe.D1)[p.context.target_index].selected
    path=_path503(inputs,p,target,origin)
    if path is None:
        return B1BosUpIngredient503(S1State439.BLOCKED,"BOS_PATH_NOT_CAUSAL")
    return _shape503(inputs,p,target,path,rc)


def inspect_b1_bos_up503_preview(inputs,*,strategy,variant_id,plan):
    _validate503(plan,variant_id)
    preview=inspect_b1_support501_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route=route_phase_inputs(inputs,zone_id="B1",strategy=strategy,variant_id=variant_id,phase="R_E")
    return B1Preview499(preview.assessments+((route,_early503(inputs,plan,preview.assessments[-1][1])),))
