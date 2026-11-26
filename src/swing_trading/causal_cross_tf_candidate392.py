"""§392 explicit H1 closed cross of a D1 upper pivot, descriptive only."""
from decimal import Decimal

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    BosGeometry, GeometryState, StructureSide, TiePolicy, _cross_tf_identity,
    _eligible, _source_identity, inspect_causal_pivot,
)
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12


def _blocked392(reason):
    return BosGeometry(StructureSide.HIGH, GeometryState.BLOCKED, reason,
                       None, None, None, None, None)


def _pair392(previous, breakout, as_of_utc):
    target = _eligible(breakout, cutoff=as_of_utc)
    if target is None or target.market_bar_key.timeframe is not Timeframe.H1:
        return None, None, "H1_TARGET_NOT_CLOSED_OR_KNOWN"
    prior = _eligible(previous, cutoff=target.market_bar_key.bar_start_utc)
    if prior is None or prior.market_bar_key.timeframe is not Timeframe.H1:
        return None, None, "H1_PREVIOUS_NOT_KNOWN_BEFORE_TARGET"
    if (prior.bar_end_utc > target.market_bar_key.bar_start_utc
            or prior.market_bar_key == target.market_bar_key
            or _source_identity(prior) != _source_identity(target)):
        return None, None, "H1_PAIR_IDENTITY_OR_CLOCK_MISMATCH"
    return prior, target, ""


def _pivot392(history, prior, target, *, pivot_index, left_count, right_count, tie_policy):
    if (type(history) is not tuple or not history
            or any(type(x) is not ResolvedBarSnapshotV12
                   or x.market_bar_key.timeframe is not Timeframe.D1 for x in history)):
        return None, "D1_PIVOT_HISTORY_MISSING_OR_WRONG_TF"
    # Require the whole explicit D1 context and right-bar confirmation
    # already available at the previous H1 start, not retroactive crossing.
    pivot = inspect_causal_pivot(
        history, candidate_index=pivot_index, left_count=left_count, right_count=right_count,
        side=StructureSide.HIGH, tie_policy=tie_policy,
        as_of_utc=prior.market_bar_key.bar_start_utc,
    )
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return None, "D1_PIVOT_" + pivot.reason
    if not pivot.geometric_extremum:
        return None, "D1_PIVOT_NOT_STRUCTURAL_EXTREMUM"
    right = history[pivot_index+right_count].selected
    if _cross_tf_identity(right) != _cross_tf_identity(target):
        return None, "D1_PIVOT_H1_SOURCE_BASIS_MISMATCH"
    return pivot, ""


def _atr392(history, target, cutoff):
    atr = calculate_wilder_atr14(history, as_of_utc=cutoff,
                                 known_before_utc=target.market_bar_key.bar_start_utc)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return None, "ATR14_" + atr.reason
    if _cross_tf_identity(history[0].selected) != _cross_tf_identity(target):
        return None, "ATR14_H1_SOURCE_BASIS_MISMATCH"
    return atr.value, ""


def inspect_h1_cross_of_d1_upper_pivot(pivot_history, *, pivot_index, left_count, right_count,
                                      previous, breakout, atr_d1_history, tie_policy,
                                      candidate_epsilon, as_of_utc):
    """Explicit D1/H1 route; never weaken or replace the generic BOS route.

    Different native TF stream IDs are allowed only under matched cross-TF
    identity. Exact prior/target H1 must match their full source identity.
    Pivot history must be known before prior H1 starts, ATR before target.
    No continuity, calendar, volume, execution or approved signal claim.
    """
    require_utc(as_of_utc)
    if (type(tie_policy) is not TiePolicy or type(candidate_epsilon) is not Decimal
            or not candidate_epsilon.is_finite() or candidate_epsilon < 0):
        raise ValueError("MST_392_EXPLICIT_H1_CROSS_CONFIG")
    prior, target, reason = _pair392(previous, breakout, as_of_utc)
    if reason:
        return _blocked392(reason)
    pivot, reason = _pivot392(pivot_history, prior, target, pivot_index=pivot_index,
                              left_count=left_count, right_count=right_count, tie_policy=tie_policy)
    if reason:
        return _blocked392(reason)
    atr, reason = _atr392(atr_d1_history, target, as_of_utc)
    if reason:
        return _blocked392(reason)
    boundary = pivot.pivot_price + candidate_epsilon * atr
    if not boundary.is_finite() or boundary < 0:
        return _blocked392("BUFFER_BOUNDARY_NOT_FINITE_OR_NEGATIVE")
    return BosGeometry(StructureSide.HIGH, GeometryState.DESCRIPTIVE_ONLY,
                       "D1_UPPER_PIVOT_H1_CLOSED_CROSS_ONLY",
                       boundary, prior.close, target.close,
                       prior.close <= boundary < target.close,
                       max(pivot.witness_known_at_utc, prior.verified_at_utc,
                           target.verified_at_utc, target.bar_end_utc))
