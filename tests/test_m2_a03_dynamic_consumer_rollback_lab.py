"""MST A03 dynamic original/V2 consumer paths and synthetic N/N-1 rollback.

No owner, data-source, cache or trading authority comes from these tests.
"""
from datetime import date, timedelta
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_dynamic_consumer_rollback_lab as m
from swing_trading.backtest import BacktestHarness
from swing_trading.causal import CausalMarketEvent
from swing_trading.contracts import DecisionStatus, Strategy, SignalDecision
from swing_trading.engineering_contracts import EngineeringPortRegistry
from swing_trading.strict_contract_v2 import StrictSignalDecisionV2
from swing_trading.v2_cache_partition_plan import (
    CandidateRefreshHint, FixtureHeadV2, FixturePartitionV2,
    plan_fixture_refresh,
)


class A03DynamicConsumerRollbackTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = m.build()
        cls.cases = {row["case"]:row for row in cls.report["cases"]}

    def case(self, name, group):
        self.assertIn(name,self.cases)
        self.assertEqual(self.cases[name]["group"],group)
        self.assertEqual(self.cases[name]["result"],"PASS_FIXTURE_ONLY")

    def test_01_fixed_schema(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_02_exact_42_executed_cases(self):
        self.assertEqual(self.report["case_count"],42)

    def test_03_no_duplicate_cases(self):
        self.assertEqual(len(self.cases),42)

    def test_04_case_digest_covers_case_content(self):
        expected=sha256(json.dumps(self.report["cases"],sort_keys=True,
              separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(self.report["case_sha256"],expected)

    def test_05_all_cases_explicitly_synthetic_only(self):
        self.assertTrue(all(row["result"]=="PASS_FIXTURE_ONLY"
                            for row in self.report["cases"]))

    def test_06_zero_a02_a03_owner_signoffs(self):
        self.assertEqual(self.report["a02_owner_signed"],0)
        self.assertEqual(self.report["a03_owner_signed"],0)

    def test_07_no_live_source_security_or_trading_approval(self):
        for field in ("automatic_compatibility_adapter_authorized",
                      "full_v1_v2_abi_or_behavior_certified",
                      "G01_G08_OA01_OA06_closed",
                      "real_source_rights_or_physical_drive_cache_proven",
                      "real_N_Nminus1_release_rollback_tested",
                      "production_or_trading_authorized"):
            self.assertIs(self.report[field],False)

    def test_08_two_additional_runtime_differences_recorded(self):
        self.assertEqual(len(self.report["new_compatibility_findings"]),2)
        self.assertTrue(all(x["owner_disposition"]=="NOT_SIGNED" for x in
                            self.report["new_compatibility_findings"]))

    def test_09_generator_differences(self):
        self.case("LEGACY_V1_GENERATOR_CONSUMED_BEFORE_FILTER","replay_difference")
        self.case("STRICT_V2_GENERATOR_MATERIALIZED_BEFORE_FILTER","replay_difference")

    def test_10_subclass_acceptance_differences(self):
        self.case("LEGACY_V1_SUBCLASS_EVENT_ACCEPTED","replay_difference")
        self.case("STRICT_V2_SUBCLASS_EVENT_DENIED","replay_difference")

    def test_11_list_case_event_visibility_equal(self):
        self.case("LIST_MARKET_SAME_VISIBLE_REVISIONS","replay")

    def test_12_first_known_future_causality(self):
        self.case("FUTURE_KNOWN_EVENT_BOTH_HIDDEN","replay")

    def test_13_sorted_event_revisions(self):
        self.case("SORTED_FIRST_KNOWN_REVISION_ORDER","replay")

    def test_14_no_double_market_fetch(self):
        self.case("MARKET_CALLED_ONCE_PER_SEPARATE_CONSUMER","replay")

    def test_15_untyped_event_rejected_both(self):
        self.case("V1_REJECTS_UNTYPED_MARKET_EVENT","replay")
        self.case("V2_REJECTS_UNTYPED_MARKET_EVENT","replay")

    def test_16_unverified_result_allowed(self):
        self.case("EXACT_UNVERIFIED_RULE_SUCCESS","rule")

    def test_17_one_rule_call_only(self):
        self.case("V2_RULE_EXECUTED_EXACTLY_ONCE","rule")

    def test_18_detected_and_not_detected_denied(self):
        self.case("V2_DETECTED_SELF_ATTESTED_RULE_DENIED","rule")
        self.case("V2_NOT_DETECTED_SELF_ATTESTED_RULE_DENIED","rule")

    def test_19_rule_identity_mismatch_denied(self):
        self.case("V2_RULE_WRONG_ZONE_ID_DENIED","rule")
        self.case("V2_RULE_WRONG_STRATEGY_DENIED","rule")

    def test_20_legacy_rule_type_no_implicit_adapter(self):
        self.case("V2_RULE_LEGACY_RESULT_TYPE_DENIED","rule")

    def test_21_prevalidation_does_not_invoke_rules(self):
        self.case("V2_BAD_ZONE_PRE_VALIDATION_NO_CALLBACK","rule")
        self.case("V2_BAD_STRATEGY_PRE_VALIDATION_NO_CALLBACK","rule")

    def test_22_truthy_legacy_evidence_is_not_authority(self):
        self.case("LEGACY_TRUTHY_EVIDENCE_IS_NOT_SOURCE_AUTHORITY","rule")

    def test_23_registry_n_to_nplusone_compatible_old_pin(self):
        self.case("PORT_N_TO_NPLUS1_OLD_CONSUMER_COMPATIBLE","registry")

    def test_24_registry_nplusone_to_n_rollback_old_pin(self):
        self.case("PORT_NPLUS1_TO_N_ROLLBACK_WITH_OLD_PIN","registry")

    def test_25_new_consumer_pin_blocks_downgrade(self):
        self.case("PORT_NEW_PIN_BLOCKS_N_MINUS_ONE_DOWNGRADE","registry")
        self.case("PORT_NO_PARTIAL_MUTATION_AFTER_REJECTED_DOWNGRADE","registry")

    def test_26_explicit_detach_allows_rollback_and_remove(self):
        self.case("PORT_ROLLBACK_AFTER_EXPLICIT_UNPIN","registry")
        self.case("PORT_PINNED_REMOVE_DENIED","registry")
        self.case("PORT_REMOVE_ONLY_AFTER_ALL_DETACHED","registry")

    def test_27_source_2_0_to_2_1_then_guarded_rollback(self):
        self.case("SOURCE_N_TO_NPLUS1_WITH_OLD_PIN","source")
        self.case("SOURCE_PINNED_NPLUS1_BLOCKS_ROLLBACK","source")
        self.case("SOURCE_ROLLBACK_AFTER_NEW_CONSUMER_DETACH","source")

    def test_28_source_no_cross_provider_switch(self):
        self.case("SOURCE_REFUSES_CROSS_PROVIDER_HOTSWAP","source")
        self.case("SOURCE_OTHER_PROVIDERS_UNTOUCHED","source")

    def test_29_source_no_delete_with_pins(self):
        self.case("SOURCE_PINNED_REMOVE_DENIED","source")
        self.case("SOURCE_REMOVE_AFTER_ALL_PINS_DETACHED","source")

    def test_30_cache_basis_and_revision_scoping(self):
        self.case("CACHE_PRICE_BASIS_NOT_INTERCHANGEABLE","cache")
        self.case("CACHE_REVISION_NAMESPACE_NOT_INTERCHANGEABLE","cache")

    def test_31_cache_future_head_and_staleness_fail_closed(self):
        self.case("CACHE_FUTURE_HEAD_REJECTED","cache")
        self.case("CACHE_STALE_METADATA_REQUIRES_REVALIDATION","cache")
        self.case("CACHE_RECENT_METADATA_ONLY_NOT_SOURCE_FRESHNESS","cache")

    def test_32_cache_does_not_authorize_external_io(self):
        self.case("CACHE_V2_PLANNER_NEVER_GRANTS_IO_OR_TRADING","cache")

    def test_33_previous_128_unverified_matrix_retained(self):
        self.case("PRIOR_128_UNVERIFIED_ONLY_DECISIONS_UNCHANGED","reference")

    def test_34_independent_one_pass_generator_reproduction(self):
        sample=m._events()[0]
        old=m._v1(m._Market((sample,),stream=True)).visible_events()
        strict=m._v2(m._Market((sample,),stream=True)).visible_events()
        self.assertEqual(old,())
        self.assertEqual(strict,(sample,))

    def test_35_independent_strict_negative_no_rule_promotion(self):
        reply=StrictSignalDecisionV2("B1",Strategy.SWING,DecisionStatus.DETECTED,
              (m.StrictEvidenceV2("synthetic",m.AT,True),))
        fake=m._Rules(reply)
        harness=m._v2(m._Market(),fake)
        with self.assertRaises(PermissionError):
            harness.evaluate_unverified("B1",Strategy.SWING)
        self.assertEqual(fake.calls,1)

    def test_36_independent_registry_atomic_rollback_denial(self):
        reg=EngineeringPortRegistry()
        p20,p21=m._desc("2.0.0"),m._desc("2.1.0")
        a20,a21=m._Adapter(),m._Adapter()
        reg.add(p20,a20)
        reg.bind_consumer("consumer.new",p21) if False else None
        reg.replace(p20,p21,a21)
        reg.bind_consumer("consumer.new",p21)
        with self.assertRaises(ValueError):
            reg.replace(p20,p20,a20)
        self.assertIs(reg.resolve(p21),a21)

    def test_37_independent_cache_freshness_untrusted(self):
        p=FixturePartitionV2("SSI","fixture.ssi.d1","TEST","M5",
              date(2026,11,10),"RAW","REV_A")
        h=FixtureHeadV2(p.digest,1,"f"*64,m.AT)
        self.assertEqual(plan_fixture_refresh(
            p,h,checked_at_utc=m.AT+timedelta(minutes=6)
        ).hint,CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION)
        self.assertFalse(plan_fixture_refresh(
            p,h,checked_at_utc=m.AT+timedelta(minutes=4)
        ).source_freshness_verified)


if __name__ == "__main__":
    import unittest
    unittest.main()
