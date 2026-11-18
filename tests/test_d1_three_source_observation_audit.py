"""§209 FICTIONAL shape tests: SSI vs DNSE vs VCBS source-limited D1.

No live OHLC, ticker, provider credentials or response recorded in GitHub.
The tested numeric equality is NEVER source authority or a tradable signal.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import unittest

from swing_trading.d1_three_source_observation_audit import (
    D1ObservationState, D1ParityState, D1ProbeDenied, D1ProbeSource,
    inspect_d1_live_response, reconcile_d1_three_source_observations,
)
from swing_trading.market_data import PriceBasis

DAY=date(2026,11,10)
TIME=datetime(2026,11,10,8,15,tzinfo=timezone.utc)
AT9=int(datetime(2026,11,10,2,0,tzinfo=timezone.utc).timestamp())
SOURCE="AAA"
OHLCV=(D("10200"),D("10500"),D("10100"),D("10300"),123456)


def ssi_compact():
    return {"status":"ok","data":{"stocks":[{
        "symbol":SOURCE,"trading_date":"10/11/2026",
        "open":"10200","high":"10500","low":"10100",
        "close":"10300","volume":"123456",
    }]}}


def ssi_detail():
    return {"status":"ok","data":{"stocks":[{
        "symbol":SOURCE,"trading_date":"10/11/2026",
        "open":"99999","high":"99999","low":"99999",
        "close":"99999","volume":"123456",
        "open_raw":"10200","high_raw":"10500",
        "low_raw":"10100","close_raw":"10300",
    }]}}


def dnse():
    return {"data":{
        "t":[AT9],"o":[10.2],"h":[10.5],
        "l":[10.1],"c":[10.3],"v":[123456],"nextTime":0,
    }}


def vcbs():
    return {
        "row_basis":{"price_unit":"VND","volume_scope":"matched_only",
                     "field_basis":{"price":"raw"}},
        "data":[{
            "tradingDate":"2026-11-10",
            "openPrice":10200,"highPrice":10500,
            "lowPrice":10100,"closePrice":10300,
            "adjClosePrice":9999,"price":10300,
            "volume":123456,"source":"board_supplement",
            "tradingValue":None,"ptValue":None,
        }],
    }


def inspect(src, payload=None, **opts):
    default={
        D1ProbeSource.SSI_COMPACT:ssi_compact,
        D1ProbeSource.SSI_DETAIL:ssi_detail,
        D1ProbeSource.DNSE_DAY:dnse,
        D1ProbeSource.VCBS_RAW:vcbs,
    }
    return inspect_d1_live_response(
        default[src]() if payload is None else payload,source=src,
        symbol=opts.get("symbol",SOURCE),
        trading_day=opts.get("trading_day",DAY),
        retrieved_at_utc=opts.get("retrieved_at_utc",TIME),
    )


def all_four():
    return tuple(inspect(s) for s in D1ProbeSource)


class RealShapeD1Readiness209Tests(unittest.TestCase):
    def test_all_endpoint_specific_shapes_normalize_unit_correctly(self):
        results=all_four()
        self.assertEqual(len(results),4)
        for x in results:
            with self.subTest(endpoint=x.source):
                self.assertEqual(x.ohlcv_vnd_shares,OHLCV)
                self.assertIs(x.state,D1ObservationState.ROW_OBSERVED)
                self.assertIs(x.action_eligible,False)
                self.assertIs(x.source_independently_attested,False)
                self.assertIs(x.vendor_first_known_verified,False)
                self.assertIs(x.venue_close_verified,False)
                self.assertIs(x.retention_rights_verified,False)
        self.assertEqual(results[0].basis,PriceBasis.ADJUSTED)
        self.assertEqual(results[1].basis,PriceBasis.RAW)
        self.assertEqual(results[2].basis,PriceBasis.UNKNOWN)
        self.assertEqual(results[3].basis,PriceBasis.RAW)

    def test_numeric_three_source_equality_cannot_be_attestation(self):
        obs=all_four()
        r=reconcile_d1_three_source_observations(
            obs,symbol=SOURCE,trading_day=DAY,
        )
        self.assertIs(r.state,D1ParityState.VALUES_EQUAL_BASIS_UNVERIFIED)
        self.assertIs(r.numeric_ohlcv_equal,True)
        self.assertEqual(len(r.present_sources),4)
        self.assertFalse(r.provider_first_known_verified)
        self.assertFalse(r.venue_close_verified)
        self.assertFalse(r.retention_rights_verified)
        self.assertFalse(r.signal_eligible)
        self.assertFalse(r.action_eligible)

    def test_detailed_ssi_missing_does_not_erase_three_other_rows(self):
        no_today=ssi_detail()
        no_today["data"]["stocks"][0]["trading_date"]="09/11/2026"
        missing=inspect(D1ProbeSource.SSI_DETAIL,no_today)
        self.assertIs(missing.state,D1ObservationState.TARGET_ABSENT)
        self.assertIsNone(missing.ohlcv_vnd_shares)
        obs=(inspect(D1ProbeSource.SSI_COMPACT),missing,
             inspect(D1ProbeSource.DNSE_DAY),
             inspect(D1ProbeSource.VCBS_RAW))
        audit=reconcile_d1_three_source_observations(
            obs,symbol=SOURCE,trading_day=DAY,
        )
        self.assertIs(audit.state,D1ParityState.VALUES_EQUAL_BASIS_UNVERIFIED)
        self.assertEqual(audit.absent_sources,(D1ProbeSource.SSI_DETAIL,))
        self.assertIn("SSI_TARGET_NOT_RETURNED_NOT_ZERO_VOLUME",audit.reasons)

    def test_ssi_downstream_unavailable_distinct_from_empty_or_zero(self):
        payload={"status":"error","data":None,
                 "error":{"code":"DOWNSTREAM_UNAVAILABLE"}}
        x=inspect(D1ProbeSource.SSI_DETAIL,payload)
        self.assertIs(x.state,D1ObservationState.DOWNSTREAM_UNAVAILABLE)
        self.assertIsNone(x.ohlcv_vnd_shares)
        self.assertNotEqual(x.source_semantics,"SSI_TARGET_NOT_RETURNED_NOT_ZERO_VOLUME")

    def test_ssi_compact_d1_date_string_is_day_first(self):
        fake=ssi_compact()
        fake["data"]["stocks"][0]["trading_date"]="11/10/2026"
        r=inspect(D1ProbeSource.SSI_COMPACT,fake)
        self.assertIs(r.state,D1ObservationState.TARGET_ABSENT)
        self.assertIsNone(r.ohlcv_vnd_shares)

    def test_ssi_detail_raw_fields_not_ambiguous_general_ohlc(self):
        base=ssi_detail()
        x=inspect(D1ProbeSource.SSI_DETAIL,base)
        self.assertEqual(x.ohlcv_vnd_shares,OHLCV)
        self.assertNotEqual(x.ohlcv_vnd_shares[0],D(base["data"]["stocks"][0]["open"]))
        self.assertEqual(x.basis,PriceBasis.RAW)

    def test_ssi_unknown_error_is_not_accepted_as_missing(self):
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.SSI_COMPACT,{
                "status":"error","error":{"code":"SOME_UNCLASSIFIED_FAILURE"}
            })

    def test_ssi_duplicate_rows_same_date_are_not_a_valid_history(self):
        bad=ssi_compact()
        bad["data"]["stocks"].append(dict(bad["data"]["stocks"][0]))
        with self.assertRaisesRegex(D1ProbeDenied,"DUPLICATE"):
            inspect(D1ProbeSource.SSI_COMPACT,bad)

    def test_dnse_0900_local_label_not_bar_finality(self):
        x=inspect(D1ProbeSource.DNSE_DAY)
        self.assertIn("NOT_CLOSE",x.source_semantics)
        self.assertIs(x.basis,PriceBasis.UNKNOWN)
        self.assertFalse(x.venue_close_verified)

    def test_dnse_wrong_intraday_clock_is_not_a_daily_session_label(self):
        bad=dnse()
        bad["data"]["t"][0]+=900
        with self.assertRaisesRegex(D1ProbeDenied,"NOT_SESSION_09"):
            inspect(D1ProbeSource.DNSE_DAY,bad)

    def test_dnse_array_lengths_need_same_verified_index(self):
        bad=dnse()
        bad["data"]["v"]=[]
        with self.assertRaisesRegex(D1ProbeDenied,"ARRAY_LENGTH"):
            inspect(D1ProbeSource.DNSE_DAY,bad)

    def test_dnse_nonmonotone_duplicate_epochs_are_refused(self):
        bad=dnse()
        for key in ("t","o","h","l","c","v"):
            bad["data"][key]=bad["data"][key]*2
        with self.assertRaisesRegex(D1ProbeDenied,"NONMONOTONE"):
            inspect(D1ProbeSource.DNSE_DAY,bad)

    def test_dnse_basis_cannot_be_forged_even_if_prices_match(self):
        row=inspect(D1ProbeSource.DNSE_DAY)
        for bad_basis in (PriceBasis.RAW,PriceBasis.ADJUSTED):
            with self.subTest(basis=bad_basis),self.assertRaises(D1ProbeDenied):
                replace(row,basis=bad_basis)

    def test_vcbs_board_supplement_and_missing_trading_value_remain_unverified(self):
        row=inspect(D1ProbeSource.VCBS_RAW)
        self.assertIn("BOARD_SUPPLEMENT",row.source_semantics)
        self.assertIs(row.basis,PriceBasis.RAW)
        self.assertFalse(row.venue_close_verified)

    def test_vcbs_price_field_adjusted_does_not_override_raw_ohlc(self):
        bad=vcbs()
        bad["data"][0]["price"]=9999
        x=inspect(D1ProbeSource.VCBS_RAW,bad)
        self.assertEqual(x.ohlcv_vnd_shares,OHLCV)
        self.assertEqual(x.basis,PriceBasis.RAW)

    def test_vcbs_wrong_unit_price_or_volume_scope_denied(self):
        for field,bad_value in (
            ("price_unit","THOUSAND_VND"),
            ("volume_scope","unknown"),
        ):
            case=vcbs()
            case["row_basis"][field]=bad_value
            with self.subTest(field=field),self.assertRaises(D1ProbeDenied):
                inspect(D1ProbeSource.VCBS_RAW,case)

    def test_vcbs_daily_absence_not_a_zero_volume_day(self):
        empty=vcbs()
        empty["data"]=[]
        x=inspect(D1ProbeSource.VCBS_RAW,empty)
        self.assertIs(x.state,D1ObservationState.TARGET_ABSENT)
        self.assertIsNone(x.ohlcv_vnd_shares)

    def test_missing_a_required_core_endpoint_is_not_three_way_parity(self):
        obs=tuple(x for x in all_four()
                  if x.source is not D1ProbeSource.DNSE_DAY)
        audit=reconcile_d1_three_source_observations(
            obs,symbol=SOURCE,trading_day=DAY,
        )
        self.assertIs(audit.state,D1ParityState.INSUFFICIENT_SOURCES_UNVERIFIED)
        self.assertIsNone(audit.numeric_ohlcv_equal)
        self.assertFalse(audit.signal_eligible)

    def test_three_way_price_and_volume_conflict_are_blocked(self):
        original=all_four()
        case=ssi_compact()
        case["data"]["stocks"][0]["close"]="10400"
        changed=inspect(D1ProbeSource.SSI_COMPACT,case)
        conflict=(changed,)+original[1:]
        r=reconcile_d1_three_source_observations(
            conflict,symbol=SOURCE,trading_day=DAY,
        )
        self.assertIs(r.state,D1ParityState.SOURCE_VALUES_CONFLICT)
        self.assertIs(r.numeric_ohlcv_equal,False)
        bad=dnse()
        bad["data"]["v"][0]=999
        changed=inspect(D1ProbeSource.DNSE_DAY,bad)
        r=reconcile_d1_three_source_observations(
            (original[0],original[1],changed,original[3]),
            symbol=SOURCE,trading_day=DAY,
        )
        self.assertIs(r.state,D1ParityState.SOURCE_VALUES_CONFLICT)

    def test_source_symbol_date_or_duplicate_endpoint_mismatch(self):
        x=inspect(D1ProbeSource.SSI_COMPACT)
        for payload in (
            (x,x),
            (replace(x,symbol="BBB"),),
            (replace(x,trading_day=DAY+timedelta(days=1)),),
        ):
            with self.subTest(payload=payload),self.assertRaises(D1ProbeDenied):
                reconcile_d1_three_source_observations(
                    payload,symbol=SOURCE,trading_day=DAY,
                )

    def test_no_approval_allowed_from_rehashed_or_crafted_dataclass(self):
        src=inspect(D1ProbeSource.SSI_COMPACT)
        for field in (
            "action_eligible","source_independently_attested",
            "vendor_first_known_verified","venue_close_verified",
            "retention_rights_verified",
        ):
            with self.subTest(field=field),self.assertRaises(D1ProbeDenied):
                replace(src,**{field:True})
        audit=reconcile_d1_three_source_observations(
            all_four(),symbol=SOURCE,trading_day=DAY,
        )
        for field in (
            "action_eligible","signal_eligible","venue_close_verified",
            "retention_rights_verified","provider_first_known_verified",
        ):
            with self.subTest(field=field),self.assertRaises(D1ProbeDenied):
                replace(audit,**{field:True})

    def test_nan_inf_bool_overflow_and_impossible_ohlc_denied(self):
        for close in ("NaN","Infinity",True,"99999999999999999999999","9000"):
            row=ssi_compact()
            row["data"]["stocks"][0]["close"]=close
            with self.subTest(close=close),self.assertRaises(D1ProbeDenied):
                inspect(D1ProbeSource.SSI_COMPACT,row)
        for vol in (-1,True,"invalid",str(2**63)):
            row=ssi_compact()
            row["data"]["stocks"][0]["volume"]=vol
            with self.subTest(vol=vol),self.assertRaises(D1ProbeDenied):
                inspect(D1ProbeSource.SSI_COMPACT,row)

    def test_oversized_or_malformed_endpoint_payload_denied(self):
        rows=ssi_compact()
        rows["data"]["stocks"]=rows["data"]["stocks"]*513
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.SSI_COMPACT,rows)
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.VCBS_RAW,{"data":None})
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.DNSE_DAY,{"data":{"t":[0]}})

    def test_datetime_requires_utc_and_session_date_cannot_be_datetime(self):
        with self.assertRaises(ValueError):
            inspect(D1ProbeSource.VCBS_RAW,retrieved_at_utc=TIME.replace(tzinfo=None))
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.VCBS_RAW,trading_day=TIME)
        with self.assertRaises(D1ProbeDenied):
            inspect(D1ProbeSource.VCBS_RAW,symbol="AAA/PRIVATE")


if __name__=="__main__":
    unittest.main()
