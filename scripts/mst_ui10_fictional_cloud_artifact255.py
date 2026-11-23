#!/usr/bin/env python3
"""§255 Cloud-only LOCKED UI-1.0 review artifact, FICTIONAL INPUT ONLY.

Generates one real HTML report and a redacted receipt using the merged
private D1 -> original 16-zone engine -> locked A-I UI renderer. This file
MUST NEVER fetch vendor data, read secret environment variables, contact
Google Drive, promote a market cache, publish analysis, or place orders.

The fake provider label exists solely to exercise the validated parser shape.
No SSI endpoint, login, linked MCP source or market-rights claim is involved.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from swing_trading.private_cache_signal_ui_preview import (
    render_private_d1_cache_signal_ui_preview,
)

HTML_NAME = "MST_UI10_FICTIONAL_INCOMPLETE.html"
RECEIPT_NAME = "MST_UI10_FICTIONAL_SAFE_RECEIPT.json"
READ_ME_NAME = "READ_ME_FIRST_FICTIONAL_NO_TRADE.txt"
OUTPUT_DIR = Path("out/mst-ui10-fictional")
FAKE_SYMBOL = "ZZZ"
FAKE_PRICES = (
    "812345", "823456", "801234", "818765",
    "811111", "799999", "807777",
)


def strictly_fictional_source() -> dict:
    """Two fabricated rows; NOT provider data or an official venue calendar."""
    return {
        "schema": "mst.private_connector_d1_cache_capture.v1",
        "project": "MST",
        "provider": "SSI",
        "symbol": FAKE_SYMBOL,
        "timeframe": "D1",
        "snapshot_day": "2026-11-13",
        "source_origin": "ChatGPT_MCP_CONNECTOR_PRIVATE_DRIVE",
        "not_appowned_github_cache_publisher": True,
        "issuer_closed_bar_attested": False,
        "signal_eligible": False,
        "trade_orders": 0,
        "source_rows_observed": 2,
        "native_source_data": [
            {
                "symbol": FAKE_SYMBOL, "trading_date": "13/11/2026",
                "open": "812345", "high": "823456",
                "low": "801234", "close": "818765", "volume": "1234",
            },
            {
                "symbol": FAKE_SYMBOL, "trading_date": "12/11/2026",
                "open": "801234", "high": "811111",
                "low": "799999", "close": "807777", "volume": "1100",
            },
        ],
    }


def build_fictional_ui_artifact(output_dir: Path) -> dict:
    """Produce ONLY a static review bundle. Refuse any authoritativeness."""
    if type(output_dir) is not Path:
        raise ValueError("MST_255_EXACT_PATH_REQUIRED")
    snapshot = strictly_fictional_source()
    preview = render_private_d1_cache_signal_ui_preview(
        snapshot,
        as_of_utc=datetime(2026, 11, 14, 6, 0, tzinfo=timezone.utc),
        run_id="mst-ui10-fictional-255",
        exchange="HOSE",
    )
    html = preview.html
    summary = preview.safe_summary
    data = preview.viewmodel.data
    if (preview.eligible_for_signals is not False
        or preview.report_published is not False
        or preview.broker_orders != 0
        or summary.get("publication_state") != "INCOMPLETE_REPORT"
        or summary.get("decision") != "NO_TRADE"
        or summary.get("symbol") != FAKE_SYMBOL
        or summary.get("source_provider") != "SSI"
        or summary.get("source_rows_observed") != 2
        or summary.get("verified_16_zone_rules") is not False
        or summary.get("source_production_qualified") is not False
        or summary.get("step08_committed") is not False
        or summary.get("trade_orders") != 0
        or data.get("zone_verified_count") != 0
        or data.get("zone_evaluated_count") != 16
        or data.get("step08_atomic_commit_verified") is not False
        or len(summary.get("required_tf_coverage", [])) != 6
        or sum(x.get("status") == "D1_REFERENCE_ONLY"
               for x in summary["required_tf_coverage"]) != 1
        or any(x.get("qualified") is not False
               for x in summary["required_tf_coverage"])
        or not html.startswith('<!doctype html><html lang="vi">')
        or html.count('data-zone-id="') != 16
        or html.count('data-pipeline-step="') != 8
        or html.count('data-audit-topic="') != 8
        or html.count('data-ui-section="') != 9
        or any(price in html for price in FAKE_PRICES)
        or "INCOMPLETE_REPORT" not in html
        or "NO_TRADE" not in html):
        raise ValueError("MST_255_FAKE_REVIEW_AUTHORITY_OR_REDACTION_DENIED")
    digest = sha256(html.encode("utf-8")).hexdigest()
    if digest != preview.html_sha256:
        raise ValueError("MST_255_HTML_HASH_DRIFT")
    receipt = {
        "schema": "mst.cloud.ui10_fictional_artifact.v0.1",
        "status": "FICTIONAL_INCOMPLETE_REPORT_NO_TRADE",
        "source": "TWO_HARDCODED_FAKE_ROWS_NOT_LIVE_MCP_OR_API",
        "fake_symbol": FAKE_SYMBOL,
        "input_is_fictional": True,
        "real_provider_data_read": False,
        "cloud_secret_read": False,
        "cloud_vendor_api_requested": False,
        "google_drive_accessed": False,
        "production_cache_head_published": False,
        "original_16_zone_rules_verified": False,
        "report_step08_committed": False,
        "signals_or_trades_eligible": False,
        "report_html_sha256": digest,
        "viewmodel_sha256": preview.viewmodel.reference_sha256,
        "rendered_sections": list("ABCDEFGHI"),
        "zones_unverified": 16,
        "pipeline_steps": 8,
        "audit_topics": 8,
        "source_timeframes_qualified": 0,
        "required_tf_coverage": summary["required_tf_coverage"],
    }
    readme = (
        "MST UI-1.0 — OFFLINE CLOUD ENGINEERING REVIEW ONLY\n"
        "FICTIONAL SAMPLE. NO MARKET DATA. NOT AN INVESTMENT REPORT.\n"
        "The symbol ZZZ and every source value/time are invented.\n"
        "A hardcoded fake SSI-shaped envelope exercises the parser only.\n"
        "It did NOT call SSI, DNSE, VCBS, a connected MCP or any other API.\n"
        "The actual 16 B/S detectors are UNVERIFIED, not NO_SIGNAL.\n"
        "Step08, source rights, venue finality, highwater/CAS, OOS and live\n"
        "publication remain UNVERIFIED. NO_TRADE and no real broker order.\n"
        "Open the HTML file for frozen A-I UI layout review. Cross-check the\n"
        "HTML SHA256 with the safe receipt; do not re-label this production.\n"
    )
    # Runner starts in a clean checkout. Never silently overwrite an artifact.
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / HTML_NAME).write_bytes(html.encode("utf-8"))
    (output_dir / RECEIPT_NAME).write_text(
        json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / READ_ME_NAME).write_text(readme, encoding="utf-8")
    return receipt


def main() -> None:
    build_fictional_ui_artifact(OUTPUT_DIR)
    print("MST_255_FICTIONAL_NO_TRADE_CLOUD_UI_ARTIFACT_CREATED")


if __name__ == "__main__":
    main()
