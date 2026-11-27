"""All-local-memory synthetic QA for the MST Cache V2.1 fake contract lab.

No Google OAuth, Drive, market vendor, network, credentials or real cache writes.
"""
from pathlib import Path
import math
import unittest

from scripts import mst_cache_v21_fake_two_read_contract as c


def sample(label="FICTIONAL_TEST_RUN", samples=None):
    return {"fixture_only": True, "label": label,
            "samples": [1, 2, 3] if samples is None else samples}


class CacheV21FakeTests(unittest.TestCase):
    def setUp(self):
        self.s = c.FakeDrive()

    def denied(self, data):
        with self.assertRaises(c.SyntheticDenied):
            c.validate_fake(data)

    def test_01_simple_fake_fixture(self):
        self.assertEqual(c.validate_fake(sample())["label"], "FICTIONAL_TEST_RUN")

    def test_02_two_read_success_and_no_external(self):
        result = c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                               next_generation=1)
        self.assertEqual(result["status"], "MST_FAKE_CACHE_V21_TWO_READ_CAS_PASS")
        self.assertTrue(result["chunk_digest_verified_twice"])
        self.assertFalse(result["google_drive_called"])
        self.assertFalse(result["google_drive_cache_written"])
        self.assertFalse(result["source_licenses_proven"])
        self.assertFalse(result["production_cache_activated"])
        self.assertEqual(self.s.read_count, 2)

    def test_03_pointer_increment(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        self.assertEqual(self.s.pointer.revision, 1)
        self.assertEqual(self.s.pointer.generation, 1)

    def test_04_two_sequential_writes(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        prev = self.s.pointer
        r = c.commit_fake(self.s, sample("FICTIONAL_NEW", [4, 5]),
                          expected_pointer=prev, next_generation=2)
        self.assertEqual(r["simulated_pointer_revision"], 2)
        self.assertEqual(r["simulated_immutable_chunk_count"], 2)
        self.assertEqual(self.s.read_count, 4)

    def test_05_repeated_same_chunk_no_duplicate_blob(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        c.commit_fake(self.s, sample(), expected_pointer=self.s.pointer, next_generation=2)
        self.assertEqual(len(self.s._chunks), 1)
        self.assertEqual(self.s.pointer.generation, 2)

    def test_06_rollback_generation_denied(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=2)
        with self.assertRaisesRegex(c.SyntheticDenied, "ROLLBACK"):
            c.commit_fake(self.s, sample(), expected_pointer=self.s.pointer,
                          next_generation=1)

    def test_07_replay_same_generation_denied(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer=self.s.pointer,
                          next_generation=1)

    def test_08_stale_pointer_denied(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        with self.assertRaisesRegex(c.SyntheticDenied, "STALE"):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=2)

    def test_09_out_of_order_generation_allowed_if_increasing(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=2)
        r = c.commit_fake(self.s, sample("FICTIONAL_ANOTHER"), expected_pointer=self.s.pointer,
                          next_generation=4)
        self.assertEqual(r["simulated_generation"], 4)

    def test_10_data_after_first_read_is_detected(self):
        self.s.replay_mutation_after_first_read = b"tampered data"
        with self.assertRaisesRegex(c.SyntheticDenied, "TWO_READBACK"):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(), next_generation=1)
        self.assertEqual(self.s.pointer, c.Pointer())

    def test_11_hash_mismatch_denied(self):
        self.s.put_chunk_immutable("fake", b"payload")
        with self.assertRaises(c.SyntheticDenied):
            c.two_readback_verified(self.s, "fake", "0"*64)

    def test_12_duplicate_key_different_bytes_denied(self):
        self.s.put_chunk_immutable("same", b"payload")
        with self.assertRaises(c.SyntheticDenied):
            self.s.put_chunk_immutable("same", b"another")

    def test_13_immutable_idempotent_same_bytes(self):
        self.s.put_chunk_immutable("same", b"payload")
        self.s.put_chunk_immutable("same", b"payload")
        self.assertEqual(self.s.write_count, 1)

    def test_14_missing_chunk_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            self.s.read_chunk("missing")

    def test_15_fake_cas_conflict_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            self.s.compare_and_swap_pointer(c.Pointer(revision=1),
                                            c.Pointer(revision=2,generation=2))

    def test_16_fake_cas_bad_revision_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            self.s.compare_and_swap_pointer(c.Pointer(),
                                            c.Pointer(revision=3,generation=1))

    def test_17_fake_cas_nonmonotonic_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            self.s.compare_and_swap_pointer(c.Pointer(),
                                            c.Pointer(revision=1,generation=0))

    def test_18_payload_deterministic(self):
        x = c.canonical(sample())
        y = c.canonical({"samples": [1, 2, 3], "label": "FICTIONAL_TEST_RUN",
                         "fixture_only": True})
        self.assertEqual(c.digest(x), c.digest(y))

    def test_19_unicode_json_is_stable(self):
        self.assertEqual(c.canonical({"t": "Đồng Nai"}), c.canonical({"t": "Đồng Nai"}))

    def test_20_nan_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.canonical({"a": float("nan")})

    def test_21_inf_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.canonical({"a": float("inf")})

    def test_22_bool_sample_rejected(self):
        self.denied(sample(samples=[True]))

    def test_23_float_sample_rejected(self):
        self.denied(sample(samples=[1.2]))

    def test_24_str_sample_rejected(self):
        self.denied(sample(samples=["1"]))

    def test_25_empty_samples_rejected(self):
        self.denied(sample(samples=[]))

    def test_26_too_many_samples_rejected(self):
        self.denied(sample(samples=[1] * 41))

    def test_27_out_of_bounds_sample_rejected(self):
        self.denied(sample(samples=[100001]))

    def test_28_bad_label_rejected(self):
        self.denied(sample(label="REAL:SSI:VCB"))

    def test_29_lowercase_label_rejected(self):
        self.denied(sample(label="FICTIONAL_test"))

    def test_30_missing_synthetic_flag_rejected(self):
        self.denied({"label": "FICTIONAL_TEST_RUN", "samples": [1]})

    def test_31_nontrue_synthetic_flag_rejected(self):
        self.denied({"fixture_only": False, "label": "FICTIONAL_TEST_RUN", "samples": [1]})

    def test_32_extra_provider_field_rejected(self):
        self.denied(dict(sample(), provider="SSI"))

    def test_33_extra_market_symbol_field_rejected(self):
        self.denied(dict(sample(), symbol="VCB"))

    def test_34_generation_boolean_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                          next_generation=True)

    def test_35_generation_float_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                          next_generation=1.0)

    def test_36_generation_zero_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                          next_generation=0)

    def test_37_generation_large_rejected(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                          next_generation=1000000001)

    def test_38_nonstore_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake({}, sample(), expected_pointer=c.Pointer(), next_generation=1)

    def test_39_nonpointer_denied(self):
        with self.assertRaises(c.SyntheticDenied):
            c.commit_fake(self.s, sample(), expected_pointer={}, next_generation=1)

    def test_40_no_real_google_vendor_dependencies(self):
        src = (Path(__file__).resolve().parents[1] /
               "scripts/mst_cache_v21_fake_two_read_contract.py").read_text()
        for forbidden in ("google.auth", "googleapiclient", "requests.get(",
                          "requests.post(", "urllib.request", "os.environ",
                          "https://", "ssi.com.vn", "dnse.com.vn", "vcbs.com.vn"):
            self.assertNotIn(forbidden, src.lower())

    def test_41_no_oauth_secret_names(self):
        src = (Path(__file__).resolve().parents[1] /
               "scripts/mst_cache_v21_fake_two_read_contract.py").read_text()
        for forbidden in ("REFRESH_TOKEN", "CLIENT_SECRET", "GITHUB_TOKEN",
                          "MST_OAUTH_BOOTSTRAP_ACCEPTED"):
            self.assertNotIn(forbidden, src)

    def test_42_receipt_distinguishes_simulation(self):
        r = c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                          next_generation=1)
        for k in ("real_google_drive_cas_proven", "trusted_external_highwater_proven",
                  "google_drive_cache_written", "market_provider_called",
                  "real_ohlcv_present", "production_cache_activated"):
            self.assertIs(r[k], False)

    def test_43_tampered_immutable_digest_denied(self):
        c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                      next_generation=1)
        k = next(iter(self.s._chunks))
        self.s._chunks[k] = b"tampered"
        with self.assertRaises(c.SyntheticDenied):
            c.two_readback_verified(self.s, k, k.split("/")[-1].removesuffix(".json"))

    def test_44_no_price_data_from_real_world(self):
        result = c.commit_fake(self.s, sample(), expected_pointer=c.Pointer(),
                               next_generation=1)
        self.assertIs(result["fixture_only"], True)
        self.assertIs(result["real_ohlcv_present"], False)


if __name__ == "__main__":
    unittest.main()
