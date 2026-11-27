"""MST private Cloud D1 snapshot/manifest adapter regression contract.

The snapshot fields mirror the REAL PRIVATE Google Docs schema, but values,
document IDs, symbols and prices below are invented TEST-ONLY data.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest

from scripts.m3_private_drive_d1_refresh import (
    parse_google_doc_json, read_private_d1_document, decide_private_d1_refresh,
    provider_from_endpoint,
)
from scripts.m3_source_native_ohlcv_delta import DailyEndpoint

SYMS = ("AAA", "BBB", "CCC")
PROVIDERS = ("SSI", "DNSE", "VCBS")
ENDPOINTS = {
    "SSI": ("MCP_SSI.marketdata_list_stock_daily_data", "SSI"),
    "DNSE": ("MCP_DNSE.price_get_history", "DNSE"),
    "VCBS": ("MCP_VCBS.vcbs_get_history", "VCBS"),
}


def row(provider, symbol, *, day="2026-11-12", close=102, volume=200):
    if provider == "SSI":
        d,m,y=day.split("-")[2],day.split("-")[1],day.split("-")[0]
        return {"symbol":symbol,"trading_date":f"{d}/{m}/{y}",
                "open":"100","high":"105","low":"99","close":str(close),
                "volume":str(volume)}
    if provider == "DNSE":
        # Synthetic date is intentionally fixed to the known Unix D1 label.
        return {"source_unix_seconds":1794448800,"date_utc":"2026-11-12",
                "open":100,"high":105,"low":99,"close":close,"volume":volume}
    return {"tradingDate":day,"openPrice":100,"highPrice":105,
            "lowPrice":99,"closePrice":close,"volume":volume,
            "adjClosePrice":close,"adjFactor":1,"price":close,
            "trading_value_scope":None}


def doc(provider, symbol, *, at="2026-11-12T10:00:00Z", rows=None):
    if rows is None:
        rows=[row(provider,symbol)]
    return {"schema":"mst.mcp.d1.private_drive_snapshot.v0.2",
            "project":"MST","symbol":symbol,"provider":provider,
            "timeframe":"D1","source_tool":ENDPOINTS[provider][0],
            "capture_utc":at,
            "source_row_count":len(rows),"retained_row_count":len(rows),
            "rows":deepcopy(rows)}


def docid(provider,symbol):
    return "SYN_PrivateDocs_" + provider + "_" + symbol + "_0123456789"


def batch():
    manifest={"schema":"mst.cloud.drive.private.mcp_d1_capture_manifest.v0.2",
              "project":"MST","source_partition_count":9,
              "snapshots":[{"provider":p,"symbol":s,"timeframe":"D1",
                            "source_snapshot_doc_id":docid(p,s),
                            "persisted_rows":1,"readback_verified":True,
                            "stored_in_private_folder":True}
                           for s in SYMS for p in PROVIDERS]}
    prior={docid(p,s):doc(p,s) for s in SYMS for p in PROVIDERS}
    now={(p,s):doc(p,s,at="2026-11-12T11:00:00Z")
         for s in SYMS for p in PROVIDERS}
    return manifest,prior,now


class PrivateDriveD1AdapterTests(unittest.TestCase):
    def test_real_google_docs_utf8_bom_is_parsed(self):
        d=doc("SSI","AAA")
        x=parse_google_doc_json("\ufeff"+json.dumps(d))
        self.assertEqual(x["symbol"],"AAA")

    def test_raw_crlf_json_works(self):
        s=json.dumps(doc("DNSE","AAA"),indent=2).replace("\n","\r\n")
        self.assertEqual(parse_google_doc_json("\ufeff"+s)["provider"],"DNSE")

    def test_duplicate_json_field_refused(self):
        with self.assertRaises(ValueError):
            parse_google_doc_json('{"schema":"ok","schema":"shadow"}')

    def test_nonfinite_json_refused(self):
        with self.assertRaises(ValueError):
            parse_google_doc_json('{"value":NaN}')

    def test_json_array_refused(self):
        with self.assertRaises(ValueError):
            parse_google_doc_json('[]')

    def test_json_trailing_junk_refused(self):
        with self.assertRaises(ValueError):
            parse_google_doc_json('{"a":1} garbage')

    def test_invalid_json_type_refused(self):
        with self.assertRaises(TypeError):
            parse_google_doc_json({"rows":[]})

    def test_ssi_native_snapshot_read(self):
        d=read_private_d1_document(doc("SSI","AAA"),document_id=docid("SSI","AAA"))
        self.assertEqual(d.endpoint,DailyEndpoint.SSI_COMPACT)
        self.assertEqual(d.symbol,"AAA")
        self.assertEqual(d.native.unit,"VND_per_share")
        self.assertTrue(d.full_source_result_observed)

    def test_dnse_native_snapshot_read(self):
        d=read_private_d1_document(doc("DNSE","AAA"),document_id=docid("DNSE","AAA"))
        self.assertEqual(d.endpoint,DailyEndpoint.DNSE_CONNECTED_DAY)
        self.assertEqual(d.native.unit,"native_unverified")

    def test_vcbs_native_snapshot_read(self):
        d=read_private_d1_document(doc("VCBS","AAA"),document_id=docid("VCBS","AAA"))
        self.assertEqual(d.endpoint,DailyEndpoint.VCBS_DAILY)
        self.assertEqual(d.native.price_basis,"VCBS_adjusted_requested")

    def test_ssi_capture_time_utc_variant(self):
        d=doc("SSI","AAA")
        d["capture_time_utc"]=d.pop("capture_utc")
        self.assertEqual(read_private_d1_document(d,document_id=docid("SSI","AAA")).symbol,"AAA")

    def test_missing_capture_clock_denied(self):
        d=doc("SSI","AAA")
        d.pop("capture_utc")
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_multiple_capture_clocks_denied(self):
        d=doc("SSI","AAA")
        d["capture_time_utc"]=d["capture_utc"]
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_non_utc_receipt_denied(self):
        d=doc("SSI","AAA",at="2026-11-12T17:00:00+07:00")
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_wrong_project_denied(self):
        d=doc("SSI","AAA");d["project"]="FOREX"
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_unrecognized_provider_endpoint_denied(self):
        d=doc("SSI","AAA");d["source_tool"]="MCP_SSI.marketdata_list_stock_infor"
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_wrong_symbol_inside_ssi_row_denied(self):
        d=doc("SSI","AAA");d["rows"][0]["symbol"]="BBB"
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_retained_row_mismatch_denied(self):
        d=doc("SSI","AAA");d["retained_row_count"]=2
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_source_cannot_underreport_retained(self):
        d=doc("SSI","AAA");d["source_row_count"]=0
        with self.assertRaises(ValueError):
            read_private_d1_document(d,document_id=docid("SSI","AAA"))

    def test_detect_truncated_source_window(self):
        d=doc("SSI","AAA");d["source_row_count"]=2
        x=read_private_d1_document(d,document_id=docid("SSI","AAA"))
        self.assertFalse(x.full_source_result_observed)

    def test_bad_doc_id_denied(self):
        with self.assertRaises(ValueError):
            read_private_d1_document(doc("SSI","AAA"),document_id="guess")

    def test_batch_9_source_unchanged_receipt_only(self):
        manifest,prior,now=batch()
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["partition_count"],9)
        self.assertEqual(d["no_change_partition_count"],9)
        self.assertEqual(d["requires_new_private_version_count"],0)
        self.assertEqual(d["quarantined_partition_count"],0)
        self.assertFalse(d["all_private_cloud_receipts_written"])
        self.assertFalse(d["signal_eligible"])
        self.assertTrue(all(p["comparison"]["unchanged_rows"]==1 for p in d["partitions"]))

    def test_one_price_only_change_triggers_private_version(self):
        manifest,prior,now=batch()
        now[("SSI","AAA")]["rows"][0]["close"]="103"
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["requires_new_private_version_count"],1)
        item=next(p for p in d["partitions"] if p["provider"]=="SSI" and p["symbol"]=="AAA")
        self.assertEqual(item["comparison"]["numeric_ohlcv_revisions"][0]["changed_fields"],["close"])
        self.assertEqual(item["decision"],"REQUIRE_NEW_PRIVATE_SOURCE_VERSION_AND_DEPENDENCY_REBUILD")
        self.assertFalse(item["real_cache_v2_writer_executed"])

    def test_vcbs_adjustment_only_revision_invalidates(self):
        manifest,prior,now=batch()
        now[("VCBS","BBB")]["rows"][0]["adjFactor"]=0.98
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["requires_new_private_version_count"],1)

    def test_vcbs_absent_null_metadata_is_receipt_only(self):
        manifest,prior,now=batch()
        del now[("VCBS","CCC")]["rows"][0]["trading_value_scope"]
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["metadata_only_partition_count"],1)
        self.assertEqual(d["requires_new_private_version_count"],0)

    def test_dnse_changed_start_label_invalidates(self):
        manifest,prior,now=batch()
        now[("DNSE","CCC")]["rows"][0]["source_unix_seconds"]+=60
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["requires_new_private_version_count"],1)
        item=next(p for p in d["partitions"] if p["provider"]=="DNSE" and p["symbol"]=="CCC")
        self.assertEqual(item["comparison"]["source_candle_start_timestamp_revisions"][0]["day"],"2026-11-12")

    def test_source_truncation_quarantines_not_delete(self):
        manifest,prior,now=batch()
        now[("SSI","AAA")]["source_row_count"]=2
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["quarantined_partition_count"],1)
        self.assertFalse(d["production_authorized"])

    def test_scope_loss_quarantines_not_delete(self):
        manifest,prior,now=batch()
        old=prior[docid("SSI","AAA")]
        old["rows"].insert(0,row("SSI","AAA",day="2026-11-11"))
        old["source_row_count"]=2;old["retained_row_count"]=2
        next(r for r in manifest["snapshots"] if
             r["provider"]=="SSI" and r["symbol"]=="AAA")["persisted_rows"]=2
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["quarantined_partition_count"],1)
        item=next(p for p in d["partitions"] if p["provider"]=="SSI" and p["symbol"]=="AAA")
        self.assertEqual(item["comparison"]["missing_prior_day_labels_UNVERIFIED"],["2026-11-11"])
        self.assertFalse(item["comparison"]["deletion_authorized"])

    def test_missing_candidate_partition_refused(self):
        manifest,prior,now=batch()
        del now[("SSI","AAA")]
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_missing_baseline_doc_refused(self):
        manifest,prior,now=batch()
        del prior[docid("SSI","AAA")]
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_manifest_source_id_mismatch_refused(self):
        manifest,prior,now=batch()
        manifest["snapshots"][0]["source_snapshot_doc_id"]=docid("VCBS","BBB")
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_manifest_partition_count_wrong_refused(self):
        manifest,prior,now=batch()
        manifest["source_partition_count"]=8
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_manifest_duplicate_source_partition_refused(self):
        manifest,prior,now=batch()
        manifest["snapshots"][1]["symbol"]="AAA"
        manifest["snapshots"][1]["provider"]="SSI"
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_candidate_wrong_endpoint_refused(self):
        manifest,prior,now=batch()
        now[("SSI","AAA")]["source_tool"]="MCP_SSI.marketdata_list_daily_stock_infor"
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_candidate_nonmonotone_clock_denied(self):
        manifest,prior,now=batch()
        now[("DNSE","AAA")]["capture_utc"]="2026-11-12T09:00:00Z"
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_mixed_changes_are_not_applied_during_decision(self):
        manifest,prior,now=batch()
        original=deepcopy(prior)
        now[("SSI","AAA")]["rows"][0]["close"]="103"
        now[("VCBS","BBB")]["rows"][0]["adjFactor"]=0.95
        now[("SSI","CCC")]["source_row_count"]=2
        d=decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["requires_new_private_version_count"],2)
        self.assertEqual(d["quarantined_partition_count"],1)
        self.assertEqual(prior,original)
        self.assertFalse(d["approved_automatic_cloud_publisher"])

    def test_nonexistent_doc_id_cannot_be_invented_by_decision(self):
        manifest,prior,now=batch()
        out=decide_private_d1_refresh(manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertTrue(all("new_source_doc_id" not in p for p in out["partitions"]))
        self.assertFalse(out["all_actual_new_private_source_versions_created"])

    def test_provider_namespace_from_endpoint(self):
        self.assertEqual(provider_from_endpoint(DailyEndpoint.SSI_DETAILED),"SSI")
        self.assertEqual(provider_from_endpoint(DailyEndpoint.DNSE_CONNECTED_DAY),"DNSE")



    def test_new_daily_session_is_a_new_private_version_not_incomplete_scope(self):
        manifest,prior,now=batch()
        current=now[("SSI","AAA")]
        current["rows"].insert(0,row("SSI","AAA",day="2026-11-11"))
        current["retained_row_count"]=2
        current["source_row_count"]=2
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        self.assertEqual(d["requires_new_private_version_count"],1)
        self.assertEqual(d["quarantined_partition_count"],0)
        item=next(x for x in d["partitions"] if x["provider"]=="SSI" and x["symbol"]=="AAA")
        self.assertEqual(item["decision"],
                         "REQUIRE_NEW_PRIVATE_SOURCE_VERSION_AND_DEPENDENCY_REBUILD")
        self.assertEqual(item["comparison"]["added_day_labels"],["2026-11-11"])
        self.assertFalse(d["all_actual_new_private_source_versions_created"])

    def test_manifest_prior_source_count_disagreement_refused(self):
        manifest,prior,now=batch()
        manifest["snapshots"][0]["persisted_rows"]=5
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(
                manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_manifest_without_private_readback_marker_refused(self):
        manifest,prior,now=batch()
        manifest["snapshots"][0]["readback_verified"]=False
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(
                manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_manifest_without_private_folder_marker_refused(self):
        manifest,prior,now=batch()
        manifest["snapshots"][0]["stored_in_private_folder"]=False
        with self.assertRaises(ValueError):
            decide_private_d1_refresh(
                manifest=manifest,prior_documents=prior,candidate_documents=now)

    def test_new_source_first_day_with_old_unchanged_is_not_retroactive_first_known(self):
        manifest,prior,now=batch()
        current=now[("SSI","BBB")]
        current["rows"].insert(0,row("SSI","BBB",day="2026-11-11"))
        current["source_row_count"]=2
        current["retained_row_count"]=2
        d=decide_private_d1_refresh(
            manifest=manifest,prior_documents=prior,candidate_documents=now)
        item=next(x for x in d["partitions"] if x["provider"]=="SSI" and x["symbol"]=="BBB")
        self.assertEqual(item["comparison"]["overlapping_rows"],1)
        self.assertEqual(item["comparison"]["numeric_ohlcv_revisions"],[])
        self.assertFalse(item["comparison"]["source_first_known_authenticated"])
        self.assertFalse(item["issuer_closed_verified"])

if __name__=="__main__":
    unittest.main()
