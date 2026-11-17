"""§210 fabricated full-session HOSE label coverage and ATO/ATC boundaries.

All labels and prices are synthetic "AAA". Source PDF is an official public
trading-schedule reference only. No SSI vendor timestamp, source close,
minute-first-known, symbol board-regime, date-specific calendar or rights are
proved; neither a full M15 nor H1 candidate may be used as a signal.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
import unittest

from swing_trading.hose_session_geometry210 import (
    CandidateWindow, ClockPhase, HoseClockDenied, HoseSessionState,
    SsiQueryMode, WindowLabelState, OFFICIAL_HOSE_SCHEDULE, SCHEMA,
    schedule_phase, inspect_mode_scoped_ssi_label,
    inspect_hose_ssi_regular_schedule_candidate,
)
from swing_trading.market_data import Timeframe

DAY = date(2026,11,10)
NOW = datetime(2026,11,10,8,15,tzinfo=timezone.utc)
VN = timezone(timedelta(hours=7))


def fmt(minute):
    return f"10/11/2026 {minute//60:02d}:{minute%60:02d}:00"


def fake():
    minutes=(
        list(range(9*60+15,11*60+30))
        +list(range(13*60,14*60+30))
        +[14*60+45]
    )
    ticks=[]
    for m in reversed(minutes):
        ticks.append({
            "symbol":"AAA", "trading_date":fmt(m),
            "open":"10000","high":"10200","low":"9900","close":"10100",
            "volume":"7" if m!=14*60+45 else "31",
        })
    return {"status":"ok","data":{"ticks":ticks}}


def inspect(payload=None, *, asof=NOW, vol=1606, **params):
    return inspect_hose_ssi_regular_schedule_candidate(
        fake() if payload is None else payload,
        symbol=params.pop("symbol","AAA"),
        trading_day=params.pop("trading_day",DAY),
        as_of_utc=asof,
        daily_matched_volume=vol,
        **params,
    )


class HoseSourceClock210Tests(unittest.TestCase):
    def test_official_ato_continuous_lunch_atc_and_post_atc_boundaries(self):
        cases=[
            (time(8,59), ClockPhase.OUTSIDE),
            (time(9,0), ClockPhase.ATO),
            (time(9,14),ClockPhase.ATO),
            (time(9,15),ClockPhase.CONTINUOUS_AM),
            (time(11,29),ClockPhase.CONTINUOUS_AM),
            (time(11,30),ClockPhase.LUNCH),
            (time(12,59),ClockPhase.LUNCH),
            (time(13,0),ClockPhase.CONTINUOUS_PM),
            (time(14,29),ClockPhase.CONTINUOUS_PM),
            (time(14,30),ClockPhase.ATC),
            (time(14,44),ClockPhase.ATC),
            (time(14,45),ClockPhase.POST_ATC),
            (time(14,59),ClockPhase.POST_ATC),
            (time(15,0),ClockPhase.OUTSIDE),
        ]
        for clock,phase in cases:
            with self.subTest(clock=clock):
                self.assertIs(schedule_phase(clock),phase)

    def test_ssi_range_dayfirst_and_latest_monthfirst_are_mode_scoped(self):
        row,p1=inspect_mode_scoped_ssi_label(
            "17/11/2026 14:45:00",
            session_day=date(2026,11,17),
            mode=SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,
        )
        latest,p2=inspect_mode_scoped_ssi_label(
            "11/17/2026 14:45:00",
            session_day=date(2026,11,17),
            mode=SsiQueryMode.LATEST_MONTH_FIRST_OBSERVED,
        )
        self.assertEqual(row,latest)
        self.assertIs(p1,ClockPhase.POST_ATC)
        self.assertIs(p2,ClockPhase.POST_ATC)

    def test_ssi_mode_crossover_never_reinterprets_date_automatically(self):
        for mode,label in (
            (SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,"11/17/2026 14:45:00"),
            (SsiQueryMode.LATEST_MONTH_FIRST_OBSERVED,"17/11/2026 14:45:00"),
        ):
            with self.subTest(mode=mode),self.assertRaises(HoseClockDenied):
                inspect_mode_scoped_ssi_label(
                    label,session_day=date(2026,11,17),mode=mode,
                )

    def test_ambiguous_11_11_date_is_not_source_verified(self):
        for mode in SsiQueryMode:
            t,p=inspect_mode_scoped_ssi_label(
                "11/11/2026 09:15:00",session_day=date(2026,11,11),
                mode=mode,
            )
            self.assertEqual(t,time(9,15))
            self.assertIs(p,ClockPhase.CONTINUOUS_AM)
        r=inspect()
        self.assertFalse(r.provider_minute_label_semantics_verified)

    def test_bad_session_clock_seconds_date_type_and_mode_rejected(self):
        for field in (
            {"raw":"10/11/2026 09:15:30"},
            {"raw":"10/11/2026 99:15:00"},
            {"raw":"10/11/2026 09:15:00","mode":"range"},
            {"raw":"10/11/2026 09:15:00","session_day":datetime(2026,11,10)},
        ):
            args=dict(
                raw="10/11/2026 09:15:00",
                mode=SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,
                session_day=DAY,
            )
            args.update(field)
            with self.subTest(field=field),self.assertRaises(HoseClockDenied):
                inspect_mode_scoped_ssi_label(**args)
        with self.assertRaises(HoseClockDenied):
            schedule_phase(time(9,15,1))

    def test_exact_synthetic_225_continuous_and_one_auction_layout(self):
        r=inspect()
        self.assertIs(r.state,HoseSessionState.OBSERVED_SCHEDULE_SHAPE_UNVERIFIED)
        self.assertEqual(r.schema,SCHEMA)
        self.assertEqual(r.official_schedule_reference,OFFICIAL_HOSE_SCHEDULE)
        self.assertEqual(r.regular_minute_label_count,225)
        self.assertEqual(r.missing_expected_labels,0)
        self.assertEqual(r.unexpected_label_count,0)
        self.assertTrue(r.auction_1445_captured)
        self.assertEqual(len(r.m15),15)
        self.assertEqual(len(r.h1),5)
        self.assertEqual(sum(w.expected_labels for w in r.m15),225)
        self.assertEqual(sum(w.observed_labels for w in r.m15),225)
        self.assertTrue(all(w.state is WindowLabelState.LABELS_PRESENT_UNVERIFIED
                            for w in r.m15))
        self.assertTrue(all(not w.action_eligible for w in r.h1))
        self.assertFalse(r.m15_source_qualified)
        self.assertFalse(r.h1_source_qualified)
        self.assertFalse(r.action_eligible)

    def test_m15_windows_do_not_cross_lunch(self):
        r=inspect()
        self.assertEqual(
            [(w.session,w.start_local,w.end_local) for w in r.m15
             if w.end_local in ("11:30","14:30")],
            [("MORNING","11:15","11:30"),("AFTERNOON","14:15","14:30")],
        )
        self.assertFalse(any(w.start_local<"13:00"<w.end_local
                             for w in r.m15))

    def test_h1_candidate_late_morning_and_afternoon_are_partial(self):
        r=inspect()
        self.assertEqual(
            [(x.start_local,x.end_local,x.expected_labels,x.state)
             for x in r.h1],
            [
                ("09:15","10:15",60,WindowLabelState.LABELS_PRESENT_UNVERIFIED),
                ("10:15","11:15",60,WindowLabelState.LABELS_PRESENT_UNVERIFIED),
                ("11:15","11:30",15,WindowLabelState.PARTIAL_SESSION_WINDOW),
                ("13:00","14:00",60,WindowLabelState.LABELS_PRESENT_UNVERIFIED),
                ("14:00","14:30",30,WindowLabelState.PARTIAL_SESSION_WINDOW),
            ],
        )
        self.assertFalse(r.h1_source_qualified)

    def test_ato_atc_cannot_be_silently_amalgamated_to_regular_m15(self):
        with_extra=fake()
        with_extra["data"]["ticks"].append({
            "symbol":"AAA","trading_date":"10/11/2026 09:00:00",
            "open":"10000","high":"10000","low":"10000","close":"10000",
            "volume":"0",
        })
        r=inspect(with_extra,vol=1606)
        self.assertEqual(r.unexpected_label_count,1)
        self.assertIs(r.state,HoseSessionState.MISSING_OR_EXTRA_LABELS_UNVERIFIED)
        self.assertEqual(r.regular_minute_label_count,225)
        self.assertFalse(r.action_eligible)

    def test_1445_candidate_is_not_1430_regular_or_normal_minute(self):
        r=inspect()
        self.assertTrue(r.auction_1445_captured)
        self.assertEqual(r.m15[-1].end_local,"14:30")
        self.assertEqual(r.h1[-1].end_local,"14:30")
        self.assertNotIn("14:45",[w.end_local for w in r.m15])

    def test_one_missing_continuous_label_is_unknown_not_zero_trade(self):
        payload=fake()
        payload["data"]["ticks"]=[
            x for x in payload["data"]["ticks"]
            if not x["trading_date"].endswith("10:00:00")
        ]
        r=inspect(payload,vol=1599)
        self.assertIs(r.state,HoseSessionState.MISSING_OR_EXTRA_LABELS_UNVERIFIED)
        self.assertEqual(r.missing_expected_labels,1)
        self.assertEqual(r.regular_minute_label_count,224)
        minute=[w for w in r.m15
                if w.start_local=="10:00" and w.session=="MORNING"]
        self.assertEqual(len(minute),1)
        self.assertIs(minute[0].state,WindowLabelState.LABELS_MISSING_UNCLASSIFIED)
        self.assertEqual(minute[0].observed_labels,14)
        self.assertFalse(r.m15_source_qualified)

    def test_missing_morning_segment_does_not_shift_other_anchor_windows(self):
        payload=fake()
        payload["data"]["ticks"]=[
            x for x in payload["data"]["ticks"]
            if not "10:20:" in x["trading_date"]
        ]
        r=inspect(payload,vol=1599)
        self.assertEqual(r.m15[0].start_local,"09:15")
        self.assertEqual(r.h1[1].start_local,"10:15")
        self.assertEqual(r.h1[1].missing_labels,1)
        self.assertEqual(r.h1[2].expected_labels,15)

    def test_missing_auction_is_not_a_full_session_after_close(self):
        payload=fake()
        payload["data"]["ticks"]=[
            x for x in payload["data"]["ticks"]
            if not "14:45:" in x["trading_date"]
        ]
        r=inspect(payload,vol=1575)
        self.assertFalse(r.auction_1445_captured)
        self.assertEqual(r.regular_minute_label_count,225)
        self.assertIs(r.state,HoseSessionState.MISSING_OR_EXTRA_LABELS_UNVERIFIED)

    def test_ssi_session_after_asof_future_is_blocked(self):
        t=datetime(2026,11,10,3,0,tzinfo=timezone.utc)
        r=inspect(asof=t)
        self.assertIs(r.state,HoseSessionState.BLOCKED)
        self.assertEqual(r.reason,"SOURCE_LABEL_FUTURE_VS_AS_OF")
        self.assertEqual(r.m15,())

    def test_previous_utc_day_is_not_current_session(self):
        asof=datetime(2026,11,9,8,15,tzinfo=timezone.utc)
        r=inspect(asof=asof)
        self.assertIs(r.state,HoseSessionState.BLOCKED)
        self.assertEqual(r.reason,"SESSION_NOT_YET_OBSERVED_AS_OF")

    def test_unknown_board_regime_cannot_claim_independent_attestation(self):
        with self.assertRaisesRegex(HoseClockDenied,"BOARD_REGIME_CLAIM"):
            inspect(regular_board_regime_independently_attested=True)
        r=inspect()
        self.assertFalse(r.venue_day_and_board_regime_verified)
        self.assertFalse(r.source_retention_rights_verified)

    def test_duplicate_or_out_of_order_minute_fails_existing_209_guard(self):
        payload=fake()
        payload["data"]["ticks"].append(dict(payload["data"]["ticks"][-1]))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_REORDERED"):
            inspect(payload)
        payload=fake()
        payload["data"]["ticks"].reverse()
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_REORDERED"):
            inspect(payload)

    def test_bad_minute_price_or_volume_fails_existing_209_guard(self):
        for field,val in (("high","0"),("volume","-1"),("open","NaN")):
            payload=fake()
            payload["data"]["ticks"][12][field]=val
            with self.subTest(field=field),self.assertRaises(ValueError):
                inspect(payload)

    def test_ssi_range_vs_latest_cross_mode_session_row_is_rejected(self):
        payload=fake()
        payload["data"]["ticks"][0]["trading_date"]="11/17/2026 14:45:00"
        with self.assertRaises(ValueError):
            inspect(payload)

    def test_no_fake_trading_approval_via_frozen_replace(self):
        r=inspect()
        for field in (
            "m15_source_qualified","h1_source_qualified","action_eligible",
            "provider_minute_label_semantics_verified",
            "venue_day_and_board_regime_verified",
            "first_known_and_revision_verified",
            "history_pagination_verified","source_retention_rights_verified",
        ):
            with self.subTest(field=field),self.assertRaises(HoseClockDenied):
                replace(r,**{field:True})

    def test_window_cannot_pretend_closed_or_future_signal(self):
        r=inspect()
        window=r.m15[0]
        for bad in (
            {"action_eligible":True},
            {"provider_clock_attested":True},
            {"provider_first_known_attested":True},
            {"price_aggregation_approved":True},
            {"missing_labels":2},
            {"expected_labels":60},
        ):
            with self.subTest(bad=bad),self.assertRaises(HoseClockDenied):
                replace(window,**bad)

    def test_no_prices_or_provider_source_bars_are_exposed_by_geometry(self):
        r=inspect()
        d=r.__dict__
        self.assertNotIn("ohlc",d)
        self.assertNotIn("close",d)
        self.assertNotIn("volume",d)
        for w in r.m15+r.h1:
            self.assertNotIn("open",w.__dict__)
            self.assertNotIn("price",w.__dict__)
            self.assertNotIn("volume",w.__dict__)
        self.assertEqual(r.regular_minute_label_count,225)

    def test_no_timestamp_data_is_authorized_from_identical_labels(self):
        a=inspect()
        b=inspect(deepcopy(fake()))
        self.assertEqual(a,b)
        self.assertFalse(a.first_known_and_revision_verified)
        self.assertFalse(a.provider_minute_label_semantics_verified)
        self.assertFalse(a.h1_source_qualified)

    def test_negative_malformed_input_types_denied(self):
        for params in (
            {"symbol":"aaa"},
            {"symbol":"AAA/B"},
            {"trading_day":datetime(2026,11,10)},
        ):
            with self.subTest(params=params),self.assertRaises(ValueError):
                inspect(**params)
        with self.assertRaises(ValueError):
            inspect(asof=NOW.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            inspect({"status":"error","error":{"code":"UNEXPECTED"}})

    def test_malformed_candidate_constructor_fails_closed(self):
        r=inspect()
        with self.assertRaises(HoseClockDenied):
            replace(r,official_schedule_reference="unverified/selfsigned")
        with self.assertRaises(HoseClockDenied):
            replace(r,m15=())
        with self.assertRaises(HoseClockDenied):
            replace(r,state=HoseSessionState.BLOCKED)
        with self.assertRaises(HoseClockDenied):
            CandidateWindow(
                Timeframe.M15,"MORNING","09:15","09:30",
                15,15,0,WindowLabelState.PARTIAL_SESSION_WINDOW,
            )


if __name__=="__main__":
    unittest.main()
