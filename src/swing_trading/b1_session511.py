"""§511 later causal D1 raw session candidate, never a fill."""
from dataclasses import dataclass
from decimal import localcontext

from .b1_decline499 import B1Preview499
from .b1_entry510 import B1EntryPlan510,inspect_b1_entry510_preview
from .b1_risk509 import _scope509,_net509
from .b8_price_band426 import B8PriceBand426,inspect_band426,validate_band426
from .causal_structure_geometry import _eligible,_sequence,_source_identity
from .market_data import Timeframe
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1SessionPlan511:
    prior: B1EntryPlan510
    target_index: int
    band: B8PriceBand426


@dataclass(frozen=True)
class B1SessionIngredient511:
    state: S1State439
    reason: str
    private_prior: object
    private_band: object = None
    private_risk: object = None
    private_candidate: object = None


def _validate511(p):
    if type(p) is not B1SessionPlan511 or type(p.prior) is not B1EntryPlan510:
        raise ValueError("MST_511_EXACT_PRIOR")
    if type(p.target_index) is not int or not 0<=p.target_index<512:
        raise ValueError("MST_511_EXACT_D1_TARGET")
    validate_band426(p.band)


def _candidate511(inputs,p,entry):
    risk=entry.private_prior
    g,_,d1,reference,_=_scope509(inputs,p.prior.prior,risk.private_prior)
    rows=inputs.snapshots_for(Timeframe.D1)
    i=p.target_index
    if i>=len(rows):
        return B1SessionIngredient511(S1State439.MISSING,"LATER_D1_MISSING",entry)
    target=_eligible(rows[i],cutoff=inputs.as_of_utc)
    if target is None or i<=g.target_index or target.market_bar_key.bar_start_utc<=reference.verified_at_utc:
        return B1SessionIngredient511(S1State439.BLOCKED,"D1_NOT_LATER_THAN_SIGNAL",entry)
    if any(s.market_bar_key.bar_start_utc>reference.verified_at_utc for s in rows[g.target_index+1:i]):
        return B1SessionIngredient511(S1State439.BLOCKED,"NOT_FIRST_SUPPLIED_LATER_D1",entry)
    path,_=_sequence(rows[g.target_index:i+1],cutoff=target.verified_at_utc)
    if not path or _source_identity(d1)!=_source_identity(target):
        return B1SessionIngredient511(S1State439.BLOCKED,"D1_SOURCE_OR_PATH",entry)
    if any(b.low<=risk.private_stop for b in path[1:]):
        return B1SessionIngredient511(S1State439.NONMATCH,"STRUCTURAL_STOP_TOUCHED",entry)
    return _grid511(p,entry,target)


def _grid511(p,entry,target):
    band=inspect_band426(target,p.band,max_entry=entry.private_max_entry)
    if band.state=="BLOCKED":
        return B1SessionIngredient511(S1State439.BLOCKED,band.reason,entry,band)
    risk=entry.private_prior
    if band.candidate_match is not True or not entry.private_pivot<target.close<risk.private_target:
        return B1SessionIngredient511(S1State439.NONMATCH,"RAW_GRID_OR_GEOMETRY_NONMATCH",entry,band)
    with localcontext() as ctx:
        ctx.prec=50
        result=_net509(p.prior.prior.risk,risk.private_prior,target.close,risk.private_stop,risk.private_target)
    return B1SessionIngredient511(result.state,"LATER_D1_RAW_CLOSE_CANDIDATE_ONLY",entry,band,result,target)


def inspect_b1_session511_preview(inputs,*,strategy,variant_id,plan):
    _validate511(plan)
    preview=inspect_b1_entry510_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.prior)
    a=preview.assessments
    if len(a)!=4 or any(p.state is not S1State439.MATCH for _,p in a):
        return preview
    route,rf=a[-1]
    return B1Preview499(a[:-1]+((route,_candidate511(inputs,plan,rf)),))
