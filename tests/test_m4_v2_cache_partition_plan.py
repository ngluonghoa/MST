"""M4 synthetic Drive-key and incremental refresh preflight tests.

No real Google Drive CRUD, no market-data access, no cache database I/O.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import unittest

from swing_trading.v2_cache_partition_plan import (
    CandidateRefreshHint, FixtureHeadV2, FixturePartitionV2,
    plan_fixture_refresh,
)

NOW = datetime(2026, 11, 9, 2, tzinfo=timezone.utc)
DAY = date(2026, 11, 9)
FAKE_SHA = "a" * 64


def partition(provider="SSI", symbol="FAKE001", timeframe="M5", basis="RAW",
              endpoint=None, day=DAY, revision="SRCREV_A"):
    return FixturePartitionV2(
        provider, endpoint or f"fixture.{provider.lower()}.d1", symbol,
        timeframe, day, basis, revision,
    )


def head(key=None, checked=NOW, generation=1):
    return FixtureHeadV2(
        (partition() if key is None else key).digest,
        generation, FAKE_SHA, checked,
    )


class ExactPartitionIsolationTests(unittest.TestCase):
    def test_deterministic_key_is_only_test_namespace(self):
        p = partition()
        self.assertEqual(p.digest, partition().digest)
        self.assertEqual(len(p.digest), 64)
        self.assertTrue(p.proposed_drive_key.startswith("MST_V2_TEST_ONLY/SSI/"))
        self.assertTrue(p.proposed_drive_key.endswith(p.digest + ".manifest.json"))
        self.assertNotIn("access_token", p.proposed_drive_key)

    def test_provider_name_changes_digest_even_same_symbol(self):
        keys = [partition(provider=p).digest for p in ("SSI", "DNSE", "VCBS", "FOURTH")]
        self.assertEqual(len(set(keys)), len(keys))

    def test_symbol_timeframe_session_basis_revision_and_endpoint_each_change_identity(self):
        base = partition()
        alternatives = (
            replace(base, symbol="FAKE002"),
            replace(base, timeframe="M15"),
            replace(base, timeframe="H1"),
            replace(base, timeframe="D1"),
            replace(base, session_date_local=date(2026, 11, 10)),
            replace(base, price_basis="ADJUSTED"),
            replace(base, source_revision_namespace="SRCREV_B"),
            replace(base, endpoint_id="fixture.ssi.intraday"),
        )
        for item in alternatives:
            with self.subTest(item=item):
                self.assertNotEqual(item.digest, base.digest)
        self.assertEqual(len({x.digest for x in alternatives}), len(alternatives))

    def test_raw_and_adjusted_cannot_share_a_head(self):
        a, b = partition(basis="RAW"), partition(basis="ADJUSTED")
        with self.assertRaisesRegex(ValueError, "CROSS_PARTITION"):
            plan_fixture_refresh(b, head(a), checked_at_utc=NOW)

    def test_different_provider_head_is_not_reused(self):
        ssi = partition(provider="SSI")
        for p in ("DNSE", "VCBS", "FOURTH"):
            with self.subTest(provider=p), self.assertRaises(ValueError):
                plan_fixture_refresh(partition(provider=p), head(ssi), checked_at_utc=NOW)

    def test_same_symbol_different_timeframe_head_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_fixture_refresh(partition(timeframe="H1"), head(partition(timeframe="M5")),
                                 checked_at_utc=NOW)

    def test_source_revision_namespace_prevents_stale_cross_revision_reuse(self):
        with self.assertRaises(ValueError):
            plan_fixture_refresh(partition(revision="SRCREV_B"), head(partition()),
                                 checked_at_utc=NOW)

    def test_bad_symbol_endpoint_and_source_revision_fail_closed(self):
        for x in ("", "FAKE/001", "fake001", None, 2):
            with self.subTest(symbol=x), self.assertRaises(ValueError):
                partition(symbol=x)
        for x in ("../token", "https://provider.example", ""):
            with self.subTest(endpoint=x), self.assertRaises(ValueError):
                replace(partition(), endpoint_id=x)
        for x in ("", "rev one", "rev/1", None):
            with self.subTest(revision=x), self.assertRaises(ValueError):
                partition(revision=x)

    def test_invalid_market_timeframe_or_price_basis_rejected(self):
        for x in ("M1", "W1", "m5", "", None):
            with self.subTest(tf=x), self.assertRaises(ValueError):
                partition(timeframe=x)
        for x in ("MIXED", "RAW+ADJUSTED", "", None):
            with self.subTest(basis=x), self.assertRaises(ValueError):
                partition(basis=x)

    def test_session_date_must_be_date_not_datetime(self):
        for item in (NOW, "2026-11-09", None):
            with self.subTest(value=item), self.assertRaises(TypeError):
                partition(day=item)

    def test_untrusted_sha_or_boolean_generation_rejected(self):
        with self.assertRaises(ValueError):
            FixtureHeadV2("not a digest", 0, FAKE_SHA, NOW)
        with self.assertRaises(ValueError):
            FixtureHeadV2(partition().digest, 1, "Z" * 64, NOW)
        for generation in (-1, True, 1.5, "2"):
            with self.subTest(gen=generation), self.assertRaises(ValueError):
                head(generation=generation)

    def test_head_metadata_cannot_be_reassigned(self):
        old = head()
        with self.assertRaises(FrozenInstanceError):
            old.partition_digest = partition(provider="VCBS").digest


class FiveMinutePlanningTests(unittest.TestCase):
    def test_miss_says_empty_but_never_fetches(self):
        result = plan_fixture_refresh(partition(), None, checked_at_utc=NOW)
        self.assertIs(result.hint, CandidateRefreshHint.EMPTY_PARTITION)
        self.assertFalse(result.can_fetch_market_data)
        self.assertFalse(result.can_read_licensed_cache)
        self.assertFalse(result.can_write_drive)
        self.assertFalse(result.source_freshness_verified)
        self.assertFalse(result.permission_to_trade)

    def test_recent_metadata_hint_is_not_market_freshness(self):
        old = head(checked=NOW)
        value = plan_fixture_refresh(partition(), old,
                                     checked_at_utc=NOW + timedelta(minutes=4))
        self.assertIs(value.hint, CandidateRefreshHint.RECENT_METADATA)
        self.assertFalse(value.source_freshness_verified)
        self.assertFalse(value.can_read_licensed_cache)

    def test_exact_five_minute_boundary_requires_provider_revalidation(self):
        value = plan_fixture_refresh(partition(), head(),
                                     checked_at_utc=NOW + timedelta(minutes=5))
        self.assertIs(value.hint, CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION)
        self.assertFalse(value.can_fetch_market_data)

    def test_later_checks_never_auto_trigger_provider_or_drive_io(self):
        for d in (6, 10, 60, 1440):
            with self.subTest(minutes=d):
                plan = plan_fixture_refresh(partition(), head(),
                                            checked_at_utc=NOW + timedelta(minutes=d))
                self.assertIs(plan.hint, CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION)
                self.assertFalse(plan.can_fetch_market_data)
                self.assertFalse(plan.can_write_drive)

    def test_future_head_or_rewound_scan_denied(self):
        with self.assertRaisesRegex(ValueError, "FUTURE_HEAD"):
            plan_fixture_refresh(partition(), head(checked=NOW + timedelta(minutes=1)),
                                 checked_at_utc=NOW)

    def test_non_utc_check_time_is_rejected(self):
        for bad in (
            NOW.replace(tzinfo=None),
            NOW.astimezone(timezone(timedelta(hours=7))),
            "2026-11-09T02:00Z",
        ):
            with self.subTest(value=bad), self.assertRaises((TypeError, ValueError)):
                plan_fixture_refresh(partition(), None, checked_at_utc=bad)

    def test_head_from_another_instrument_is_rejected_before_reuse(self):
        with self.assertRaises(ValueError):
            plan_fixture_refresh(partition(symbol="FAKE002"),
                                 head(partition(symbol="FAKE001")), checked_at_utc=NOW)

    def test_one_to_five_to_twenty_symbols_keep_distinct_planned_keys(self):
        names = [f"FAKE{i:03d}" for i in range(1, 21)]
        first = {s: partition(symbol=s).digest for s in names[:1]}
        five = {s: partition(symbol=s).digest for s in names[:5]}
        twenty = {s: partition(symbol=s).digest for s in names}
        self.assertEqual(first["FAKE001"], five["FAKE001"])
        self.assertEqual(five["FAKE001"], twenty["FAKE001"])
        self.assertEqual(len(set(twenty.values())), 20)
        self.assertFalse(plan_fixture_refresh(partition(symbol="FAKE001"), None,
                                              checked_at_utc=NOW).can_write_drive)

    def test_no_stored_chunk_data_or_entitlement_in_partitions(self):
        p = partition()
        self.assertFalse(hasattr(p, "candles"))
        self.assertFalse(hasattr(p, "access_token"))
        self.assertFalse(hasattr(p, "rights_verified"))
        self.assertFalse(hasattr(p, "source_timestamp_verified"))


if __name__ == "__main__":
    unittest.main()
