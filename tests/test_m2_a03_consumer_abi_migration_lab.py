"""A03 isolated original-V1/V2 consumer ABI differential and denial QA."""
from datetime import timedelta
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_consumer_abi_migration_lab as m
from swing_trading.contracts import DecisionStatus, Evidence, SignalDecision, Strategy
from swing_trading.replay import ReplayClock
from swing_trading.strict_contract_v2 import (
    StrictReplayClockV2, StrictEvidenceV2,
    decode_untrusted_v2_json, legacy_to_v2_unverified,
    v2_to_legacy_unverified,
)
from swing_trading.engineering_contracts import check_port
from scripts.m2_a03_behavior_equivalence_lab import V1_MARKET_PORT
from swing_trading.v2_replay_port import V2_MARKET_PORT


class ConsumerAbiMigrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = m.build()
        cls.by_name = {row["case"]: row for row in cls.report["cases"]}

    def assert_case(self, key, area):
        self.assertEqual(self.by_name[key]["area"], area)
        self.assertEqual(self.by_name[key]["result"], "PASS_SYNTHETIC_ONLY")

    def test_01_schema_is_unapproved_v1(self):
        self.assertEqual(self.report["schema"], m.SCHEMA)

    def test_02_exact_26_cases(self):
        self.assertEqual(self.report["case_count"], 26)

    def test_03_unique_case_names(self):
        self.assertEqual(len(self.by_name), 26)

    def test_04_case_sha_fingerprint_is_content_based(self):
        s=json.dumps(self.report["cases"],sort_keys=True,separators=(",",":"))
        self.assertEqual(self.report["case_sha256"],sha256(s.encode()).hexdigest())

    def test_05_all_synthetic_checks_have_expected_result(self):
        self.assertTrue(all(row["result"]=="PASS_SYNTHETIC_ONLY"
                            for row in self.report["cases"]))

    def test_06_only_two_known_contract_breaks(self):
        self.assertEqual(self.report["intentional_noninterchangeable_legacy_contracts"],(
            "ReplayClock.as_of_utc_direct_rewind","Evidence.verified_truthy_nonboolean"))

    def test_07_only_empty_evidence_unverified_adapter(self):
        self.assertEqual(self.report["approved_adapters"],
                         "EMPTY_EVIDENCE_UNVERIFIED_ONLY")

    def test_08_human_owner_remains_unsigned(self):
        self.assertEqual(self.report["owner_a02_signed"],0)
        self.assertEqual(self.report["owner_a03_signed"],0)

    def test_09_neither_v1_nor_v2_runtime_modified(self):
        self.assertFalse(self.report["original_v1_modified"])
        self.assertFalse(self.report["preexisting_eight_v2_modules_modified"])

    def test_10_external_and_production_gates_false(self):
        for key in ("full_v1_v2_abi_parity_proven",
                    "real_vendor_rights_or_live_cache_proven",
                    "independent_G01_G08_and_OA01_OA06_closed",
                    "production_or_trading_authorized"):
            self.assertIs(self.report[key],False)

    def test_11_legacy_clock_compatibility_packet(self):
        self.assert_case("LEGACY_PUBLIC_CLOCK_REWIND_PRESERVED","clock")

    def test_12_strict_clock_rewind_packet(self):
        self.assert_case("STRICT_PUBLIC_CLOCK_REWIND_DENIED","clock")

    def test_13_legacy_integer_evidence_packet(self):
        self.assert_case("LEGACY_TRUTHY_INTEGER_IS_NOT_BOOLEAN","evidence")

    def test_14_strict_integer_evidence_denial_packet(self):
        self.assert_case("STRICT_NONBOOLEAN_EVIDENCE_REJECTED","evidence")

    def test_15_upgrade_and_rollback_packet(self):
        self.assert_case("EXPLICIT_EMPTY_UNVERIFIED_UPGRADE_DOWNGRADE","migration")

    def test_16_no_legacy_classified_promotion(self):
        self.assert_case("LEGACY_DETECTED_NOT_AUTOMIGRATED","migration")

    def test_17_no_classified_downgrade(self):
        self.assert_case("V2_CLASSIFIED_RECORD_NOT_DOWNGRADED","migration")

    def test_18_no_untrusted_detected_wire(self):
        self.assert_case("UNTRUSTED_DETECTED_WIRE_DENIED","wire")

    def test_19_no_duplicate_json_member(self):
        self.assert_case("UNTRUSTED_DUPLICATE_JSON_KEY_DENIED","wire")

    def test_20_bidirectional_consumer_major_isolation(self):
        for key in ("V1_MARKET_PORT_REJECTS_V2_MAJOR",
                    "V2_MARKET_PORT_REJECTS_V1_MAJOR",
                    "V2_RULE_PORT_REJECTS_V1_MAJOR"):
            self.assert_case(key,"consumer_ports")

    def test_21_no_implicit_harness_clock_substitution(self):
        self.assert_case("V1_BACKTEST_CONSUMER_REJECTS_V2_CLOCK","consumer_ports")
        self.assert_case("V2_REPLAY_CONSUMER_REJECTS_V1_CLOCK","consumer_ports")

    def test_22_source_rights_and_scope_denials(self):
        self.assert_case("SOURCE_PROBE_SELF_CLAIM_CANNOT_GRANT_RIGHTS","source")
        self.assert_case("CROSS_PROVIDER_CONSUMER_SCOPE_DENIED","source")

    def test_23_cache_cross_version_cross_provider_denials(self):
        for key in ("PROVIDER_PARTITION_ISOLATION","FOREIGN_PARTITION_HEAD_DENIED",
                    "V2_CACHE_PLAN_NEVER_AUTHORIZES_IO",
                    "LEGACY_UNVERIFIED_SOURCE_BLOCKS_FETCH",
                    "CROSS_VERSION_CACHE_OBJECT_NOT_DROPIN"):
            self.assert_case(key,"cache")

    def test_24_prior_safe_128_case_behavior_not_promoted(self):
        self.assert_case("PRIOR_128_UNVERIFIED_DIFFERENTIAL_RETAINED","replay")

    def test_25_direct_negative_injections_are_still_rejected(self):
        old=ReplayClock(m.AT)
        old.as_of_utc=m.AT-timedelta(seconds=1)
        self.assertLess(old.as_of_utc,m.AT)
        strict=StrictReplayClockV2(m.AT)
        with self.assertRaises(ValueError):
            strict.as_of_utc=m.AT-timedelta(seconds=1)
        self.assertEqual(strict.as_of_utc,m.AT)
        self.assertIs(type(Evidence("synthetic",m.AT,1).verified),int)
        with self.assertRaises(TypeError):
            StrictEvidenceV2("synthetic",m.AT,1)
        self.assertFalse(check_port(V1_MARKET_PORT,V2_MARKET_PORT,m.FixtureMarket()).compatible)
        old_decision=SignalDecision("B1",Strategy.SWING,DecisionStatus.UNVERIFIED)
        self.assertEqual(v2_to_legacy_unverified(legacy_to_v2_unverified(old_decision)),
                         old_decision)
        with self.assertRaises(PermissionError):
            decode_untrusted_v2_json(
                '{"schema":"mst.signal_decision.v2","zone_id":"B1","strategy":"SWING",'
                '"status":"NOT_DETECTED","evidence":[]}'
            )


if __name__=="__main__":
    import unittest
    unittest.main()
