"""§453 cumulative strict S2 candidate completeness, no action authority."""
from dataclasses import replace

from .causal_structure_geometry import _cross_tf_identity, _eligible
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs


def _observed453(rows,early,target,resistance,states):
    cutoff=target.market_bar_key.bar_start_utc
    for snap in rows:
        start=snap.market_bar_key.bar_start_utc
        if start>=cutoff:
            break
        bar=snap.selected
        if bar is None:
            if start>=early.market_bar_key.bar_start_utc:
                return states.BLOCKED
            continue
        if bar.bar_end_utc<=early.bar_end_utc or bar.bar_end_utc>cutoff:
            continue
        if (_eligible(snap,cutoff=cutoff) is None
                or _cross_tf_identity(bar)!=_cross_tf_identity(target)):
            return states.BLOCKED
        if bar.close>resistance:
            return states.NONMATCH
    return states.MATCH


def _rf453(inputs,plan,proof,states):
    early=inputs.snapshots_for(Timeframe.M15)[plan.early.target_index].selected
    target=inputs.snapshots_for(plan.rf.timeframe)[plan.rf.target_index].selected
    for tf in (Timeframe.H1,Timeframe.M15):
        state=_observed453(inputs.snapshots_for(tf),early,target,proof.private_resistance,states)
        if state is not states.MATCH:
            return replace(proof,state=state,reason="RF_INTERVENING_CONTEXT_UNRESOLVED_OR_RECLAIMED",
                           candidate_evidence_complete=False)
    if proof.holdings is None or proof.holdings.candidate_match is not True:
        return replace(proof,state=states.MISSING,reason="RF_HOLDINGS_SCENARIO_MISSING",
                       candidate_evidence_complete=False,mandatory_gaps=("RF_SETTLED_HOLDINGS_SCENARIO",))
    return replace(proof,candidate_evidence_complete=True)


def _apply453(inputs,plan,proof,phase,previous,states):
    if proof.state is not states.MATCH:
        return replace(proof,candidate_evidence_complete=False)
    if not previous:
        return replace(proof,state=states.BLOCKED,reason="PRIOR_STRICT_CANDIDATE_INCOMPLETE",
                       candidate_evidence_complete=False,mandatory_gaps=("PRIOR_PHASE",))
    if phase=="R_F":
        return _rf453(inputs,plan,proof,states)
    return replace(proof,candidate_evidence_complete=True)


def strict_chain453(inputs,plan,assessments,*,strategy,variant,states,ingredient):
    if not plan.strict_candidate_evidence:
        return assessments
    existing={route.phase:(route,proof) for route,proof in assessments}
    out=[]
    previous=True
    for phase in ("R0","R_C","R_E","R_F"):
        if phase in existing:
            route,proof=existing[phase]
        else:
            route=route_phase_inputs(inputs,zone_id="S2",strategy=strategy,variant_id=variant,phase=phase)
            proof=ingredient(states.MISSING,"EXPLICIT_PHASE_PLAN_MISSING",
                             mandatory_gaps=("PLAN_"+phase,))
        proof=_apply453(inputs,plan,proof,phase,previous,states)
        previous=proof.candidate_evidence_complete is True
        out.append((route,proof))
    return tuple(out)
