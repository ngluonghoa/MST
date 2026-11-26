#!/usr/bin/env python3
"""MST §240: private app-owned UNPUBLISHED source CHUNK, two media readbacks.

Cloud-only reusable *library*, NOT a GitHub workflow or publisher. No caller
on protected main invokes this today. Requires separate licensed source
adapter, owner-approved manual workflow and authenticated drive.file session.

Google Drive permits duplicate filenames, and two readbacks are NOT a CAS,
distributed lock, independent signature, venue closure or retention right.
An upload error may leave an orphan; never delete/overwrite/promote it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5, sha256
import json
import re
import secrets
from scripts.mst_ssi_retrieval_provenance import (
    SSI_PROVENANCE_SCHEMA, RetrievalDenied, validate_provenance,
)
from typing import Any, Mapping

FILES = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
MIME = "application/json"
SCHEMA = "mst.cloud.unpublished_source_snapshot.v0.1"
MAX_BYTES = 1_500_000
DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"[1-9][0-9]{5,19}\Z")
SYMBOLS = ("FPT", "HPG", "DCM")
TFS = ("M5", "M15", "M30", "H1", "D1")
PROVIDERS = ("SSI", "DNSE", "VCBS")
CONTEXT = {
    "GITHUB_REPOSITORY": "ngluonghoa/MST",
    "GITHUB_REPOSITORY_ID": "1450356304",
    "GITHUB_REPOSITORY_OWNER_ID": "353049266",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_WORKFLOW_REF": (
        "ngluonghoa/MST/.github/workflows/"
        "mst-private-source-chunks-manual.yml@refs/heads/main"
    ),
    "GITHUB_RUN_ATTEMPT": "1",
    "MST_CHUNK_STAGE_CONFIRM": "STAGE_SOURCE_ONLY",
    "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED": "true",
    "MST_SOURCE_RETENTION_RIGHTS_CONFIRMED": "true",
}

class ChunkDenied(ValueError):
    """Always fixed, non-sensitive codes. Never print a provider exception."""


@dataclass(frozen=True)
class PrivateUnpublishedChunk:
    file_id: str = field(repr=False)
    sha256: str = field(repr=False)
    provider: str
    symbol: str
    native_tf: str
    bytes_verified: int
    distinct_readbacks_verified: int = 2
    media_md5_matched: bool = True
    source_rights_independently_attested: bool = False
    venue_closed_bar_attested: bool = False
    signed_cas_verified: bool = False
    published_to_market_cache: bool = False
    signals_or_trade_eligible: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.file_id, str)
            or not DRIVE_ID.fullmatch(self.file_id)
            or type(self.sha256) is not str or not HEX_SHA.fullmatch(self.sha256)
            or self.provider not in PROVIDERS or self.symbol not in SYMBOLS
            or self.native_tf not in TFS
            or type(self.bytes_verified) is not int or not 0 < self.bytes_verified <= MAX_BYTES
            or type(self.distinct_readbacks_verified) is not int
            or self.distinct_readbacks_verified != 2
            or self.media_md5_matched is not True
            or any(getattr(self, key) is not False for key in (
                "source_rights_independently_attested", "venue_closed_bar_attested",
                "signed_cas_verified", "published_to_market_cache",
                "signals_or_trade_eligible"
            ))):
            raise ChunkDenied("MST_240_RECEIPT_AUTHORITY_OR_SHAPE_DENIED")

    def public_receipt(self) -> dict[str, object]:
        """No Drive IDs, raw market bars, provider secrets, SHA or owner info."""
        return {
            "schema": "mst.cloud.private_chunk_readback_receipt.v0.1",
            "status": "UNPUBLISHED_PRIVATE_CHUNK_READBACK_ONLY",
            "provider": self.provider,
            "native_tf": self.native_tf,
            "two_independent_media_reads": True,
            "sha256_and_md5_readback_verified": True,
            "source_rights_independently_attested": False,
            "venue_closed_bar_attested": False,
            "independent_signed_monotone_cas_verified": False,
            "market_cache_promoted": False,
            "signals_or_trade_eligible": False,
        }


def _id(value: Any) -> str:
    if type(value) is not str or not DRIVE_ID.fullmatch(value):
        raise ChunkDenied("MST_240_INVALID_PRIVATE_DRIVE_ID")
    return value


def _json_reply(resp: Any, allowed: tuple[int, ...]) -> dict[str, Any]:
    try:
        if resp.status_code not in allowed:
            raise ChunkDenied("MST_240_DRIVE_HTTP_DENIED")
        body = resp.json()
        if type(body) is not dict:
            raise ChunkDenied("MST_240_DRIVE_REPLY_SHAPE_DENIED")
        return body
    except ChunkDenied:
        raise
    except Exception:
        raise ChunkDenied("MST_240_DRIVE_TRANSPORT_OR_JSON_DENIED") from None


def _get_json(session: Any, url: str, *, params: dict[str, str]) -> dict[str, Any]:
    try:
        reply = session.get(url, params=params, timeout=25, allow_redirects=False)
    except Exception:
        raise ChunkDenied("MST_240_DRIVE_GET_FAILED") from None
    return _json_reply(reply, (200,))


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ChunkDenied("MST_240_DUPLICATE_JSON_KEY_DENIED")
        out[key] = value
    return out


def _deny_constant(_: str) -> None:
    raise ChunkDenied("MST_240_NONFINITE_JSON_DENIED")


def _validate_owner_source(
    env: Mapping[str, str], raw: bytes
) -> tuple[str, str, str, str, str]:
    # All gates BEFORE any Drive HTTP. Variables are owner declarations, not
    # independent source-retention/first-known or cryptographic attestations.
    if (not isinstance(env, Mapping)
        or any(env.get(k) != v for k, v in CONTEXT.items())):
        raise ChunkDenied("MST_240_MANUAL_OWNER_RETENTION_GATE_REQUIRED")
    run = env.get("GITHUB_RUN_ID")
    if type(run) is not str or not RUN_ID.fullmatch(run):
        raise ChunkDenied("MST_240_FIRST_RUN_IDENTIFIER_REQUIRED")
    if type(raw) is not bytes or not 20 <= len(raw) <= MAX_BYTES:
        raise ChunkDenied("MST_240_SOURCE_BYTES_BOUNDS_DENIED")
    try:
        payload = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
            parse_constant=_deny_constant,
        )
    except ChunkDenied:
        raise
    except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError):
        raise ChunkDenied("MST_240_SOURCE_JSON_INVALID") from None
    base_fields = {
        "schema", "project", "provider", "symbol", "native_tf",
        "raw_native", "eligible_for_signals"
    }
    if type(payload) is not dict:
        raise ChunkDenied("MST_240_SOURCE_ENVELOPE_UNQUALIFIED")
    version = payload.get("schema")
    valid_shape = (
        version == SCHEMA and set(payload) == base_fields
        or version == SSI_PROVENANCE_SCHEMA and payload.get("provider") == "SSI"
        and set(payload) == base_fields | {"retrieval_provenance"}
    )
    if (not valid_shape or payload.get("project") != "MST"
        or payload.get("provider") not in PROVIDERS
        or payload.get("symbol") not in SYMBOLS
        or payload.get("native_tf") not in TFS
        or payload.get("eligible_for_signals") is not False
        or type(payload.get("raw_native")) not in (dict, list)
        or not payload["raw_native"]):
        raise ChunkDenied("MST_240_SOURCE_ENVELOPE_UNQUALIFIED")
    provider, symbol, tf = (
        payload["provider"], payload["symbol"], payload["native_tf"]
    )
    if env.get("MST_" + provider + "_SOURCE_RIGHTS_CONFIRMED") != "true":
        raise ChunkDenied("MST_240_PROVIDER_RETENTION_RIGHTS_GATE_REQUIRED")
    if (env.get("MST_SOURCE_TF") != tf
        or env.get("MST_SOURCE_SYMBOL") != symbol
        or env.get("MST_SOURCE_PROVIDER") != provider):
        raise ChunkDenied("MST_240_SOURCE_CONTEXT_MISMATCH")
    if version == SSI_PROVENANCE_SCHEMA:
        try:
            validate_provenance(payload["retrieval_provenance"], payload["raw_native"], env)
        except RetrievalDenied:
            raise ChunkDenied("MST_240_SSI_RETRIEVAL_PROVENANCE_DENIED") from None
    digest = sha256(raw).hexdigest()
    return provider, symbol, tf, run, digest


def _candidate_name(provider: str, symbol: str, tf: str, run: str, digest: str) -> str:
    return "MST_UNPUBLISHED_RAW_" + "_".join((provider, symbol, tf, run, digest)) + ".json"


def _parent_private(session: Any, parent_id: str) -> None:
    meta = _get_json(session, FILES + "/" + parent_id, params={
        "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,isAppAuthorized",
    })
    if (meta.get("id") != parent_id or meta.get("name") != "CHUNKS"
        or meta.get("mimeType") != "application/vnd.google-apps.folder"
        or not isinstance(meta.get("parents"), list) or len(meta["parents"]) != 1
        or meta.get("trashed") is not False
        or meta.get("shared") is not False
        or meta.get("ownedByMe") is not True
        or meta.get("isAppAuthorized") is not True):
        raise ChunkDenied("MST_240_PRIVATE_CHUNKS_SCOPE_DENIED")


def _list_exact(session: Any, parent_id: str, name: str) -> list[dict[str, Any]]:
    response = _get_json(session, FILES, params={
        "q": "'" + parent_id + "' in parents and name = '" + name +
             "' and trashed = false",
        "pageSize": "100",
        "fields": "nextPageToken,incompleteSearch,files(id,name,mimeType,parents,trashed)",
    })
    entries = response.get("files")
    if (response.get("incompleteSearch", False) is not False
        or type(entries) is not list or len(entries) > 1
        or response.get("nextPageToken") not in (None, "")):
        raise ChunkDenied("MST_240_CHUNK_CENSUS_AMBIGUOUS")
    for item in entries:
        if (type(item) is not dict or type(item.get("id")) is not str
            or not DRIVE_ID.fullmatch(item["id"])
            or item.get("name") != name or item.get("mimeType") != MIME
            or item.get("parents") != [parent_id]
            or item.get("trashed") is not False):
            raise ChunkDenied("MST_240_CHUNK_CENSUS_SCOPE_INVALID")
    return entries


def _file_metadata(
    session: Any, file_id: str, parent: str, name: str,
    digest: str, payload: bytes, provider: str, symbol: str, tf: str, run: str,
) -> str:
    info = _get_json(session, FILES + "/" + file_id, params={
        "fields": ("id,name,mimeType,parents,trashed,shared,ownedByMe,"
                   "isAppAuthorized,size,md5Checksum,version,appProperties"),
    })
    props = info.get("appProperties")
    expected_props = {
        "mst_unpublished": "true", "source_sha256": digest,
        "source_provider": provider, "source_symbol": symbol,
        "source_native_tf": tf, "source_run_id": run,
        "source_rights_independently_attested": "false",
        "source_closed_bar_attested": "false",
        "source_signal_eligible": "false",
    }
    version = info.get("version")
    if (info.get("id") != file_id or info.get("name") != name
        or info.get("mimeType") != MIME or info.get("parents") != [parent]
        or info.get("trashed") is not False or info.get("shared") is not False
        or info.get("ownedByMe") is not True
        or info.get("isAppAuthorized") is not True
        or info.get("size") != str(len(payload))
        or info.get("md5Checksum") != md5(payload).hexdigest()
        or props != expected_props or type(version) is not str
        or not re.fullmatch(r"[1-9][0-9]{0,19}", version)):
        raise ChunkDenied("MST_240_CHUNK_METADATA_NOT_PRIVATE_OR_INTACT")
    return version


def _get_media(session: Any, file_id: str, original: bytes, digest: str) -> None:
    try:
        resp = session.get(
            FILES + "/" + file_id, params={"alt": "media"},
            timeout=35, allow_redirects=False,
        )
        if (resp.status_code != 200 or type(resp.content) is not bytes
            or len(resp.content) != len(original)
            or sha256(resp.content).hexdigest() != digest
            or resp.content != original):
            raise ChunkDenied("MST_240_MEDIA_READBACK_MISMATCH")
    except ChunkDenied:
        raise
    except Exception:
        raise ChunkDenied("MST_240_MEDIA_READBACK_TRANSPORT_FAILED") from None


def _multipart(meta: dict[str, Any], payload: bytes, boundary: str) -> bytes:
    # Drive requires multipart/related, NOT requests' multipart/form-data.
    header = json.dumps(
        meta, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    sep = boundary.encode("ascii")
    return (
        b"--" + sep + b"\r\n"
        b"Content-Type: application/json; charset=UTF-8\r\n\r\n" +
        header + b"\r\n--" + sep + b"\r\n"
        b"Content-Type: application/json\r\n\r\n" +
        payload + b"\r\n--" + sep + b"--\r\n"
    )


def upload_private_unpublished_chunk(
    session: Any, env: Mapping[str, str], parent_id: str, raw: bytes
) -> PrivateUnpublishedChunk:
    """One unpromoted writer. Fails closed; never reuses/overwrites a name.

    Any failed/ambiguous upload may leave an orphan. No cleanup or retry.
    Explicitly NO uniqueness/CAS guarantee from Google Drive file names.
    """
    provider, symbol, tf, run, digest = _validate_owner_source(env, raw)
    parent = _id(parent_id)
    if env.get("MST_PRIVATE_CHUNKS_FOLDER_ID") != parent:
        raise ChunkDenied("MST_240_CONFIGURED_CHUNKS_FOLDER_MISMATCH")
    name = _candidate_name(provider, symbol, tf, run, digest)
    _parent_private(session, parent)
    if _list_exact(session, parent, name):
        raise ChunkDenied("MST_240_EXISTING_CHUNK_NAME_DENIED")
    props = {
        "mst_unpublished": "true", "source_sha256": digest,
        "source_provider": provider, "source_symbol": symbol,
        "source_native_tf": tf, "source_run_id": run,
        "source_rights_independently_attested": "false",
        "source_closed_bar_attested": "false",
        "source_signal_eligible": "false",
    }
    metadata = {
        "name": name, "mimeType": MIME, "parents": [parent],
        "appProperties": props,
        "description": "MST PRIVATE UNPUBLISHED SOURCE; NO TRADE/NO CAS",
    }
    boundary = "mstprivate" + secrets.token_hex(16)
    upload_body = _multipart(metadata, raw, boundary)
    try:
        response = session.post(
            UPLOAD, params={
                "uploadType": "multipart",
                "fields": "id,name,mimeType,parents,trashed",
            },
            headers={"Content-Type": "multipart/related; boundary=" + boundary},
            data=upload_body, timeout=35, allow_redirects=False,
        )
    except Exception:
        raise ChunkDenied("MST_240_UPLOAD_TRANSPORT_AMBIGUOUS_ORPHAN_POSSIBLE") from None
    reply = _json_reply(response, (200, 201))
    file_id = _id(reply.get("id"))
    if (reply.get("name") != name or reply.get("mimeType") != MIME
        or reply.get("parents") != [parent]
        or reply.get("trashed") is not False):
        raise ChunkDenied("MST_240_UPLOAD_IDENTITY_NOT_CONFIRMED")
    ver = _file_metadata(session, file_id, parent, name, digest, raw,
                         provider, symbol, tf, run)
    for _ in range(2):
        _get_media(session, file_id, raw, digest)
        now = _file_metadata(session, file_id, parent, name, digest, raw,
                             provider, symbol, tf, run)
        if now != ver:
            raise ChunkDenied("MST_240_PRIVATE_CHUNK_VERSION_DRIFT")
    if [entry["id"] for entry in _list_exact(session, parent, name)] != [file_id]:
        raise ChunkDenied("MST_240_POSTUPLOAD_NAME_DUPLICATE_OR_GONE")
    # Readback success is NOT proof of immutable Drive behavior, signed CAS,
    # global single writer, vendor retention rights or venue finality.
    return PrivateUnpublishedChunk(
        file_id=file_id, sha256=digest,
        provider=provider, symbol=symbol, native_tf=tf,
        bytes_verified=len(raw),
    )
