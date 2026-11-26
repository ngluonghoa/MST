"""§381 signed SMA50 candidate arithmetic with fictional D1 bars."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest

from swing_trading.causal_indicators import (
    IndicatorState, calculate_d1_sma50_delta_candidate,
)
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import CoverageState, QualityState, resolve_as_known
from test_causal_indicators import AS_OF, make_bar, snap


def history(direction=1, n=60):
    start = AS_OF - timedelta(days=100)
    rows = []
    for i in range(n):
        price = Decimal(100 + direction * i)
        rows.append(snap(make_bar(i, start=start + timedelta(days=i),
                                 open_price=price, high=price + 1, low=price - 1,
                                 close=price)))
    return tuple(rows)


def calculate(rows, lookback=10, **kwargs):
    return calculate_d1_sma50_delta_candidate(rows, lookback=lookback,
                                             as_of_utc=AS_OF, **kwargs)


class Sma50Candidate381Tests(unittest.TestCase):
    def test_rising_falling_flat_signed_math_without_authority(self):
        for direction in (1, -1, 0):
            with self.subTest(direction=direction):
                result = calculate(history(direction))
                self.assertEqual(result.earlier_sma50, Decimal(100) + Decimal("24.5") * direction)
                self.assertEqual(result.delta, Decimal(10 * direction))
                self.assertEqual(result.delta_per_supplied_bar, Decimal(direction))
                self.assertEqual(result.used_bar_count, 60)
                self.assertEqual(result.state, IndicatorState.COMPUTED_UNCALIBRATED)
                self.assertFalse(result.data_certified)
                self.assertFalse(result.parameter_approved)
                self.assertFalse(result.actionable)

    def test_exact_windows_and_explicit_nondefault_lookback(self):
        self.assertEqual(calculate(history(n=57), lookback=7).delta, Decimal(7))
        for rows in (history(n=59), history(n=61), list(history())):
            result = calculate(rows)
            self.assertEqual(result.state, IndicatorState.BLOCKED)
            self.assertIsNone(result.delta)
            self.assertEqual(result.used_bar_count, 0)
        for lookback in (True, 0, -1, 463, 10.0, None):
            with self.subTest(lookback=lookback), self.assertRaises(ValueError):
                calculate(history(), lookback=lookback)
        with self.assertRaises(TypeError):
            calculate_d1_sma50_delta_candidate(history(), as_of_utc=AS_OF)

    def test_causal_cutoff_and_no_naive_clock(self):
        rows = history()
        cutoff = rows[-1].selected.verified_at_utc - timedelta(seconds=1)
        self.assertEqual(calculate(rows, known_before_utc=cutoff).reason,
                         "BAR_NOT_QUALIFIED_AT_CUTOFF")
        with self.assertRaises(ValueError):
            calculate(rows, known_before_utc=AS_OF.replace(tzinfo=None))

    def test_duplicate_reorder_and_mixed_timeframe_block(self):
        rows = history()
        cases = (rows[:5] + (rows[4],) + rows[6:],
                 rows[:5] + (rows[6], rows[5]) + rows[7:],
                 rows[:-1] + (snap(make_bar(99, timeframe=Timeframe.H1,
                                            start=rows[-1].selected.market_bar_key.bar_start_utc)),))
        for case in cases:
            self.assertEqual(calculate(case).state, IndicatorState.BLOCKED)

    def test_source_scope_quality_and_coverage_block(self):
        rows = history()
        c = rows[8].selected
        changed = (replace(c, quality_state=QualityState.UNVERIFIED),
                   replace(c, coverage_state=CoverageState.SESSION_PARTIAL),
                   replace(c, observation_revision=replace(c.observation_revision,
                                                            adjustment_revision="changed")))
        for row in changed:
            self.assertEqual(calculate(rows[:8] + (snap(row),) + rows[9:]).state,
                             IndicatorState.BLOCKED)

    def test_revision_conflict_blocks_entire_window(self):
        rows = history()
        c = rows[0].selected
        other_rev = replace(c.observation_revision, source_revision_or_payload_digest="other",
                            first_known_time_utc=c.bar_end_utc + timedelta(minutes=2),
                            retrieved_at_utc=c.retrieved_at_utc + timedelta(minutes=2))
        other = replace(c, observation_revision=other_rev,
                        retrieved_at_utc=other_rev.retrieved_at_utc,
                        verified_at_utc=other_rev.retrieved_at_utc + timedelta(minutes=1))
        conflict = resolve_as_known(c.market_bar_key, (c, other), AS_OF)
        result = calculate((conflict,) + rows[1:])
        self.assertEqual(result.state, IndicatorState.BLOCKED)
        self.assertIsNone(result.earlier_sma50)
