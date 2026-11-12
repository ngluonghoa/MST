"""Cloud-only manual Drive D1 snapshot adapter for MST private source Cache.

Consumes JSON CONTENT of the actual private Google Docs source snapshots
created by an owner-authorized connector read.  This module DOES NOT contact
Google, fetch an endpoint, accept credentials, write a Cloud file, or authorize
a trading signal. It joins the actual private source schema to the existing
M3 source-native OHLCV comparator; no duplicate price-comparison engine.

Intended invocation: Cloud GitHub Actions / an approved private Cloud runner
after a scoped caller has fetched both documents privately. Public CI uses
ONLY invented synthetic JSON. Never supply private source payload as a public
Action artifact, repository commit, issue, workflow input or log.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from typing import Any

from scripts.m3_source_native_ohlcv_delta import (
    DailyEndpoint, NativeD1Snapshot, diff_native_d1_versions,
)

_SCHEMA = "mst.mcp.d1.private_drive_snapshot.v0.2"
_TOOL_ENDPOINT = {
    ("SSI", "MCP_SSI.marketdata_list_stock_daily_data"): DailyEndpoint.SSI_COMPACT,
    ("SSI", "MCP_SSI.marketdata_list_daily_stock_infor"): DailyEndpoint.SSI_DETAILED,
    ("DNSE", "MCP_DNSE.price_get_history"): DailyEndpoint.DNSE_CONNECTED_DAY,
    ("VCBS", "MCP_VCBS.vcbs_get_history"): DailyEndpoint.VCBS_DAILY,
}
_POLICY = {
    DailyEndpoint.SSI_COMPACT: ("SSI_source_native", "VND_per_share"),
    DailyEndpoint.SSI_DETAILED: ("SSI_source_native", "VND_per_share"),
    DailyEndpoint.DNSE_CONNECTED_DAY: ("DNSE_native_unverified", "native_unverified"),
    DailyEndpoint.VCBS_DAILY: ("VCBS_adjusted_requested", "VND_per_share"),
}
_DOC_ID = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


def parse_google_doc_json(content: str) -> dict[str, Any]:
    """Only a full JSON object; tolerate Google Docs' optional leading UTF BOM."""
    if type(content) is not str:
        raise TypeError("PRIVATE_GOOGLE_DOC_JSON_TEXT_REQUIRED")
    raw = content.lstrip("\ufeff").strip()
    if not raw or len(raw) > 16_000_000:
        raise ValueError("NONEMPTY_BOUNDED_JSON_DOCUMENT_REQUIRED")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("DUPLICATE_JSON_FIELD_DENIED")
            output[key] = value
        return output

    def reject_constant(token: str) -> None:
        raise ValueError("NONFINITE_JSON_SOURCE_NUMBER_DENIED")

    doc = json.loads(raw, object_pairs_hook=reject_duplicate,
                     parse_constant=reject_constant)
    if type(doc) is not dict:
        raise ValueError("JSON_OBJECT_SNAPSHOT_REQUIRED")
    return doc


def _utc_receipt(data: dict[str, Any]) -> datetime:
    names = ("capture_utc", "capture_time_utc", "observed_at_utc")
    vals = [data[name] for name in names if name in data]
    if len(vals) != 1 or type(vals[0]) is not str:
        raise ValueError("EXACTLY_ONE_SOURCE_LOCAL_CAPTURE_CLOCK_REQUIRED")
    try:
        time = datetime.fromisoformat(vals[0].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("INVALID_SOURCE_CAPTURE_CLOCK") from None
    if time.tzinfo is None or time.utcoffset() != timedelta(0):
        raise ValueError("UTC_SOURCE_LOCAL_CAPTURE_CLOCK_REQUIRED")
    return time


@dataclass(frozen=True)
class PrivateD1Document:
    source_doc_id: str
    endpoint: DailyEndpoint
    symbol: str
    native: NativeD1Snapshot
    source_rows_reported: int
    exact_rows_retained: int

    @property
    def product_key(self) -> tuple[str, str]:
        return (self.endpoint.value, self.symbol)

    @property
    def full_source_result_observed(self) -> bool:
        return self.source_rows_reported == self.exact_rows_retained


def read_private_d1_document(data: dict[str, Any], *, document_id: str) -> PrivateD1Document:
    """Validate original provider product, date/row schema, local receipt and Doc ID."""
    if type(document_id) is not str or not _DOC_ID.fullmatch(document_id):
        raise ValueError("EXACT_KNOWN_PRIVATE_DOC_ID_REQUIRED")
    if type(data) is not dict or data.get("schema") != _SCHEMA or data.get("project") != "MST":
        raise ValueError("KNOWN_PRIVATE_MST_D1_SCHEMA_REQUIRED")
    key = (data.get("provider"), data.get("source_tool"))
    try:
        endpoint = _TOOL_ENDPOINT[key]
    except (TypeError, KeyError):
        raise ValueError("EXACT_CONNECTED_PROVIDER_ENDPOINT_PRODUCT_REQUIRED") from None
    symbol = data.get("symbol")
    if data.get("timeframe") != "D1":
        raise ValueError("D1_PRIVATE_SNAPSHOT_ONLY")
    rows = data.get("rows")
    if type(rows) is not list or not rows:
        raise ValueError("NONEMPTY_JSON_ROWS_REQUIRED")
    n = data.get("retained_row_count")
    reported = data.get("source_row_count")
    if type(n) is not int or n != len(rows):
        raise ValueError("RETAINED_COUNT_MUST_MATCH_PARSED_ROWS")
    if type(reported) is not int or reported < n:
        raise ValueError("SOURCE_COUNT_CANNOT_BE_SMALLER_THAN_RETAINED")
    if any(type(row) is not dict or
           (endpoint in (DailyEndpoint.SSI_COMPACT,DailyEndpoint.SSI_DETAILED)
            and row.get("symbol") != symbol)
           for row in rows):
        raise ValueError("SOURCE_NATIVE_ROW_AND_SYMBOL_REQUIRED")

    basis, unit = _POLICY[endpoint]
    native = NativeD1Snapshot(
        endpoint=endpoint, symbol=symbol,
        price_basis=basis, unit=unit,
        observed_at_utc=_utc_receipt(data),
        rows=tuple(rows),
    )
    return PrivateD1Document(
        source_doc_id=document_id, endpoint=endpoint, symbol=symbol,
        native=native, source_rows_reported=reported, exact_rows_retained=n,
    )


def _read_manifest(manifest: dict[str, Any]) -> dict[tuple[str, str], str]:
    if type(manifest) is not dict or manifest.get("schema") != "mst.cloud.drive.private.mcp_d1_capture_manifest.v0.2":
        raise ValueError("EXACT_MST_PRIVATE_MANIFEST_SCHEMA_REQUIRED")
    if manifest.get("project") != "MST":
        raise ValueError("MST_PROJECT_REQUIRED")
    sources = manifest.get("snapshots")
    if type(sources) is not list or not sources or len(sources) > 300:
        raise ValueError("BOUNDED_NONEMPTY_SOURCE_MANIFEST_REQUIRED")
    if type(manifest.get("source_partition_count")) is not int or manifest["source_partition_count"] != len(sources):
        raise ValueError("MANIFEST_PARTITION_COUNT_MISMATCH")
    items = {}
    for r in sources:
        if type(r) is not dict or type(r.get("symbol")) is not str or type(r.get("provider")) is not str:
            raise ValueError("BAD_MANIFEST_SOURCE_ENTRY")
        key = (r["provider"],r["symbol"])
        doc_id = r.get("source_snapshot_doc_id")
        if key in items or type(doc_id) is not str or not _DOC_ID.fullmatch(doc_id):
            raise ValueError("DUPLICATE_OR_MALFORMED_SOURCE_MANIFEST_ENTRY")
        if r.get("timeframe") != "D1":
            raise ValueError("D1_MANIFEST_PARTITIONS_ONLY")
        items[key] = doc_id
    return items


def decide_private_d1_refresh(
    *,
    manifest: dict[str, Any],
    prior_documents: dict[str, dict[str, Any]],
    candidate_documents: dict[tuple[str, str], dict[str, Any]],
    prior_source_document_ids: bool = True,
) -> dict[str, Any]:
    """Evaluate ALL source partitions atomically in-memory, emit receipt plan only.

    candidate_documents come from a private Cloud-fetch stage and are not
    persisted by this pure function. A successful decision is NOT an upload.
    """
    if prior_source_document_ids is not True:
        raise PermissionError("MANIFEST_DOCUMENT_PROVENANCE_REQUIRED")
    expected = _read_manifest(manifest)
    if type(prior_documents) is not dict or set(prior_documents) != set(expected.values()):
        raise ValueError("EXACT_PRIOR_DOCUMENT_SET_REQUIRED")
    if type(candidate_documents) is not dict or set(candidate_documents) != set(expected):
        raise ValueError("EXACT_CANDIDATE_SOURCE_PARTITIONS_REQUIRED")
    partitions: list[dict[str, Any]] = []
    for (provider, symbol), prior_doc_id in sorted(expected.items()):
        prior = read_private_d1_document(prior_documents[prior_doc_id], document_id=prior_doc_id)
        if (prior.symbol,prior.endpoint) == (None,None):  # defensive type-independent no-op
            raise ValueError("INVALID_PRIOR_SOURCE")
        if (provider,symbol) != (provider_from_endpoint(prior.endpoint),prior.symbol):
            raise ValueError("MANIFEST_SOURCE_AND_DOCUMENT_IDENTITY_DISAGREE")

        candidate = candidate_documents[(provider,symbol)]
        if type(candidate) is not dict:
            raise TypeError("CANDIDATE_SOURCE_JSON_OBJECT_REQUIRED")
        # Never invent an actual new Google Docs ID before a source version is saved:
        # use the validated prior Doc ID only as a structural validator here.
        current = read_private_d1_document(candidate, document_id=prior_doc_id)
        if current.endpoint != prior.endpoint or current.symbol != prior.symbol:
            raise ValueError("EXACT_PRIOR_VS_CURRENT_SOURCE_IDENTITY_REQUIRED")
        compare = diff_native_d1_versions(prior.native,current.native)
        affected = compare["affected_research_day_labels"]
        missing = compare["missing_prior_day_labels_UNVERIFIED"]
        if not current.full_source_result_observed or missing:
            decision = "QUARANTINE_INCOMPLETE_SOURCE_SCOPE_NO_DELETE"
        elif affected:
            decision = "REQUIRE_NEW_PRIVATE_SOURCE_VERSION_AND_DEPENDENCY_REBUILD"
        elif compare["metadata_changes_only_or_in_addition"]:
            decision = "APPEND_METADATA_RECEIPT_REUSE_SOURCE_PRICE_ROWS"
        else:
            decision = "APPEND_NO_CHANGE_RECEIPT_REUSE_SOURCE_VERSION"
        partitions.append({
            "provider": provider,"symbol":symbol,"endpoint":prior.endpoint.value,
            "source_snapshot_doc_id":prior_doc_id,
            "comparison":compare,"decision":decision,
            "old_rows":prior.exact_rows_retained,"new_rows":current.exact_rows_retained,
            "issuer_closed_verified":False,"source_first_known_authenticated":False,
            "real_cache_v2_writer_executed":False,"signal_eligible":False,
        })
    return {
        "schema":"mst.private.m3.d1-refresh-decision.v1",
        "partition_count":len(partitions),
        "partitions":partitions,
        "requires_new_private_version_count":sum(x["decision"].startswith("REQUIRE_NEW") for x in partitions),
        "quarantined_partition_count":sum(x["decision"].startswith("QUARANTINE") for x in partitions),
        "metadata_only_partition_count":sum(x["decision"].startswith("APPEND_METADATA") for x in partitions),
        "no_change_partition_count":sum(x["decision"].startswith("APPEND_NO_CHANGE") for x in partitions),
        "prior_documents_not_modified":True,
        "all_actual_new_private_source_versions_created":False,
        "all_private_cloud_receipts_written":False,
        "approved_automatic_cloud_publisher":False,
        "signal_eligible":False,
        "production_authorized":False,
    }


def provider_from_endpoint(endpoint: DailyEndpoint) -> str:
    return endpoint.value.split(".",1)[0]
