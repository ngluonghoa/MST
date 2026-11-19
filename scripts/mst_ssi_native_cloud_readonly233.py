#!/usr/bin/env python3
"""MST §233: GitHub main-only manual SSI FastConnect marketdata read-only probe.

This is not a cache writer or source attestation. Never print market bars,
bearer tokens, credentials, provider HTTP error bodies or traceback text.
"""
from __future__ import annotations

import json
import os
from typing import Any, Mapping


from scripts.mst_mfx_ssi_readonly import (
    SsiSourceDenied, guard_ssi, read_ssi_native_once, MAX_PAGES, MAX_ROWS,
)
from scripts.mst_mfx_native_timeframes import provider_resolution


WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-ssi-native-readonly-manual.yml@refs/heads/main"
)
CONFIRM = "READ_SSI_ONLY"
REQUIRED_CONTEXT = {
    "GITHUB_REPOSITORY": "ngluonghoa/MST",
    "GITHUB_REPOSITORY_ID": "1450356304",
    "GITHUB_REPOSITORY_OWNER_ID": "353049266",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
    "GITHUB_RUN_ATTEMPT": "1",
    "MST_SSI_PROBE_CONFIRM": CONFIRM,
}


class SsiCloudProbeDenied(ValueError):
    """Only fixed safe codes; no untrusted data or provider exception text."""


def require_manual_owner_readonly(env: Mapping[str, str]) -> None:
    if (not isinstance(env, Mapping)
            or any(env.get(k) != v for k, v in REQUIRED_CONTEXT.items())):
        raise SsiCloudProbeDenied("MST_233_MAIN_FIRST_ATTEMPT_OWNER_GATE_REQUIRED")
    if env.get("MST_MFX_SOURCE_MODE") != "ssi-native-readonly":
        raise SsiCloudProbeDenied("MST_233_SSI_READONLY_MODE_REQUIRED")
    try:
        guard_ssi(env)
    except SsiSourceDenied:
        raise SsiCloudProbeDenied("MST_233_SSI_CREDENTIALS_RIGHTS_OR_WINDOW_DENIED") from None


def _bounded_receipt(report: Any, env: Mapping[str, str]) -> dict[str, object]:
    """Deny unknown report shape; output only trusted authored fields."""
    if type(report) is not dict:
        raise SsiCloudProbeDenied("MST_233_INVALID_READONLY_SOURCE_REPORT")
    tf = env["MST_SOURCE_TF"]
    expected_resolution = provider_resolution("SSI", tf)
    row_count = report.get("native_source_rows_observed")
    pages = report.get("source_pages_verified")
    if (report.get("provider") != "SSI_FASTCONNECT_V3_MARKET_DATA"
            or report.get("source_native_tf") != tf
            or report.get("provider_resolution") != expected_resolution
            or type(row_count) is not int or not 1 <= row_count <= MAX_ROWS
            or type(pages) is not int or not 1 <= pages <= MAX_PAGES
            or report.get("source_ohlcv_invariants_verified") is not True
            or report.get("private_data_stored_to_drive") is not False
            or report.get("signal_eligible") is not False
            or report.get("trade_signal_eligible") is not False
            or report.get("trading_or_broker_calls") != 0
            or report.get("source_closed_bar_attestation_proven") is not False
            or report.get("provider_marketdata_rights_verified") is not False):
        raise SsiCloudProbeDenied("MST_233_INVALID_READONLY_SOURCE_REPORT")
    return {
        "schema": "mst.cloud.ssi_native_readonly_receipt.v0.1",
        "status": "MST_233_SSI_CLOUD_NATIVE_READONLY_PROBE_PASS",
        "source": "SSI_FASTCONNECT_V3_MARKET_DATA",
        "timeframe": tf,
        "source_rows_observed": row_count,
        "source_pages_verified": pages,
        "source_ohlcv_invariants_verified": True,
        "source_rights_independently_attested": False,
        "closed_candle_first_known_attested": False,
        "vendor_corporate_action_basis_attested": False,
        "data_written_to_drive": False,
        "market_cache_promoted": False,
        "signals_and_trading_eligible": False,
    }


def run_probe(session: Any, env: Mapping[str, str]) -> dict[str, object]:
    require_manual_owner_readonly(env)
    try:
        report = read_ssi_native_once(session, env)
    except SsiSourceDenied:
        raise SsiCloudProbeDenied("MST_233_SSI_SOURCE_READ_FAILED_CLOSED") from None
    except Exception:
        raise SsiCloudProbeDenied("MST_233_SSI_TRANSPORT_FAILED_CLOSED") from None
    return _bounded_receipt(report, env)


def main() -> None:
    # Keep offline unittest import path free of runtime-only HTTPS packages.
    # The protected GitHub workflow installs the pinned requests dependency.
    try:
        import requests
    except Exception:
        raise SsiCloudProbeDenied("MST_233_HTTPS_DEPENDENCY_UNAVAILABLE") from None
    receipt = run_probe(requests.Session(), os.environ)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except SsiCloudProbeDenied as exc:
        raise SystemExit(str(exc)) from None
