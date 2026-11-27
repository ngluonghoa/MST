"""§492 S8 R0 exact causal distribution candidate, not a detector."""
from dataclasses import dataclass

from .causal_exhaustion492 import ExhaustionFeaturePlan492,ExhaustionFeatures492
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
