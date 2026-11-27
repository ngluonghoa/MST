"""§434 explicit aligned independent raw/adjusted D1 stock streams."""
from dataclasses import dataclass

from .causal_structure_geometry import _sequence
from .market_data import InstrumentClass, PriceBasis, Timeframe
from .relative_strength421 import (RSResult421, inspect_rs421, inspect_rs_confirmation422,
                                   _newer_supplied421)
from .source_quality import ResolvedBarSnapshotV12


@dataclass(frozen=True)
class B8RSStockPlan434:
    adjusted_daily: tuple[ResolvedBarSnapshotV12, ...]
    alignment_policy: str


def validate_stock434(p):
    if type(p) is not B8RSStockPlan434:
        raise ValueError("MST_434_EXPLICIT_ADJUSTED_STOCK_PLAN")
    if type(p.alignment_policy) is not str or not p.alignment_policy.strip():
        raise ValueError("MST_434_EXPLICIT_ALIGNMENT_POLICY")
    if type(p.adjusted_daily) is not tuple or not 1<=len(p.adjusted_daily)<=512:
        raise ValueError("MST_434_BOUNDED_ADJUSTED_STREAM")
    if any(type(x) is not ResolvedBarSnapshotV12 for x in p.adjusted_daily):
        raise ValueError("MST_434_EXACT_ADJUSTED_SNAPSHOTS")


def _identity434(row):
    k,o=row.market_bar_key,row.observation_key
    return (k.instrument_id,k.exchange,k.instrument_class,k.timeframe,k.calendar_version,
            k.session_period_id,k.bar_start_utc,row.bar_end_utc,o.project_id,o.provider_id)


def _aligned434(raw,adj):
    a,b=raw.market_bar_key,adj.market_bar_key
    return (a.price_basis is PriceBasis.RAW and b.price_basis is PriceBasis.ADJUSTED
            and a.timeframe is Timeframe.D1 and a.instrument_class is InstrumentClass.STOCK
            and _identity434(raw)==_identity434(adj)
            and raw.observation_key.source_stream_id!=adj.observation_key.source_stream_id)


def _check_alignment434(raw,stock,p,cutoff):
    if min(len(raw),len(stock.adjusted_daily))<p.stock_stop:
        return RSResult421("MISSING_INPUT","RAW_OR_ADJUSTED_D1_WINDOW_MISSING")
    if _newer_supplied421(raw[p.stock_stop:],cutoff):
        return RSResult421("BLOCKED","RAW_D1_WINDOW_NOT_LATEST")
    a,_=_sequence(raw[p.stock_start:p.stock_stop],cutoff=cutoff)
    b,_=_sequence(stock.adjusted_daily[p.stock_start:p.stock_stop],cutoff=cutoff)
    if not a or not b or not all(_aligned434(x,y) for x,y in zip(a,b)):
        return RSResult421("BLOCKED","RAW_ADJUSTED_IDENTITY_OR_CAUSAL_ALIGNMENT")
    return None


def inspect_b8_rs434(raw,p,*,cutoff,stock=None,earlier=None):
    daily=raw
    if stock is not None:
        validate_stock434(stock)
        issue=_check_alignment434(raw,stock,p,cutoff)
        if issue is not None:
            return issue
        daily=stock.adjusted_daily
    if earlier is None:
        return inspect_rs421(daily,p,cutoff=cutoff)
    return inspect_rs_confirmation422(daily,earlier,p,cutoff=cutoff)
