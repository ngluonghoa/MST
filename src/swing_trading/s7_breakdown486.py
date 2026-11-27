"""§486 S7 exact causal prior breakdown event candidate, never event approval."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .causal_structure_geometry import (
    GeometryState,StructureSide,TiePolicy,_eligible,_sequence,_source_identity,inspect_causal_pivot,
)
from .contracts import DecisionStatus,Strategy
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_context_preview439 import S1State439
from .s1_failed_break441 import validate_pair_atr442
from .s5_transition473 import _identity473


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


def inspect_s6_breakdown_preview(inputs,*,strategy,variant_id,plan):
    _validate486(plan)
    if type(strategy) is not Strategy or variant_id not in ("S7/F_MICRO_BREAK","S7/F_CONTINUATION"):
        raise ValueError("MST_486_EXACT_SCOPE")
    route=route_phase_inputs(inputs,zone_id="S7",strategy=strategy,variant_id=variant_id,phase="R0",selected_frame=plan.timeframe)
    return S7Preview486(((route,_r0486(inputs,plan)),))
