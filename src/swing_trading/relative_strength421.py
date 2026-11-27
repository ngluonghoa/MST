"""§421 explicit aligned adjusted-close log RS and endpoint slope candidate."""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import Enum

from .causal_structure_geometry import _sequence
from .market_data import InstrumentClass, PriceBasis, Timeframe
from .replay import require_utc


class RSBenchmark421(str, Enum):
    SECTOR = "SECTOR"
    INDEX = "INDEX"


@dataclass(frozen=True)
class RSPlan421:
    stock_start: int
    stock_stop: int
    horizon: int
    slope_window: int
    benchmark_kind: RSBenchmark421
    benchmark_id: str
    alignment_policy_version: str
    benchmark_rows: tuple
    candidate_min_slope: Decimal | None


@dataclass(frozen=True)
class RSResult421:
    state: str
    reason: str
    current_rs: Decimal | None = None
    slope: Decimal | None = None
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def _validate_window421(p):
    if any(type(x) is not int for x in (p.stock_start,p.stock_stop,p.horizon,p.slope_window)):
        raise ValueError("MST_421_EXPLICIT_INTEGER_WINDOWS")
    if not 0 <= p.stock_start < p.stock_stop <= 512:
        raise ValueError("MST_421_BOUNDED_STOCK_SLICE")
    if min(p.horizon,p.slope_window) < 1 or p.stock_stop-p.stock_start != p.horizon+p.slope_window+1:
        raise ValueError("MST_421_EXACT_H_PLUS_N_PLUS_1")


def validate_rs421(p):
    if type(p) is not RSPlan421 or type(p.benchmark_kind) is not RSBenchmark421:
        raise ValueError("MST_421_EXPLICIT_BENCHMARK")
    _validate_window421(p)
    for v in (p.benchmark_id,p.alignment_policy_version):
        if type(v) is not str or not v.strip():
            raise ValueError("MST_421_EXPLICIT_BENCHMARK_ID_AND_POLICY")
    if type(p.benchmark_rows) is not tuple or len(p.benchmark_rows) != p.stock_stop-p.stock_start:
        raise ValueError("MST_421_EXACT_BENCHMARK_WINDOW")
    k=p.candidate_min_slope
    if k is not None and (type(k) is not Decimal or not k.is_finite()):
        raise ValueError("MST_421_EXPLICIT_SLOPE_THRESHOLD")


def _scope421(stock, benchmark, p):
    a,b=stock.market_bar_key,benchmark.market_bar_key
    return (a.instrument_class is InstrumentClass.STOCK
            and b.instrument_class is InstrumentClass.INDEX
            and a.instrument_id != b.instrument_id == p.benchmark_id
            and a.timeframe is b.timeframe is Timeframe.D1
            and a.price_basis is b.price_basis is PriceBasis.ADJUSTED
            and a.calendar_version == b.calendar_version
            and a.exchange == b.exchange
            and stock.observation_key.project_id == benchmark.observation_key.project_id)


def _aligned421(stock, benchmark):
    return all(a.market_bar_key.bar_start_utc == b.market_bar_key.bar_start_utc
               and a.bar_end_utc == b.bar_end_utc and a.close > 0 and b.close > 0
               for a,b in zip(stock,benchmark))


def _newer_supplied421(rows, cutoff):
    return any(s.market_bar_key.bar_start_utc < cutoff
               and (s.selected is None or s.selected.bar_end_utc <= cutoff)
               for s in rows)


def _math421(stock, benchmark, p):
    with localcontext() as ctx:
        ctx.prec=50
        def value(i):
            h=p.horizon
            return (stock[i].close/stock[i-h].close).ln()-(benchmark[i].close/benchmark[i-h].close).ln()
        current=value(len(stock)-1)
        slope=(current-value(p.horizon))/Decimal(p.slope_window)
    match=None if p.candidate_min_slope is None else slope >= p.candidate_min_slope
    return RSResult421("COMPUTED_UNCALIBRATED","LOG_RS_AND_ENDPOINT_SLOPE_ONLY",current,slope,match)


def inspect_rs421(daily, p, *, cutoff):
    require_utc(cutoff)
    validate_rs421(p)
    if type(daily) is not tuple or p.stock_stop > len(daily):
        return RSResult421("MISSING_INPUT","EXACT_STOCK_WINDOW_MISSING")
    if _newer_supplied421(daily[p.stock_stop:],cutoff):
        return RSResult421("BLOCKED","NEWER_OR_UNRESOLVED_D1_STOCK_ROW")
    stock,_=_sequence(daily[p.stock_start:p.stock_stop],cutoff=cutoff)
    benchmark,_=_sequence(p.benchmark_rows,cutoff=cutoff)
    if stock is None or benchmark is None:
        return RSResult421("BLOCKED","RS_WINDOW_NOT_CAUSALLY_AVAILABLE")
    if not _scope421(stock[0],benchmark[0],p) or not _aligned421(stock,benchmark):
        return RSResult421("BLOCKED","RS_SCOPE_OR_ALIGNMENT_MISMATCH")
    return _math421(stock,benchmark,p)
