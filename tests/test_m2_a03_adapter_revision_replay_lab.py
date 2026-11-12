"""A03 original-code replay revisions and proposed adapter opt-in denial tests."""
from datetime import datetime, timedelta
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_adapter_revision_replay_lab as m
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.engine import evaluate_unimplemented_zones


class A03AdapterRevisionReplayTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = m.build()
        cls.by_case = {x["case"]: x for x in cls.r["cases"]}

    def check_case(self, name, area):
        self.assertEqual(self.by_case[name]["area"], area)
        self.assertEqual(self.by_case[name]["status"], "PASS_FIXTURE_ONLY")

    def test_01_exact_schema(self):
        self.assertEqual(self.r["schema"], m.SCHEMA)

    def test_02_case_count_38(self):
        self.assertEqual(self.r["case_count"], 38)

    def test_03_no_duplicate_fixture_cases(self):
        self.assertEqual(len(self.by_case), 38)

    def test_04_all_cases_explicitly_synthetic(self):
        self.assertTrue(all(x["status"] == "PASS_FIXTURE_ONLY"
                            for x in self.r["cases"]))

    def test_05_case_digest_covers_snapshots_and_owner_matrix(self):
        canon=json.dumps({
            "cases":self.r["cases"],
            "snapshots":self.r["as_of_snapshots"],
            "decisions":tuple(self.r["owner_decision_matrix"]),
        },sort_keys=True,separators=(",",":"),allow_nan=False)
        self.assertEqual(self.r["case_and_snapshot_sha256"],
                         sha256(canon.encode()).hexdigest())

    def test_06_six_owner_decision_rows_unsigned(self):
        self.assertEqual(len(self.r["owner_decision_matrix"]),6)
        self.assertTrue(all(d["owner_signed"] is False for d in
                            self.r["owner_decision_matrix"]))

    def test_07_owner_review_ids_unique(self):
        self.assertEqual(len({d["id"] for d in self.r["owner_decision_matrix"]}),6)

    def test_08_no_owner_A02_A03_approval(self):
        self.assertEqual(self.r["a02_owner_approvals"],0)
        self.assertEqual(self.r["a03_owner_approvals"],0)
        self.assertFalse(self.r["adapter_owner_approved"])

    def test_09_no_unauthorized_production_assertions(self):
        for key in ("real_source_revision_supersession_proven",
                    "historical_vendor_as_of_authenticity_proven",
                    "data_rights_or_physical_drive_cache_proven",
                    "all_g01_g08_oa01_oa06_closed",
                    "production_release_or_trading_authorized"):
            with self.subTest(key=key):
                self.assertIs(self.r[key],False)

    def test_10_original_sources_unmodified(self):
        self.assertFalse(self.r["legacy_source_or_preexisting_v2_changed"])

    def test_11_raw_v1_generator_bug_is_not_hidden(self):
        self.check_case("RAW_GENERATOR_V1_EXHAUSTION_REPRODUCED","iterator")

    def test_12_raw_v2_generator_visibility_is_distinct(self):
        self.check_case("RAW_GENERATOR_V2_MATERIALIZATION_REPRODUCED","iterator")

    def test_13_explicit_tuple_candidate_v1(self):
        self.check_case("EXPLICIT_BOUNDED_TUPLE_RESTORES_V1_VISIBILITY","iterator")

    def test_14_explicit_tuple_candidate_v2(self):
        self.check_case("EXPLICIT_BOUNDED_TUPLE_PRESERVES_V2_VISIBILITY","iterator")

    def test_15_adapter_calls_one_source_once(self):
        self.check_case("SOURCE_CALLED_ONCE_BY_EACH_EXPLICIT_ADAPTER","iterator")

    def test_16_preserve_payload_object_no_coercion(self):
        self.check_case("ADAPTER_PRESERVES_EXACT_OBJECT_AND_PAYLOAD","iterator")

    def test_17_bounded_iterator_excess_denied(self):
        self.check_case("OVERSIZED_GENERATOR_FAILS_CLOSED","iterator")

    def test_18_invalid_max_and_source_port_rejected(self):
        self.check_case("INVALID_MAX_BOOL_NOT_ALLOWED","iterator")
        self.check_case("INVALID_MAX_ZERO_NOT_ALLOWED","iterator")
        self.check_case("MISSING_SOURCE_PORT_DENIED","iterator")

    def test_19_foreign_event_type_rejected(self):
        self.check_case("UNSUPPORTED_ITEM_TYPE_DENIED","iterator")

    def test_20_legacy_subclass_still_accepted_with_tuple(self):
        self.check_case("V1_SUBCLASS_WITH_TUPLE_ACCEPTED","subclass")

    def test_21_strict_v2_refuses_subclass(self):
        self.check_case("V2_SUBCLASS_WITH_TUPLE_DENIED","subclass")

    def test_22_optin_strict_adapters_fail_closed_for_both(self):
        self.check_case("EXPLICIT_STRICT_TYPE_PORT_DENIES_SUBCLASS_V1","subclass")
        self.check_case("EXPLICIT_STRICT_TYPE_PORT_DENIES_SUBCLASS_V2","subclass")

    def test_23_exact_base_type_still_works(self):
        self.check_case("EXACT_TYPE_POLICY_ACCEPTS_BASE_EVENT","subclass")

    def test_24_nonboolean_exact_flag_rejected(self):
        self.check_case("NONBOOLEAN_STRICT_FLAG_DENIED","subclass")

    def test_25_four_historical_as_of_snapshots(self):
        self.assertEqual(len(self.r["as_of_snapshots"]),4)
        self.assertEqual([len(x["visible_revisions"])
                          for x in self.r["as_of_snapshots"]],[1,1,2,3])

    def test_26_late_correction_not_visible_early(self):
        self.assertEqual(self.r["as_of_snapshots"][0]["visible_revisions"],
                         (("BAR-1","r1"),))
        self.assertEqual(self.r["as_of_snapshots"][1]["visible_revisions"],
                         (("BAR-1","r1"),))

    def test_27_revisions_accumulate_without_automatic_supersession(self):
        self.assertEqual(self.r["as_of_snapshots"][2]["visible_revisions"],
                         (("BAR-1","r1"),("BAR-1","r2")))
        self.assertEqual(self.r["as_of_snapshots"][3]["visible_revisions"],
                         (("BAR-1","r1"),("BAR-1","r2"),("BAR-1","r3")))

    def test_28_each_correction_snapshot_enforces_no_future(self):
        for i in range(4):
            self.check_case(f"CORRECTION_AS_OF_{i}_NO_FUTURE_KNOWLEDGE","correction")

    def test_29_each_snapshot_v1_v2_equal_when_explicit_tuple(self):
        for i in range(4):
            self.check_case(f"CORRECTION_AS_OF_{i}_V1_EQUALS_V2","correction")

    def test_30_all_versions_remain_raw_not_selected_winner(self):
        self.check_case("REVISIONS_RAW_HISTORY_NOT_AUTO_SUPERSEDED","correction")
        self.check_case("LATE_REVISION_DOES_NOT_REPAINT_EARLY_SNAPSHOT","correction")

    def test_31_causal_constructor_refuses_future_misordering(self):
        self.check_case("CAUSAL_KNOWN_BEFORE_EVENT_TIME_REJECTED","correction")
        self.check_case("NAIVE_FIRST_KNOWN_TIME_REJECTED","correction")

    def test_32_all_16_zones_two_strategies_remain_unverified(self):
        self.check_case("ALL_SYNTHETIC_ZONES_REMAIN_UNVERIFIED","signal")
        for strat in Strategy:
            decisions=evaluate_unimplemented_zones(strat,m.TIMES[-1])
            self.assertEqual(len(decisions),16)
            self.assertTrue(all(x.status is DecisionStatus.UNVERIFIED
                                for x in decisions))

    def test_33_correction_not_source_or_release_authority(self):
        self.check_case("SOURCE_REVISIONS_CANNOT_ASSERT_VERIFIED_TRADE","signal")
        self.check_case("ALL_OWNER_OPTIONS_ARE_PROPOSALS_ONLY","governance")

    def test_34_independent_excess_cap_rejection(self):
        event=CausalMarketEvent("TEST","r1",m.T0,m.T0,{"test":1})
        adapter=m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource((event,event)),max_events=1)
        with self.assertRaises(ValueError):
            adapter.available_events(m.T0)

    def test_35_independent_source_event_subclass_policy(self):
        subclass=m._SubclassEvent("TEST","r1",m.T0,m.T0,{"test":1})
        liberal=m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource((subclass,)),exact_base_type=False)
        strict=m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource((subclass,)),exact_base_type=True)
        self.assertIs(liberal.available_events(m.T0)[0],subclass)
        with self.assertRaises(TypeError):
            strict.available_events(m.T0)

    def test_36_independent_replay_after_late_revision(self):
        events=m.correction_events()
        early=m.v1_harness(m.TIMES[0],m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource(events))).visible_events()
        later=m.v2_harness(m.TIMES[-1],m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource(events))).visible_events()
        replayed=m.v1_harness(m.TIMES[0],m.BoundedTupleFixtureAdapter(
            m.GeneratorFixtureSource(events))).visible_events()
        self.assertEqual(m._ids(early),(("BAR-1","r1"),))
        self.assertEqual(replayed,early)
        self.assertEqual(len(later),3)


if __name__=="__main__":
    import unittest
    unittest.main()
