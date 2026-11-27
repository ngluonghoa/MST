"""§409 B7 causal support distance, not an approved rebound predicate."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, _cross_tf_identity, _eligible,
    inspect_causal_pivot,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .zone_manifest_v03 import inspect_near_zone_arithmetic


@dataclass(frozen=True)
class B7SupportPlan409:
    target_index: int
    pivot_tf: Timeframe
    pivot_start: int
    pivot_stop: int
    candidate_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_start: int
    atr_stop: int
    candidate_k_near: Decimal | None


class B7SupportState409(str, Enum):
    BLOCKED = "BLOCKED"
    MISSING = "MISSING_INPUT"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"


@dataclass(frozen=True)
class B7SupportIngredient409:
    state: B7SupportState409
    reason: str
    distance_atr: Decimal | None = None
    near_candidate: bool | None = None


@dataclass(frozen=True)
class B7SupportPreview409:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _window409(rows, start, stop):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= 512:
        raise ValueError("MST_409_EXPLICIT_WINDOW")
    if stop > len(rows):
        return ()
    return rows[start:stop]


def _validate409(plan):
    if type(plan.pivot_tf) is not Timeframe or plan.pivot_tf not in (Timeframe.D1, Timeframe.H1):
        raise ValueError("MST_409_EXPLICIT_PIVOT_FRAME")
    if type(plan.target_index) is not int or not 0 <= plan.target_index < 512:
        raise ValueError("MST_409_EXPLICIT_TARGET")
    k = plan.candidate_k_near
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k < 0):
        raise ValueError("MST_409_EXPLICIT_K")
    if (type(plan.candidate_index) is not int or plan.candidate_index < 0
            or type(plan.left_count) is not int or not 1 <= plan.left_count <= 40
            or type(plan.right_count) is not int or not 1 <= plan.right_count <= 40
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_409_EXPLICIT_PIVOT")


def _rc409(inputs, plan):
    targets = inputs.snapshots_for(Timeframe.M15)
    history = _window409(inputs.snapshots_for(plan.pivot_tf), plan.pivot_start, plan.pivot_stop)
    daily = _window409(inputs.snapshots_for(Timeframe.D1), plan.atr_start, plan.atr_stop)
    if plan.target_index >= len(targets) or not history or len(daily) < 15:
        return B7SupportIngredient409(B7SupportState409.MISSING, "EXACT_INPUT_MISSING")
    target = _eligible(targets[plan.target_index], cutoff=inputs.as_of_utc)
    if target is None:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "TARGET_NOT_ELIGIBLE")
    cutoff = target.market_bar_key.bar_start_utc
    pivot = inspect_causal_pivot(history, candidate_index=plan.candidate_index,
        left_count=plan.left_count, right_count=plan.right_count, side=StructureSide.LOW,
        tie_policy=plan.tie_policy, as_of_utc=cutoff)
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY or pivot.geometric_extremum is not True:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "SUPPORT_NOT_CAUSALLY_AVAILABLE")
    atr = calculate_wilder_atr14(daily, as_of_utc=inputs.as_of_utc, known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "ATR_NOT_CAUSALLY_AVAILABLE")
    if not (_cross_tf_identity(history[0].selected) == _cross_tf_identity(daily[0].selected)
            == _cross_tf_identity(target)):
        return B7SupportIngredient409(B7SupportState409.BLOCKED, "CROSS_FRAME_SOURCE_MISMATCH")
    near = inspect_near_zone_arithmetic(price=target.low, zone_lower=pivot.pivot_price,
        zone_upper=pivot.pivot_price, atr_d1=atr.value, candidate_k_near=plan.candidate_k_near)
    return B7SupportIngredient409(B7SupportState409.DISTANCE,
        "SUPPORT_DISTANCE_ONLY_NO_REVERSAL_OR_RISK_APPROVAL",
        near.normalized_by_atr, near.in_candidate_band)


def inspect_b7_support_preview(inputs, *, strategy, variant_id, plan):
    """Explicit M15 low and D1/H1 pivot diagnostic; RC timeframe remains pending."""
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not B7SupportPlan409
            or variant_id not in ("B7/E_RECLAIM", "B7/E_CHOCH")):
        raise ValueError("MST_409_EXACT_SCOPE")
    _validate409(plan)
    route = route_phase_inputs(inputs, zone_id="B7", strategy=strategy,
                               variant_id=variant_id, phase="R_C")
    return B7SupportPreview409(((route, _rc409(inputs, plan)),))
