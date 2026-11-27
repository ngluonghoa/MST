"""§404 D1 closed cross of the exact selected compression upper pivot."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_compression_approach403 import inspect_compression_approach
from .causal_structure_geometry import GeometryState, StructureSide, inspect_closed_bos_geometry
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class CompressionD1RFPlan404:
    breakout_index: int
    candidate_epsilon: Decimal


@dataclass(frozen=True)
class CompressionBreakout404:
    state: str
    reason: str


def _check_rf404(plan, target_index):
    if type(plan) is not CompressionD1RFPlan404:
        raise ValueError("MST_404_EXPLICIT_D1_RF_PLAN")
    if type(plan.breakout_index) is not int or plan.breakout_index <= target_index+1:
        raise ValueError("MST_404_PRIOR_AND_TARGET_MUST_FOLLOW_BASE")
    eps = plan.candidate_epsilon
    if type(eps) is not Decimal or not eps.is_finite() or eps < 0:
        raise ValueError("MST_404_EXPLICIT_EPSILON")


def _cross404(rows, target_index, upper_pivot, early, rf, as_of):
    start = target_index+1-upper_pivot.base_count
    history = rows[start:target_index+1]
    index = rf.breakout_index
    geom = inspect_closed_bos_geometry(
        history, pivot_index=upper_pivot.candidate_index,
        left_count=upper_pivot.left_count, right_count=upper_pivot.right_count,
        side=StructureSide.HIGH, tie_policy=upper_pivot.tie_policy,
        previous=rows[index-1], breakout=rows[index],
        atr_d1_history=rows[early.atr_start:early.atr_stop],
        candidate_epsilon=rf.candidate_epsilon, as_of_utc=as_of)
    if geom.state is GeometryState.BLOCKED:
        return CompressionBreakout404("BLOCKED", "D1_CLOSED_CROSS_" + geom.reason)
    state = "GEOMETRY_MATCH_UNVERIFIED" if geom.candidate_cross else "GEOMETRY_NONMATCH_UNVERIFIED"
    return CompressionBreakout404(state, "COMPRESSION_SAME_PIVOT_D1_CROSS_ONLY")


def inspect_compression_d1_breakout(rows, m15, *, target_index, percentile,
                                    upper_pivot, early, rf, as_of_utc,
                                    expected_base_count=None):
    """Recompute the earlier M15 approach at D1 breakout START.

    The same exact D1 base, upper pivot and early ATR prefix feed the existing
    closed BOS geometry. No alternate pivot or timeframe, no volume/risk
    confirmation, and no detector authorization.
    """
    require_utc(as_of_utc)
    _check_rf404(rf, target_index)
    if rf.breakout_index >= len(rows):
        return CompressionBreakout404("MISSING_INPUT", "D1_BREAKOUT_OR_PREVIOUS_MISSING")
    if early is None or upper_pivot is None:
        return CompressionBreakout404("MISSING_INPUT", "EXPLICIT_APPROACH_OR_PIVOT_MISSING")
    pair = rows[rf.breakout_index-1:rf.breakout_index+1]
    if any(s.market_bar_key.timeframe is not Timeframe.D1 for s in pair):
        return CompressionBreakout404("BLOCKED", "D1_BREAKOUT_TIMEFRAME_MISMATCH")
    target = pair[-1].selected
    if target is None or not pair[-1].confirmation_prerequisites(as_of_utc):
        return CompressionBreakout404("BLOCKED", "D1_BREAKOUT_NOT_CAUSALLY_AVAILABLE")
    cutoff = target.market_bar_key.bar_start_utc
    approach = inspect_compression_approach(
        rows, m15, target_index=target_index, percentile=percentile,
        upper_pivot=upper_pivot, plan=early, as_of_utc=cutoff,
        expected_base_count=expected_base_count)
    if approach.approach is not True:
        return CompressionBreakout404("BLOCKED", "M15_APPROACH_NOT_AVAILABLE_BEFORE_D1_BREAKOUT")
    return _cross404(rows, target_index, upper_pivot, early, rf, as_of_utc)
