"""Fixture-only regression tests for multi-provider D1 incremental cache."""
import copy
import unittest

from scripts.mst_d1_incremental_cache_delta import DeltaDenied, plan_d1_delta


def ssi(day="12/11/2026", volume="100", symbol="FPT"):
    return {"symbol": symbol, "trading_date": day,
            "open": "50", "high": "52", "low": "49",
            "close": "51", "volume": volume}


def vcbs(day="2026-11-12", volume=100, display=51):
    return {"tradingDate": day, "openPrice": 50, "highPrice": 52,
            "lowPrice": 49, "closePrice": 51, "volume": volume,
            "adjClosePrice": 48, "price": display}


def dnse(t=1794441600, volume=100):
    return {"source_unix_seconds": t, "date_utc": "2026-11-12",
            "open": 50, "high": 52, "low": 49, "close": 51, "volume": volume}


def previous(provider, rows):
    return {"schema": "mst.mcp.d1.private_drive_snapshot.v0.2",
            "provider": provider, "symbol": "FPT", "timeframe": "D1",
            "retained_row_count": len(rows), "rows": rows}


def current(provider, rows):
    if provider == "DNSE":
        data = {"t": [r["source_unix_seconds"] for r in rows],
                "o": [r["open"] for r in rows], "h": [r["high"] for r in rows],
                "l": [r["low"] for r in rows], "c": [r["close"] for r in rows],
                "v": [r["volume"] for r in rows], "nextTime": 0}
    elif provider == "VCBS":
        data = {"data": rows}
    else:
        data = rows
    return {"schema": "mst.private_connector_d1_cache_capture.v1",
            "provider": provider, "symbol": "FPT", "timeframe": "D1",
            "source_rows_observed": len(rows), "native_source_data": data}


class PrivateD1Incremental(unittest.TestCase):
    def test_ssi_new_days_and_rolling_window_exit_keeps_history(self):
        p = previous("SSI", [ssi("11/11/2026"), ssi("10/11/2026")])
        n = current("SSI", [ssi("13/11/2026"), ssi("12/11/2026"),
                            ssi("11/11/2026")])
        x = plan_d1_delta(p, n, provider="SSI", symbol="FPT")
        self.assertEqual([r["date"] for r in x["added"]],
                         ["2026-11-12", "2026-11-13"])
        self.assertEqual(x["window_exited_not_deleted"], ["2026-11-10"])
        self.assertEqual(x["unchanged_overlap"], 1)
        self.assertFalse(x["signal_eligible"])
        self.assertFalse(x["independent_signed_publish_cas"])
        self.assertEqual(x["trade_orders"], 0)

    def test_dnse_unix_day_and_unfinished_page_fail_closed(self):
        t11, t12, t13 = 1794355200, 1794441600, 1794528000
        p = previous("DNSE", [dict(dnse(t11), date_utc="2026-11-11"), dnse(t12)])
        n = current("DNSE", [dnse(t12), dict(dnse(t13), date_utc="2026-11-13")])
        x = plan_d1_delta(p, n, provider="DNSE", symbol="FPT")
        self.assertEqual(x["window_exited_not_deleted"], ["2026-11-11"])
        self.assertEqual(x["added"][0]["date"], "2026-11-13")
        n["native_source_data"]["nextTime"] = t13
        with self.assertRaisesRegex(DeltaDenied, "UNFINISHED_PAGE"):
            plan_d1_delta(p, n, provider="DNSE", symbol="FPT")

    def test_vcbs_presentation_basis_change_is_not_source_revision(self):
        p = previous("VCBS", [vcbs("2026-11-12", display=48)])
        n = current("VCBS", [vcbs("2026-11-12", display=51),
                              vcbs("2026-11-13")])
        x = plan_d1_delta(p, n, provider="VCBS", symbol="FPT")
        self.assertEqual(x["revised"], [])
        self.assertEqual(len(x["added"]), 1)
        self.assertEqual(x["unchanged_overlap"], 1)

    def test_vcbs_dcm_like_source_volume_revision_preserves_before_after(self):
        p = previous("VCBS", [vcbs("2026-11-12", volume=1749500)])
        n = current("VCBS", [vcbs("2026-11-12", volume=1749600)])
        x = plan_d1_delta(p, n, provider="VCBS", symbol="FPT")
        self.assertEqual(x["revised"][0]["changed_fields"], ["volume"])
        self.assertEqual(x["revised"][0]["before"]["volume"], 1749500)
        self.assertEqual(x["revised"][0]["after"]["volume"], 1749600)
        self.assertFalse(x["venue_closed_bar_attested"])

    def test_idempotence_exact_source_and_fingerprint(self):
        p = current("SSI", [ssi()])
        a = plan_d1_delta(p, copy.deepcopy(p), provider="SSI", symbol="FPT")
        b = plan_d1_delta(p, copy.deepcopy(p), provider="SSI", symbol="FPT")
        self.assertEqual(a, b)
        self.assertEqual(a["added"], [])
        self.assertEqual(a["revised"], [])
        self.assertEqual(a["window_exited_not_deleted"], [])
        self.assertEqual(a["previous_sha256"], a["current_sha256"])

    def test_invalid_provider_symbol_timeframe(self):
        p = previous("SSI", [ssi()])
        n = current("SSI", [ssi()])
        for provider, symbol in (("SSI", "DCM"), ("DNSE", "FPT"),
                                 ("VCBS", "FPT"), ("BAD", "FPT")):
            with self.subTest(provider=provider, symbol=symbol):
                with self.assertRaises(DeltaDenied):
                    plan_d1_delta(p, n, provider=provider, symbol=symbol)
        n["timeframe"] = "M5"
        with self.assertRaisesRegex(DeltaDenied, "PROVIDER_SYMBOL_TF_DRIFT"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")

    def test_duplicate_days_and_broken_row_count(self):
        p = previous("SSI", [ssi()])
        n = current("SSI", [ssi(), ssi()])
        with self.assertRaisesRegex(DeltaDenied, "DUPLICATE_SESSION"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")
        n["source_rows_observed"] = 1
        with self.assertRaisesRegex(DeltaDenied, "COUNT_MISMATCH"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")

    def test_invalid_ohlc_price_volume_and_missing_field(self):
        p = previous("SSI", [ssi()])
        for field, value in (("high", "48"), ("close", "nan"),
                             ("volume", "-1"), ("open", 10**200), ("low", None)):
            n = current("SSI", [ssi("13/11/2026")])
            n["native_source_data"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(DeltaDenied):
                    plan_d1_delta(p, n, provider="SSI", symbol="FPT")
        n = current("SSI", [ssi("13/11/2026")])
        del n["native_source_data"][0]["high"]
        with self.assertRaisesRegex(DeltaDenied, "MISSING_OHLCV"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")

    def test_bad_date_and_symbol_drift(self):
        p = previous("SSI", [ssi("31/02/2026")])
        n = current("SSI", [ssi("13/11/2026")])
        with self.assertRaisesRegex(DeltaDenied, "INVALID_DATE"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")
        p = previous("SSI", [ssi(symbol="DCM")])
        with self.assertRaisesRegex(DeltaDenied, "ROW_SYMBOL_DRIFT"):
            plan_d1_delta(p, n, provider="SSI", symbol="FPT")

    def test_dnse_invalid_unix_milliseconds_and_array_mismatch(self):
        p = previous("DNSE", [dnse()])
        n = current("DNSE", [dnse()])
        n["native_source_data"]["t"][0] *= 1000
        with self.assertRaisesRegex(DeltaDenied, "INVALID_DATE"):
            plan_d1_delta(p, n, provider="DNSE", symbol="FPT")
        n = current("DNSE", [dnse()])
        n["native_source_data"]["v"].append(100)
        with self.assertRaisesRegex(DeltaDenied, "BAD_ARRAYS"):
            plan_d1_delta(p, n, provider="DNSE", symbol="FPT")

    def test_existing_version_kept_when_window_shrinks(self):
        p = previous("VCBS", [vcbs("2026-11-11"), vcbs("2026-11-12")])
        n = current("VCBS", [vcbs("2026-11-12"), vcbs("2026-11-13")])
        x = plan_d1_delta(p, n, provider="VCBS", symbol="FPT")
        self.assertEqual(x["window_exited_not_deleted"], ["2026-11-11"])
        self.assertEqual(x["added"][0]["date"], "2026-11-13")
        self.assertEqual(len(x["revised"]), 0)


if __name__ == "__main__":
    unittest.main()
