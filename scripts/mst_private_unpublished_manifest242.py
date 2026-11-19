#!/usr/bin/env python3
"""MST §242: PRIVATE UNPUBLISHED manifest custody for a verified source CHUNK.

Not a market Cache publisher, independent signer or CAS. No cron, broker,
data-vendor call, automatic repair, deletion, overwrite or retry. Google Drive
does not guarantee unique filenames or an atomic distributed compare-and-swap.
All external source rights, bar first-known/finality remain UNATTESTED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5, sha256
import json
import re
import secrets
from typing import Any, Mapping

from scripts.mst_private_chunk_readback240 import (
    CONTEXT, FILES, UPLOAD, MIME, MAX_BYTES,
    PrivateUnpublishedChunk, ChunkDenied,
    _id, _get_json, _json_reply, _get_media, _file_metadata,
    _list_exact, _candidate_name, _validate_owner_source, _multipart,
)

SCHEMA = "mst.cloud.private_unpublished_manifest.v0.1"
RECEIPT_SCHEMA = "mst.cloud.unpublished_manifest_readback_receipt.v0.1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
DIGEST_TAG = "MST_UNPUBLISHED_MANIFEST"
FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_MANIFEST_BYTES = 8192


class ManifestDenied(ValueError):
    """Fixed diagnostics only. Never leak file IDs, hashes or market rows."""


@dataclass(frozen=True)
class UnpublishedManifestReceipt:
    manifest_file_id: str = field(repr=False)
    manifest_sha256: str = field(repr=False)
    source_sha256: str = field(repr=False)
    provider: str
    symbol: str
    native_tf: str
    verified_readback_count: int = 2
    manifest_published: bool = False
    source_finality_attested: bool = False
    rights_independently_attested: bool = False
    independent_signed_cas_proven: bool = False
    eligible_for_signals_or_trades: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.manifest_file_id) is not str or not self.manifest_file_id
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,160}", self.manifest_file_id)
            or any(type(d) is not str or not HEX.fullmatch(d)
                   for d in (self.manifest_sha256, self.source_sha256))
            or self.provider not in ("SSI", "DNSE", "VCBS")
            or self.symbol not in ("FPT", "HPG", "DCM")
            or self.native_tf not in ("M5", "M15", "M30", "H1", "D1")
            or type(self.verified_readback_count) is not int
            or self.verified_readback_count != 2
            or any(getattr(self, name) is not False for name in (
                "manifest_published", "source_finality_attested",
                "rights_independently_attested", "independent_signed_cas_proven",
                "eligible_for_signals_or_trades"
            ))
        ):
            raise ManifestDenied("MST_242_MANIFEST_RECEIPT_AUTHORITY_INVALID")

    def public_receipt(self) -> dict[str, Any]:
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "UNPUBLISHED_PRIVATE_MANIFEST_TWO_READ_ONLY",
            "provider": self.provider,
            "native_tf": self.native_tf,
            "source_chunk_reverified": True,
            "manifest_media_sha256_twice_verified": True,
            "manifest_published": False,
            "source_finality_attested": False,
            "rights_independently_attested": False,
            "independent_signed_monotone_cas_proven": False,
            "eligible_for_signals_or_trades": False,
        }


def _verify_guard(env: Mapping[str, str], source: PrivateUnpublishedChunk) -> str:
    if (
        not isinstance(env, Mapping)
        or any(env.get(key) != value for key, value in CONTEXT.items())
        or env.get("MST_PRIVATE_MANIFEST_WRITE_ACCEPTED") != "true"
        or not isinstance(source, PrivateUnpublishedChunk)
        or not re.fullmatch(r"[1-9][0-9]{5,19}", env.get("GITHUB_RUN_ID", ""))
        or env.get("MST_SOURCE_PROVIDER") != source.provider
        or env.get("MST_SOURCE_SYMBOL") != source.symbol
        or env.get("MST_SOURCE_TF") != source.native_tf
        or env.get("MST_" + source.provider + "_SOURCE_RIGHTS_CONFIRMED") != "true"
    ):
        raise ManifestDenied("MST_242_MAIN_FIRST_ATTEMPT_OWNER_SOURCE_GATE_REQUIRED")
    # A forged dataclass receipt is not source integrity proof. Below we
    # independently re-read the CHUNK, metadata and own source envelope.
    return env["GITHUB_RUN_ID"]


def _folder(
    session: Any, folder_id: str, name: str, expected_parent: str | None = None,
) -> str:
    obj = _get_json(session, FILES + "/" + folder_id, params={
        "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,isAppAuthorized"
    })
    parents = obj.get("parents")
    if (
        obj.get("id") != folder_id or obj.get("name") != name
        or obj.get("mimeType") != FOLDER_MIME or obj.get("trashed") is not False
        or obj.get("shared") is not False or obj.get("ownedByMe") is not True
        or obj.get("isAppAuthorized") is not True
        or type(parents) is not list or len(parents) != 1
        or type(parents[0]) is not str
        or not re.fullmatch(r"[A-Za-z0-9_-]{8,160}", parents[0])
        or (expected_parent is not None and parents != [expected_parent])
    ):
        raise ManifestDenied("MST_242_PRIVATE_FOLDER_CUSTODY_DENIED")
    return parents[0]


def _private_sibling_folders(
    session: Any, chunks_id: str, manifests_id: str,
) -> None:
    root = _folder(session, chunks_id, "CHUNKS")
    _folder(session, manifests_id, "MANIFESTS", expected_parent=root)
    _folder(session, root, "MST_OAUTH_CACHE_V1")
    if chunks_id == manifests_id:
        raise ManifestDenied("MST_242_PRIVATE_FOLDER_CUSTODY_DENIED")


def _chunk_bytes(
    session: Any, env: Mapping[str, str], chunk: PrivateUnpublishedChunk,
    chunks_id: str, run: str,
) -> bytes:
    if type(chunk) is not PrivateUnpublishedChunk:
        raise ManifestDenied("MST_242_CHUNK_RECEIPT_REQUIRED")
    name = _candidate_name(
        chunk.provider, chunk.symbol, chunk.native_tf, run, chunk.sha256
    )
    if [entry["id"] for entry in _list_exact(session, chunks_id, name)] != [chunk.file_id]:
        raise ManifestDenied("MST_242_SOURCE_CHUNK_IDENTITY_NOT_UNIQUE")
    try:
        res = session.get(
            FILES + "/" + chunk.file_id,
            params={"alt": "media"},
            timeout=35, allow_redirects=False,
        )
        if (
            res.status_code != 200
            or type(res.content) is not bytes
            or not 20 <= len(res.content) <= MAX_BYTES
            or len(res.content) != chunk.bytes_verified
            or sha256(res.content).hexdigest() != chunk.sha256
        ):
            raise ManifestDenied("MST_242_CHUNK_MEDIA_REHASH_DENIED")
        raw = res.content
    except ManifestDenied:
        raise
    except Exception:
        raise ManifestDenied("MST_242_CHUNK_MEDIA_REHASH_FAILED") from None
    try:
        provider, symbol, tf, actual_run, digest = _validate_owner_source(env, raw)
    except ChunkDenied:
        raise ManifestDenied("MST_242_CHUNK_SOURCE_ENVELOPE_RECHECK_DENIED") from None
    if (provider, symbol, tf, actual_run, digest) != (
        chunk.provider, chunk.symbol, chunk.native_tf, run, chunk.sha256
    ):
        raise ManifestDenied("MST_242_CHUNK_SOURCE_IDENTITY_MISMATCH")
    version = _file_metadata(
        session, chunk.file_id, chunks_id, name, chunk.sha256, raw,
        chunk.provider, chunk.symbol, chunk.native_tf, run,
    )
    # Two additional independent media GETs and stable version readbacks
    # detect a TOCTOU modification between preparation and manifest creation.
    for _ in range(2):
        _get_media(session, chunk.file_id, raw, chunk.sha256)
        if version != _file_metadata(
            session, chunk.file_id, chunks_id, name, chunk.sha256, raw,
            chunk.provider, chunk.symbol, chunk.native_tf, run,
        ):
            raise ManifestDenied("MST_242_CHUNK_VERSION_CHANGED")
    return raw


def _build_manifest(
    chunk: PrivateUnpublishedChunk, run: str,
) -> bytes:
    # No raw prices or tokens in manifest; contains private Drive ID/hash.
    # "generation" and "previous_head" are deliberately absent. This
    # manifest cannot serve as a published highwater or market Cache head.
    manifest = {
        "schema": SCHEMA,
        "project": "MST",
        "status": "UNPUBLISHED",
        "provider": chunk.provider,
        "symbol": chunk.symbol,
        "native_tf": chunk.native_tf,
        "source_run_id": run,
        "source_chunk_file_id": chunk.file_id,
        "source_chunk_sha256": chunk.sha256,
        "source_chunk_byte_count": chunk.bytes_verified,
        "source_chunk_readback_verified": True,
        "immutable_source_history_attested": False,
        "source_retention_rights_independently_attested": False,
        "source_first_known_clock_attested": False,
        "venue_session_bar_close_attested": False,
        "corporate_action_basis_attested": False,
        "independent_signed_monotone_cas_verified": False,
        "cache_head_published": False,
        "trading_eligible": False,
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                     allow_nan=False, ensure_ascii=True).encode("utf-8")
    if not 100 <= len(raw) <= MAX_MANIFEST_BYTES:
        raise ManifestDenied("MST_242_MANIFEST_BOUNDS_DENIED")
    return raw


def _manifest_props(
    chunk: PrivateUnpublishedChunk, run: str, manifest_sha: str,
) -> dict[str, str]:
    return {
        "mst_unpublished": "true",
        "manifest_sha256": manifest_sha,
        "source_sha256": chunk.sha256,
        "source_provider": chunk.provider,
        "source_symbol": chunk.symbol,
        "source_native_tf": chunk.native_tf,
        "source_run_id": run,
        "signed_cas_verified": "false",
        "market_cache_published": "false",
    }


def _manifest_meta(
    session: Any, manifest_id: str, manifests_id: str, name: str,
    raw: bytes, props: dict[str, str],
) -> str:
    info = _get_json(session, FILES + "/" + manifest_id, params={
        "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,"
                  "isAppAuthorized,size,md5Checksum,version,appProperties",
    })
    version = info.get("version")
    if (
        info.get("id") != manifest_id or info.get("name") != name
        or info.get("mimeType") != MIME or info.get("parents") != [manifests_id]
        or info.get("trashed") is not False or info.get("shared") is not False
        or info.get("ownedByMe") is not True
        or info.get("isAppAuthorized") is not True
        or info.get("size") != str(len(raw))
        or info.get("md5Checksum") != md5(raw).hexdigest()
        or info.get("appProperties") != props or type(version) is not str
        or not re.fullmatch(r"[1-9][0-9]{0,19}", version)
    ):
        raise ManifestDenied("MST_242_MANIFEST_METADATA_CUSTODY_DENIED")
    return version


def stage_unpublished_manifest(
    session: Any, env: Mapping[str, str], chunks_id: str,
    manifests_id: str, source_chunk: PrivateUnpublishedChunk,
) -> UnpublishedManifestReceipt:
    """No publisher. Failures may leave orphan unpublished manifest files.

    Need separate independently signed monotone CAS before any public head.
    """
    run = _verify_guard(env, source_chunk)
    chunks_id, manifests_id = _id(chunks_id), _id(manifests_id)
    if (
        env.get("MST_PRIVATE_CHUNKS_FOLDER_ID") != chunks_id
        or env.get("MST_PRIVATE_MANIFESTS_FOLDER_ID") != manifests_id
        or chunks_id == manifests_id
    ):
        raise ManifestDenied("MST_242_PRIVATE_PARENT_IDS_UNAUTHORIZED")
    _private_sibling_folders(session, chunks_id, manifests_id)
    _chunk_bytes(session, env, source_chunk, chunks_id, run)
    raw = _build_manifest(source_chunk, run)
    digest = sha256(raw).hexdigest()
    name = (DIGEST_TAG + "_" + source_chunk.provider + "_" + source_chunk.symbol
            + "_" + source_chunk.native_tf + "_" + run + "_" + digest + ".json")
    if _list_exact(session, manifests_id, name):
        raise ManifestDenied("MST_242_MANIFEST_ALREADY_EXISTS")
    props = _manifest_props(source_chunk, run, digest)
    meta = {
        "name": name, "mimeType": MIME, "parents": [manifests_id],
        "appProperties": props,
        "description": "MST PRIVATE UNPUBLISHED MANIFEST; NO CAS/NO TRADE",
    }
    boundary = "mstmanifest" + secrets.token_hex(16)
    try:
        res = session.post(
            UPLOAD, params={"uploadType": "multipart",
                            "fields": "id,name,mimeType,parents,trashed"},
            headers={"Content-Type": "multipart/related; boundary=" + boundary},
            data=_multipart(meta, raw, boundary),
            timeout=35, allow_redirects=False,
        )
    except Exception:
        raise ManifestDenied("MST_242_MANIFEST_UPLOAD_AMBIGUOUS_ORPHAN_POSSIBLE") from None
    reply = _json_reply(res, (200, 201))
    identifier = _id(reply.get("id"))
    if (
        reply.get("name") != name or reply.get("mimeType") != MIME
        or reply.get("parents") != [manifests_id]
        or reply.get("trashed") is not False
    ):
        raise ManifestDenied("MST_242_MANIFEST_UPLOAD_IDENTITY_MISMATCH")
    version = _manifest_meta(session, identifier, manifests_id, name, raw, props)
    for _ in range(2):
        _get_media(session, identifier, raw, digest)
        if version != _manifest_meta(session, identifier, manifests_id, name,
                                      raw, props):
            raise ManifestDenied("MST_242_MANIFEST_VERSION_MUTATED")
    if [entry["id"] for entry in _list_exact(session, manifests_id, name)] != [identifier]:
        raise ManifestDenied("MST_242_MANIFEST_NAME_RACE_OR_MISSING")
    # Final CHUNK identity reread detects a late deletion/duplicate, but
    # cannot prove Google Drive eventual/global uniqueness or atomicity.
    chunk_name = _candidate_name(
        source_chunk.provider, source_chunk.symbol,
        source_chunk.native_tf, run, source_chunk.sha256,
    )
    if [entry["id"] for entry in _list_exact(session, chunks_id, chunk_name)] != [
        source_chunk.file_id
    ]:
        raise ManifestDenied("MST_242_CHUNK_CHANGED_AFTER_MANIFEST_UPLOAD")
    return UnpublishedManifestReceipt(
        manifest_file_id=identifier,
        manifest_sha256=digest,
        source_sha256=source_chunk.sha256,
        provider=source_chunk.provider,
        symbol=source_chunk.symbol,
        native_tf=source_chunk.native_tf,
    )
