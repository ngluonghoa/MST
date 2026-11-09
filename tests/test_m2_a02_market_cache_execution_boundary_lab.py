"""A02 real inherited market/revision/cache/VN fixture boundary regressions.

The expected 'gaps' here are contract distinctions, not evidence of deployed
rights or full V2 parity. The original 63 V1 source blobs remain untouched.
"""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D
import unittest

from scripts.m2_a02_market_cache_execution_boundary_lab import (
    T0, build_candles, minute, run_boundary_matrix,
)
from swing_trading.cache_fetch_planner import (
    SourceCapability, SourceCursor, RefreshAction, plan_refresh,
)
from swing_trading.market_data import (
    BarClosure, PriceBasis, Quality,
)
from swing_trading.replay_batch import replay_frame
from swing_trading.source_quality import (
    CoverageState, QualityState, LifecycleState,
)
from swing_trading.v2_cache_partition_plan import (
    FixturePartitionV2, FixtureHeadV2, CandidateRefreshHint, plan_fixture_refresh,
)
from swing_trading.vn_backtest_execution_fixture import (
    VNAction, VNSyntheticFill, VNSyntheticRules, VNBarVerdict,
    calculate_fixture_vn_trade, inspect_fixture_vn_long_exit_bar,
    require_vn_backtest_release,
)


class ActualCandleBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = run_boundary_matrix()

    def test_all_six_explicit_timepoints(self):
        self.assertEqual(
            [r["minute"] for r in self.receipt["candle_snapshots"]],
            [14, 15, 20, 24, 25, 30],
        )
        self.assertEqual(self.receipt["first_known_revision_boundaries_checked"], 6)

    def test_legacy_simple_quality_necessary_at_bar_close(self):
        self.assertEqual(
            [r["legacy_simple_quality_necessary"] for r in self.receipt["candle_snapshots"]],
            [False, True, True, True, True, True],
        )

    def test_v12_requires_verification_beyond_first_known_time(self):
        self.assertEqual(
            [r["v12_source_prerequisites"] for r in self.receipt["candle_snapshots"]],
            [False, False, False, False, True, True],
        )
        self.assertTrue(self.receipt["simple_v1_and_v12_prerequisites_not_interchangeable"])

    def test_v12_revision_known_before_qualification_is_not_actionable(self):
        data = self.receipt["candle_snapshots"]
        self.assertEqual([r["v12_revision_visible"] for r in data],
                         [False, True, True, True, True, True])
        self.assertTrue(all(not r["source_authority_independently_attested"] for r in data))

    def test_canonical_zero_volume_is_valid_but_missing_volume_not(self):
        legacy, rich = build_candles()
        self.assertEqual((legacy.volume, rich.volume), (0, 0))
        self.assertTrue(legacy.eligible_for_confirmed_signals(minute(25)))
        self.assertTrue(rich.confirmation_prerequisites(minute(25)))
        self.assertFalse(replace(legacy, volume=None).eligible_for_confirmed_signals(minute(30)))
        self.assertFalse(replace(rich, volume=None).confirmation_prerequisites(minute(30)))

    def test_open_partial_unknown_basis_never_qualifies(self):
        base, rich = build_candles()
        self.assertFalse(replace(base, closure=BarClosure.OPEN).eligible_for_confirmed_signals(minute(30)))
        self.assertFalse(replace(rich, lifecycle_state=LifecycleState.OPEN).confirmation_prerequisites(minute(30)))
        self.assertFalse(replace(rich, coverage_state=CoverageState.SPARSE_UNVERIFIED)
                         .confirmation_prerequisites(minute(30)))
        self.assertFalse(replace(rich, quality_state=QualityState.UNVERIFIED)
                         .confirmation_prerequisites(minute(30)))
        self.assertFalse(replace(base, quality=Quality.UNVERIFIED)
                         .eligible_for_confirmed_signals(minute(30)))
        self.assertFalse(replace(base, market_bar_key=replace(
            base.market_bar_key, price_basis=PriceBasis.UNKNOWN,
        )).eligible_for_confirmed_signals(minute(30)))

    def test_v12_caller_supplied_entitlement_is_not_externally_verified(self):
        _, rich = build_candles()
        self.assertTrue(rich.confirmation_prerequisites(minute(30)))
        unapproved = replace(rich, provenance=replace(
            rich.provenance, entitlement_verified=False,
        ))
        self.assertFalse(unapproved.confirmation_prerequisites(minute(30)))
        self.assertFalse(self.receipt["vendor_source_evidence_independently_authenticated"])

    def test_v12_calendar_cutoff_or_quality_flags_fail_closed(self):
        _, rich = build_candles()
        self.assertFalse(replace(rich, calendar_cutoff_verified=False)
                         .confirmation_prerequisites(minute(30)))
        self.assertFalse(replace(rich, quality_flags=frozenset({"UNKNOWN_SOURCE_TIME"}))
                         .confirmation_prerequisites(minute(30)))

    def test_exact_retransmissions_are_deduplicated(self):
        self.assertEqual(self.receipt["exact_retransmissions_removed"], 2)
        _, rich = build_candles()
        result = replay_frame((rich.market_bar_key,), (rich, rich, rich), minute(30))
        self.assertEqual(result.bars[0].resolution.visible_candidate_count, 1)

    def test_same_revision_identity_different_payload_blocks(self):
        _, rich = build_candles()
        alter = replace(rich, close=D("11.5"), raw_digest_sha256="c" * 64)
        result = replay_frame((rich.market_bar_key,), (rich, alter), minute(30)).bars[0]
        self.assertTrue(result.revision_identity_collision)
        self.assertIsNone(result.resolution.selected)
        self.assertFalse(result.source_prerequisites_at(minute(30)))

    def test_future_correction_cannot_appear_in_prior_snapshot(self):
        _, rich = build_candles()
        revision = replace(
            rich.observation_revision, source_revision_or_payload_digest="r2",
            first_known_time_utc=minute(40), retrieved_at_utc=minute(41),
        )
        later = replace(rich, observation_revision=revision,
                        retrieved_at_utc=minute(41), verified_at_utc=minute(42))
        current = replay_frame((rich.market_bar_key,), (rich, later), minute(30)).bars[0]
        future = replay_frame((rich.market_bar_key,), (rich, later), minute(50)).bars[0]
        self.assertEqual(current.resolution.selected, rich)
        self.assertEqual(future.resolution.reason, "SOURCE_OR_REVISION_CONFLICT")
        self.assertIsNone(future.resolution.selected)

    def test_synthetic_replay_is_not_market_permission(self):
        self.assertFalse(self.receipt["production_cache_authorized"])
        self.assertFalse(self.receipt["a02_63_owner_dispositions_approved"])
        self.assertFalse(self.receipt["trading_authorized"])


class DifferentCacheContractTests(unittest.TestCase):
    def cursor(self):
        return SourceCursor(minute(0), minute(25), minute(22))

    def v1_plan(self, *, minute_now=28, capability=SourceCapability.WINDOWED):
        return plan_refresh(
            now_utc=minute(minute_now), session_start_utc=minute(0),
            latest_expected_closed_start_utc=minute(0),
            bar_duration=timedelta(minutes=15), capability=capability,
            cursor=self.cursor(),
        )

    def partition(self):
        return FixturePartitionV2(
            "SSI", "fixture.ssi.d1", "FAKE001", "M15",
            date(2026, 11, 6), "RAW", "SYNTHETIC.R1",
        )

    def test_v1_planner_reuse_revalidate_full_correction(self):
        self.assertEqual(self.v1_plan().action, RefreshAction.REUSE_CLOSED)
        self.assertEqual(self.v1_plan(minute_now=30).action, RefreshAction.REQUEST_WINDOW)
        self.assertEqual(self.v1_plan(minute_now=55).action,
                         RefreshAction.REQUEST_FULL_SESSION)
        self.assertEqual(
            self.v1_plan(minute_now=55).reason, "CORRECTION_RECONCILIATION_DUE",
        )

    def test_v1_unknown_provider_capability_blocks(self):
        p = self.v1_plan(capability=SourceCapability.UNKNOWN)
        self.assertEqual(p.action, RefreshAction.BLOCKED)
        self.assertFalse(p.data_authorized)
        self.assertFalse(p.certified_source_freshness)

    def test_v2_recent_metadata_never_certifies_real_provider_head(self):
        partition = self.partition()
        head = FixtureHeadV2(partition.digest, 1, "a" * 64, minute(25))
        hint = plan_fixture_refresh(partition, head, checked_at_utc=minute(28))
        self.assertIs(hint.hint, CandidateRefreshHint.RECENT_METADATA)
        self.assertFalse(hint.source_freshness_verified)
        self.assertFalse(hint.can_fetch_market_data)
        self.assertFalse(hint.can_read_licensed_cache)
        self.assertFalse(hint.can_write_drive)
        self.assertFalse(hint.permission_to_trade)

    def test_v2_five_minute_hint_requires_revalidation_not_automatic_fetch(self):
        partition = self.partition()
        head = FixtureHeadV2(partition.digest, 1, "a" * 64, minute(25))
        h = plan_fixture_refresh(partition, head, checked_at_utc=minute(30))
        self.assertIs(h.hint, CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION)
        self.assertFalse(h.can_fetch_market_data)

    def test_v2_cross_provider_head_reuse_is_denied(self):
        partition = self.partition()
        changed = replace(partition, provider_id="DNSE", endpoint_id="fixture.dnse.d1")
        head = FixtureHeadV2(partition.digest, 1, "a" * 64, minute(25))
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION_HEAD_REUSE_DENIED"):
            plan_fixture_refresh(changed, head, checked_at_utc=minute(30))

    def test_v2_future_metadata_cannot_rewind_clock(self):
        partition = self.partition()
        head = FixtureHeadV2(partition.digest, 1, "a" * 64, minute(40))
        with self.assertRaisesRegex(ValueError, "FUTURE_HEAD_CANNOT_REWIND_CLOCK"):
            plan_fixture_refresh(partition, head, checked_at_utc=minute(30))

    def test_v1_and_v2_planners_have_different_public_semantics(self):
        x = run_boundary_matrix()
        self.assertEqual(x["v1_refresh_hints"], [
            "REUSE_CLOSED", "REQUEST_WINDOW", "REQUEST_FULL_SESSION",
        ])
        self.assertEqual(x["v2_refresh_hints"], [
            "RECENT_METADATA", "NEEDS_PROVIDER_REVALIDATION",
        ])
        self.assertFalse(x["v2_market_data_replay_and_vn_backtest_parity_implemented"])
        self.assertTrue(x["v1_and_v2_cache_contracts_are_not_equivalent"])


class VnCashEquityReferenceTests(unittest.TestCase):
    def fixture(self):
        rules = VNSyntheticRules(
            "HOSE", 100, D("0.1"), D("8"), D("20"),
            D("0.001"), D("0.001"), D("0.001"),
        )
        entry = VNSyntheticFill(
            "FAKE001", "HOSE", VNAction.BUY, 100, D("10"),
            minute(0), minute(1), 1,
        )
        exit_fill = VNSyntheticFill(
            "FAKE001", "HOSE", VNAction.EXIT_LONG_SELL, 100, D("12"),
            minute(60), minute(61), 4,
        )
        return rules, entry, exit_fill

    def test_only_supplied_synthetic_settlement_index_scores(self):
        rules, entry, exit_fill = self.fixture()
        metric = calculate_fixture_vn_trade(
            entry, exit_fill, rules,
            exit_allowed_from_session=3, as_of_utc=minute(70),
        )
        self.assertEqual(metric.gross_pnl, D("200"))
        self.assertEqual(metric.net_pnl, D("196.6"))
        self.assertFalse(metric.validated_backtest)
        self.assertFalse(metric.live_action_eligible)

    def test_unsettled_or_unknown_settlement_index_rejected(self):
        rules, entry, exit_fill = self.fixture()
        for release in (None, 5):
            with self.subTest(release=release), self.assertRaises(ValueError):
                calculate_fixture_vn_trade(
                    entry, exit_fill, rules,
                    exit_allowed_from_session=release, as_of_utc=minute(70),
                )

    def test_earlier_unverified_exit_fill_cannot_score_future(self):
        rules, entry, exit_fill = self.fixture()
        with self.assertRaisesRegex(ValueError, "future-known"):
            calculate_fixture_vn_trade(
                entry, exit_fill, rules,
                exit_allowed_from_session=3, as_of_utc=minute(60),
            )

    def test_wrong_symbol_or_oversell_denied(self):
        rules, entry, exit_fill = self.fixture()
        for mutated in (
            replace(exit_fill, symbol="FAKE002"),
            replace(exit_fill, shares=200),
        ):
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                calculate_fixture_vn_trade(
                    entry, mutated, rules,
                    exit_allowed_from_session=3, as_of_utc=minute(70),
                )

    def test_stop_and_target_same_bar_is_ambiguous_not_fill(self):
        actual = inspect_fixture_vn_long_exit_bar(
            entry=D("10"), stop=D("9"), target=D("11"),
            low=D("8.5"), high=D("11.5"),
            bar_closed_utc=minute(15), bar_known_utc=minute(25),
            decision_utc=minute(30),
        )
        self.assertEqual(actual, VNBarVerdict.AMBIGUOUS_BOTH)
        self.assertEqual(run_boundary_matrix()["vn_both_stop_and_target_touched"],
                         "AMBIGUOUS_BOTH")

    def test_future_known_bar_cannot_generate_exit_scenario(self):
        with self.assertRaisesRegex(ValueError, "Look-ahead"):
            inspect_fixture_vn_long_exit_bar(
                entry=D("10"), stop=D("9"), target=D("11"),
                low=D("8.5"), high=D("11.5"),
                bar_closed_utc=minute(15), bar_known_utc=minute(40),
                decision_utc=minute(30),
            )

    def test_real_backtest_and_trading_release_remain_denied(self):
        with self.assertRaises(PermissionError):
            require_vn_backtest_release()
        x = run_boundary_matrix()
        self.assertFalse(x["calendar_and_t_plus_two_certified"])
        self.assertFalse(x["real_broker_fill_verified"])
        self.assertFalse(x["trading_authorized"])

    def test_observation_fingerprint_is_reproducible_not_attestation(self):
        first, second = run_boundary_matrix(), run_boundary_matrix()
        self.assertEqual(first["synthetic_observation_sha256"],
                         second["synthetic_observation_sha256"])
        self.assertEqual(len(first["synthetic_observation_sha256"]), 64)
        self.assertFalse(first["vendor_source_evidence_independently_authenticated"])


if __name__ == "__main__":
    unittest.main()
