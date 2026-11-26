"""§382 explicit paired D1 pivot and SMA50 candidate geometry, not trend approval."""
from .causal_indicators import IndicatorState, calculate_d1_sma50_delta_candidate
from .causal_structure_geometry import GeometryState, StructureSide, TiePolicy, inspect_causal_pivot


def _result(structure, slope, relation):
    return {
        "schema": "mst.private.d1_paired_trend_candidate.v0.1",
        "structure": structure, "sma50_delta_direction": slope, "relation": relation,
        "trend_verified": False, "parameter_approved": False,
        "source_qualified": False, "action_eligible": False,
    }


def _direction(a, b):
    return "RISING" if b > a else "FALLING" if b < a else "FLAT"


def _validate_plan(high_indices, low_indices, left_count, right_count, tie_policy):
    if type(high_indices) is not tuple or type(low_indices) is not tuple:
        raise ValueError("MST_382_EXPLICIT_PIVOT_PAIRS_REQUIRED")
    if any(len(pair) not in (0, 2) for pair in (high_indices, low_indices)):
        raise ValueError("MST_382_EMPTY_OR_EXACT_PAIR_REQUIRED")
    if any(type(i) is not int or i < 0 for i in high_indices + low_indices):
        raise ValueError("MST_382_INVALID_PIVOT_INDEX")
    if (type(left_count) is not int or not 1 <= left_count <= 40
            or type(right_count) is not int or not 1 <= right_count <= 40
            or type(tie_policy) is not TiePolicy):
        raise ValueError("MST_382_INVALID_PIVOT_POLICY")


def _paired_order(highs, lows):
    return (highs[0] < lows[0] < highs[1] < lows[1]
            or lows[0] < highs[0] < lows[1] < highs[1])


def _inspect_pair(history, indices, side, policy, as_of_utc):
    return tuple(inspect_causal_pivot(
        history, candidate_index=i, side=side, as_of_utc=as_of_utc, **policy,
    ) for i in indices)


def _structure_state(history, highs, lows, policy, cutoff):
    if not highs or not lows:
        return "MISSING_PAIR"
    if not _paired_order(highs, lows):
        return "INCONSISTENT_ORDER"
    hp = _inspect_pair(history, highs, StructureSide.HIGH, policy, cutoff)
    lp = _inspect_pair(history, lows, StructureSide.LOW, policy, cutoff)
    if any(p.state is GeometryState.BLOCKED for p in hp + lp):
        return "BLOCKED_PIVOT"
    if any(p.geometric_extremum is not True for p in hp + lp):
        return "NON_EXTREMUM"
    h, l = (_direction(pair[0].pivot_price, pair[1].pivot_price) for pair in (hp, lp))
    if h == l == "RISING":
        return "HH_HL_GEOMETRY"
    if h == l == "FALLING":
        return "LH_LL_GEOMETRY"
    if h == l == "FLAT":
        return "FLAT_PAIRS"
    return "MIXED_PAIRS"


def _relation(structure, slope):
    if (structure, slope) in (("HH_HL_GEOMETRY", "RISING"), ("LH_LL_GEOMETRY", "FALLING")):
        return "ALIGNED_GEOMETRY_ONLY"
    if structure in ("HH_HL_GEOMETRY", "LH_LL_GEOMETRY"):
        return "SLOPE_FLAT" if slope == "FLAT" else "DIRECTION_CONFLICT"
    return "INSUFFICIENT_DIRECTIONAL_GEOMETRY"


def inspect_d1_paired_trend_candidate(history, *, high_indices, low_indices,
                                     left_count, right_count, tie_policy, lookback, as_of_utc):
    """One exact 50+N D1 history for both ingredients, same cutoff.

    Caller supplies candidate pairs; alternation is a conservative versioned
    diagnostic choice, not an approved selection of latest pivots. All pivots
    must have right-bar witnesses by the common cutoff, not earlier replay.
    No automatic sideways, fallback, calendar continuity or signal.
    """
    _validate_plan(high_indices, low_indices, left_count, right_count, tie_policy)
    sma = calculate_d1_sma50_delta_candidate(history, lookback=lookback, as_of_utc=as_of_utc)
    if sma.state is IndicatorState.BLOCKED:
        return _result("NOT_EVALUATED", "BLOCKED", "BLOCKED_INPUT")
    slope = _direction(sma.earlier_sma50, sma.current_sma50)
    policy = dict(left_count=left_count, right_count=right_count, tie_policy=tie_policy)
    structure = _structure_state(history, high_indices, low_indices, policy, as_of_utc)
    return _result(structure, slope, _relation(structure, slope))
