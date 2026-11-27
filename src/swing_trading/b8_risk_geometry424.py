"""§424 B8 synthetic-safe base-floor stop and measured-base net reward/risk."""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .causal_structure_geometry import _sequence


@dataclass(frozen=True)
class B8MeasuredBaseRisk424:
    candidate_stop_buffer_atr: Decimal
    buy_fee_rate: Decimal
    sell_fee_rate: Decimal
    sell_tax_rate: Decimal
    candidate_min_net_rr: Decimal | None


@dataclass(frozen=True)
class B8RiskResult424:
    state: str
    reason: str
    stop: Decimal | None = None
    target: Decimal | None = None
    net_reward: Decimal | None = None
    net_risk: Decimal | None = None
    net_rr: Decimal | None = None
    candidate_match: bool | None = None

    @property
    def action_eligible(self):
        return False


def _nonnegative424(value):
    return type(value) is Decimal and value.is_finite() and value >= 0


def validate_risk424(plan):
    if type(plan) is not B8MeasuredBaseRisk424:
        raise ValueError("MST_424_EXPLICIT_MEASURED_BASE_RISK_PLAN")
    if not all(_nonnegative424(x) for x in (plan.candidate_stop_buffer_atr,
                   plan.buy_fee_rate,plan.sell_fee_rate,plan.sell_tax_rate)):
        raise ValueError("MST_424_EXPLICIT_FINITE_COST_BUFFER")
    if plan.buy_fee_rate >= 1 or plan.sell_fee_rate+plan.sell_tax_rate >= 1:
        raise ValueError("MST_424_COST_RATE_OUT_OF_RANGE")
    k=plan.candidate_min_net_rr
    if k is not None and (not _nonnegative424(k) or k == 0):
        raise ValueError("MST_424_EXPLICIT_POSITIVE_RR_THRESHOLD")


def _levels424(rows, resistance, atr, plan):
    floor=min(x.low for x in rows)
    if max(x.high for x in rows)!=resistance or floor>=resistance:
        return None
    return (floor-plan.candidate_stop_buffer_atr*atr,
            resistance+(resistance-floor))


def _net424(entry, stop, target, plan):
    principal=entry*(1+plan.buy_fee_rate)
    exit_factor=1-plan.sell_fee_rate-plan.sell_tax_rate
    reward=target*exit_factor-principal
    risk=principal-stop*exit_factor
    if risk<=0:
        return B8RiskResult424("BLOCKED","NONPOSITIVE_NET_RISK")
    ratio=reward/risk
    k=plan.candidate_min_net_rr
    match=None if k is None else reward>0 and reward>=k*risk
    return B8RiskResult424("COMPUTED_UNCALIBRATED","MEASURED_BASE_NET_RR_ONLY",
                           stop,target,reward,risk,ratio,match)


def inspect_b8_risk424(history, *, target, resistance, atr, plan):
    validate_risk424(plan)
    rows,_=_sequence(history,cutoff=target.market_bar_key.bar_start_utc)
    if not rows:
        return B8RiskResult424("BLOCKED","BASE_NOT_CAUSALLY_AVAILABLE")
    with localcontext() as ctx:
        ctx.prec=50
        levels=_levels424(rows,resistance,atr,plan)
        if levels is None:
            return B8RiskResult424("BLOCKED","BASE_BOUNDARY_MISMATCH")
        stop,take=levels
        if not 0<stop<target.close<take:
            return B8RiskResult424("NONMATCH","NO_VALID_LONG_REWARD_GEOMETRY")
        return _net424(target.close,stop,take,plan)
