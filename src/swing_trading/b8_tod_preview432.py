"""§432 selected-variant raw-prefix TOD candidate threshold."""
from dataclasses import replace
from decimal import Decimal

from .causal_indicators import IndicatorState
from .market_data import Timeframe
from .rvol_tod_contract import (TODCumulativeObservation, TODRawPrefix,
                                calculate_rvol_tod20_from_raw_prefixes)


def validate_tod432(p, variant_id, k, *, plan_type):
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<=0):
        raise ValueError("MST_432_EXPLICIT_POSITIVE_TOD_THRESHOLD")
    if p is None and k is None:
        return
    if variant_id != "B8/INTRADAY_RVOL_TOD_PENDING":
        raise ValueError("MST_420_EXPLICIT_TOD_VARIANT")
    if p is None:
        return
    if type(p) is not plan_type:
        raise ValueError("MST_420_EXPLICIT_TOD_VARIANT")
    if (type(p.target) is not TODCumulativeObservation or type(p.target_prefix) is not TODRawPrefix
            or type(p.prior_sessions) is not tuple or len(p.prior_sessions) != 20
            or any(type(x) is not TODCumulativeObservation for x in p.prior_sessions)
            or type(p.prior_prefixes) is not tuple or len(p.prior_prefixes) != 20
            or any(type(x) is not TODRawPrefix for x in p.prior_prefixes)):
        raise ValueError("MST_420_EXACT_TOD_PLAN")


def inspect_early_tod432(inputs, p, geometry, *, states):
    tod = p.early.tod
    k = p.early.candidate_min_rvol_tod
    if geometry.state is not states.MATCH:
        return geometry
    if tod is None:
        if k is not None:
            return replace(geometry,state=states.MISSING,reason="RE_EXPLICIT_TOD_WITNESS_REQUIRED")
        return geometry
    rows = inputs.snapshots_for(Timeframe.M15)
    index = p.target_index + 2
    if tod.target.snapshot != rows[index]:
        return replace(geometry, state=states.BLOCKED, reason="TOD_TARGET_NOT_BOUND",
                       volume_state="TOD_BLOCKED")
    if any(x.snapshot not in rows[:index] for x in tod.prior_sessions):
        return replace(geometry, state=states.BLOCKED, reason="TOD_PRIOR_NOT_BOUND",
                       volume_state="TOD_BLOCKED")
    cutoff = inputs.as_of_utc if k is None else rows[index].selected.verified_at_utc
    result = calculate_rvol_tod20_from_raw_prefixes(tod.target, tod.prior_sessions,
        target_prefix=tod.target_prefix, prior_prefixes=tod.prior_prefixes,
        as_of_utc=cutoff)
    if result.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return replace(geometry, state=states.BLOCKED, reason="TOD_RAW_PREFIX_BLOCKED",
                       volume_state="TOD_BLOCKED", rvol=result)
    return _threshold432(geometry,result,k,states)


def _threshold432(geometry,result,k,states):
    bound=replace(geometry,reason="RE_CROSS_AND_RAW_TOD_ARITHMETIC_ONLY",
                  volume_state="TOD_COMPUTED_UNCALIBRATED",rvol=result)
    if k is None:
        return bound
    match=result.value>=k
    state=states.MATCH if match else states.NONMATCH
    return replace(bound,state=state,reason="RE_EXPLICIT_RAW_TOD_THRESHOLD_CANDIDATE_ONLY",
                   tod_candidate_match=match)


