"""Fictional-only exact-turnover VWAP candidate, no market data."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from swing_trading.market_data import Timeframe, PriceBasis
from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness
from swing_trading.session_calendar import CalendarSnapshot, SessionType, TradingSession
from swing_trading.source_quality import resolve_as_known
from swing_trading.vwap_contract343 import (
    TurnoverMeaning, TurnoverObservation, VwapAnchor, calculate_continuous_vwap,
    calculate_continuous_vwap_raw_matched,
)
from test_source_quality import candle

T = datetime(2000, 1, 3, 2, 15, tzinfo=timezone.utc)
END = T + timedelta(hours=4)
D = Decimal


def minute(n):
    return T + timedelta(minutes=n)


def calendar():
    def session(name, a, b, kind=SessionType.CONTINUOUS):
        return TradingSession("HOSE", T.date(), name, kind, minute(a), minute(b),
                              "fixture-calendar-v1", "fixture", "fixture", True)
    return CalendarSnapshot("HOSE", T.date(), "fixture-calendar-v1", "fixture", True,
                            (session("AM", 0, 2), session("PM", 100, 102),
                             session("ATC", 102, 103, SessionType.AUCTION)))


def item(n, *, volume=10, value="105", meaning=TurnoverMeaning.MATCHED_VND,
         session=None, basis=PriceBasis.RAW):
    base = candle()
    key = replace(base.market_bar_key, timeframe=Timeframe.M1,
                  bar_start_utc=minute(n), session_period_id=session or ("AM" if n < 2 else "PM"),
                  price_basis=basis)
    obs = replace(base.observation_key, market_bar_key=key)
    rev = replace(base.observation_revision, observation_key=obs,
                  source_revision_or_payload_digest=f"rev-{n}",
                  first_known_time_utc=minute(n+1), retrieved_at_utc=minute(n+2))
    event = f"event-{n}"
    row = replace(base, market_bar_key=key, observation_key=obs, observation_revision=rev,
                  bar_end_utc=minute(n+1), retrieved_at_utc=minute(n+2),
                  verified_at_utc=minute(n+3), observed_minutes=1, expected_minutes=1,
                  volume=volume, matched_value=None if value is None else D(value),
                  source_event_ids=(event,))
    return TurnoverObservation(resolve_as_known(key, (row,), END), meaning, event,
                               rev.source_revision_or_payload_digest, row.verified_at_utc, True)


def calc(items, **kw):
    args = dict(calendar=calendar(), through_utc=minute(102), as_of_utc=END)
    args.update(kw)
    return calculate_continuous_vwap(items, **args)


def sample():
    return item(0), item(1, value="115"), item(100, value="100"), item(101, value="120")


class VwapContract343(unittest.TestCase):
    def test_session_weighted_value_crosses_lunch_not_auction(self):
        r = calc(sample())
        self.assertEqual(r.value, D("11"))
        self.assertEqual(r.used_bar_count, 4)
        self.assertFalse(r.actionable)
        self.assertFalse(r.data_certified)

    def test_weighted_not_mean_of_prices(self):
        r = calc((item(0, volume=20, value="200"), item(1, value="120")),
                 through_utc=minute(2))
        self.assertEqual(r.value, D(320)/D(30))

    def test_proxy_even_if_numeric_bounds_hold(self):
        for mode in (TurnoverMeaning.CLOSE_TIMES_VOLUME, TurnoverMeaning.OHLC_PROXY,
                     TurnoverMeaning.UNKNOWN):
            with self.subTest(mode=mode):
                self.assertEqual(calc((item(0, meaning=mode), *sample()[1:])).reason,
                                 "TURNOVER_NOT_EXACT_MATCHED")

    def test_missing_or_out_of_bounds_value(self):
        for value, reason in ((None, "MATCHED_VALUE_MISSING"),
                              ("121", "MATCHED_VALUE_OUTSIDE_OHLC_VOLUME_BOUNDS")):
            self.assertEqual(calc((item(0, value=value), *sample()[1:])).reason, reason)

    def test_true_zero_vs_missing_and_all_zero(self):
        r = calc((item(0, volume=0, value="0"), *sample()[1:]))
        self.assertEqual(r.value, D(335)/D(30))
        self.assertIsNone(calc((item(0, volume=0, value="1"), *sample()[1:])).value)
        self.assertEqual(calc(tuple(item(n, volume=0, value="0")
                                   for n in (0, 1, 100, 101))).reason,
                         "ZERO_VOLUME_DENOMINATOR")

    def test_missing_duplicate_and_reordered_minute(self):
        a = sample()
        for seq in (a[1:], (a[0], a[0], *a[2:]), (a[1], a[0], *a[2:])):
            self.assertIsNone(calc(seq).value)

    def test_lunch_and_auction_cannot_enter(self):
        self.assertIsNone(calc((*sample(), item(102, session="ATC")),
                               through_utc=minute(103)).value)
        self.assertIsNone(calc((sample()[0], item(50), *sample()[2:])).value)

    def test_unverified_turnover_and_calendar(self):
        a = sample()
        self.assertEqual(calc((replace(a[0], semantics_verified=False), *a[1:])).reason,
                         "TURNOVER_SEMANTICS_UNVERIFIED")
        self.assertIsNone(calc(a, calendar=replace(calendar(), verified=False)).value)

    def test_event_revision_and_future_evidence(self):
        a = sample()
        for bad in (replace(a[0], source_event_id="different"),
                    replace(a[0], source_revision="different"),
                    replace(a[0], verified_at_utc=END+timedelta(minutes=1))):
            self.assertIsNone(calc((bad, *a[1:])).value)

    def test_adjusted_basis_never_used_for_raw_matched_value(self):
        self.assertIsNone(calc((item(0, basis=PriceBasis.ADJUSTED), *sample()[1:])).value)

    def test_anchor_revision_and_no_retroactive_knowledge(self):
        a = sample()
        anchor = VwapAnchor("event-1", "rev-1", minute(1), minute(2), minute(3))
        r = calc(a[1:], anchor=anchor)
        self.assertEqual(r.indicator_id, "ANCHORED_VWAP")
        self.assertEqual(r.value, D(335)/D(30))
        self.assertEqual(r.anchor_revision, "rev-1")
        for bad in (replace(anchor, source_revision="changed"),
                    replace(anchor, first_known_utc=END+timedelta(minutes=1),
                            verified_at_utc=END+timedelta(minutes=2))):
            self.assertIsNone(calc(a[1:], anchor=bad).value)

    def test_future_window_and_conflict(self):
        self.assertIsNone(calc(sample(), through_utc=END+timedelta(minutes=1)).value)
        a = sample()
        row = a[0].snapshot.selected
        conflict = resolve_as_known(row.market_bar_key, (row, row), END)
        self.assertIsNone(calc((replace(a[0], snapshot=conflict), *a[1:])).value)

    def test_unbounded_or_nonminute_calendar_rejected(self):
        cal = calendar()
        bad = replace(cal.sessions[0], end_utc=minute(0)+timedelta(days=2))
        long_calendar = replace(cal, sessions=(bad,))
        self.assertIsNone(calc(sample(), calendar=long_calendar).value)
        fractional = replace(cal.sessions[0], start_utc=minute(0)+timedelta(seconds=1),
                             end_utc=minute(2)+timedelta(seconds=1))
        self.assertIsNone(calc(sample(), calendar=replace(cal, sessions=(fractional,))).value)


def volume_witnesses(items):
    return tuple(VolumeBasisWitness(x.snapshot.selected, VolumeBasis.RAW_MATCHED_SHARES,
                                   "fictional-regime", f"volume-{i}", x.verified_at_utc)
                 for i, x in enumerate(items))


def strict_calc(items, witnesses=None, **kw):
    args = dict(calendar=calendar(), through_utc=minute(102), as_of_utc=END)
    args.update(kw)
    return calculate_continuous_vwap_raw_matched(
        items, witnesses=volume_witnesses(items) if witnesses is None else witnesses, **args)


class RawMatchedVwap359(unittest.TestCase):
    def test_session_and_anchor_preserve_arithmetic_only(self):
        a = sample()
        result = strict_calc(a)
        self.assertEqual(result.value, D("11"))
        self.assertFalse(result.data_certified)
        self.assertFalse(result.actionable)
        anchor = VwapAnchor("event-1", "rev-1", minute(1), minute(2), minute(3))
        self.assertEqual(strict_calc(a[1:], anchor=anchor).value, D(335)/D(30))

    def test_raw_price_does_not_establish_raw_volume(self):
        a = sample()
        w = volume_witnesses(a)
        for basis in (VolumeBasis.ADJUSTED_SHARES, VolumeBasis.ALL_TRADES_SHARES,
                      VolumeBasis.UNKNOWN):
            changed = (replace(w[0], basis=basis), *w[1:])
            self.assertEqual(strict_calc(a, changed).reason,
                             "RAW_MATCHED_VOLUME_WITNESS_UNVERIFIED")

    def test_missing_mutable_and_wrong_revision_witness(self):
        a = sample()
        w = volume_witnesses(a)
        for witnesses in (w[1:], list(w), (w[1], *w[1:])):
            self.assertIsNone(strict_calc(a, witnesses).value)

    def test_future_or_premature_witness(self):
        a = sample()
        w = volume_witnesses(a)
        for when in (END+timedelta(minutes=1), minute(0)):
            self.assertIsNone(strict_calc(a, (replace(w[0], verified_at_utc=when),
                                              *w[1:])).value)

    def test_share_regime_discontinuity(self):
        a = sample()
        w = volume_witnesses(a)
        self.assertEqual(strict_calc(a, (replace(w[0], share_regime_id="other"),
                                         *w[1:])).reason,
                         "SHARE_REGIME_CHANGED_WITHIN_VWAP_WINDOW")

    def test_legacy_turnover_gate_still_enforced(self):
        a = (item(0, meaning=TurnoverMeaning.CLOSE_TIMES_VOLUME), *sample()[1:])
        self.assertEqual(strict_calc(a).reason, "TURNOVER_NOT_EXACT_MATCHED")

    def test_overlap_in_source_event_union(self):
        a = sample()
        row = a[1].snapshot.selected
        row = replace(row, source_event_ids=(*row.source_event_ids, a[0].source_event_id))
        changed = (a[0], replace(a[1], snapshot=resolve_as_known(
            row.market_bar_key, (row,), END)), *a[2:])
        self.assertEqual(strict_calc(changed).reason, "DUPLICATE_SOURCE_EVENT")
