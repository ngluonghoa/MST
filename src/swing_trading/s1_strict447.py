"""§447 opt-in cumulative S1 candidate completeness, never action authority."""
from dataclasses import replace

from .phase_input_routing369 import route_phase_inputs


def _gaps447(proof,variant,phase):
    if phase=="R_C":
        return () if proof.rvol is not None else ("RC_RAW_VOLUME",)
    if phase!="R_F":
        return ()
    gaps=[]
    if proof.rvol is None:
        gaps.append("RF_RAW_VOLUME")
    if proof.holdings is None or proof.holdings.candidate_match is not True:
        gaps.append("RF_SETTLED_HOLDINGS_SCENARIO")
    if variant=="S1/F_MAJOR_CYCLE_TOP_PENDING":
        if proof.major is None or proof.major.candidate_match is not True:
            gaps.append("RF_W1_CLOSED_BREAK")
        if proof.major is None or proof.major.weekly_holdings is None:
            gaps.append("RF_W1_SETTLED_HOLDINGS_SCENARIO")
    return tuple(gaps)


def _apply447(proof,phase,variant,previous,states):
    if proof.state is not states.MATCH:
        return replace(proof,candidate_evidence_complete=False)
    if not previous:
        return replace(proof,state=states.BLOCKED,reason="PRIOR_STRICT_CANDIDATE_INCOMPLETE",
                       candidate_evidence_complete=False,mandatory_gaps=("PRIOR_PHASE",))
    gaps=_gaps447(proof,variant,phase)
    if gaps:
        return replace(proof,state=states.MISSING,reason="MANDATORY_CANDIDATE_INPUT_MISSING",
                       candidate_evidence_complete=False,mandatory_gaps=gaps)
    return replace(proof,candidate_evidence_complete=True)


def strict_chain447(inputs,plan,assessments,*,strategy,variant,states,ingredient):
    if not plan.strict_candidate_evidence:
        return assessments
    existing={route.phase:(route,proof) for route,proof in assessments}
    out=[]
    previous=True
    for phase in ("R0","R_C","R_E","R_F"):
        if phase in existing:
            route,proof=existing[phase]
        else:
            route=route_phase_inputs(inputs,zone_id="S1",strategy=strategy,variant_id=variant,phase=phase)
            proof=ingredient(states.MISSING,"EXPLICIT_PHASE_PLAN_MISSING",
                             mandatory_gaps=("PLAN_"+phase,))
        proof=_apply447(proof,phase,variant,previous,states)
        previous=proof.candidate_evidence_complete is True
        out.append((route,proof))
    return tuple(out)
