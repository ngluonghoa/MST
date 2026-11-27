"""§473 S5 prior rising structure and explicit bearish transition candidate."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .causal_structure_geometry import (
    GeometryState,StructureSide,TiePolicy,_eligible,_sequence,_source_identity,
    _cross_tf_identity,inspect_causal_pivot,
)
from .contracts import DecisionStatus,Strategy
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_choch442 import _validate_pivots442,_pivots442
from .s1_failed_break441 import validate_pair_atr442
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class S5TransitionPlan473:
    timeframe: Timeframe
    history_start: int
    target_index: int
    high_indices: tuple[int,int]
    low_indices: tuple[int,int]
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


@dataclass(frozen=True)
class S5Ingredient473:
    state: S1State439
    reason: str
    private_prior_high: Decimal | None = None
    private_prior_hl: Decimal | None = None
    private_event_id: str | None = None
    private_event_start: datetime | None = None


@dataclass(frozen=True)
class S5Preview473:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _validate473(p):
    if type(p) is not S5TransitionPlan473:
        raise ValueError("MST_473_EXPLICIT_TRANSITION")
    validate_pair_atr442(p,frames=(Timeframe.D1,Timeframe.H1))
    if type(p.history_start) is not int or not 0<=p.history_start<p.target_index-1:
        raise ValueError("MST_473_BOUNDED_HISTORY")
    _validate_pivots442(p,p.target_index-1-p.history_start)
    if any(type(v) is not str or not v.strip() for v in (p.event_id,p.revision_digest)):
        raise ValueError("MST_473_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.bar_start_utc,p.event_known_at_utc)):
        raise ValueError("MST_473_EXACT_EVENT_CLOCK")
    require_utc(p.bar_start_utc)
    require_utc(p.event_known_at_utc)


def _identity473(p,bar,cutoff):
    return (p.bar_start_utc==bar.market_bar_key.bar_start_utc
            and bar.verified_at_utc<=p.event_known_at_utc<=cutoff
            and bar.source_event_ids.count(p.event_id)==1
            and p.revision_digest==bar.observation_revision.source_revision_or_payload_digest)


def _rising473(history,p,cutoff):
    h1,h2=p.high_indices
    l1,l2=p.low_indices
    if not (h1<l1<h2<l2 or l1<h1<l2<h2):
        return S5Ingredient473(S1State439.NONMATCH,"PRIOR_PAIRS_NOT_ALTERNATING")
    highs,lows=_pivots442(history,p,cutoff)
    if any(v.state is not GeometryState.DESCRIPTIVE_ONLY for v in highs+lows):
        return S5Ingredient473(S1State439.BLOCKED,"PRIOR_PIVOT_WITNESS_UNRESOLVED")
    if any(v.geometric_extremum is not True for v in highs+lows):
        return S5Ingredient473(S1State439.NONMATCH,"PRIOR_PIVOT_NOT_EXTREMUM")
    if not (highs[1].pivot_price>highs[0].pivot_price and lows[1].pivot_price>lows[0].pivot_price):
        return S5Ingredient473(S1State439.NONMATCH,"PRIOR_UPTREND_NOT_OBSERVED")
    return S5Ingredient473(S1State439.MATCH,"PRIOR_RISING_GEOMETRY_ONLY",
                           highs[1].pivot_price,lows[1].pivot_price)


def _context473(inputs,p,rows,bar):
    prior=_eligible(rows[p.target_index-1],cutoff=bar.market_bar_key.bar_start_utc)
    if prior is None:
        return None,None
    history=rows[p.history_start:p.target_index-1]
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=bar.market_bar_key.bar_start_utc)
    if not path or _source_identity(path[0])!=_source_identity(bar):
        return None,None
    proof=_rising473(history,p,prior.market_bar_key.bar_start_utc)
    return prior,proof


def _cross473(inputs,p,prior,bar,proof):
    atr=inspect_target_d1_atr(inputs,p,bar)
    if atr is None or atr<=0:
        return S5Ingredient473(S1State439.BLOCKED,"TRANSITION_ATR_UNRESOLVED")
    low=proof.private_prior_hl
    if prior.close<low or bar.close>=low:
        state=S1State439.NONMATCH
    elif p.candidate_epsilon is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if bar.close<low-p.candidate_epsilon*atr else S1State439.NONMATCH
    return S5Ingredient473(state,"CLOSED_BEARISH_TRANSITION_CANDIDATE_ONLY",
                           proof.private_prior_high,low,p.event_id,p.bar_start_utc)


def _r0473(inputs,p):
    rows=inputs.snapshots_for(p.timeframe)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S5Ingredient473(S1State439.MISSING,"TRANSITION_OR_ATR_MISSING")
    bar=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if bar is None or not _identity473(p,bar,inputs.as_of_utc):
        return S5Ingredient473(S1State439.BLOCKED,"TRANSITION_IDENTITY_OR_CLOCK_UNRESOLVED")
    prior,proof=_context473(inputs,p,rows,bar)
    if proof is None:
        return S5Ingredient473(S1State439.BLOCKED,"TRANSITION_HISTORY_NOT_CAUSAL")
    if proof.state is not S1State439.MATCH:
        return proof
    return _cross473(inputs,p,prior,bar,proof)


def inspect_s5_transition_preview(inputs,*,strategy,variant_id,plan):
    _validate473(plan)
    if type(strategy) is not Strategy or variant_id!="S5/BASE":
        raise ValueError("MST_473_EXACT_SCOPE")
    route=route_phase_inputs(inputs,zone_id="S5",strategy=strategy,variant_id=variant_id,
                             phase="R0",selected_frame=plan.timeframe)
    return S5Preview473(((route,_r0473(inputs,plan)),))


@dataclass(frozen=True)
class S5RallyPlan474:
    context: S5TransitionPlan473
    history_start: int
    low_index: int
    high_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class S5RallyIngredient474:
    state: S1State439
    reason: str
    private_prior_high: Decimal | None = None
    private_rally_low: Decimal | None = None
    private_rally_high: Decimal | None = None
    private_event_id: str | None = None
    private_witness_known: datetime | None = None


def _validate474(p):
    if type(p) is not S5RallyPlan474 or type(p.context) is not S5TransitionPlan473:
        raise ValueError("MST_474_EXACT_RALLY_PLAN")
    if any(type(v) is not int for v in (p.history_start,p.low_index,p.high_index,p.left_count,p.right_count)):
        raise ValueError("MST_474_EXACT_INDICES")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_474_EXACT_PIVOT_POLICY")
    if not 0<=p.history_start or not p.left_count<=p.low_index<p.high_index:
        raise ValueError("MST_474_EXACT_RALLY_ORDER")
    if p.history_start+p.high_index+p.right_count>=512:
        raise ValueError("MST_474_BOUNDED_WINDOW")


def _first474(history,p,side,start,stop,cutoff):
    for index in range(start,stop):
        pivot=inspect_causal_pivot(history,candidate_index=index,side=side,
            left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,as_of_utc=cutoff)
        if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
            return None,None
        if pivot.geometric_extremum is True:
            return index,pivot
    return None,None


def _path474(inputs,p,witness):
    rows=inputs.snapshots_for(Timeframe.M15)
    known=p.context.event_known_at_utc
    if any(s.market_bar_key.bar_start_utc>=known for s in rows[:p.history_start]):
        return None,None
    stop=p.history_start+p.high_index+p.right_count+1
    history=rows[p.history_start:stop]
    bars,_=_sequence(history,cutoff=witness.verified_at_utc)
    event=inputs.snapshots_for(p.context.timeframe)[p.context.target_index].selected
    if not bars or bars[0].market_bar_key.bar_start_utc<known:
        return None,None
    if _cross_tf_identity(bars[0])!=_cross_tf_identity(event):
        return None,None
    return history,bars


def _shape474(history,bars,p,base,witness):
    cutoff=witness.verified_at_utc
    li,low=_first474(history,p,StructureSide.LOW,p.left_count,p.low_index+1,cutoff)
    hi,high=_first474(history,p,StructureSide.HIGH,p.low_index+1,p.high_index+1,cutoff)
    if low is None or high is None:
        return S5RallyIngredient474(S1State439.NONMATCH,"FIRST_RALLY_PIVOT_NOT_OBSERVED")
    if li!=p.low_index or hi!=p.high_index:
        return S5RallyIngredient474(S1State439.NONMATCH,"EARLIER_SUPPLIED_PIVOT_EXISTS")
    if low.witness_known_at_utc>bars[hi].market_bar_key.bar_start_utc:
        return S5RallyIngredient474(S1State439.BLOCKED,"RALLY_LOW_NOT_KNOWN_BEFORE_HIGH")
    if any(b.high>=base.private_prior_high for b in bars) or high.pivot_price<=low.pivot_price:
        return S5RallyIngredient474(S1State439.NONMATCH,"PRIOR_HIGH_NOT_PRESERVED")
    return S5RallyIngredient474(S1State439.MATCH,"FIRST_SUPPLIED_FAILED_RALLY_CANDIDATE_ONLY",
        base.private_prior_high,low.pivot_price,high.pivot_price,p.context.event_id,high.witness_known_at_utc)


def _rally474(inputs,p,base):
    if base.state is not S1State439.MATCH:
        return S5RallyIngredient474(S1State439.BLOCKED,"TRANSITION_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    index=p.history_start+p.high_index+p.right_count
    if index>=len(rows):
        return S5RallyIngredient474(S1State439.MISSING,"RALLY_WITNESS_MISSING")
    witness=_eligible(rows[index],cutoff=inputs.as_of_utc)
    if witness is None:
        return S5RallyIngredient474(S1State439.BLOCKED,"RALLY_WITNESS_UNQUALIFIED")
    history,bars=_path474(inputs,p,witness)
    if history is None:
        return S5RallyIngredient474(S1State439.BLOCKED,"RALLY_PATH_NOT_CAUSAL_OR_FIRST_SUPPLIED")
    return _shape474(history,bars,p,base,witness)


def inspect_s5_rally_preview(inputs,*,strategy,variant_id,plan):
    _validate474(plan)
    preview=inspect_s5_transition_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route=route_phase_inputs(inputs,zone_id="S5",strategy=strategy,variant_id=variant_id,phase="R_C")
    return S5Preview473(preview.assessments+((route,_rally474(inputs,plan,preview.assessments[0][1])),))


@dataclass(frozen=True)
class S5EarlyPlan475:
    rally: S5RallyPlan474
    target_index: int
    atr_start: int
    atr_stop: int
    candidate_k_rejection: Decimal | None


@dataclass(frozen=True)
class S5EarlyIngredient475:
    state: S1State439
    reason: str
    private_rally_high: Decimal | None = None
    private_rally_low: Decimal | None = None
    private_event_id: str | None = None
    private_target_start: datetime | None = None
    private_distance: Decimal | None = None


def _validate475(p):
    if type(p) is not S5EarlyPlan475 or type(p.rally) is not S5RallyPlan474:
        raise ValueError("MST_475_EXACT_EARLY_PLAN")
    _validate474(p.rally)
    if any(type(i) is not int for i in (p.target_index,p.atr_start,p.atr_stop)):
        raise ValueError("MST_475_EXACT_INDICES")
    witness=p.rally.history_start+p.rally.high_index+p.rally.right_count
    if not witness<p.target_index<512 or not 0<=p.atr_start<p.atr_stop<=512:
        raise ValueError("MST_475_DISTINCT_LATER_TARGET")
    if p.atr_stop-p.atr_start<15:
        raise ValueError("MST_475_ATR_WARMUP")
    k=p.candidate_k_rejection
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_475_EXPLICIT_THRESHOLD")


def _path475(inputs,p,target,rc):
    rows=inputs.snapshots_for(Timeframe.M15)
    witness=p.rally.history_start+p.rally.high_index+p.rally.right_count
    cutoff=target.market_bar_key.bar_start_utc
    bars,_=_sequence(rows[witness:p.target_index],cutoff=cutoff)
    if not bars or _source_identity(bars[0])!=_source_identity(target):
        return None
    if rc.private_witness_known>cutoff:
        return None
    return bars


def _shape475(inputs,p,target,bars,rc):
    high=rc.private_rally_high
    if any(b.high>high for b in (*bars,target)):
        return S5EarlyIngredient475(S1State439.NONMATCH,"FIRST_LH_INVALIDATED")
    if target.close>=target.open or target.close>=bars[-1].close or target.close>=high:
        return S5EarlyIngredient475(S1State439.NONMATCH,"CLOSED_REJECTION_NOT_OBSERVED")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return S5EarlyIngredient475(S1State439.BLOCKED,"REJECTION_ATR_UNRESOLVED")
    distance=high-target.high
    k=p.candidate_k_rejection
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if distance<=k*atr else S1State439.NONMATCH
    return S5EarlyIngredient475(state,"FIRST_LH_CLOSED_REJECTION_CANDIDATE_ONLY",high,
        rc.private_rally_low,rc.private_event_id,target.market_bar_key.bar_start_utc,distance)


def _early475(inputs,p,rc):
    if rc.state is not S1State439.MATCH:
        return S5EarlyIngredient475(S1State439.BLOCKED,"R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S5EarlyIngredient475(S1State439.MISSING,"REJECTION_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None:
        return S5EarlyIngredient475(S1State439.BLOCKED,"REJECTION_TARGET_UNQUALIFIED")
    bars=_path475(inputs,p,target,rc)
    if bars is None:
        return S5EarlyIngredient475(S1State439.BLOCKED,"REJECTION_PATH_NOT_CAUSAL")
    return _shape475(inputs,p,target,bars,rc)


def inspect_s5_early_preview(inputs,*,strategy,variant_id,plan):
    _validate475(plan)
    preview=inspect_s5_rally_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.rally)
    route=route_phase_inputs(inputs,zone_id="S5",strategy=strategy,variant_id=variant_id,phase="R_E")
    return S5Preview473(preview.assessments+((route,_early475(inputs,plan,preview.assessments[1][1])),))
