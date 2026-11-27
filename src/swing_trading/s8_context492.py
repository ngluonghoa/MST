"""§492 S8 R0 exact causal distribution candidate, not a detector."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .causal_exhaustion492 import ExhaustionFeaturePlan492,ExhaustionFeatures492
from .causal_structure_geometry import (_eligible, _sequence, _source_identity, _cross_tf_identity,
    GeometryState, StructureSide, TiePolicy, inspect_causal_pivot)
from .replay import require_utc
from .s5_transition473 import _identity473
from .contracts import DecisionStatus,Strategy
from .feature_engine460 import inspect_d1_exhaustion492, inspect_target_d1_atr
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class S8ContextPlan492:
    features: ExhaustionFeaturePlan492


@dataclass(frozen=True)
class S8Ingredient492:
    state: S1State439
    reason: str
    private_features: ExhaustionFeatures492 | None = None


@dataclass(frozen=True)
class S8Preview492:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def inspect_s8_context492_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S8ContextPlan492 or type(strategy) is not Strategy or variant_id!="S8/BASE":
        raise ValueError("MST_492_EXACT_SCOPE")
    features=inspect_d1_exhaustion492(inputs,plan.features)
    if features.reason=="EXACT_D1_DISTRIBUTION_CANDIDATE_ONLY":
        state=S1State439.MATCH
    elif features.reason=="EXACT_HISTORY_MISSING":
        state=S1State439.MISSING
    else:
        state=S1State439.BLOCKED
    route=route_phase_inputs(inputs,zone_id="S8",strategy=strategy,variant_id=variant_id,phase="R0")
    return S8Preview492(((route,S8Ingredient492(state,features.reason,features)),))


class S8ExhaustionMode493(str,Enum):
    RANGE_UPPER_WICK="RANGE_UPPER_WICK"
    VOLUME_CLIMAX="VOLUME_CLIMAX"


@dataclass(frozen=True)
class S8ExhaustionPlan493:
    context: S8ContextPlan492
    mode: S8ExhaustionMode493
    candidate_min_return: Decimal | None
    candidate_min_range_atr: Decimal | None
    candidate_min_upper_wick: Decimal | None
    candidate_min_volume_multiple: Decimal | None
    event_id: str
    revision_digest: str
    bar_start_utc: datetime
    event_known_at_utc: datetime
    policy_known_at_utc: datetime
    expires_at_utc: datetime


@dataclass(frozen=True)
class S8ExhaustionIngredient493:
    state: S1State439
    reason: str
    private_event_id: str | None = None
    private_event_known: datetime | None = None
    private_high: Decimal | None = None
    private_mode: S8ExhaustionMode493 | None = None


def _validate493(p):
    if type(p) is not S8ExhaustionPlan493 or type(p.context) is not S8ContextPlan492:
        raise ValueError("MST_493_EXACT_EXHAUSTION_PLAN")
    if type(p.mode) is not S8ExhaustionMode493:
        raise ValueError("MST_493_EXPLICIT_MODE")
    values=(p.candidate_min_return,p.candidate_min_range_atr,p.candidate_min_upper_wick,p.candidate_min_volume_multiple)
    if any(x is not None and (type(x) is not Decimal or not x.is_finite() or x<=0) for x in values):
        raise ValueError("MST_493_EXPLICIT_POSITIVE_THRESHOLDS")
    if p.candidate_min_upper_wick is not None and p.candidate_min_upper_wick>1:
        raise ValueError("MST_493_WICK_FRACTION")
    if p.mode is S8ExhaustionMode493.RANGE_UPPER_WICK and p.candidate_min_volume_multiple is not None:
        raise ValueError("MST_493_NO_IMPLICIT_VOLUME_BRANCH")
    if p.mode is S8ExhaustionMode493.VOLUME_CLIMAX and any(x is not None for x in values[1:3]):
        raise ValueError("MST_493_NO_IMPLICIT_RANGE_BRANCH")
    if p.candidate_min_volume_multiple is not None and p.candidate_min_volume_multiple<=1:
        raise ValueError("MST_493_CLIMAX_MULTIPLE_ABOVE_ONE")
    if any(type(x) is not str or not x.strip() for x in (p.event_id,p.revision_digest)):
        raise ValueError("MST_493_EXACT_EVENT_ID")
    for clock in (p.bar_start_utc,p.event_known_at_utc,p.policy_known_at_utc,p.expires_at_utc):
        if type(clock) is not datetime:
            raise ValueError("MST_493_EXPLICIT_CLOCK")
        require_utc(clock)
    if not p.policy_known_at_utc<=p.bar_start_utc<p.event_known_at_utc<=p.expires_at_utc:
        raise ValueError("MST_493_CAUSAL_POLICY_CLOCK")


def _range493(p,f,target):
    if p.candidate_min_range_atr is None or p.candidate_min_upper_wick is None:
        return S1State439.DISTANCE
    if target.high<=target.low:
        return S1State439.NONMATCH
    wick=target.high-max(target.open,target.close)
    match=(f.target_range_atr>f.reference_range_atr and f.target_range_atr>=p.candidate_min_range_atr
           and wick>=p.candidate_min_upper_wick*(target.high-target.low))
    return S1State439.MATCH if match else S1State439.NONMATCH


def _climax493(p,f):
    if f.reference_volume<=0:
        return S1State439.BLOCKED
    if p.candidate_min_volume_multiple is None:
        return S1State439.DISTANCE
    match=f.target_volume>=p.candidate_min_volume_multiple*f.reference_volume
    return S1State439.MATCH if match else S1State439.NONMATCH


def _shape493(p,f,target):
    if f.target_return<=max(Decimal(0),f.reference_return):
        state=S1State439.NONMATCH
    elif p.candidate_min_return is None:
        state=S1State439.DISTANCE
    elif f.target_return<p.candidate_min_return:
        state=S1State439.NONMATCH
    elif p.mode is S8ExhaustionMode493.RANGE_UPPER_WICK:
        state=_range493(p,f,target)
    else:
        state=_climax493(p,f)
    return S8ExhaustionIngredient493(state,"EXPLICIT_ACCELERATION_EXHAUSTION_CANDIDATE_ONLY",
        p.event_id,p.event_known_at_utc,target.high,p.mode)


def _exhaustion493(inputs,p,r0):
    if r0.state is not S1State439.MATCH:
        return S8ExhaustionIngredient493(S1State439.BLOCKED,"R0_DISTRIBUTION_NOT_MATCHED")
    i=p.context.features.target_index
    target=_eligible(inputs.snapshots_for(Timeframe.D1)[i],cutoff=inputs.as_of_utc)
    if target is None or not _identity473(p,target,inputs.as_of_utc):
        return S8ExhaustionIngredient493(S1State439.BLOCKED,"EXHAUSTION_EVENT_NOT_EXACT")
    return _shape493(p,r0.private_features,target)


def inspect_s8_exhaustion493_preview(inputs,*,strategy,variant_id,plan):
    _validate493(plan)
    preview=inspect_s8_context492_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    route=route_phase_inputs(inputs,zone_id="S8",strategy=strategy,variant_id=variant_id,phase="R_C")
    return S8Preview492(preview.assessments+((route,_exhaustion493(inputs,plan,preview.assessments[0][1])),))


@dataclass(frozen=True)
class S8EarlyPlan494:
    exhaustion: S8ExhaustionPlan493
    history_start: int
    target_index: int
    low_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class S8EarlyIngredient494:
    state: S1State439
    reason: str
    private_event_id: str | None = None
    private_high: Decimal | None = None
    private_micro_low: Decimal | None = None
    private_early_known: datetime | None = None


def _validate494(p):
    if type(p) is not S8EarlyPlan494 or type(p.exhaustion) is not S8ExhaustionPlan493:
        raise ValueError("MST_494_EXACT_EARLY_PLAN")
    indices=(p.history_start,p.target_index,p.low_index,p.left_count,p.right_count,p.atr_start,p.atr_stop)
    if any(type(i) is not int for i in indices):
        raise ValueError("MST_494_EXACT_INDICES")
    if not 1<=p.left_count<=40 or not 1<=p.right_count<=40 or type(p.tie_policy) is not TiePolicy:
        raise ValueError("MST_494_EXPLICIT_PIVOT_POLICY")
    if not 0<=p.history_start or not p.left_count<=p.low_index or not p.history_start+p.low_index+p.right_count<p.target_index-1<511:
        raise ValueError("MST_494_DISTINCT_CAUSAL_TARGET")
    if not 0<=p.atr_start<p.atr_stop<=512 or p.atr_stop-p.atr_start<15:
        raise ValueError("MST_494_ATR_WINDOW")
    k=p.candidate_epsilon
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<0):
        raise ValueError("MST_494_EXPLICIT_EPSILON")


def _path494(inputs,p,target,rc):
    rows=inputs.snapshots_for(Timeframe.M15)
    if any(s.market_bar_key.bar_start_utc>=rc.private_event_known for s in rows[:p.history_start]):
        return None
    path,_=_sequence(rows[p.history_start:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    origin=inputs.snapshots_for(Timeframe.D1)[p.exhaustion.context.features.target_index].selected
    if not path or path[0].market_bar_key.bar_start_utc<rc.private_event_known:
        return None
    if _cross_tf_identity(origin)!=_cross_tf_identity(target) or _source_identity(path[0])!=_source_identity(target):
        return None
    if any(a.verified_at_utc>b.market_bar_key.bar_start_utc for a,b in zip(path,path[1:])):
        return None
    return path


def _shape494(inputs,p,target,path,rc):
    history=inputs.snapshots_for(Timeframe.M15)[p.history_start:p.target_index-1]
    pivot=inspect_causal_pivot(history,candidate_index=p.low_index,side=StructureSide.LOW,
        left_count=p.left_count,right_count=p.right_count,tie_policy=p.tie_policy,
        as_of_utc=path[-1].market_bar_key.bar_start_utc)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return S8EarlyIngredient494(S1State439.BLOCKED,"MICRO_SUPPORT_NOT_CAUSAL")
    if pivot.geometric_extremum is not True or pivot.pivot_price>=rc.private_high:
        return S8EarlyIngredient494(S1State439.NONMATCH,"MICRO_SUPPORT_NOT_CONFIRMED")
    return _cross494(inputs,p,target,path,rc,pivot.pivot_price)


def _cross494(inputs,p,target,path,rc,low):
    if any(b.high>rc.private_high for b in (*path,target)):
        return S8EarlyIngredient494(S1State439.NONMATCH,"EXHAUSTION_HIGH_INVALIDATED")
    if any(b.close<low for b in path[p.low_index+p.right_count+1:]):
        return S8EarlyIngredient494(S1State439.NONMATCH,"EARLIER_SUPPLIED_CLOSE_BELOW_SUPPORT")
    if path[-1].close<low or target.close>=low or target.close>=target.open:
        return S8EarlyIngredient494(S1State439.NONMATCH,"NO_CLOSED_BEARISH_SUPPORT_CROSS")
    atr=inspect_target_d1_atr(inputs,p,target)
    if atr is None or atr<=0:
        return S8EarlyIngredient494(S1State439.BLOCKED,"EARLY_ATR_UNRESOLVED")
    k=p.candidate_epsilon
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if target.close<low-k*atr else S1State439.NONMATCH
    return S8EarlyIngredient494(state,"M15_CLOSED_MICRO_SUPPORT_REVERSAL_CANDIDATE_ONLY",
        rc.private_event_id,rc.private_high,low,target.verified_at_utc)


def _early494(inputs,p,rc):
    if rc.state is not S1State439.MATCH:
        return S8EarlyIngredient494(S1State439.BLOCKED,"EXHAUSTION_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S8EarlyIngredient494(S1State439.MISSING,"EARLY_BAR_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or target.verified_at_utc>p.exhaustion.expires_at_utc:
        return S8EarlyIngredient494(S1State439.BLOCKED,"EARLY_BAR_OR_EXPIRY_UNRESOLVED")
    path=_path494(inputs,p,target,rc)
    if path is None:
        return S8EarlyIngredient494(S1State439.BLOCKED,"EARLY_PATH_NOT_CAUSAL")
    return _shape494(inputs,p,target,path,rc)


def inspect_s8_early494_preview(inputs,*,strategy,variant_id,plan):
    _validate494(plan)
    preview=inspect_s8_exhaustion493_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.exhaustion)
    route=route_phase_inputs(inputs,zone_id="S8",strategy=strategy,variant_id=variant_id,phase="R_E")
    return S8Preview492(preview.assessments+((route,_early494(inputs,plan,preview.assessments[1][1])),))
