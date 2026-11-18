#!/usr/bin/env python3
"""MST §219: bounded GitHub-OAuth census of four private app-owned Cache folders.

Manual, main-only, GET-only Google Drive metadata audit. No market API, file
content, upload, Watchlist, cache promotion, cron or trading. Do not print IDs,
paths, token errors, provider bodies or credentials in public CI logs.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

from scripts.mst_oauth_manual_drive_bootstrap import (
    CHILDREN, DRIVE_FILES, FOLDER_MIME, OWNER_ID, OWNER_REPO, REPO_ID,
    ROOT_NAME, OAuthSecrets, _list_exact_child, _new_authorized_session,
)

WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-oauth-cache-census-manual.yml@refs/heads/main"
)
CONFIRM = "RUN_READONLY_CENSUS"
MAX_PAGES = 6
PAGE_SIZE = 100
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
OAUTH_KEYS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)


class CensusDenied(ValueError):
    """Fixed public failure codes only; never embed untrusted data."""


def authorize_manual_readonly(env: Mapping[str, str]) -> OAuthSecrets:
    """GitHub context is an execution gate, not cryptographic proof elsewhere."""
    expected = {
        "GITHUB_REPOSITORY": OWNER_REPO,
        "GITHUB_REPOSITORY_ID": REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
        "MST_CACHE_CENSUS_CONFIRM": CONFIRM,
    }
    if not isinstance(env, Mapping) or any(
        env.get(k) != v for k, v in expected.items()
    ):
        raise CensusDenied("MST_219_MANUAL_MAIN_READONLY_CONTEXT_REQUIRED")
    if (env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON")
            or env.get("MST_OAUTH_MODE") == "bootstrap"):
        raise CensusDenied("MST_219_NO_BOOTSTRAP_OR_WIF_FALLBACK")
    if any(type(env.get(k)) is not str or not env[k].strip()
           for k in OAUTH_KEYS):
        raise CensusDenied("MST_219_EXISTING_OAUTH_SECRET_TRIO_REQUIRED")
    return OAuthSecrets(*(env[k] for k in OAUTH_KEYS))


def _identifier(value: Any) -> str:
    if type(value) is not str or not ID_PATTERN.fullmatch(value):
        raise CensusDenied("MST_219_PRIVATE_DRIVE_ID_INVALID")
    return value


def _get_json(session: Any, url: str, params: dict[str, Any]) -> dict:
    try:
        response = session.get(
            url, params=params, timeout=25, allow_redirects=False
        )
        if response.status_code != 200:
            raise CensusDenied("MST_219_PRIVATE_DRIVE_GET_REJECTED")
        obj = response.json()
        if type(obj) is not dict:
            raise CensusDenied("MST_219_PRIVATE_DRIVE_JSON_INVALID")
        return obj
    except CensusDenied:
        raise
    except Exception:
        raise CensusDenied("MST_219_PRIVATE_DRIVE_GET_FAILED_CLOSED") from None


def _verify_folder(
    session: Any, folder_id: str, name: str, parent: str | None
) -> None:
    info = _get_json(session, DRIVE_FILES + "/" + _identifier(folder_id), {
        "fields": "id,name,mimeType,parents,trashed,shared,"
                  "ownedByMe,isAppAuthorized",
    })
    parents = info.get("parents")
    if (info.get("id") != folder_id or info.get("name") != name
            or info.get("mimeType") != FOLDER_MIME
            or info.get("trashed") is not False
            or info.get("shared") is not False
            or info.get("ownedByMe") is not True
            or info.get("isAppAuthorized") is not True
            or type(parents) is not list or len(parents) != 1
            or type(parents[0]) is not str
            or (parent is not None and parents != [parent])):
        raise CensusDenied("MST_219_PRIVATE_APP_FOLDER_SCOPE_UNVERIFIED")


def census_app_owned_cache(session: Any) -> dict[str, Any]:
    """Never claim source integrity, manifest trust or production eligibility."""
    try:
        root = _list_exact_child(session, ROOT_NAME, None)
        if type(root) is not dict:
            raise CensusDenied("MST_219_APP_ROOT_NOT_DISCOVERED")
        root_id = _identifier(root.get("id"))
        _verify_folder(session, root_id, ROOT_NAME, None)
        folder_ids: set[str] = {root_id}
        all_file_ids: set[str] = set()
        counts: dict[str, int] = {}
        for name in CHILDREN:
            child = _list_exact_child(session, name, root_id)
            if type(child) is not dict:
                raise CensusDenied("MST_219_APP_CHILD_NOT_DISCOVERED")
            child_id = _identifier(child.get("id"))
            if child_id in folder_ids:
                raise CensusDenied("MST_219_APP_FOLDER_ID_COLLISION")
            folder_ids.add(child_id)
            _verify_folder(session, child_id, name, root_id)

            token: str | None = None
            used_tokens: set[str] = set()
            total = 0
            for _ in range(MAX_PAGES):
                params: dict[str, Any] = {
                    "q": "'" + child_id + "' in parents and trashed = false",
                    "pageSize": PAGE_SIZE,
                    "fields": "nextPageToken,incompleteSearch,files(id,mimeType,parents,trashed,"
                              "shared,ownedByMe,isAppAuthorized)",
                }
                if token is not None:
                    params["pageToken"] = token
                page = _get_json(session, DRIVE_FILES, params)
                # An omitted incompleteSearch is the API default; an explicit
                # true or malformed value cannot certify an exhaustive count.
                if page.get("incompleteSearch", False) is not False:
                    raise CensusDenied("MST_219_PRIVATE_CENSUS_INCOMPLETE_SEARCH")
                files = page.get("files")
                if type(files) is not list or len(files) > PAGE_SIZE:
                    raise CensusDenied("MST_219_PRIVATE_CENSUS_PAGE_INVALID")
                for item in files:
                    if type(item) is not dict:
                        raise CensusDenied("MST_219_PRIVATE_CENSUS_ITEM_INVALID")
                    item_id = _identifier(item.get("id"))
                    if (item_id in all_file_ids or item_id in folder_ids
                            or item.get("mimeType") == FOLDER_MIME
                            or type(item.get("mimeType")) is not str
                            or item.get("parents") != [child_id]
                            or item.get("trashed") is not False
                            or item.get("shared") is not False
                            or item.get("ownedByMe") is not True
                            or item.get("isAppAuthorized") is not True):
                        raise CensusDenied("MST_219_PRIVATE_CENSUS_ITEM_SCOPE_INVALID")
                    all_file_ids.add(item_id)
                total += len(files)
                new_token = page.get("nextPageToken")
                if new_token is None:
                    break
                if (type(new_token) is not str or not new_token
                        or len(new_token) > 1024 or new_token in used_tokens):
                    raise CensusDenied("MST_219_PRIVATE_CENSUS_PAGINATION_INVALID")
                used_tokens.add(new_token)
                token = new_token
            else:
                raise CensusDenied("MST_219_PRIVATE_CENSUS_PAGE_LIMIT_REACHED")
            counts[name] = total

        return {
            "schema": "mst.cloud.app_owned_cache_inventory.v0.1",
            "status": "MST_219_GITHUB_OAUTH_CACHE_CENSUS_PASS",
            "visibility_context": "GITHUB_ACTIONS_OAUTH_APP_ONLY",
            "verified_app_owned_folder_count": 1 + len(CHILDREN),
            "observed_counts": counts,
            "state": ("BOOTSTRAPPED_FOLDERS_EMPTY"
                      if all(n == 0 for n in counts.values())
                      else "PRIVATE_FILES_PRESENT_UNVERIFIED"),
            "census_complete": True,
            "google_drive_write_performed": False,
            "market_provider_called": False,
            "source_retention_rights_attested": False,
            "published_manifest_readback_attested": False,
            "independent_signed_highwater_attested": False,
            "production_cache_ready": False,
            "signals_and_trading_eligible": False,
        }
    except CensusDenied:
        raise
    except Exception:
        raise CensusDenied("MST_219_PRIVATE_CENSUS_FAILED_CLOSED") from None


def main() -> None:
    secrets = authorize_manual_readonly(os.environ)
    try:
        session = _new_authorized_session(secrets)
    except Exception:
        raise CensusDenied("MST_219_OAUTH_SESSION_NOT_READY") from None
    print(json.dumps(census_app_owned_cache(session), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except CensusDenied as error:
        raise SystemExit(str(error))
