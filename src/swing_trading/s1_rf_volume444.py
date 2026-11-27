"""§444 S1 independent D1 raw volume and bearish close candidate."""
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from .causal_indicators import IndicatorState, VolumeBasisWitness
from .market_data import PriceBasis, Timeframe
from .s1_distribution440 import _rvol440, validate_volume_policy440


@dataclass(frozen=True)
class S1RFVolumePlan444:
    comparison_policy: str
    witnesses: tuple[VolumeBasisWitness, ...]
    candidate_min_rvol: Decimal | None
    candidate_max_close_location: Decimal | None


def validate_volume444(p):
    if type(p) is not S1RFVolumePlan444:
        raise ValueError("MST_444_EXPLICIT_RF_VOLUME")
    validate_volume_policy440(p)


def _metrics444(target,p,rvol,geometry,states):
    if target.high<=target.low:
        return replace(geometry,state=states.BLOCKED,reason="RF_ZERO_RANGE",rvol=rvol)
    with localcontext() as ctx:
        ctx.prec=50
        location=(target.close-target.low)/(target.high-target.low)
        k,q=p.candidate_min_rvol,p.candidate_max_close_location
        if target.close>=target.open:
            state=states.NONMATCH
        elif k is None or q is None:
            state=states.DISTANCE
        else:
            match=rvol.value>=k and target.close-target.low<=q*(target.high-target.low)
            state=states.MATCH if match else states.NONMATCH
    return replace(geometry,state=state,reason="RF_RAW_RVOL_BEARISH_CLOSE_CANDIDATE_ONLY",
                   rvol=rvol,close_location=location)


def inspect_volume444(inputs,plan,geometry,*,states):
    p=plan.rf.volume
    if p is None:
        return geometry
    validate_volume444(p)
    if geometry.state is not states.MATCH:
        return geometry
    rows=inputs.snapshots_for(Timeframe.D1)
    i=plan.rf.target_index
    if i<20:
        return replace(geometry,state=states.MISSING,reason="RF_EXACT_PRIOR20_MISSING")
    target=rows[i].selected
    if target.market_bar_key.price_basis is not PriceBasis.RAW:
        return replace(geometry,state=states.BLOCKED,reason="RF_RAW_PRICE_REQUIRED")
    rvol=_rvol440(rows[i-20:i+1],p,target)
    if rvol.state is not IndicatorState.COMPUTED_UNCALIBRATED:
        return replace(geometry,state=states.BLOCKED,reason="RF_RAW_WITNESS_BLOCKED",rvol=rvol)
    return _metrics444(target,p,rvol,geometry,states)
