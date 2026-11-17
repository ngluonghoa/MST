"""§209 FICTIONAL SSI intraday minute snapshot; no real exchange data."""
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from unittest import TestCase

from swing_trading.ssi_intraday_session_probe209 import (
    MinuteProbeDenied, MinuteProbeState,
    inspect_ssi_minute_session_reference,
)
from swing_trading.ssi_source_qualification import ParityState

DAY=date(2026,11,10)
ASOF=datetime(2026,11,10,8,15,tzinfo=timezone.utc)


def fixture():
    return {"status":"ok","data":{"ticks":[
        {"symbol":"AAA","trading_date":"10/11/2026 14:45:00",
         "open":"10200","high":"10200","low":"10200","close":"10200",
         "volume":"150"},
        {"symbol":"AAA","trading_date":"10/11/2026 09:16:00",
         "open":"10300","high":"10500","low":"10200","close":"10200",
         "volume":"100"},
        {"symbol":"AAA","trading_date":"10/11/2026 09:15:00",
         "open":"10200","high":"10400","low":"10100","close":"10300",
         "volume":"50"},
    ]}}


def run(data=None, volume=300):
    return inspect_ssi_minute_session_reference(
        fixture() if data is None else data,
        symbol="AAA",trading_day=DAY,as_of_utc=ASOF,
        daily_matched_volume=volume,
    )


class SsiPrivateIntradayProbe209Tests(TestCase):
    def test_auction_and_three_typed_rows_numeric_equal_but_unverified(self):
        r=run()
        self.assertIs(r.state,MinuteProbeState.OBSERVED_UNVERIFIED)
        self.assertEqual(r.observed_rows,3)
        self.assertEqual(r.summed_minute_volume,300)
        self.assertIs(r.numeric_match_to_d1,True)
        self.assertTrue(r.auction_1445_present)
        self.assertEqual(r.latest_label,"10/11/2026 14:45:00")
        self.assertEqual(r.earliest_label,"10/11/2026 09:15:00")
        self.assertIs(r.volume_parity_state,ParityState.MISSING_UNKNOWN)
        for attr in ("source_clock_verified","official_calendar_verified",
                     "pagination_complete_verified","first_known_verified",
                     "m15_source_qualified","h1_source_qualified","action_eligible"):
            self.assertIs(getattr(r,attr),False)

    def test_observed_day_first_vs_documented_month_first_conflict(self):
        r=run()
        self.assertEqual(r.timestamp_policy_reason,"DATE_ORDER_CONFLICT_OR_UNKNOWN")
        self.assertFalse(r.source_clock_verified)

    def test_wrong_daily_volume_does_not_make_valid_m15_bars(self):
        r=run(volume=301)
        self.assertIs(r.numeric_match_to_d1,False)
        self.assertIs(r.volume_parity_state,ParityState.MISSING_UNKNOWN)
        self.assertFalse(r.m15_source_qualified)

    def test_d1_volume_absent_is_unknown_not_zero(self):
        r=run(volume=None)
        self.assertIsNone(r.numeric_match_to_d1)
        self.assertIs(r.volume_parity_state,ParityState.MISSING_UNKNOWN)

    def test_empty_list_is_blocked_not_verified_no_trade(self):
        bad=fixture()
        bad["data"]["ticks"]=[]
        r=run(bad)
        self.assertIs(r.state,MinuteProbeState.BLOCKED)
        self.assertEqual(r.observed_rows,0)
        self.assertIsNone(r.summed_minute_volume)
        self.assertFalse(r.auction_1445_present)

    def test_downstream_unavailable_distinct_from_missing(self):
        r=run({"status":"error","data":None,
               "error":{"code":"DOWNSTREAM_UNAVAILABLE"}})
        self.assertIs(r.state,MinuteProbeState.BLOCKED)
        self.assertEqual(r.timestamp_policy_reason,
                         "SSI_INTRADAY_DOWNSTREAM_UNAVAILABLE")

    def test_unclassified_source_error_refused(self):
        with self.assertRaises(MinuteProbeDenied):
            run({"status":"error","error":{"code":"SOME_OTHER_FAILURE"}})

    def test_duplicate_last_trade_label_refused(self):
        bad=fixture()
        bad["data"]["ticks"].append(dict(bad["data"]["ticks"][-1]))
        with self.assertRaisesRegex(MinuteProbeDenied,"DUPLICATE_OR_REORDERED"):
            run(bad)

    def test_ascending_timestamps_refused(self):
        bad=fixture()
        bad["data"]["ticks"].reverse()
        with self.assertRaisesRegex(MinuteProbeDenied,"DUPLICATE_OR_REORDERED"):
            run(bad)

    def test_documented_month_first_label_not_silently_accepted(self):
        bad=fixture()
        bad["data"]["ticks"][0]["trading_date"]="11/17/2026 14:45:00"
        with self.assertRaisesRegex(MinuteProbeDenied,"UNPARSEABLE_DAY_FIRST"):
            run(bad)

    def test_cross_day_clock_not_trusted_by_symbol(self):
        bad=fixture()
        bad["data"]["ticks"][0]["trading_date"]="09/11/2026 14:45:00"
        with self.assertRaisesRegex(MinuteProbeDenied,"SESSION_DATE_MISMATCH"):
            run(bad)

    def test_row_with_foreign_symbol_must_not_join(self):
        bad=fixture()
        bad["data"]["ticks"][0]["symbol"]="BBB"
        with self.assertRaisesRegex(MinuteProbeDenied,"SYMBOL_OR_SHAPE"):
            run(bad)

    def test_negative_unknown_and_oversized_volume_rejected(self):
        for volume in (-1,True,"bad",str(2**63)):
            bad=fixture()
            bad["data"]["ticks"][0]["volume"]=volume
            with self.subTest(volume=volume),self.assertRaises(MinuteProbeDenied):
                run(bad)

    def test_invalid_ohlc_and_nan_refused(self):
        for val in ("NaN","Infinity","9000"):
            bad=fixture()
            bad["data"]["ticks"][0]["close"]=val
            with self.subTest(val=val),self.assertRaises(MinuteProbeDenied):
                run(bad)

    def test_no_auction_cannot_be_implied_by_last_regular_bar(self):
        bad=fixture()
        bad["data"]["ticks"][0]["trading_date"]="10/11/2026 14:29:00"
        r=run(bad)
        self.assertIs(r.auction_1445_present,False)
        self.assertIs(r.numeric_match_to_d1,True)
        self.assertFalse(r.m15_source_qualified)

    def test_bad_metadata_types_and_too_many_rows_refused(self):
        for response in ({},{"status":"ok","data":{"ticks":None}}):
            with self.subTest(data=response),self.assertRaises(MinuteProbeDenied):
                run(response)
        huge=fixture()
        huge["data"]["ticks"]*=172
        with self.assertRaises(MinuteProbeDenied):
            run(huge)
        with self.assertRaises(ValueError):
            inspect_ssi_minute_session_reference(
                fixture(),symbol="AAA",trading_day=DAY,
                as_of_utc=ASOF.replace(tzinfo=None),daily_matched_volume=300,
            )

    def test_cannot_relabel_source_and_bar_finality_with_dataclass_replace(self):
        r=run()
        for attr in ("m15_source_qualified","h1_source_qualified",
                     "source_clock_verified","official_calendar_verified",
                     "pagination_complete_verified","first_known_verified",
                     "action_eligible"):
            with self.subTest(field=attr),self.assertRaises(MinuteProbeDenied):
                replace(r,**{attr:True})

    def test_missing_price_or_timestamp_cannot_emit_a_false_minute(self):
        for field in ("high","trading_date"):
            bad=deepcopy(fixture())
            bad["data"]["ticks"][1].pop(field)
            with self.subTest(field=field),self.assertRaises(MinuteProbeDenied):
                run(bad)
