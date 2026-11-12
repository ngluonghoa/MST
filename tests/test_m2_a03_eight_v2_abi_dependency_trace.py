"""A03 8 opt-in V2 original-to-V1 ABI trace tests: NO owner signoff."""
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import m2_a03_eight_v2_abi_dependency_trace as m
from scripts.m2_a03_behavior_equivalence_lab import run_behavior_matrix, CLOCK_TIMES
from swing_trading.contracts import Evidence, SignalDecision, DecisionStatus, Strategy, ZONE_IDS
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictReplayClockV2, StrictEvidenceV2, StrictSignalDecisionV2,
    legacy_to_v2_unverified, v2_to_legacy_unverified,
)
from swing_trading.v2_replay_port import V2_MARKET_PORT, V2_RULES_PORT


class A03V1V2DependencyTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.build()
        cls.by_name={x["v2_module"]:x for x in cls.report["v2_sidecars"]}

    def test_01_exact_eight_optin_sidecars(self):
        self.assertEqual(len(self.by_name),8)
        self.assertEqual(set(self.by_name),set(m.SIDECARS))

    def test_02_h3_original_v1_count_remains_63(self):
        self.assertEqual(self.report["original_v1_module_count"],63)

    def test_03_not_full_abi_or_behavior(self):
        self.assertFalse(self.report["a03_full_abi_and_behavior_interchangeability_proven"])
        self.assertEqual(self.report["a03_owner_signed_abi_behavior_approvals"],0)

    def test_04_zero_A02_module_dispositions(self):
        self.assertEqual(self.report["a02_owner_signed_module_dispositions"],0)

    def test_05_all_v2_rows_unapproved(self):
        self.assertTrue(all(not x["legacy_v1_abi_interchangeable"]
                            and not x["full_original_to_v2_behavior_parity_proven"]
                            and not x["owner_a03_approved"] for x in self.by_name.values()))

    def test_06_direct_imports_are_original_not_v2_sidecars(self):
        originals=set(m.package_graph())-set(m.SIDECARS)
        for v in self.by_name.values():
            with self.subTest(v2=v["v2_module"]):
                self.assertTrue(set(v["direct_original_v1_imports"])<=originals)
                self.assertTrue(set(v["transitive_original_v1_imports"])<=originals)

    def test_07_transitive_and_direct_imports_disjoint(self):
        for v in self.by_name.values():
            self.assertFalse(set(v["direct_original_v1_imports"])
                             &set(v["transitive_original_v1_imports"]))

    def test_08_no_V2_self_reachable(self):
        for v in self.by_name.values():
            self.assertNotIn(v["v2_module"],v["v2_sidecars_reachable"])

    def test_09_every_trace_dependency_has_A02_owner_false(self):
        for v in self.by_name.values():
            for original in v["original_abi_evidence_dependencies"]:
                self.assertEqual(original["owner_disposition"],"NOT_SIGNED")
                self.assertRegex(original["original_static_abi_sha256"],r"^[a-f0-9]{64}$")

    def test_10_static_graph_is_not_full_call_graph(self):
        self.assertTrue(self.report["direct_plus_transitive_graph_is_static_only"])
        self.assertTrue(all(not v["static_import_graph_is_complete_behavior_call_graph"]
                            for v in self.by_name.values()))

    def test_11_eight_public_static_ABI_hashes_present(self):
        self.assertTrue(all(len(r["v2_static_public_abi_sha256"])==64
                            and len(r["v2_source_sha256"])==64
                            for r in self.by_name.values()))

    def test_12_original_contract_imported_by_strict_v2(self):
        self.assertIn("contracts",self.by_name["strict_contract_v2"]["direct_original_v1_imports"])
        self.assertIn("replay",self.by_name["strict_contract_v2"]["direct_original_v1_imports"])

    def test_13_replay_port_transitively_reaches_contracts(self):
        v=self.by_name["v2_replay_port"]
        self.assertIn("strict_contract_v2",v["v2_sidecars_reachable"])
        self.assertIn("contracts",v["direct_original_v1_imports"])

    def test_14_provider_gate_transitively_reaches_replay_clock(self):
        v=self.by_name["v2_provider_readiness"]
        self.assertIn("v2_source_adapter",v["v2_sidecars_reachable"])
        self.assertIn("replay",v["direct_original_v1_imports"])

    def test_15_cloud_publish_reaches_ref_witness(self):
        v=self.by_name["v2_cloud_publish_verify_lab"]
        self.assertIn("v2_cloud_ref_witness_plan",v["v2_sidecars_reachable"])

    def test_16_sha256_graph_fingerprint_stable(self):
        self.assertEqual(self.report["v2_abi_trace_fingerprint"],
                         m.build(run_safe_fixture=False)["v2_abi_trace_fingerprint"])

    def test_17_graph_contains_exact_71_source_files(self):
        self.assertEqual(len(m.package_graph()),71)

    def test_18_graph_honors_isolated_originals(self):
        graph={"v2":[],"original":[]}
        self.assertEqual(m.reachable(graph,"v2"),[])

    def test_19_graph_direct_vs_transitive_paths(self):
        graph={"v2":["middle","original"],"middle":["nested"],
               "nested":["original"],"original":[]}
        self.assertEqual(m.reachable(graph,"v2"),["middle","nested","original"])

    def test_20_graph_cycle_terminates_without_self(self):
        graph={"v2":["a"],"a":["v2","b"],"b":["a"]}
        self.assertEqual(m.reachable(graph,"v2"),["a","b"])

    def test_21_safe_original_V1_V2_replay_differential_128(self):
        x=self.report["prior_safe_unverified_fixture_differential"]
        self.assertEqual((x["comparisons"],x["snapshots"],x["zones"],x["strategies"]),
                         (128,4,16,2))

    def test_22_no_live_real_source_or_Drive(self):
        for key in ("real_provider_market_data_or_licence_proven",
                    "real_google_drive_market_cache_or_distributed_cas_proven",
                    "full_v2_detector_formula_parity_proven",
                    "all_g01_g08_independent_security_gates_closed",
                    "production_release_authorized","trading_authorized"):
            with self.subTest(k=key):self.assertFalse(self.report[key])

    def test_23_V1_direct_rewind_permissive(self):
        clock=ReplayClock(m.TIME)
        clock.as_of_utc=m.TIME-timedelta(minutes=1)
        self.assertLess(clock.as_of_utc,m.TIME)

    def test_24_V2_direct_rewind_denied_without_mutation(self):
        clock=StrictReplayClockV2(m.TIME)
        with self.assertRaises(ValueError):
            clock.as_of_utc=m.TIME-timedelta(minutes=1)
        self.assertEqual(clock.as_of_utc,m.TIME)

    def test_25_old_Evidence_accepts_truthy_non_bool(self):
        old=Evidence("fixture",m.TIME,1)
        self.assertIs(type(old.verified),int)

    def test_26_strict_Evidence_non_bool_denied(self):
        with self.assertRaises(TypeError):
            StrictEvidenceV2("fixture",m.TIME,1)

    def test_27_two_intentional_non_interchangeable_contracts_recorded(self):
        self.assertEqual(len(self.report["legacy_contract_divergences"]),2)
        self.assertTrue(all(x["classification"]=="INTENTIONAL_STRICTER_NON_INTERCHANGEABLE"
                            for x in self.report["legacy_contract_divergences"]))

    def test_28_unverified_legacy_decision_adapts_only_explicitly(self):
        old=SignalDecision("B1",Strategy.SWING,DecisionStatus.UNVERIFIED)
        converted=legacy_to_v2_unverified(old)
        self.assertEqual(v2_to_legacy_unverified(converted),old)

    def test_29_non_UNVERIFIED_legacy_no_auto_promotion(self):
        legacy=SignalDecision("B1",Strategy.SWING,DecisionStatus.DETECTED,
                              (Evidence("fake",m.TIME,True),))
        with self.assertRaises(PermissionError):
            legacy_to_v2_unverified(legacy)

    def test_30_all_16_zone_identifiers_and_two_strategies_remain_unverified(self):
        self.assertEqual(len(ZONE_IDS),16)
        self.assertEqual(len(tuple(Strategy)),2)
        self.assertEqual(self.report["prior_safe_unverified_fixture_differential"]["comparisons"],128)

    def test_31_V1_and_V2_ports_differ_at_major_version(self):
        self.assertEqual(V2_MARKET_PORT.version,"2.0.0")
        self.assertEqual(V2_RULES_PORT.version,"2.0.0")
        self.assertNotEqual(V2_MARKET_PORT.version,"1.0.0")

    def test_32_public_v2_ABI_is_not_full_v1_abi_interchangeability(self):
        for v in self.by_name.values():
            self.assertFalse(v["legacy_v1_abi_interchangeable"])
            self.assertIn("ABI",v["owner_review_required"])

    def test_33_static_markdown_lists_eight_sidecars(self):
        s=m.as_markdown(self.report)
        rows=[l for l in s.splitlines() if l.startswith("| v2_") or l.startswith("| strict_contract_v2")]
        self.assertEqual(len(rows),8)

    def test_34_static_markdown_names_two_known_breaks(self):
        s=m.as_markdown(self.report)
        self.assertIn("ReplayClock",s)
        self.assertIn("Evidence.verified",s)
        self.assertIn("NO-GO",s)

    def test_35_root_63_source_and_eight_V2_not_modified(self):
        self.assertEqual(self.report["source_upstream_sha"],
                         "cd90c1babae8912db31490ad614fc2ad2f868042")
        self.assertEqual(self.report["protected_main_sha"],
                         "4048f91beaaa3410116d97e35896c8b688384e19")


if __name__=="__main__":
    unittest.main()
