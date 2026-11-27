"""§397 explicit normalized D1 candle range percentile, candidate only."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from .causal_indicators import _validate_ordered_bars
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class RangePercentilePlan397:
    reference_count: int
    quantile: Decimal


@dataclass(frozen=True)
class RangePercentileCandidate397:
    reason: str
    target_range_percent: Decimal | None = None
    reference_threshold_percent: Decimal | None = None
    reference_count: int = 0
    at_or_below: bool | None = None

    def safe_summary(self):
        return {
            "schema": "mst.private.range_percentile_candidate.v0.1",
            "reason": self.reason, "at_or_below": self.at_or_below,
            "compression_verified": False, "parameter_approved": False,
            "source_qualified": False, "action_eligible": False,
        }


def _check_plan397(plan):
    if type(plan) is not RangePercentilePlan397:
        raise ValueError("MST_397_EXPLICIT_RANGE_PLAN")
    if type(plan.reference_count) is not int or not 2 <= plan.reference_count <= 511:
        raise ValueError("MST_397_BOUNDED_REFERENCE_COUNT")
    q = plan.quantile
    if type(q) is not Decimal or not q.is_finite() or not 0 < q <= 1:
        raise ValueError("MST_397_EXPLICIT_QUANTILE")


def _range_pct397(row):
    if row.close <= 0:
        return None
    return (row.high - row.low) * Decimal(100) / row.close


def inspect_range_percentile_candidate(history, *, plan, as_of_utc):
    """Exact N prior D1 ranges and distinct target, normalized by own close.

    Nearest-rank ceil(q*N), inclusive comparison. Prior reference snapshots
    must be known at target start; target closed at as-of. This describes
    intrabar high-low range, not true range/ATR or multibar base width.
    No omitted-bar certification, automatic fallback or approved threshold.
    """
    require_utc(as_of_utc)
    _check_plan397(plan)
    if type(history) is not tuple or len(history) != plan.reference_count + 1:
        return RangePercentileCandidate397("EXACT_REFERENCE_TARGET_HISTORY_REQUIRED")
    rows, reason = _validate_ordered_bars(history, as_of_utc, as_of_utc, Timeframe.D1)
    if rows is None:
        return RangePercentileCandidate397("INPUT_" + reason)
    cutoff = rows[-1].market_bar_key.bar_start_utc
    prior, reason = _validate_ordered_bars(history[:-1], as_of_utc, cutoff, Timeframe.D1)
    if prior is None:
        return RangePercentileCandidate397("REFERENCE_" + reason)
    reference = tuple(_range_pct397(row) for row in prior)
    target = _range_pct397(rows[-1])
    if target is None or any(v is None for v in reference):
        return RangePercentileCandidate397("NORMALIZED_RANGE_UNAVAILABLE")
    rank = int((plan.quantile * Decimal(plan.reference_count)).to_integral_value(rounding=ROUND_CEILING))
    threshold = sorted(reference)[rank-1]
    return RangePercentileCandidate397("RANGE_PERCENTILE_GEOMETRY_ONLY", target, threshold,
                                       plan.reference_count, target <= threshold)
