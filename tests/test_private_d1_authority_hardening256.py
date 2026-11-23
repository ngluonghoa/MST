"""§256 defend typed D1 boundaries against bypass of the source adapter.

Fixtures are invented values; never source/licence/backend confirmations.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
import unittest

from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import PriceBasis
from swing_trading.private_cache_source_bridge import (
    PrivateSourceDenied, PrivateD1Diagnostic, PrivateD1Reference,
    QuarantinedD1Bar, inspect_private_d1_snapshot,
    diagnose_private_d1_without_signals,
)
from test_private_cache_source_bridge import NOW, source


def refs(provider="SSI"):
    ref = inspect_private_d1_snapshot(source(provider), as_of_utc=NOW)
    return ref, ref.bars[-1]


class TypedQuarantineBar256(unittest.TestCase):
    def test_all_three_adapters_continue_to_normalize_without_authority(self):
        for provider in ("SSI", "DNSE", "VCBS"):
            with self.subTest(provider=provider):
                ref, bar = refs(provider)
                self.assertEqual(ref.provider, provider)
                self.assertEqual(len(ref.bars), 2)
                self.assertEqual(bar.close_vnd, Decimal("50500"))
                self.assertEqual(bar.volume_shares, 800)
                self.assertFalse(bar.eligible_for_signals)
                self.assertFalse(ref.eligible_for_signals)
                self.assertFalse(ref.source_is_appowned_publisher)
                self.assertEqual(ref.has_provisional_source, provider == "VCBS")

    def test_direct_construction_rejects_invalid_prices(self):
        _, b = refs()
        for field, value in (
            ("open_vnd", Decimal("NaN")),
            ("open_vnd", Decimal("Infinity")),
            ("high_vnd", Decimal("-1")),
            ("low_vnd", Decimal("0")),
            ("close_vnd", Decimal("1e10")),
            ("close_vnd", 50500),
            ("close_vnd", "50500"),
            ("close_vnd", True),
        ):
            with self.subTest(field=field, value=str(value)):
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "^MST_PRIVATE_BRIDGE_TYPED_PRICE_INVALID$"
                ):
                    replace(b, **{field: value})

    def test_direct_construction_rejects_bad_identity_and_types(self):
        _, b = refs()
        for field, value in (
            ("provider", "NOT_AN_ISSUER"),
            ("provider", None),
            ("symbol", "FPT/secret"),
            ("symbol", 10),
            ("trading_date", "2026-11-13"),
            ("trading_date", datetime(2026, 11, 13, tzinfo=timezone.utc)),
            ("reported_price_basis", "RAW"),
            ("provisional_source", 1),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PrivateSourceDenied, "BAD_IDENTITY"):
                    replace(b, **{field: value})

    def test_direct_construction_rejects_non_integer_and_overflow_volumes(self):
        _, b = refs()
        for value, code in (
            (False, "VOLUME_TYPE"),
            ("100", "VOLUME_TYPE"),
            (Decimal("100"), "VOLUME_TYPE"),
            (-1, "VOLUME_RANGE"),
            ((1 << 63), "VOLUME_RANGE"),
        ):
            with self.subTest(volume=str(value)):
                with self.assertRaisesRegex(PrivateSourceDenied, code):
                    replace(b, volume_shares=value)

    def test_ohlc_order_still_rejected(self):
        _, b = refs()
        for field, value in (
            ("low_vnd", Decimal("60000")),
            ("high_vnd", Decimal("49000")),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                PrivateSourceDenied, "OHLC_BAD_ORDER"
            ):
                replace(b, **{field: value})


class TypedQuarantineSource256(unittest.TestCase):
    def test_direct_source_claims_cannot_forge_production_authority(self):
        src, _ = refs()
        for field in (
            "source_is_appowned_publisher",
            "venue_close_attested",
            "issuer_first_known_attested",
            "eligible_for_signals",
            "eligible_for_backtest",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                PrivateSourceDenied, "^MST_PRIVATE_BRIDGE_AUTHORITY_FORGED$"
            ):
                replace(src, **{field: True})
        with self.assertRaisesRegex(PrivateSourceDenied, "AUTHORITY_FORGED"):
            replace(src, eligible_for_backtest=1)

    def test_provenance_mismatch_and_cross_source_rows_rejected(self):
        src, bar = refs()
        vcbs, _ = refs("VCBS")
        for change in (
            {"provider": "DNSE"},
            {"symbol": "HPG"},
            {"bars": (src.bars[0], vcbs.bars[1])},
            {"source_snapshot_day": date(2026, 11, 12)},
        ):
            with self.subTest(change=str(list(change))):
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "SOURCE_PARTITION_DRIFT"
                ):
                    replace(src, **change)

    def test_must_keep_unique_sorted_d1_sessions(self):
        src, _ = refs()
        for bars in (
            tuple(reversed(src.bars)),
            (src.bars[0], src.bars[0]),
        ):
            with self.subTest(days=str([b.trading_date for b in bars])):
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "DUPLICATE_OR_UNSORTED"
                ):
                    replace(src, bars=bars)

    def test_missing_or_mismatched_provisional_flag_rejected(self):
        for provider in ("SSI", "VCBS"):
            with self.subTest(provider=provider):
                src, _ = refs(provider)
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "PROVISIONAL_DRIFT"
                ):
                    replace(src, has_provisional_source=not src.has_provisional_source)
        src, _ = refs()
        with self.assertRaisesRegex(PrivateSourceDenied, "DIGEST_OR_ROWS"):
            replace(src, has_provisional_source="false")

    def test_digest_and_structure_cannot_be_overridden(self):
        src, _ = refs()
        for change in (
            {"raw_source_sha256": "f"},
            {"raw_source_sha256": 5},
            {"source_rows_observed": 1},
            {"source_rows_observed": True},
            {"source_rows_observed": 2049},
            {"bars": list(src.bars)},
            {"bars": tuple()},
            {"provider": None},
            {"symbol": "not-symbol"},
            {"source_snapshot_day": "2026-11-13"},
        ):
            with self.subTest(fields=list(change)):
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "DIGEST_OR_ROWS_INVALID"
                ):
                    replace(src, **change)

    def test_bar_class_is_not_interchangeable_with_random_object(self):
        src, _ = refs()
        with self.assertRaisesRegex(PrivateSourceDenied, "SOURCE_PARTITION_DRIFT"):
            replace(src, bars=(src.bars[0], {"fake_bar": True}))


class TypedQuarantineDiagnostic256(unittest.TestCase):
    def test_original_engine_remains_sixteen_unverified_both_strategies(self):
        for provider in ("SSI", "DNSE", "VCBS"):
            for strategy in (Strategy.SHORT, Strategy.SWING):
                with self.subTest(provider=provider, strategy=strategy):
                    diag = diagnose_private_d1_without_signals(
                        source(provider), strategy=strategy, as_of_utc=NOW,
                    )
                    self.assertEqual(len(diag.decisions), 16)
                    self.assertTrue(all(
                        d.status is DecisionStatus.UNVERIFIED and
                        d.strategy is strategy for d in diag.decisions
                    ))
                    self.assertFalse(diag.eligible_for_signals)
                    self.assertEqual(diag.trading_or_broker_calls, 0)

    def test_direct_diagnostic_authority_and_orders_are_forbidden(self):
        diag = diagnose_private_d1_without_signals(
            source("SSI"), strategy=Strategy.SWING, as_of_utc=NOW,
        )
        for change in (
            {"eligible_for_signals": True},
            {"eligible_for_signals": 1},
            {"trading_or_broker_calls": 1},
            {"trading_or_broker_calls": True},
            {"trading_or_broker_calls": "0"},
        ):
            with self.subTest(fields=list(change)):
                with self.assertRaisesRegex(
                    PrivateSourceDenied, "DIAGNOSTIC_AUTHORITY_FORGED"
                ):
                    replace(diag, **change)
        with self.assertRaisesRegex(PrivateSourceDenied, "DIAGNOSTIC_SOURCE_INVALID"):
            replace(diag, source="fake")
        with self.assertRaisesRegex(PrivateSourceDenied, "BAD_STRATEGY"):
            replace(diag, strategy="SWING")

    def test_asof_cannot_come_before_capture(self):
        diag = diagnose_private_d1_without_signals(
            source("SSI"), strategy=Strategy.SHORT, as_of_utc=NOW,
        )
        with self.assertRaisesRegex(PrivateSourceDenied, "RETROSPECTIVE_LOOKAHEAD"):
            replace(diag, as_of_utc=datetime(
                2026, 11, 12, 23, 59, tzinfo=timezone.utc,
            ))

    def test_errors_do_not_print_private_raw_data(self):
        src, bar = refs("DNSE")
        with self.assertRaises(PrivateSourceDenied) as caught:
            replace(bar, close_vnd=Decimal("NaN"))
        fixed_code = str(caught.exception)
        self.assertEqual(fixed_code, "MST_PRIVATE_BRIDGE_TYPED_PRICE_INVALID")
        self.assertNotIn(src.raw_source_sha256, fixed_code)


if __name__ == "__main__":
    unittest.main()
