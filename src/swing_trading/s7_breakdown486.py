"""§486 S7 exact causal prior breakdown event candidate, never event approval."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .causal_structure_geometry import (
    GeometryState,StructureSide,TiePolicy,_eligible,_sequence,_source_identity,_cross_tf_identity,inspect_causal_pivot,
)
from .contracts import DecisionStatus,Strategy
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_context_preview439 import S1State439
from .s1_failed_break441 import validate_pair_atr442
from .s5_transition473 import _identity473
from .s7_retest_evidence import S7EarlyMode


@dataclass(frozen=True)
class S7BreakdownPlan486:
    timeframe: Timeframe
    history_start: int
    target_index: int
    pivot_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None
    event_id: str
    revision_digest: str
    bar_start_utc: datetime
    event_known_at_utc: datetime
    pivot_price: Decimal


@dataclass(frozen=True)
class S7Ingredient486:
    state: S1State439
    reason: str
    private_pivot: Decimal | None = None
    private_event_id: str | None = None
    private_event_start: datetime | None = None
    private_event_known: datetime | None = None


@dataclass(frozen=True)
class S7Preview486:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _validate486(p):
    if type(p) is not S7BreakdownPlan486:
        raise ValueError("MST_486_EXACT_BREAKDOWN_PLAN")
    validate_pair_atr442(p,frames=(Timeframe.D1,Timeframe.H1))
    if any(type(v) is not int for v in (p.history_start,p.pivot_index,p.left_count,p.right_count)):
        raise ValueError("MST_486_EXACT_PIVOT_INDICES")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_486_EXPLICIT_PIVOT_POLICY")
    if not 0<=p.history_start or not p.left_count<=p.pivot_index or not p.history_start+p.pivot_index+p.right_count<p.target_index-1:
        raise ValueError("MST_486_PRIOR_CAUSAL_PIVOT")
    if type(p.pivot_price) is not Decimal or not p.pivot_price.is_finite() or p.pivot_price<=0:
        raise ValueError("MST_486_EXACT_PIVOT_PRICE")
    if any(type(v) is not str or not v.strip() for v in (p.event_id,p.revision_digest)):
        raise ValueError("MST_486_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.bar_start_utc,p.event_known_at_utc)):
        raise ValueError("MST_486_EXACT_EVENT_CLOCK")
    require_utc(p.bar_start_utc)
    require_utc(p.event_known_at_utc)


def _path486(inputs,p,target):
    rows=inputs.snapshots_for(p.timeframe)
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not path or _source_identity(path[0])!=_source_identity(target):
        return None,None
    history=rows[p.history_start:p.target_index-1]
    pivot=inspect_causal_pivot(history,candidate_index=p.pivot_index,side=StructureSide.LOW,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=path[-1].market_bar_key.bar_start_utc)
    return path,pivot


def _cross486(inputs,p,target,path,pivot):
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return S7Ingredient486(S1State439.BLOCKED,"BREAKDOWN_PIVOT_UNRESOLVED")
    if pivot.geometric_extremum is not True or pivot.pivot_price!=p.pivot_price:
        return S7Ingredient486(S1State439.NONMATCH,"BREAKDOWN_PIVOT_NOT_EXACT")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return S7Ingredient486(S1State439.BLOCKED,"BREAKDOWN_ATR_UNRESOLVED")
    return _geometry486(p,target,path,atr)


def _geometry486(p,target,path,atr):
    if path[-1].close<p.pivot_price or target.close>=p.pivot_price:
        state=S1State439.NONMATCH
    elif p.candidate_epsilon is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if target.close<p.pivot_price-p.candidate_epsilon*atr else S1State439.NONMATCH
    return S7Ingredient486(state,"EXACT_PRIOR_CLOSED_BREAKDOWN_CANDIDATE_ONLY",
        p.pivot_price,p.event_id,p.bar_start_utc,p.event_known_at_utc)


def _r0486(inputs,p):
    rows=inputs.snapshots_for(p.timeframe)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S7Ingredient486(S1State439.MISSING,"BREAKDOWN_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or not _identity473(p,target,inputs.as_of_utc):
        return S7Ingredient486(S1State439.BLOCKED,"BREAKDOWN_IDENTITY_OR_CLOCK_UNRESOLVED")
    path,pivot=_path486(inputs,p,target)
    if path is None:
        return S7Ingredient486(S1State439.BLOCKED,"BREAKDOWN_HISTORY_NOT_CAUSAL")
    return _cross486(inputs,p,target,path,pivot)


def inspect_s7_breakdown_preview(inputs,*,strategy,variant_id,plan):
    _validate486(plan)
    if type(strategy) is not Strategy or variant_id not in ("S7/F_MICRO_BREAK","S7/F_CONTINUATION"):
        raise ValueError("MST_486_EXACT_SCOPE")
    route=route_phase_inputs(inputs,zone_id="S7",strategy=strategy,variant_id=variant_id,phase="R0",selected_frame=plan.timeframe)
    return S7Preview486(((route,_r0486(inputs,plan)),))


@dataclass(frozen=True)
class S7RetestPlan487:
    breakdown: S7BreakdownPlan486
    history_start: int
    target_index: int
    atr_start: int
    atr_stop: int
    candidate_max_sessions: int | None
    candidate_near_atr: Decimal | None


@dataclass(frozen=True)
class S7RetestIngredient487:
    state: S1State439
    reason: str
    private_pivot: Decimal | None = None
    private_event_id: str | None = None
    private_sessions: int | None = None
    private_range_distance_atr: Decimal | None = None
    private_close_distance_atr: Decimal | None = None
    private_target_start: datetime | None = None


def _validate487(p):
    if type(p) is not S7RetestPlan487 or type(p.breakdown) is not S7BreakdownPlan486:
        raise ValueError("MST_487_EXACT_RETEST_PLAN")
    if any(type(v) is not int for v in (p.history_start,p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_487_EXACT_INDICES")
    if not 0<=p.history_start<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512:
        raise ValueError("MST_487_BOUNDED_WINDOWS")
    if p.atr_stop-p.atr_start<15:
        raise ValueError("MST_487_ATR_WARMUP")
    n,k=p.candidate_max_sessions,p.candidate_near_atr
    if n is not None and (type(n) is not int or not 1<=n<=15):
        raise ValueError("MST_487_EXPLICIT_CANDIDATE_SESSION_WINDOW")
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_487_EXPLICIT_NEAR_THRESHOLD")


def _path487(inputs,p,target):
    rows=inputs.snapshots_for(Timeframe.M15)
    known=p.breakdown.event_known_at_utc
    if any(s.market_bar_key.bar_start_utc>=known for s in rows[:p.history_start]):
        return None
    bars,_=_sequence(rows[p.history_start:p.target_index+1],cutoff=target.verified_at_utc)
    origin=inputs.snapshots_for(p.breakdown.timeframe)[p.breakdown.target_index].selected
    if not bars or bars[0].market_bar_key.bar_start_utc<known:
        return None
    if _cross_tf_identity(bars[0])!=_cross_tf_identity(origin):
        return None
    if any(a.verified_at_utc>b.market_bar_key.bar_start_utc for a,b in zip(bars,bars[1:])):
        return None
    return bars


def _sessions487(bars):
    seen=set()
    previous=None
    for bar in bars:
        sid=bar.market_bar_key.session_period_id
        if sid!=previous:
            if sid in seen:
                return None
            seen.add(sid)
            previous=sid
    return len(seen)


def _geometry487(p,target,path,proof,atr,n):
    pivot=proof.private_pivot
    if path[-2].close>=pivot or any(b.close>=pivot for b in path[:-1]):
        return S7RetestIngredient487(S1State439.NONMATCH,"RETEST_NOT_FROM_BELOW")
    distance=max(target.low-pivot,Decimal(0),pivot-target.high)/atr
    close_distance=abs(target.close-pivot)/atr
    if p.candidate_max_sessions is not None and n>p.candidate_max_sessions:
        state=S1State439.NONMATCH
    elif p.candidate_max_sessions is None or p.candidate_near_atr is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if distance<=p.candidate_near_atr else S1State439.NONMATCH
    return S7RetestIngredient487(state,"OBSERVED_SESSION_RANGE_NEAR_CANDIDATE_ONLY",
        pivot,proof.private_event_id,n,distance,close_distance,target.market_bar_key.bar_start_utc)


def _retest487(inputs,p,proof):
    if proof.state is not S1State439.MATCH:
        return S7RetestIngredient487(S1State439.BLOCKED,"BREAKDOWN_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S7RetestIngredient487(S1State439.MISSING,"RETEST_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S7RetestIngredient487(S1State439.BLOCKED,"RETEST_TARGET_UNQUALIFIED")
    path=_path487(inputs,p,target)
    if path is None:
        return S7RetestIngredient487(S1State439.BLOCKED,"RETEST_PATH_NOT_CAUSAL")
    n=_sessions487(path)
    atr=inspect_target_d1_atr(inputs,p,target)
    if n is None or atr is None or atr<=0:
        return S7RetestIngredient487(S1State439.BLOCKED,"RETEST_SESSIONS_OR_ATR_UNRESOLVED")
    return _geometry487(p,target,path,proof,atr,n)


def inspect_s7_retest487_preview(inputs,*,strategy,variant_id,plan):
    _validate487(plan)
    preview=inspect_s7_breakdown_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.breakdown)
    route=route_phase_inputs(inputs,zone_id="S7",strategy=strategy,variant_id=variant_id,phase="R_C")
    return S7Preview486(preview.assessments+((route,_retest487(inputs,plan,preview.assessments[0][1])),))


@dataclass(frozen=True)
class S7EarlyPlan488:
    retest: S7RetestPlan487
    mode: S7EarlyMode
    target_index: int
    expires_at_utc: datetime
    policy_known_at_utc: datetime


@dataclass(frozen=True)
class S7EarlyIngredient488:
    state: S1State439
    reason: str
    private_pivot: Decimal | None = None
    private_event_id: str | None = None
    private_early_known: datetime | None = None
    private_mode: S7EarlyMode | None = None


def _validate488(p):
    if type(p) is not S7EarlyPlan488 or type(p.retest) is not S7RetestPlan487:
        raise ValueError("MST_488_EXACT_EARLY_PLAN")
    _validate487(p.retest)
    if type(p.mode) is not S7EarlyMode or type(p.target_index) is not int:
        raise ValueError("MST_488_EXPLICIT_SHAPE_AND_INDEX")
    offset=0 if p.mode is S7EarlyMode.TOUCH_CLOSE_BELOW else 1
    if p.target_index!=p.retest.target_index+offset or p.target_index>=512:
        raise ValueError("MST_488_EXACT_RETEST_OR_NEXT_OBSERVED")
    if any(type(v) is not datetime for v in (p.expires_at_utc,p.policy_known_at_utc)):
        raise ValueError("MST_488_EXPLICIT_HYPOTHETICAL_CLOCK")
    require_utc(p.expires_at_utc)
    require_utc(p.policy_known_at_utc)
    if p.policy_known_at_utc>p.retest.breakdown.bar_start_utc or p.expires_at_utc<=p.policy_known_at_utc:
        raise ValueError("MST_488_POLICY_NOT_CAUSAL")


def _shape488(p,target,retest,rc):
    pivot=rc.private_pivot
    if p.mode is S7EarlyMode.TOUCH_CLOSE_BELOW:
        matched=target.high>=pivot and target.close<pivot
    else:
        matched=retest.close>pivot and target.close<pivot
    return S7EarlyIngredient488(S1State439.MATCH if matched else S1State439.NONMATCH,
        "EXACT_M15_CLOSED_REJECTION_CANDIDATE_ONLY",pivot,rc.private_event_id,
        target.verified_at_utc,p.mode)


def _early488(inputs,p,rc):
    if rc.state is not S1State439.MATCH:
        return S7EarlyIngredient488(S1State439.BLOCKED,"R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return S7EarlyIngredient488(S1State439.MISSING,"EARLY_BAR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or target.verified_at_utc>p.expires_at_utc:
        return S7EarlyIngredient488(S1State439.BLOCKED,"EARLY_TARGET_OR_EXPIRY_UNRESOLVED")
    retest=rows[p.retest.target_index].selected
    if p.mode is S7EarlyMode.LATER_CLOSE_BELOW:
        if (_eligible(rows[p.retest.target_index],cutoff=target.market_bar_key.bar_start_utc) is None
                or _source_identity(retest)!=_source_identity(target)):
            return S7EarlyIngredient488(S1State439.BLOCKED,"EARLY_FOLLOWUP_NOT_CAUSAL")
    return _shape488(p,target,retest,rc)


def inspect_s7_early488_preview(inputs,*,strategy,variant_id,plan):
    _validate488(plan)
    preview=inspect_s7_retest487_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.retest)
    route=route_phase_inputs(inputs,zone_id="S7",strategy=strategy,variant_id=variant_id,phase="R_E")
    return S7Preview486(preview.assessments+((route,_early488(inputs,plan,preview.assessments[1][1])),))
