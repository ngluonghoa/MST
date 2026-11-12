"""A03 candidate cache consumer: scope loss, current-state and numerical integrity tests.

Review-only: zero Drive read/write, zero licensed providers, zero release.
"""
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from scripts.m2_a02_incremental_cache_oracle_lab import (
    _apply, bar, identity, instant,
)
from scripts.m2_a03_v2_cache_consumer_contract import (
    SCHEMA, STATUS, FixtureV2ConsumerScope, fixture_scope,
    preview_v2_consumer, run_v2_consumer_contract_lab,
)
from swing_trading.incremental_cache import (
    Provider, SyntheticIncrementalStore,
)
from swing_trading.v2_cache_partition_plan import (
    FixtureHeadV2, FixturePartitionV2,
)


class V2CacheConsumerContractMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run_v2_consumer_contract_lab()
        cls.steps = {x["stage"]: x for x in cls.r["stages"]}

    def test_draft_contract_cannot_certify_v2_drive_parity(self):
        self.assertEqual(self.r["status"],
                         "V2_CONSUMER_DRAFT_CONTRACT_AND_V1_GOLDEN_DIFFERENTIAL_PASS")
        self.assertEqual(self.r["schema"], SCHEMA)
        self.assertEqual(self.r["stages_checked"], 4)
        self.assertEqual(self.r["bar_count"], 20)
        self.assertEqual(self.r["atr_first_valid_bar_index_1_based"], 14)
        self.assertFalse(self.r["v2_complete_drive_consumer_implemented"])
        self.assertFalse(self.r["production_cache_authorized"])
        self.assertFalse(self.r["trading_authorized"])

    def test_cold_empty_v2_head_is_only_candidate_plan(self):
        self.assertEqual(self.steps["COLD"]["v2_refresh_hint"], "EMPTY_PARTITION")
        self.assertFalse(self.steps["COLD"]["read_rights_verified"])

    def test_warm_same_bars_and_indicators(self):
        a, b = self.steps["COLD"], self.steps["WARM"]
        self.assertEqual(a["bar_revisions_digest"], b["bar_revisions_digest"])
        self.assertEqual(a["ema20_atr14_digest"], b["ema20_atr14_digest"])
        self.assertEqual(b["v2_refresh_hint"], "NEEDS_PROVIDER_REVALIDATION")

    def test_metadata_only_revision_changes_bar_lineage_not_indicator(self):
        a, b = self.steps["WARM"], self.steps["LINEAGE_ONLY"]
        self.assertNotEqual(a["bar_revisions_digest"], b["bar_revisions_digest"])
        self.assertEqual(a["ema20_atr14_digest"], b["ema20_atr14_digest"])

    def test_price_correction_changes_bar_and_indicator(self):
        a, b = self.steps["LINEAGE_ONLY"], self.steps["CORRECTION"]
        self.assertNotEqual(a["bar_revisions_digest"], b["bar_revisions_digest"])
        self.assertNotEqual(a["ema20_atr14_digest"], b["ema20_atr14_digest"])

    def test_changes_to_rights_must_be_bound_beyond_v2_partition_hash(self):
        self.assertTrue(self.r["v2_partition_hash_omits_rights_version"])
        self.assertTrue(self.r["full_binding_digest_changes_on_rights_revocation"])
        self.assertTrue(self.r["revoked_rights_cannot_reuse_existing_legacy_scope"])

    def test_historical_as_of_latest_materialized_denied(self):
        self.assertTrue(self.r["historical_as_of_from_latest_state_denied"])
        self.assertTrue(self.r["v2_metadata_head_is_untrusted"])

    def test_reproducible_fixture_preview(self):
        other = run_v2_consumer_contract_lab()
        self.assertEqual(self.r, other)

    def test_scope_fingerprints_contain_separate_project_namespaces(self):
        s = fixture_scope()
        self.assertEqual(s.legacy.project_id, "SwingTrading1.8")
        self.assertEqual(s.legacy.environment, "SYNTHETIC_TEST_ONLY")
        self.assertEqual(s.candidate.symbol, "FAKE001")
        self.assertEqual(s.candidate.provider_id, s.legacy.provider.value)
        self.assertEqual(len(s.binding_sha256), 64)


class ConsumerReadOnlyNegativeTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "cache.sqlite"
        self.store = SyntheticIncrementalStore(self.path)
        self.store.initialize()
        self.scope = fixture_scope()
        self.key = self.scope.legacy
        _apply(self.store, self.key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        self.head = FixtureHeadV2(
            self.scope.candidate.digest, 1, "a" * 64, instant(20),
        )

    def preview(self, *, scope=None, at=20, head=None):
        return preview_v2_consumer(
            self.store, self.scope if scope is None else scope,
            as_of_utc=instant(at), proposed_head=head,
        )

    def test_schema_untrusted_and_all_release_flags_false(self):
        x = self.preview(head=self.head)
        self.assertEqual(x["schema"], SCHEMA)
        self.assertEqual(x["status"], STATUS)
        self.assertEqual(x["bar_count"], 20)
        self.assertEqual(x["first_valid_atr14_bar_index_1_based"], 14)
        self.assertEqual(x["v2_refresh_hint"], "RECENT_METADATA")
        for flag in (
            "can_reconstruct_historical_as_of_from_latest_materialized",
            "source_entitlement_independently_verified",
            "v2_real_drive_manifest_or_bytes_read",
            "v2_cache_publisher_or_cas_implemented",
            "v2_authoritative_consumer_parity_verified",
            "owner_a02_a03_release_signed_off",
            "licensed_cache_read_authorized",
            "drive_write_authorized",
            "trading_authorized",
        ):
            with self.subTest(flag=flag):
                self.assertIs(x[flag], False)

    def test_legacy_policy_versions_are_not_discarded(self):
        x = self.preview()
        self.assertEqual(set(x["legacy_policy_versions"]), {
            "rights", "resolution", "quality", "adjustment", "calendar",
            "aggregation", "indicator", "indicator_parameters",
        })
        self.assertEqual(x["legacy_identity_sha256"], self.key.fingerprint)

    def test_each_v1_policy_version_changes_binding(self):
        fields = (
            "source_rights_policy_version", "source_resolution_policy_version",
            "quality_policy_version", "calendar_version",
            "aggregation_policy_version", "indicator_version",
            "indicator_parameter_version",
        )
        base = self.scope.binding_sha256
        for key in fields:
            with self.subTest(key=key):
                s = fixture_scope(replace(self.key, **{key: "VERSION.2"}))
                self.assertNotEqual(s.binding_sha256, base)
                self.assertEqual(s.candidate.digest, self.scope.candidate.digest)
                with self.assertRaisesRegex(PermissionError, "NOT_MATERIALIZED"):
                    self.preview(scope=s)

    def test_mismatched_provider_is_rejected(self):
        x = replace(self.scope.candidate, provider_id="DNSE")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH_PROVIDER"):
            replace(self.scope, candidate=x)

    def test_mismatched_endpoint_is_rejected(self):
        x = replace(self.scope.candidate, endpoint_id="synthetic.other")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH_ENDPOINT"):
            replace(self.scope, candidate=x)

    def test_mismatched_price_basis_is_rejected(self):
        x = replace(self.scope.candidate, price_basis="ADJUSTED")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH_BASIS"):
            replace(self.scope, candidate=x)

    def test_mismatched_timeframe_is_rejected(self):
        x = replace(self.scope.candidate, timeframe="M15")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH_TIMEFRAME"):
            replace(self.scope, candidate=x)

    def test_mismatched_adjustment_revision_is_rejected(self):
        x = replace(self.scope.candidate, source_revision_namespace="ADJ2")
        with self.assertRaisesRegex(ValueError, "SCOPE_MISMATCH_REVISION"):
            replace(self.scope, candidate=x)

    def test_mismatched_session_date_is_rejected(self):
        x = replace(self.scope.candidate, session_date_local=date(2026, 11, 10))
        with self.assertRaisesRegex(ValueError, "SESSION_MAP"):
            replace(self.scope, candidate=x)

    def test_missing_explicit_symbol_mapping_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INSTRUMENT_MAPPING"):
            replace(self.scope, mapped_candidate_symbol="OTHER")
        with self.assertRaisesRegex(ValueError, "INSTRUMENT_MAPPING"):
            replace(self.scope, accepted_legacy_instrument="OTHER")

    def test_nonexistent_new_rights_scope_cannot_read_prior_cache(self):
        new_scope = fixture_scope(replace(
            self.key, source_rights_policy_version="RIGHTS.REVOKED",
        ))
        with self.assertRaisesRegex(PermissionError, "NOT_MATERIALIZED"):
            self.preview(scope=new_scope)

    def test_v2_head_cross_partition_rejected(self):
        wrong = FixtureHeadV2("b" * 64, 1, "a" * 64, instant(20))
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_HEAD_REUSE"):
            self.preview(head=wrong)

    def test_v2_future_head_cannot_be_read_as_current(self):
        future = FixtureHeadV2(
            self.scope.candidate.digest, 1, "a" * 64, instant(21),
        )
        with self.assertRaisesRegex(ValueError, "FUTURE_HEAD_CANNOT_REWIND"):
            self.preview(head=future)

    def test_as_of_before_latest_materialized_cursor_is_denied(self):
        _apply(self.store, self.key, (bar(5, close=200, revision="r2"),),
               now=23, start=5, end=6)
        with self.assertRaisesRegex(PermissionError, "HISTORICAL_MATERIALIZED"):
            self.preview(at=22)

    def test_as_of_requiring_future_session_bar_is_rejected(self):
        with self.assertRaisesRegex(PermissionError, "HISTORICAL_MATERIALIZED"):
            self.preview(at=19)

    def test_unknown_key_in_same_synthetic_store_is_denied(self):
        empty = fixture_scope(replace(self.key, indicator_version="EMA20_NEW"))
        with self.assertRaisesRegex(PermissionError, "NOT_MATERIALIZED"):
            self.preview(scope=empty)

    def test_tampered_checkpoint_detected_by_independent_oracle(self):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE fixture_checkpoints SET ema20=? "
                      "WHERE cache_key=? AND start_utc=?",
                      ("999", self.key.fingerprint, bar(5).start_utc.isoformat()))
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_COLD_PARITY"):
            self.preview()

    def test_tampered_bar_content_digest_is_detected(self):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE fixture_bars SET c=? "
                      "WHERE cache_key=? AND start_utc=?",
                      ("101", self.key.fingerprint, bar(0).start_utc.isoformat()))
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            self.preview()

    def test_no_production_source_through_identity(self):
        with self.assertRaises(PermissionError):
            replace(self.key, environment="PRODUCTION")

    def test_incorrect_scope_or_head_type_denied(self):
        with self.assertRaises(TypeError):
            preview_v2_consumer(
                self.store, "not-typed", as_of_utc=instant(20),
                proposed_head=None,
            )
        with self.assertRaises(TypeError):
            self.preview(head=object())

    def test_naive_as_of_clock_denied(self):
        with self.assertRaisesRegex(TypeError, "EXPLICIT_UTC"):
            preview_v2_consumer(
                self.store, self.scope, as_of_utc=instant(20).replace(tzinfo=None),
                proposed_head=None,
            )

    def test_clock_offset_other_than_utc_denied(self):
        from datetime import timezone
        with self.assertRaisesRegex(ValueError, "UTC_ZERO_OFFSET"):
            preview_v2_consumer(
                self.store, self.scope,
                as_of_utc=instant(20).astimezone(timezone(timedelta(hours=7))),
                proposed_head=None,
            )


if __name__ == "__main__":
    unittest.main()
