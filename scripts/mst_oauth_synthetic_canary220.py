#!/usr/bin/env python3
"""MST §220: single-use synthetic-only OAuth Drive STAGING_ONLY write/readback.

Protected-main, manual-only workflow with explicit consent. No market APIs,
OHLCV, licensed source data, real Cache promotion, cron, or orders.
All failures have static codes without exception text, private IDs or tokens.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping

from scripts.mst_oauth_manual_drive_bootstrap import (
    DRIVE_FILES, OWNER_ID, OWNER_REPO, REPO_ID, ROOT_NAME, FOLDER_MIME,
    OAuthSecrets, _list_exact_child, _new_authorized_session,
)
from scripts.mst_oauth_cache_census219 import census_app_owned_cache

WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-oauth-synthetic-canary-manual.yml@refs/heads/main"
)
CONFIRM = "WRITE_SYNTHETIC_STAGING_ONLY"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
STAGING = "STAGING_ONLY"
CANARY_PREFIX = "MST_SYNTHETIC_CANARY_"
ID_RE = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
RUN_RE = re.compile(r"[1-9][0-9]{5,19}\Z")
OAUTH_KEYS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
MAX_MEDIA_BYTES = 2048


class CanaryDenied(ValueError):
    """Only fixed codes; never include credentials, Drive IDs or response text."""


def authorize_manual_synthetic_write(env: Mapping[str, str]) -> tuple[OAuthSecrets, str]:
    if not isinstance(env, Mapping):
        raise CanaryDenied("MST_220_OWNER_CONTEXT_REQUIRED")
    expected = {
        "GITHUB_REPOSITORY": OWNER_REPO,
        "GITHUB_REPOSITORY_ID": REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
        "MST_CANARY_CONFIRM": CONFIRM,
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if any(env.get(key) != value for key, value in expected.items()):
        raise CanaryDenied("MST_220_MAIN_FIRST_ATTEMPT_OWNER_CONSENT_REQUIRED")
    run_id = env.get("GITHUB_RUN_ID")
    if type(run_id) is not str or not RUN_RE.fullmatch(run_id):
        raise CanaryDenied("MST_220_RUN_ID_UNTRUSTED")
    if env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON") or env.get("MST_OAUTH_MODE") == "bootstrap":
        raise CanaryDenied("MST_220_NO_LEGACY_OR_BOOTSTRAP_FALLBACK")
    if any(type(env.get(k)) is not str or not env[k].strip() for k in OAUTH_KEYS):
        raise CanaryDenied("MST_220_EXISTING_OAUTH_TRIO_REQUIRED")
    return OAuthSecrets(*(env[k] for k in OAUTH_KEYS)), run_id


def _id(value: Any) -> str:
    if type(value) is not str or not ID_RE.fullmatch(value):
        raise CanaryDenied("MST_220_PRIVATE_FILE_ID_INVALID")
    return value


def _json_get(session: Any, url: str, *, params: dict[str, Any]) -> dict:
    try:
        response = session.get(url, params=params, timeout=25, allow_redirects=False)
        if response.status_code != 200:
            raise CanaryDenied("MST_220_DRIVE_METADATA_HTTP_REJECTED")
        data = response.json()
        if type(data) is not dict:
            raise CanaryDenied("MST_220_DRIVE_METADATA_JSON_INVALID")
        return data
    except CanaryDenied:
        raise
    except Exception:
        raise CanaryDenied("MST_220_DRIVE_METADATA_GET_FAILED_CLOSED") from None


def _exact_named_files(session: Any, folder_id: str, filename: str) -> list[dict]:
    # Both the parent and file name are generated internally from a bounded
    # GitHub run ID. No user-provided query/identifier is accepted.
    files = _json_get(session, DRIVE_FILES, params={
        "q": "'" + _id(folder_id) + "' in parents and name = '" + filename
             + "' and trashed = false",
        "pageSize": 100,
        "fields": "nextPageToken,files(id,name,mimeType,parents,trashed)",
    })
    items = files.get("files")
    if (type(items) is not list or len(items) > 1
            or files.get("nextPageToken") is not None):
        raise CanaryDenied("MST_220_CANARY_DUPLICATE_OR_INCOMPLETE_CENSUS")
    for item in items:
        if (type(item) is not dict or item.get("name") != filename
                or item.get("parents") != [folder_id]
                or item.get("mimeType") != "application/json"
                or item.get("trashed") is not False):
            raise CanaryDenied("MST_220_CANARY_SCOPE_DRIFT")
        _id(item.get("id"))
    return items


def _verify_file_metadata(session: Any, file_id: str, name: str,
                          folder_id: str, expected_size: int) -> None:
    data = _json_get(session, DRIVE_FILES + "/" + _id(file_id), params={
        "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,"
                  "isAppAuthorized,size,appProperties",
    })
    props = data.get("appProperties")
    if (data.get("id") != file_id or data.get("name") != name
            or data.get("mimeType") != "application/json"
            or data.get("parents") != [folder_id]
            or data.get("trashed") is not False
            or data.get("shared") is not False
            or data.get("ownedByMe") is not True
            or data.get("isAppAuthorized") is not True
            or type(data.get("size")) is not str
            or data["size"] != str(expected_size)
            or type(props) is not dict
            or props.get("synthetic_only") != "true"):
        raise CanaryDenied("MST_220_SYNTHETIC_METADATA_READBACK_MISMATCH")


def _upload_once(session: Any, folder_id: str, name: str,
                 payload: bytes) -> str:
    metadata = {
        "name": name,
        "mimeType": "application/json",
        "parents": [_id(folder_id)],
        "appProperties": {"synthetic_only": "true"},
    }
    boundary = "MST_220_SYNTHETIC_BOUNDARY"
    body = (
        ("--" + boundary + "\r\n"
         "Content-Type: application/json; charset=UTF-8\r\n\r\n"
         + json.dumps(metadata, sort_keys=True, separators=(",", ":"))
         + "\r\n--" + boundary + "\r\n"
         "Content-Type: application/json\r\n\r\n").encode("utf-8")
        + payload
        + ("\r\n--" + boundary + "--\r\n").encode("ascii")
    )
    try:
        response = session.post(
            DRIVE_UPLOAD,
            params={"uploadType": "multipart", "fields": "id"},
            data=body,
            headers={"Content-Type": "multipart/related; boundary=" + boundary},
            timeout=25,
            allow_redirects=False,
        )
        if response.status_code not in (200, 201):
            raise CanaryDenied("MST_220_SYNTHETIC_UPLOAD_HTTP_REJECTED")
        created = response.json()
        if type(created) is not dict:
            raise CanaryDenied("MST_220_SYNTHETIC_UPLOAD_RESPONSE_INVALID")
        return _id(created.get("id"))
    except CanaryDenied:
        raise
    except Exception:
        raise CanaryDenied("MST_220_SYNTHETIC_UPLOAD_FAILED_CLOSED") from None


def synthetic_staging_canary(session: Any, run_id: str) -> dict[str, Any]:
    """Exactly one append-only fake JSON upload to private STAGING_ONLY."""
    if type(run_id) is not str or not RUN_RE.fullmatch(run_id):
        raise CanaryDenied("MST_220_RUN_ID_UNTRUSTED")
    # Existing §219 census must pass before writing. Does not promote Cache.
    audit = census_app_owned_cache(session)
    if not audit["census_complete"] or audit["production_cache_ready"] is not False:
        raise CanaryDenied("MST_220_PREWRITE_CENSUS_NOT_SAFE")
    try:
        root = _list_exact_child(session, ROOT_NAME, None)
        if type(root) is not dict:
            raise CanaryDenied("MST_220_APP_ROOT_MISSING")
        folder = _list_exact_child(session, STAGING, _id(root.get("id")))
        if type(folder) is not dict:
            raise CanaryDenied("MST_220_STAGING_FOLDER_MISSING")
        staging_id = _id(folder.get("id"))
    except CanaryDenied:
        raise
    except Exception:
        raise CanaryDenied("MST_220_APP_FOLDER_LOOKUP_FAILED_CLOSED") from None
    name = CANARY_PREFIX + run_id + "_1.json"
    if _exact_named_files(session, staging_id, name):
        raise CanaryDenied("MST_220_CANARY_ALREADY_EXISTS_NO_OVERWRITE")

    payload = json.dumps({
        "schema": "mst.cloud.synthetic_staging_probe.v0.1",
        "run_id": run_id,
        "sentinel": "MST_SYNTHETIC_ONLY_NO_MARKET_DATA",
        "eligible_for_signals": False,
        "market_data": None,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not 0 < len(payload) <= MAX_MEDIA_BYTES:
        raise CanaryDenied("MST_220_SYNTHETIC_PAYLOAD_INVALID")
    expected_sha = hashlib.sha256(payload).hexdigest()

    file_id = _upload_once(session, staging_id, name, payload)
    _verify_file_metadata(session, file_id, name, staging_id, len(payload))
    try:
        media = session.get(
            DRIVE_FILES + "/" + file_id,
            params={"alt": "media"}, timeout=25, allow_redirects=False,
        )
        if (media.status_code != 200 or type(media.content) is not bytes
                or not 0 < len(media.content) <= MAX_MEDIA_BYTES
                or hashlib.sha256(media.content).hexdigest() != expected_sha):
            raise CanaryDenied("MST_220_SYNTHETIC_MEDIA_SHA256_MISMATCH")
    except CanaryDenied:
        raise
    except Exception:
        raise CanaryDenied("MST_220_SYNTHETIC_MEDIA_READBACK_FAILED_CLOSED") from None

    matches = _exact_named_files(session, staging_id, name)
    if len(matches) != 1 or matches[0].get("id") != file_id:
        raise CanaryDenied("MST_220_CANARY_POSTWRITE_LIST_DRIFT")
    return {
        "status": "MST_220_SYNTHETIC_STAGING_WRITE_SHA256_READBACK_PASS",
        "schema": "mst.cloud.synthetic_drive_canary_receipt.v0.1",
        "private_staging_file_written": True,
        "app_owned_folder_census_passed_before_write": True,
        "bytes_verified": len(payload),
        "readback_sha256": expected_sha,
        "synthetic_only": True,
        "stock_provider_called": False,
        "market_cache_promoted": False,
        "manifest_published": False,
        "independent_signed_highwater_attested": False,
        "production_cache_ready": False,
        "signals_and_trading_eligible": False,
    }


def main() -> None:
    secrets, run_id = authorize_manual_synthetic_write(os.environ)
    try:
        session = _new_authorized_session(secrets)
    except Exception:
        raise CanaryDenied("MST_220_OAUTH_SESSION_NOT_READY") from None
    print(json.dumps(synthetic_staging_canary(session, run_id), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except CanaryDenied as error:
        raise SystemExit(str(error))
