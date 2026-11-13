"""SSI FastConnect V3 market-data-only Cloud adapter tests; HTTP is fabricated.

No real API key, source data or token is used in public GitHub CI.
"""
from __future__ import annotations

import json
import unittest
from scripts import mst_mfx_ssi_readonly as m


def settings(**overrides):
    env = {
        "MST_MFX_SOURCE_MODE":"ssi-d1-readonly",
        "MST_SSI_READONLY_OWNER_ACCEPTED":"true",
        "MST_SSI_SOURCE_RIGHTS_CONFIRMED":"true",
        "MST_SSI_API_KEY":"FAKE_MARKETDATA_SSI_KEY",
        "MST_SSI_API_SECRET":"FAKE_MARKETDATA_SSI_SECRET",
        "MST_SSI_SYMBOL":"FPT",
        "MST_SSI_FROM_DATE":"2026-11-01",
        "MST_SSI_TO_DATE":"2026-11-12",
    }
    env.update(overrides)
    return env


def row(date_, symbol="FPT", volume="190"):
    return {
        "symbol":symbol, "tradingDate":date_,
        "open":"100.2", "high":"101.0", "low":"99.8",
        "close":"100.5", "volume":volume, "value":"123456",
    }


class Response:
    def __init__(self, obj, status=200):
        self.status_code = status
        self._obj=obj
        self.content = json.dumps(obj).encode()
    def json(self):
        return self._obj


class FakeSsiApi:
    def __init__(self):
        self.auth_status=200
        self.auth={"tokenType":"Bearer","accessToken":"FAKE_JWT_MARKETDATA_ONLY_"+("x"*30)}
        self.pages={
            1: {"pageSize":100,"pageIndex":1,"pageCount":2,
                "data":[row("2026-11-12"), row("2026-11-11")]},
            2: {"pageSize":100,"pageIndex":2,"pageCount":2,
                "data":[row("2026-11-10")]},
        }
        self.calls=[]
    def post(self, url, *, json, headers, allow_redirects, timeout):
        self.calls.append(("POST",url,json,headers,allow_redirects,timeout))
        return Response(self.auth,self.auth_status)
    def get(self, url, *, params, headers, allow_redirects, timeout):
        self.calls.append(("GET",url,params,headers,allow_redirects,timeout))
        return Response(self.pages.get(params["pageIndex"],{
            "pageIndex":params["pageIndex"],"data":[],
        }))


class GateTests(unittest.TestCase):
    def test_valid_marketdata_only_scope(self):
        self.assertEqual(m.guard_ssi(settings())[0],"FPT")
    def test_source_rights_gate_before_any_api(self):
        api=FakeSsiApi()
        with self.assertRaises(m.SsiSourceDenied):
            m.read_ssi_d1_once(api,settings(MST_SSI_SOURCE_RIGHTS_CONFIRMED="false"))
        self.assertFalse(api.calls)
    def test_missing_api_credentials(self):
        with self.assertRaises(m.SsiSourceDenied):
            m.guard_ssi(settings(MST_SSI_API_SECRET=""))
    def test_other_mode_does_not_infer_rights(self):
        with self.assertRaises(m.SsiSourceDenied):
            m.guard_ssi(settings(MST_MFX_SOURCE_MODE="dnse-d1-readonly"))
    def test_invalid_date_window_bounded(self):
        for overrides in (
            {"MST_SSI_FROM_DATE":"2026-01-01"},
            {"MST_SSI_FROM_DATE":"2026-11-13"},
            {"MST_SSI_TO_DATE":"2026/11/12"},
            {"MST_SSI_TO_DATE":"2026-11-31"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(m.SsiSourceDenied):
                m.guard_ssi(settings(**overrides))


class NativeSourceTests(unittest.TestCase):
    def test_real_route_shapes_with_fake_http_and_complete_paging(self):
        api=FakeSsiApi()
        report=m.read_ssi_d1_once(api,settings())
        self.assertEqual(report["native_source_rows_observed"],3)
        self.assertEqual(report["source_pages_verified"],2)
        self.assertTrue(report["market_data_token_used_without_otp"])
        self.assertFalse(report["private_data_stored_to_drive"])
        self.assertFalse(report["signal_eligible"])
        self.assertEqual(report["trading_or_broker_calls"],0)
        self.assertEqual(len(api.calls),3)
        method,url,body,_,redirect,_=api.calls[0]
        self.assertEqual((method,url),("POST",m.AUTH_URL))
        self.assertEqual(set(body),{"apiKey","apiSecret"})
        self.assertFalse(redirect)
        for item in api.calls[1:]:
            self.assertEqual(item[0],"GET")
            self.assertEqual(item[1],m.OHLC_URL)
            self.assertEqual(item[2]["timeFrame"],"1d")
            self.assertTrue(item[3]["Authorization"].startswith("Bearer "))
            self.assertFalse(item[4])
        self.assertNotIn("FAKE_MARKETDATA_SSI_SECRET",str(report))
        self.assertNotIn("2026-11-12",str(report))

    def test_no_trading_or_otp_request(self):
        api=FakeSsiApi()
        m.read_ssi_d1_once(api,settings())
        self.assertFalse(any("/trading/" in x[1] or "otp" in str(x[2]).lower()
                             for x in api.calls))

    def test_auth_failure_is_fail_closed(self):
        api=FakeSsiApi()
        api.auth_status=403
        with self.assertRaisesRegex(m.SsiSourceDenied,"TOKEN_HTTP_NOT_200"):
            m.read_ssi_d1_once(api,settings())
        self.assertEqual(len(api.calls),1)

    def test_bearer_missing_is_fail_closed(self):
        api=FakeSsiApi()
        api.auth["accessToken"]=""
        with self.assertRaises(m.SsiSourceDenied):
            m.read_ssi_d1_once(api,settings())
        self.assertEqual(len(api.calls),1)

    def test_wrong_symbol_prevents_any_success_claim(self):
        api=FakeSsiApi()
        api.pages[1]["data"][0]["symbol"]="OTHER"
        with self.assertRaisesRegex(m.SsiSourceDenied,"SYMBOL_MISMATCH"):
            m.read_ssi_d1_once(api,settings())

    def test_invalid_native_ohlcv_denied(self):
        for field, value in (("high","99.0"),("low","102.0"),
                             ("close","NaN"),("volume","1.2"),("open",True)):
            api=FakeSsiApi()
            api.pages[1]["data"][0][field]=value
            with self.subTest(field=field),self.assertRaises(m.SsiSourceDenied):
                m.read_ssi_d1_once(api,settings())

    def test_duplicate_day_on_second_page_denied(self):
        api=FakeSsiApi()
        api.pages[2]["data"][0]["tradingDate"]="2026-11-11"
        with self.assertRaisesRegex(m.SsiSourceDenied,"DUPLICATE"):
            m.read_ssi_d1_once(api,settings())

    def test_metadata_pagecount_drift_denied(self):
        api=FakeSsiApi()
        api.pages[2]["pageCount"]=3
        with self.assertRaisesRegex(m.SsiSourceDenied,"PAGING_METADATA_MUTATED"):
            m.read_ssi_d1_once(api,settings())

    def test_missing_pagecount_can_terminate_on_short_last_page(self):
        api=FakeSsiApi()
        api.pages[1].pop("pageCount")
        api.pages[1]["data"]=api.pages[1]["data"][:1]
        report=m.read_ssi_d1_once(api,settings())
        self.assertEqual(report["source_pages_verified"],1)
        self.assertEqual(report["native_source_rows_observed"],1)

    def test_stale_or_wrong_day_label_denied(self):
        api=FakeSsiApi()
        api.pages[1]["data"][0]["tradingDate"]="2026-10-30"
        with self.assertRaisesRegex(m.SsiSourceDenied,"OUTSIDE_REQUESTED_WINDOW"):
            m.read_ssi_d1_once(api,settings())



class SsiNativeTimeframeTests(unittest.TestCase):
    def test_five_tf_contract_and_h4_no_native(self):
        from scripts.mst_mfx_native_timeframes import provider_resolution, NativeTfDenied
        expected={"M5":"5m","M15":"15m","M30":"30m","H1":"1h","D1":"1d"}
        for tf,resolution in expected.items():
            self.assertEqual(provider_resolution("SSI",tf),resolution)
        with self.assertRaisesRegex(NativeTfDenied, "NATIVE_H4"):
            provider_resolution("SSI","H4")

    def test_intraday_m5_multiple_distinct_bars_same_day(self):
        api=FakeSsiApi()
        api.pages[1]["data"]=[
            row("2026-11-12 09:00:00"),
            row("2026-11-12 09:05:00"),
        ]
        api.pages[2]["data"]=[row("2026-11-11 14:45:00")]
        env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="M5",
                     MST_SSI_FROM_DATE="2026-11-10",MST_SSI_TO_DATE="2026-11-12")
        report=m.read_ssi_native_once(api,env)
        self.assertEqual(report["native_source_rows_observed"],3)
        self.assertEqual(report["provider_resolution"],"5m")
        self.assertEqual(report["source_native_tf"],"M5")
        self.assertFalse(report["source_closed_bar_attestation_proven"])
        self.assertFalse(report["trade_signal_eligible"])
        self.assertTrue(all(x[2]["timeFrame"]=="5m" for x in api.calls[1:]))

    def test_intraday_date_only_rejected_not_fake_d1(self):
        api=FakeSsiApi()
        env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="M5",
                     MST_SSI_FROM_DATE="2026-11-10",MST_SSI_TO_DATE="2026-11-12")
        with self.assertRaisesRegex(m.SsiSourceDenied,"NATIVE_TF_TRADING_TIMESTAMP_INVALID"):
            m.read_ssi_native_once(api,env)

    def test_daily_mode_does_not_coerce_m5_and_h4_stays_no_go(self):
        for env in (
            settings(MST_SOURCE_TF="M5"),
            settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="H4"),
        ):
            with self.assertRaises(m.SsiSourceDenied):
                m.guard_ssi(env)

    def test_two_intraday_rows_same_timestamp_rejected(self):
        api=FakeSsiApi()
        api.pages[1]["data"]=[row("2026-11-12 09:00:00"),row("2026-11-12 09:00:00")]
        api.pages[2]["data"]=[row("2026-11-11 14:45:00")]
        env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="M5",
                     MST_SSI_FROM_DATE="2026-11-10",MST_SSI_TO_DATE="2026-11-12")
        with self.assertRaisesRegex(m.SsiSourceDenied,"DUPLICATE"):
            m.read_ssi_native_once(api,env)



class SsiRealApiWireContractTests(unittest.TestCase):
    def test_intraday_query_has_ssi_required_calendar_and_clock(self):
        api=FakeSsiApi()
        api.pages[1]["data"]=[
            row("2026-11-12 09:00:00"),row("2026-11-12 09:05:00"),
        ]
        api.pages[2]["data"]=[row("2026-11-11 14:45:00")]
        env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="M5",
                     MST_SSI_FROM_DATE="2026-11-10",MST_SSI_TO_DATE="2026-11-12")
        m.read_ssi_native_once(api,env)
        for request in api.calls[1:]:
            params=request[2]
            self.assertEqual(params["from"],"2026/11/10 00:00:00")
            self.assertEqual(params["to"],"2026/11/12 23:59:59")
            self.assertEqual(params["timeFrame"],"5m")

    def test_d1_wire_query_still_requires_date_without_clock(self):
        api=FakeSsiApi()
        m.read_ssi_d1_once(api,settings())
        for request in api.calls[1:]:
            self.assertEqual(request[2]["from"],"2026/11/01")
            self.assertEqual(request[2]["to"],"2026/11/12")
            self.assertEqual(request[2]["timeFrame"],"1d")

    def test_two_different_native_delimiter_strings_are_same_candle(self):
        api=FakeSsiApi()
        api.pages[1]["data"]=[
            row("2026-11-12 09:00:00"),row("2026/11/12 09:00:00"),
        ]
        api.pages[2]["data"]=[row("2026-11-11 14:45:00")]
        env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF="M5",
                     MST_SSI_FROM_DATE="2026-11-10",MST_SSI_TO_DATE="2026-11-12")
        with self.assertRaisesRegex(m.SsiSourceDenied,"DUPLICATE_SOURCE_BAR_TIMESTAMP"):
            m.read_ssi_native_once(api,env)

    def test_intraday_probes_must_stay_bounded(self):
        for tf, limit in m.MAX_CALENDAR_SPAN_BY_TF.items():
            env=settings(MST_MFX_SOURCE_MODE="ssi-native-readonly",MST_SOURCE_TF=tf,
                         MST_SSI_FROM_DATE="2026-01-01",MST_SSI_TO_DATE="2026-11-12")
            with self.subTest(tf=tf), self.assertRaisesRegex(
                    m.SsiSourceDenied,"TF_BOUNDED_WINDOW_REQUIRED"):
                m.guard_ssi(env)
        self.assertEqual(m.MAX_CALENDAR_SPAN_BY_TF["D1"],95)



class SsiOfficialPaginationCompletenessTests(unittest.TestCase):
    def test_items_count_exact_multi_page_match_verified(self):
        api=FakeSsiApi()
        for page in api.pages.values():
            page["itemsCount"]=3
        report=m.read_ssi_d1_once(api,settings())
        self.assertTrue(report["source_items_count_verified"])
        self.assertEqual(report["native_source_rows_observed"],3)
        self.assertFalse(report["complete_historical_source_coverage_proven"])

    def test_items_count_short_final_page_is_not_silently_complete(self):
        api=FakeSsiApi()
        for page in api.pages.values():
            page["itemsCount"]=4
        with self.assertRaisesRegex(m.SsiSourceDenied,"ITEMS_COUNT_MISMATCH"):
            m.read_ssi_d1_once(api,settings())

    def test_items_count_mutation_between_pages_is_quarantined(self):
        api=FakeSsiApi()
        api.pages[1]["itemsCount"]=3
        api.pages[2]["itemsCount"]=4
        with self.assertRaisesRegex(m.SsiSourceDenied,"ITEMS_COUNT_MUTATED"):
            m.read_ssi_d1_once(api,settings())

    def test_page_size_ignored_by_server_is_quarantined(self):
        api=FakeSsiApi()
        api.pages[1]["pageSize"]=2
        with self.assertRaisesRegex(m.SsiSourceDenied,"PAGE_SIZE_DRIFT"):
            m.read_ssi_d1_once(api,settings())

    def test_page_index_and_page_number_both_must_agree(self):
        api=FakeSsiApi()
        api.pages[1]["pageNumber"]=2
        with self.assertRaisesRegex(m.SsiSourceDenied,"PAGE_NUMBER_DRIFT"):
            m.read_ssi_d1_once(api,settings())

    def test_declared_items_prevent_short_page_false_completion(self):
        api=FakeSsiApi()
        for page in api.pages.values():
            page.pop("pageCount")
            page["itemsCount"]=3
        report=m.read_ssi_d1_once(api,settings())
        self.assertEqual(report["source_pages_verified"],2)
        self.assertEqual(report["native_source_rows_observed"],3)
        self.assertTrue(report["source_items_count_verified"])

    def test_declared_items_not_satisfied_by_empty_page(self):
        api=FakeSsiApi()
        for page in api.pages.values():
            page.pop("pageCount")
            page["itemsCount"]=4
        with self.assertRaisesRegex(m.SsiSourceDenied,"ITEMS_COUNT_MISMATCH"):
            m.read_ssi_d1_once(api,settings())

    def test_declared_items_beyond_bounded_probe_is_rejected(self):
        api=FakeSsiApi()
        api.pages[1]["itemsCount"]=501
        with self.assertRaisesRegex(m.SsiSourceDenied,"ITEMS_COUNT_UNBOUNDED"):
            m.read_ssi_d1_once(api,settings())

    def test_legacy_no_item_count_is_observation_not_certified_total(self):
        api=FakeSsiApi()
        report=m.read_ssi_d1_once(api,settings())
        self.assertFalse(report["source_items_count_verified"])
        self.assertFalse(report["complete_historical_source_coverage_proven"])



if __name__=="__main__":
    unittest.main()
