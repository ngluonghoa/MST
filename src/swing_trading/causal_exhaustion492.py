"""§492 causal D1 return, prior ATR normalized range, raw matched volume distribution."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from .causal_indicators import (
    IndicatorState, VolumeBasisWitness, VolumeComparisonBar, VolumeSessionClass,
    _raw_volume_witness_ok, _validate_ordered_bars, calculate_wilder_atr14,
)
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class ExhaustionFeaturePlan492:
    start: int
    target_index: int
    return_span: int
    reference_count: int
    quantile: Decimal
    comparison_policy: str
    witnesses: tuple[VolumeBasisWitness, ...]


@dataclass(frozen=True)
class ExhaustionFeatures492:
    reason: str
    target_return: Decimal | None = None
    reference_return: Decimal | None = None
    target_range_atr: Decimal | None = None
    reference_range_atr: Decimal | None = None
    target_volume: int | None = None
    reference_volume: int | None = None


def validate_features492(p):
    if type(p) is not ExhaustionFeaturePlan492:
        raise ValueError("MST_492_EXPLICIT_FEATURE_PLAN")
    if any(type(x) is not int for x in (p.start,p.target_index,p.return_span,p.reference_count)):
        raise ValueError("MST_492_EXPLICIT_INTEGER_WINDOWS")
    if not 0<=p.start<p.target_index<512 or not 5<=p.return_span<=10 or not 2<=p.reference_count<=128:
        raise ValueError("MST_492_BOUNDED_WINDOWS")
    if p.target_index-p.start<p.return_span+p.reference_count+15:
        raise ValueError("MST_492_CAUSAL_WARMUP")
    if type(p.quantile) is not Decimal or not p.quantile.is_finite() or not 0<p.quantile<=1:
        raise ValueError("MST_492_EXPLICIT_QUANTILE")
    if type(p.comparison_policy) is not str or not p.comparison_policy.strip():
        raise ValueError("MST_492_COMPARISON_POLICY")
    if type(p.witnesses) is not tuple or len(p.witnesses)!=p.reference_count+1:
        raise ValueError("MST_492_EXACT_VOLUME_WITNESSES")
    if any(type(w) is not VolumeBasisWitness for w in p.witnesses):
        raise ValueError("MST_492_WITNESS_TYPE")


def _reference_indices492(p):
    end=p.target_index-p.start-p.return_span
    return tuple(range(end-p.reference_count,end))


def _sample492(history,rows,i,span,as_of):
    row=rows[i]
    prior=rows[i-span]
    cutoff=row.market_bar_key.bar_start_utc
    if prior.close<=0 or row.close<=0 or any(x.verified_at_utc>cutoff for x in rows[i-span:i]):
        return None
    atr=calculate_wilder_atr14(history[:i],as_of_utc=as_of,known_before_utc=cutoff)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None:
        return None
    return (row.close/prior.close-Decimal(1),(row.high-row.low)/atr.value,row.volume)


def _volume492(history,indices,p,cutoff,as_of):
    for i,w in zip(indices,p.witnesses):
        tagged=VolumeComparisonBar(history[i],VolumeSessionClass.DAILY,p.comparison_policy)
        limit=as_of if i==indices[-1] else cutoff
        if not _raw_volume_witness_ok(tagged,w,limit):
            return False
    return all(w.share_regime_id==p.witnesses[0].share_regime_id for w in p.witnesses)


def _summary492(samples,p):
    ref,target=samples[:-1],samples[-1]
    rank=int((p.quantile*Decimal(p.reference_count)).to_integral_value(rounding=ROUND_CEILING))-1
    if not any(x[2]>0 for x in ref):
        return ExhaustionFeatures492("ZERO_REFERENCE_VOLUME")
    thresholds=tuple(sorted(x[j] for x in ref)[rank] for j in range(3))
    return ExhaustionFeatures492("EXACT_D1_DISTRIBUTION_CANDIDATE_ONLY",
        target[0],thresholds[0],target[1],thresholds[1],target[2],thresholds[2])


def inspect_exhaustion_features492(rows,*,plan,as_of_utc):
    """Non-overlapping target return window; prior ATR for each endpoint.
    
    The reference distribution uses supplied historical observations only.
    Nearest rank is explicit candidate math, not approved threshold or
    calendar completeness. Raw share witnesses are not source attestation.
    """
    require_utc(as_of_utc)
    validate_features492(plan)
    p=plan
    if type(rows) is not tuple or p.target_index>=len(rows):
        return ExhaustionFeatures492("EXACT_HISTORY_MISSING")
    history=rows[p.start:p.target_index+1]
    bars,reason=_validate_ordered_bars(history,as_of_utc,as_of_utc,Timeframe.D1)
    if bars is None:
        return ExhaustionFeatures492("HISTORY_"+reason)
    indices=_reference_indices492(p)+(len(bars)-1,)
    cutoff=bars[-1-p.return_span].market_bar_key.bar_start_utc
    if not _volume492(history,indices,p,cutoff,bars[-1].verified_at_utc):
        return ExhaustionFeatures492("RAW_MATCHED_VOLUME_UNRESOLVED")
    samples=tuple(_sample492(history,bars,i,p.return_span,as_of_utc) for i in indices)
    if any(x is None for x in samples):
        return ExhaustionFeatures492("CAUSAL_RETURN_OR_ATR_UNRESOLVED")
    return _summary492(samples,p)
