"""§496 independent same-frame raw matched volume, candidate only."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_indicators import (
    CausalIndicatorResult, IndicatorState, VolumeBasisWitness, VolumeComparisonBar,
    VolumeSessionClass, calculate_rvol_tf20_raw_matched,
)
from .market_data import PriceBasis
from .s1_context_preview439 import S1State439
from .s8_context492 import S8ConfirmPlan495,S8ConfirmIngredient495,S8Preview492,inspect_s8_confirm495_preview


@dataclass(frozen=True)
class S8RFVolumePlan496:
    comparison_policy_version: str
    session_classes: tuple[VolumeSessionClass, ...]
    witnesses: tuple[VolumeBasisWitness, ...]
    candidate_min_rvol: Decimal | None


@dataclass(frozen=True)
class S8VolumePlan496:
    geometry: S8ConfirmPlan495
    volume: S8RFVolumePlan496


@dataclass(frozen=True)
class S8VolumeIngredient496:
    state: S1State439
    reason: str
    private_geometry: S8ConfirmIngredient495
    private_rvol: CausalIndicatorResult | None = None


def _validate496(p):
    if type(p) is not S8RFVolumePlan496:
        raise ValueError("MST_496_EXACT_VOLUME_PLAN")
    if type(p.comparison_policy_version) is not str or not p.comparison_policy_version.strip():
        raise ValueError("MST_496_EXPLICIT_COMPARISON_POLICY")
    if type(p.session_classes) is not tuple or len(p.session_classes)!=21 or any(
            type(x) is not VolumeSessionClass for x in p.session_classes):
        raise ValueError("MST_496_EXACT_SESSION_CLASSES")
    if type(p.witnesses) is not tuple or len(p.witnesses)!=21 or any(
            type(x) is not VolumeBasisWitness for x in p.witnesses):
        raise ValueError("MST_496_EXACT_VOLUME_WITNESSES")
    k=p.candidate_min_rvol
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<=0):
        raise ValueError("MST_496_EXPLICIT_POSITIVE_RVOL")


def _compute496(rows,p,target):
    bars=tuple(VolumeComparisonBar(x,s,p.comparison_policy_version)
               for x,s in zip(rows,p.session_classes))
    return calculate_rvol_tf20_raw_matched(
        bars[-1],bars[:-1],target_witness=p.witnesses[-1],
        prior_witnesses=p.witnesses[:-1],as_of_utc=target.verified_at_utc)


def _apply496(inputs,plan,proof):
    g,p=plan.geometry,plan.volume
    rows=inputs.snapshots_for(g.timeframe)
    i=g.target_index
    if i<20 or i>=len(rows):
        return S8VolumeIngredient496(S1State439.MISSING,"RF_EXACT_PRIOR20_MISSING",proof)
    target=rows[i].selected
    if target is None or target.market_bar_key.price_basis is not PriceBasis.RAW:
        return S8VolumeIngredient496(S1State439.BLOCKED,"RF_RAW_PRICE_REQUIRED",proof)
    r=_compute496(rows[i-20:i+1],p,target)
    if r.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return S8VolumeIngredient496(S1State439.BLOCKED,"RF_RAW_VOLUME_WITNESS_BLOCKED",proof,r)
    if p.candidate_min_rvol is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if r.value>=p.candidate_min_rvol else S1State439.NONMATCH
    return S8VolumeIngredient496(state,"RF_SAME_FRAME_RAW_MATCHED_RVOL_CANDIDATE_ONLY",proof,r)


def inspect_s8_volume496_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S8VolumePlan496 or type(plan.geometry) is not S8ConfirmPlan495:
        raise ValueError("MST_496_EXACT_RF_GEOMETRY_PLAN")
    _validate496(plan.volume)
    preview=inspect_s8_confirm495_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.geometry)
    route,proof=preview.assessments[-1]
    if proof.state is not S1State439.MATCH:
        return preview
    return S8Preview492(preview.assessments[:-1]+((route,_apply496(inputs,plan,proof)),))
