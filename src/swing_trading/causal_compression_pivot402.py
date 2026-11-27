"""§402 explicit upper-pivot candidate bound to a compression base."""
from dataclasses import dataclass

from .causal_indicators import _validate_ordered_bars
from .causal_structure_geometry import (
    GeometryState, PivotGeometry, StructureSide, TiePolicy, inspect_causal_pivot,
)
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class CompressionPivotPlan402:
    base_count: int
    candidate_index: int
    left_count: int
    right_count: int
    tie_policy: TiePolicy


@dataclass(frozen=True)
class CompressionPivotCandidate402:
    reason: str
    pivot: PivotGeometry | None = None
    upper_boundary: bool | None = None

    def safe_summary(self):
        return {"schema": "mst.private.compression_upper_pivot.v0.1",
                "reason": self.reason, "upper_boundary": self.upper_boundary,
                "pivot_approved": False, "source_qualified": False,
                "action_eligible": False}


def _check_plan402(plan):
    if type(plan) is not CompressionPivotPlan402:
        raise ValueError("MST_402_EXPLICIT_PIVOT_PLAN")
    if type(plan.base_count) is not int or not 3 <= plan.base_count <= 512:
        raise ValueError("MST_402_EXACT_BASE_COUNT")
    if any(type(n) is not int or not 1 <= n <= 40 for n in (plan.left_count, plan.right_count)):
        raise ValueError("MST_402_EXPLICIT_RIGHT_LEFT_COUNTS")
    if type(plan.candidate_index) is not int or not 0 <= plan.candidate_index < plan.base_count:
        raise ValueError("MST_402_BASE_RELATIVE_PIVOT_INDEX")
    if type(plan.tie_policy) is not TiePolicy:
        raise ValueError("MST_402_EXPLICIT_TIE_POLICY")


def inspect_compression_upper_pivot(rows, *, target_index, plan, as_of_utc,
                                    expected_base_count=None):
    """Exact trailing D1 base ending at selected target; no external pivot.

    Explicit local HIGH and no higher supplied high anywhere in that base.
    This is geometry, not proof of a base, continuity or valid resistance.
    All selected right bars and the base must be known at the decision cutoff.
    """
    require_utc(as_of_utc)
    _check_plan402(plan)
    if type(target_index) is not int or target_index < 0:
        raise ValueError("MST_402_EXPLICIT_TARGET")
    if expected_base_count is not None and plan.base_count != expected_base_count:
        raise ValueError("MST_402_DRYUP_BASE_MISMATCH")
    start = target_index + 1 - plan.base_count
    if type(rows) is not tuple or start < 0 or target_index >= len(rows):
        return CompressionPivotCandidate402("EXACT_COMPRESSION_BASE_MISSING")
    history = rows[start:target_index+1]
    bars, reason = _validate_ordered_bars(history, as_of_utc, as_of_utc, Timeframe.D1)
    if bars is None:
        return CompressionPivotCandidate402("BASE_" + reason)
    result = inspect_causal_pivot(
        history, candidate_index=plan.candidate_index, left_count=plan.left_count,
        right_count=plan.right_count, side=StructureSide.HIGH,
        tie_policy=plan.tie_policy, as_of_utc=as_of_utc,
    )
    if result.state is GeometryState.BLOCKED:
        return CompressionPivotCandidate402("PIVOT_" + result.reason)
    upper = result.geometric_extremum and all(b.high <= result.pivot_price for b in bars)
    return CompressionPivotCandidate402("UPPER_PIVOT_GEOMETRY_ONLY", result, upper)
