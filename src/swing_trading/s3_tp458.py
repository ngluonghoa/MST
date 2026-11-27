"""§458 explicit pre-existing hypothetical TP scenario; never actual plan approval."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .causal_structure_geometry import _eligible, _sequence, _source_identity
from .contracts import Strategy
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .replay import require_utc
from .s1_choch442 import _validate_pivots442
from .feature_engine460 import inspect_target_d1_atr as _atr441
from .s3_context454 import (
    S3TrendWindow454, S3NearPlan455, S3State454, S3Preview454,
    _window454, _history454, _trend454, _validate_near455,
)


@dataclass(frozen=True)
class S3TargetScenario458:
    instrument_id: str
    strategy: Strategy
    plan_id: str
    plan_version: str
    known_at_utc: datetime
    expires_at_utc: datetime
    target_price: Decimal


@dataclass(frozen=True)
class S3TPPlan458:
    anchor_index: int
    d1: S3TrendWindow454
    target: S3TargetScenario458
    near: S3NearPlan455 | None=None


@dataclass(frozen=True)
class S3TPIngredient458:
    state: S3State454
    reason: str
    private_d1_hh: Decimal | None=None
    private_higher_low: Decimal | None=None
    private_target: Decimal | None=None
    private_atr: Decimal | None=None
    private_distance: Decimal | None=None
    private_extension_atr: Decimal | None=None


def _validate_target458(p):
    if type(p) is not S3TargetScenario458 or type(p.strategy) is not Strategy:
        raise ValueError("MST_458_EXPLICIT_TP_SCENARIO")
    if any(type(v) is not str or not v.strip() for v in (p.instrument_id,p.plan_id,p.plan_version)):
        raise ValueError("MST_458_EXPLICIT_PLAN_SCOPE")
    if any(type(v) is not datetime for v in (p.known_at_utc,p.expires_at_utc)):
        raise ValueError("MST_458_EXACT_PLAN_TIMES")
    require_utc(p.known_at_utc)
    require_utc(p.expires_at_utc)
    if p.known_at_utc>=p.expires_at_utc:
        raise ValueError("MST_458_PLAN_WINDOW")
    if type(p.target_price) is not Decimal or not p.target_price.is_finite() or p.target_price<=0:
        raise ValueError("MST_458_EXPLICIT_TARGET_PRICE")


def _validate458(p):
    if type(p.anchor_index) is not int or not 0<=p.anchor_index<512:
        raise ValueError("MST_458_EXACT_ANCHOR")
    if type(p.d1) is not S3TrendWindow454:
        raise ValueError("MST_458_EXPLICIT_D1_WINDOW")
    _window454(p.d1)
    _validate_pivots442(p.d1,p.d1.stop-p.d1.start)
    _validate_target458(p.target)
    if p.near is not None:
        _validate_near455(p.near,p.anchor_index)


def _scope458(p,bar,strategy):
    return (p.instrument_id==bar.market_bar_key.instrument_id
            and p.strategy is strategy
            and p.known_at_utc<=bar.market_bar_key.bar_start_utc
            and bar.verified_at_utc<=p.expires_at_utc)


def _r0458(inputs,p,strategy):
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.anchor_index>=len(rows):
        return S3TPIngredient458(S3State454.MISSING,"TP_ANCHOR_MISSING")
    anchor=_eligible(rows[p.anchor_index],cutoff=inputs.as_of_utc)
    if anchor is None or not _scope458(p.target,anchor,strategy):
        return S3TPIngredient458(S3State454.BLOCKED,"TP_PLAN_NOT_CAUSAL_ACTIVE_OR_SCOPED")
    history,state=_history454(inputs.snapshots_for(Timeframe.D1),p.d1,anchor)
    if history is None:
        return S3TPIngredient458(state,"TP_D1_CONTEXT_UNRESOLVED")
    trend=_trend454(history,p.d1,anchor.market_bar_key.bar_start_utc)
    if trend.state is not S3State454.MATCH:
        return S3TPIngredient458(trend.state,trend.reason)
    match=trend.private_higher_low<=anchor.close<=p.target.target_price
    state=S3State454.MATCH if match else S3State454.NONMATCH
    return S3TPIngredient458(state,"HYPOTHETICAL_PREEXISTING_TP_TARGET_ONLY",
                            trend.private_d1_hh,trend.private_higher_low,p.target.target_price)


def _near_geometry458(base,anchor,target,prior,atr,p):
    distance=base.private_target-target.close
    extension=(target.close-base.private_higher_low)/atr
    if target.close<=anchor.close or distance<0 or extension<0:
        state=S3State454.NONMATCH
    elif any(not base.private_higher_low<=b.close<=base.private_target for b in prior):
        state=S3State454.NONMATCH
    elif p.candidate_k_near is None or p.candidate_min_extension is None:
        state=S3State454.DISTANCE
    else:
        match=distance<=p.candidate_k_near*atr and extension>=p.candidate_min_extension
        state=S3State454.MATCH if match else S3State454.NONMATCH
    return S3TPIngredient458(state,"NEAR_HYPOTHETICAL_TP_EXTENSION_ONLY",
        base.private_d1_hh,base.private_higher_low,base.private_target,atr,distance,extension)


def _near458(inputs,plan,base,strategy):
    p=plan.near
    if base.state is not S3State454.MATCH:
        return S3TPIngredient458(S3State454.BLOCKED,"TP_R0_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows) or p.atr_stop>len(inputs.snapshots_for(Timeframe.D1)):
        return S3TPIngredient458(S3State454.MISSING,"TP_NEAR_TARGET_OR_ATR_MISSING")
    target=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if target is None or not _scope458(plan.target,target,strategy):
        return S3TPIngredient458(S3State454.BLOCKED,"TP_NEAR_PLAN_NOT_ACTIVE_OR_CAUSAL")
    prior,_=_sequence(rows[plan.anchor_index:p.target_index],cutoff=target.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(target):
        return S3TPIngredient458(S3State454.BLOCKED,"TP_NEAR_PATH_NOT_CAUSAL")
    history,state=_history454(inputs.snapshots_for(Timeframe.D1),plan.d1,target)
    if history is None:
        return S3TPIngredient458(state,"TP_NEAR_D1_CONTEXT_NOT_CURRENT")
    atr=_atr441(inputs,p,target)
    if atr is None or atr<=0:
        return S3TPIngredient458(S3State454.BLOCKED,"TP_NEAR_ATR_UNRESOLVED")
    return _near_geometry458(base,prior[0],target,prior,atr,p)


def inspect_s3_tp_preview(inputs,*,strategy,variant_id,plan):
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(plan) is not S3TPPlan458 or variant_id not in ("S3/E_TP","S3/F_TP")):
        raise ValueError("MST_458_EXACT_TP_SCOPE")
    _validate458(plan)
    route=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R0")
    base=_r0458(inputs,plan,strategy)
    assessments=((route,base),)
    if plan.near is not None:
        rc=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R_C")
        assessments+=((rc,_near458(inputs,plan,base,strategy)),)
    return S3Preview454(assessments)
