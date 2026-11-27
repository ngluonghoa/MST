"""§484 S6 explicit hypothetical exit plan and settled holdings candidate."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .causal_structure_geometry import _eligible
from .contracts import Strategy
from .s1_context_preview439 import S1State439
from .replay import require_utc
from .s1_holdings445 import S1HoldingsPlan445,S1HoldingsResult445,validate_holdings445
from .s6_breakout479 import S6Preview479
from .s6_rf_volume483 import S6VolumePlan483,S6VolumeIngredient483,inspect_s6_volume_preview


@dataclass(frozen=True)
class S6SellScenario484:
    instrument_id: str
    strategy: Strategy
    variant_id: str
    plan_id: str
    plan_version: str
    breakout_event_id: str
    known_at_utc: datetime
    expires_at_utc: datetime
    sell_shares: int


@dataclass(frozen=True)
class S6HoldingsPlan484:
    geometry: S6VolumePlan483
    exit_plan: S6SellScenario484
    holdings: S1HoldingsPlan445


@dataclass(frozen=True)
class S6HoldingsIngredient484:
    state: S1State439
    reason: str
    private_geometry: S6VolumeIngredient483
    private_holdings: S1HoldingsResult445 | None = None


def _validate484(p):
    if type(p) is not S6SellScenario484 or type(p.strategy) is not Strategy:
        raise ValueError("MST_484_EXPLICIT_EXIT_SCENARIO")
    if p.variant_id != "S6/BASE":
        raise ValueError("MST_484_EXACT_EXIT_VARIANT")
    if any(type(v) is not str or not v.strip() for v in (p.instrument_id,p.plan_id,p.plan_version,p.breakout_event_id)):
        raise ValueError("MST_484_EXPLICIT_EXIT_SCOPE")
    if any(type(v) is not datetime for v in (p.known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_484_EXPLICIT_EXIT_TIMES")
    require_utc(p.known_at_utc)
    require_utc(p.expires_at_utc)
    if p.known_at_utc>=p.expires_at_utc or type(p.sell_shares) is not int or p.sell_shares<=0:
        raise ValueError("MST_484_EXIT_WINDOW_OR_SIZE")


def _scope484(s,anchor,target,strategy,variant):
    return (s.instrument_id==anchor.market_bar_key.instrument_id==target.market_bar_key.instrument_id
            and s.strategy is strategy and s.variant_id==variant
            and s.breakout_event_id in anchor.source_event_ids
            and s.known_at_utc<=anchor.market_bar_key.bar_start_utc
            and target.verified_at_utc<=s.expires_at_utc)


def _apply484(plan,proof,anchor,target,strategy,variant):
    s,p=plan.exit_plan,plan.holdings
    if s.breakout_event_id!=plan.geometry.geometry.early.failure.breakout.event_id or not _scope484(s,anchor,target,strategy,variant):
        return S6HoldingsIngredient484(S1State439.BLOCKED,"RF_EXIT_PLAN_SCOPE_OR_CLOCK",proof)
    if p.instrument_id!=s.instrument_id or p.strategy is not strategy or p.sell_shares!=s.sell_shares:
        return S6HoldingsIngredient484(S1State439.BLOCKED,"RF_HOLDINGS_SCOPE_OR_PLAN_SIZE",proof)
    age=target.verified_at_utc-p.known_at_utc
    if not timedelta(0)<=age<=timedelta(seconds=p.max_age_seconds):
        return S6HoldingsIngredient484(S1State439.BLOCKED,"RF_HOLDINGS_NOT_CAUSAL_OR_FRESH",proof)
    available=p.settled_shares-p.reserved_shares
    match=p.sell_shares<=available
    result=S1HoldingsResult445(available,p.sell_shares,match)
    return S6HoldingsIngredient484(S1State439.MATCH if match else S1State439.NONMATCH,
                                   "HYPOTHETICAL_SETTLED_HOLDINGS_AND_EXIT_PLAN_ONLY",proof,result)


def inspect_s6_holdings_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S6HoldingsPlan484 or type(plan.geometry) is not S6VolumePlan483:
        raise ValueError("MST_484_EXACT_HOLDINGS_PLAN")
    _validate484(plan.exit_plan)
    validate_holdings445(plan.holdings)
    g=plan.geometry
    preview=inspect_s6_volume_preview(inputs,strategy=strategy,variant_id=variant_id,plan=g)
    route,proof=preview.assessments[-1]
    if proof.state is not S1State439.MATCH:
        return preview
    ctx=g.geometry.early.failure.breakout
    anchor=_eligible(inputs.snapshots_for(ctx.timeframe)[ctx.target_index],cutoff=inputs.as_of_utc)
    target=_eligible(inputs.snapshots_for(g.geometry.timeframe)[g.geometry.target_index],cutoff=inputs.as_of_utc)
    if anchor is None or target is None:
        result=S6HoldingsIngredient484(S1State439.BLOCKED,"RF_HOLDINGS_GEOMETRY_UNRESOLVED",proof)
    else:
        result=_apply484(plan,proof,anchor,target,strategy,variant_id)
    return S6Preview479(preview.assessments[:-1]+((route,result),))
