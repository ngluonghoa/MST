"""MST DNSE native intraday append-only source continuity (UNPUBLISHED only).

Reads an app-owned, private, pre-existing candidate from Cloud Drive. This is
not a trusted publisher/head, a bar-close attestation, or a signal source.
No local persistence, no network without the exact manual-owner guard.
"""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Any, Mapping

NATIVE_TFS = ("M5", "M15", "M30", "H1")
MAX_PAGES = 8
PAGE_SIZE = 100
MAX_PRIOR_BYTES = 1_500_000
NATIVE_NAME = re.compile(
    r"MST_UNPUBLISHED_DNSE_NATIVE_(M5|M15|M30|H1)_([1-9][0-9]{5,19})_1\.json\Z"
)
D1_NAME = re.compile(
    r"MST_UNPUBLISHED_DNSE_(?:D1|NATIVE_D1)_[1-9][0-9]{5,19}_1\.json\Z"
)


def _cloud():
    # Late import preserves the existing manual workflow's dependency boundary.
    from scripts import mst_mfx_style_appowned_pipeline as cloud
    return cloud


def _guard(env: Mapping[str, str], parent: str) -> str:
    cloud = _cloud()
    mode, _ = cloud.guard(env)
    tf = env.get("MST_SOURCE_TF", "D1")
    if mode != cloud.MODE_STAGE_NATIVE or tf not in NATIVE_TFS:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_NATIVE_STAGE_ONLY")
    if type(parent) is not str or not cloud.DRIVE_ID_RE.fullmatch(parent):
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_PARENT_INVALID")
    return tf


def discover_native_predecessor(
    session: Any, env: Mapping[str, str], parent: str,
) -> str | None:
    """Return unique latest older app-owned native TF candidate, not a head.

    An exhaustive empty census is the only way a true first capture is allowed.
    Unknown names, incomplete scans, duplicates, unlabeled matching TF objects
    and self/future run IDs fail before any new upload.
    """
    cloud = _cloud()
    tf = _guard(env, parent)
    run_id = env.get("GITHUB_RUN_ID", "")
    if type(run_id) is not str or not re.fullmatch(r"[1-9][0-9]{5,19}", run_id):
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_RUN_INVALID")
    symbol = env["MST_DNSE_SYMBOL"]
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    tokens: set[str] = set()
    page_token = None
    matching: list[tuple[int, str]] = []
    completed = False
    for _ in range(MAX_PAGES):
        params: dict[str, Any] = {
            "q": ("'" + parent + "' in parents and "
                  "name contains 'MST_UNPUBLISHED_DNSE_' and trashed = false"),
            "fields": ("nextPageToken,incompleteSearch,"
                       "files(id,name,mimeType,parents,trashed,appProperties)"),
            "pageSize": PAGE_SIZE,
        }
        if page_token is not None:
            params["pageToken"] = page_token
        try:
            response = session.get(
                "https://www.googleapis.com/drive/v3/files", params=params,
                timeout=25, allow_redirects=False,
            )
            if response.status_code != 200:
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_CENSUS_HTTP_DENIED")
            data = response.json()
        except cloud.CloudGateDenied:
            raise
        except Exception:
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_CENSUS_TRANSPORT_FAILED") from None
        if (type(data) is not dict or type(data.get("files")) is not list
                or len(data["files"]) > PAGE_SIZE
                or data.get("incompleteSearch") is True):
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_CENSUS_INCOMPLETE_OR_INVALID")
        for record in data["files"]:
            if type(record) is not dict:
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_RECORD_INVALID")
            name, ident = record.get("name"), record.get("id")
            if (type(name) is not str or not name.startswith("MST_UNPUBLISHED_DNSE_")
                    or type(ident) is not str or not cloud.DRIVE_ID_RE.fullmatch(ident)
                    or record.get("parents") != [parent]
                    or record.get("mimeType") != "application/json"
                    or record.get("trashed") is not False):
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_SCOPE_DRIFT")
            if ident in seen_ids or name in seen_names:
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_DUPLICATE_CENSUS")
            seen_ids.add(ident)
            seen_names.add(name)
            hit = NATIVE_NAME.fullmatch(name)
            if hit is None:
                if D1_NAME.fullmatch(name) is None:
                    raise cloud.CloudGateDenied("MST_DNSE_INTRA_UNKNOWN_CANDIDATE")
                continue
            candidate_tf, candidate_run = hit.groups()
            if candidate_tf != tf:
                continue
            props = record.get("appProperties")
            if (type(props) is not dict
                    or props.get("mst_unpublished") != "true"
                    or props.get("source_native_tf") != tf
                    or props.get("source_run_id") != candidate_run
                    or props.get("source_symbol") not in ("FPT", "DCM", "HPG")
                    or type(props.get("source_sha256")) is not str
                    or not re.fullmatch(r"[0-9a-f]{64}", props["source_sha256"])):
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_LEGACY_OR_UNLABELED")
            if props["source_symbol"] != symbol:
                continue
            if int(candidate_run) >= int(run_id):
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_SELF_OR_FUTURE_RUN")
            matching.append((int(candidate_run), ident))
        nxt = data.get("nextPageToken")
        if nxt in (None, ""):
            completed = True
            break
        if type(nxt) is not str or len(nxt) > 512 or nxt in tokens:
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_CENSUS_TOKEN_INVALID")
        tokens.add(nxt)
        page_token = nxt
    if not completed:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_CENSUS_PAGES_EXHAUSTED")
    if not matching:
        return None
    matching.sort(reverse=True)
    if len(matching) > 1 and matching[0][0] == matching[1][0]:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_AMBIGUOUS_PREDECESSOR")
    return matching[0][1]


def plan_intraday_delta(
    previous: Mapping[str, Any], current: Mapping[str, Any], *,
    tf: str, symbol: str,
) -> dict[str, Any]:
    """Compare native timestamp+OHLCV observations, retain both revisions.

    This is not a vendor closing/finality proof; do not derive H4 from it.
    """
    cloud = _cloud()
    if tf not in NATIVE_TFS or symbol not in ("FPT", "DCM", "HPG"):
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_DELTA_IDENTITY_INVALID")
    def rows(snapshot: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
        if type(snapshot) is not dict:
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_DELTA_SOURCE_INVALID")
        start, end = snapshot.get("from_unix"), snapshot.get("to_unix")
        if (type(start) is not int or type(end) is not int
                or start >= end):
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_DELTA_WINDOW_INVALID")
        data = snapshot.get("raw_native")
        cloud.validate_dnse_native(data, start, end, timeframe=tf)
        return {
            stamp: {"t": stamp, **{
                k: data[k][i] for k in ("o", "h", "l", "c", "v")
            }} for i, stamp in enumerate(data["t"])
        }

    old, new = rows(previous), rows(current)
    overlap = old.keys() & new.keys()
    if not overlap:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_NO_OVERLAP")
    def equal(o: dict[str, Any], n: dict[str, Any]) -> bool:
        return (all(Decimal(str(o[k])) == Decimal(str(n[k]))
                    for k in ("o", "h", "l", "c", "v")))
    changed = sorted(k for k in overlap if not equal(old[k], new[k]))
    result = {
        "schema": "mst.cloud.dnse_intraday_incremental_delta.v0.1",
        "provider": "DNSE", "symbol": symbol, "source_native_tf": tf,
        "timestamp_semantics": "SOURCE_NATIVE_UNATTESTED",
        "added": [new[k] for k in sorted(new.keys() - old.keys())],
        "revised": [{"t": k, "before": old[k], "after": new[k]} for k in changed],
        "window_exited_not_deleted": [
            old[k] for k in sorted(old.keys() - new.keys())
        ],
        "unchanged_overlap": len(overlap) - len(changed),
        "preserve_all_original_versions": True,
        "issuer_closed_verified": False,
        "independent_signed_atomic_cas": False,
        "signal_eligible": False,
        "trade_orders": 0,
    }
    result["plan_sha256"] = sha256(
        json.dumps(result, sort_keys=True, separators=(",",":"),
                   allow_nan=False).encode("utf-8")
    ).hexdigest()
    return result


def read_previous_native_delta(
    session: Any, env: Mapping[str, str], parent: str,
    current_payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Verify private predecessor bytes twice before staging a new candidate."""
    cloud = _cloud()
    tf = _guard(env, parent)
    previous_id = discover_native_predecessor(session, env, parent)
    if previous_id is None:
        return None
    try:
        response = session.get(cloud.DRIVE_URL + previous_id, params={
            "fields": ("id,name,mimeType,parents,trashed,shared,ownedByMe,"
                       "isAppAuthorized,md5Checksum,size,version,appProperties"),
        }, timeout=25)
        if response.status_code != 200 or type(response.json()) is not dict:
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_METADATA_INVALID")
        info = response.json()
        name = info.get("name")
        props = info.get("appProperties")
        if (info.get("id") != previous_id or type(name) is not str
                or NATIVE_NAME.fullmatch(name) is None
                or NATIVE_NAME.fullmatch(name).group(1) != tf
                or info.get("mimeType") != "application/json"
                or info.get("parents") != [parent]
                or info.get("trashed") is not False
                or info.get("shared") is not False
                or info.get("ownedByMe") is not True
                or info.get("isAppAuthorized") is not True
                or type(info.get("size")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,6}", info["size"])
                or not 0 < int(info["size"]) <= MAX_PRIOR_BYTES
                or type(info.get("version")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,19}", info["version"])
                or type(props) is not dict
                or props.get("source_native_tf") != tf
                or props.get("source_symbol") != env["MST_DNSE_SYMBOL"]
                or props.get("source_run_id") != NATIVE_NAME.fullmatch(name).group(2)
                or props.get("mst_unpublished") != "true"):
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_PRIVATE_SCOPE_FAILURE")
        if cloud._exact_named_quarantine(session, parent, name) != [previous_id]:
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_NAME_CENSUS_DRIFT")
        old_body = None
        for _ in range(2):
            media = session.get(
                cloud.DRIVE_URL + previous_id, params={"alt":"media"},
                timeout=35, allow_redirects=False,
            )
            if (media.status_code != 200 or type(media.content) is not bytes
                    or len(media.content) != int(info["size"])):
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_READBACK_INVALID")
            if old_body is not None and old_body != media.content:
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_MEDIA_MUTATION")
            old_body = media.content
            if cloud._quarantine_metadata(
                session, previous_id, parent, name, old_body,
            ) != info["version"]:
                raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_VERSION_DRIFT")
        if sha256(old_body).hexdigest() != props.get("source_sha256"):
            raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_SHA_MISMATCH")
        prior = json.loads(old_body)
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_TRANSPORT_FAILED") from None
    from scripts.mst_mfx_native_timeframes import provider_resolution
    if (type(prior) is not dict
            or prior.get("schema") != "mst.cloud.dnse_native_unpublished_candidate.v0.1"
            or prior.get("project") != "MST"
            or prior.get("source") != "DNSE_OFFICIAL_OPENAPI"
            or prior.get("symbol") != env["MST_DNSE_SYMBOL"]
            or prior.get("source_native_tf") != tf
            or prior.get("resolution") != provider_resolution("DNSE",tf)
            or prior.get("issuer_first_known_verified") is not False
            or prior.get("official_venue_closed_verified") is not False
            or prior.get("independent_publish_cas_verified") is not False
            or prior.get("eligible_for_signals") is not False):
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_PRIOR_SOURCE_IDENTITY_DRIFT")
    current = {
        "from_unix": int(env["MST_DNSE_FROM_UNIX"]),
        "to_unix": int(env["MST_DNSE_TO_UNIX"]),
        "raw_native": current_payload,
    }
    try:
        delta = plan_intraday_delta(prior, current, tf=tf,
                                    symbol=env["MST_DNSE_SYMBOL"])
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_DNSE_INTRA_DELTA_INVALID") from None
    return {
        "schema": "mst.cloud.dnse_native_prior_source_delta_candidate.v0.1",
        "prior_private_file_id": previous_id,
        "prior_source_sha256": sha256(old_body).hexdigest(),
        "delta": delta,
        "prior_and_current_issuer_closed_verified": False,
        "eligible_for_signals": False,
    }
