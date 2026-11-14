"""Synthetic three-provider envelopes, identical in shape only to private MCP captures.

Do NOT paste real private source documents or prices into public GitHub tests.
The underlying original engine still has zero verified B1..S8 rules.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

from swing_trading.private_cache_source_bridge import (
    PrivateSourceDenied, inspect_private_d1_snapshot,
    diagnose_private_d1_without_signals,
)
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import PriceBasis

NOW = datetime(2026,11,14,6,0,tzinfo=timezone.utc)


def source(provider="SSI"):
    data={
        "schema":"mst.private_connector_d1_cache_capture.v1",
        "project":"MST","provider":provider,"symbol":"FPT",
        "timeframe":"D1","snapshot_day":"2026-11-13",
        "source_origin":"ChatGPT_MCP_CONNECTOR_PRIVATE_DRIVE",
        "not_appowned_github_cache_publisher":True,
        "issuer_closed_bar_attested":False,
        "signal_eligible":False,
        "trade_orders":0,"source_rows_observed":2,
    }
    if provider=="SSI":
        data["native_source_data"]=[
            {"symbol":"FPT","trading_date":"13/11/2026","open":"51000",
             "high":"52000","low":"50000","close":"50500","volume":"800"},
            {"symbol":"FPT","trading_date":"12/11/2026","open":"50000",
             "high":"51000","low":"49000","close":"50750","volume":"700"},
        ]
    elif provider=="DNSE":
        first=int(datetime(2026,11,12,2,tzinfo=timezone.utc).timestamp())
        second=int(datetime(2026,11,13,2,tzinfo=timezone.utc).timestamp())
        data["native_source_data"]={
            "t":[first,second],
            "o":[50.0,51.0],"h":[51.0,52.0],
            "l":[49.0,50.0],"c":[50.75,50.5],
            "v":[700,800],"nextTime":0,
        }
    elif provider=="VCBS":
        data["native_source_data"]={
            "symbol":"FPT","row_basis":{
                "price_unit":"VND","volume_scope":"matched_only",
                "field_basis":{"price":"raw","changePct":"previous_close"}},
            "data":[
                {"tradingDate":"2026-11-13","openPrice":51000,
                 "highPrice":52000,"lowPrice":50000,"closePrice":50500,
                 "adjClosePrice":50000,"volume":800,
                 "source":"board_supplement","tradingValue":None},
                {"tradingDate":"2026-11-12","openPrice":50000,
                 "highPrice":51000,"lowPrice":49000,"closePrice":50750,
                 "adjClosePrice":50000,"volume":700},
            ],
        }
    else:
        raise AssertionError("fixture only")
    return data


class RealShapeButSyntheticPrivateD1Bridge(unittest.TestCase):
    def test_three_sources_are_separate_and_do_not_emit_signals(self):
        for provider in ("SSI","DNSE","VCBS"):
            for strategy in (Strategy.SHORT,Strategy.SWING):
                with self.subTest(provider=provider,strategy=strategy):
                    p=diagnose_private_d1_without_signals(
                        source(provider),strategy=strategy,as_of_utc=NOW)
                    self.assertEqual(p.source.provider,provider)
                    self.assertEqual(p.source.symbol,"FPT")
                    self.assertEqual(p.source.source_rows_observed,2)
                    self.assertEqual(len(p.source.raw_source_sha256),64)
                    self.assertEqual(len(p.decisions),16)
                    self.assertTrue(all(
                        x.status is DecisionStatus.UNVERIFIED for x in p.decisions
                    ))
                    self.assertTrue(all(x.strategy is strategy for x in p.decisions))
                    self.assertFalse(p.eligible_for_signals)
                    self.assertFalse(p.source.eligible_for_signals)
                    self.assertFalse(p.source.eligible_for_backtest)
                    self.assertFalse(p.source.source_is_appowned_publisher)
                    self.assertFalse(p.source.issuer_first_known_attested)
                    self.assertFalse(p.source.venue_close_attested)
                    self.assertEqual(p.trading_or_broker_calls,0)
                    self.assertTrue(all(not bar.eligible_for_signals
                                        for bar in p.source.bars))

    def test_vendor_scale_price_and_basis_are_not_conflated(self):
        s=inspect_private_d1_snapshot(source("SSI"),as_of_utc=NOW)
        d=inspect_private_d1_snapshot(source("DNSE"),as_of_utc=NOW)
        v=inspect_private_d1_snapshot(source("VCBS"),as_of_utc=NOW)
        for x in (s,d,v):
            self.assertEqual(x.bars[-1].close_vnd,Decimal("50500"))
            self.assertEqual(x.bars[-1].volume_shares,800)
        self.assertEqual(s.bars[-1].reported_price_basis,PriceBasis.UNKNOWN)
        self.assertEqual(d.bars[-1].reported_price_basis,PriceBasis.UNKNOWN)
        self.assertEqual(v.bars[-1].reported_price_basis,PriceBasis.RAW)
        self.assertTrue(v.has_provisional_source)
        self.assertFalse(d.has_provisional_source)
        self.assertFalse(s.has_provisional_source)
        self.assertEqual(
            tuple(x.trading_date for x in d.bars),
            (date(2026,11,12),date(2026,11,13))
        )

    def test_stable_digest_and_correction_changes_digest_without_promoting(self):
        src=source("VCBS")
        a=inspect_private_d1_snapshot(src,as_of_utc=NOW)
        b=inspect_private_d1_snapshot(deepcopy(src),as_of_utc=NOW)
        self.assertEqual(a.raw_source_sha256,b.raw_source_sha256)
        correction=deepcopy(src)
        correction["native_source_data"]["data"][0]["tradingValue"]=10000
        revised=inspect_private_d1_snapshot(correction,as_of_utc=NOW)
        self.assertNotEqual(a.raw_source_sha256,revised.raw_source_sha256)
        self.assertFalse(revised.eligible_for_signals)

    def test_private_snapshot_cannot_be_used_before_capture_day(self):
        for provider in ("SSI","DNSE","VCBS"):
            p=source(provider)
            with self.subTest(provider=provider),self.assertRaisesRegex(
                PrivateSourceDenied,"RETROSPECTIVE_LOOKAHEAD"
            ):
                diagnose_private_d1_without_signals(
                    p,strategy=Strategy.SWING,
                    as_of_utc=datetime(2026,11,12,12,tzinfo=timezone.utc)
                )
        with self.assertRaises(ValueError):
            inspect_private_d1_snapshot(source("SSI"),
                as_of_utc=datetime(2026,11,14,12))

    def test_private_records_cannot_be_relabelled_as_prod_authority(self):
        for name,value in (
            ("schema","mst.cloud.verified_source"),
            ("project","MFX"),("timeframe","H4"),
            ("source_origin","GITHUB_APP_OWNED_VERIFIED"),
            ("not_appowned_github_cache_publisher",False),
            ("issuer_closed_bar_attested",True),
            ("signal_eligible",True),("trade_orders",1),
            ("trade_orders",False),
        ):
            p=source()
            p[name]=value
            with self.subTest(name=name,value=value),self.assertRaises(
                PrivateSourceDenied
            ):
                inspect_private_d1_snapshot(p,as_of_utc=NOW)

    def test_unknown_provider_or_corrupt_count_never_silently_passes(self):
        for p in (
            dict(source(),provider="FAKE"),
            dict(source(),symbol="FPT-EQUITY"),
            dict(source(),source_rows_observed=1),
            dict(source(),source_rows_observed=True),
            dict(source(),snapshot_day="13/11/2026"),
            dict(source(),snapshot_day="2026-11-12"),
        ):
            with self.subTest(p=p.get("provider")),self.assertRaises(
                PrivateSourceDenied
            ):
                inspect_private_d1_snapshot(p,as_of_utc=NOW)

    def test_ssi_unreliable_or_duplicate_rows_fail_closed(self):
        for kind in ("wrong_symbol","duplicate","nan","bad_high",
                     "negative_vol","boolean_vol","bad_date","future_date"):
            p=source("SSI")
            rows=p["native_source_data"]
            if kind=="wrong_symbol":rows[0]["symbol"]="HPG"
            elif kind=="duplicate":rows[0]["trading_date"]=rows[1]["trading_date"]
            elif kind=="nan":rows[0]["close"]="NaN"
            elif kind=="bad_high":rows[0]["high"]="45000"
            elif kind=="negative_vol":rows[0]["volume"]="-1"
            elif kind=="boolean_vol":rows[0]["volume"]=True
            elif kind=="bad_date":rows[0]["trading_date"]="31/02/2026"
            elif kind=="future_date":rows[0]["trading_date"]="15/11/2026"
            with self.subTest(kind=kind),self.assertRaises(
                PrivateSourceDenied
            ):
                inspect_private_d1_snapshot(p,as_of_utc=NOW)

    def test_dnse_incomplete_ms_duplicate_or_wrong_venue_clock_fail_closed(self):
        for kind in ("unfinished","milliseconds","duplicate","not_0200",
                     "arrays","bad_price","future","bool_stamp"):
            p=source("DNSE")
            data=p["native_source_data"]
            if kind=="unfinished":data["nextTime"]=12345
            if kind=="milliseconds":data["t"][0]*=1000
            if kind=="duplicate":data["t"][1]=data["t"][0]
            if kind=="not_0200":data["t"][0]+=60
            if kind=="arrays":data["v"]=data["v"][:1]
            if kind=="bad_price":data["h"][0]=45.0
            if kind=="future":
                data["t"][1]=int(datetime(2026,11,15,2,tzinfo=timezone.utc).timestamp())
            if kind=="bool_stamp":data["t"][0]=True
            with self.subTest(kind=kind),self.assertRaises(
                PrivateSourceDenied
            ):
                inspect_private_d1_snapshot(p,as_of_utc=NOW)

    def test_vcbs_reported_raw_basis_not_fabricated_from_adjusted_or_board(self):
        for kind in ("price_unit","basis","mixed_volume","supplement",
                     "duplicate","bad_OHLC","symbol","adjusted_only"):
            p=source("VCBS")
            data=p["native_source_data"]
            if kind=="price_unit":data["row_basis"]["price_unit"]="THOUSAND_VND"
            if kind=="basis":data["row_basis"]["field_basis"]["price"]="adjusted"
            if kind=="mixed_volume":data["row_basis"]["volume_scope"]="mixed"
            if kind=="supplement":data["data"][0]["source"]="unverified_venue"
            if kind=="duplicate":data["data"][0]["tradingDate"]="2026-11-12"
            if kind=="bad_OHLC":data["data"][0]["lowPrice"]=53000
            if kind=="symbol":data["symbol"]="DCM"
            if kind=="adjusted_only":del data["data"][0]["closePrice"]
            with self.subTest(kind=kind),self.assertRaises(
                PrivateSourceDenied
            ):
                inspect_private_d1_snapshot(p,as_of_utc=NOW)

    def test_observation_order_canonical_no_provider_merges(self):
        p=source("SSI")
        first=inspect_private_d1_snapshot(p,as_of_utc=NOW)
        p["native_source_data"].reverse()
        second=inspect_private_d1_snapshot(p,as_of_utc=NOW)
        self.assertEqual(
            tuple(b.trading_date for b in first.bars),
            tuple(b.trading_date for b in second.bars)
        )
        # Raw-source digest still tracks the exact observed source ordering.
        self.assertNotEqual(first.raw_source_sha256,second.raw_source_sha256)
        self.assertEqual({b.provider for b in first.bars},{"SSI"})


if __name__=="__main__":
    unittest.main()
