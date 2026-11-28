"""§510 explicit structural no-chase and net R:R entry cap candidate."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from decimal import Decimal,localcontext,ROUND_FLOOR

from .b1_decline499 import B1Preview499
from .b1_risk509 import B1RiskPlan509,_scope509,_nonnegative509,inspect_b1_risk509_preview
from .feature_engine460 import inspect_target_d1_atr
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1EntryTerms510:
    policy_version: str
    known_at_utc: datetime
    candidate_max_extension_atr: Decimal | None


@dataclass(frozen=True)
class B1EntryPlan510:
    prior: B1RiskPlan509
    entry: B1EntryTerms510


@dataclass(frozen=True)
class B1EntryIngredient510:
    state: S1State439
    reason: str
    private_prior: object
    private_pivot: Decimal | None = None
    private_no_chase_cap: Decimal | None = None
    private_rr_cap: Decimal | None = None
    private_max_entry: Decimal | None = None


def _validate510(p):
    if type(p) is not B1EntryPlan510 or type(p.prior) is not B1RiskPlan509:
        raise ValueError("MST_510_EXACT_PRIOR")
    e=p.entry
    if type(e) is not B1EntryTerms510 or type(e.policy_version) is not str or not e.policy_version.strip():
        raise ValueError("MST_510_EXPLICIT_ENTRY_POLICY")
    if type(e.known_at_utc) is not datetime or e.known_at_utc.utcoffset()!=timedelta(0):
        raise ValueError("MST_510_UTC_POLICY_CLOCK")
    if e.candidate_max_extension_atr is not None and not _nonnegative509(e.candidate_max_extension_atr):
        raise ValueError("MST_510_NONNEGATIVE_EXTENSION")


def _caps510(p,rf,pivot,atr):
    r=p.prior.risk
    k=r.candidate_min_net_rr
    with localcontext() as ctx:
        ctx.prec=50
        ctx.rounding=ROUND_FLOOR
        chase=pivot+p.entry.candidate_max_extension_atr*atr
        rr=(rf.private_target+k*rf.private_stop)*(1-r.sell_fee_rate-r.sell_tax_rate)/((1+k)*(1+r.buy_fee_rate))
        cap=min(chase,rr)
    state=S1State439.MATCH if pivot<rf.private_reference<=cap else S1State439.NONMATCH
    return B1EntryIngredient510(state,"MAX_ENTRY_CANDIDATE_ONLY",rf,pivot,chase,rr,cap)


def _entry510(inputs,p,rf):
    g,geometry,d1,reference,_=_scope509(inputs,p.prior,rf.private_prior)
    if p.entry.known_at_utc>reference.market_bar_key.bar_start_utc:
        return B1EntryIngredient510(S1State439.BLOCKED,"ENTRY_POLICY_NOT_KNOWN_BEFORE_REFERENCE",rf)
    atr=inspect_target_d1_atr(inputs,g,d1)
    if atr is None or atr<=0:
        return B1EntryIngredient510(S1State439.BLOCKED,"RF_D1_ATR_UNRESOLVED",rf)
    if p.entry.candidate_max_extension_atr is None:
        return B1EntryIngredient510(S1State439.DISTANCE,"EXTENSION_CANDIDATE_MISSING",rf)
    return _caps510(p,rf,geometry.private_key_high,atr)


def inspect_b1_entry510_preview(inputs,*,strategy,variant_id,plan):
    _validate510(plan)
    preview=inspect_b1_risk509_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.prior)
    a=preview.assessments
    if len(a)!=4 or any(p.state is not S1State439.MATCH for _,p in a):
        return preview
    route,rf=a[-1]
    return B1Preview499(a[:-1]+((route,_entry510(inputs,plan,rf)),))
