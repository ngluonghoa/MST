"""§385 same-input B3/S4 R0 and R_C range ingredients, never phase approval."""
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum

from .causal_range_candidate384 import inspect_d1_range_candidate
from .causal_structure_geometry import TiePolicy, _cross_tf_identity
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .source_quality import CoverageState


@dataclass(frozen=True)
class RangeSlice385:
    start: int
    stop: int
    high_indices: tuple[int, int]
    low_indices: tuple[int, int]
    left_count: int
    right_count: int
    tie_policy: TiePolicy
    atr_stop: int
    candidate_k_touch: Decimal
    candidate_k_min_width: Decimal


@dataclass(frozen=True)
class RangeEnginePlan385:
    range_slice: RangeSlice385
    target_tf: Timeframe
    target_index: int
    candidate_k_near: Decimal


class RangeState385(str, Enum):
    BLOCKED = "BLOCKED"
    MISSING = "MISSING_INPUT"
    MATCH = "GEOMETRY_MATCH_UNVERIFIED"
    NONMATCH = "GEOMETRY_NONMATCH_UNVERIFIED"
    DISTANCE = "CAUSAL_DISTANCE_UNCALIBRATED"


@dataclass(frozen=True)
class RangeIngredient385:
    state: RangeState385
    reason: str
    private_range: object | None = None
    distance: Decimal | None = None
    near_candidate: bool | None = None

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


@dataclass(frozen=True)
class RangeEnginePreview385:
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _range_rows385(inputs, plan):
    if type(plan) is not RangeSlice385:
        raise ValueError("MST_385_EXPLICIT_RANGE_SLICE")
    if type(plan.start) is not int or type(plan.stop) is not int or not 0 <= plan.start < plan.stop:
        raise ValueError("MST_385_RANGE_SLICE_INVALID")
    rows = inputs.snapshots_for(Timeframe.D1)
    if rows and plan.stop > len(rows):
        raise ValueError("MST_385_RANGE_SLICE_OUTSIDE_SCOPE")
    return rows[plan.start:plan.stop]


def _range385(rows, plan, cutoff):
    params = asdict(plan)
    del params["start"], params["stop"]
    return inspect_d1_range_candidate(rows, as_of_utc=cutoff, **params)


def _match385(result):
    return (result.upper_touch == result.lower_touch == "NEAR_ONLY"
            and result.width_state == "MEETS_CANDIDATE_MINIMUM"
            and result.close_state == "SUPPLIED_CLOSES_INSIDE_ONLY")


def _r0385(rows, plan, cutoff):
    if not rows:
        return RangeIngredient385(RangeState385.MISSING, "D1_RANGE_HISTORY_MISSING")
    result = _range385(rows, plan, cutoff)
    state = RangeState385.BLOCKED
    if result.reason == "BOUNDARY_GEOMETRY_ONLY":
        state = RangeState385.MATCH if _match385(result) else RangeState385.NONMATCH
    return RangeIngredient385(state, result.reason, result)


def _target385(inputs, plan):
    if type(plan.target_tf) is not Timeframe or plan.target_tf not in (
            Timeframe.D1, Timeframe.H1, Timeframe.M30, Timeframe.M15):
        raise ValueError("MST_385_EXPLICIT_TARGET_TF_CANDIDATE")
    if type(plan.target_index) is not int or plan.target_index < 0:
        raise ValueError("MST_385_INVALID_TARGET_INDEX")
    if type(plan.candidate_k_near) is not Decimal or not plan.candidate_k_near.is_finite() or plan.candidate_k_near < 0:
        raise ValueError("MST_385_EXPLICIT_NEAR_MULTIPLIER")
    rows = inputs.snapshots_for(plan.target_tf)
    if not rows:
        return None
    if plan.target_index >= len(rows):
        raise ValueError("MST_385_TARGET_OUTSIDE_SCOPE")
    return rows[plan.target_index]


def _rc385(inputs, rows, plan, zone):
    target = _target385(inputs, plan)
    if not rows or target is None:
        return RangeIngredient385(RangeState385.MISSING, "RANGE_OR_TARGET_MISSING")
    bar = target.selected
    if (bar is None or not target.confirmation_prerequisites(inputs.as_of_utc)
            or bar.coverage_state is not CoverageState.COMPLETE):
        return RangeIngredient385(RangeState385.BLOCKED, "TARGET_NOT_LOCALLY_ELIGIBLE")
    result = _range385(rows, plan.range_slice, bar.market_bar_key.bar_start_utc)
    if result.reason != "BOUNDARY_GEOMETRY_ONLY" or not _match385(result):
        return RangeIngredient385(RangeState385.BLOCKED, "RANGE_NOT_DESCRIPTIVELY_AVAILABLE_BEFORE_TARGET", result)
    if _cross_tf_identity(rows[0].selected) != _cross_tf_identity(bar):
        return RangeIngredient385(RangeState385.BLOCKED, "RANGE_TARGET_SOURCE_MISMATCH")
    boundary = result.lower if zone == "B3" else result.upper
    distance = abs(bar.close - boundary)
    return RangeIngredient385(RangeState385.DISTANCE, "BOUNDARY_DISTANCE_ONLY_NO_REJECTION_APPROVAL",
                              result, distance, distance <= plan.candidate_k_near * result.atr)


def inspect_routed_range_preview(inputs, *, zone_id, strategy, variant_id, plan):
    """Independent current R0 and pre-target R_C; no prior-phase pass inferred.

    Target frame is an explicit diagnostic choice where source R_C TF is
    pending, not an approved timeframe. R_C requires the supplied range
    geometry to have been available before target START, not backfilled.
    """
    if (type(inputs) is not BaselineResolvedInputs or zone_id not in ("B3", "S4")
            or type(strategy) is not Strategy or type(plan) is not RangeEnginePlan385):
        raise ValueError("MST_385_EXACT_RANGE_SCOPE")
    scope = dict(zone_id=zone_id, strategy=strategy, variant_id=variant_id)
    r0 = route_phase_inputs(inputs, phase="R0", **scope)
    rc = route_phase_inputs(inputs, phase="R_C", **scope)
    rows = _range_rows385(inputs, plan.range_slice)
    return RangeEnginePreview385(((r0, _r0385(rows, plan.range_slice, inputs.as_of_utc)),
                                  (rc, _rc385(inputs, rows, plan, zone_id))))
