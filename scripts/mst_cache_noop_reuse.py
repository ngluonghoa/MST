"""Strict no-op reuse of a previously verified private source candidate.

Call ONLY after the provider-specific complete candidate discovery, exact
private metadata/owner/parent, 2 media readbacks and positive-overlap delta.
This is an optimization, NOT source finality or signed Cache publication.
"""
from __future__ import annotations

from typing import Any, Mapping
import re


def verified_unchanged_receipt(
    prior_link: Mapping[str, Any] | None, *,
    provider: str, tf: str, observed_rows: int,
) -> dict[str, Any] | None:
    """Skip identical native OHLCV; rolling window exits do NOT delete history.

    Reject malformed summaries even though they are supplied by the strict
    provider verifier. A missing prior or actual added/revised bar means the
    caller must continue the ordinary append-only source staging path.
    """
    if prior_link is None:
        return None
    if provider not in ("SSI", "DNSE") or tf not in ("M5","M15","M30","H1","D1"):
        raise ValueError("MST_CACHE_REUSE_SOURCE_SCOPE_INVALID")
    if type(observed_rows) is not int or not 1 <= observed_rows <= 2048:
        raise ValueError("MST_CACHE_REUSE_ROW_COUNT_INVALID")
    if type(prior_link) is not dict:
        raise ValueError("MST_CACHE_REUSE_PREDECESSOR_INVALID")
    proof=prior_link.get("delta")
    if type(proof) is not dict:
        raise ValueError("MST_CACHE_REUSE_DELTA_REQUIRED")
    expected = {
        ("SSI","M5"):("mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
                       "mst.cloud.ssi_native_incremental_delta.v0.1",
                       "SSI_FASTCONNECT_V3_MARKET_DATA","source_native_tf"),
        ("SSI","M15"):("mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
                       "mst.cloud.ssi_native_incremental_delta.v0.1",
                       "SSI_FASTCONNECT_V3_MARKET_DATA","source_native_tf"),
        ("SSI","M30"):("mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
                       "mst.cloud.ssi_native_incremental_delta.v0.1",
                       "SSI_FASTCONNECT_V3_MARKET_DATA","source_native_tf"),
        ("SSI","H1"):("mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
                       "mst.cloud.ssi_native_incremental_delta.v0.1",
                       "SSI_FASTCONNECT_V3_MARKET_DATA","source_native_tf"),
        ("SSI","D1"):("mst.cloud.ssi_native_prior_source_delta_candidate.v0.1",
                       "mst.cloud.ssi_native_incremental_delta.v0.1",
                       "SSI_FASTCONNECT_V3_MARKET_DATA","source_native_tf"),
        ("DNSE","D1"):("mst.cloud.dnse_d1_prior_source_delta_candidate.v0.1",
                        "mst.private_d1_source_delta_plan.v1",
                        "DNSE","timeframe"),
        **{("DNSE",timeframe):(
            "mst.cloud.dnse_native_prior_source_delta_candidate.v0.1",
            "mst.cloud.dnse_intraday_incremental_delta.v0.1",
            "DNSE","source_native_tf",
        ) for timeframe in ("M5","M15","M30","H1")},
    }
    chain_schema, delta_schema, delta_provider, tf_field=expected[(provider,tf)]
    if (prior_link.get("schema") != chain_schema
            or proof.get("schema") != delta_schema
            or proof.get("provider") != delta_provider
            or proof.get(tf_field) != tf
            or type(proof.get("symbol")) is not str
            or not re.fullmatch(r"[A-Z]{3}",proof["symbol"])):
        raise ValueError("MST_CACHE_REUSE_CROSS_PROVIDER_OR_TF_DRIFT")
    added=proof.get("added")
    revised=proof.get("revised")
    exited=proof.get("window_exited_not_deleted")
    same=proof.get("unchanged_overlap")
    if (type(added) is not list or type(revised) is not list
            or type(exited) is not list or type(same) is not int
            or not 0 <= same <= observed_rows):
        raise ValueError("MST_CACHE_REUSE_DELTA_SHAPE_INVALID")
    if added or revised:
        return None
    if same != observed_rows:
        raise ValueError("MST_CACHE_REUSE_OVERLAP_INCOMPLETE")
    if (prior_link.get("eligible_for_signals") is not False
            or type(prior_link.get("prior_private_file_id")) is not str
            or not prior_link["prior_private_file_id"]
            or type(prior_link.get("prior_source_sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}",prior_link["prior_source_sha256"])):
        raise ValueError("MST_CACHE_REUSE_PRIOR_PROOF_INVALID")
    return {
        "unpublished_private_source_document_stored":False,
        "source_noop_reused_verified_prior":True,
        "source_provider":provider,
        "source_native_tf":tf,
        "source_rows_observed":observed_rows,
        "source_delta_linked_to_prior_private_d1":provider=="DNSE" and tf=="D1",
        "source_delta_linked_to_prior_private_native_tf":(
            provider=="SSI" or tf!="D1"
        ),
        "source_delta_added_rows":0,
        "source_delta_revised_rows":0,
        "source_delta_window_exited_not_deleted":len(exited),
        "source_unchanged_overlap":same,
        "previous_candidate_kept_unmodified":True,
        "prior_verified_with_two_private_media_readbacks":True,
        "stored_object_count":0,
        "not_a_cache_publish_commit":True,
        "independent_atomic_cas_ready":False,
        "signals_and_trading_eligible":False,
        "trading_or_broker_calls":0,
    }
