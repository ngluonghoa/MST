"""54 untrusted fixture revision/tombstone checks: NO vendor or owner authority."""
from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_revision_tombstone_hypothesis_lab as m


class A03RevisionTombstoneHypothesisTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.build()
        cls.cases={r["case"]:r for r in cls.report["cases"]}

    def assert_case(self,name,group):
        self.assertIn(name,self.cases)
        self.assertEqual(self.cases[name]["group"],group)
        self.assertEqual(self.cases[name]["result"],"PASS_UNTRUSTED_FIXTURE_ONLY")

    def test_01_report_schema(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_02_exact_54_fixture_cases(self):
        self.assertEqual(self.report["case_count"],54)

    def test_03_unique_case_ids(self):
        self.assertEqual(len(self.cases),54)

    def test_04_case_hash_covers_snapshots_and_owner(self):
        b=json.dumps({"cases":self.report["cases"],
                      "snapshots":self.report["as_of_snapshots"],
                      "owner_choices":self.report["owner_review_choices"]},
                     sort_keys=True,separators=(",",":"),allow_nan=False)
        self.assertEqual(self.report["case_and_snapshot_sha256"],
                         sha256(b.encode()).hexdigest())

    def test_05_all_fixtures_untrusted(self):
        self.assertTrue(all(x["result"]=="PASS_UNTRUSTED_FIXTURE_ONLY"
                            for x in self.report["cases"]))

    def test_06_four_owner_decisions_unsigned(self):
        self.assertEqual(len(self.report["owner_review_choices"]),4)
        self.assertEqual(len({x["id"] for x in self.report["owner_review_choices"]}),4)
        self.assertTrue(all(x["owner_signed"] is False
                            for x in self.report["owner_review_choices"]))

    def test_07_prior_owner_signoffs_zero(self):
        self.assertEqual(self.report["owner_a02_signed"],0)
        self.assertEqual(self.report["owner_a03_signed"],0)

    def test_08_no_external_authorization(self):
        for key in ("v1_v2_native_supersession_or_tombstone_semantics_implemented",
                    "provider_revision_sequence_independently_attested",
                    "real_market_data_source_authority_or_entitlement_proven",
                    "legal_google_drive_market_cache_or_durable_cas_proven",
                    "g01_g08_oa01_oa06_closed",
                    "production_release_or_trading_authorized"):
            with self.subTest(key=key):
                self.assertIs(self.report[key],False)

    def test_09_five_asof_snapshots(self):
        self.assertEqual(len(self.report["as_of_snapshots"]),5)

    def test_10_asof_raw_prefix_counts(self):
        self.assertEqual([len(x["raw_visible_revisions"])
                          for x in self.report["as_of_snapshots"]],[1,1,2,3,3])

    def test_11_asof_candidate_before_first_correction(self):
        self.assertEqual([x["candidate_revision_id"] for x
                         in self.report["as_of_snapshots"][:2]],["r1","r1"])

    def test_12_asof_candidate_after_correction(self):
        self.assertEqual(self.report["as_of_snapshots"][2]["candidate_revision_id"],
                         "r2")

    def test_13_tombstone_suppresses_candidate(self):
        self.assertIsNone(self.report["as_of_snapshots"][3]["candidate_revision_id"])
        self.assertEqual(self.report["as_of_snapshots"][3]["status"],
                         "UNVERIFIED_TOMBSTONED")

    def test_14_tombstone_does_not_promote_absence_to_not_detected(self):
        self.assertNotEqual(self.report["as_of_snapshots"][4]["status"],"NOT_DETECTED")
        self.assertIsNone(self.report["as_of_snapshots"][4]["candidate_revision_id"])

    def test_15_original_and_v2_raw_replay_comparison(self):
        for n in range(5):
            self.assert_case(f"AS_OF_{n}_RAW_V1_V2_VISIBILITY_PARITY","as_of")

    def test_16_no_future_data_lookahead(self):
        for n in range(5):
            self.assert_case(f"AS_OF_{n}_NO_FUTURE_KNOWLEDGE","as_of")

    def test_17_all_views_no_authorization(self):
        for n in range(5):
            self.assert_case(f"AS_OF_{n}_NO_AUTHORITY_CLAIM","as_of")

    def test_18_hypothesis_states_not_owner_proven(self):
        for n in range(5):
            self.assert_case(f"AS_OF_{n}_UNTRUSTED_CANDIDATE_STATE","as_of")

    def test_19_historical_replay_does_not_repaint(self):
        self.assert_case("FRESH_EARLY_REPLAY_NOT_REPAINTED","correction")
        self.assertEqual(m.resolve_untrusted_fixture(
            m.PARTITION,"BAR1",m.RECORDS,as_of_utc=m.TIMES[0]
        ).candidate_revision_id,"r1")

    def test_20_raw_v1_v2_does_not_implement_tombstone_selection(self):
        self.assert_case("V1_V2_RETURN_RAW_TOMBSTONE_AS_EVENT","tombstone")
        self.assertFalse(self.report[
            "v1_v2_native_supersession_or_tombstone_semantics_implemented"])

    def test_21_out_of_order_input_not_trusted_as_order(self):
        self.assert_case("OUT_OF_ORDER_INPUT_IS_SORTED_BY_DECLARED_SEQUENCE_ONLY",
                         "correction")

    def test_22_opaque_digest_required_not_authenticated(self):
        with self.assertRaises(ValueError):
            replace(m.UP1,payload_sha256="NOT_A_SHA")

    def test_23_tombstone_with_payload_is_invalid(self):
        self.assert_case("TOMBSTONE_WITH_PAYLOAD_REJECTED","validation")

    def test_24_boolean_seq_not_integer(self):
        self.assert_case("BOOLEAN_SEQUENCE_REJECTED","validation")

    def test_25_future_timestamp_and_naive_clock(self):
        self.assert_case("NAIVE_KNOWLEDGE_TIMESTAMP_REJECTED","validation")
        self.assert_case("FIRST_KNOWN_BEFORE_EVENT_REJECTED","validation")

    def test_26_wrong_source_provider_rejected(self):
        self.assert_case("UNVERIFIED_CROSS_PROVIDER_REJECTED","isolation")

    def test_27_cross_price_basis_rejected(self):
        self.assert_case("UNVERIFIED_CROSS_PRICE_BASIS_REJECTED","isolation")

    def test_28_cross_bar_event_rejected(self):
        self.assert_case("UNVERIFIED_CROSS_EVENT_ID_REJECTED","isolation")

    def test_29_missing_root_sequence_denied(self):
        self.assert_case("MISSING_ROOT_SEQUENCE_BLOCKED","chain")
        with self.assertRaises(ValueError):
            m.resolve_untrusted_fixture(m.PARTITION,"BAR1",(m.UP2,),
                                        as_of_utc=m.TIMES[2])

    def test_30_duplicate_sequence_or_revision_rejected(self):
        self.assert_case("DUPLICATE_SEQUENCE_BLOCKED","chain")
        self.assert_case("DUPLICATE_REVISION_ID_BLOCKED","chain")

    def test_31_wrong_parent_or_chain_gap_denied(self):
        self.assert_case("GAPPED_CHAIN_BLOCKED","chain")
        self.assert_case("WRONG_PARENT_REVISION_BLOCKED","chain")

    def test_32_same_instant_tie_denied(self):
        self.assert_case("SAME_KNOWLEDGE_INSTANT_AMBIGUOUS","chain")

    def test_33_regressed_knowledge_denied(self):
        self.assert_case("REGRESSED_KNOWLEDGE_BLOCKED","chain")

    def test_34_mixed_event_time_denied(self):
        self.assert_case("MIXED_EVENT_START_TIMES_BLOCKED","chain")

    def test_35_tombstone_resurrection_denied_asof_arrival(self):
        self.assert_case("TOMBSTONE_RESURRECTION_REQUIRES_POLICY","tombstone")
        rev=m.FixtureRevision(m.PARTITION,"BAR1","r4",4,
            m.RevisionKind.UPSERT,m.T0,m.TIMES[4],
            supersedes_revision_id="r3",payload_sha256="4"*64)
        self.assertEqual(
            m.resolve_untrusted_fixture(m.PARTITION,"BAR1",m.RECORDS+(rev,),
                as_of_utc=m.TIMES[3]).status,"UNVERIFIED_TOMBSTONED")
        with self.assertRaises(ValueError):
            m.resolve_untrusted_fixture(m.PARTITION,"BAR1",m.RECORDS+(rev,),
                as_of_utc=m.TIMES[4])

    def test_36_none_of_the_candidate_ids_are_trusted_prices(self):
        self.assert_case("NO_EXTERNAL_SEQUENCE_ATTESTATION_IN_FIXTURE","governance")
        self.assertIs(self.report["fixture_revision_candidate_only"],True)

    def test_37_negative_untype_batch(self):
        self.assert_case("UNTYPED_EVENT_OBJECT_REJECTED","validation")
        self.assert_case("LIST_INSTEAD_OF_IMMUTABLE_TUPLE_REJECTED","validation")

    def test_38_bad_revision_shape(self):
        self.assert_case("NONENUM_KIND_REJECTED","validation")
        self.assert_case("NONROOT_WITHOUT_PREDECESSOR_REJECTED","validation")
        self.assert_case("ROOT_WITH_PREDECESSOR_REJECTED","validation")

    def test_39_false_no_data_does_not_mean_no_signal(self):
        self.assert_case("EMPTY_CANDIDATE_NEVER_MEANS_NOT_DETECTED","governance")
        empty=m.resolve_untrusted_fixture(m.PARTITION,"BAR1",(),as_of_utc=m.T0)
        self.assertEqual(empty.status,"UNVERIFIED_EMPTY")
        self.assertFalse(empty.trading_authorized)

    def test_40_original_source_overwrites_not_permitted(self):
        self.assertFalse(self.report["production_release_or_trading_authorized"])
        self.assertFalse(self.report["real_market_data_source_authority_or_entitlement_proven"])


if __name__=="__main__":
    import unittest
    unittest.main()
