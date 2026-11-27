"""§479 S6 exact causal prior breakout event candidate, never event approval."""
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
class S6BreakoutPlan479:
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
class S6Ingredient479:
    state: S1State439
    reason: str
    private_pivot: Decimal | None = None
    private_event_id: str | None = None
    private_event_start: datetime | None = None
    private_event_known: datetime | None = None


@dataclass(frozen=True)
class S6Preview479:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _validate479(p):
    if type(p) is not S6BreakoutPlan479:
        raise ValueError("MST_479_EXACT_BREAKOUT_PLAN")
    validate_pair_atr442(p,frames=(Timeframe.D1,Timeframe.H1))
    if any(type(v) is not int for v in (p.history_start,p.pivot_index,p.left_count,p.right_count)):
        raise ValueError("MST_479_EXACT_PIVOT_INDICES")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_479_EXPLICIT_PIVOT_POLICY")
    if not 0<=p.history_start or not p.left_count<=p.pivot_index or not p.history_start+p.pivot_index+p.right_count<p.target_index-1:
        raise ValueError("MST_479_PRIOR_CAUSAL_PIVOT")
    if type(p.pivot_price) is not Decimal or not p.pivot_price.is_finite() or p.pivot_price<=0:
        raise ValueError("MST_479_EXACT_PIVOT_PRICE")
    if any(type(v) is not str or not v.strip() for v in (p.event_id,p.revision_digest)):
        raise ValueError("MST_479_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.bar_start_utc,p.event_known_at_utc)):
        raise ValueError("MST_479_EXACT_EVENT_CLOCK")
    require_utc(p.bar_start_utc)
    require_utc(p.event_known_at_utc)


def _path479(inputs,p,target):
    rows=inputs.snapshots_for(p.timeframe)
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not path or _source_identity(path[0])!=_source_identity(target):
        return None,None
    history=rows[p.history_start:p.target_index-1]
    pivot=inspect_causal_pivot(history,candidate_index=p.pivot_index,side=StructureSide.HIGH,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=path[-1].market_bar_key.bar_start_utc)
    return path,pivot


def _cross479(inputs,p,target,path,pivot):
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return S6Ingredient479(S1State439.BLOCKED,"BREAKOUT_PIVOT_UNRESOLVED")
    if pivot.geometric_extremum is not True or pivot.pivot_price!=p.pivot_price:
        return S6Ingredient479(S1State439.NONMATCH,"BREAKOUT_PIVOT_NOT_EXACT")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return S6Ingredient479(S1State439.BLOCKED,"BREAKOUT_ATR_UNRESOLVED")
    return _geometry479(p,target,path,atr)


def _geometry479(p,target,path,atr):
    if path[-1].close>p.pivot_price or target.close<=p.pivot_price:
        state=S1State439.NONMATCH
    elif p.candidate_epsilon is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if target.close>p.pivot_price+p.candidate_epsilon*atr else S1State439.NONMATCH
    return S6Ingredient479(state,"EXACT_PRIOR_CLOSED_BREAKOUT_CANDIDATE_ONLY",
        p.pivot_price,p.event_id,p.bar_start_utc,p.event_known_at_utc)


def _r0479(inputs,p):
    rows=inputs.snapshots_for(p.timeframe)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S6Ingredient479(S1State439.MISSING,"BREAKOUT_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or not _identity473(p,target,inputs.as_of_utc):
        return S6Ingredient479(S1State439.BLOCKED,"BREAKOUT_IDENTITY_OR_CLOCK_UNRESOLVED")
    path,pivot=_path479(inputs,p,target)
    if path is None:
        return S6Ingredient479(S1State439.BLOCKED,"BREAKOUT_HISTORY_NOT_CAUSAL")
    return _cross479(inputs,p,target,path,pivot)


def inspect_s6_breakout_preview(inputs,*,strategy,variant_id,plan):
    _validate479(plan)
    if type(strategy) is not Strategy or variant_id!="S6/BASE":
        raise ValueError("MST_479_EXACT_SCOPE")
    route=route_phase_inputs(inputs,zone_id="S6",strategy=strategy,variant_id=variant_id,phase="R0")
    return S6Preview479(((route,_r0479(inputs,plan)),))

@dataclass(frozen=True)
class S6FailurePlan480:
    breakout: S6BreakoutPlan479
    failure_index: int
    candidate_max_bars: int | None


@dataclass(frozen=True)
class S6FailureIngredient480:
    state: S1State439
    reason: str
    private_pivot: Decimal | None = None
    private_event_id: str | None = None
    private_failure_start: datetime | None = None
    private_failure_known: datetime | None = None
    private_supplied_bars: int | None = None


def _validate480(p):
    if type(p) is not S6FailurePlan480 or type(p.breakout) is not S6BreakoutPlan479:
        raise ValueError("MST_480_EXACT_FAILURE_PLAN")
    _validate479(p.breakout)
    if type(p.failure_index) is not int or not p.breakout.target_index<p.failure_index<512:
        raise ValueError("MST_480_DISTINCT_LATER_FAILURE")
    n=p.candidate_max_bars
    limit=3 if p.breakout.timeframe is Timeframe.D1 else 6
    if n is not None and (type(n) is not int or not 1<=n<=limit):
        raise ValueError("MST_480_EXPLICIT_CANDIDATE_WINDOW")


def _path480(inputs,p,target):
    b=p.breakout
    rows=inputs.snapshots_for(b.timeframe)
    bars,_=_sequence(rows[b.target_index:p.failure_index+1],cutoff=target.verified_at_utc)
    if not bars or len(bars)<2:
        return None
    if b.event_known_at_utc>bars[1].market_bar_key.bar_start_utc:
        return None
    for previous,current in zip(bars,bars[1:]):
        if previous.verified_at_utc>current.market_bar_key.bar_start_utc:
            return None
    return bars


def _shape480(p,target,bars,base):
    pivot=base.private_pivot
    elapsed=p.failure_index-p.breakout.target_index
    if any(b.close<=pivot for b in bars[1:-1]) or target.close>pivot:
        state=S1State439.NONMATCH
    elif p.candidate_max_bars is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if elapsed<=p.candidate_max_bars else S1State439.NONMATCH
    return S6FailureIngredient480(state,"FIRST_SUPPLIED_FAILURE_TO_HOLD_PIVOT_CANDIDATE_ONLY",
        pivot,base.private_event_id,target.market_bar_key.bar_start_utc,target.verified_at_utc,elapsed)


def _failure480(inputs,p,base):
    if base.state is not S1State439.MATCH:
        return S6FailureIngredient480(S1State439.BLOCKED,"BREAKOUT_NOT_MATCHED")
    rows=inputs.snapshots_for(p.breakout.timeframe)
    if p.failure_index>=len(rows):
        return S6FailureIngredient480(S1State439.MISSING,"FAILURE_BAR_MISSING")
    target=_eligible(rows[p.failure_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S6FailureIngredient480(S1State439.BLOCKED,"FAILURE_BAR_UNQUALIFIED")
    bars=_path480(inputs,p,target)
    if bars is None:
        return S6FailureIngredient480(S1State439.BLOCKED,"FAILURE_PATH_NOT_CAUSAL")
    return _shape480(p,target,bars,base)


def inspect_s6_failure_preview(inputs,*,strategy,variant_id,plan):
    _validate480(plan)
    preview=inspect_s6_breakout_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.breakout)
    route=route_phase_inputs(inputs,zone_id="S6",strategy=strategy,variant_id=variant_id,phase="R_C")
    return S6Preview479(preview.assessments+((route,_failure480(inputs,plan,preview.assessments[0][1])),))
