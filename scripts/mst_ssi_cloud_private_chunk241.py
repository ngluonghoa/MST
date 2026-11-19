#!/usr/bin/env python3
"""MST §241: owner-gated SSI native OHLC -> PRIVATE UNPUBLISHED Drive CHUNK.

Explicit manual protected-main only. Never log source prices, tokens, OAuth
secrets, Google file IDs or provider error responses. Not a market publisher:
no MANIFESTS, highwater CAS, schedule, broker endpoint or trading.

GitHub vars are gate declarations only: not an independent vendor license,
first-known bar attestation, market session/calendar or corporate-action basis.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

from scripts.mst_private_chunk_readback240 import (
    CONTEXT as CHUNK_CONTEXT, ChunkDenied, _get_json,
    upload_private_unpublished_chunk, SCHEMA,
)
from scripts.mst_mfx_ssi_readonly import (
    SsiSourceDenied, _fetch_ssi_native_once, guard_ssi,
    MAX_ROWS,
)
from scripts.mst_oauth_manual_drive_bootstrap import (
    BootstrapDenied, OAuthSecrets, _new_authorized_session,
)

DRIVE = "https://www.googleapis.com/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_NAME = "MST_OAUTH_CACHE_V1"
CHILD_NAME = "CHUNKS"
NATIVE_SYMBOLS = ("FPT", "HPG", "DCM")
OWNER_SECRET_KEYS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
FIXED_REJECTIONS = {
    "MST_SSI_CLOUD_STAGE_MAIN_OWNER_GATES_REQUIRED",
    "MST_SSI_CLOUD_STAGE_MISSING_OAUTH_SECRETS",
    "MST_SSI_CLOUD_STAGE_UNKNOWN_SOURCE_SCOPE",
    "MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE",
    "MST_SSI_CLOUD_STAGE_SOURCE_ROWS_OR_STATUS_INVALID",
    "MST_SSI_CLOUD_STAGE_SOURCE_JSON_OR_TRANSPORT_FAILURE",
    "MST_SSI_CLOUD_STAGE_UNEXPECTED_FAILURE",
}


class SsiStageDenied(ValueError):
    """Static fail-closed errors; no private data in exceptions."""


def require_manual_source_stage(env: Mapping[str, str]) -> None:
    """Require all gates before reaching provider or Drive network."""
    if (not isinstance(env, Mapping)
        or any(env.get(key) != value for key, value in CHUNK_CONTEXT.items())
        or env.get("MST_SSI_READONLY_OWNER_ACCEPTED") != "true"
        or env.get("MST_SSI_SOURCE_RIGHTS_CONFIRMED") != "true"
        or env.get("MST_SOURCE_PROVIDER") != "SSI"
        or env.get("MST_SSI_SYMBOL") != env.get("MST_SOURCE_SYMBOL")
        or env.get("MST_SOURCE_SYMBOL") not in NATIVE_SYMBOLS
        or env.get("MST_OAUTH_BOOTSTRAP_ACCEPTED") == "true"
        or env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON")):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_MAIN_OWNER_GATES_REQUIRED")
    if any(type(env.get(key)) is not str or not env[key].strip()
           for key in OWNER_SECRET_KEYS):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_MISSING_OAUTH_SECRETS")
    if type(env.get("GITHUB_RUN_ID")) is not str or not re.fullmatch(
        r"[1-9][0-9]{5,19}", env["GITHUB_RUN_ID"]
    ):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_MAIN_OWNER_GATES_REQUIRED")
    try:
        augmented = dict(env)
        augmented["MST_MFX_SOURCE_MODE"] = "ssi-native-quarantine-stage"
        guard_ssi(augmented)
    except (SsiSourceDenied, ValueError, KeyError):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_UNKNOWN_SOURCE_SCOPE") from None


def _one_private_folder(
    drive: Any, *, name: str, parent: str | None,
) -> str:
    """Exact bounded census, no first-match behavior or shared-parent escape."""
    if name not in (ROOT_NAME, CHILD_NAME):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    if parent is None and name != ROOT_NAME:
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    if parent is not None and name != CHILD_NAME:
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    parent_expr = "'root'" if parent is None else "'" + parent + "'"
    response = _get_json(drive, DRIVE, params={
        "q": (parent_expr + " in parents and name = '" + name +
              "' and mimeType = '" + FOLDER_MIME + "' and trashed = false"),
        "fields": (
            "nextPageToken,incompleteSearch,"
            "files(id,name,mimeType,parents,trashed,ownedByMe,isAppAuthorized,shared)"
        ),
        "pageSize": "100",
    })
    files = response.get("files")
    if (response.get("incompleteSearch", False) is not False
        or response.get("nextPageToken") not in (None, "")
        or type(files) is not list or len(files) != 1):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    item = files[0]
    if (type(item) is not dict or item.get("name") != name
        or item.get("mimeType") != FOLDER_MIME
        or item.get("trashed") is not False
        or item.get("ownedByMe") is not True
        or item.get("isAppAuthorized") is not True
        or item.get("shared") is not False):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    ident = item.get("id")
    if type(ident) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{8,160}", ident):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    parents = item.get("parents")
    if (type(parents) is not list or len(parents) != 1
        or (parent is not None and parents != [parent])):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_PRIVATE_FOLDER_NOT_UNIQUE")
    return ident


def discover_private_chunks_folder(drive: Any) -> str:
    root = _one_private_folder(drive, name=ROOT_NAME, parent=None)
    return _one_private_folder(drive, name=CHILD_NAME, parent=root)


def source_envelope(
    report: Mapping[str, Any], captured: Any, env: Mapping[str, str],
) -> bytes:
    """No log output; only exactly seven fields in provider-source envelope."""
    tf, symbol = env["MST_SOURCE_TF"], env["MST_SOURCE_SYMBOL"]
    if (type(report) is not dict
        or report.get("provider") != "SSI_FASTCONNECT_V3_MARKET_DATA"
        or report.get("source_native_tf") != tf
        or report.get("source_ohlcv_invariants_verified") is not True
        or report.get("private_data_stored_to_drive") is not False
        or report.get("signal_eligible") is not False
        or report.get("trading_or_broker_calls") != 0
        or type(report.get("native_source_rows_observed")) is not int
        or type(captured) is not list
        or not 1 <= len(captured) <= MAX_ROWS
        or report["native_source_rows_observed"] != len(captured)):
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_SOURCE_ROWS_OR_STATUS_INVALID")
    # Original SSI adapter validates individual source rows and bounded
    # page count before returning. Do not accept arbitrary keys in captured
    # rows, nor accidentally serialize credentials or HTTP/provider metadata.
    allowed = {"symbol", "tradingDate", "open", "high", "low", "close", "volume"}
    for row in captured:
        if (type(row) is not dict or set(row) != allowed
            or row.get("symbol") != symbol):
            raise SsiStageDenied("MST_SSI_CLOUD_STAGE_SOURCE_ROWS_OR_STATUS_INVALID")
    value = {
        "schema": SCHEMA,
        "project": "MST",
        "provider": "SSI",
        "symbol": symbol,
        "native_tf": tf,
        "raw_native": captured,
        "eligible_for_signals": False,
    }
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except Exception:
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_SOURCE_JSON_OR_TRANSPORT_FAILURE") from None


def run_private_ssi_stage(
    source_session: Any, drive_session: Any, env: Mapping[str, str],
) -> dict[str, object]:
    """Never expose raw source or IDs; return only a sanitized cloud receipt."""
    require_manual_source_stage(env)
    # Folder preflight precedes broker-free provider read, and all rights
    # gates precede both: fail without fetching confidential data on bad Drive.
    try:
        folder = discover_private_chunks_folder(drive_session)
        source_env = dict(env)
        source_env["MST_MFX_SOURCE_MODE"] = "ssi-native-quarantine-stage"
        report, captured = _fetch_ssi_native_once(source_session, source_env)
        raw = source_envelope(report, captured, env)
        write_env = dict(env)
        write_env["MST_PRIVATE_CHUNKS_FOLDER_ID"] = folder
        result = upload_private_unpublished_chunk(
            drive_session, write_env, folder, raw
        )
    except (ChunkDenied, SsiSourceDenied, BootstrapDenied, SsiStageDenied):
        raise
    except Exception:
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_UNEXPECTED_FAILURE") from None
    receipt = result.public_receipt()
    receipt["source_observed_rows"] = len(captured)
    receipt["source_provider"] = "SSI_FASTCONNECT_V3_MARKET_DATA"
    receipt["source_timestamp_semantics_attested"] = False
    receipt["vendor_corporate_action_basis_attested"] = False
    return receipt


def main() -> None:
    # No dependency import or network until all fixed main/owner gates pass.
    require_manual_source_stage(os.environ)
    try:
        import requests
        import google.auth.transport.requests  # noqa: F401
        oauth = OAuthSecrets(*(os.environ[key] for key in OWNER_SECRET_KEYS))
        drive = _new_authorized_session(oauth)
        receipt = run_private_ssi_stage(requests.Session(), drive, os.environ)
    except (ChunkDenied, SsiSourceDenied, BootstrapDenied, SsiStageDenied):
        raise
    except Exception:
        raise SsiStageDenied("MST_SSI_CLOUD_STAGE_UNEXPECTED_FAILURE") from None
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ChunkDenied, SsiSourceDenied, BootstrapDenied, SsiStageDenied) as exc:
        # Known fixed error code only, never a source exception repr/response.
        raise SystemExit(str(exc)) from None
