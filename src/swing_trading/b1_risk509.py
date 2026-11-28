"""§509 structural stop and causal resistance net reward/risk candidate."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

from .b1_decline499 import B1Preview499
from .b1_major508 import B1MajorPlan508,inspect_b1_major508_preview
from .b1_market507 import B1MarketPlan507,inspect_b1_market507_preview
from .feature_engine460 import inspect_target_d1_atr
from .market_data import Timeframe
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1RiskTerms509:
    policy_version: str
    known_at_utc: datetime
    weekly_high_index: int
    candidate_stop_buffer_atr: Decimal
    buy_fee_rate: Decimal
    sell_fee_rate: Decimal
    sell_tax_rate: Decimal
    candidate_min_net_rr: Decimal | None


@dataclass(frozen=True)
class B1RiskPlan509:
    prior: B1MarketPlan507 | B1MajorPlan508
    risk: B1RiskTerms509


@dataclass(frozen=True)
class B1RiskIngredient509:
    state: S1State439
    reason: str
    private_prior: object
    private_reference: Decimal | None = None
    private_stop: Decimal | None = None
    private_target: Decimal | None = None
    private_net_risk: Decimal | None = None
    private_net_reward: Decimal | None = None
    private_net_rr: Decimal | None = None


def _nonnegative509(value):
    return type(value) is Decimal and value.is_finite() and value>=0


def _validate509(p):
    if type(p) is not B1RiskPlan509 or type(p.prior) not in (B1MarketPlan507,B1MajorPlan508):
        raise ValueError("MST_509_EXACT_PRIOR")
    r=p.risk
    if type(r) is not B1RiskTerms509 or type(r.policy_version) is not str or not r.policy_version.strip():
        raise ValueError("MST_509_EXPLICIT_RISK_POLICY")
    if type(r.known_at_utc) is not datetime or r.known_at_utc.utcoffset()!=timedelta(0):
        raise ValueError("MST_509_UTC_POLICY_CLOCK")
    if type(r.weekly_high_index) is not int:
        raise ValueError("MST_509_EXACT_HISTORICAL_PIVOT")
    if not all(_nonnegative509(x) for x in (r.candidate_stop_buffer_atr,r.buy_fee_rate,r.sell_fee_rate,r.sell_tax_rate)):
        raise ValueError("MST_509_EXPLICIT_COST_BUFFER")
    if r.buy_fee_rate>=1 or r.sell_fee_rate+r.sell_tax_rate>=1:
        raise ValueError("MST_509_COST_RATE_OUT_OF_RANGE")
    k=r.candidate_min_net_rr
    if k is not None and (not _nonnegative509(k) or k==0):
        raise ValueError("MST_509_EXPLICIT_POSITIVE_RR")


def _scope509(inputs,p,rf):
    major=type(p.prior) is B1MajorPlan508
    market=p.prior.prior if major else p.prior
    g=market.prior.prior.geometry
    geometry=(rf.private_rf if major else rf).private_volume.private_geometry
    d1=inputs.snapshots_for(Timeframe.D1)[g.target_index].selected
    weeks=inputs.snapshots_for(Timeframe.W1)
    reference=weeks[p.prior.weekly_target_index].selected if major else d1
    window=g.early.context.context.context.weekly
    if p.risk.weekly_high_index not in window.high_indices:
        raise ValueError("MST_509_EXACT_CONFIRMED_W1_HIGH")
    resistance=weeks[window.start+p.risk.weekly_high_index].selected
    return g,geometry,d1,reference,resistance


def _net509(r,rf,reference,stop,target):
    principal=reference*(1+r.buy_fee_rate)
    exit_factor=1-r.sell_fee_rate-r.sell_tax_rate
    risk=principal-stop*exit_factor
    reward=target*exit_factor-principal
    if risk<=0:
        return B1RiskIngredient509(S1State439.BLOCKED,"NONPOSITIVE_NET_RISK",rf)
    ratio=reward/risk
    k=r.candidate_min_net_rr
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if reward>0 and reward>=k*risk else S1State439.NONMATCH
    return B1RiskIngredient509(state,"STRUCTURAL_NET_RR_CANDIDATE_ONLY",rf,reference,stop,target,risk,reward,ratio)


def _risk509(inputs,p,rf):
    g,geometry,d1,reference,resistance=_scope509(inputs,p,rf)
    r=p.risk
    if r.known_at_utc>reference.market_bar_key.bar_start_utc:
        return B1RiskIngredient509(S1State439.BLOCKED,"RISK_POLICY_NOT_KNOWN_BEFORE_REFERENCE",rf)
    atr=inspect_target_d1_atr(inputs,g,d1)
    if atr is None or atr<=0:
        return B1RiskIngredient509(S1State439.BLOCKED,"RF_D1_ATR_UNRESOLVED",rf)
    with localcontext() as ctx:
        ctx.prec=50
        stop=geometry.private_support-r.candidate_stop_buffer_atr*atr
        target=resistance.high
        if not 0<stop<reference.close<target:
            return B1RiskIngredient509(S1State439.NONMATCH,"NO_VALID_STRUCTURAL_LONG_GEOMETRY",rf,reference.close,stop,target)
        return _net509(r,rf,reference.close,stop,target)


def inspect_b1_risk509_preview(inputs,*,strategy,variant_id,plan):
    _validate509(plan)
    fn=inspect_b1_major508_preview if type(plan.prior) is B1MajorPlan508 else inspect_b1_market507_preview
    preview=fn(inputs,strategy=strategy,variant_id=variant_id,plan=plan.prior)
    a=preview.assessments
    if len(a)!=4 or any(p.state is not S1State439.MATCH for _,p in a):
        return preview
    route,rf=a[-1]
    return B1Preview499(a[:-1]+((route,_risk509(inputs,plan,rf)),))
