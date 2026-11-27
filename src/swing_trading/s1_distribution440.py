"""§440 explicit D1 resistance rejection and raw matched volume candidate."""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .causal_indicators import (
    CausalIndicatorResult, IndicatorState, VolumeBasisWitness, VolumeComparisonBar,
    VolumeSessionClass, calculate_rvol_tf20_raw_matched,
)
from .causal_structure_geometry import _cross_tf_identity, _eligible
from .market_data import PriceBasis, Timeframe


@dataclass(frozen=True)
class S1DistributionPlan440:
    target_index: int
    comparison_policy: str
    witnesses: tuple[VolumeBasisWitness, ...]
    candidate_min_rvol: Decimal | None
    candidate_max_close_location: Decimal | None


def _threshold440(value,upper=None):
    return (type(value) is Decimal and value.is_finite() and value>=0
            and (upper is None or value<=upper))


def validate_distribution440(p):
    if type(p) is not S1DistributionPlan440:
        raise ValueError("MST_440_EXPLICIT_DISTRIBUTION")
    if type(p.target_index) is not int or not 0<=p.target_index<512:
        raise ValueError("MST_440_EXPLICIT_INDEX")
    if type(p.comparison_policy) is not str or not p.comparison_policy.strip():
        raise ValueError("MST_440_EXPLICIT_COMPARISON_POLICY")
    if type(p.witnesses) is not tuple or len(p.witnesses)!=21:
        raise ValueError("MST_440_EXACT_21_WITNESSES")
    if any(type(w) is not VolumeBasisWitness for w in p.witnesses):
        raise ValueError("MST_440_EXACT_WITNESS_TYPE")
    k,q=p.candidate_min_rvol,p.candidate_max_close_location
    if k is not None and (not _threshold440(k) or k==0):
        raise ValueError("MST_440_POSITIVE_RVOL")
    if q is not None and not _threshold440(q,Decimal(1)):
        raise ValueError("MST_440_CLOSE_LOCATION_RANGE")


def _rvol440(rows,p,target):
    tagged=tuple(VolumeComparisonBar(s,VolumeSessionClass.DAILY,p.comparison_policy)
                 for s in rows)
    return calculate_rvol_tf20_raw_matched(tagged[-1],tagged[:-1],
        target_witness=p.witnesses[-1],prior_witnesses=p.witnesses[:-1],
        as_of_utc=target.verified_at_utc)


def _metrics440(target,p,resistance,rvol,states,ingredient):
    if target.high<=target.low:
        return ingredient(states.BLOCKED,"ZERO_RANGE_DISTRIBUTION",rvol=rvol)
    with localcontext() as ctx:
        ctx.prec=50
        location=(target.close-target.low)/(target.high-target.low)
        shape=target.high>=resistance and target.close<=resistance
        k,q=p.candidate_min_rvol,p.candidate_max_close_location
        if not shape:
            state=states.NONMATCH
        elif k is None or q is None:
            state=states.DISTANCE
        else:
            match=rvol.value>=k and target.close-target.low<=q*(target.high-target.low)
            state=states.MATCH if match else states.NONMATCH
    return ingredient(state,"D1_RAW_RVOL_WEAK_CLOSE_AT_RESISTANCE_CANDIDATE",
                      rvol=rvol,close_location=location)


def inspect_distribution440(inputs,plan,base,*,states,ingredient):
    p=plan.distribution
    validate_distribution440(p)
    if base.state is not states.MATCH:
        return ingredient(states.BLOCKED,"R0_CONTEXT_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.D1)
    i=p.target_index
    if i<20 or i>=len(rows):
        return ingredient(states.MISSING,"EXACT_D1_TARGET_OR_PRIOR20_MISSING")
    target=_eligible(rows[i],cutoff=inputs.as_of_utc)
    anchor=inputs.snapshots_for(Timeframe.M15)[plan.target_index].selected
    if target is None:
        return ingredient(states.BLOCKED,"DISTRIBUTION_TARGET_NOT_ELIGIBLE")
    if (target.market_bar_key.bar_start_utc<anchor.verified_at_utc
            or target.market_bar_key.price_basis is not PriceBasis.RAW
            or _cross_tf_identity(target)!=_cross_tf_identity(anchor)):
        return ingredient(states.BLOCKED,"DISTRIBUTION_CAUSAL_RAW_SCOPE")
    rvol=_rvol440(rows[i-20:i+1],p,target)
    if rvol.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return ingredient(states.BLOCKED,"DISTRIBUTION_RAW_WITNESS_BLOCKED",rvol=rvol)
    return _metrics440(target,p,base.private_resistance,rvol,states,ingredient)
