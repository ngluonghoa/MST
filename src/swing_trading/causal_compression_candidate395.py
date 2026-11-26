"""§395 normalized D1 ATR compression percentile candidate, not approved VCP."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from .causal_indicators import IndicatorState, _validate_ordered_bars, calculate_wilder_atr14
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class AtrPercentilePlan395:
    reference_count: int
    quantile: Decimal


@dataclass(frozen=True)
class CompressionCandidate395:
    reason: str
    target_atr_percent: Decimal | None = None
    reference_threshold_percent: Decimal | None = None
    reference_count: int = 0
    at_or_below: bool | None = None

    def safe_summary(self):
        return {
            "schema": "mst.private.atr_compression_candidate.v0.1",
            "reason": self.reason, "at_or_below": self.at_or_below,
            "compression_verified": False, "parameter_approved": False,
            "source_qualified": False, "action_eligible": False,
        }


def _check_plan395(plan):
    if type(plan) is not AtrPercentilePlan395:
        raise ValueError("MST_395_EXPLICIT_PERCENTILE_PLAN")
    if type(plan.reference_count) is not int or not 2 <= plan.reference_count <= 497:
        raise ValueError("MST_395_BOUNDED_REFERENCE_COUNT")
    q = plan.quantile
    if type(q) is not Decimal or not q.is_finite() or not 0 < q <= 1:
        raise ValueError("MST_395_EXPLICIT_QUANTILE")


def _atr_pct395(history, cutoff):
    atr = calculate_wilder_atr14(history, as_of_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return None
    close = history[-1].selected.close
    if close <= 0:
        return None
    return atr.value * Decimal(100) / close


def _reference395(history, cutoff):
    # All references share the same initial ATR seed. This is the prefix
    # available at target start, NOT a reconstructed earlier as-known replay.
    return tuple(_atr_pct395(history[:end], cutoff)
                 for end in range(15, len(history)))


def inspect_atr_percentile_candidate(history, *, plan, as_of_utc):
    """Exact 15+N D1 snapshots: N prior normalized ATRs and a distinct target.

    Prior reference prefix must be known before the target starts; target
    must be closed and known at the decision cutoff. Nearest-rank quantile
    ceil(q*N), inclusive <= comparison, with no implicit q or window.
    No calendar continuity, volume dry-up or approved compression predicate.
    """
    require_utc(as_of_utc)
    _check_plan395(plan)
    if type(history) is not tuple or len(history) != 15 + plan.reference_count:
        return CompressionCandidate395("EXACT_SEED_REFERENCE_TARGET_HISTORY_REQUIRED")
    rows, reason = _validate_ordered_bars(history, as_of_utc, as_of_utc, Timeframe.D1)
    if rows is None:
        return CompressionCandidate395("INPUT_" + reason)
    cutoff = rows[-1].market_bar_key.bar_start_utc
    prior, reason = _validate_ordered_bars(history[:-1], as_of_utc, cutoff, Timeframe.D1)
    if prior is None:
        return CompressionCandidate395("REFERENCE_" + reason)
    reference = _reference395(history, cutoff)
    target = _atr_pct395(history, as_of_utc)
    if target is None or any(v is None for v in reference):
        return CompressionCandidate395("NORMALIZED_ATR_UNAVAILABLE")
    rank = int((plan.quantile * Decimal(plan.reference_count)).to_integral_value(rounding=ROUND_CEILING))
    threshold = sorted(reference)[rank-1]
    return CompressionCandidate395("ATR_PERCENTILE_GEOMETRY_ONLY", target, threshold,
                                   plan.reference_count, target <= threshold)
