"""§502 B1 explicit M15 false breakdown/reclaim candidate."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .b1_bottom500 import B1SupportPlan501,inspect_b1_support501_preview
from .b1_decline499 import B1Preview499
from .causal_structure_geometry import _eligible,_sequence,_source_identity,_cross_tf_identity
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1ReclaimPlan502:
    context: B1SupportPlan501
    breach_index: int
    target_index: int
    event_id: str
    event_revision: str
    event_known_at_utc: datetime
    expires_at_utc: datetime
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class B1ReclaimIngredient502:
    state: S1State439
    reason: str
    private_support: Decimal | None = None
    private_event_id: str | None = None
    private_early_known: datetime | None = None


def _validate502(p,variant):
    if type(p) is not B1ReclaimPlan502 or type(p.context) is not B1SupportPlan501 or variant!="B1/E_RECLAIM":
        raise ValueError("MST_502_EXACT_RECLAIM_PLAN_AND_VARIANT")
    if any(type(i) is not int for i in (p.breach_index,p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_502_EXACT_INDICES")
    if not 1<=p.breach_index<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512 or p.atr_stop-p.atr_start<15:
        raise ValueError("MST_502_EXPLICIT_WINDOWS")
    if any(type(v) is not str or not v.strip() for v in (p.event_id,p.event_revision)):
        raise ValueError("MST_502_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.event_known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_502_EXPLICIT_UTC_CLOCKS")
    require_utc(p.event_known_at_utc)
    require_utc(p.expires_at_utc)
    if p.event_known_at_utc>=p.expires_at_utc:
        raise ValueError("MST_502_EXPIRY_ORDER")
    k=p.candidate_epsilon
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_502_EXPLICIT_EPSILON")


def _path502(inputs,p,target,origin):
    rows=inputs.snapshots_for(Timeframe.M15)
    start=next((i for i,s in enumerate(rows[:p.breach_index])
                if s.market_bar_key.bar_start_utc>=origin.verified_at_utc),None)
    if start is None:
        return None
    bars,_=_sequence(rows[start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not bars or _source_identity(bars[0])!=_source_identity(target):
        return None
    if _cross_tf_identity(origin)!=_cross_tf_identity(target):
        return None
    if any(a.verified_at_utc>b.market_bar_key.bar_start_utc for a,b in zip(bars,bars[1:])):
        return None
    return bars,p.breach_index-start


def _shape502(inputs,p,target,path,rc):
    bars,i=path
    breach=bars[i]
    if (p.event_id not in breach.source_event_ids
            or p.event_revision!=breach.observation_revision.source_revision_or_payload_digest
            or p.event_known_at_utc!=breach.verified_at_utc
            or target.verified_at_utc>p.expires_at_utc):
        return B1ReclaimIngredient502(S1State439.BLOCKED,"RECLAIM_EVENT_ID_REVISION_OR_CLOCK")
    support=rc.private_support
    if any(b.close<support for b in bars[:i]) or any(b.close>=support for b in bars[i:]) or target.close<=support:
        state=S1State439.NONMATCH
    else:
        atr=inspect_target_d1_atr(inputs,p,target)
        if atr is None or atr<=0:
            return B1ReclaimIngredient502(S1State439.BLOCKED,"RECLAIM_ATR_UNRESOLVED")
        k=p.candidate_epsilon
        state=S1State439.DISTANCE if k is None else S1State439.MATCH if target.close>support+k*atr else S1State439.NONMATCH
    return B1ReclaimIngredient502(state,"FIRST_SUPPLIED_CLOSED_M15_RECLAIM_CANDIDATE_ONLY",
                                  support,p.event_id,target.verified_at_utc)


def _early502(inputs,p,rc):
    if rc.state is not S1State439.MATCH:
        return B1ReclaimIngredient502(S1State439.BLOCKED,"R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return B1ReclaimIngredient502(S1State439.MISSING,"RECLAIM_TARGET_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return B1ReclaimIngredient502(S1State439.BLOCKED,"RECLAIM_TARGET_UNQUALIFIED")
    origin=inputs.snapshots_for(Timeframe.D1)[p.context.target_index].selected
    path=_path502(inputs,p,target,origin)
    if path is None:
        return B1ReclaimIngredient502(S1State439.BLOCKED,"RECLAIM_PATH_NOT_CAUSAL")
    return _shape502(inputs,p,target,path,rc)


def inspect_b1_reclaim502_preview(inputs,*,strategy,variant_id,plan):
    _validate502(plan,variant_id)
    preview=inspect_b1_support501_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route=route_phase_inputs(inputs,zone_id="B1",strategy=strategy,variant_id=variant_id,phase="R_E")
    return B1Preview499(preview.assessments+((route,_early502(inputs,plan,preview.assessments[-1][1])),))
