"""§190: strictly synthetic 21-session cross-provider D1 QA; no live issuer."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

from scripts.mst_private_d1_cross_provider_audit import (
    audit_common_tail, DENIAL,
)
from swing_trading.market_data import PriceBasis
from swing_trading.private_cache_source_bridge import (
    PrivateD1Reference, PrivateSourceDenied, QuarantinedD1Bar,
)

NOW = datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)
END = date(2026, 11, 13)


def fixture(provider: str, n: int) -> PrivateD1Reference:
    bars = []
    first = END - timedelta(days=n - 1)
    # The calendar here is deliberately FICTIONAL; no venue-close claim.
    for i in range(n):
        d = first + timedelta(days=i)
        price = Decimal(1000) + Decimal((d - date(2026, 1, 1)).days) * 10
        bars.append(QuarantinedD1Bar(
            provider, "FPT", d, price, price + 5, price - 5, price,
            2000 if d == END else 1000,
            PriceBasis.RAW if provider == "VCBS" else PriceBasis.UNKNOWN,
        ))
    return PrivateD1Reference(
        provider, "FPT", END, "a" * 64, n, tuple(bars), False,
    )


def trio(a: int = 62, b: int = 248, c: int = 70):
    return (fixture("SSI", a), fixture("DNSE", b), fixture("VCBS", c))


class StrictCrossProviderD1(unittest.TestCase):
    def test_different_prehistory_lengths_same_21_tail_stays_nonactionable(self):
        result = audit_common_tail(trio(), as_of_utc=NOW)
        self.assertEqual(result["providers"], ["SSI", "DNSE", "VCBS"])
        self.assertEqual(result["source_rows_by_provider"],
                         {"SSI": 62, "DNSE": 248, "VCBS": 70})
        self.assertEqual(result["native_tail_days_each"], 21)
        self.assertEqual(result["aligned_last_day"], "2026-11-13")
        self.assertEqual(result["numerical_ohlcv_difference_days"], 0)
        self.assertEqual(result["numerical_close_difference_days"], 0)
        self.assertEqual(result["numerical_volume_difference_days"], 0)
        self.assertTrue(result["atr_references_numerically_equal"])
        self.assertTrue(result["rvol_all_three_available"])
        self.assertTrue(result["rvol_references_numerically_equal"])
        self.assertEqual(set(result["aligned_seed21_atr14_reference"].values()),
                         {"15"})
        self.assertEqual(set(result["aligned_prior20_rvol_reference"].values()),
                         {"2"})
        self.assertFalse(result["adjustment_basis_comparability_attested"])
        self.assertFalse(result["official_venue_close_attested"])
        self.assertFalse(result["issuer_first_known_attested"])
        self.assertFalse(result["eligible_for_signal_or_backtest"])
        self.assertFalse(result["cache_published"])
        self.assertEqual(result["trade_orders"], 0)
        self.assertEqual(result["status"], "PRIVATE_REFERENCE_ONLY_NO_TRADE")
        self.assertNotIn("source_rows", result)

    def test_numeric_price_revision_is_detected_not_promoted(self):
        a, b, c = trio()
        bars = list(c.bars)
        changed = bars[-10]
        bars[-10] = replace(changed, close_vnd=changed.close_vnd + Decimal(1))
        c = replace(c, bars=tuple(bars), raw_source_sha256="b" * 64)
        receipt = audit_common_tail((a, b, c), as_of_utc=NOW)
        self.assertEqual(receipt["numerical_ohlcv_difference_days"], 1)
        self.assertEqual(receipt["numerical_close_difference_days"], 1)
        self.assertEqual(receipt["numerical_volume_difference_days"], 0)
        self.assertFalse(receipt["atr_references_numerically_equal"])
        self.assertFalse(receipt["provider_winner_selected"])
        self.assertFalse(receipt["eligible_for_signal_or_backtest"])

    def test_volume_disagreement_without_price_disagreement(self):
        a, b, c = trio()
        rows = list(b.bars)
        rows[-1] = replace(rows[-1], volume_shares=3000)
        b = replace(b, bars=tuple(rows), raw_source_sha256="c" * 64)
        receipt = audit_common_tail((a, b, c), as_of_utc=NOW)
        self.assertEqual(receipt["numerical_ohlcv_difference_days"], 1)
        self.assertEqual(receipt["numerical_close_difference_days"], 0)
        self.assertEqual(receipt["numerical_volume_difference_days"], 1)
        self.assertTrue(receipt["atr_references_numerically_equal"])
        self.assertFalse(receipt["rvol_references_numerically_equal"])

    def test_missing_one_day_cannot_be_hidden_by_intersection(self):
        a, b, c = trio()
        rows = tuple(row for row in c.bars
                     if row.trading_date != END - timedelta(days=5))
        c = replace(c, bars=rows, source_rows_observed=len(rows))
        with self.assertRaisesRegex(PrivateSourceDenied, "TAIL_NOT_ALIGNED"):
            audit_common_tail((a, b, c), as_of_utc=NOW)

    def test_wrong_provider_symbol_and_not_three_inputs_are_denied(self):
        a, b, c = trio()
        bad_symbol = replace(c, symbol="HPG")
        duplicate = replace(c, provider="SSI",
                            bars=tuple(replace(x, provider="SSI") for x in c.bars))
        for values in ((a, b), (a, a, c), (a, b, bad_symbol),
                       (a, b, duplicate), [a, b, c]):
            with self.subTest(values=str(type(values))):
                with self.assertRaisesRegex(PrivateSourceDenied, DENIAL):
                    audit_common_tail(values, as_of_utc=NOW)

    def test_past_asof_future_capture_and_promoted_authority_denied(self):
        a, b, c = trio()
        with self.assertRaises(PrivateSourceDenied):
            audit_common_tail((a, b, c),
                              as_of_utc=datetime(2026, 11, 12,
                                                 tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            audit_common_tail((a, b, c), as_of_utc=datetime(2026, 11, 15))
        for key in ("eligible_for_signals", "eligible_for_backtest",
                    "venue_close_attested", "issuer_first_known_attested",
                    "source_is_appowned_publisher"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(PrivateSourceDenied, DENIAL):
                    audit_common_tail((a, b, replace(c, **{key: True})),
                                      as_of_utc=NOW)

    def test_short_series_unsorted_or_invalid_price_denied(self):
        a, b, c = trio()
        short = fixture("VCBS", 20)
        unsorted = replace(c, bars=tuple(reversed(c.bars)))
        rows = list(c.bars)
        rows[-1] = replace(rows[-1], low_vnd=Decimal(0))
        invalid = replace(c, bars=tuple(rows))
        for x in (short, unsorted, invalid):
            with self.subTest(kind=str(x.source_rows_observed)):
                with self.assertRaisesRegex(PrivateSourceDenied, DENIAL):
                    audit_common_tail((a, b, x), as_of_utc=NOW)

    def test_zero_denominator_rvol_yields_null_and_no_data_certification(self):
        a, b, c = trio()
        result = []
        for s in (a, b, c):
            rows = tuple(replace(row, volume_shares=0)
                         for row in s.bars)
            result.append(replace(s, bars=rows))
        receipt = audit_common_tail(tuple(result), as_of_utc=NOW)
        self.assertEqual(receipt["aligned_prior20_rvol_reference"],
                         {"SSI": None, "DNSE": None, "VCBS": None})
        self.assertFalse(receipt["rvol_all_three_available"])
        self.assertFalse(receipt["rvol_references_numerically_equal"])
        self.assertFalse(receipt["calendar_completeness_attested"])
        self.assertFalse(receipt["source_licence_attested"])


if __name__ == "__main__":
    unittest.main()
