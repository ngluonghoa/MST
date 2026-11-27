"""§429 explicit hypothetical same-size portfolio risk; no account authority."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

from .contracts import Strategy
from .replay import require_utc
from .market_data import PriceBasis


@dataclass(frozen=True)
class B8PortfolioPlan429:
    instrument_id: str
    strategy: Strategy
    known_at_utc: datetime
    max_age_seconds: int
    currency_policy: str
    price_unit_multiplier: Decimal
    equity: Decimal
    available_cash: Decimal
    reserved_risk: Decimal
    candidate_trade_risk_fraction: Decimal
    candidate_total_risk_fraction: Decimal


@dataclass(frozen=True)
class B8PortfolioResult429:
    state: str
    reason: str
    cash_required: Decimal | None = None
    added_risk: Decimal | None = None
    total_risk: Decimal | None = None
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def _nonnegative429(x):
    return type(x) is Decimal and x.is_finite() and x>=0


def validate_portfolio429(p):
    if type(p) is not B8PortfolioPlan429 or type(p.strategy) is not Strategy:
        raise ValueError("MST_429_EXPLICIT_PORTFOLIO")
    require_utc(p.known_at_utc)
    if not all(type(x) is str and x.strip() for x in (p.instrument_id,p.currency_policy)):
        raise ValueError("MST_429_EXPLICIT_SCOPE_UNITS")
    if type(p.max_age_seconds) is not int or not 0<=p.max_age_seconds<=86400:
        raise ValueError("MST_429_EXPLICIT_FRESHNESS")
    _numbers429(p)


def _numbers429(p):
    if not all(_nonnegative429(x) for x in (p.price_unit_multiplier,p.equity,
              p.available_cash,p.reserved_risk,p.candidate_trade_risk_fraction,
              p.candidate_total_risk_fraction)):
        raise ValueError("MST_429_FINITE_PORTFOLIO_VALUES")
    if p.equity<=0 or p.price_unit_multiplier<=0:
        raise ValueError("MST_429_POSITIVE_EQUITY_MULTIPLIER")
    if not 0<p.candidate_trade_risk_fraction<=p.candidate_total_risk_fraction<=1:
        raise ValueError("MST_429_EXPLICIT_ORDERED_RISK_LIMITS")


def _scope429(target,p,strategy):
    return (target.market_bar_key.instrument_id==p.instrument_id
            and target.market_bar_key.price_basis is PriceBasis.RAW
            and p.strategy is strategy
            and timedelta(0)<=target.verified_at_utc-p.known_at_utc
            <=timedelta(seconds=p.max_age_seconds))


def _budget429(target,p,shares,net_risk,buy_fee_rate):
    with localcontext() as ctx:
        ctx.prec=50
        scale=shares*p.price_unit_multiplier
        cash=target.close*(1+buy_fee_rate)*scale
        added=net_risk*scale
        total=p.reserved_risk+added
        match=(cash<=p.available_cash and added<=p.equity*p.candidate_trade_risk_fraction
               and total<=p.equity*p.candidate_total_risk_fraction)
        return B8PortfolioResult429("COMPUTED_UNCALIBRATED","HYPOTHETICAL_BUDGET_ONLY",
                                    cash,added,total,match)


def inspect_portfolio429(target,p,*,strategy,shares,net_risk,buy_fee_rate):
    validate_portfolio429(p)
    if not _scope429(target,p,strategy):
        return B8PortfolioResult429("BLOCKED","PORTFOLIO_SCOPE_OR_FRESHNESS")
    if shares is None or net_risk is None or buy_fee_rate is None:
        return B8PortfolioResult429("MISSING_INPUT","RISK_OR_LIQUIDITY_NOT_AVAILABLE")
    if type(shares) is not int or shares<=0 or not _nonnegative429(net_risk) or net_risk<=0:
        return B8PortfolioResult429("BLOCKED","INVALID_RISK_OR_SIZE")
    if not _nonnegative429(buy_fee_rate) or buy_fee_rate>=1:
        return B8PortfolioResult429("BLOCKED","INVALID_COST")
    return _budget429(target,p,shares,net_risk,buy_fee_rate)
