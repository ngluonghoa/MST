"""§379 same-input private baseline to locked UI-1.0 section F contract.

Not a D1 reference, rendered report, issuer attestation or signal release.
The public entry point executes the engine itself; no detached summary input.
"""
from .b6_baseline_preview387 import B6EnginePreview387
from .contracts import Strategy
from .engine import evaluate_baseline_preview
from .locked_ui10_binding import SECTION_IDS, ZONE_LEGEND, PIPELINE_STEPS, AUDIT_TOPICS
from .private_multitf_readiness import BaselineResolvedInputs


def _phase_cell(row):
    return {
        "strategy": row["strategy"],
        "phases": tuple(dict(p) for p in row["phases"]),
        "status": "UNVERIFIED",
        "action_eligible": False,
    }


def _zone_row(zone, label, indexed):
    return {
        "zone_id": zone, "locked_legend": label, "status": "UNVERIFIED",
        "confirmed": False, "eligible_for_signal": False, "evidence": [],
        "phase_diagnostics": tuple(_phase_cell(indexed[(zone, s.value)]) for s in Strategy),
    }


def build_baseline_ui10_runtime(inputs, *, requests=()):
    """Private, deterministic projection; fresh evaluation of exact inputs.

    Section F diagnostics remain separate from approved zone evidence.
    Other sections are still blocked; their locked names and order remain.
    """
    if type(inputs) is not BaselineResolvedInputs:
        raise TypeError("MST_379_REQUIRE_BASELINE_INPUT")
    evaluation = evaluate_baseline_preview(inputs, requests=requests)
    return _project_runtime379(inputs, evaluation.safe_phase_summary())


def _project_runtime379(inputs, phase):
    indexed = {(r["zone_id"], r["strategy"]): r for r in phase["zones"]}
    return {
        "schema": "mst.private.baseline_ui10_runtime.v0.1",
        "ui_version": "UI-1.0", "ui_design_locked": True,
        "source_relation": "SAME_RESOLVED_INPUT_EXECUTION_ONLY",
        "as_of_utc": inputs.as_of_utc.isoformat(),
        "section_ids": SECTION_IDS,
        "zone_rows": tuple(_zone_row(z, label, indexed) for z, label in ZONE_LEGEND),
        "pipeline_steps": tuple((n, label, "BLOCKED") for n, label in enumerate(PIPELINE_STEPS, 1)),
        "audit_topics": tuple((n, label, "WARN") for n, label in enumerate(AUDIT_TOPICS, 1)),
        "timeframes": inputs.safe_readiness()["timeframes"],
        "source_released": False, "detector_parity_verified": False,
        "zone_verified_count": 0, "pipeline_verified_count": 0, "audit_verified_count": 0,
        "publication_state": "INCOMPLETE_REPORT", "decision": "NO_TRADE",
        "action_eligible": False, "report_published": False, "rendered_ui": False,
        "step08_committed": False, "trade_orders": 0,
    }


def _b6_volume391(row, rf):
    if type(row.private_preview) is B6EnginePreview387:
        return row.private_preview.safe_rf_volume_summary()["volume_state"]
    if row.private_preview is not None:
        return "NOT_SUPPORTED_BY_PREVIEW"
    return rf["ingredient_state"]


def _b6_diagnostic391(row, phases):
    r0, rc, re, rf = phases
    return {
        "zone_id": "B6", "strategy": row.decision.strategy.value,
        "r0_context_state": r0["ingredient_state"],
        "r0_input_state": r0["input_state"],
        "rf_geometry_state": rf["ingredient_state"],
        "rf_input_state": rf["input_state"],
        "rf_volume_state": _b6_volume391(row, rf),
        "trend_approved": False, "volume_approved": False,
        "risk_approved": False, "phase_verified": False, "action_eligible": False,
    }


def build_baseline_ui10_b6_diagnostics(inputs, *, requests=()):
    """Separate opt-in redacted contract; one fresh engine execution.

    Existing runtime and renderer stay unchanged. The B6 sidecar is not
    zone evidence, a second execution, or a trend/volume/risk approval.
    """
    if type(inputs) is not BaselineResolvedInputs:
        raise TypeError("MST_391_REQUIRE_BASELINE_INPUT")
    evaluation = evaluate_baseline_preview(inputs, requests=requests)
    phase = evaluation.safe_phase_summary()
    runtime = _project_runtime379(inputs, phase)
    indexed = {(r["zone_id"], r["strategy"]): r["phases"] for r in phase["zones"]}
    rows = {r.decision.strategy: r for r in evaluation.rows if r.decision.zone_id == "B6"}
    diagnostics = tuple(_b6_diagnostic391(rows[s], indexed[("B6", s.value)]) for s in Strategy)
    return {
        "schema": "mst.private.baseline_ui10_b6_diagnostics.v0.1",
        "runtime": runtime, "b6_diagnostics": diagnostics,
        "source_relation": "SAME_RESOLVED_INPUT_EXECUTION_ONLY",
        "publication_state": "INCOMPLETE_REPORT", "decision": "NO_TRADE",
        "source_released": False, "report_published": False,
        "step08_committed": False, "action_eligible": False, "trade_orders": 0,
    }
