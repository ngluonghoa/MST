"""§204 fake-only six-TF readiness and D1 Cache→Signal→UI integration.

All OHLCV, canonical bars, timestamps, stocks and IDs here are fictional.
This never retrieves or publishes actual market source, never implements
the original 16 detector formulae, and never generates broker orders.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import unittest

from swing_trading.contracts import DecisionStatus
from swing_trading.market_data import (
    BarClosure, CanonicalCandle, InstrumentClass, MarketBarKey,
    ObservationRevision, PriceBasis, ProviderObservationKey, Quality,
    Timeframe,
)
from swing_trading.private_multitf_readiness import (
    PrivateMultiTfDenied, PrivateMultiTfReadiness, TF_NAMES, TF_ORDER,
    inspect_six_tf_candidate_coverage,
)
from swing_trading.private_cache_signal_ui_preview import (
    PrivateCacheUiPreview, PrivateCacheUiPreviewDenied,
    render_private_d1_cache_signal_ui_preview,
)
from swing_trading.private_cache_source_bridge import PrivateSourceDenied
from swing_trading.locked_ui10_binding import LockedUi10Denied
from test_private_cache_source_bridge import NOW, source

STOCK = "STOCK:HOSE:FPT:fixture_registry_v1"
AT = datetime(2026, 11, 6, 2, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 11, 15, 2, 0, tzinfo=timezone.utc)
SECONDS = {
    Timeframe.M5: 300, Timeframe.M15: 900, Timeframe.M30: 1800,
    Timeframe.H1: 3600, Timeframe.H4: 14400, Timeframe.D1: 86400,
}


def candle(tf=Timeframe.D1, *, provider="SSI", basis=PriceBasis.RAW,
           start=AT, seen=AT, symbol=STOCK, exchange="HOSE"):
    key = MarketBarKey(
        instrument_id=symbol, exchange=exchange,
        instrument_class=InstrumentClass.STOCK, timeframe=tf,
        session_period_id="HOSE:FICTIONAL_SESSION",
        bar_start_utc=start, price_basis=basis,
        calendar_version="FAKE_CALENDAR_UNVERIFIED",
        aggregation_policy_version=(
            "FAKE_H4_DERIVED_POLICY_UNVERIFIED"
            if tf is Timeframe.H4 else "FAKE_NATIVE_POLICY_UNVERIFIED"
        ),
    )
    return CanonicalCandle(
        market_bar_key=key,
        observation_key=ProviderObservationKey(
            provider, "fake://provider-source", "FICTIONAL_ROW"
        ),
        revision=ObservationRevision(
            "FAKE_REV_0001", "a" * 64, seen, seen,
        ),
        bar_end_utc=start + timedelta(seconds=SECONDS[tf]),
        open=Decimal("20"), high=Decimal("22"),
        low=Decimal("19"), close=Decimal("21"),
        volume=100, quality=Quality.VERIFIED,
        closure=BarClosure.CLOSED,
        observed_minutes=SECONDS[tf] // 60,
        expected_minutes=SECONDS[tf] // 60,
    )


def buckets(**options):
    d = {tf: [] for tf in TF_ORDER}
    for name, bars in options.items():
        d[Timeframe(name)] = list(bars)
    return d


def examine(d, **kw):
    return inspect_six_tf_candidate_coverage(
        d, instrument_id=kw.get("instrument_id", STOCK),
        exchange=kw.get("exchange", "HOSE"),
        as_of_utc=kw.get("as_of_utc", AS_OF),
    )


def preview(provider="SSI"):
    return render_private_d1_cache_signal_ui_preview(
        source(provider), as_of_utc=NOW,
        run_id="fictional_cloud_204", exchange="HOSE",
    )


class SixTimeframeCandidateReadinessTests(unittest.TestCase):
    def test_domain_represents_all_six_and_h4_cannot_be_native(self):
        self.assertEqual(
            TF_NAMES, ("M5", "M15", "M30", "H1", "H4", "D1"),
        )
        self.assertEqual(Timeframe.H4.value, "H4")
        result = examine(buckets())
        self.assertEqual(
            [r["status"] for r in result.summary["timeframes"]],
            ["MISSING"] * 6,
        )
        self.assertEqual(result.summary["candidate_timeframes_present"], 0)
        self.assertIs(result.summary["h4_native_provider_supported"], False)
        self.assertIs(result.summary["w1_context_verified"], False)
        self.assertIs(result.summary["trades_eligible"], False)

    def test_six_fictitious_locally_complete_bars_still_not_signals(self):
        d = {tf: [candle(tf)] for tf in TF_ORDER}
        r = examine(d)
        self.assertEqual(r.summary["candidate_timeframes_present"], 6)
        self.assertEqual([x["local_necessary_checks_count"]
                          for x in r.summary["timeframes"]], [1] * 6)
        self.assertTrue(all(
            x["status"] == "CANDIDATE_ONLY_UNVERIFIED"
            for x in r.summary["timeframes"]
        ))
        self.assertTrue(all(not x["verified_for_signals"]
                            for x in r.summary["timeframes"]))
        self.assertFalse(r.qualified_for_signals)
        self.assertFalse(r.qualified_for_backtest)
        self.assertFalse(r.eligible_for_trades)
        self.assertFalse(r.summary["source_released"])
        self.assertFalse(r.summary["highwater_independent_cas_verified"])
        self.assertFalse(r.summary["ui_step08_approved"])

    def test_only_five_native_tfs_with_missing_h4_still_blocked(self):
        d = {tf: ([] if tf is Timeframe.H4 else [candle(tf)])
             for tf in TF_ORDER}
        r = examine(d)
        self.assertEqual(r.summary["candidate_timeframes_present"], 5)
        h4 = r.summary["timeframes"][4]
        self.assertEqual(h4["timeframe"], "H4")
        self.assertEqual(h4["status"], "MISSING")
        self.assertIs(h4["derived_h4_venue_policy_proven"], False)
        self.assertFalse(r.summary["signal_engine_parity_verified"])

    def test_different_candle_provider_must_not_be_mixed(self):
        d = buckets(D1=[candle(Timeframe.D1, provider="SSI")],
                    M5=[candle(Timeframe.M5, provider="DNSE")])
        with self.assertRaisesRegex(
            PrivateMultiTfDenied, "MIXED_PROVIDER_OR_BASIS"
        ):
            examine(d)

    def test_mixed_raw_adjusted_or_unknown_basis_denied(self):
        for basis in (PriceBasis.ADJUSTED, PriceBasis.UNKNOWN):
            d = buckets(
                D1=[candle(Timeframe.D1, basis=PriceBasis.RAW)],
                M5=[candle(Timeframe.M5, basis=basis)],
            )
            with self.subTest(basis=basis), self.assertRaisesRegex(
                PrivateMultiTfDenied, "MIXED_PROVIDER_OR_BASIS"
            ):
                examine(d)

    def test_unverified_source_bar_passes_no_necessary_checks(self):
        raw = candle(Timeframe.D1)
        d = buckets(D1=[replace(
            raw, quality=Quality.UNVERIFIED, closure=BarClosure.UNKNOWN
        )])
        r = examine(d)
        self.assertEqual(r.summary["timeframes"][-1]["observed_candles"], 1)
        self.assertEqual(r.summary["timeframes"][-1]["local_necessary_checks_count"], 0)
        self.assertIs(r.summary["source_released"], False)

    def test_wrong_symbol_exchange_timeframe_or_index_class_denied(self):
        base = candle()
        for changed in (
            replace(base, market_bar_key=replace(
                base.market_bar_key, instrument_id="STOCK:HOSE:HPG:fixture"
            )),
            replace(base, market_bar_key=replace(
                base.market_bar_key, exchange="HNX"
            )),
            replace(base, market_bar_key=replace(
                base.market_bar_key, timeframe=Timeframe.H1
            )),
            replace(base, market_bar_key=replace(
                base.market_bar_key, instrument_class=InstrumentClass.INDEX
            )),
        ):
            with self.subTest(source=changed.market_bar_key), self.assertRaisesRegex(
                PrivateMultiTfDenied, "LOOKAHEAD_OR_IDENTITY"
            ):
                examine(buckets(D1=[changed]))

    def test_lookahead_first_known_retrieval_and_bar_end_denied(self):
        base = candle()
        future = AS_OF + timedelta(hours=4)
        for changed in (
            replace(base, revision=ObservationRevision(
                "r2", "b" * 64, future, future
            )),
            replace(base, revision=ObservationRevision(
                "r3", "c" * 64, AT, future
            )),
            replace(base, market_bar_key=replace(
                base.market_bar_key, bar_start_utc=future
            ), bar_end_utc=future+timedelta(days=1)),
        ):
            with self.subTest(change=changed.revision.revision_id), self.assertRaisesRegex(
                PrivateMultiTfDenied, "LOOKAHEAD_OR_IDENTITY"
            ):
                examine(buckets(D1=[changed]))

    def test_repeated_or_reordered_bar_timestamp_denied(self):
        first = candle(Timeframe.M15)
        later = candle(Timeframe.M15, start=AT+timedelta(minutes=15))
        for samples in ([first, first], [later, first]):
            with self.subTest(n=len(samples)), self.assertRaisesRegex(
                PrivateMultiTfDenied, "DUPLICATE_OR_REORDERED"
            ):
                examine(buckets(M15=samples))

    def test_missing_extra_w1_bucket_and_oversized_bucket_denied(self):
        d = buckets()
        del d[Timeframe.H4]
        with self.assertRaisesRegex(PrivateMultiTfDenied, "INPUT_SCOPE_INVALID"):
            examine(d)
        d = buckets()
        d[Timeframe.W1] = []
        with self.assertRaisesRegex(PrivateMultiTfDenied, "INPUT_SCOPE_INVALID"):
            examine(d)
        d = buckets()
        d[Timeframe.M5] = [candle(Timeframe.M5)] * 513
        with self.assertRaisesRegex(PrivateMultiTfDenied, "COUNT_OR_TYPE"):
            examine(d)

    def test_bad_tf_bucket_types_and_spoofed_candles_denied(self):
        for bars in (None, {}, [1], ["FAKE_CANDLE"]):
            with self.subTest(bars=repr(bars)[:40]), self.assertRaises(
                PrivateMultiTfDenied,
            ):
                examine(buckets(D1=bars) if isinstance(bars,list)
                        else dict(buckets(), **{}) | {Timeframe.D1:bars})

    def test_instrument_asof_or_exchange_invalid_denied(self):
        for kw in (
            {"exchange": "NYSE"},
            {"instrument_id": "../private"},
            {"instrument_id": ""},
        ):
            with self.subTest(kw=kw),self.assertRaisesRegex(
                PrivateMultiTfDenied, "INPUT_SCOPE_INVALID"
            ):
                examine(buckets(), **kw)
        with self.assertRaises(ValueError):
            examine(buckets(), as_of_utc=datetime(2026, 11, 16))

    def test_deterministic_coverage_digest_without_price_rows(self):
        a = examine(buckets(M5=[candle(Timeframe.M5)]))
        b = examine(buckets(M5=[candle(Timeframe.M5)]))
        self.assertEqual(a.reference_sha256,b.reference_sha256)
        self.assertEqual(a.summary,b.summary)
        wire=json.dumps(a.summary,sort_keys=True,separators=(",",":"),
                        allow_nan=False,ensure_ascii=True)
        self.assertNotIn('"open"',wire)
        self.assertNotIn('"close"',wire)
        self.assertNotIn('"volume"',wire)
        self.assertNotIn('"source_record_id"',wire)
        self.assertNotIn('"source_sha256"',wire)

    def test_rehashed_false_release_claim_still_rejected(self):
        r = examine(buckets(D1=[candle()]))
        for key in ("source_released", "signal_engine_parity_verified",
                    "ui_step08_approved", "trades_eligible"):
            changed=deepcopy(r.summary)
            changed[key]=True
            raw=json.dumps(changed,sort_keys=True,separators=(",",":"),
                           allow_nan=False,ensure_ascii=True).encode()
            with self.subTest(key=key),self.assertRaises(
                PrivateMultiTfDenied
            ):
                PrivateMultiTfReadiness(changed,sha256(raw).hexdigest())
        r.summary["pipeline_state"]="FAKE_COMPLETED"
        with self.assertRaises(PrivateMultiTfDenied):
            PrivateMultiTfReadiness(r.summary,r.reference_sha256)


class PrivateD1CacheSignalUiIntegrationTests(unittest.TestCase):
    def test_all_three_private_source_shapes_run_end_to_end_no_trade(self):
        for provider in ("SSI","DNSE","VCBS"):
            with self.subTest(provider=provider):
                r=preview(provider)
                self.assertEqual(r.safe_summary["source_provider"],provider)
                self.assertEqual(r.safe_summary["source_rows_observed"],2)
                self.assertEqual(r.safe_summary["publication_state"],"INCOMPLETE_REPORT")
                self.assertEqual(r.safe_summary["decision"],"NO_TRADE")
                self.assertEqual(len(r.safe_summary["required_tf_coverage"]),6)
                self.assertEqual([x["status"] for x in
                    r.safe_summary["required_tf_coverage"]],
                    ["MISSING"]*5+["D1_REFERENCE_ONLY"])
                self.assertEqual(r.viewmodel.data["zone_verified_count"],0)
                self.assertEqual(len(r.viewmodel.data["zone_rows"]),16)
                self.assertTrue(all(x["status"]=="UNVERIFIED"
                                    for x in r.viewmodel.data["zone_rows"]))
                self.assertTrue(r.html.startswith('<!doctype html>'))
                self.assertIn('data-ui-section="I"',r.html)
                self.assertIn('NO_TRADE',r.html)
                self.assertIn('0/16 VERIFIED',r.html)
                self.assertFalse(r.report_published)
                self.assertFalse(r.eligible_for_signals)
                self.assertEqual(r.broker_orders,0)

    def test_preview_repeatability_and_digest_binding(self):
        a,b=preview("DNSE"),preview("DNSE")
        self.assertEqual(a.html,b.html)
        self.assertEqual(a.html_sha256,b.html_sha256)
        self.assertEqual(a.safe_summary_sha256,b.safe_summary_sha256)
        self.assertEqual(sha256(a.html.encode()).hexdigest(),a.html_sha256)
        self.assertEqual(a.safe_summary["html_sha256"],a.html_sha256)
        self.assertEqual(
            a.safe_summary["viewmodel_sha256"],a.viewmodel.reference_sha256
        )

    def test_source_snapshot_revision_changes_preview_fingerprint_not_signal(self):
        doc=source("SSI")
        a=render_private_d1_cache_signal_ui_preview(
            doc, as_of_utc=NOW, run_id="fixture204", exchange="HOSE",
        )
        bdoc=deepcopy(doc)
        bdoc["native_source_data"][0]["close"]="50800"
        b=render_private_d1_cache_signal_ui_preview(
            bdoc, as_of_utc=NOW, run_id="fixture204", exchange="HOSE",
        )
        self.assertNotEqual(a.html_sha256,b.html_sha256)
        self.assertNotEqual(a.viewmodel.reference_sha256,b.viewmodel.reference_sha256)
        self.assertEqual(a.safe_summary["decision"],"NO_TRADE")
        self.assertEqual(b.safe_summary["decision"],"NO_TRADE")

    def test_bad_source_authority_cannot_promote_ui(self):
        for provider in ("SSI","DNSE","VCBS"):
            doc=source(provider)
            doc["signal_eligible"]=True
            with self.subTest(provider=provider),self.assertRaises(
                PrivateSourceDenied
            ):
                render_private_d1_cache_signal_ui_preview(
                    doc, as_of_utc=NOW, run_id="fixture204", exchange="HOSE",
                )

    def test_invalid_run_or_exchange_or_lookahead_fail_closed(self):
        for arg in (
            {"run_id":"../leak"},
            {"exchange":"NYSE"},
        ):
            with self.subTest(arg=arg),self.assertRaises(LockedUi10Denied):
                render_private_d1_cache_signal_ui_preview(
                    source(),as_of_utc=NOW,
                    run_id=arg.get("run_id","fixture204"),
                    exchange=arg.get("exchange","HOSE"),
                )
        with self.assertRaises(PrivateSourceDenied):
            render_private_d1_cache_signal_ui_preview(
                source(), as_of_utc=datetime(2026,11,12,2,tzinfo=timezone.utc),
                run_id="fixture204", exchange="HOSE",
            )

    def test_no_source_ohlcv_prices_or_credentials_in_rendered_html(self):
        r=preview("VCBS")
        for value in ("50500","50750","51000","52000","50000",
                      "native_source_data","MST_DNSE_API_SECRET",
                      "MST_SSI_API_SECRET","FIRST_KNOWN_VERIFIED"):
            self.assertNotIn(value,r.html)
        self.assertNotIn("<script",r.html)
        self.assertNotIn("<form",r.html)
        self.assertNotIn("<button",r.html)
        self.assertNotIn("AUTO_TRADE",r.html)
        self.assertNotIn("FULL_ANALYSIS · APPROVED",r.html)

    def test_changed_html_model_or_summary_is_rejected_at_preview_boundary(self):
        original=preview()
        altered=original.html+"<script>malicious</script>"
        with self.assertRaisesRegex(
            PrivateCacheUiPreviewDenied, "AUTHORITY_OR_DIGEST"
        ):
            PrivateCacheUiPreview(
                altered,original.html_sha256,original.viewmodel,
                original.safe_summary,original.safe_summary_sha256,
            )
        changed=deepcopy(original.safe_summary)
        changed["step08_committed"]=True
        raw=json.dumps(changed,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False).encode()
        with self.assertRaisesRegex(
            PrivateCacheUiPreviewDenied, "AUTHORITY_OR_DIGEST"
        ):
            PrivateCacheUiPreview(
                original.html,original.html_sha256,original.viewmodel,
                changed,sha256(raw).hexdigest(),
            )

    def test_forced_strategies_buy_cannot_bypass_renderer(self):
        model=preview()
        model.viewmodel.data["strategies"]["SHORT"]["decision"]="BUY"
        with self.assertRaises(LockedUi10Denied):
            PrivateCacheUiPreview(
                model.html,model.html_sha256,model.viewmodel,
                model.safe_summary,model.safe_summary_sha256,
            )


if __name__=="__main__":
    unittest.main()
