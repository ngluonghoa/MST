"""§405 extract shared B6 RF volume plans and bound calculators unchanged."""
from dataclasses import dataclass, replace

from .causal_indicators import (
    IndicatorState, VolumeBasisWitness, VolumeComparisonBar, VolumeSessionClass,
    calculate_rvol_tf20_raw_matched,
)
from .market_data import Timeframe


@dataclass(frozen=True)
class B6RFVolumePlan389:
    comparison_policy_version: str
    witnesses: tuple[VolumeBasisWitness, ...]


@dataclass(frozen=True)
class B6H1VolumePlan394:
    comparison_policy_version: str
    session_classes: tuple[VolumeSessionClass, ...]
    witnesses: tuple[VolumeBasisWitness, ...]


def _check_volume389(plan):
    if (type(plan) is not B6RFVolumePlan389
            or type(plan.comparison_policy_version) is not str
            or not plan.comparison_policy_version.strip()
            or type(plan.witnesses) is not tuple or len(plan.witnesses) != 21
            or any(type(w) is not VolumeBasisWitness for w in plan.witnesses)):
        raise ValueError("MST_389_EXACT_RAW_MATCHED_WITNESS_PLAN")


def _volume389(inputs, rf, geometry):
    if rf.volume is None:
        return replace(geometry, volume_state="RAW_MATCHED_WITNESS_MISSING")
    plan = rf.volume
    _check_volume389(plan)
    rows = inputs.snapshots_for(Timeframe.D1)
    index = rf.breakout_index
    if index < 20 or index >= len(rows):
        return replace(geometry, volume_state="EXACT_TARGET_OR_PRIOR20_MISSING")
    tagged = tuple(VolumeComparisonBar(row, VolumeSessionClass.DAILY,
                                      plan.comparison_policy_version)
                   for row in rows[index-20:index+1])
    rvol = calculate_rvol_tf20_raw_matched(
        tagged[-1], tagged[:-1], target_witness=plan.witnesses[-1],
        prior_witnesses=plan.witnesses[:-1], as_of_utc=inputs.as_of_utc,
    )
    state = ("RVOL_COMPUTED_UNCALIBRATED" if rvol.state is IndicatorState.COMPUTED_UNCALIBRATED
             else "RVOL_BLOCKED")
    return replace(geometry, volume_state=state, rvol=rvol)


def _check_h1_volume394(plan):
    if (type(plan) is not B6H1VolumePlan394
            or type(plan.comparison_policy_version) is not str
            or not plan.comparison_policy_version.strip()
            or type(plan.session_classes) is not tuple or len(plan.session_classes) != 21
            or any(type(c) is not VolumeSessionClass for c in plan.session_classes)
            or type(plan.witnesses) is not tuple or len(plan.witnesses) != 21
            or any(type(w) is not VolumeBasisWitness for w in plan.witnesses)):
        raise ValueError("MST_394_EXPLICIT_H1_VOLUME_PLAN")


def _h1_volume394(inputs, rf, geometry):
    if rf.volume is None:
        return replace(geometry, volume_state="H1_VOLUME_SPEC_PENDING")
    plan = rf.volume
    _check_h1_volume394(plan)
    rows = inputs.snapshots_for(Timeframe.H1)
    index = rf.breakout_index
    if index < 20 or index >= len(rows):
        return replace(geometry, volume_state="EXACT_TARGET_OR_PRIOR20_MISSING")
    tagged = tuple(VolumeComparisonBar(row, session, plan.comparison_policy_version)
                   for row, session in zip(rows[index-20:index+1], plan.session_classes))
    rvol = calculate_rvol_tf20_raw_matched(
        tagged[-1], tagged[:-1], target_witness=plan.witnesses[-1],
        prior_witnesses=plan.witnesses[:-1], as_of_utc=inputs.as_of_utc,
    )
    state = ("RVOL_COMPUTED_UNCALIBRATED" if rvol.state is IndicatorState.COMPUTED_UNCALIBRATED
             else "RVOL_BLOCKED")
    return replace(geometry, volume_state=state, rvol=rvol)
