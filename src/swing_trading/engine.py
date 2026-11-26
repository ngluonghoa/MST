"""Fail-closed signal engine plus §375 opt-in baseline preview dispatcher.

The existing legacy API stays available and all actual SignalDecision values
remain UNVERIFIED. The new path is private, deterministic and does not call
providers, cache, UI publisher, broker, or an approved detector.
"""
from dataclasses import dataclass
from datetime import datetime

from .contracts import (
    DecisionStatus, Strategy, SignalDecision, ZONE_IDS, evaluate_unimplemented_zones,
)
from .private_multitf_readiness import BaselineResolvedInputs
from .b2s2_swing_evidence215 import B2S2PreviewPlan371, inspect_b2s2_baseline_preview
from .b5_formula_geometry import (
    B5RetestPlan372, B5RFPlan373, B5RFVolumePlan373, inspect_b5_baseline_confirmation,
)
from .s7_retest_evidence import S7OriginPlan374, S7MicroPlan374, inspect_s7_baseline_preview
from .zone_manifest_v03 import MANIFESTS

PREVIEW_ZONES = ("B2", "B5", "S2", "S7")


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
class BaselinePreviewRequest375:
    zone_id: str
    strategy: Strategy
    variant_id: str
    plan: B2S2PreviewPlan371 | B5EnginePlan375 | S7EnginePlan375


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
            } for r in self.rows],
            "publication_state": self.publication_state, "decision": self.decision,
            "source_released": False, "detector_parity_verified": False, "trade_orders": 0,
        }


def _request_index375(requests):
    if type(requests) is not tuple or len(requests) > 8:
        raise ValueError("MST_375_BOUNDED_REQUEST_TUPLE")
    indexed = {}
    for request in requests:
        if (type(request) is not BaselinePreviewRequest375
                or type(request.zone_id) is not str or request.zone_id not in PREVIEW_ZONES
                or type(request.strategy) is not Strategy):
            raise ValueError("MST_375_UNSUPPORTED_REQUEST")
        key = (request.zone_id, request.strategy)
        if key in indexed:
            raise ValueError("MST_375_DUPLICATE_ZONE_STRATEGY")
        indexed[key] = request
    return indexed


def _dispatch375(inputs, request):
    zone, strategy, variant, plan = (
        request.zone_id, request.strategy, request.variant_id, request.plan)
    if type(variant) is not str or variant not in MANIFESTS[zone].variants:
        raise ValueError("MST_375_VARIANT_INVALID")
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
