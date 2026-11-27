"""Fail-closed signal engine plus §375 opt-in baseline preview dispatcher.

The existing legacy API stays available and all actual SignalDecision values
remain UNVERIFIED. The new path is private, deterministic and does not call
providers, cache, UI publisher, broker, or an approved detector.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from .contracts import (
    DecisionStatus, Strategy, SignalDecision, ZONE_IDS, evaluate_unimplemented_zones,
)
from .private_multitf_readiness import BaselineResolvedInputs
from .market_data import Timeframe
from .causal_structure_geometry import TiePolicy
from .feature_engine460 import inspect_current_d1_context
from .structural_phase_evidence import ROUTES, inspect_routed_phase_bos
from .b2s2_swing_evidence215 import (
    B2S2BaselinePreview371, B2S2PreviewPlan371, inspect_b2s2_baseline_preview,
)
from .b5_formula_geometry import (
    B5RetestPlan372, B5RFPlan373, B5RFVolumePlan373, B5RFPreview373,
    inspect_b5_baseline_confirmation,
)
from .s7_retest_evidence import (
    S7BaselinePreview374, S7OriginPlan374, S7MicroPlan374, inspect_s7_baseline_preview,
)
from .range_baseline_preview385 import RangeEnginePlan385, RangeEnginePreview385, inspect_routed_range_preview
from .s4_rejection467 import S4RejectionPlan467, inspect_s4_rejection_preview, S4FalseBreakPlan468, inspect_s4_false_break_preview, S4BosDownPlan469, inspect_s4_bos_down_preview, S4ConfirmPlan470, inspect_s4_confirm_preview
from .s4_holdings471 import S4HoldingsPlan471, inspect_s4_holdings_preview, S4StrictPlan472, inspect_s4_strict_preview
from .s5_transition473 import S5TransitionPlan473,S5Preview473,inspect_s5_transition_preview,S5RallyPlan474,inspect_s5_rally_preview,S5EarlyPlan475,inspect_s5_early_preview,S5ConfirmPlan476,inspect_s5_confirm_preview
from .s5_holdings477 import S5HoldingsPlan477,inspect_s5_holdings_preview,S5StrictPlan478,inspect_s5_strict_preview
from .s6_breakout479 import S6BreakoutPlan479,S6Preview479,inspect_s6_breakout_preview,S6FailurePlan480,inspect_s6_failure_preview,S6EarlyPlan481,inspect_s6_early_preview,S6ConfirmPlan482,inspect_s6_confirm_preview
from .s7_breakdown486 import S7BreakdownPlan486,S7Preview486,inspect_s7_breakdown_preview,S7RetestPlan487,inspect_s7_retest487_preview,S7EarlyPlan488,inspect_s7_early488_preview,S7ConfirmPlan489,inspect_s7_confirm489_preview
from .s8_context492 import S8ContextPlan492,S8Preview492,inspect_s8_context492_preview,S8ExhaustionPlan493,inspect_s8_exhaustion493_preview,S8EarlyPlan494,inspect_s8_early494_preview,S8ConfirmPlan495,inspect_s8_confirm495_preview
from .s8_rf_volume496 import S8VolumePlan496,inspect_s8_volume496_preview
from .s7_holdings490 import S7HoldingsPlan490,inspect_s7_holdings490_preview,S7StrictPlan491,inspect_s7_strict491_preview
from .s6_rf_volume483 import S6VolumePlan483,inspect_s6_volume_preview
from .s6_holdings484 import S6HoldingsPlan484,inspect_s6_holdings_preview,S6StrictPlan485,inspect_s6_strict_preview
from .b6_baseline_preview387 import (B6EnginePlan387, B6EnginePreview387, B6CompressionPlan396,
                                     inspect_b6_baseline_preview, inspect_b6_compression_preview)
from .b7_support_preview409 import B7SupportPlan409, B7SupportPreview409, inspect_b7_support_preview
from .b8_base_preview415 import B8BasePlan415, B8Preview415, inspect_b8_preview
from .s1_context_preview439 import S1ContextPlan439, S1Preview439, inspect_s1_preview
from .s2_context448 import S2ContextPlan448, S2Preview448, inspect_s2_preview
from .s3_context454 import S3ContextPlan454, S3Preview454, inspect_s3_preview
from .s3_tp458 import S3TPPlan458, inspect_s3_tp_preview
from .s3_tp_event463 import S3TPEventPlan463, inspect_s3_tp_event_preview, S3TPConfirmPlan464, inspect_s3_tp_confirm_preview
from .s3_holdings465 import S3HoldingsPlan465, inspect_s3_holdings_preview, S3StrictPlan466, inspect_s3_strict_preview
from .zone_manifest_v03 import MANIFESTS

PREVIEW_ZONES = ("B2", "B5", "S2", "S7")
STRUCTURAL_PREVIEW_ZONES = tuple(z for z in ZONE_IDS if any(k[0] == z for k in ROUTES))


@dataclass(frozen=True)
class B5EnginePlan375:
    retest: B5RetestPlan372
    rf: B5RFPlan373
    volume: B5RFVolumePlan373 | None = None


@dataclass(frozen=True)
class S7EnginePlan375:
    origin: S7OriginPlan374
    micro: S7MicroPlan374 | None = None


@dataclass(frozen=True)
class StructuralPhasePlan376:
    phase: str
    timeframe: Timeframe
    breakout_index: int
    pivot_index: int
    left_count: int
    right_count: int
    atr_start: int
    atr_stop: int
    tie_policy: TiePolicy
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class StructuralEnginePlan376:
    phases: tuple[StructuralPhasePlan376, ...]


@dataclass(frozen=True)
class StructuralEnginePreview376:
    zone_id: str
    strategy: Strategy
    variant_id: str
    as_of_utc: datetime
    assessments: tuple

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


@dataclass(frozen=True)
class BaselinePreviewRequest375:
    zone_id: str
    strategy: Strategy
    variant_id: str
    plan: B2S2PreviewPlan371 | B5EnginePlan375 | S7EnginePlan375 | StructuralEnginePlan376 | RangeEnginePlan385 | B6EnginePlan387 | B6CompressionPlan396 | B7SupportPlan409 | B8BasePlan415 | S1ContextPlan439 | S2ContextPlan448 | S3ContextPlan454 | S3TPPlan458 | S3TPEventPlan463 | S3TPConfirmPlan464 | S3HoldingsPlan465 | S3StrictPlan466 | S4RejectionPlan467 | S4FalseBreakPlan468 | S4BosDownPlan469 | S4ConfirmPlan470 | S4HoldingsPlan471 | S4StrictPlan472 | S5TransitionPlan473 | S5RallyPlan474 | S5EarlyPlan475 | S5ConfirmPlan476 | S5HoldingsPlan477 | S5StrictPlan478 | S6BreakoutPlan479 | S6FailurePlan480 | S6EarlyPlan481 | S6ConfirmPlan482 | S6VolumePlan483 | S6HoldingsPlan484 | S6StrictPlan485 | S7BreakdownPlan486 | S7RetestPlan487 | S7EarlyPlan488 | S7ConfirmPlan489 | S7HoldingsPlan490 | S7StrictPlan491 | S8ContextPlan492 | S8ExhaustionPlan493 | S8EarlyPlan494 | S8ConfirmPlan495 | S8VolumePlan496


@dataclass(frozen=True)
class BaselineZonePreview375:
    decision: SignalDecision
    variant_id: str | None
    reason: str
    private_preview: object | None


@dataclass(frozen=True)
class BaselineEnginePreview375:
    as_of_utc: datetime
    rows: tuple[BaselineZonePreview375, ...]

    @property
    def publication_state(self):
        return "INCOMPLETE_REPORT"

    @property
    def decision(self):
        return "NO_TRADE"

    def safe_summary(self):
        """No source rows, symbols, prices, candidate parameters or raw IDs."""
        return {
            "schema": "mst.private.baseline_engine_preview.v0.1",
            "as_of_utc": self.as_of_utc.isoformat(),
            "zones": [{
                "zone_id": r.decision.zone_id, "strategy": r.decision.strategy.value,
                "status": r.decision.status.value, "variant_id": r.variant_id,
                "reason": r.reason, "preview_present": r.private_preview is not None,
                "structural_preview_supported": r.decision.zone_id in STRUCTURAL_PREVIEW_ZONES,
            } for r in self.rows],
            "publication_state": self.publication_state, "decision": self.decision,
            "source_released": False, "detector_parity_verified": False, "trade_orders": 0,
        }


    def safe_phase_summary(self):
        """Separate redacted contract; legacy summary and decisions unchanged."""
        summary = self.safe_summary()
        summary["schema"] = "mst.private.baseline_engine_phase_preview.v0.1"
        for output, row in zip(summary["zones"], self.rows):
            output["phases"] = _phase_rows377(row)
        return summary



_PHASES377 = ("R0", "R_C", "R_E", "R_F")
_GEOMETRY377 = {
    "BLOCKED": "BLOCKED",
    "MISSING_INPUT": "MISSING_INPUT",
    "GEOMETRY_MATCH_UNVERIFIED": "GEOMETRY_MATCH_ONLY",
    "GEOMETRY_NONMATCH_UNVERIFIED": "GEOMETRY_NONMATCH_ONLY",
    "CROSS_GEOMETRY_UNVERIFIED": "GEOMETRY_MATCH_ONLY",
    "NONCROSS_GEOMETRY_ONLY": "GEOMETRY_NONMATCH_ONLY",
    "CAUSAL_DISTANCE_UNCALIBRATED": "DISTANCE_ONLY",
    "RAW_RETEST_UNCALIBRATED": "CHAIN_GEOMETRY_ONLY",
    "RAW_CONFIRMATION_UNCALIBRATED": "CHAIN_GEOMETRY_ONLY",
}


def _route_input_state377(route):
    if route is None:
        return "NOT_ROUTED"
    if any(x.startswith("MISSING_") for x in route.unresolved):
        return "MISSING_REQUIRED_INPUT"
    if any(x.startswith(("UNRESOLVED_REVISION_", "LOCAL_PREREQUISITES_INCOMPLETE_"))
           for x in route.unresolved):
        return "BLOCKED_REQUIRED_INPUT"
    return "REQUIREMENTS_PENDING"


def _pair_states377(preview):
    return {r.phase: (r, _GEOMETRY377.get(e.state.value, "BLOCKED"))
            for r, e in preview.assessments}


def _b5_states377(preview):
    base = _GEOMETRY377.get(preview.retest.state.value, "BLOCKED")
    # The retest result is combined R0/RC/RE geometry, not three phase passes.
    if base == "GEOMETRY_NONMATCH_ONLY":
        base = "CHAIN_NONMATCH_ONLY"
    return dict([(r.phase, (r, base)) for r in preview.retest.routed_phases]
                + [("R_F", (preview.routed_rf,
                            _GEOMETRY377.get(preview.state.value, "BLOCKED")))])


def _s7_retest_state377(retest):
    if retest is None:
        return "MISSING_INPUT"
    return "CHAIN_GEOMETRY_ONLY" if retest.retest_preview_id is not None else "BLOCKED"


def _s7_early_state377(early):
    if early is None:
        return "NOT_EVALUATED"
    if early.shape_observed is True:
        return "GEOMETRY_MATCH_ONLY"
    if early.shape_observed is False:
        return "GEOMETRY_NONMATCH_ONLY"
    return "BLOCKED"


def _s7_rf_state377(preview):
    if preview.variant_id == "S7/F_CONTINUATION":
        return "SPEC_PENDING"
    if preview.confirmation is None:
        return "MISSING_INPUT" if preview.reason == "MICRO_INPUT_MISSING" else "NOT_EVALUATED"
    return ("CHAIN_GEOMETRY_ONLY" if preview.confirmation.confirmation_preview_id is not None
            else "BLOCKED")


def _s7_states377(preview):
    base = _s7_retest_state377(preview.retest)
    states = (base, base, _s7_early_state377(preview.early), _s7_rf_state377(preview))
    return {r.phase: (r, state) for r, state in zip(preview.routed_phases, states)}


def _preview_states377(preview):
    if type(preview) in (B2S2BaselinePreview371, StructuralEnginePreview376, RangeEnginePreview385, B6EnginePreview387, B7SupportPreview409, B8Preview415, S1Preview439, S2Preview448, S3Preview454, S5Preview473, S6Preview479, S7Preview486, S8Preview492):
        return _pair_states377(preview)
    if type(preview) is B5RFPreview373:
        return _b5_states377(preview)
    if type(preview) is S7BaselinePreview374:
        return _s7_states377(preview)
    if preview is not None:
        raise RuntimeError("MST_377_UNKNOWN_PREVIEW_TYPE")
    return {}


def _phase_rows377(row):
    states = _preview_states377(row.private_preview)
    default = "NOT_REQUESTED" if row.private_preview is not None else "NOT_CONFIGURED"
    if row.reason == "PREVIEW_REJECTED_UNVERIFIED":
        default = "CONFIG_REJECTED"
    return [_phase_row377(p, *states.get(p, (None, default))) for p in _PHASES377]


def _phase_row377(phase, route, state):
    inputs = _route_input_state377(route)
    if state == "BLOCKED" and inputs == "MISSING_REQUIRED_INPUT":
        state = "MISSING_INPUT"
    return {"phase": phase, "ingredient_state": state, "input_state": inputs,
            "phase_verified": False, "action_eligible": False}


def _request_supported376(request):
    if type(request) is not BaselinePreviewRequest375:
        return False
    if type(request.zone_id) is not str or type(request.strategy) is not Strategy:
        return False
    if type(request.plan) in (B6EnginePlan387, B6CompressionPlan396):
        return request.zone_id == "B6"
    if type(request.plan) in (S3ContextPlan454, S3TPPlan458, S3TPEventPlan463, S3TPConfirmPlan464, S3HoldingsPlan465, S3StrictPlan466):
        return request.zone_id == "S3"
    if type(request.plan) is S2ContextPlan448:
        return request.zone_id == "S2"
    if type(request.plan) is S1ContextPlan439:
        return request.zone_id == "S1"
    if type(request.plan) is B8BasePlan415:
        return request.zone_id == "B8"
    if type(request.plan) is B7SupportPlan409:
        return request.zone_id == "B7"
    if type(request.plan) in (S8ContextPlan492,S8ExhaustionPlan493,S8EarlyPlan494,S8ConfirmPlan495,S8VolumePlan496):
        return request.zone_id == "S8"
    if type(request.plan) in (S7BreakdownPlan486,S7RetestPlan487,S7EarlyPlan488,S7ConfirmPlan489,S7HoldingsPlan490,S7StrictPlan491):
        return request.zone_id == "S7"
    if type(request.plan) in (S6BreakoutPlan479,S6FailurePlan480,S6EarlyPlan481,S6ConfirmPlan482,S6VolumePlan483,S6HoldingsPlan484,S6StrictPlan485):
        return request.zone_id == "S6"
    if type(request.plan) in (S5TransitionPlan473,S5RallyPlan474,S5EarlyPlan475,S5ConfirmPlan476,S5HoldingsPlan477,S5StrictPlan478):
        return request.zone_id == "S5"
    if type(request.plan) in (S4RejectionPlan467, S4FalseBreakPlan468, S4BosDownPlan469, S4ConfirmPlan470, S4HoldingsPlan471, S4StrictPlan472):
        return request.zone_id == "S4"
    if type(request.plan) is RangeEnginePlan385:
        return request.zone_id in ("B3", "S4")
    if request.zone_id in PREVIEW_ZONES:
        return True
    return (type(request.plan) is StructuralEnginePlan376
            and request.zone_id in STRUCTURAL_PREVIEW_ZONES)


def _request_index375(requests):
    if type(requests) is not tuple or len(requests) > 32:
        raise ValueError("MST_375_BOUNDED_REQUEST_TUPLE")
    indexed = {}
    for request in requests:
        if not _request_supported376(request):
            raise ValueError("MST_375_UNSUPPORTED_REQUEST")
        key = (request.zone_id, request.strategy)
        if key in indexed:
            raise ValueError("MST_375_DUPLICATE_ZONE_STRATEGY")
        indexed[key] = request
    return indexed


def _structural376(inputs, request):
    phases = request.plan.phases
    if (type(phases) is not tuple or not 1 <= len(phases) <= 2
            or any(type(p) is not StructuralPhasePlan376 for p in phases)):
        raise ValueError("MST_376_EXPLICIT_PHASE_TUPLE")
    names = tuple(p.phase for p in phases)
    if names not in (("R_E",), ("R_F",), ("R_E", "R_F")):
        raise ValueError("MST_376_DUPLICATE_OR_UNORDERED_PHASE")
    scope = dict(zone_id=request.zone_id, strategy=request.strategy,
                 variant_id=request.variant_id)
    for plan in phases:
        route = ROUTES.get((request.zone_id, request.variant_id, plan.phase))
        if route is None or type(plan.timeframe) is not Timeframe or plan.timeframe not in route[1]:
            raise ValueError("MST_376_EXACT_STRUCTURAL_ROUTE_REQUIRED")
    assessments = tuple(inspect_routed_phase_bos(inputs, **scope, **asdict(plan))
                        for plan in phases)
    return StructuralEnginePreview376(request.zone_id, request.strategy,
                                      request.variant_id, inputs.as_of_utc, assessments)


def _dispatch375(inputs, request):
    zone, strategy, variant, plan = (
        request.zone_id, request.strategy, request.variant_id, request.plan)
    if type(variant) is not str or variant not in MANIFESTS[zone].variants:
        raise ValueError("MST_375_VARIANT_INVALID")
    if type(plan) is S3StrictPlan466:
        return inspect_s3_strict_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S3HoldingsPlan465:
        return inspect_s3_holdings_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S3TPConfirmPlan464:
        return inspect_s3_tp_confirm_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S3TPEventPlan463:
        return inspect_s3_tp_event_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S3TPPlan458:
        return inspect_s3_tp_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S3ContextPlan454:
        return inspect_s3_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S2ContextPlan448:
        return inspect_s2_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S1ContextPlan439:
        return inspect_s1_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is B8BasePlan415:
        return inspect_b8_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is B7SupportPlan409:
        return inspect_b7_support_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is B6CompressionPlan396:
        return inspect_b6_compression_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is B6EnginePlan387:
        return inspect_b6_baseline_preview(inputs, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is S8VolumePlan496:
        return inspect_s8_volume496_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S8ConfirmPlan495:
        return inspect_s8_confirm495_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S8EarlyPlan494:
        return inspect_s8_early494_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S8ExhaustionPlan493:
        return inspect_s8_exhaustion493_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S8ContextPlan492:
        return inspect_s8_context492_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7StrictPlan491:
        return inspect_s7_strict491_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7HoldingsPlan490:
        return inspect_s7_holdings490_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7ConfirmPlan489:
        return inspect_s7_confirm489_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7EarlyPlan488:
        return inspect_s7_early488_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7RetestPlan487:
        return inspect_s7_retest487_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S7BreakdownPlan486:
        return inspect_s7_breakdown_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6StrictPlan485:
        return inspect_s6_strict_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6HoldingsPlan484:
        return inspect_s6_holdings_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6VolumePlan483:
        return inspect_s6_volume_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6ConfirmPlan482:
        return inspect_s6_confirm_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6EarlyPlan481:
        return inspect_s6_early_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6FailurePlan480:
        return inspect_s6_failure_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S6BreakoutPlan479:
        return inspect_s6_breakout_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5StrictPlan478:
        return inspect_s5_strict_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5HoldingsPlan477:
        return inspect_s5_holdings_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5ConfirmPlan476:
        return inspect_s5_confirm_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5EarlyPlan475:
        return inspect_s5_early_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5RallyPlan474:
        return inspect_s5_rally_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S5TransitionPlan473:
        return inspect_s5_transition_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4StrictPlan472:
        return inspect_s4_strict_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4HoldingsPlan471:
        return inspect_s4_holdings_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4ConfirmPlan470:
        return inspect_s4_confirm_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4BosDownPlan469:
        return inspect_s4_bos_down_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4FalseBreakPlan468:
        return inspect_s4_false_break_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is S4RejectionPlan467:
        return inspect_s4_rejection_preview(inputs,strategy=strategy,variant_id=variant,plan=plan)
    if type(plan) is RangeEnginePlan385:
        return inspect_routed_range_preview(inputs, zone_id=zone, strategy=strategy, variant_id=variant, plan=plan)
    if type(plan) is StructuralEnginePlan376:
        return _structural376(inputs, request)
    if zone in ("B2", "S2") and type(plan) is B2S2PreviewPlan371:
        return inspect_b2s2_baseline_preview(
            inputs, zone_id=zone, strategy=strategy, plan=plan)
    if zone == "B5" and type(plan) is B5EnginePlan375:
        return inspect_b5_baseline_confirmation(
            inputs, strategy=strategy, variant_id=variant, retest_plan=plan.retest,
            rf_plan=plan.rf, volume_plan=plan.volume)
    if zone == "S7" and type(plan) is S7EnginePlan375:
        return inspect_s7_baseline_preview(
            inputs, strategy=strategy, variant_id=variant, origin_plan=plan.origin,
            micro_plan=plan.micro)
    raise ValueError("MST_375_PLAN_TYPE_MISMATCH")


def _row375(inputs, decision, request):
    if request is None:
        reason = ("PREVIEW_NOT_CONFIGURED" if decision.zone_id in PREVIEW_ZONES
                  else "FULL_DETECTOR_SPEC_PENDING")
        return BaselineZonePreview375(decision, None, reason, None)
    try:
        preview = _dispatch375(inputs, request)
    except (TypeError, ValueError):
        # Malformed explicit preview configuration is isolated to its scope;
        # never echo exception text or manufacture a negative signal.
        return BaselineZonePreview375(decision, None, "PREVIEW_REJECTED_UNVERIFIED", None)
    if preview.status is not DecisionStatus.UNVERIFIED or preview.action_eligible is not False:
        raise RuntimeError("MST_375_PREVIEW_AUTHORITY_DRIFT")
    return BaselineZonePreview375(decision, request.variant_id,
                                 "PREVIEW_EVALUATED_UNVERIFIED", preview)


def evaluate_baseline_preview(inputs, *, requests=()):
    """Produce all 16 rows independently for each strategy.

    Explicit requests run the existing bound ingredient path, never a full
    approved detector. Unconfigured/unsupported zones remain UNVERIFIED.
    An invalid batch scope is rejected; a malformed per-zone plan is isolated.
    Unexpected runtime errors propagate, never produce a completed report.
    """
    if type(inputs) is not BaselineResolvedInputs:
        raise TypeError("MST_375_BASELINE_INPUT_REQUIRED")
    indexed = _request_index375(requests)
    decisions = tuple(d for strategy in Strategy
                      for d in evaluate_unimplemented_zones(strategy, inputs.as_of_utc))
    rows = tuple(_row375(inputs, d, indexed.get((d.zone_id, d.strategy))) for d in decisions)
    return BaselineEnginePreview375(inputs.as_of_utc, rows)

@dataclass(frozen=True)
class D1ContextPlan383:
    lookback: int
    high_indices: tuple[int, ...]
    low_indices: tuple[int, ...]
    left_count: int
    right_count: int
    tie_policy: TiePolicy


# Source §24.4: explicit CURRENT D1 trend requirements only.
# Historical decline/uptrend, alternate bases and continuation are separate.
_D1_CONTEXT_PHASES383 = (
    ("B2", "R0", "UP"), ("B2", "R_F", "UP"),
    ("B7", "R0", "DOWN"), ("B7", "R_F", "DOWN"),
    ("S2", "R0", "DOWN"), ("S2", "R_F", "DOWN"),
    ("S3", "R0", "UP"),
)


def _current_d1_context383(inputs, plan):
    if type(plan) is not D1ContextPlan383:
        raise TypeError("MST_383_EXPLICIT_D1_CONTEXT_PLAN")
    return inspect_current_d1_context(inputs, **asdict(plan))


def _context_phase_rows383(context):
    relation = context["relation"]
    direction = {"HH_HL_GEOMETRY": "UP", "LH_LL_GEOMETRY": "DOWN"}.get(context["structure"])
    return tuple(_context_phase383(z, p, expected, relation, direction)
                 for z, p, expected in _D1_CONTEXT_PHASES383)


def _context_phase383(zone, phase, expected, relation, direction):
    observation = "CONTEXT_UNRESOLVED"
    if relation == "ALIGNED_GEOMETRY_ONLY":
        observation = "DIRECTION_ALIGNED_ONLY" if direction == expected else "OPPOSITE_DIRECTION_ONLY"
    return {"zone_id": zone, "phase": phase, "expected_direction": expected,
            "observation": observation, "phase_verified": False,
            "historical_trend_preserved": False, "action_eligible": False}


def evaluate_baseline_context_preview(inputs, *, trend_plan, requests=()):
    """Run actual engine and one shared current D1 context on identical input.

    Separate redacted contract: no detached feature, no phase promotion and
    no duplicate evidence count per zone or strategy. R_F continuity is not
    established by a same-cutoff context snapshot.
    """
    result = evaluate_baseline_preview(inputs, requests=requests).safe_phase_summary()
    context = _current_d1_context383(inputs, trend_plan)
    return _attach_context383(result, context)


def _attach_context383(result, context):
    result["schema"] = "mst.private.baseline_engine_context_preview.v0.1"
    result["shared_d1_context"] = context
    result["d1_context_phase_references"] = _context_phase_rows383(context)
    return result
