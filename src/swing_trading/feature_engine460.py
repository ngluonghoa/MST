"""§460 shared Feature Engine boundary; existing §382 causal D1 computation."""
from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import _cross_tf_identity
from .causal_trend_candidate382 import inspect_d1_paired_trend_candidate
from .market_data import Timeframe
from .private_multitf_readiness import BaselineResolvedInputs


def inspect_current_d1_context(inputs, *, lookback, high_indices, low_indices,
                               left_count, right_count, tie_policy):
    """Evaluate the same latest supplied causal window; no older fallback."""
    if type(inputs) is not BaselineResolvedInputs:
        raise TypeError("MST_460_BASELINE_INPUT_REQUIRED")
    if type(lookback) is not int or not 1 <= lookback <= 462:
        raise ValueError("MST_383_BOUNDED_LOOKBACK")
    rows = inputs.snapshots_for(Timeframe.D1)[-(50 + lookback):]
    return inspect_d1_paired_trend_candidate(
        rows, as_of_utc=inputs.as_of_utc, lookback=lookback,
        high_indices=high_indices, low_indices=low_indices,
        left_count=left_count, right_count=right_count, tie_policy=tie_policy,
    )


def inspect_target_d1_atr(inputs,p,target):
    """Existing latest supplied D1 ATR known before the target start."""
    daily=inputs.snapshots_for(Timeframe.D1)
    cutoff=target.market_bar_key.bar_start_utc
    if p.atr_stop>len(daily):
        return None
    atr=calculate_wilder_atr14(daily[p.atr_start:p.atr_stop],
                as_of_utc=inputs.as_of_utc,known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return None
    if _cross_tf_identity(daily[p.atr_start].selected)!=_cross_tf_identity(target):
        return None
    for snap in daily[p.atr_stop:]:
        if snap.selected is None and snap.market_bar_key.bar_start_utc<cutoff:
            return None
        if snap.selected is not None and snap.selected.bar_end_utc<=cutoff:
            return None
    return atr.value
