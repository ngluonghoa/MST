"""MST SSI app-owned Cloud source quarantine, strictly UNPUBLISHED.

A manual main-only workflow can preserve licensed SSI native OHLCV without
publishing a Cache head. All persistence is into the existing private OAuth
app-owned CHUNKS folder; never GitHub logs, local files, or a trading client.
This does NOT certify exchange close, source price scale, adjustment basis,
issuer first-known, license entitlement, or independent atomic CAS.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from hashlib import sha256, md5
import json
import re
from typing import Any, Mapping
from uuid import uuid4

from scripts import mst_mfx_style_appowned_pipeline as cloud
from scripts.mst_mfx_ssi_readonly import _native_source_row
from scripts.mst_mfx_native_timeframes import provider_resolution

MAX_PAGES = 8
PAGE_SIZE = 100
MAX_ARCHIVE_BYTES = 1_500_000
MAX_ROWS = 500
NAME = re.compile(
    r"MST_UNPUBLISHED_SSI_NATIVE_(M5|M15|M30|H1|D1)_([1-9][0-9]{5,19})_1\.json\Z"
)
NATIVE_KEYS = ("symbol", "tradingDate", "open", "high", "low", "close", "volume")


def _guard(env: Mapping[str, str]) -> tuple[str, str, date, date]:
    mode, _ = cloud.guard(env)
    if mode != cloud.MODE_SSI_STAGE:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_EXACT_OWNER_MODE_REQUIRED")
    tf = env.get("MST_SOURCE_TF", "D1")
    try:
        a, b = date.fromisoformat(env["MST_SSI_FROM_DATE"]), date.fromisoformat(env["MST_SSI_TO_DATE"])
    except (KeyError, ValueError):
        raise cloud.CloudGateDenied("MST_SSI_STAGE_DATE_INVALID") from None
    return env["MST_SSI_SYMBOL"], tf, a, b


def _normal_rows(
    source: Any, *, symbol: str, tf: str, first: date, last: date,
) -> dict[str, dict[str, Any]]:
    """Reject extra source fields/tokens; do not implicitly resample bars."""
    if type(source) is not list or not 1 <= len(source) <= MAX_ROWS:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_NATIVE_ROWS_BOUNDED_REQUIRED")
    observed: dict[str, dict[str, Any]] = {}
    for row in source:
        if type(row) is not dict or set(row) != set(NATIVE_KEYS):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_NATIVE_FIELD_SET_INVALID")
        try:
            label = _native_source_row(row, symbol=symbol, first=first,
                                       last=last, timeframe=tf)
        except Exception:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_NATIVE_OHLCV_INVALID") from None
        if label != row["tradingDate"] or label in observed:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_TIMESTAMP_NOT_CANONICAL_OR_DUPLICATE")
        observed[label] = row
    return observed


def _archive_rows(archive: dict[str, Any], *, symbol: str, tf: str) -> dict[str, dict[str, Any]]:
    try:
        if (type(archive.get("from_date")) is not str
                or type(archive.get("to_date")) is not str):
            raise ValueError("invalid archive dates")
        a, b = date.fromisoformat(archive["from_date"]), date.fromisoformat(archive["to_date"])
        if b < a:
            raise ValueError("reversed dates")
    except ValueError:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_DATE_INVALID") from None
    return _normal_rows(archive.get("raw_native"), symbol=symbol, tf=tf,
                        first=a, last=b)


def _delta(
    prior_rows: dict[str, dict[str, Any]], current_rows: dict[str, dict[str, Any]],
    *, symbol: str, tf: str,
) -> dict[str, Any]:
    old, new = set(prior_rows), set(current_rows)
    overlap = old & new
    if not overlap:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_NO_OVERLAP")
    def same(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return all(Decimal(str(a[k])) == Decimal(str(b[k]))
                   for k in ("open", "high", "low", "close", "volume"))
    revisions = [k for k in sorted(overlap) if not same(prior_rows[k], current_rows[k])]
    result = {
        "schema":"mst.cloud.ssi_native_incremental_delta.v0.1",
        "provider":"SSI_FASTCONNECT_V3_MARKET_DATA",
        "symbol":symbol, "source_native_tf":tf,
        "source_price_unit_or_adjustment_attested":False,
        "issuer_first_known_verified":False,
        "official_venue_closed_verified":False,
        "signed_atomic_cas_ready":False,
        "eligible_for_signals":False,
        "added":[current_rows[k] for k in sorted(new-old)],
        "revised":[{"timestamp":k,"before":prior_rows[k],"after":current_rows[k]}
                   for k in revisions],
        "window_exited_not_deleted":[prior_rows[k] for k in sorted(old-new)],
        "unchanged_overlap":len(overlap)-len(revisions),
        "preserve_all_versions":True,
    }
    result["plan_sha256"] = sha256(json.dumps(
        result, sort_keys=True, separators=(",",":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return result


def discover_ssi_prior(
    session: Any, env: Mapping[str,str], parent: str,
) -> str | None:
    symbol, tf, _, _ = _guard(env)
    if type(parent) is not str or not cloud.DRIVE_ID_RE.fullmatch(parent):
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PARENT_INVALID")
    current_run = env["GITHUB_RUN_ID"]
    seen_names: set[str] = set()
    seen_ids: set[str] = set()
    used_tokens: set[str] = set()
    continuation = None
    completed = False
    matching: list[tuple[int,str]] = []
    for _ in range(MAX_PAGES):
        params: dict[str, Any] = {
            "q":("'" + parent + "' in parents and "
                 "name contains 'MST_UNPUBLISHED_SSI_' and trashed = false"),
            "fields":"nextPageToken,incompleteSearch,files(id,name,mimeType,parents,trashed,appProperties)",
            "pageSize":PAGE_SIZE,
        }
        if continuation is not None:
            params["pageToken"] = continuation
        try:
            resp = session.get("https://www.googleapis.com/drive/v3/files",
                               params=params, timeout=25, allow_redirects=False)
            if resp.status_code != 200:
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_DENIED")
            census = resp.json()
        except cloud.CloudGateDenied:
            raise
        except Exception:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_TRANSPORT_ERROR") from None
        if (type(census) is not dict or type(census.get("files")) is not list
                or len(census["files"]) > PAGE_SIZE
                or census.get("incompleteSearch") is True):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_INVALID")
        for entry in census["files"]:
            if type(entry) is not dict:
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_RECORD_INVALID")
            name, ident = entry.get("name"), entry.get("id")
            if (type(name) is not str or not name.startswith("MST_UNPUBLISHED_SSI_")
                    or NAME.fullmatch(name) is None
                    or type(ident) is not str or not cloud.DRIVE_ID_RE.fullmatch(ident)
                    or entry.get("mimeType") != "application/json"
                    or entry.get("parents") != [parent]
                    or entry.get("trashed") is not False):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_SCOPE_OR_LEGACY_INVALID")
            if name in seen_names or ident in seen_ids:
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_DUPLICATED")
            seen_names.add(name)
            seen_ids.add(ident)
            hit = NAME.fullmatch(name)
            record_tf, run = hit.groups()
            if record_tf != tf:
                continue
            props = entry.get("appProperties")
            if (type(props) is not dict
                    or props.get("mst_unpublished") != "true"
                    or props.get("source_native_tf") != tf
                    or props.get("source_run_id") != run
                    or props.get("source_symbol") not in ("FPT","DCM","HPG")
                    or props.get("schema") != "ssi_native_candidate_v1"
                    or type(props.get("source_sha256")) is not str
                    or not re.fullmatch(r"[0-9a-f]{64}",props["source_sha256"])):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_UNLABELED")
            if props["source_symbol"] != symbol:
                continue
            if int(run) >= int(current_run):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_SELF_OR_FUTURE")
            matching.append((int(run),ident))
        next_token = census.get("nextPageToken")
        if next_token in (None,""):
            completed = True
            break
        if (type(next_token) is not str or len(next_token) > 512
                or next_token in used_tokens):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_TOKEN_DRIFT")
        used_tokens.add(next_token)
        continuation = next_token
    if not completed:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CENSUS_INCOMPLETE")
    if not matching:
        return None
    matching.sort(reverse=True)
    if len(matching)>1 and matching[0][0]==matching[1][0]:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_AMBIGUOUS")
    return matching[0][1]


def _verified_prior(
    session: Any, env: Mapping[str,str], parent: str,
    file_id: str, current_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    symbol, tf, _, _ = _guard(env)
    try:
        r = session.get(cloud.DRIVE_URL+file_id, params={
            "fields":"id,name,mimeType,parents,trashed,shared,ownedByMe,isAppAuthorized,"
                     "md5Checksum,size,version,appProperties",
        }, timeout=25)
        if r.status_code != 200 or type(r.json()) is not dict:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_METADATA_DENIED")
        info=r.json()
        name=info.get("name")
        props=info.get("appProperties")
        match = NAME.fullmatch(name) if type(name) is str else None
        if (info.get("id")!=file_id or match is None
                or match.group(1)!=tf
                or int(match.group(2))>=int(env["GITHUB_RUN_ID"])
                or info.get("mimeType")!="application/json"
                or info.get("parents")!=[parent]
                or info.get("trashed") is not False
                or info.get("shared") is not False
                or info.get("ownedByMe") is not True
                or info.get("isAppAuthorized") is not True
                or type(info.get("size")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,6}",info["size"])
                or not 0 < int(info["size"])<=MAX_ARCHIVE_BYTES
                or type(info.get("version")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,19}",info["version"])
                or type(props) is not dict
                or props.get("mst_unpublished")!="true"
                or props.get("source_symbol")!=symbol
                or props.get("source_native_tf")!=tf
                or props.get("source_run_id")!=match.group(2)
                or props.get("schema")!="ssi_native_candidate_v1"):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_PRIVATE_METADATA_INVALID")
        if cloud._exact_named_quarantine(session,parent,name)!=[file_id]:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_NAME_CENSUS_DRIFT")
        body=None
        for _ in range(2):
            media=session.get(cloud.DRIVE_URL+file_id,params={"alt":"media"},
                              timeout=35,allow_redirects=False)
            if (media.status_code!=200 or type(media.content) is not bytes
                    or len(media.content)!=int(info["size"])):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_MEDIA_READBACK_DENIED")
            if body is not None and body!=media.content:
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_CONTENT_MUTATION")
            body=media.content
            if (cloud._quarantine_metadata(session,file_id,parent,name,body)
                    !=info["version"]):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_VERSION_MUTATION")
        if (sha256(body).hexdigest()!=props.get("source_sha256")
                or md5(body).hexdigest()!=info.get("md5Checksum")):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_DIGEST_INVALID")
        archive=json.loads(body)
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_TRANSPORT_INVALID") from None
    if (type(archive) is not dict
            or archive.get("schema")!="mst.cloud.ssi_native_unpublished_candidate.v0.1"
            or archive.get("project")!="MST"
            or archive.get("source")!="SSI_FASTCONNECT_V3_MARKET_DATA"
            or archive.get("symbol")!=symbol
            or archive.get("source_native_tf")!=tf
            or archive.get("resolution")!=provider_resolution("SSI",tf)
            or archive.get("issuer_first_known_verified") is not False
            or archive.get("official_venue_closed_verified") is not False
            or archive.get("independent_publish_cas_verified") is not False
            or archive.get("eligible_for_signals") is not False):
        raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIOR_IDENTITY_INVALID")
    previous=_archive_rows(archive,symbol=symbol,tf=tf)
    delta=_delta(previous,current_rows,symbol=symbol,tf=tf)
    return {
        "schema":"mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
        "prior_private_file_id":file_id,
        "prior_source_sha256":sha256(body).hexdigest(),
        "delta":delta,
        "eligible_for_signals":False,
        "issuer_close_not_attested":True,
    }


def stage_ssi_native_source(
    session: Any, env: Mapping[str,str], source_rows: list[dict[str,Any]],
) -> dict[str,Any]:
    """Single private app-owned write with two readbacks; no publisher."""
    symbol,tf,first,last=_guard(env)
    rows=_normal_rows(source_rows,symbol=symbol,tf=tf,first=first,last=last)
    try:
        root=cloud._list_exact_child(session,cloud.DRIVE_ROOT,None)
        chunks=cloud._list_exact_child(session,"CHUNKS",root["id"]) if root else None
        if not chunks:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_CHUNKS_NOT_FOUND")
        parent=chunks["id"]
        # Metadata/private folder identity checked by Cloud preflight caller.
        if not cloud.DRIVE_ID_RE.fullmatch(parent):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_CHUNKS_SCOPE_INVALID")
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_CHUNKS_LOOKUP_FAILED") from None
    prior_id=discover_ssi_prior(session,env,parent)
    prior=_verified_prior(session,env,parent,prior_id,rows) if prior_id else None
    # A fully verified old candidate already retains all previously seen bars.
    # If only the provider's rolling window changes, do not reupload identical
    # source OHLCV or delete window-exited bars. This is not a published head.
    if prior is not None:
        from scripts.mst_cache_noop_reuse import verified_unchanged_receipt
        try:
            no_change=verified_unchanged_receipt(
                prior,provider="SSI",symbol=symbol,tf=tf,observed_rows=len(rows),
            )
        except ValueError:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_REUSE_PROOF_INVALID") from None
        if no_change is not None:
            candidate_name=f"MST_UNPUBLISHED_SSI_NATIVE_{tf}_{env['GITHUB_RUN_ID']}_1.json"
            if cloud._exact_named_quarantine(session,parent,candidate_name):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_DUPLICATE_ATTEMPT_MANUAL_REVIEW")
            return no_change
    archive=
        "schema":"mst.cloud.ssi_native_unpublished_candidate.v0.1",
        "project":"MST","source":"SSI_FASTCONNECT_V3_MARKET_DATA",
        "symbol":symbol,"source_native_tf":tf,
        "resolution":provider_resolution("SSI",tf),
        "from_date":first.isoformat(),"to_date":last.isoformat(),
        "issuer_first_known_verified":False,
        "official_venue_closed_verified":False,
        "price_unit_adjusted_basis_verified":False,
        "independent_publish_cas_verified":False,
        "eligible_for_signals":False,
        "raw_native":[rows[k] for k in sorted(rows)],
    }
    if prior is not None:
        archive["prior_source_incremental_delta"]=prior
    body=json.dumps(archive,sort_keys=True,separators=(",",":"),
                    allow_nan=False).encode("utf-8")
    if not 0<len(body)<=MAX_ARCHIVE_BYTES:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_ARCHIVE_BOUND_EXCEEDED")
    checksum=sha256(body).hexdigest()
    name=f"MST_UNPUBLISHED_SSI_NATIVE_{tf}_{env['GITHUB_RUN_ID']}_1.json"
    if cloud._exact_named_quarantine(session,parent,name):
        raise cloud.CloudGateDenied("MST_SSI_STAGE_DUPLICATE_ATTEMPT_MANUAL_REVIEW")
    metadata={
        "name":name,"mimeType":"application/json","parents":[parent],
        "description":"MST SSI UNPUBLISHED SOURCE QUARANTINE; not Cache/Signals",
        "appProperties":{
            "mst_unpublished":"true",
            "source_sha256":checksum,
            "source_symbol":symbol,"source_native_tf":tf,
            "source_run_id":env["GITHUB_RUN_ID"],
            "schema":"ssi_native_candidate_v1",
        },
    }
    boundary="mst"+uuid4().hex
    prefix=("--"+boundary+"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            +json.dumps(metadata,separators=(",",":"))
            +"\r\n--"+boundary+"\r\nContent-Type: application/json\r\n\r\n").encode()
    multipart=prefix+body+("\r\n--"+boundary+"--\r\n").encode()
    try:
        upload=session.post("https://www.googleapis.com/upload/drive/v3/files",
             params={"uploadType":"multipart","ignoreDefaultVisibility":"true",
                     "fields":"id,name,mimeType,parents"},
             data=multipart,
             headers={"Content-Type":"multipart/related; boundary="+boundary},
             timeout=35)
        if upload.status_code not in (200,201):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_PRIVATE_UPLOAD_DENIED")
        created=upload.json()
        ident=created.get("id") if type(created) is dict else None
        if type(ident) is not str or not cloud.DRIVE_ID_RE.fullmatch(ident):
            raise cloud.CloudGateDenied("MST_SSI_STAGE_UPLOAD_ACK_UNVERIFIED")
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_UPLOAD_ACK_UNKNOWN_MANUAL_REVIEW") from None
    version=cloud._quarantine_metadata(session,ident,parent,name,body)
    for _ in range(2):
        try:
            media=session.get(cloud.DRIVE_URL+ident,params={"alt":"media"},
                              timeout=35,allow_redirects=False)
            if (media.status_code!=200 or type(media.content) is not bytes
                    or media.content!=body):
                raise cloud.CloudGateDenied("MST_SSI_STAGE_MEDIA_MISMATCH")
        except cloud.CloudGateDenied:
            raise
        except Exception:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_MEDIA_READBACK_FAILED") from None
        if cloud._quarantine_metadata(session,ident,parent,name,body)!=version:
            raise cloud.CloudGateDenied("MST_SSI_STAGE_VERSION_MUTATION")
    if cloud._exact_named_quarantine(session,parent,name)!=[ident]:
        raise cloud.CloudGateDenied("MST_SSI_STAGE_UPLOAD_NAME_CENSUS_CHANGED")
    delta=prior["delta"] if prior else None
    return {
        "unpublished_private_source_document_stored":True,
        "source_provider":"SSI_FASTCONNECT_V3_MARKET_DATA",
        "source_native_tf":tf,
        "source_rows_observed":len(rows),
        "source_delta_linked_to_prior_private_native_tf":bool(prior),
        "source_delta_added_rows":len(delta["added"]) if delta else 0,
        "source_delta_revised_rows":len(delta["revised"]) if delta else 0,
        "source_delta_window_exited_not_deleted":(
            len(delta["window_exited_not_deleted"]) if delta else 0),
        "stored_object_count":1,
        "two_private_media_readbacks_sha256_verified":True,
        "not_a_cache_publish_commit":True,
        "independent_atomic_cas_ready":False,
        "signals_and_trading_eligible":False,
    }
