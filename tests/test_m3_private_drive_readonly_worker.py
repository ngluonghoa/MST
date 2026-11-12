"""Offline scoped Google Drive D1 worker tests: fake OAuth HTTP only.

All content, document names, symbols, IDs and counts are INVENTED fixtures.
Never run live Google Drive APIs or include actual market values in CI.
"""
from copy import deepcopy
import json
import unittest

from scripts import m3_private_drive_readonly_worker as m

PARENT="PrivateFixtureParent_AAAABBBBCCCCDDDDEEEE"
OLD="FakePriorManifest_AAAABBBBCCCCDDDD"
NEW="FakeCurrentManifest_AAAABBBBCCCC"
SSI_OLD="FakeSSI_20261111_AAAABBBBCCCCDDDD"
SSI_NEW="FakeSSI_20261112_AAAABBBBCCCCDDDD"
DNSE="FakeDNSE_20261112_AAAABBBBCCCCDDDD"


def ssi_row(day,volume="200"):
    return {"symbol":"AAA","trading_date":day,"open":"100","high":"104","low":"98",
            "close":"101","volume":volume}


def ssi_snapshot(rows,clock):
    return {"schema":"mst.mcp.d1.private_drive_snapshot.v0.2","project":"MST",
            "provider":"SSI","symbol":"AAA","timeframe":"D1",
            "source_tool":"MCP_SSI.marketdata_list_stock_daily_data",
            "capture_utc":clock,"source_row_count":len(rows),"retained_row_count":len(rows),
            "rows":rows}


def dnse_snapshot():
    return {"schema":"mst.mcp.d1.private_drive_snapshot.v0.2","project":"MST",
            "provider":"DNSE","symbol":"BBB","timeframe":"D1",
            "source_tool":"MCP_DNSE.price_get_history",
            "capture_utc":"2026-11-12T10:00:00Z","source_row_count":1,
            "retained_row_count":1,
            "rows":[{"source_unix_seconds":1794448800,"date_utc":"2026-11-12",
                     "open":100,"high":104,"low":98,"close":101,"volume":200}]}


def record(provider,symbol,ref,count):
    return {"provider":provider,"symbol":symbol,"timeframe":"D1",
            "source_snapshot_doc_id":ref,"persisted_rows":count,
            "readback_verified":True,"stored_in_private_folder":True}


def manifest(records):
    return {"schema":"mst.cloud.drive.private.mcp_d1_capture_manifest.v0.2",
            "project":"MST","source_partition_count":len(records),
            "snapshots":records}


class FakeResponse:
    def __init__(self, status=200, *, json_value=None, content=b""):
        self.status_code=status
        self._json=json_value
        self.content=content

    def json(self):
        return self._json


class FakeSession:
    def __init__(self, documents=None):
        self.documents=documents if documents is not None else fixtures()
        self.meta={}
        self.calls=[]

    def get(self,url,*,params,timeout):
        self.calls.append(("GET",url,params,timeout))
        prefix="https://www.googleapis.com/drive/v3/files/"
        if not url.startswith(prefix):
            raise AssertionError("EXTERNAL_NON_GOOGLE_DRIVE_TARGET")
        suffix=url[len(prefix):]
        if suffix.endswith("/export"):
            id=suffix[:-len("/export")]
            if id not in self.documents:
                return FakeResponse(403)
            if params!={"mimeType":"text/plain"}:
                raise AssertionError("ONLY_TEXT_PLAIN_EXPORT")
            data=("\ufeff"+json.dumps(self.documents[id])).encode("utf-8")
            return FakeResponse(content=data)
        if suffix not in self.documents:
            return FakeResponse(403)
        metadata={"id":suffix,"mimeType":"application/vnd.google-apps.document",
                  "parents":[PARENT],"trashed":False,
                  "capabilities":{"canDownload":True}}
        metadata.update(self.meta.get(suffix,{}))
        return FakeResponse(json_value=metadata)


def fixtures():
    return {
      OLD:manifest([record("SSI","AAA",SSI_OLD,1),
                    record("DNSE","BBB",DNSE,1)]),
      NEW:manifest([record("SSI","AAA",SSI_NEW,2),
                    record("DNSE","BBB",DNSE,1)]),
      SSI_OLD:ssi_snapshot([ssi_row("11/11/2026")],"2026-11-12T10:00:00Z"),
      SSI_NEW:ssi_snapshot([ssi_row("12/11/2026"),ssi_row("11/11/2026")],
                           "2026-11-12T11:00:00Z"),
      DNSE:dnse_snapshot()
    }


def env():
    return {
      "GITHUB_REPOSITORY":"ngluonghoa/MST",
      "GITHUB_REPOSITORY_ID":"1450356304",
      "GITHUB_REPOSITORY_OWNER_ID":"353049266",
      "GITHUB_EVENT_NAME":"workflow_dispatch",
      "GITHUB_REF":"refs/heads/main",
      "GITHUB_WORKFLOW_REF":(
         "ngluonghoa/MST/.github/workflows/"
         "mst-m3-private-d1-readonly.yml@refs/heads/main"),
      "MST_M3_DRIVE_READONLY_OWNER_ACCEPTED":"true",
      "MST_GDRIVE_OAUTH_CLIENT_ID":"FAKE_TEST_ID",
      "MST_GDRIVE_OAUTH_CLIENT_SECRET":"FAKE_TEST_SECRET",
      "MST_GDRIVE_OAUTH_REFRESH_TOKEN":"FAKE_TEST_REFRESH",
      "MST_M3_PRIVATE_D1_OLD_MANIFEST_ID":OLD,
      "MST_M3_PRIVATE_D1_NEW_MANIFEST_ID":NEW,
      "MST_M3_PRIVATE_D1_ALLOWED_PARENT_IDS":PARENT,
    }


class ExactDocumentReadTests(unittest.TestCase):
    def test_valid_metadata_export_and_parse(self):
        s=FakeSession()
        data=m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))
        self.assertEqual(data["rows"][0]["volume"],"200")
        self.assertEqual(len(s.calls),2)
        self.assertTrue(all(method=="GET" for method,*_ in s.calls))

    def test_wrong_google_parent_denied_without_export(self):
        s=FakeSession();s.meta[SSI_OLD]={"parents":["FakeOtherParent_AAAABBBBCCCCDDDD"]}
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))
        self.assertEqual(len(s.calls),1)

    def test_mimetype_mismatch_denied(self):
        s=FakeSession();s.meta[SSI_OLD]={"mimeType":"application/pdf"}
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))

    def test_file_marked_trashed_denied(self):
        s=FakeSession();s.meta[SSI_OLD]={"trashed":True}
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))

    def test_export_restricted_denied(self):
        s=FakeSession();s.meta[SSI_OLD]={"capabilities":{"canDownload":False}}
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))

    def test_inaccessible_app_scoped_doc_denied(self):
        with self.assertRaisesRegex(m.DriveReadonlyDenied,"NOT_ACCESSIBLE"):
            m.fetch_private_doc_readonly(FakeSession(), "MissingPrivateDoc_AAAABBBBCCCCDD",
                                         frozenset([PARENT]))

    def test_unknown_parent_type_denied(self):
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(FakeSession(),SSI_OLD,{PARENT})

    def test_fake_invalid_docid_denied(self):
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(FakeSession(),"x",frozenset([PARENT]))

    def test_duplicate_source_field_json_denied(self):
        s=FakeSession()
        class DuplicateJsonSession(FakeSession):
            def get(self,url,*,params,timeout):
                r=super().get(url,params=params,timeout=timeout)
                if url.endswith("/export"):
                    r.content=b'{"schema":"a","schema":"b"}'
                return r
        with self.assertRaises(m.DriveReadonlyDenied):
            m.fetch_private_doc_readonly(DuplicateJsonSession(),SSI_OLD,frozenset([PARENT]))

    def test_metadata_fetch_never_mutates_google(self):
        s=FakeSession()
        m.fetch_private_doc_readonly(s,SSI_OLD,frozenset([PARENT]))
        self.assertEqual(len(s.calls),2)
        self.assertFalse(any("Authorization" in str(entry) for entry in s.calls))


class TwoManifestReadOnlyTests(unittest.TestCase):
    def test_new_ssi_session_one_source_and_one_reused(self):
        s=FakeSession()
        out=m.read_two_private_manifests(s,prior_manifest_id=OLD,
                                         next_manifest_id=NEW,
                                         approved_parents=frozenset([PARENT]))
        self.assertEqual(out["partition_count"],2)
        self.assertEqual(out["changed_source_versions"],1)
        self.assertEqual(out["reused_source_versions"],1)
        self.assertEqual(out["quarantined_scope_or_revision"],0)
        self.assertEqual(out["new_day_labels"],1)
        self.assertEqual(out["overlapping_rows_checked"],1)
        self.assertEqual(out["distinct_private_docs_read"],5)
        self.assertFalse(out["private_data_written"])
        self.assertFalse(out["trade_signal_eligible"])

    def test_unchanged_source_ids_are_not_immutable_attestation(self):
        out=m.read_two_private_manifests(
            FakeSession(),prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        self.assertFalse(out["previous_mutable_docs_immutable_proof"])
        self.assertFalse(out["source_issuer_first_known_verified"])

    def test_changed_price_detected_without_price_value_leak(self):
        data=fixtures()
        data[SSI_NEW]["rows"][1]["close"]="102"
        out=m.read_two_private_manifests(
            FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        self.assertEqual(out["numeric_ohlcv_revisions"],1)
        self.assertNotIn("102",json.dumps(out))

    def test_truncated_new_source_quarantined(self):
        data=fixtures()
        data[SSI_NEW]["source_row_count"]=3
        out=m.read_two_private_manifests(
            FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        self.assertEqual(out["quarantined_scope_or_revision"],1)

    def test_missing_prior_date_quarantined(self):
        data=fixtures()
        data[SSI_NEW]["rows"]=data[SSI_NEW]["rows"][:1]
        data[SSI_NEW]["retained_row_count"]=1
        data[SSI_NEW]["source_row_count"]=1
        data[NEW]["snapshots"][0]["persisted_rows"]=1
        out=m.read_two_private_manifests(
            FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        self.assertEqual(out["quarantined_scope_or_revision"],1)

    def test_mismatched_provider_source_denied(self):
        data=fixtures()
        data[SSI_NEW]["symbol"]="BBB"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))

    def test_wrong_manifest_ref_rowcount_denied(self):
        data=fixtures()
        data[NEW]["snapshots"][0]["persisted_rows"]=99
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))

    def test_manifest_extra_unknown_provider_denied(self):
        data=fixtures()
        data[NEW]["snapshots"][0]["provider"]="MFX"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))

    def test_reused_prior_source_missing_scope_denied(self):
        data=fixtures()
        del data[DNSE]
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(data),prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))

    def test_same_manifest_id_denied(self):
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(),prior_manifest_id=OLD,next_manifest_id=OLD,
                approved_parents=frozenset([PARENT]))

    def test_no_private_file_ids_appear_in_receipt(self):
        out=m.read_two_private_manifests(
            FakeSession(),prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        text=json.dumps(out)
        for id in (OLD,NEW,SSI_OLD,SSI_NEW,DNSE,PARENT):
            self.assertNotIn(id,text)


class ManualContextTests(unittest.TestCase):
    def test_valid_owner_manual_env(self):
        secrets,a,b,parents=m.require_manual_owner_env(env())
        self.assertEqual(a,OLD)
        self.assertEqual(b,NEW)
        self.assertEqual(parents,frozenset([PARENT]))
        self.assertNotIn("FAKE_TEST_SECRET",repr(secrets))

    def test_wrong_branch_denied(self):
        e=env();e["GITHUB_REF"]="refs/heads/mst/m3-cross-surface-finality-20261112"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_schedule_event_denied(self):
        e=env();e["GITHUB_EVENT_NAME"]="schedule"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_pr_event_denied(self):
        e=env();e["GITHUB_EVENT_NAME"]="pull_request"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_missing_owner_gate_denied(self):
        e=env();e.pop("MST_M3_DRIVE_READONLY_OWNER_ACCEPTED")
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_missing_secret_denied(self):
        e=env();e.pop("MST_GDRIVE_OAUTH_REFRESH_TOKEN")
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_legacy_service_account_not_supported(self):
        e=env();e["MST_GDRIVE_SERVICE_ACCOUNT_JSON"]="FAKE"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_duplicate_approved_folders_denied(self):
        e=env();e["MST_M3_PRIVATE_D1_ALLOWED_PARENT_IDS"]=PARENT+","+PARENT
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)

    def test_unapproved_manifest_id_not_allowed(self):
        e=env();e["MST_M3_PRIVATE_D1_NEW_MANIFEST_ID"]="bad"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.require_manual_owner_env(e)



def nine_partition_fixtures():
    """Invented 3-provider x 3-symbol v1->v2 fixture, no live source data."""
    old_files = []
    new_files = []
    docs = {}
    for sym in ("AAA", "BBB", "CCC"):
        for provider in ("SSI", "DNSE", "VCBS"):
            prefix = f"Fake9_{provider}_{sym}_00000000000000000"
            old_id = prefix + "_prior"
            new_id = prefix + "_current" if provider == "SSI" else old_id
            if provider == "SSI":
                old_rows = [{"symbol":sym, "trading_date":"11/11/2026",
                             "open":"100","high":"103","low":"98",
                             "close":"101","volume":"200"}]
                new_rows = [{"symbol":sym, "trading_date":"12/11/2026",
                             "open":"101","high":"104","low":"99",
                             "close":"102","volume":"250"}] + deepcopy(old_rows)
                prev = ssi_snapshot(old_rows,"2026-11-12T10:00:00Z")
                curr = ssi_snapshot(new_rows,"2026-11-12T11:00:00Z")
                prev["symbol"]=sym
                curr["symbol"]=sym
                docs[old_id]=prev
                docs[new_id]=curr
            elif provider == "DNSE":
                docs[old_id]=dnse_snapshot()
                docs[old_id]["symbol"]=sym
            else:
                docs[old_id]={
                    "schema":"mst.mcp.d1.private_drive_snapshot.v0.2",
                    "project":"MST","provider":"VCBS","symbol":sym,"timeframe":"D1",
                    "source_tool":"MCP_VCBS.vcbs_get_history",
                    "capture_utc":"2026-11-12T10:00:00Z",
                    "source_row_count":1,"retained_row_count":1,
                    "rows":[{"tradingDate":"2026-11-12",
                             "openPrice":100,"highPrice":103,"lowPrice":98,
                             "closePrice":101,"volume":200,"adjClosePrice":101,
                             "adjFactor":1,"price":101}],
                }
            old_files.append(record(provider,sym,old_id,1))
            new_files.append(record(provider,sym,new_id,2 if provider=="SSI" else 1))
    docs[OLD]=manifest(old_files)
    docs[NEW]=manifest(new_files)
    return docs


class NinePartitionOfflineCloudReadbackTests(unittest.TestCase):
    def test_nine_source_partitions_three_new_and_six_reused(self):
        session=FakeSession(nine_partition_fixtures())
        report=m.read_two_private_manifests(
            session,prior_manifest_id=OLD,next_manifest_id=NEW,
            approved_parents=frozenset([PARENT]))
        self.assertEqual(report["partition_count"],9)
        self.assertEqual(report["changed_source_versions"],3)
        self.assertEqual(report["reused_source_versions"],6)
        self.assertEqual(report["new_day_labels"],3)
        self.assertEqual(report["overlapping_rows_checked"],3)
        self.assertEqual(report["quarantined_scope_or_revision"],0)
        self.assertEqual(report["distinct_private_docs_read"],14)
        self.assertFalse(report["private_data_written"])
        self.assertFalse(report["cross_provider_volume_qa_crosschecked"])

    def test_nine_partition_private_parent_mismatch_fails_entire_run(self):
        session=FakeSession(nine_partition_fixtures())
        session.meta[OLD]={"parents":["UnapprovedPrivateParent0000000000"]}
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                session,prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))
        self.assertEqual(len(session.calls),1)

    def test_nine_partition_one_bad_symbol_refuses_entire_report(self):
        docs=nine_partition_fixtures()
        one_id=next(id for id,v in docs.items()
                    if id.endswith("_current") and v.get("symbol")=="BBB")
        docs[one_id]["symbol"]="CCC"
        with self.assertRaises(m.DriveReadonlyDenied):
            m.read_two_private_manifests(
                FakeSession(docs),prior_manifest_id=OLD,next_manifest_id=NEW,
                approved_parents=frozenset([PARENT]))


if __name__ == "__main__":
    unittest.main()
