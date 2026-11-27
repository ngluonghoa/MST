"""§460 shared Feature Engine boundary; existing §382 causal D1 computation."""
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
