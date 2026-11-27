"""§471 S4 explicit hypothetical exit plan and settled holdings candidate."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .causal_structure_geometry import _eligible
from .contracts import Strategy
from .range_baseline_preview385 import RangeEnginePreview385,RangeIngredient385,RangeState385
from .replay import require_utc
from .s1_holdings445 import S1HoldingsPlan445,S1HoldingsResult445,validate_holdings445
from .s4_rejection467 import S4ConfirmPlan470,inspect_s4_confirm_preview


@dataclass(frozen=True)
class S4SellScenario471:
    instrument_id: str
    strategy: Strategy
    variant_id: str
    plan_id: str
    plan_version: str
    known_at_utc: datetime
    expires_at_utc: datetime
    sell_shares: int


@dataclass(frozen=True)
class S4HoldingsPlan471:
    geometry: S4ConfirmPlan470
    exit_plan: S4SellScenario471
    holdings: S1HoldingsPlan445


@dataclass(frozen=True)
class S4HoldingsIngredient471:
    state: RangeState385
    reason: str
    private_geometry: RangeIngredient385
    private_holdings: S1HoldingsResult445 | None = None


def _validate471(p):
    if type(p) is not S4SellScenario471 or type(p.strategy) is not Strategy:
        raise ValueError("MST_471_EXPLICIT_EXIT_SCENARIO")
    if p.variant_id not in ("S4/E_FALSE_BREAK","S4/E_BOS_DOWN"):
        raise ValueError("MST_471_EXACT_EXIT_VARIANT")
    if any(type(v) is not str or not v.strip() for v in (p.instrument_id,p.plan_id,p.plan_version)):
        raise ValueError("MST_471_EXPLICIT_EXIT_SCOPE")
    if any(type(v) is not datetime for v in (p.known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_471_EXPLICIT_EXIT_TIMES")
    require_utc(p.known_at_utc)
    require_utc(p.expires_at_utc)
    if p.known_at_utc>=p.expires_at_utc or type(p.sell_shares) is not int or p.sell_shares<=0:
        raise ValueError("MST_471_EXIT_WINDOW_OR_SIZE")


def _scope471(s,anchor,target,strategy,variant):
    return (s.instrument_id==anchor.market_bar_key.instrument_id==target.market_bar_key.instrument_id
            and s.strategy is strategy and s.variant_id==variant
            and s.known_at_utc<=anchor.market_bar_key.bar_start_utc
            and target.verified_at_utc<=s.expires_at_utc)


def _apply471(plan,proof,anchor,target,strategy,variant):
    s,p=plan.exit_plan,plan.holdings
    if not _scope471(s,anchor,target,strategy,variant):
        return S4HoldingsIngredient471(RangeState385.BLOCKED,"RF_EXIT_PLAN_SCOPE_OR_CLOCK",proof)
    if p.instrument_id!=s.instrument_id or p.strategy is not strategy or p.sell_shares!=s.sell_shares:
        return S4HoldingsIngredient471(RangeState385.BLOCKED,"RF_HOLDINGS_SCOPE_OR_PLAN_SIZE",proof)
    age=target.verified_at_utc-p.known_at_utc
    if not timedelta(0)<=age<=timedelta(seconds=p.max_age_seconds):
        return S4HoldingsIngredient471(RangeState385.BLOCKED,"RF_HOLDINGS_NOT_CAUSAL_OR_FRESH",proof)
    available=p.settled_shares-p.reserved_shares
    match=p.sell_shares<=available
    result=S1HoldingsResult445(available,p.sell_shares,match)
    return S4HoldingsIngredient471(RangeState385.MATCH if match else RangeState385.NONMATCH,
                                   "HYPOTHETICAL_SETTLED_HOLDINGS_AND_EXIT_PLAN_ONLY",proof,result)


def inspect_s4_holdings_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S4HoldingsPlan471 or type(plan.geometry) is not S4ConfirmPlan470:
        raise ValueError("MST_471_EXACT_HOLDINGS_PLAN")
    _validate471(plan.exit_plan)
    validate_holdings445(plan.holdings)
    g=plan.geometry
    preview=inspect_s4_confirm_preview(inputs,strategy=strategy,variant_id=variant_id,plan=g)
    route,proof=preview.assessments[-1]
    if proof.state is not RangeState385.MATCH:
        return preview
    ctx=g.early.context.context
    anchor=_eligible(inputs.snapshots_for(ctx.target_tf)[ctx.target_index],cutoff=inputs.as_of_utc)
    target=_eligible(inputs.snapshots_for(g.timeframe)[g.target_index],cutoff=inputs.as_of_utc)
    if anchor is None or target is None:
        result=S4HoldingsIngredient471(RangeState385.BLOCKED,"RF_HOLDINGS_GEOMETRY_UNRESOLVED",proof)
    else:
        result=_apply471(plan,proof,anchor,target,strategy,variant_id)
    return RangeEnginePreview385(preview.assessments[:-1]+((route,result),))


@dataclass(frozen=True)
class S4StrictPlan472:
    scenario: S4HoldingsPlan471


@dataclass(frozen=True)
class S4StrictIngredient472:
    state: RangeState385
    reason: str
    private_ingredient: object | None = None
    candidate_evidence_complete: bool = False
    mandatory_gaps: tuple[str,...] = ()


def _strict472(proof,phase,previous):
    if proof is None:
        return S4StrictIngredient472(RangeState385.MISSING,"EXPLICIT_PHASE_PLAN_MISSING",
                                     mandatory_gaps=("PLAN_"+phase,))
    if proof.state is not RangeState385.MATCH:
        return S4StrictIngredient472(proof.state,proof.reason,proof)
    if not previous:
        return S4StrictIngredient472(RangeState385.BLOCKED,"PRIOR_STRICT_CANDIDATE_INCOMPLETE",
                                     proof,mandatory_gaps=("PRIOR_PHASE",))
    if phase=="R_F" and (type(proof) is not S4HoldingsIngredient471
            or type(proof.private_holdings) is not S1HoldingsResult445
            or proof.private_holdings.candidate_match is not True):
        return S4StrictIngredient472(RangeState385.MISSING,"RF_HOLDINGS_SCENARIO_MISSING",
                                     proof,mandatory_gaps=("RF_SETTLED_HOLDINGS_SCENARIO",))
    return S4StrictIngredient472(proof.state,proof.reason,proof,True)


def inspect_s4_strict_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S4StrictPlan472 or type(plan.scenario) is not S4HoldingsPlan471:
        raise ValueError("MST_472_EXACT_STRICT_SCENARIO")
    preview=inspect_s4_holdings_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.scenario)
    phases=("R0","R_C","R_E","R_F")
    if tuple(route.phase for route,_ in preview.assessments)!=phases:
        raise ValueError("MST_472_EXACT_PHASE_CHAIN")
    out=[]
    previous=True
    for route,proof in preview.assessments:
        result=_strict472(proof,route.phase,previous)
        previous=result.candidate_evidence_complete
        out.append((route,result))
    return RangeEnginePreview385(tuple(out))
