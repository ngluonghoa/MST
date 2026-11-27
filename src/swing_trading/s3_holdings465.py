"""§465 explicit hypothetical S3 exit plan and settled holdings, no authority."""
from dataclasses import dataclass
from datetime import datetime,timedelta

from .causal_structure_geometry import _eligible
from .contracts import Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_holdings445 import S1HoldingsPlan445,S1HoldingsResult445,validate_holdings445
from .s3_context454 import S3ContextPlan454,S3Ingredient454,S3State454,S3Preview454,inspect_s3_preview
from .s3_tp_event463 import S3TPConfirmPlan464,S3TPEventIngredient463,inspect_s3_tp_confirm_preview


@dataclass(frozen=True)
class S3SellScenario465:
    instrument_id: str
    strategy: Strategy
    variant_id: str
    plan_id: str
    plan_version: str
    known_at_utc: datetime
    expires_at_utc: datetime
    sell_shares: int


@dataclass(frozen=True)
class S3HoldingsPlan465:
    geometry: S3ContextPlan454 | S3TPConfirmPlan464
    exit_plan: S3SellScenario465
    holdings: S1HoldingsPlan445


@dataclass(frozen=True)
class S3HoldingsIngredient465:
    state: S3State454
    reason: str
    private_geometry: S3Ingredient454 | S3TPEventIngredient463
    private_holdings: S1HoldingsResult445 | None=None


def _validate_exit465(p):
    if type(p) is not S3SellScenario465 or type(p.strategy) is not Strategy:
        raise ValueError("MST_465_EXPLICIT_EXIT_SCENARIO")
    if p.variant_id not in ("S3/F_TP","S3/F_MICRO_BREAK"):
        raise ValueError("MST_465_EXPLICIT_EXIT_VARIANT")
    if any(type(v) is not str or not v.strip() for v in
           (p.instrument_id,p.plan_id,p.plan_version,p.variant_id)):
        raise ValueError("MST_465_EXPLICIT_EXIT_SCOPE")
    if any(type(v) is not datetime for v in (p.known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_465_EXPLICIT_EXIT_TIMES")
    require_utc(p.known_at_utc)
    require_utc(p.expires_at_utc)
    if p.known_at_utc>=p.expires_at_utc or type(p.sell_shares) is not int or p.sell_shares<=0:
        raise ValueError("MST_465_EXIT_WINDOW_OR_SIZE")


def _geometry465(inputs,plan,strategy,variant):
    g=plan.geometry
    if variant=="S3/F_TP" and type(g) is S3TPConfirmPlan464:
        preview=inspect_s3_tp_confirm_preview(inputs,strategy=strategy,variant_id=variant,plan=g)
        return preview,g.event.context.anchor_index,Timeframe.M15,g.confirmation.target_index
    if variant=="S3/F_MICRO_BREAK" and type(g) is S3ContextPlan454 and g.rf is not None:
        preview=inspect_s3_preview(inputs,strategy=strategy,variant_id=variant,plan=g)
        return preview,g.anchor_index,g.rf.timeframe,g.rf.target_index
    raise ValueError("MST_465_EXACT_CONFIRMATION_BRANCH")


def _scope465(s,anchor,target,strategy,variant):
    return (s.instrument_id==anchor.market_bar_key.instrument_id==target.market_bar_key.instrument_id
            and s.strategy is strategy and s.variant_id==variant
            and s.known_at_utc<=anchor.market_bar_key.bar_start_utc
            and target.verified_at_utc<=s.expires_at_utc)


def _target_link465(s,geometry):
    if type(geometry) is not S3TPConfirmPlan464:
        return True
    t=geometry.event.context.target
    return ((s.plan_id,s.plan_version,s.known_at_utc,s.expires_at_utc)
            ==(t.plan_id,t.plan_version,t.known_at_utc,t.expires_at_utc))


def _apply465(plan,proof,anchor,target,strategy,variant):
    s,p=plan.exit_plan,plan.holdings
    if not _scope465(s,anchor,target,strategy,variant) or not _target_link465(s,plan.geometry):
        return S3HoldingsIngredient465(S3State454.BLOCKED,"RF_EXIT_PLAN_SCOPE_OR_CLOCK",proof)
    if p.instrument_id!=s.instrument_id or p.strategy is not strategy or p.sell_shares!=s.sell_shares:
        return S3HoldingsIngredient465(S3State454.BLOCKED,"RF_HOLDINGS_SCOPE_OR_PLAN_SIZE",proof)
    age=target.verified_at_utc-p.known_at_utc
    if not timedelta(0)<=age<=timedelta(seconds=p.max_age_seconds):
        return S3HoldingsIngredient465(S3State454.BLOCKED,"RF_HOLDINGS_NOT_CAUSAL_OR_FRESH",proof)
    available=p.settled_shares-p.reserved_shares
    match=p.sell_shares<=available
    result=S1HoldingsResult445(available,p.sell_shares,match)
    state=S3State454.MATCH if match else S3State454.NONMATCH
    return S3HoldingsIngredient465(state,"HYPOTHETICAL_SETTLED_HOLDINGS_AND_EXIT_PLAN_ONLY",proof,result)


def inspect_s3_holdings_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S3HoldingsPlan465:
        raise ValueError("MST_465_EXPLICIT_HOLDINGS_PLAN")
    _validate_exit465(plan.exit_plan)
    validate_holdings445(plan.holdings)
    preview,anchor_index,tf,target_index=_geometry465(inputs,plan,strategy,variant_id)
    route,proof=preview.assessments[-1]
    if proof.state is not S3State454.MATCH:
        return preview
    anchor=_eligible(inputs.snapshots_for(Timeframe.M15)[anchor_index],cutoff=inputs.as_of_utc)
    target=_eligible(inputs.snapshots_for(tf)[target_index],cutoff=inputs.as_of_utc)
    if anchor is None or target is None:
        result=S3HoldingsIngredient465(S3State454.BLOCKED,"RF_HOLDINGS_GEOMETRY_UNRESOLVED",proof)
    else:
        result=_apply465(plan,proof,anchor,target,strategy,variant_id)
    return S3Preview454(preview.assessments[:-1]+((route,result),))


@dataclass(frozen=True)
class S3StrictPlan466:
    scenario: S3HoldingsPlan465


@dataclass(frozen=True)
class S3StrictIngredient466:
    state: S3State454
    reason: str
    private_ingredient: object | None = None
    candidate_evidence_complete: bool = False
    mandatory_gaps: tuple[str,...] = ()


def _strict466(proof,phase,previous):
    if proof is None:
        return S3StrictIngredient466(S3State454.MISSING,"EXPLICIT_PHASE_PLAN_MISSING",
                                    mandatory_gaps=("PLAN_"+phase,))
    if proof.state is not S3State454.MATCH:
        return S3StrictIngredient466(proof.state,proof.reason,proof)
    if not previous:
        return S3StrictIngredient466(S3State454.BLOCKED,"PRIOR_STRICT_CANDIDATE_INCOMPLETE",
                                    proof,mandatory_gaps=("PRIOR_PHASE",))
    if phase=="R_F" and (type(proof) is not S3HoldingsIngredient465
            or proof.private_holdings is None
            or proof.private_holdings.candidate_match is not True):
        return S3StrictIngredient466(S3State454.MISSING,"RF_HOLDINGS_SCENARIO_MISSING",
                                    proof,mandatory_gaps=("RF_SETTLED_HOLDINGS_SCENARIO",))
    return S3StrictIngredient466(proof.state,proof.reason,proof,True)


def inspect_s3_strict_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S3StrictPlan466 or type(plan.scenario) is not S3HoldingsPlan465:
        raise ValueError("MST_466_EXPLICIT_STRICT_SCENARIO")
    preview=inspect_s3_holdings_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.scenario)
    existing={route.phase:(route,proof) for route,proof in preview.assessments}
    out=[]
    previous=True
    for phase in ("R0","R_C","R_E","R_F"):
        if phase in existing:
            route,proof=existing[phase]
        else:
            v="S3/E_MICRO_CHOCH" if phase=="R_E" and variant_id=="S3/F_MICRO_BREAK" else variant_id
            route=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=v,phase=phase)
            proof=None
        result=_strict466(proof,phase,previous)
        previous=result.candidate_evidence_complete
        out.append((route,result))
    return S3Preview454(tuple(out))
