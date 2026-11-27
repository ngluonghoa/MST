"""§428 raw causal D1 liquidity candidate; not executable order capacity."""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .causal_structure_geometry import _sequence, _cross_tf_identity
from .contracts import Strategy
from .market_data import Timeframe, PriceBasis, InstrumentClass


@dataclass(frozen=True)
class B8LiquidityPlan428:
    strategy: Strategy
    start: int
    stop: int
    order_shares: int
    units_policy: str
    candidate_min_mean_turnover: Decimal | None
    candidate_max_volume_fraction: Decimal | None


@dataclass(frozen=True)
class B8LiquidityResult428:
    state: str
    reason: str
    mean_turnover: Decimal | None = None
    mean_volume: Decimal | None = None
    volume_fraction: Decimal | None = None
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def _nonnegative428(x):
    return type(x) is Decimal and x.is_finite() and x>=0


def validate_liquidity428(p):
    if type(p) is not B8LiquidityPlan428 or type(p.strategy) is not Strategy:
        raise ValueError("MST_428_EXPLICIT_STRATEGY_LIQUIDITY")
    if type(p.start) is not int or type(p.stop) is not int or not 0<=p.start<p.stop<=512:
        raise ValueError("MST_428_EXACT_WINDOW")
    if type(p.order_shares) is not int or p.order_shares<=0:
        raise ValueError("MST_428_POSITIVE_ORDER_SIZE")
    if type(p.units_policy) is not str or not p.units_policy.strip():
        raise ValueError("MST_428_EXPLICIT_UNITS_POLICY")
    _thresholds428(p)


def _thresholds428(p):
    t,f=p.candidate_min_mean_turnover,p.candidate_max_volume_fraction
    if t is not None and not _nonnegative428(t):
        raise ValueError("MST_428_INVALID_TURNOVER_THRESHOLD")
    if f is not None and (not _nonnegative428(f) or f>1):
        raise ValueError("MST_428_INVALID_PARTICIPATION_THRESHOLD")


def _raw_scope428(row,target):
    k=row.market_bar_key
    return (k.timeframe is Timeframe.D1 and k.price_basis is PriceBasis.RAW
            and k.instrument_class is InstrumentClass.STOCK
            and _cross_tf_identity(row)==_cross_tf_identity(target))


def _metrics428(rows,p):
    if any(x.matched_value is None or x.volume is None for x in rows):
        return B8LiquidityResult428("MISSING_INPUT","MATCHED_TURNOVER_OR_VOLUME_MISSING")
    vol=sum(x.volume for x in rows)
    if vol<=0:
        return B8LiquidityResult428("BLOCKED","ZERO_LIQUIDITY_DENOMINATOR")
    with localcontext() as ctx:
        ctx.prec=50
        turnover=sum(x.matched_value for x in rows)
        n=len(rows)
        fraction=Decimal(p.order_shares*n)/vol
        t,f=p.candidate_min_mean_turnover,p.candidate_max_volume_fraction
        match=None if t is None or f is None else turnover>=t*n and p.order_shares*n<=f*vol
        return B8LiquidityResult428("COMPUTED_UNCALIBRATED","RAW_D1_LIQUIDITY_ONLY",
                                   turnover/n,Decimal(vol)/n,fraction,match)


def inspect_liquidity428(daily,target,p,*,strategy):
    validate_liquidity428(p)
    if p.strategy is not strategy:
        return B8LiquidityResult428("BLOCKED","STRATEGY_SCOPE_MISMATCH")
    if len(daily)<p.stop:
        return B8LiquidityResult428("MISSING_INPUT","D1_WINDOW_MISSING")
    cutoff=target.market_bar_key.bar_start_utc
    rows,_=_sequence(daily[p.start:p.stop],cutoff=cutoff)
    if not rows or not all(_raw_scope428(x,target) for x in rows):
        return B8LiquidityResult428("BLOCKED","RAW_D1_CAUSAL_SCOPE_MISMATCH")
    if any(s.market_bar_key.bar_start_utc<cutoff for s in daily[p.stop:]):
        return B8LiquidityResult428("BLOCKED","D1_WINDOW_NOT_LATEST")
    return _metrics428(rows,p)
