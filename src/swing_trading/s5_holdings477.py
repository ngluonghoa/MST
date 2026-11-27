"""§477 S5 explicit hypothetical exit plan and settled holdings candidate."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .causal_structure_geometry import _eligible
from .contracts import Strategy
from .s1_context_preview439 import S1State439
from .market_data import Timeframe
from .replay import require_utc
from .s1_holdings445 import S1HoldingsPlan445,S1HoldingsResult445,validate_holdings445
from .s5_transition473 import S5ConfirmPlan476,S5Preview473,S5ConfirmIngredient476,inspect_s5_confirm_preview


@dataclass(frozen=True)
class S5SellScenario477:
    instrument_id: str
    strategy: Strategy
    variant_id: str
    plan_id: str
    plan_version: str
    known_at_utc: datetime
    expires_at_utc: datetime
    sell_shares: int


@dataclass(frozen=True)
class S5HoldingsPlan477:
    geometry: S5ConfirmPlan476
    exit_plan: S5SellScenario477
    holdings: S1HoldingsPlan445


@dataclass(frozen=True)
class S5HoldingsIngredient477:
    state: S1State439
    reason: str
    private_geometry: S5ConfirmIngredient476
    private_holdings: S1HoldingsResult445 | None = None


def _validate477(p):
    if type(p) is not S5SellScenario477 or type(p.strategy) is not Strategy:
        raise ValueError("MST_477_EXPLICIT_EXIT_SCENARIO")
    if p.variant_id != "S5/BASE":
        raise ValueError("MST_477_EXACT_EXIT_VARIANT")
    if any(type(v) is not str or not v.strip() for v in (p.instrument_id,p.plan_id,p.plan_version)):
        raise ValueError("MST_477_EXPLICIT_EXIT_SCOPE")
    if any(type(v) is not datetime for v in (p.known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_477_EXPLICIT_EXIT_TIMES")
    require_utc(p.known_at_utc)
    require_utc(p.expires_at_utc)
    if p.known_at_utc>=p.expires_at_utc or type(p.sell_shares) is not int or p.sell_shares<=0:
        raise ValueError("MST_477_EXIT_WINDOW_OR_SIZE")


def _scope477(s,anchor,target,strategy,variant):
    return (s.instrument_id==anchor.market_bar_key.instrument_id==target.market_bar_key.instrument_id
            and s.strategy is strategy and s.variant_id==variant
            and s.known_at_utc<=anchor.market_bar_key.bar_start_utc
            and target.verified_at_utc<=s.expires_at_utc)


def _apply477(plan,proof,anchor,target,strategy,variant):
    s,p=plan.exit_plan,plan.holdings
    if not _scope477(s,anchor,target,strategy,variant):
        return S5HoldingsIngredient477(S1State439.BLOCKED,"RF_EXIT_PLAN_SCOPE_OR_CLOCK",proof)
    if p.instrument_id!=s.instrument_id or p.strategy is not strategy or p.sell_shares!=s.sell_shares:
        return S5HoldingsIngredient477(S1State439.BLOCKED,"RF_HOLDINGS_SCOPE_OR_PLAN_SIZE",proof)
    age=target.verified_at_utc-p.known_at_utc
    if not timedelta(0)<=age<=timedelta(seconds=p.max_age_seconds):
        return S5HoldingsIngredient477(S1State439.BLOCKED,"RF_HOLDINGS_NOT_CAUSAL_OR_FRESH",proof)
    available=p.settled_shares-p.reserved_shares
    match=p.sell_shares<=available
    result=S1HoldingsResult445(available,p.sell_shares,match)
    return S5HoldingsIngredient477(S1State439.MATCH if match else S1State439.NONMATCH,
                                   "HYPOTHETICAL_SETTLED_HOLDINGS_AND_EXIT_PLAN_ONLY",proof,result)


def inspect_s5_holdings_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S5HoldingsPlan477 or type(plan.geometry) is not S5ConfirmPlan476:
        raise ValueError("MST_477_EXACT_HOLDINGS_PLAN")
    _validate477(plan.exit_plan)
    validate_holdings445(plan.holdings)
    g=plan.geometry
    preview=inspect_s5_confirm_preview(inputs,strategy=strategy,variant_id=variant_id,plan=g)
    route,proof=preview.assessments[-1]
    if proof.state is not S1State439.MATCH:
        return preview
    ctx=g.early.rally.context
    anchor=_eligible(inputs.snapshots_for(ctx.timeframe)[ctx.target_index],cutoff=inputs.as_of_utc)
    target=_eligible(inputs.snapshots_for(Timeframe.M15)[g.target_index],cutoff=inputs.as_of_utc)
    if anchor is None or target is None:
        result=S5HoldingsIngredient477(S1State439.BLOCKED,"RF_HOLDINGS_GEOMETRY_UNRESOLVED",proof)
    else:
        result=_apply477(plan,proof,anchor,target,strategy,variant_id)
    return S5Preview473(preview.assessments[:-1]+((route,result),))

@dataclass(frozen=True)
class S5StrictPlan478:
    scenario: S5HoldingsPlan477


@dataclass(frozen=True)
class S5StrictIngredient478:
    state: S1State439
    reason: str
    private_ingredient: object | None = None
    candidate_evidence_complete: bool = False
    mandatory_gaps: tuple[str,...] = ()


def _strict478(proof,phase,previous):
    if proof is None:
        return S5StrictIngredient478(S1State439.MISSING,"EXPLICIT_PHASE_PLAN_MISSING",
                                     mandatory_gaps=("PLAN_"+phase,))
    if proof.state is not S1State439.MATCH:
        return S5StrictIngredient478(proof.state,proof.reason,proof)
    if not previous:
        return S5StrictIngredient478(S1State439.BLOCKED,"PRIOR_STRICT_CANDIDATE_INCOMPLETE",
                                     proof,mandatory_gaps=("PRIOR_PHASE",))
    if phase=="R_F" and (type(proof) is not S5HoldingsIngredient477
            or type(proof.private_holdings) is not S1HoldingsResult445
            or proof.private_holdings.candidate_match is not True):
        return S5StrictIngredient478(S1State439.MISSING,"RF_HOLDINGS_SCENARIO_MISSING",
                                     proof,mandatory_gaps=("RF_SETTLED_HOLDINGS_SCENARIO",))
    return S5StrictIngredient478(proof.state,proof.reason,proof,True)


def inspect_s5_strict_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S5StrictPlan478 or type(plan.scenario) is not S5HoldingsPlan477:
        raise ValueError("MST_478_EXACT_STRICT_SCENARIO")
    preview=inspect_s5_holdings_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.scenario)
    phases=("R0","R_C","R_E","R_F")
    if tuple(route.phase for route,_ in preview.assessments)!=phases:
        raise ValueError("MST_478_EXACT_PHASE_CHAIN")
    out=[]
    previous=True
    for route,proof in preview.assessments:
        result=_strict478(proof,route.phase,previous)
        previous=result.candidate_evidence_complete
        out.append((route,result))
    return S5Preview473(tuple(out))
