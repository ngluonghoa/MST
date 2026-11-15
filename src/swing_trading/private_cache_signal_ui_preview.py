"""§204 actual in-memory D1 Cache reference → 16-zone Signal gate → UI-1.0.

A single strictly scoped *unpublished private reference* snapshot goes through
the existing three-provider parser, both original-engine Strategy branches,
the locked UI-1.0 viewmodel, and static HTML renderer. This is a runnable,
non-trading integration path and deterministic HTML evidence, NOT a deployed
browser screenshot, fully qualified six-TF Cache, validated original B/S
detectors, provider license, publisher or production LIVE report.

It does not read/write Google Drive, GitHub, local files, or emit orders.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Any

from .contracts import DecisionStatus, Strategy
from .locked_ui10_binding import (
    LockedUi10DiagnosticViewModel, build_private_d1_ui10_diagnostic,
)
from .locked_ui10_renderer import render_ui10_incomplete_html
from .private_cache_source_bridge import (
    diagnose_private_d1_without_signals,
)
from .private_multitf_readiness import TF_NAMES


class PrivateCacheUiPreviewDenied(ValueError):
    """Never echo raw source rows, secrets or private file identifiers."""


@dataclass(frozen=True)
class PrivateCacheUiPreview:
    html: str
    html_sha256: str
    viewmodel: LockedUi10DiagnosticViewModel
    safe_summary: dict[str, Any]
    safe_summary_sha256: str
    eligible_for_signals: bool = False
    report_published: bool = False
    broker_orders: int = 0

    def __post_init__(self) -> None:
        if (type(self.html) is not str or len(self.html) > 100_000
                or not self.html.startswith('<!doctype html>')
                or sha256(self.html.encode("utf-8")).hexdigest()
                   != self.html_sha256
                or self.eligible_for_signals is not False
                or self.report_published is not False
                or type(self.broker_orders) is not int
                or self.broker_orders != 0
                or type(self.viewmodel) is not LockedUi10DiagnosticViewModel
                or type(self.safe_summary) is not dict
                or self.safe_summary.get("schema")
                   != "mst.cloud.private_cache_signal_ui_preview.v0.1"
                or self.safe_summary.get("publication_state") != "INCOMPLETE_REPORT"
                or self.safe_summary.get("decision") != "NO_TRADE"
                or self.safe_summary.get("viewmodel_sha256")
                   != self.viewmodel.reference_sha256
                or self.safe_summary.get("html_sha256") != self.html_sha256
                or self.safe_summary.get("verified_16_zone_rules") is not False
                or self.safe_summary.get("step08_committed") is not False
                or self.safe_summary.get("source_production_qualified") is not False
                or self.safe_summary.get("trade_orders") != 0):
            raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_AUTHORITY_OR_DIGEST_INVALID")
        coverage = self.safe_summary.get("required_tf_coverage")
        if (type(coverage) is not list or len(coverage) != 6
                or [row.get("timeframe") for row in coverage
                    if type(row) is dict] != list(TF_NAMES)
                or any(type(row) is not dict
                       or row.get("status") not in ("MISSING", "D1_REFERENCE_ONLY")
                       or row.get("qualified") is not False
                       or (row["timeframe"] == "D1") != (
                           row.get("status") == "D1_REFERENCE_ONLY")
                       for row in coverage)):
            raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_SIX_TF_COVERAGE_INVALID")
        # Revalidate the entire mutable nested viewmodel at this boundary.
        LockedUi10DiagnosticViewModel(
            self.viewmodel.data, self.viewmodel.reference_sha256,
        )
        actual_html = render_ui10_incomplete_html(self.viewmodel)
        if actual_html != self.html:
            raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_HTML_MODEL_DRIFT")
        try:
            payload = json.dumps(
                self.safe_summary, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode()
        except (TypeError, ValueError, OverflowError):
            raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_SUMMARY_INVALID") from None
        if sha256(payload).hexdigest() != self.safe_summary_sha256:
            raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_SUMMARY_DRIFT")


def render_private_d1_cache_signal_ui_preview(
    private_d1_snapshot: Any, *, as_of_utc: datetime,
    run_id: str, exchange: str,
) -> PrivateCacheUiPreview:
    """Run the existing PRIVATE SOURCE→ORIGINAL UNVERIFIED ENGINE→LOCKED UI.

    Crucially, D1 source rows do NOT become a fully qualified D1 canonical
    Candle, much less the five other required TFs. No false "no signal".
    """
    short = diagnose_private_d1_without_signals(
        private_d1_snapshot, strategy=Strategy.SHORT, as_of_utc=as_of_utc,
    )
    swing = diagnose_private_d1_without_signals(
        private_d1_snapshot, strategy=Strategy.SWING, as_of_utc=as_of_utc,
    )
    if (len(short.decisions) != 16 or len(swing.decisions) != 16
            or any(item.status is not DecisionStatus.UNVERIFIED
                   for item in (*short.decisions, *swing.decisions))):
        raise PrivateCacheUiPreviewDenied("MST_CACHE_UI_PREVIEW_SIGNAL_PROMOTION_REFUSED")
    viewmodel = build_private_d1_ui10_diagnostic(
        short, swing, run_id=run_id, exchange=exchange,
    )
    html = render_ui10_incomplete_html(viewmodel)
    digest = sha256(html.encode("utf-8")).hexdigest()
    tf_coverage = [
        {
            "timeframe": tf,
            "status": "D1_REFERENCE_ONLY" if tf == "D1" else "MISSING",
            "qualified": False,
        }
        for tf in TF_NAMES
    ]
    summary = {
        "schema": "mst.cloud.private_cache_signal_ui_preview.v0.1",
        "source_provider": short.source.provider,
        "symbol": short.source.symbol,
        "source_rows_observed": short.source.source_rows_observed,
        "as_of_utc": as_of_utc.isoformat(),
        "required_tf_coverage": tf_coverage,
        "h4_native_provider_supported": False,
        "w1_context_attested": False,
        "verified_16_zone_rules": False,
        "source_production_qualified": False,
        "step08_committed": False,
        "publication_state": "INCOMPLETE_REPORT",
        "decision": "NO_TRADE",
        "trade_orders": 0,
        "viewmodel_sha256": viewmodel.reference_sha256,
        "html_sha256": digest,
    }
    wire = json.dumps(summary, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()
    return PrivateCacheUiPreview(
        html, digest, viewmodel, summary, sha256(wire).hexdigest(),
    )
