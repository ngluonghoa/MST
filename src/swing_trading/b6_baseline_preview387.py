"""§387 B6 causal contraction and M15 upper-pivot approach ingredients."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .causal_contraction_candidate386 import ContractionPlan386, inspect_d1_contraction_candidate
from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import _cross_tf_identity, _source_identity
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .source_quality import CoverageState


@dataclass(frozen=True)
class B6EnginePlan387:
    d1_start: int
    d1_stop: int
    contraction: ContractionPlan386
    atr_start: int
    atr_stop: int
    target_index: int
    candidate_k_near: Decimal


class B6State387(str, Enum):
    BLOCKED = "BLOCKED"
    MISSING = "MISSING_INPUT"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"


@dataclass(frozen=True)
class B6Ingredient387:
    state: B6State387
    reason: str
    contraction: object | None = None
    distance: Decimal | None = None
    approach: bool | None = None

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


@dataclass(frozen=True)
class B6EnginePreview387:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _slice387(rows, start, stop):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop:
        raise ValueError("MST_387_INVALID_SLICE")
    if rows and stop > len(rows):
        raise ValueError("MST_387_SLICE_OUTSIDE_SCOPE")
    return rows[start:stop]


def _check_plan387(plan):
    if type(plan) is not B6EnginePlan387 or type(plan.contraction) is not ContractionPlan386:
        raise ValueError("MST_387_EXPLICIT_PLAN")
    if type(plan.target_index) is not int or plan.target_index < 1:
        raise ValueError("MST_387_REQUIRE_PRIOR_M15_INDEX")
    k = plan.candidate_k_near
    if type(k) is not Decimal or not k.is_finite() or k < 0:
        raise ValueError("MST_387_EXPLICIT_NEAR_MULTIPLIER")


def _rc387(history, plan, cutoff):
    if not history:
        return B6Ingredient387(B6State387.MISSING, "CONTRACTION_HISTORY_MISSING")
    result = inspect_d1_contraction_candidate(history, plan=plan.contraction, as_of_utc=cutoff)
    state = B6State387.BLOCKED
    if result.reason == "PULLBACK_DEPTH_GEOMETRY_ONLY":
        state = B6State387.MATCH if result.trailing_contractions >= 2 else B6State387.NONMATCH
    return B6Ingredient387(state, result.reason, result)


def _m15_pair387(inputs, index):
    rows = inputs.snapshots_for(Timeframe.M15)
    if not rows:
        return None
    if index >= len(rows):
        raise ValueError("MST_387_TARGET_OUTSIDE_SCOPE")
    return rows[index-1], rows[index]


def _pair_ok387(pair, cutoff):
    previous, target = pair
    if not target.confirmation_prerequisites(cutoff):
        return False
    bar = target.selected
    if not previous.confirmation_prerequisites(bar.market_bar_key.bar_start_utc):
        return False
    prior = previous.selected
    return (prior.coverage_state is bar.coverage_state is CoverageState.COMPLETE
            and prior.bar_end_utc <= bar.market_bar_key.bar_start_utc
            and _source_identity(prior) == _source_identity(bar))


def _distance387(pair, history, atr_rows, plan, atr):
    target = pair[1].selected
    previous = pair[0].selected
    if not all(_cross_tf_identity(x.selected) == _cross_tf_identity(target)
               for x in (history[0], atr_rows[0])):
        return B6Ingredient387(B6State387.BLOCKED, "CROSS_TF_SOURCE_MISMATCH")
    # Explicit last selected high, not an inferred highest/most recent pivot.
    high = history[plan.contraction.swings[-1][0]].selected.high
    distance = abs(high - target.close)
    approach = previous.close < target.close <= high and distance <= plan.candidate_k_near * atr.value
    return B6Ingredient387(B6State387.DISTANCE, "CLOSED_RISE_AND_NEAR_GEOMETRY_ONLY",
                           distance=distance, approach=approach)


def _re387(inputs, history, atr_rows, plan):
    pair = _m15_pair387(inputs, plan.target_index)
    if pair is None or not history or not atr_rows:
        return B6Ingredient387(B6State387.MISSING, "CONTRACTION_ATR_OR_M15_MISSING")
    if not _pair_ok387(pair, inputs.as_of_utc):
        return B6Ingredient387(B6State387.BLOCKED, "M15_PAIR_NOT_CAUSALLY_AVAILABLE")
    cutoff = pair[1].selected.market_bar_key.bar_start_utc
    rc = _rc387(history, plan, cutoff)
    if rc.state is not B6State387.MATCH:
        return B6Ingredient387(B6State387.BLOCKED, "TWO_CONTRACTIONS_NOT_AVAILABLE_BEFORE_TARGET")
    # ATR must be validated before inspecting its selected row.
    atr = calculate_wilder_atr14(atr_rows, as_of_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return B6Ingredient387(B6State387.BLOCKED, "ATR_PREFIX_BLOCKED")
    return _distance387(pair, history, atr_rows, plan, atr)


def inspect_b6_baseline_preview(inputs, *, strategy, variant_id, plan):
    """Only explicit two-contraction branch; not R0 trend/base or R_F breakout.

    No alternate compression fallback, no claimed volume dry-up or ATR approval.
    Target must be M15 and both D1 histories causally known at target start.
    """
    if type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy:
        raise ValueError("MST_387_BASELINE_SCOPE")
    if variant_id != "B6/C_TWO_CONTRACTIONS":
        raise ValueError("MST_387_EXACT_CONTRACTION_VARIANT")
    _check_plan387(plan)
    rows = inputs.snapshots_for(Timeframe.D1)
    history = _slice387(rows, plan.d1_start, plan.d1_stop)
    atr_rows = _slice387(rows, plan.atr_start, plan.atr_stop)
    scope = dict(zone_id="B6", strategy=strategy, variant_id=variant_id)
    rc = route_phase_inputs(inputs, phase="R_C", **scope)
    re = route_phase_inputs(inputs, phase="R_E", **scope)
    return B6EnginePreview387(((rc, _rc387(history, plan, inputs.as_of_utc)),
                               (re, _re387(inputs, history, atr_rows, plan))))
