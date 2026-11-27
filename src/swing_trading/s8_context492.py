"""§492 S8 R0 exact causal distribution candidate, not a detector."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .causal_exhaustion492 import ExhaustionFeaturePlan492,ExhaustionFeatures492
from .causal_structure_geometry import _eligible
from .replay import require_utc
from .s5_transition473 import _identity473
from .contracts import DecisionStatus,Strategy
from .feature_engine460 import inspect_d1_exhaustion492
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
