"""§384 D1 two-touch boundary geometry for B3/S4, not a range verdict."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import GeometryState, StructureSide, TiePolicy, inspect_causal_pivot
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12


@dataclass(frozen=True)
class D1RangeCandidate384:
    reason: str
    upper: Decimal | None = None
    lower: Decimal | None = None
    atr: Decimal | None = None
    upper_touch: str = "NOT_EVALUATED"
    lower_touch: str = "NOT_EVALUATED"
    width_state: str = "NOT_EVALUATED"
    close_state: str = "NOT_EVALUATED"

    @property
    def range_verified(self):
        return False

    @property
    def action_eligible(self):
        return False

    def safe_summary(self):
        return {
            "schema": "mst.private.d1_range_geometry.v0.1", "reason": self.reason,
            "upper_touch": self.upper_touch, "lower_touch": self.lower_touch,
            "width_state": self.width_state, "close_state": self.close_state,
            "range_verified": False, "source_qualified": False,
            "parameter_approved": False, "action_eligible": False,
        }


def _check_pair384(indices):
    if (type(indices) is not tuple or len(indices) != 2
            or any(type(i) is not int or i < 0 for i in indices)):
        raise ValueError("MST_384_EXACT_TWO_PIVOT_INDICES_REQUIRED")


def _check_multiplier384(value):
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise ValueError("MST_384_EXPLICIT_NONNEGATIVE_DECIMAL_MULTIPLIER")


def _check_policy384(left_count, right_count, tie_policy, atr_stop):
    if (type(left_count) is not int or not 1 <= left_count <= 40
            or type(right_count) is not int or not 1 <= right_count <= 40
            or type(tie_policy) is not TiePolicy or type(atr_stop) is not int):
        raise ValueError("MST_384_EXPLICIT_PIVOT_AND_ATR_POLICY")


def _history_ok384(history):
    return (type(history) is tuple and 15 <= len(history) <= 512
            and all(type(row) is ResolvedBarSnapshotV12
                    and row.market_bar_key.timeframe is Timeframe.D1 for row in history))


def _ordered384(highs, lows, n):
    return (len(set(highs + lows)) == 4 and max(highs[0], lows[0]) < min(highs[1], lows[1])
            and max(highs + lows) < n)


def _pivots384(history, indices, side, policy, as_of_utc):
    return tuple(inspect_causal_pivot(history, candidate_index=i, side=side,
                                     as_of_utc=as_of_utc, **policy) for i in indices)


def _touch384(reference, retest, tolerance):
    return "NEAR_ONLY" if abs(reference - retest) <= tolerance else "OUTSIDE_TOLERANCE"


def _describe384(history, hp, lp, atr, touch_k, width_k, first_test):
    upper, lower = hp[0].pivot_price, lp[0].pivot_price
    if upper <= lower:
        return D1RangeCandidate384("NONPOSITIVE_REFERENCE_WIDTH")
    outside = any(not lower <= row.selected.close <= upper for row in history[first_test:])
    return D1RangeCandidate384(
        "BOUNDARY_GEOMETRY_ONLY", upper, lower, atr,
        _touch384(upper, hp[1].pivot_price, touch_k * atr),
        _touch384(lower, lp[1].pivot_price, touch_k * atr),
        "MEETS_CANDIDATE_MINIMUM" if upper - lower >= width_k * atr else "BELOW_CANDIDATE_MINIMUM",
        "OUTSIDE_REFERENCE_CLOSE_OBSERVED" if outside else "SUPPLIED_CLOSES_INSIDE_ONLY",
    )


def inspect_d1_range_candidate(history, *, high_indices, low_indices, left_count, right_count,
                               tie_policy, atr_stop, candidate_k_touch, candidate_k_min_width,
                               as_of_utc):
    """Two pre-known boundary anchors and two local extrema as subsequent tests.

    Explicit multipliers only. ATR prefix and both anchors must be known
    before either retest starts. Closes after first test are descriptive
    against the original exact anchors, not a validated range/reentry policy.
    No automatic search, source calendar continuity, SIDEWAYS or approval.
    """
    require_utc(as_of_utc)
    _check_pair384(high_indices)
    _check_pair384(low_indices)
    _check_multiplier384(candidate_k_touch)
    _check_multiplier384(candidate_k_min_width)
    _check_policy384(left_count, right_count, tie_policy, atr_stop)
    if not _history_ok384(history):
        return D1RangeCandidate384("MISSING_OR_INVALID_D1_HISTORY")
    if not _ordered384(high_indices, low_indices, len(history)):
        return D1RangeCandidate384("NON_DISTINCT_OR_UNORDERED_BOUNDARY_TESTS")
    first_test = min(high_indices[1], low_indices[1])
    if not 15 <= atr_stop <= first_test:
        return D1RangeCandidate384("ATR_PREFIX_NOT_BEFORE_TESTS")
    cutoff = history[first_test].market_bar_key.bar_start_utc
    policy = dict(left_count=left_count, right_count=right_count, tie_policy=tie_policy)
    hp = _pivots384(history, high_indices, StructureSide.HIGH, policy, as_of_utc)
    lp = _pivots384(history, low_indices, StructureSide.LOW, policy, as_of_utc)
    if any(p.state is GeometryState.BLOCKED for p in hp + lp):
        return D1RangeCandidate384("PIVOT_INPUT_BLOCKED")
    if any(p.geometric_extremum is not True for p in hp + lp):
        return D1RangeCandidate384("BOUNDARY_TEST_NOT_EXTREMUM")
    if max(hp[0].witness_known_at_utc, lp[0].witness_known_at_utc) > cutoff:
        return D1RangeCandidate384("ANCHOR_NOT_KNOWN_BEFORE_TEST")
    atr = calculate_wilder_atr14(history[:atr_stop], as_of_utc=as_of_utc, known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return D1RangeCandidate384("ATR_PREFIX_BLOCKED")
    return _describe384(history, hp, lp, atr.value, candidate_k_touch, candidate_k_min_width, first_test)
