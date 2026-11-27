"""§403 causal M15 rise/near geometry for the explicit B6 compression branch."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_compression_candidate395 import AtrPercentilePlan395, inspect_atr_percentile_candidate
from .causal_compression_pivot402 import inspect_compression_upper_pivot
from .causal_range_percentile397 import RangePercentilePlan397, inspect_range_percentile_candidate
from .causal_indicators import IndicatorState, calculate_wilder_atr14, _validate_ordered_bars
from .causal_structure_geometry import _cross_tf_identity, _source_identity
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class CompressionEarlyPlan403:
    m15_index: int
    atr_start: int
    atr_stop: int
    candidate_k_near: Decimal


@dataclass(frozen=True)
class CompressionApproach403:
    state: str
    reason: str
    distance: Decimal | None = None
    approach: bool | None = None


def compression_method398(p):
    if type(p) is AtrPercentilePlan395:
        return inspect_atr_percentile_candidate, 14, "EXACT_ATR_WINDOW_MISSING"
    if type(p) is RangePercentilePlan397:
        return inspect_range_percentile_candidate, 0, "EXACT_RANGE_WINDOW_MISSING"
    raise ValueError("MST_398_EXPLICIT_COMPRESSION_METHOD")


def _check_early403(plan, target_index):
    if type(plan) is not CompressionEarlyPlan403:
        raise ValueError("MST_403_EXPLICIT_EARLY_PLAN")
    if type(plan.m15_index) is not int or plan.m15_index < 1:
        raise ValueError("MST_403_EXPLICIT_M15_PAIR")
    if (type(plan.atr_start) is not int or type(plan.atr_stop) is not int
            or not 0 <= plan.atr_start < plan.atr_stop <= target_index+1):
        raise ValueError("MST_403_ATR_SLICE_MUST_END_WITHIN_BASE_TARGET")
    k = plan.candidate_k_near
    if type(k) is not Decimal or not k.is_finite() or k < 0:
        raise ValueError("MST_403_EXPLICIT_NEAR_MULTIPLIER")


def _pair403(m15, index, cutoff):
    pair = m15[index-1:index+1]
    bars, _ = _validate_ordered_bars(pair, cutoff, cutoff, Timeframe.M15)
    if bars is None:
        return None
    before = bars[-1].market_bar_key.bar_start_utc
    prior, _ = _validate_ordered_bars(pair[:1], cutoff, before, Timeframe.M15)
    return bars if prior is not None else None


def _base403(rows, target_index, percentile, upper_pivot, cutoff, expected_base_count):
    method, warmup, _ = compression_method398(percentile)
    start = target_index - warmup - percentile.reference_count
    if start < 0 or target_index >= len(rows):
        return None
    result = method(rows[start:target_index+1], plan=percentile, as_of_utc=cutoff)
    if result.at_or_below is not True:
        return None
    pivot = inspect_compression_upper_pivot(
        rows, target_index=target_index, plan=upper_pivot, as_of_utc=cutoff,
        expected_base_count=expected_base_count)
    return pivot if pivot.upper_boundary is True else None


def _distance403(rows, bars, target_index, plan, pivot, cutoff):
    atr_rows = rows[plan.atr_start:plan.atr_stop]
    atr = calculate_wilder_atr14(atr_rows, as_of_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return CompressionApproach403("BLOCKED", "ATR_PREFIX_BLOCKED")
    d1 = rows[target_index].selected
    if (_source_identity(atr_rows[0].selected) != _source_identity(d1)
            or _cross_tf_identity(d1) != _cross_tf_identity(bars[-1])):
        return CompressionApproach403("BLOCKED", "CROSS_TF_SOURCE_MISMATCH")
    high = pivot.pivot.pivot_price
    close = bars[-1].close
    distance = abs(high - close)
    approach = bars[0].close < close <= high and distance <= plan.candidate_k_near * atr.value
    return CompressionApproach403("CAUSAL_DISTANCE_UNCALIBRATED",
                                  "COMPRESSION_SAME_PIVOT_CLOSED_RISE_NEAR_ONLY", distance, approach)


def inspect_compression_approach(rows, m15, *, target_index, percentile, upper_pivot,
                                 plan, as_of_utc, expected_base_count=None):
    """Selected compression and its upper pivot recomputed before M15 target.

    Raw geometry only; dry-up, trend, volume, risk and source admission remain
    independent. No later D1 bar, alternate method or guessed pivot.
    """
    require_utc(as_of_utc)
    _check_early403(plan, target_index)
    if upper_pivot is None or plan.m15_index >= len(m15) or target_index >= len(rows):
        return CompressionApproach403("MISSING_INPUT", "BASE_PIVOT_OR_M15_PAIR_MISSING")
    bars = _pair403(m15, plan.m15_index, as_of_utc)
    if bars is None:
        return CompressionApproach403("BLOCKED", "M15_PAIR_NOT_CAUSALLY_AVAILABLE")
    cutoff = bars[-1].market_bar_key.bar_start_utc
    pivot = _base403(rows, target_index, percentile, upper_pivot, cutoff, expected_base_count)
    if pivot is None:
        return CompressionApproach403("BLOCKED", "COMPRESSION_AND_UPPER_PIVOT_NOT_AVAILABLE_BEFORE_TARGET")
    return _distance403(rows, bars, target_index, plan, pivot, cutoff)
