#!/usr/bin/env python3
"""MST OAuth drive.file readiness contract: synthetic-only, NO Google calls.

This module does not authenticate, exchange or log tokens, read Google Drive,
write Cache, or grant OAuth consent. Inputs are fictional configuration states.
A green result is NOT an actual GitHub OAuth login or Cloud readiness proof.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping

REPO = "ngluonghoa/MST"
REPO_ID = "1450356304"
OWNER_ID = "353049266"
MAIN = "refs/heads/main"
EVENT = "workflow_dispatch"
BOOTSTRAP_WORKFLOW = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-oauth-drivefile-bootstrap-manual.yml@refs/heads/main"
)
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
CREDENTIAL_NAMES = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
CACHE_ROOT = "MST_OAUTH_CACHE_V1"
CACHE_SUBFOLDERS = ("STAGING_ONLY", "CHUNKS", "MANIFESTS", "AUDIT")
FOLDER_MIME = "application/vnd.google-apps.folder"
FAKE_ID = re.compile(r"[A-Za-z0-9_-]{8,128}\Z")


class OAuthReadinessError(ValueError):
    """Fail closed rather than guess identity, access or Cache ownership."""


@dataclass(frozen=True)
class OAuthGate:
    """Synthetic evidence only: not an authenticated GitHub/JWT assertion."""
    repository: str
    repository_id: str
    repository_owner_id: str
    ref: str
    event_name: str
    workflow_ref: str
    oauth_scope: str
    client_id_present: bool
    client_secret_present: bool
    refresh_token_present: bool
    provider_testing_mode: bool
    service_account_present: bool = False
    allow_drive_write: bool = False
    allow_vendor_call: bool = False
    allow_cache_activation: bool = False


@dataclass(frozen=True)
class SyntheticFolders:
    """Invented app-owned folder IDs used by fake metadata-only tests."""
    root: str
    staging: str
    chunks: str
    manifests: str
    audit: str


def validate_synthetic_gate(gate: OAuthGate) -> None:
    if type(gate) is not OAuthGate:
        raise OAuthReadinessError("typed OAuth gate required")
    expected = (
        (gate.repository, REPO),
        (gate.repository_id, REPO_ID),
        (gate.repository_owner_id, OWNER_ID),
        (gate.ref, MAIN),
        (gate.event_name, EVENT),
        (gate.workflow_ref, BOOTSTRAP_WORKFLOW),
        (gate.oauth_scope, DRIVE_FILE_SCOPE),
    )
    if any(actual != required for actual, required in expected):
        raise OAuthReadinessError("wrong signed-context placeholder or OAuth scope")
    if any(type(x) is not bool for x in (
        gate.client_id_present, gate.client_secret_present,
        gate.refresh_token_present, gate.provider_testing_mode,
        gate.service_account_present, gate.allow_drive_write,
        gate.allow_vendor_call, gate.allow_cache_activation,
    )):
        raise OAuthReadinessError("all safety flags must be boolean")
    present = (
        gate.client_id_present, gate.client_secret_present,
        gate.refresh_token_present,
    )
    if not all(present):
        raise OAuthReadinessError("complete separate MST OAuth credential trio required")
    if gate.service_account_present:
        raise OAuthReadinessError("no fallback to WIF or service-account key")
    if any((gate.allow_drive_write, gate.allow_vendor_call,
            gate.allow_cache_activation)):
        raise OAuthReadinessError("staged readiness gate prohibits all side effects")
    # Testing refresh token expiry is a *risk*. It is permitted for synthetic
    # checks, but not for automatic/production use. This lab cannot verify an
    # OAuth app publishing status from an untrusted boolean.
    # 'allow_cache_activation' above is forbidden irrespective of mode.


def assert_private_app_owned_folder_tree(
    folders: SyntheticFolders,
    metadata: Mapping[str, dict],
) -> dict[str, object]:
    """Validate ONLY synthetic Drive API metadata for a dedicated app-owned tree.

    Does not inspect or confer access to the pre-existing owner-created MST
    Watchlist Google Sheet or any existing MST folder.
    """
    if type(folders) is not SyntheticFolders or not isinstance(metadata, Mapping):
        raise OAuthReadinessError("typed folders and fake metadata map required")
    targets = (
        (folders.root, CACHE_ROOT, None),
        (folders.staging, "STAGING_ONLY", folders.root),
        (folders.chunks, "CHUNKS", folders.root),
        (folders.manifests, "MANIFESTS", folders.root),
        (folders.audit, "AUDIT", folders.root),
    )
    ids = [v[0] for v in targets]
    if not all(isinstance(i, str) and FAKE_ID.fullmatch(i) for i in ids):
        raise OAuthReadinessError("invalid fake Drive IDs")
    if len(set(ids)) != len(ids):
        raise OAuthReadinessError("duplicate app-owned folder IDs")
    if set(metadata) != set(ids):
        raise OAuthReadinessError("missing or unexpected metadata target")
    for file_id, name, parent in targets:
        value = metadata[file_id]
        if type(value) is not dict:
            raise OAuthReadinessError("invalid folder metadata")
        if value.get("id") != file_id or value.get("name") != name:
            raise OAuthReadinessError("wrong folder name/ID")
        if value.get("mimeType") != FOLDER_MIME or value.get("trashed") is not False:
            raise OAuthReadinessError("wrong MIME, trashed or missing trashed")
        if value.get("appOwned") is not True:
            raise OAuthReadinessError("no assumed access to owner-created folders")
        if parent is None:
            if value.get("parents") != ["root"]:
                raise OAuthReadinessError("cache root must be app-owned My Drive root")
        elif value.get("parents") != [parent]:
            raise OAuthReadinessError("app-owned private child parent mismatch")
    receipt = {
        "schema": "mst.oauth.drivefile.synthetic.v1",
        "mode": "SYNTHETIC_NOT_AUTHENTICATED",
        "folder_count": len(targets),
        "scope": DRIVE_FILE_SCOPE,
        "no_user_created_watchlist_access_assumed": True,
        "refresh_token_lifetime_verified": False,
        "google_oauth_token_exchanged": False,
        "actual_google_drive_accessed": False,
        "google_drive_write_performed": False,
        "vendor_market_api_called": False,
        "market_ohlcv_downloaded": False,
        "real_cache_activated": False,
        "production_trading_enabled": False,
    }
    return receipt


def mock_tree() -> tuple[SyntheticFolders, dict[str, dict]]:
    folders = SyntheticFolders(
        "FAKE_MST_ROOT_0001", "FAKE_MST_STAGE_0001", "FAKE_MST_CHUNKS_0001",
        "FAKE_MST_MANIF_0001", "FAKE_MST_AUDIT_0001",
    )
    values = {}
    for file_id, name, parent in (
        (folders.root, CACHE_ROOT, "root"),
        (folders.staging, "STAGING_ONLY", folders.root),
        (folders.chunks, "CHUNKS", folders.root),
        (folders.manifests, "MANIFESTS", folders.root),
        (folders.audit, "AUDIT", folders.root),
    ):
        values[file_id] = {
            "id": file_id, "name": name, "mimeType": FOLDER_MIME,
            "parents": [parent], "trashed": False, "appOwned": True,
        }
    return folders, values


def synthetic_self_test() -> dict[str, object]:
    gate = OAuthGate(REPO, REPO_ID, OWNER_ID, MAIN, EVENT, BOOTSTRAP_WORKFLOW,
                     DRIVE_FILE_SCOPE, True, True, True, True)
    validate_synthetic_gate(gate)
    folders, metadata = mock_tree()
    return assert_private_app_owned_folder_tree(folders, metadata)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-self-test", action="store_true", required=True)
    parser.parse_args()
    # No IDs, credentials, or personally identifying Google account details.
    print(json.dumps(synthetic_self_test(), sort_keys=True))


if __name__ == "__main__":
    main()
