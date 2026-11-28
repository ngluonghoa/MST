"""§506 explicit causal B1 R0 benchmark context, uncalibrated."""
from dataclasses import dataclass
from decimal import Decimal,localcontext

from .b1_decline499 import B1Preview499
from .b1_rf_volume505 import B1VolumePlan505,inspect_b1_volume505_preview
from .causal_structure_geometry import _sequence
from .market_data import InstrumentClass,Timeframe
from .s1_context_preview439 import S1State439
from .source_quality import ResolvedBarSnapshotV12


@dataclass(frozen=True)
class B1MarketWindow506:
    benchmark_id: str
    policy_version: str
    stock_start: int
    stock_stop: int
    benchmark_rows: tuple[ResolvedBarSnapshotV12,...]
    candidate_min_return: Decimal | None


@dataclass(frozen=True)
class B1MarketPlan506:
    prior: B1VolumePlan505
    market: B1MarketWindow506


@dataclass(frozen=True)
class B1MarketIngredient506:
    state: S1State439
    reason: str
    private_bottom: object
    private_market_return: Decimal | None = None


def _validate506(p):
    if type(p) is not B1MarketWindow506:
        raise ValueError("MST_506_EXACT_MARKET_WINDOW")
    if any(type(v) is not str or not v.strip() for v in (p.benchmark_id,p.policy_version)):
        raise ValueError("MST_506_EXPLICIT_BENCHMARK_AND_POLICY")
    if any(type(i) is not int for i in (p.stock_start,p.stock_stop)):
        raise ValueError("MST_506_EXACT_INDICES")
    if not 0<=p.stock_start<p.stock_stop<=512 or p.stock_stop-p.stock_start<2:
        raise ValueError("MST_506_EXACT_COMPARATOR_WINDOW")
    if type(p.benchmark_rows) is not tuple or len(p.benchmark_rows)!=p.stock_stop-p.stock_start:
        raise ValueError("MST_506_EXACT_BENCHMARK_LENGTH")
    if any(type(x) is not ResolvedBarSnapshotV12 for x in p.benchmark_rows):
        raise ValueError("MST_506_EXACT_BENCHMARK_ROWS")
    k=p.candidate_min_return
    if k is not None and (type(k) is not Decimal or not k.is_finite() or k<=-1):
        raise ValueError("MST_506_EXPLICIT_RETURN_THRESHOLD")


def _aligned506(a,b,p):
    x,y=a.market_bar_key,b.market_bar_key
    return (x.instrument_class is InstrumentClass.STOCK and y.instrument_class is InstrumentClass.INDEX
            and x.instrument_id!=y.instrument_id==p.benchmark_id
            and x.timeframe is y.timeframe is Timeframe.D1 and x.price_basis is y.price_basis
            and x.exchange==y.exchange and x.calendar_version==y.calendar_version
            and x.bar_start_utc==y.bar_start_utc and a.bar_end_utc==b.bar_end_utc
            and a.observation_key.project_id==b.observation_key.project_id and a.close>0 and b.close>0)


def _market506(inputs,p,stop,cutoff,bottom):
    rows=inputs.snapshots_for(Timeframe.D1)
    if p.stock_stop!=stop:
        return B1MarketIngredient506(S1State439.BLOCKED,"MARKET_WRONG_DECISION_WINDOW",bottom)
    if len(rows)<stop:
        return B1MarketIngredient506(S1State439.MISSING,"MARKET_STOCK_WINDOW_MISSING",bottom)
    stock,_=_sequence(rows[p.stock_start:stop],cutoff=cutoff)
    bench,_=_sequence(p.benchmark_rows,cutoff=cutoff)
    if not stock or not bench or not all(_aligned506(a,b,p) for a,b in zip(stock,bench)):
        return B1MarketIngredient506(S1State439.BLOCKED,"MARKET_SOURCE_CLOCK_OR_ALIGNMENT",bottom)
    with localcontext() as ctx:
        ctx.prec=50
        value=bench[-1].close/bench[0].close-1
    k=p.candidate_min_return
    state=S1State439.DISTANCE if k is None else S1State439.MATCH if value>=k else S1State439.NONMATCH
    return B1MarketIngredient506(state,"BENCHMARK_RETURN_CANDIDATE_ONLY",bottom,value)


def inspect_b1_market506_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not B1MarketPlan506 or type(plan.prior) is not B1VolumePlan505:
        raise ValueError("MST_506_EXACT_PRIOR_PLAN")
    _validate506(plan.market)
    preview=inspect_b1_volume505_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.prior)
    route,bottom=preview.assessments[0]
    if bottom.state is not S1State439.MATCH:
        return preview
    origin=plan.prior.geometry.early.context.context
    anchor=inputs.snapshots_for(Timeframe.M15)[origin.evaluation_index].selected
    proof=_market506(inputs,plan.market,origin.stop,anchor.market_bar_key.bar_start_utc,bottom)
    return B1Preview499(((route,proof),)+(preview.assessments[1:] if proof.state is S1State439.MATCH else ()))
