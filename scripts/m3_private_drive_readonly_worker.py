"""Read ONLY owner-approved private MST D1 Docs through Google Drive OAuth.

DRAFT for future explicit main-branch/manual GitHub Actions dispatch. Never
runs on CI PR, schedule or a ChatGPT automation. Uses Google's files.get
metadata and files.export(text/plain) APIs on preselected file IDs only;
NO folders listing, POST/PATCH/DELETE, mutation, new vendor queries, trading,
or raw source data output.

Google's drive.file OAuth is app-scoped: owner Docs created by a different
OAuth app (such as a ChatGPT connector) are NOT automatically readable. Fail
closed if Google denies access; do not escalate scopes or copy data publicly.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
import os
import re
from typing import Any

from scripts.m3_private_drive_d1_refresh import (
    parse_google_doc_json, read_private_d1_document, _read_manifest,
)
from scripts.m3_source_native_ohlcv_delta import diff_native_d1_versions
from scripts.mst_oauth_manual_drive_bootstrap import (
    OAuthSecrets, _new_authorized_session,
)

_API = "https://www.googleapis.com/drive/v3/files/"
_DOC_MIME = "application/vnd.google-apps.document"
_DOC_ID = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_MAX_JSON_BYTES = 8_000_000
_MAX_DOCS = 90
_OWNER = "ngluonghoa/MST"
_REPO_ID = "1450356304"
_OWNER_ID = "353049266"
_EVENT = "workflow_dispatch"
_REF = "refs/heads/main"
_WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-m3-private-d1-readonly.yml@refs/heads/main"
)
_SECRETS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
_DOC_SECRETS = (
    "MST_M3_PRIVATE_D1_OLD_MANIFEST_ID",
    "MST_M3_PRIVATE_D1_NEW_MANIFEST_ID",
    "MST_M3_PRIVATE_D1_ALLOWED_PARENT_IDS",
)


class DriveReadonlyDenied(ValueError):
    """Always raise privacy-safe codes: never propagate HTTP body or doc IDs."""


def _id(raw: Any) -> str:
    if type(raw) is not str or not _DOC_ID.fullmatch(raw):
        raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_ID_REQUIRED")
    return raw


def require_manual_owner_env(env: Mapping[str, str]) -> tuple[OAuthSecrets, str, str, frozenset[str]]:
    checks = {
        "GITHUB_REPOSITORY": _OWNER,
        "GITHUB_REPOSITORY_ID": _REPO_ID,
        "GITHUB_REPOSITORY_OWNER_ID": _OWNER_ID,
        "GITHUB_EVENT_NAME": _EVENT,
        "GITHUB_REF": _REF,
        "GITHUB_WORKFLOW_REF": _WORKFLOW_REF,
        "MST_M3_DRIVE_READONLY_OWNER_ACCEPTED": "true",
    }
    if not isinstance(env, Mapping) or any(env.get(k) != v for k, v in checks.items()):
        raise DriveReadonlyDenied("MST_M3_OWNER_MAIN_MANUAL_GATE_REQUIRED")
    if env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON"):
        raise DriveReadonlyDenied("MST_M3_NO_LEGACY_SA_CREDENTIAL_FALLBACK")
    if any(type(env.get(k)) is not str or not env[k].strip()
           for k in (*_SECRETS, *_DOC_SECRETS)):
        raise DriveReadonlyDenied("MST_M3_COMPLETE_PRIVATE_SECRET_CONFIG_REQUIRED")
    raw_folders = env[_DOC_SECRETS[2]].split(",")
    if not 1 <= len(raw_folders) <= 8:
        raise DriveReadonlyDenied("MST_M3_BOUNDED_FOLDER_ALLOWLIST_REQUIRED")
    parents = frozenset(_id(folder.strip()) for folder in raw_folders)
    if len(parents) != len(raw_folders):
        raise DriveReadonlyDenied("MST_M3_DUPLICATE_APPROVED_FOLDER_ID")
    old_id, new_id = (_id(env[k]) for k in _DOC_SECRETS[:2])
    if old_id == new_id:
        raise DriveReadonlyDenied("MST_M3_DISTINCT_PRIVATE_MANIFESTS_REQUIRED")
    secrets = OAuthSecrets(*(env[k] for k in _SECRETS))
    return secrets, old_id, new_id, parents


def fetch_private_doc_readonly(session: Any, file_id: str,
                               approved_parents: frozenset[str]) -> dict[str, Any]:
    """Metadata-verify parent and MIME before exact-ID text export.

    Returning parsed quote rows is confined to this private process memory.
    A denied Drive access proves nothing about the user-owned Doc's existence.
    """
    _id(file_id)
    if (type(approved_parents) is not frozenset or not approved_parents or
            any(type(p) is not str or not _DOC_ID.fullmatch(p)
                for p in approved_parents)):
        raise DriveReadonlyDenied("MST_M3_APPROVED_PRIVATE_PARENT_REQUIRED")
    try:
        resp = session.get(_API + file_id, params={
            "fields": "id,mimeType,parents,trashed,capabilities(canDownload)",
        }, timeout=20)
        if resp.status_code != 200:
            raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_NOT_ACCESSIBLE_WITH_SCOPED_OAUTH")
        meta = resp.json()
        if (type(meta) is not dict or meta.get("id") != file_id
                or meta.get("mimeType") != _DOC_MIME or meta.get("trashed") is not False
                or type(meta.get("parents")) is not list
                or len(meta["parents"]) != 1
                or meta["parents"][0] not in approved_parents
                or meta.get("capabilities", {}).get("canDownload") is not True):
            raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_METADATA_SCOPE_FAILURE")
        exported = session.get(_API + file_id + "/export",
                               params={"mimeType": "text/plain"}, timeout=35)
        if exported.status_code != 200:
            raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_TEXT_EXPORT_NOT_AUTHORIZED")
        raw = exported.content
        if type(raw) is not bytes or not 0 < len(raw) <= _MAX_JSON_BYTES:
            raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_TEXT_SIZE_INVALID")
        return parse_google_doc_json(raw.decode("utf-8-sig"))
    except DriveReadonlyDenied:
        raise
    except (ValueError, UnicodeError, TypeError, AttributeError):
        raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_UNTRUSTED_JSON_OR_METADATA") from None
    except Exception:
        # Never include URL, OAuth token, Google body or source rows in logs.
        raise DriveReadonlyDenied("MST_M3_PRIVATE_DOC_HTTP_READ_FAILED_CLOSED") from None


def read_two_private_manifests(
    session: Any, *,
    prior_manifest_id: str, next_manifest_id: str,
    approved_parents: frozenset[str],
) -> dict[str, Any]:
    """Compare two private manifest versions, returning counts ONLY.

    Existing same-ID source snapshots cannot prove historical immutability.
    Changed-ID rows must retain prior keys; missing prior days are quarantined.
    This is a verified *read* of source versions, not issuer-signed proof, CAS,
    new source fetch or any form of Google Drive write.
    """
    if _id(prior_manifest_id) == _id(next_manifest_id):
        raise DriveReadonlyDenied("MST_M3_DISTINCT_PRIVATE_MANIFESTS_REQUIRED")
    earlier = fetch_private_doc_readonly(session, prior_manifest_id, approved_parents)
    later = fetch_private_doc_readonly(session, next_manifest_id, approved_parents)
    previous = _read_manifest(earlier)
    current = _read_manifest(later)
    if set(previous) != set(current) or not 1 <= len(current) <= _MAX_DOCS:
        raise DriveReadonlyDenied("MST_M3_MANIFEST_SOURCE_PARTITION_SET_DRIFT")
    ids = sorted(set(previous.values()) | set(current.values()))
    if len(ids) > 2 * _MAX_DOCS:
        raise DriveReadonlyDenied("MST_M3_EXCESSIVE_PRIVATE_DOCUMENT_READ_SCOPE")
    documents = {id: fetch_private_doc_readonly(session, id, approved_parents)
                 for id in ids}
    prev_rows = { (r["provider"],r["symbol"]):r for r in earlier["snapshots"] }
    next_rows = { (r["provider"],r["symbol"]):r for r in later["snapshots"] }
    states = {"reused_source_versions": 0, "changed_source_versions": 0,
              "quarantined_scope_or_revision": 0, "new_day_labels": 0,
              "overlapping_rows_checked": 0, "numeric_ohlcv_revisions": 0,
              "adjustment_revisions": 0, "candle_start_revisions": 0,
              "metadata_only_revisions": 0}
    for key in sorted(previous):
        old_id,new_id=previous[key],current[key]
        o=read_private_d1_document(documents[old_id], document_id=old_id)
        n=read_private_d1_document(documents[new_id], document_id=new_id)
        if ((o.endpoint,o.symbol)!=(n.endpoint,n.symbol)
            or (o.endpoint.value.split(".",1)[0],o.symbol)!=key
            or o.native.price_basis != n.native.price_basis
            or o.native.unit != n.native.unit):
            raise DriveReadonlyDenied("MST_M3_ENDPOINT_NATIVE_IDENTITY_MISMATCH")
        for ref,doc in ((prev_rows[key],o),(next_rows[key],n)):
            if (type(ref.get("persisted_rows")) is not int
                or ref["persisted_rows"] != doc.exact_rows_retained
                or ref.get("stored_in_private_folder") is not True
                or ref.get("readback_verified") is not True):
                raise DriveReadonlyDenied("MST_M3_PRIVATE_MANIFEST_DOCUMENT_COUNT_DRIFT")
        if not o.full_source_result_observed or not n.full_source_result_observed:
            states["quarantined_scope_or_revision"] += 1
            continue
        if old_id==new_id:
            # One current read cannot prove what mutable Doc contained earlier!
            states["reused_source_versions"] += 1
            continue
        try:
            diff=diff_native_d1_versions(o.native,n.native)
        except (ValueError,TypeError):
            states["quarantined_scope_or_revision"] += 1
            continue
        states["overlapping_rows_checked"] += diff["overlapping_rows"]
        states["new_day_labels"] += len(diff["added_day_labels"])
        states["numeric_ohlcv_revisions"] += len(diff["numeric_ohlcv_revisions"])
        states["adjustment_revisions"] += len(diff["adjustment_or_price_basis_revisions"])
        states["candle_start_revisions"] += len(diff["source_candle_start_timestamp_revisions"])
        states["metadata_only_revisions"] += len(diff["metadata_changes_only_or_in_addition"])
        if (diff["missing_prior_day_labels_UNVERIFIED"]
            or not diff["affected_research_day_labels"] and
                   not diff["metadata_changes_only_or_in_addition"]):
            # Changing a file ID for identical observations is not unsafe in
            # itself but must be reviewed: potential provenance/version drift.
            states["quarantined_scope_or_revision"] += 1
        else:
            states["changed_source_versions"] += 1
    return {
        "schema": "mst.m3.scoped-oauth.readonly-two-manifest-reconciliation.v1",
        "partition_count": len(previous),
        "distinct_private_docs_read": len(ids) + 2,
        **states,
        "oauth_drive_file_access_to_exact_docs_observed": True,
        "previous_mutable_docs_immutable_proof": False,
        "private_data_written": False,
        "new_vendor_data_fetched": False,
        "automatic_cache_v2_writer_authorized": False,
        "source_issuer_first_known_verified": False,
        "trade_signal_eligible": False,
    }


def main() -> None:
    # Hard gate happens before any OAuth session creation or Google request.
    secrets, old, new, parents = require_manual_owner_env(os.environ)
    session = _new_authorized_session(secrets)
    report = read_two_private_manifests(
        session, prior_manifest_id=old, next_manifest_id=new,
        approved_parents=parents,
    )
    # Counts/booleans only. Source values, file IDs, symbols, tokens and parent
    # identifiers MUST NOT appear in publicly visible GitHub Action logs.
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except DriveReadonlyDenied as exc:
        raise SystemExit(str(exc))
