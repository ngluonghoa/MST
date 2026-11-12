"""MST Cloud-only MFX-style app-owned Drive + native DNSE read-only ingress.

This is the first real-source integration gate, NOT a producer/writer/release.
GitHub Actions -> official DNSE market data (only if independently authorized);
GitHub-owned OAuth drive.file -> exact app-owned private folders (read-only).
Do not confuse ChatGPT MCP access with a GitHub API entitlement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import base64
import hashlib
import hmac
import json
import math
import os
import re
from typing import Any, Mapping
from urllib.parse import urlencode, quote
from uuid import uuid4

from scripts.mst_oauth_manual_drive_bootstrap import (
    OAuthSecrets, _new_authorized_session, _list_exact_child,
)

REPO = "ngluonghoa/MST"
REPO_ID = "1450356304"
OWNER_ID = "353049266"
WORKFLOW = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-mfx-style-appowned-readonly.yml@refs/heads/main"
)
MODE_DRIVE = "drive-probe"
MODE_DNSE = "dnse-d1-readonly"
DRIVE_ROOT = "MST_OAUTH_CACHE_V1"
DRIVE_CHILDREN = ("STAGING_ONLY", "CHUNKS", "MANIFESTS", "AUDIT")
DRIVE_URL = "https://www.googleapis.com/drive/v3/files/"
DNSE_ORIGIN = "https://openapi.dnse.com.vn"
DNSE_PATH = "/price/ohlc"
DNSE_VERSION = "2026-07-23"
MAX_DNSE_ROWS = 2048
MIME_FOLDER = "application/vnd.google-apps.folder"
SYMBOL_RE = re.compile(r"[A-Z]{3}\Z")
DRIVE_ID_RE = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")


class CloudGateDenied(ValueError):
    """Exception messages must contain only fixed codes; never source data."""


def guard(env: Mapping[str, str]) -> tuple[str, OAuthSecrets]:
    if not isinstance(env, Mapping):
        raise CloudGateDenied("MST_MFX_CLOUD_CONTEXT_REQUIRED")
    required = {
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_REPOSITORY_ID": REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": WORKFLOW,
        "MST_MFX_APP_OWNED_READONLY_ACCEPTED": "true",
    }
    if any(env.get(k) != v for k, v in required.items()):
        raise CloudGateDenied("MST_MFX_MANUAL_MAIN_OWNER_GATE_REQUIRED")
    mode = env.get("MST_MFX_SOURCE_MODE", MODE_DRIVE)
    if mode not in (MODE_DRIVE, MODE_DNSE):
        raise CloudGateDenied("MST_MFX_UNKNOWN_READONLY_MODE")
    if (env.get("MST_OAUTH_BOOTSTRAP_ACCEPTED") == "true"
            or env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON")):
        raise CloudGateDenied("MST_MFX_NO_BOOTSTRAP_OR_WIF_FALLBACK")
    keys = ("MST_GDRIVE_OAUTH_CLIENT_ID", "MST_GDRIVE_OAUTH_CLIENT_SECRET",
            "MST_GDRIVE_OAUTH_REFRESH_TOKEN")
    if any(type(env.get(k)) is not str or not env[k].strip() for k in keys):
        raise CloudGateDenied("MST_MFX_COMPLETE_EXISTING_OAUTH_TRIO_REQUIRED")
    if mode == MODE_DNSE:
        if (env.get("MST_DNSE_READONLY_OWNER_ACCEPTED") != "true"
                or env.get("MST_DNSE_SOURCE_RIGHTS_CONFIRMED") != "true"):
            raise CloudGateDenied("MST_MFX_DNSE_SOURCE_AND_RIGHTS_GATES_REQUIRED")
        if any(type(env.get(k)) is not str or not env[k].strip()
               for k in ("MST_DNSE_API_KEY", "MST_DNSE_API_SECRET")):
            raise CloudGateDenied("MST_MFX_DNSE_MARKETDATA_CREDENTIALS_REQUIRED")
        if not SYMBOL_RE.fullmatch(env.get("MST_DNSE_SYMBOL", "")):
            raise CloudGateDenied("MST_MFX_BOUND_STOCK_SYMBOL_REQUIRED")
        start, end = env.get("MST_DNSE_FROM_UNIX", ""), env.get("MST_DNSE_TO_UNIX", "")
        if not start.isdecimal() or not end.isdecimal():
            raise CloudGateDenied("MST_MFX_BOUNDED_EPOCH_WINDOW_REQUIRED")
        a, b = int(start), int(end)
        if a <= 0 or b <= a or b - a > 95 * 86400:
            raise CloudGateDenied("MST_MFX_BOUNDED_EPOCH_WINDOW_REQUIRED")
    return mode, OAuthSecrets(*(env[k] for k in keys))


def _metadata(session: Any, file_id: str) -> dict[str, Any]:
    if type(file_id) is not str or not DRIVE_ID_RE.fullmatch(file_id):
        raise CloudGateDenied("MST_MFX_DRIVE_IDENTIFIER_INVALID")
    try:
        response = session.get(DRIVE_URL + file_id, params={
            "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,isAppAuthorized",
        }, timeout=25)
        if response.status_code != 200:
            raise CloudGateDenied("MST_MFX_PRIVATE_DRIVE_FILE_NOT_ACCESSIBLE")
        info = response.json()
        if type(info) is not dict:
            raise CloudGateDenied("MST_MFX_DRIVE_METADATA_INVALID")
        return info
    except CloudGateDenied:
        raise
    except Exception:
        raise CloudGateDenied("MST_MFX_PRIVATE_DRIVE_METADATA_FAILURE") from None


def inspect_app_owned_drive(session: Any) -> dict[str, Any]:
    """Read exact known OAuth app folders; never create, upload or list prices."""
    try:
        root = _list_exact_child(session, DRIVE_ROOT, None)
    except Exception:
        raise CloudGateDenied("MST_MFX_APP_ROOT_LOOKUP_FAILED") from None
    if root is None:
        raise CloudGateDenied("MST_MFX_APP_ROOT_MISSING_BOOTSTRAP_SEPARATELY")
    root_id = root.get("id")
    try:
        all_ids = [root_id]
        for name in DRIVE_CHILDREN:
            child = _list_exact_child(session, name, root_id)
            if child is None:
                raise CloudGateDenied("MST_MFX_APP_CHILD_FOLDER_MISSING")
            all_ids.append(child.get("id"))
        if len(set(all_ids)) != len(all_ids):
            raise CloudGateDenied("MST_MFX_APP_FOLDER_ID_COLLISION")
        for index, file_id in enumerate(all_ids):
            info = _metadata(session, file_id)
            expected_name = DRIVE_ROOT if index == 0 else DRIVE_CHILDREN[index-1]
            if (info.get("id") != file_id or info.get("name") != expected_name
                    or info.get("mimeType") != MIME_FOLDER
                    or info.get("trashed") is not False
                    or info.get("shared") is not False
                    or info.get("ownedByMe") is not True
                    or info.get("isAppAuthorized") is not True
                    or type(info.get("parents")) is not list
                    or len(info["parents"]) != 1
                    or (index > 0 and info["parents"][0] != root_id)):
                raise CloudGateDenied("MST_MFX_APP_FOLDER_PRIVATE_SCOPE_FAILURE")
        return {
            "app_owned_folder_count": len(all_ids),
            "exact_app_owned_private_scope_verified": True,
            "drive_writes": 0,
        }
    except CloudGateDenied:
        raise
    except Exception:
        raise CloudGateDenied("MST_MFX_APP_OWNED_FOLDER_PROBE_FAILED") from None


def build_dnse_request(
    symbol: str, from_unix: int, to_unix: int,
    api_key: str, api_secret: str, *, date_header: str, nonce: str,
) -> tuple[str, dict[str, str]]:
    """Construct DNSE documented HMAC-SHA256 market-data-only GET.

    Signing the exact path and canonical URL query (no trading token/OTP).
    A real authenticated read still requires vendor-issued credentials/rights.
    """
    if (not SYMBOL_RE.fullmatch(symbol) or not api_key or not api_secret
            or not re.fullmatch(r"[0-9a-f]{32}", nonce)
            or from_unix <= 0 or to_unix <= from_unix
            or to_unix-from_unix > 95*86400):
        raise CloudGateDenied("MST_MFX_INVALID_DNSE_REQUEST")
    q = urlencode({"symbol":symbol,"type":"STOCK","resolution":"1D",
                   "from":from_unix,"to":to_unix})
    target = DNSE_PATH + "?" + q
    signing = f"(request-target): get {target}\ndate: {date_header}\nnonce: {nonce}"
    raw = hmac.new(api_secret.encode("utf-8"), signing.encode("utf-8"),
                   hashlib.sha256).digest()
    signature = quote(base64.b64encode(raw).decode("ascii"), safe="")
    header = (
        f'Signature keyId="{api_key}",algorithm="hmac-sha256",'
        f'headers="(request-target) date",signature="{signature}",nonce="{nonce}"'
    )
    return DNSE_ORIGIN+target, {
        "X-API-Key":api_key,
        "X-Signature":header,
        "Date":date_header,
        "version":DNSE_VERSION,
        "Accept":"application/json",
    }


def validate_dnse_native(payload: Any, from_unix: int, to_unix: int) -> dict[str, Any]:
    """Check six native arrays without logging values or claiming closed candles."""
    if type(payload) is not dict:
        raise CloudGateDenied("MST_MFX_DNSE_NATIVE_OBJECT_REQUIRED")
    names = ("t","o","h","l","c","v")
    if any(type(payload.get(k)) is not list for k in names):
        raise CloudGateDenied("MST_MFX_DNSE_NATIVE_ARRAYS_REQUIRED")
    count = len(payload["t"])
    if not 1 <= count <= MAX_DNSE_ROWS or any(len(payload[k]) != count for k in names):
        raise CloudGateDenied("MST_MFX_DNSE_NATIVE_ARRAY_LENGTH_MISMATCH")
    if type(payload.get("nextTime")) is not int or payload["nextTime"] != 0:
        raise CloudGateDenied("MST_MFX_DNSE_INCOMPLETE_PAGE_NO_ACCEPTANCE")
    last = 0
    for i in range(count):
        t = payload["t"][i]
        if type(t) is not int or not from_unix <= t <= to_unix or t <= last:
            raise CloudGateDenied("MST_MFX_DNSE_NATIVE_TIMESTAMP_MISMATCH")
        last = t
        nums = [payload[k][i] for k in ("o","h","l","c")]
        if any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0
               for v in nums):
            raise CloudGateDenied("MST_MFX_DNSE_NATIVE_PRICE_INVALID")
        o,h,l,c = nums
        v = payload["v"][i]
        if h < max(o,c,l) or l > min(o,c) or type(v) is not int or v < 0:
            raise CloudGateDenied("MST_MFX_DNSE_NATIVE_OHLCV_INVALID")
    return {
        "observed_native_d1_rows": count,
        "native_ohlcv_shape_verified": True,
        "native_source_close_issuer_attested": False,
        "independent_source_first_known_verified": False,
        "source_storage_and_retain_rights_independently_audited": False,
        "market_data_written_to_drive": False,
        "trade_signal_eligible": False,
    }


def read_dnse_once(session: Any, env: Mapping[str,str]) -> dict[str, Any]:
    start, end = int(env["MST_DNSE_FROM_UNIX"]), int(env["MST_DNSE_TO_UNIX"])
    dt = format_datetime(datetime.now(timezone.utc), usegmt=False)
    url, headers = build_dnse_request(
        env["MST_DNSE_SYMBOL"], start, end,
        env["MST_DNSE_API_KEY"], env["MST_DNSE_API_SECRET"],
        date_header=dt, nonce=uuid4().hex,
    )
    try:
        response = session.get(url, headers=headers, timeout=25,
                               allow_redirects=False)
        if response.status_code != 200:
            raise CloudGateDenied("MST_MFX_DNSE_MARKETDATA_HTTP_DENIED")
        if len(response.content) > 1_500_000:
            raise CloudGateDenied("MST_MFX_DNSE_BOUNDED_RESPONSE_REQUIRED")
        payload = response.json()
    except CloudGateDenied:
        raise
    except Exception:
        raise CloudGateDenied("MST_MFX_DNSE_PRIVATE_REQUEST_FAILURE") from None
    return validate_dnse_native(payload, start, end)


def main() -> None:
    mode, secrets = guard(os.environ)
    session = _new_authorized_session(secrets)
    observed = inspect_app_owned_drive(session)
    receipt: dict[str, Any] = {
        "status": "MST_MFX_STYLE_APP_OWNED_READONLY_PREFLIGHT",
        "drive": observed,
        "provider": None,
        "read_only": True,
        "cloud_cache_publisher_ready": False,
        "independent_atomic_cas_ready": False,
        "automatic_scheduling_enabled_by_this_workflow": False,
        "trade_orders": 0,
    }
    if mode == MODE_DNSE:
        import requests
        receipt["provider"] = {
            "name": "DNSE_OFFICIAL_OPENAPI_READ_ONLY",
            **read_dnse_once(requests.Session(), os.environ),
        }
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except CloudGateDenied as exc:
        raise SystemExit(str(exc))
