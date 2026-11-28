"""§507 B1 later RF market context with preserved R0 definition."""
from dataclasses import dataclass

from .b1_decline499 import B1Preview499
from .b1_market506 import B1MarketPlan506,B1MarketWindow506,_validate506,_market506,inspect_b1_market506_preview
from .relative_strength421 import _same_stream422,_overlap422
from .market_data import Timeframe
from .s1_context_preview439 import S1State439


@dataclass(frozen=True)
class B1MarketPlan507:
    prior: B1MarketPlan506
    market: B1MarketWindow506


@dataclass(frozen=True)
class B1MarketIngredient507:
    state: S1State439
    reason: str
    private_volume: object
    private_market: object = None


def _definition507(p):
    return (p.benchmark_id,p.policy_version,p.stock_stop-p.stock_start,p.candidate_min_return)


def _lineage507(inputs,early,later):
    if _definition507(early)!=_definition507(later) or later.stock_stop<=early.stock_stop:
        return False
    daily=inputs.snapshots_for(Timeframe.D1)
    return (_same_stream422(early.benchmark_rows,later.benchmark_rows)
            and _overlap422(early.benchmark_rows,later.benchmark_rows)
            and _same_stream422(daily[early.stock_start:early.stock_stop],daily[later.stock_start:later.stock_stop]))


def inspect_b1_market507_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not B1MarketPlan507 or type(plan.prior) is not B1MarketPlan506:
        raise ValueError("MST_507_EXACT_PRIOR_PLAN")
    _validate506(plan.market)
    preview=inspect_b1_market506_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.prior)
    if len(preview.assessments)!=4 or any(p.state is not S1State439.MATCH for _,p in preview.assessments):
        return preview
    route,volume=preview.assessments[-1]
    i=plan.prior.prior.geometry.target_index
    target=inputs.snapshots_for(Timeframe.D1)[i].selected
    market=_market506(inputs,plan.market,i+1,target.verified_at_utc,volume)
    if market.state is S1State439.MATCH and not _lineage507(inputs,plan.prior.market,plan.market):
        proof=B1MarketIngredient507(S1State439.BLOCKED,"RF_MARKET_DEFINITION_OR_LINEAGE_CHANGED",volume,market)
    else:
        proof=B1MarketIngredient507(market.state,market.reason,volume,market)
    return B1Preview499(preview.assessments[:-1]+((route,proof),))
