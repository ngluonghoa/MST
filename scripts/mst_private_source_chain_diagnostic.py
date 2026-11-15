"""§195 Bounded, read-only private source candidate lineage verifier.

This operates ONLY on a complete, caller-supplied private Drive snapshot plus
two independently *supplied* pin values. It does not fetch a trustworthy
checkpoint, verify a signature, mutate Drive, publish a Cache head or enable
signals. An attacker able to replace both the snapshot and the supplied pins
can forge a new self-consistent chain. Independent signed/highwater/CAS
infrastructure remains a hard NO-GO gate.
"""
from __future__ import annotations

from hashlib import md5, sha256
import json
import re
from typing import Any, Mapping

from scripts.mst_native_source_fingerprint import native_canonical_sha256
from scripts.mst_private_candidate_identity import (
    verify_new_candidate_identity,
)
from scripts.mst_private_source_ingress_binding import (
    verify_archived_source_binding,
)

DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN = re.compile(r"[1-9][0-9]{5,19}\Z")
SYMBOL = re.compile(r"[A-Z]{3}\Z")
TFS = frozenset(("D1", "M5", "M15", "M30", "H1"))
PROVIDERS = {
    "DNSE": "DNSE_OFFICIAL_OPENAPI",
    "SSI": "SSI_FASTCONNECT_V3_MARKET_DATA",
}
MAX_RECORDS = 128
MAX_BODY_BYTES = 1_500_000
ANCHOR_KEYS = frozenset((
    "provider","symbol","native_tf","file_id","run_id","source_sha256",
))


class LineageDenied(ValueError):
    """Failures use only fixed codes; never expose rows or tokens."""


def _id(value: Any) -> bool:
    return type(value) is str and DRIVE_ID.fullmatch(value) is not None


def _sha(value: Any) -> bool:
    return type(value) is str and SHA.fullmatch(value) is not None


def _run(value: Any) -> bool:
    return type(value) is str and RUN.fullmatch(value) is not None


def _proof(proof: Any, label: str) -> Mapping[str, Any]:
    if (type(proof) is not dict or set(proof) != ANCHOR_KEYS
            or proof["provider"] not in PROVIDERS
            or type(proof["symbol"]) is not str
            or SYMBOL.fullmatch(proof["symbol"]) is None
            or proof["native_tf"] not in TFS
            or not _id(proof["file_id"])
            or not _run(proof["run_id"])
            or not _sha(proof["source_sha256"])):
        raise LineageDenied("MST_LINEAGE_"+label+"_PIN_INVALID")
    return proof


def _record(record: Any, *, parent: str, provider: str,
            symbol: str, tf: str) -> dict[str, Any]:
    """Recheck exact bytes+metadata+native and optional ingress receipt.

    Inputs must already originate from two exact private Drive media reads and
    independent private owner/ACL/census preflight by the future caller.
    """
    if (type(record) is not dict
            or set(record) != {"file_id","metadata","body"}
            or not _id(record["file_id"])
            or type(record["body"]) is not bytes
            or not 0 < len(record["body"]) <= MAX_BODY_BYTES
            or type(record["metadata"]) is not dict):
        raise LineageDenied("MST_LINEAGE_RECORD_SHAPE_INVALID")
    info, body = record["metadata"], record["body"]
    props = info.get("appProperties")
    if (type(props) is not dict
            or info.get("id") != record["file_id"]
            or info.get("mimeType") != "application/json"
            or info.get("parents") != [parent]
            or info.get("trashed") is not False
            or info.get("shared") is not False
            or info.get("ownedByMe") is not True
            or info.get("isAppAuthorized") is not True
            or info.get("size") != str(len(body))
            or info.get("md5Checksum") != md5(body).hexdigest()
            or props.get("source_sha256") != sha256(body).hexdigest()
            or props.get("mst_unpublished") != "true"
            or not _run(props.get("source_run_id"))):
        raise LineageDenied("MST_LINEAGE_PRIVATE_RECORD_INTEGRITY_INVALID")
    try:
        archive = json.loads(body)
        # Synthetic record must be fully canonical and carry unambiguous body.
        canonical = json.dumps(
            archive,sort_keys=True,separators=(",",":"),
            ensure_ascii=True,allow_nan=False,
        ).encode("utf-8")
        if canonical != body:
            raise ValueError("not canonical")
        if not verify_new_candidate_identity(archive,info):
            raise ValueError("legacy cannot anchor new source chain")
        if (archive["source"] != PROVIDERS[provider]
                or archive["symbol"] != symbol
                or archive["source_native_tf"] != tf
                or native_canonical_sha256(
                    provider,symbol,tf,archive["raw_native"],
                ) != archive["native_canonical_sha256"]):
            raise ValueError("wrong native identity")
        verify_archived_source_binding(archive,props)
    except (ValueError,TypeError,KeyError,OverflowError):
        raise LineageDenied("MST_LINEAGE_RECORD_SEMANTICS_INVALID") from None
    return {
        "file_id":record["file_id"],
        "run_id":props["source_run_id"],
        "source_sha256":sha256(body).hexdigest(),
        "link":archive.get("prior_source_incremental_delta"),
    }


def verify_private_source_chain(
    records: Any, *,
    parent: str,
    floor_pin: Mapping[str, Any],
    expected_head_pin: Mapping[str, Any],
    complete_census_supplied: bool,
) -> dict[str, Any]:
    """Verify complete linear history between two out-of-band supplied pins.

    Refuses missing intermediate files, forks, duplicate run IDs, stale heads,
    shifted provider/TF, broken prior SHA pointers, and a missing HEAD pin.
    It does NOT authenticate either pin or the completeness claim. Both must
    later come from a truly independent signed, monotone source to be trusted.
    """
    floor=_proof(floor_pin,"FLOOR")
    head=_proof(expected_head_pin,"HEAD")
    if (complete_census_supplied is not True
            or not _id(parent)
            or any(floor[k] != head[k]
                   for k in ("provider","symbol","native_tf"))
            or int(head["run_id"]) < int(floor["run_id"])):
        raise LineageDenied("MST_LINEAGE_SCOPE_OR_CENSUS_UNVERIFIED")
    if (type(records) is not list or not 1 <= len(records) <= MAX_RECORDS
            or head["file_id"]==floor["file_id"]
            and head != floor):
        raise LineageDenied("MST_LINEAGE_RECORD_SET_INVALID")
    by_id: dict[str,dict[str,Any]]={}
    by_run: set[str]=set()
    for rec in records:
        item=_record(rec,parent=parent,provider=floor["provider"],
                     symbol=floor["symbol"],tf=floor["native_tf"])
        if item["file_id"] in by_id or item["run_id"] in by_run:
            raise LineageDenied("MST_LINEAGE_DUPLICATE_FILE_OR_RUN")
        by_id[item["file_id"]]=item
        by_run.add(item["run_id"])
    root=by_id.get(floor["file_id"])
    tip=by_id.get(head["file_id"])
    for actual,pin,code in (
        (root,floor,"FLOOR"),
        (tip,head,"HEAD"),
    ):
        if (actual is None
                or any(actual[k] != pin[k]
                       for k in ("file_id","run_id","source_sha256"))):
            raise LineageDenied("MST_LINEAGE_"+code+"_PIN_MISMATCH")
    children: dict[str,str]={}
    for child in by_id.values():
        if child["file_id"] == floor["file_id"]:
            # Trusted floor starts the observed segment. It may have
            # older predecessors not included in this bounded audit.
            continue
        link=child["link"]
        if (type(link) is not dict
                or not _id(link.get("prior_private_file_id"))
                or not _sha(link.get("prior_source_sha256"))):
            raise LineageDenied("MST_LINEAGE_PREDECESSOR_REQUIRED")
        pid=link["prior_private_file_id"]
        predecessor=by_id.get(pid)
        if (predecessor is None
                or predecessor["source_sha256"] != link["prior_source_sha256"]
                or int(predecessor["run_id"]) >= int(child["run_id"])):
            raise LineageDenied("MST_LINEAGE_BROKEN_OR_REVERSED_EDGE")
        if pid in children:
            raise LineageDenied("MST_LINEAGE_FORK_NOT_A_LINEAR_HISTORY")
        children[pid]=child["file_id"]
    visited={floor["file_id"]}
    current=floor["file_id"]
    steps=0
    while current in children:
        current=children[current]
        if current in visited:
            raise LineageDenied("MST_LINEAGE_CYCLE_INVALID")
        visited.add(current)
        steps+=1
    if current != head["file_id"] or visited != set(by_id):
        raise LineageDenied("MST_LINEAGE_GAP_OR_UNANCHORED_BRANCH")
    return {
        "schema":"mst.private.source_chain_diagnostic.v0.1",
        "provider":floor["provider"],
        "symbol":floor["symbol"],
        "native_tf":floor["native_tf"],
        "candidate_count":len(visited),
        "linked_edges_verified":steps,
        "floor_and_expected_head_pins_matched":True,
        "all_supplied_records_accounted_for":True,
        "external_pin_signature_verified":False,
        "drive_census_independently_verified":False,
        "independent_monotone_highwater_verified":False,
        "signed_atomic_publish_cas_verified":False,
        "source_finality_verified":False,
        "signal_eligible":False,
        "cache_published":False,
    }
