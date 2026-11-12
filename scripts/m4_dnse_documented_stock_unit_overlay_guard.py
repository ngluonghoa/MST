"""MST M4: source-unit documentation overlay CONTRACT, not a production data reader.

This module validates a caller-supplied metadata-only overlay that references
official DNSE OpenAPI documentation and previously observed native Docs IDs.
GitHub CI uses only fictional source/manifest IDs and symbols.

Critical split:
  1. Official DNSE STOCK market-price guidance says 1000 VND per source unit.
  2. The /price/ohlc schema documents numeric fields but not a specific
     adjusted/unadjusted price basis or authenticated connected MCP API version.
  3. The three older DNSE source snapshots and their manifests disagree
     in UNVERIFIED unit token labels; these labels remain untouched.
NONE of (1) or numerical x1000 coincidence authorizes (2) or changing (3).
No network, GCP, Drive, vendor authentication, source prices or cache writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SCHEMA="mst.m4.dnse_external_source_unit_evidence_overlay.v0.1"
STATUS="DOCUMENTED_STOCK_UNIT_GENERAL_ONLY_DNSE_NATIVE_MCP_OHLC_UNATTESTED_PRODUCTION_NO_GO"
DOCUMENTED_URLS=(
    "https://developers.dnse.com.vn/docs/guide/intro/trading-flow/",
    "https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/",
    "https://developers.dnse.com.vn/docs/guide/market-data/connect/",
    "https://developers.dnse.com.vn/docs/guide/versioning/api/",
)
KNOWN_CONFLICTS={
    ("source_native_DNSE_units_unverified","source_native_units_unverified"),
    ("source_native_scale_unverified","native_scale_unverified"),
}
DENY_SOURCE_CLAIMS=(
    "connected_MCP_DNSE_history_price_unit_verified_by_provider_issuer",
    "connected_MCP_DNSE_history_adjustment_basis_verified_by_provider_issuer",
    "connected_MCP_DNSE_API_effective_version_verified",
    "historical_OHLC_trusted_minute_bar_close_verified",
    "vendor_cloud_storage_and_processing_rights_verified",
    "provider_issued_signed_correction_first_known_verified",
    "official_historical_VN_venue_calendar_verified",
)
DENY_RELEASE_CLAIMS=(
    "price_scale_applied_to_source_files",
    "price_scale_approved_for_MST_signals_or_cache",
    "source_manifest_mutated",
    "original_source_docs_mutated",
    "automatic_cloud_cache_refresh_enabled",
    "production_cloud_cache_writer_enabled",
    "trading_authorized",
)
DENY_WIF_CLAIMS=(
    "exists_on_protected_main",
    "default_branch_workflow_dispatch_executable_now",
    "github_repo_variables_inspected",
    "gcp_project_pool_provider_and_service_account_inspected",
    "owner_private_fpt_folder_metadata_shared",
    "owner_private_qa_folder_metadata_shared",
    "exact_service_account_google_drive_viewer_grant_verified",
    "real_runner_google_STS_identity_or_Drive_files_get_success",
)

def _exact_false(raw,fields,name):
    if type(raw) is not dict:
        raise ValueError("EXACT_"+name+"_OBJECT_REQUIRED")
    for field in fields:
        if raw.get(field) is not False:
            raise PermissionError(name+"_CANNOT_SELF_APPROVE_"+field)

def check_source_unit_overlay(obj:dict)->dict:
    if type(obj) is not dict or obj.get("schema")!=SCHEMA or obj.get("status")!=STATUS:
        raise ValueError("UNSUPPORTED_EVIDENCE_OVERLAY_OR_STATUS")
    if obj.get("project")!="MST" or obj.get("recorded_local_date")!="2026-11-11":
        raise PermissionError("UNEXPECTED_PROJECT_OR_EVIDENCE_DATE")
    if obj.get("immutable_originals_preserved") is not True:
        raise PermissionError("ORIGINAL_HISTORY_MUST_BE_PRESERVED")
    docs=obj.get("vendor_doc_evidence")
    if type(docs) is not list or len(docs)!=len(DOCUMENTED_URLS) or [d.get("url") for d in docs if type(d) is dict]!=list(DOCUMENTED_URLS):
        raise ValueError("FOUR_ORDERED_OFFICIAL_DNSE_SOURCE_DOCUMENTS_REQUIRED")
    for d in docs:
        if d.get("publisher")!="DNSE official OpenAPI":
            raise PermissionError("UNAUTHENTICATED_DOCUMENT_PUBLISHER_CLAIM")
    if (docs[0].get("documented_unit")!="thousand_VND_for_stock_market_price"
        or type(docs[0].get("unit_scale_to_VND")) is not int
        or docs[0]["unit_scale_to_VND"]!=1000
        or docs[0].get("source_specific_historical_ohlc_unit_claimed") is not False):
        raise PermissionError("GENERAL_STOCK_UNIT_NOT_HISTORICAL_OHLC_ATTESTATION")
    for flag in ("declares_specific_OHLC_price_unit_in_response_schema",
                 "declares_adjustment_basis_in_response_schema"):
        if docs[1].get(flag) is not False:
            raise PermissionError("HISTORICAL_OHLC_SCHEMA_MUST_NOT_BE_PROMOTED_"+flag)
    if docs[1].get("exposes_ohlc_numeric") is not True or docs[1].get("requires_X_API_Key_and_signature") is not True:
        raise PermissionError("OHLC_API_VERSION_AND_AUTH_CONTRACT_MISSING")
    if docs[2].get("native_closed_channel_publicly_documented") is not True or docs[2].get("authenticated_MST_cloud_connection_proven") is not False:
        raise PermissionError("PUBLIC_WS_DOCS_NOT_REAL_CLOSED_STREAM")
    if docs[3].get("historical_MST_connected_MCP_effective_version_authenticated") is not False:
        raise PermissionError("API_VERSION_CANNOT_SELF_ATTEST")
    obs=obj.get("real_read_only_evidence")
    if type(obs) is not dict or any(type(obs.get(k)) is not int for k in ("symbol_count","provider_partitions","historical_D1_source_rows_preserved","three_provider_aligned_sessions_per_symbol","diagnostic_SSI_DNSE_1000_scale_OHLC_discrepancy_days")):
        raise ValueError("STRUCTURAL_SOURCE_COUNTS_REQUIRED")
    if (obs["symbol_count"],obs["provider_partitions"],obs["historical_D1_source_rows_preserved"],obs["three_provider_aligned_sessions_per_symbol"],obs["diagnostic_SSI_DNSE_1000_scale_OHLC_discrepancy_days"])!=(3,9,180,20,0):
        raise PermissionError("KNOWN_PRIVATE_D1_OBSERVATION_COUNTS_CHANGED")
    if obs.get("diagnostic_only") is not True or obs.get("real_per_snapshot_source_revision_attested") is not False:
        raise PermissionError("SOURCE_DIAGNOSTICS_NOT_ISSUER_CERTIFICATION")
    _exact_false(obj.get("source_issuer_specific_claims"),DENY_SOURCE_CLAIMS,"ISSUER")
    _exact_false(obj.get("release"),DENY_RELEASE_CLAIMS,"RELEASE")
    if obj["release"].get("price_scale_documented_in_general_stock_API_context") is not True:
        raise ValueError("GENERAL_VENDOR_UNIT_DOCUMENTATION_MISSING")
    wif=obj.get("wif_real_access_readiness")
    _exact_false(wif,DENY_WIF_CLAIMS,"WIF")
    if (wif.get("github_repo")!="ngluonghoa/MST"
        or wif.get("source_locked_main")!="4048f91beaaa3410116d97e35896c8b688384e19"
        or wif.get("draft_pr")!=8
        or wif.get("proposed_manual_workflow")!=".github/workflows/m4-drive-wif-metadata-only-manual.yml"
        or wif.get("exists_on_draft_branch") is not True):
        raise PermissionError("WRONG_GITHUB_DRAFT_WIF_BOUNDARY")
    entries=obj.get("unresolved_metadata_conflicts")
    if type(entries) is not list or len(entries)!=3:
        raise ValueError("THREE_DNSE_UNIT_CONFLICT_ENTRIES_REQUIRED")
    symbols=set()
    for e in entries:
        if type(e) is not dict or e.get("provider")!="DNSE" or e.get("disposition")!="QUARANTINE_NO_CANONICAL_UNIT_PROMOTION":
            raise PermissionError("SOURCE_UNIT_CONFLICT_MUST_QUARANTINE")
        symbol=e.get("symbol")
        if type(symbol) is not str or not re.fullmatch("[A-Z]{3,5}",symbol) or symbol in symbols:
            raise ValueError("THREE_DISTINCT_SOURCE_SYMBOLS_REQUIRED")
        symbols.add(symbol)
        if (e.get("snapshot_unit_token"),e.get("manifest_unit_token")) not in KNOWN_CONFLICTS:
            raise PermissionError("UNKNOWN_DNSE_UNIT_ALIAS_CANNOT_BE_AUTO_CORRECTED")
        for field in ("snapshot_id","manifest_id"):
            val=e.get(field)
            if type(val) is not str or not re.fullmatch("[A-Za-z0-9_-]{15,100}",val):
                raise ValueError("SOURCE_DOC_IDS_MUST_BE_NONEMPTY_OPAQUE_IDS")
    if len(symbols)!=3:
        raise ValueError("EXACT_THREE_SYMBOLS_REQUIRED")
    # No source ID, token, quote, symbol data, dates of candles or vendor
    # values are emitted to public synthetic artifacts.
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "provider":"DNSE",
        "three_snapshot_manifest_unit_aliases_quarantined":len(entries),
        "official_general_stock_unit_in_thousand_vnd_documented":True,
        "historical_ohlc_effective_unit_or_price_basis_issuer_verified":False,
        "historical_connected_mcp_effective_api_version_verified":False,
        "any_source_unit_alias_resolved_for_publishing":False,
        "origin_source_docs_or_manifests_mutated":False,
        "real_drive_or_gcp_connectors_called_by_this_script":False,
        "actual_workflow_dispatch_main_ready":False,
        "dnse_native_ohlc_closed_m5_authenticated":False,
        "licensed_source_cloud_retention_or_production_cache":False,
        "trading_authorized":False,
    }

def fictional_overlay():
    base_docs=[
        {"url":url,"publisher":"DNSE official OpenAPI"}
        for url in DOCUMENTED_URLS
    ]
    base_docs[0].update(documented_unit="thousand_VND_for_stock_market_price",
                        unit_scale_to_VND=1000,source_specific_historical_ohlc_unit_claimed=False)
    base_docs[1].update(exposes_ohlc_numeric=True,
                        declares_specific_OHLC_price_unit_in_response_schema=False,
                        declares_adjustment_basis_in_response_schema=False,
                        requires_X_API_Key_and_signature=True)
    base_docs[2].update(native_closed_channel_publicly_documented=True,
                        authenticated_MST_cloud_connection_proven=False)
    base_docs[3].update(historical_MST_connected_MCP_effective_version_authenticated=False)
    src=[("AAA","source_native_DNSE_units_unverified","source_native_units_unverified"),
         ("BBB","source_native_scale_unverified","native_scale_unverified"),
         ("CCC","source_native_scale_unverified","native_scale_unverified")]
    return {
        "schema":SCHEMA,"status":STATUS,"recorded_local_date":"2026-11-11",
        "project":"MST","immutable_originals_preserved":True,
        "vendor_doc_evidence":base_docs,
        "real_read_only_evidence":{"symbol_count":3,"provider_partitions":9,
        "historical_D1_source_rows_preserved":180,"three_provider_aligned_sessions_per_symbol":20,
        "diagnostic_SSI_DNSE_1000_scale_OHLC_discrepancy_days":0,
        "diagnostic_only":True,"real_per_snapshot_source_revision_attested":False},
        "unresolved_metadata_conflicts":[{"symbol":symbol,"provider":"DNSE",
          "snapshot_id":"fictional_source_ID_"+symbol+"_1234567890",
          "manifest_id":"fictional_manifest_ID_"+symbol+"_1234567890",
          "snapshot_unit_token":before,"manifest_unit_token":after,
          "disposition":"QUARANTINE_NO_CANONICAL_UNIT_PROMOTION"}
          for symbol,before,after in src],
        "wif_real_access_readiness":{"github_repo":"ngluonghoa/MST",
          "source_locked_main":"4048f91beaaa3410116d97e35896c8b688384e19",
          "draft_pr":8,
          "proposed_manual_workflow":".github/workflows/m4-drive-wif-metadata-only-manual.yml",
          "exists_on_draft_branch":True,
          **{name:False for name in DENY_WIF_CLAIMS}},
        "source_issuer_specific_claims":{name:False for name in DENY_SOURCE_CLAIMS},
        "release":{"price_scale_documented_in_general_stock_API_context":True,
          **{name:False for name in DENY_RELEASE_CLAIMS}}
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    report=check_source_unit_overlay(fictional_overlay())
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(json.dumps({"status":STATUS,"synthetic_only":True,
                      "production_allowed":False},sort_keys=True))

if __name__=="__main__":
    main()
