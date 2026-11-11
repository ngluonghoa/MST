#!/usr/bin/env python3
"""MST OAuth Drive private folder bootstrap. DRAFT; NEVER run before approval.

Exactly one manual main-branch GitHub Actions run may create a standalone
app-owned folder tree at the user's My Drive root after an explicit GitHub
repository gate and separate user-granted OAuth drive.file consent.

There is no market API call, Watchlist access, market Cache, or trading here.
Credentials must NEVER be printed, logged, saved to artifacts or committed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
from typing import Any, Callable, Mapping

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
SCOPE = "https://www.googleapis.com/auth/drive.file"
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_NAME = "MST_OAUTH_CACHE_V1"
CHILDREN = ("STAGING_ONLY", "CHUNKS", "MANIFESTS", "AUDIT")
OWNER_REPO = "ngluonghoa/MST"
REPO_ID = "1450356304"
OWNER_ID = "353049266"
HEAD_REF = "refs/heads/main"
RUN_EVENT = "workflow_dispatch"
EXPECTED_WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-oauth-manual-drive-bootstrap.yml@refs/heads/main"
)
SECRET_NAMES = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)


class BootstrapDenied(ValueError):
    """No credentials, IDs or raw HTTP errors should be included in messages."""


@dataclass(frozen=True)
class OAuthSecrets:
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    refresh_token: str = field(repr=False)


def require_manual_main_context(env: Mapping[str, str]) -> OAuthSecrets:
    """Defense-in-depth: no schedule, PR, fork, WIF or main-mismatch fallback.

    GitHub environment strings are runtime gates, NOT signed identity proof
    outside the protected GitHub Actions execution environment.
    """
    checks = {
        "GITHUB_REPOSITORY": OWNER_REPO,
        "GITHUB_REPOSITORY_ID": REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": HEAD_REF,
        "GITHUB_EVENT_NAME": RUN_EVENT,
        "GITHUB_WORKFLOW_REF": EXPECTED_WORKFLOW_REF,
        "MST_OAUTH_BOOTSTRAP_ACCEPTED": "true",
    }
    if not isinstance(env, Mapping) or any(
        env.get(key) != value for key, value in checks.items()
    ):
        raise BootstrapDenied("MST_OAUTH_MANUAL_MAIN_EXPLICIT_OWNER_GATE_REQUIRED")
    if any(not isinstance(env.get(key), str) or not env[key].strip()
           for key in SECRET_NAMES):
        raise BootstrapDenied("MST_OAUTH_COMPLETE_PRIVATE_SECRET_TRIO_REQUIRED")
    if env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON"):
        raise BootstrapDenied("MST_OAUTH_NO_LEGACY_SERVICE_ACCOUNT_FALLBACK")
    return OAuthSecrets(*(env[key] for key in SECRET_NAMES))


def _get_response(session: Any, method: str, url: str, *,
                  params: dict[str, Any], body: dict | None = None) -> dict:
    try:
        if method == "GET":
            response = session.get(url, params=params, timeout=30)
        elif method == "POST":
            response = session.post(url, params=params, json=body, timeout=30)
        else:
            raise BootstrapDenied("UNSUPPORTED_DRIVE_METHOD")
        if response.status_code not in (200, 201):
            raise BootstrapDenied("MST_OAUTH_DRIVE_REQUEST_REJECTED")
        payload = response.json()
        if type(payload) is not dict:
            raise BootstrapDenied("MST_OAUTH_DRIVE_JSON_OBJECT_REQUIRED")
        return payload
    except BootstrapDenied:
        raise
    except Exception:
        raise BootstrapDenied("MST_OAUTH_DRIVE_REQUEST_FAILED_CLOSED") from None


def _list_exact_child(session: Any, name: str, parent: str | None) -> dict | None:
    if name not in (ROOT_NAME, *CHILDREN):
        raise BootstrapDenied("MST_OAUTH_FIXED_FOLDER_NAMES_ONLY")
    if parent is not None and not re.fullmatch(r"[A-Za-z0-9_-]{8,160}", parent):
        raise BootstrapDenied("MST_OAUTH_INVALID_PARENT_ID")
    parent_expr = "'root'" if parent is None else "'" + parent + "'"
    obj = _get_response(session, "GET", DRIVE_FILES, params={
        "q": f"{parent_expr} in parents and name = '{name}' "
             f"and mimeType = '{FOLDER_MIME}' and trashed = false",
        "pageSize": 100,
        "fields": "nextPageToken,files(id,name,mimeType,parents,trashed)",
    })
    results = obj.get("files")
    if not isinstance(results, list) or obj.get("nextPageToken") or len(results) > 1:
        raise BootstrapDenied("MST_OAUTH_AMBIGUOUS_OR_INCOMPLETE_DRIVE_LIST")
    return results[0] if results else None


def _verify_exact(session: Any, file_id: str, name: str,
                  parent: str | None) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,160}", file_id):
        raise BootstrapDenied("MST_OAUTH_INVALID_FILE_ID")
    obj = _get_response(session, "GET", DRIVE_FILES + "/" + file_id, params={
        "fields": "id,name,mimeType,parents,trashed",
    })
    if (obj.get("id") != file_id or obj.get("name") != name or
            obj.get("mimeType") != FOLDER_MIME or obj.get("trashed") is not False):
        raise BootstrapDenied("MST_OAUTH_METADATA_READBACK_DRIFT")
    parents = obj.get("parents")
    if not isinstance(parents, list):
        raise BootstrapDenied("MST_OAUTH_INCOMPLETE_PARENTS")
    if parent is None:
        # Google returns the actual My Drive root ID, NOT necessarily 'root'.
        # The list/create call is explicitly scoped to the user's My Drive root.
        if len(parents) != 1 or not isinstance(parents[0], str) or not parents[0]:
            raise BootstrapDenied("MST_OAUTH_ROOT_NOT_MYDRIVE_SINGLE_PARENT")
    elif parents != [parent]:
        raise BootstrapDenied("MST_OAUTH_CHILD_PARENT_MISMATCH")


def find_or_create_app_folder(session: Any, name: str,
                              parent: str | None) -> str:
    """Scoped OAuth drive.file folder create, bounded and rerunnable.

    Existing owner-created MST folders are NOT searched/modified.
    """
    existing = _list_exact_child(session, name, parent)
    if existing is not None:
        file_id = existing.get("id")
        if not isinstance(file_id, str):
            raise BootstrapDenied("MST_OAUTH_LIST_FILE_ID_REQUIRED")
    else:
        body: dict[str, object] = {"name": name, "mimeType": FOLDER_MIME}
        if parent is not None:
            body["parents"] = [parent]
        created = _get_response(session, "POST", DRIVE_FILES, params={
            "fields": "id,name,mimeType,parents,trashed",
        }, body=body)
        file_id = created.get("id")
        if not isinstance(file_id, str):
            raise BootstrapDenied("MST_OAUTH_CREATE_FILE_ID_REQUIRED")
    _verify_exact(session, file_id, name, parent)
    return file_id


def bootstrap_from_session(session: Any) -> dict[str, object]:
    """Called only after GitHub manual gate and OAuth authorize token flow."""
    root = find_or_create_app_folder(session, ROOT_NAME, None)
    ids = [root]
    for child in CHILDREN:
        ids.append(find_or_create_app_folder(session, child, root))
    if len(set(ids)) != len(ids):
        raise BootstrapDenied("MST_OAUTH_DUPLICATED_FOLDER_IDS")
    # No IDs in PUBLIC GitHub logs or action artifacts; discover privately
    # through the consenting owner account's Drive UI/connector as needed.
    return {
        "status": "MST_OAUTH_APP_OWNED_FOLDERS_METADATA_READBACK_PASS",
        "app_owned_folder_count": len(ids),
        "existing_watchlist_sheet_access_proven": False,
        "google_sheets_contents_read": False,
        "market_provider_called": False,
        "ohlcv_downloaded": False,
        "drive_cache_data_written": False,
        "market_cache_or_trading_activated": False,
        "oauth_refresh_token_continuity_proven": False,
    }


def _new_authorized_session(secrets: OAuthSecrets) -> Any:
    """Construct actual Google authorized session *after* manual context gate."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        creds = Credentials(
            token=None,
            refresh_token=secrets.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=secrets.client_id,
            client_secret=secrets.client_secret,
            scopes=(SCOPE,),
        )
        return AuthorizedSession(creds)
    except Exception:
        raise BootstrapDenied("MST_OAUTH_AUTH_RUNTIME_NOT_READY") from None


def main() -> None:
    # Critical: do not log either the env or OAuthSecrets repr.
    secrets = require_manual_main_context(os.environ)
    session = _new_authorized_session(secrets)
    receipt = bootstrap_from_session(session)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BootstrapDenied as exc:
        raise SystemExit(str(exc))
