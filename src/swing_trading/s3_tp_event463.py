"""§463 explicit M15 closed target attainment; hypothetical event only, not a fill."""
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from .causal_structure_geometry import _eligible, _sequence, _source_identity
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .s1_choch442 import _validate_pivots442
from .s3_context454 import (
    S3TrendWindow454, S3State454, S3Preview454, _history454, _trend454, _window454,
)
from .s3_tp458 import S3TPPlan458, inspect_s3_tp_preview, _scope458, _validate458


@dataclass(frozen=True)
class S3TPEvent463:
    target_index: int
    plan_id: str
    plan_version: str
    source_event_id: str
    revision_digest: str
    bar_start_utc: datetime
    event_known_at_utc: datetime
    d1: S3TrendWindow454


@dataclass(frozen=True)
class S3TPEventPlan463:
    context: S3TPPlan458
    early: S3TPEvent463


@dataclass(frozen=True)
class S3TPEventIngredient463:
    state: S3State454
    reason: str
    private_event_id: str | None = None
    private_target_close: Decimal | None = None


def _validate_event463(p,context):
    if type(p) is not S3TPEvent463 or context.near is None:
        raise ValueError("MST_463_EXPLICIT_EVENT_AND_NEAR")
    if type(p.target_index) is not int or not context.near.target_index<=p.target_index<512:
        raise ValueError("MST_463_EXACT_EVENT_INDEX")
    if any(type(v) is not str or not v.strip() for v in
           (p.plan_id,p.plan_version,p.source_event_id,p.revision_digest)):
        raise ValueError("MST_463_EXACT_EVENT_IDENTITY")
    if any(type(v) is not datetime for v in (p.bar_start_utc,p.event_known_at_utc)):
        raise ValueError("MST_463_EXACT_EVENT_TIMES")
    require_utc(p.bar_start_utc)
    require_utc(p.event_known_at_utc)
    if type(p.d1) is not S3TrendWindow454:
        raise ValueError("MST_463_EXPLICIT_EVENT_D1_WINDOW")
    _window454(p.d1)
    _validate_pivots442(p.d1,p.d1.stop-p.d1.start)


def _matches_event463(p,scenario,bar,strategy,cutoff):
    return (_scope458(scenario,bar,strategy)
            and (p.plan_id,p.plan_version)==(scenario.plan_id,scenario.plan_version)
            and p.bar_start_utc==bar.market_bar_key.bar_start_utc
            and bar.verified_at_utc<=p.event_known_at_utc<=min(cutoff,scenario.expires_at_utc)
            and p.revision_digest==bar.observation_revision.source_revision_or_payload_digest
            and bar.source_event_ids.count(p.source_event_id)==1)


def _path463(rows,context,p,base,bar):
    if p.target_index==context.near.target_index:
        return S3State454.MATCH
    prior,_=_sequence(rows[context.near.target_index:p.target_index],cutoff=bar.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(bar):
        return S3State454.BLOCKED
    if any(not base.private_higher_low<=b.close<base.private_target for b in prior):
        return S3State454.NONMATCH
    return S3State454.MATCH


def _event_trend463(inputs,p,base,bar):
    history,state=_history454(inputs.snapshots_for(Timeframe.D1),p.d1,bar)
    if history is None:
        return S3TPEventIngredient463(state,"TP_EVENT_D1_CONTEXT_UNRESOLVED")
    trend=_trend454(history,p.d1,bar.market_bar_key.bar_start_utc)
    if trend.state is not S3State454.MATCH:
        return S3TPEventIngredient463(trend.state,trend.reason)
    if (trend.private_d1_hh<base.private_d1_hh
            or trend.private_higher_low<base.private_higher_low
            or bar.close<trend.private_higher_low):
        return S3TPEventIngredient463(S3State454.NONMATCH,"TP_EVENT_RISING_CONTEXT_LOST")
    return None


def _event463(inputs,plan,base,rc,strategy):
    p,context=plan.early,plan.context
    if rc.state is not S3State454.MATCH:
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_R_C_NOT_MATCHED")
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return S3TPEventIngredient463(S3State454.MISSING,"TP_EVENT_BAR_MISSING")
    bar=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if bar is None or not _matches_event463(p,context.target,bar,strategy,inputs.as_of_utc):
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_EVENT_IDENTITY_OR_CLOCK_UNRESOLVED")
    state=_path463(rows,context,p,base,bar)
    if state is not S3State454.MATCH:
        return S3TPEventIngredient463(state,"TP_EVENT_PRIOR_PATH_UNRESOLVED_OR_ALREADY_ATTAINED")
    denial=_event_trend463(inputs,p,base,bar)
    if denial is not None:
        return denial
    state=S3State454.MATCH if bar.close>=base.private_target else S3State454.NONMATCH
    return S3TPEventIngredient463(state,"CLOSED_HYPOTHETICAL_TP_ATTAINMENT_ONLY",
                                 p.source_event_id,bar.close)


def inspect_s3_tp_event_preview(inputs,*,strategy,variant_id,plan):
    if type(plan) is not S3TPEventPlan463:
        raise ValueError("MST_463_EXACT_EVENT_PLAN")
    preview=inspect_s3_tp_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.context)
    _validate_event463(plan.early,plan.context)
    base,rc=(g for _,g in preview.assessments)
    route=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R_E")
    return S3Preview454(preview.assessments+((route,_event463(inputs,plan,base,rc,strategy)),))


@dataclass(frozen=True)
class S3TPConfirmPlan464:
    event: S3TPEventPlan463
    confirmation: S3TPEvent463
    linked_early_event_id: str
    linked_early_revision_digest: str
    linked_early_start_utc: datetime


def _validate_confirm464(plan,variant):
    if type(plan) is not S3TPConfirmPlan464 or variant!="S3/F_TP":
        raise ValueError("MST_464_EXPLICIT_F_TP_VARIANT")
    if type(plan.event) is not S3TPEventPlan463:
        raise ValueError("MST_464_EXPLICIT_PRIOR_EVENT")
    if type(plan.event.context) is not S3TPPlan458:
        raise ValueError("MST_464_EXACT_TP_CONTEXT")
    _validate458(plan.event.context)
    _validate_event463(plan.event.early,plan.event.context)
    p,early=plan.confirmation,plan.event.early
    _validate_event463(p,plan.event.context)
    if p.target_index<=early.target_index or p.d1.stop<early.d1.stop:
        raise ValueError("MST_464_DISTINCT_LATER_CONFIRMATION")
    if any(type(v) is not str or not v.strip() for v in
           (plan.linked_early_event_id,plan.linked_early_revision_digest)):
        raise ValueError("MST_464_EXPLICIT_PRIOR_EVENT_LINK")
    if type(plan.linked_early_start_utc) is not datetime:
        raise ValueError("MST_464_EXACT_PRIOR_START")
    require_utc(plan.linked_early_start_utc)


def _linked464(plan,bar):
    e,p=plan.event.early,plan.confirmation
    return ((plan.linked_early_event_id,plan.linked_early_revision_digest,
             plan.linked_early_start_utc)==(e.source_event_id,e.revision_digest,e.bar_start_utc)
            and e.source_event_id!=p.source_event_id
            and e.event_known_at_utc<=bar.market_bar_key.bar_start_utc)


def _confirm_trend464(inputs,plan,base,early_bar,bar):
    e=plan.event.early
    history,state=_history454(inputs.snapshots_for(Timeframe.D1),e.d1,early_bar)
    if history is None:
        return S3TPEventIngredient463(state,"TP_RF_EARLY_D1_UNRESOLVED")
    trend=_trend454(history,e.d1,early_bar.market_bar_key.bar_start_utc)
    if trend.state is not S3State454.MATCH:
        return S3TPEventIngredient463(trend.state,trend.reason)
    current=replace(base,private_d1_hh=trend.private_d1_hh,
                    private_higher_low=trend.private_higher_low)
    return _event_trend463(inputs,plan.confirmation,current,bar)


def _confirm464(inputs,plan,base,early,strategy):
    if early.state is not S3State454.MATCH:
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_RF_RE_NOT_MATCHED")
    p,e=plan.confirmation,plan.event.early
    rows=inputs.snapshots_for(Timeframe.M15)
    if p.target_index>=len(rows):
        return S3TPEventIngredient463(S3State454.MISSING,"TP_RF_BAR_MISSING")
    bar=_eligible(rows[p.target_index],cutoff=inputs.as_of_utc)
    if bar is None or not _linked464(plan,bar):
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_RF_EVENT_LINK_OR_CLOCK")
    if not _matches_event463(p,plan.event.context.target,bar,strategy,inputs.as_of_utc):
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_RF_CONFIRM_IDENTITY")
    prior,_=_sequence(rows[e.target_index:p.target_index],cutoff=bar.market_bar_key.bar_start_utc)
    if not prior or _source_identity(prior[0])!=_source_identity(bar):
        return S3TPEventIngredient463(S3State454.BLOCKED,"TP_RF_PATH_UNRESOLVED")
    if any(b.close<base.private_higher_low for b in prior):
        return S3TPEventIngredient463(S3State454.NONMATCH,"TP_RF_PRIOR_D1_HL_LOSS")
    denial=_confirm_trend464(inputs,plan,base,prior[0],bar)
    if denial is not None:
        return denial
    state=S3State454.MATCH if bar.close>=base.private_target else S3State454.NONMATCH
    return S3TPEventIngredient463(state,"DISTINCT_CLOSED_HYPOTHETICAL_TP_CONFIRMATION_ONLY",
                                 p.source_event_id,bar.close)


def inspect_s3_tp_confirm_preview(inputs,*,strategy,variant_id,plan):
    _validate_confirm464(plan,variant_id)
    preview=inspect_s3_tp_event_preview(inputs,strategy=strategy,variant_id=variant_id,plan=plan.event)
    base,_,early=(g for _,g in preview.assessments)
    route=route_phase_inputs(inputs,zone_id="S3",strategy=strategy,variant_id=variant_id,phase="R_F")
    return S3Preview454(preview.assessments+((route,_confirm464(inputs,plan,base,early,strategy)),))
