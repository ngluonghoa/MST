"""Pure deterministic tests: all source rows, headers and private IDs fictitious."""
from __future__ import annotations
import unittest

from scripts.mst_cache_noop_reuse import verified_unchanged_receipt


def proof(provider="DNSE",tf="D1",symbol="FPT",exits=1,overlap=2):
    if provider=="SSI":
        chain="mst.cloud.ssi_native_prior_source_delta_candidate.v0.1"
        delta_schema="mst.cloud.ssi_native_incremental_delta.v0.1"
        issuer="SSI_FASTCONNECT_V3_MARKET_DATA"
        tf_field="source_native_tf"
    elif tf=="D1":
        chain="mst.cloud.dnse_d1_prior_source_delta_candidate.v0.1"
        delta_schema="mst.private_d1_source_delta_plan.v1"
        issuer="DNSE"
        tf_field="timeframe"
    else:
        chain="mst.cloud.dnse_native_prior_source_delta_candidate.v0.1"
        delta_schema="mst.cloud.dnse_intraday_incremental_delta.v0.1"
        issuer="DNSE"
        tf_field="source_native_tf"
    return {
        "schema":chain,
        "eligible_for_signals":False,
        "prior_private_file_id":"FAKE_PREVIOUS_PRIVATE_SOURCE_123",
        "prior_source_sha256":"a"*64,
        "delta":{
            "schema":delta_schema,
            "provider":issuer,
            "symbol":symbol,
            tf_field:tf,
            "added":[],
            "revised":[],
            "window_exited_not_deleted":[{"FAKE":"old"}]*exits,
            "unchanged_overlap":overlap,
            "signal_eligible":False,
        },
    }


class VerifiedSourceReuse(unittest.TestCase):
    def test_no_previous_is_not_a_noop(self):
        self.assertIsNone(verified_unchanged_receipt(
            None,provider="DNSE",symbol="FPT",tf="D1",observed_rows=2))

    def test_all_verified_provider_native_tfs_reuse_without_data_loss(self):
        for provider,tfs in (("SSI",("M5","M15","M30","H1","D1")),
                             ("DNSE",("M5","M15","M30","H1","D1"))):
            for tf in tfs:
                with self.subTest(provider=provider,tf=tf):
                    result=verified_unchanged_receipt(proof(provider,tf),
                        provider=provider,symbol="FPT",tf=tf,observed_rows=2)
                    self.assertTrue(result["source_noop_reused_verified_prior"])
                    self.assertFalse(result["unpublished_private_source_document_stored"])
                    self.assertEqual(result["stored_object_count"],0)
                    self.assertEqual(result["source_unchanged_overlap"],2)
                    self.assertEqual(result["source_delta_window_exited_not_deleted"],1)
                    self.assertTrue(result["previous_candidate_kept_unmodified"])
                    self.assertFalse(result["signals_and_trading_eligible"])

    def test_new_or_revised_source_requires_append_only_stage(self):
        for key in ("added","revised"):
            p=proof()
            p["delta"][key].append({"FAKE":"new"})
            self.assertIsNone(verified_unchanged_receipt(p,
                provider="DNSE",symbol="FPT",tf="D1",observed_rows=2))

    def test_incomplete_overlap_cannot_claim_unchanged(self):
        p=proof(overlap=1)
        with self.assertRaisesRegex(ValueError,"OVERLAP_INCOMPLETE"):
            verified_unchanged_receipt(p,provider="DNSE",
                                     symbol="FPT",tf="D1",observed_rows=2)

    def test_cross_provider_symbol_tf_schema_is_denied(self):
        for bad in ("wrong_provider","wrong_symbol","wrong_tf","wrong_schema",
                    "wrong_digest","missing_prior","claimed_signal","missing_delta"):
            p=proof()
            kwargs={"provider":"DNSE","symbol":"FPT","tf":"D1","observed_rows":2}
            if bad=="wrong_provider":kwargs["provider"]="SSI"
            if bad=="wrong_symbol":kwargs["symbol"]="DCM"
            if bad=="wrong_tf":kwargs["tf"]="M5"
            if bad=="wrong_schema":p["schema"]="unverified"
            if bad=="wrong_digest":p["prior_source_sha256"]="?"*64
            if bad=="missing_prior":del p["prior_private_file_id"]
            if bad=="claimed_signal":p["eligible_for_signals"]=True
            if bad=="missing_delta":del p["delta"]
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                verified_unchanged_receipt(p,**kwargs)

    def test_bool_counts_are_not_valid_evidence(self):
        p=proof()
        p["delta"]["unchanged_overlap"]=True
        with self.assertRaises(ValueError):
            verified_unchanged_receipt(p,provider="DNSE",
                                     symbol="FPT",tf="D1",observed_rows=2)
        p=proof()
        with self.assertRaises(ValueError):
            verified_unchanged_receipt(p,provider="DNSE",
                                     symbol="FPT",tf="D1",observed_rows=True)


if __name__=="__main__":
    unittest.main()
