"""§289 fictional retrieval provenance and compatibility regressions."""
import json
from unittest import TestCase
from unittest.mock import patch

from scripts import mst_ssi_cloud_private_chunk241 as stage
from scripts import mst_private_chunk_readback240 as chunk
from scripts.mst_ssi_retrieval_provenance import native_rows_digest
from test_mst_ssi_cloud_private_chunk241 import owner_env, report, rows, FakeDiscovery


class RetrievalProvenance289(TestCase):
    def test_new_envelope_and_legacy_reader(self):
        env = owner_env()
        raw = stage.source_envelope(report(), rows(), env)
        v = json.loads(raw)
        self.assertEqual(v["retrieval_provenance"]["native_rows_sha256"], native_rows_digest(rows()))
        self.assertIsNone(v["retrieval_provenance"]["vendor_adjustment_revision"])
        self.assertIs(v["retrieval_provenance"]["source_first_known_clock_attested"], False)
        self.assertEqual(chunk._validate_owner_source(env, raw)[:3], ("SSI", "FPT", "D1"))
        del v["retrieval_provenance"]
        v["schema"] = chunk.SCHEMA
        self.assertEqual(chunk._validate_owner_source(env, json.dumps(v).encode())[:3], ("SSI", "FPT", "D1"))

    def test_tampered_provenance_denied_at_both_boundaries(self):
        env = owner_env()
        for key, value in (
            ("retrieval_finished_utc", "2026-11-19T00:59:00.000000+00:00"),
            ("retrieval_started_utc", "2026-11-19T01:00:00.000000+07:00"),
            ("requested_from_date", "2026-11-16"),
            ("requested_symbol", "HPG"),
            ("requested_native_tf", "M5"),
            ("native_rows_sha256", "0"*64),
            ("vendor_adjustment_revision", "invented"),
            ("source_first_known_clock_attested", True),
            ("unknown", "secret"),
        ):
            with self.subTest(key=key):
                r = report()
                r["private_retrieval_provenance"][key] = value
                with self.assertRaises(stage.SsiStageDenied):
                    stage.source_envelope(r, rows(), env)
                v = json.loads(stage.source_envelope(report(), rows(), env))
                v["retrieval_provenance"][key] = value
                with self.assertRaises(chunk.ChunkDenied):
                    chunk._validate_owner_source(env, json.dumps(v).encode())

    def test_mutated_rows_and_missing_provenance_denied(self):
        env = owner_env()
        v = json.loads(stage.source_envelope(report(), rows(), env))
        v["raw_native"][0]["volume"] += 1
        with self.assertRaises(chunk.ChunkDenied):
            chunk._validate_owner_source(env, json.dumps(v).encode())
        r = report()
        del r["private_retrieval_provenance"]
        with patch.object(stage, "_fetch_ssi_native_once", return_value=(r, rows())), patch.object(stage, "upload_private_unpublished_chunk") as put:
            with self.assertRaises(stage.SsiStageDenied):
                stage.run_private_ssi_stage(object(), FakeDiscovery(), env)
            put.assert_not_called()

    def test_actual_adapter_records_two_page_capture_and_redacts_readonly(self):
        from datetime import datetime, timezone
        from scripts import mst_mfx_ssi_readonly as adapter
        from test_mst_mfx_ssi_readonly import FakeSsiApi, settings
        env = settings(MST_MFX_SOURCE_MODE="ssi-native-quarantine-stage")
        api = FakeSsiApi()
        before = datetime.now(timezone.utc)
        receipt, native = adapter._fetch_ssi_native_once(api, env)
        after = datetime.now(timezone.utc)
        p = receipt["private_retrieval_provenance"]
        self.assertEqual(len(native), 3)
        self.assertEqual(len(api.calls), 3)
        self.assertLessEqual(before, datetime.fromisoformat(p["retrieval_started_utc"]))
        self.assertLessEqual(datetime.fromisoformat(p["retrieval_started_utc"]), datetime.fromisoformat(p["retrieval_finished_utc"]))
        self.assertLessEqual(datetime.fromisoformat(p["retrieval_finished_utc"]), after)
        self.assertEqual(p["native_rows_sha256"], native_rows_digest(native))
        self.assertNotIn("private_retrieval_provenance", adapter.read_ssi_native_once(FakeSsiApi(), env))

    def test_clock_reversal_fails_closed(self):
        from datetime import datetime, timezone
        from scripts import mst_mfx_ssi_readonly as adapter
        from test_mst_mfx_ssi_readonly import FakeSsiApi, settings
        with patch.object(adapter, "datetime", wraps=datetime) as clock:
            clock.now.side_effect = [
                datetime(2026, 11, 19, 2, tzinfo=timezone.utc),
                datetime(2026, 11, 19, 1, tzinfo=timezone.utc),
            ]
            with self.assertRaisesRegex(adapter.SsiSourceDenied, "RETRIEVAL_PROVENANCE_DENIED"):
                adapter._fetch_ssi_native_once(FakeSsiApi(), settings())
