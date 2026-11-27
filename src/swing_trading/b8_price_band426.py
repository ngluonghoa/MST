"""§426 caller-supplied session-scoped raw price band and tick preview."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext, ROUND_FLOOR

from .market_data import InstrumentClass, PriceBasis
from .replay import require_utc


@dataclass(frozen=True)
class B8PriceBand426:
    instrument_id: str
    exchange: str
    calendar_version: str
    session_period_id: str
    policy_version: str
    known_at_utc: datetime
    lower: Decimal
    upper: Decimal
    tick: Decimal


@dataclass(frozen=True)
class B8PriceBandResult426:
    state: str
    reason: str
    grid_entry_ceiling: Decimal | None = None
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def _positive426(x):
    return type(x) is Decimal and x.is_finite() and x>0


def validate_band426(p):
    if type(p) is not B8PriceBand426:
        raise ValueError("MST_426_EXPLICIT_SESSION_BAND")
    require_utc(p.known_at_utc)
    if not all(type(x) is str and x.strip() for x in (p.instrument_id,p.exchange,
                    p.calendar_version,p.session_period_id,p.policy_version)):
        raise ValueError("MST_426_EXPLICIT_SESSION_AND_POLICY")
    if not all(_positive426(x) for x in (p.lower,p.upper,p.tick)):
        raise ValueError("MST_426_POSITIVE_FINITE_BAND_TICK")
    if p.lower>p.upper or p.lower%p.tick or p.upper%p.tick:
        raise ValueError("MST_426_ALIGNED_BAND")


def _scope426(target,p):
    k=target.market_bar_key
    return (k.instrument_class is InstrumentClass.STOCK and k.price_basis is PriceBasis.RAW
            and (k.instrument_id,k.exchange,k.calendar_version,k.session_period_id)
            ==(p.instrument_id,p.exchange,p.calendar_version,p.session_period_id)
            and p.known_at_utc<=k.bar_start_utc)


def _bar_grid426(target,p):
    return all(p.lower<=x<=p.upper and x%p.tick==0
               for x in (target.open,target.high,target.low,target.close))


def inspect_band426(target,p,*,max_entry=None):
    validate_band426(p)
    if not _scope426(target,p):
        return B8PriceBandResult426("BLOCKED","RAW_SESSION_SCOPE_OR_CLOCK_MISMATCH")
    if not _bar_grid426(target,p):
        return B8PriceBandResult426("BLOCKED","RF_OHLC_OUTSIDE_SUPPLIED_GRID")
    if max_entry is None:
        return B8PriceBandResult426("COMPUTED_UNCALIBRATED","BAND_ONLY_NO_MAX_ENTRY")
    if not _positive426(max_entry):
        return B8PriceBandResult426("BLOCKED","INVALID_MAX_ENTRY")
    with localcontext() as ctx:
        ctx.prec=50
        ctx.rounding=ROUND_FLOOR
        ceiling=(min(max_entry,p.upper)/p.tick).to_integral_value(rounding=ROUND_FLOOR)*p.tick
    if ceiling<p.lower:
        return B8PriceBandResult426("NONMATCH","NO_PRICE_IN_SUPPLIED_GRID")
    return B8PriceBandResult426("COMPUTED_UNCALIBRATED","RAW_GRID_CANDIDATE_ONLY",
                                ceiling,target.close<=ceiling)
