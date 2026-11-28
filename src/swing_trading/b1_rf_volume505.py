"""§505 independent same-frame raw matched volume, candidate only."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_indicators import (
    CausalIndicatorResult, IndicatorState, VolumeBasisWitness, VolumeComparisonBar,
    VolumeSessionClass, calculate_rvol_tf20_raw_matched,
)
from .market_data import PriceBasis, Timeframe
from .s1_context_preview439 import S1State439
from .b1_confirm504 import B1ConfirmPlan504,B1ConfirmIngredient504,inspect_b1_confirm504_preview
from .b1_decline499 import B1Preview499


@dataclass(frozen=True)
class B1RFVolumePlan505:
    comparison_policy_version: str
    session_classes: tuple[VolumeSessionClass, ...]
    witnesses: tuple[VolumeBasisWitness, ...]
    candidate_min_rvol: Decimal | None


@dataclass(frozen=True)
class B1VolumePlan505:
    geometry: B1ConfirmPlan504
    volume: B1RFVolumePlan505


@dataclass(frozen=True)
class B1VolumeIngredient505:
    state: S1State439
    reason: str
    private_geometry: B1ConfirmIngredient504
    private_rvol: CausalIndicatorResult | None = None


def _validate505(p):
    if type(p) is not B1RFVolumePlan505:
        raise ValueError("MST_505_EXACT_VOLUME_PLAN")
    if type(p.comparison_policy_version) is not str or not p.comparison_policy_version.strip():
        raise ValueError("MST_505_EXPLICIT_COMPARISON_POLICY")
    if type(p.session_classes) is not tuple or len(p.session_classes)!=21 or any(
            type(x) is not VolumeSessionClass for x in p.session_classes):
        raise ValueError("MST_505_EXACT_SESSION_CLASSES")
    if type(p.witnesses) is not tuple or len(p.witnesses)!=21 or any(
            type(x) is not VolumeBasisWitness for x in p.witnesses):
        raise ValueError("MST_505_EXACT_VOLUME_WITNESSES")
    k=p.candidate_min_rvol
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<=0):
        raise ValueError("MST_505_EXPLICIT_POSITIVE_RVOL")


def _compute505(rows,p,target):
    bars=tuple(VolumeComparisonBar(x,s,p.comparison_policy_version)
               for x,s in zip(rows,p.session_classes))
    return calculate_rvol_tf20_raw_matched(
        bars[-1],bars[:-1],target_witness=p.witnesses[-1],
        prior_witnesses=p.witnesses[:-1],as_of_utc=target.verified_at_utc)


def _apply505(inputs,plan,proof):
    g,p=plan.geometry,plan.volume
    rows=inputs.snapshots_for(Timeframe.D1)
    i=g.target_index
    if i<20 or i>=len(rows):
        return B1VolumeIngredient505(S1State439.MISSING,"RF_EXACT_PRIOR20_MISSING",proof)
    target=rows[i].selected
    if target is None or target.market_bar_key.price_basis is not PriceBasis.RAW:
        return B1VolumeIngredient505(S1State439.BLOCKED,"RF_RAW_PRICE_REQUIRED",proof)
    r=_compute505(rows[i-20:i+1],p,target)
    if r.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return B1VolumeIngredient505(S1State439.BLOCKED,"RF_RAW_VOLUME_WITNESS_BLOCKED",proof,r)
    if p.candidate_min_rvol is None:
        state=S1State439.DISTANCE
    else:
        state=S1State439.MATCH if r.value>=p.candidate_min_rvol else S1State439.NONMATCH
    return B1VolumeIngredient505(state,"RF_SAME_FRAME_RAW_MATCHED_RVOL_CANDIDATE_ONLY",proof,r)


def inspect_b1_volume505_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not B1VolumePlan505 or type(plan.geometry) is not B1ConfirmPlan504:
        raise ValueError("MST_505_EXACT_RF_GEOMETRY_PLAN")
    _validate505(plan.volume)
    preview=inspect_b1_confirm504_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.geometry)
    route,proof=preview.assessments[-1]
    if proof.state is not S1State439.MATCH:
        return preview
    return B1Preview499(preview.assessments[:-1]+((route,_apply505(inputs,plan,proof)),))
