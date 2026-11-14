"""Pure fake OHLCV, exact maths, rolling-window and fail-closed reference tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

from swing_trading.market_data import PriceBasis
from swing_trading.private_cache_source_bridge import (
    PrivateD1Reference, PrivateSourceDenied, QuarantinedD1Bar,
)
from swing_trading.private_d1_math_reference import (
    ReferenceMathState, PrivateD1Math, compute_private_d1_math,
    inspect_and_compute_private_d1,
)
from test_private_cache_source_bridge import source, NOW


def snap(provider="SSI", n=35, volume_target=2000,
         adjusted=False, first_day=date(2026,9,10)):
    bars=[]
    for i in range(n):
        price=Decimal(1000+10*i)
        v=volume_target if i==n-1 else 1000
        bars.append(QuarantinedD1Bar(
            provider,"FPT",first_day+timedelta(days=i),
            price,price+5,price-5,price,v,
            PriceBasis.RAW if provider=="VCBS" and not adjusted
            else PriceBasis.UNKNOWN,
            False,
        ))
    return PrivateD1Reference(
        provider,"FPT",date(2026,11,13),"a"*64,n,tuple(bars),False
    )


class PrivateD1MathReferenceTests(unittest.TestCase):
    def test_three_sources_exact_wilder_tr_and_rvol_math(self):
        for provider in ("SSI","DNSE","VCBS"):
            for n in (21,35,62):
                with self.subTest(provider=provider,n=n):
                    obj=snap(provider,n=n)
                    atr,rvol=compute_private_d1_math(obj,as_of_utc=NOW)
                    self.assertEqual(atr.state,
                                     ReferenceMathState.COMPUTED_UNCALIBRATED)
                    self.assertEqual(rvol.state,
                                     ReferenceMathState.COMPUTED_UNCALIBRATED)
                    self.assertEqual(atr.value,Decimal(15))
                    self.assertEqual(rvol.value,Decimal(2))
                    self.assertEqual(atr.used_bar_count,n)
                    self.assertEqual(rvol.used_bar_count,21)
                    for v in (atr,rvol):
                        self.assertFalse(v.actionable)
                        self.assertFalse(v.venue_close_attested)
                        self.assertFalse(v.first_known_attested)
                        self.assertFalse(v.data_certified)
                        self.assertFalse(v.parameter_approved)
                        self.assertFalse(v.history_complete_certified)
                        self.assertFalse(v.comparator_policy_certified)
                        self.assertEqual(v.source_provider,provider)
                        self.assertEqual(v.source_symbol,"FPT")
                        self.assertEqual(v.capture_day,date(2026,11,13))
                        self.assertEqual(v.source_digest_sha256,"a"*64)
                    if provider=="VCBS":
                        self.assertEqual(atr.price_basis,PriceBasis.RAW)
                    else:
                        self.assertEqual(atr.price_basis,PriceBasis.UNKNOWN)

    def test_exact_minimum_bar_counts_fail_closed_below_boundary(self):
        for n in (1,3,14,15,20):
            with self.subTest(n=n):
                a,r=compute_private_d1_math(snap(n=n),as_of_utc=NOW)
                if n<15:
                    self.assertEqual(a.state,ReferenceMathState.BLOCKED)
                    self.assertIsNone(a.value)
                else:
                    self.assertEqual(a.state,ReferenceMathState.COMPUTED_UNCALIBRATED)
                    self.assertEqual(a.value,Decimal(15))
                self.assertEqual(r.state,ReferenceMathState.BLOCKED)
                self.assertIsNone(r.value)

    def test_wilder_smoothing_uses_entire_native_provider_window(self):
        baseline=snap(n=35)
        x,_=compute_private_d1_math(baseline,as_of_utc=NOW)
        # A valid altered high on the FIRST seeded bar changes the seed,
        # and propagates causally through all later Wilder updates.
        bars=list(baseline.bars)
        b=bars[1]
        bars[1]=replace(b,high_vnd=b.high_vnd+Decimal(100))
        corrected=replace(baseline,bars=tuple(bars),raw_source_sha256="b"*64)
        y,_=compute_private_d1_math(corrected,as_of_utc=NOW)
        self.assertNotEqual(x.value,y.value)
        self.assertGreater(y.value,x.value)
        self.assertEqual(y.source_digest_sha256,"b"*64)
        self.assertEqual(x.value,Decimal(15))

    def test_rolling_window_shortening_is_not_an_indication_to_delete(self):
        old=snap(n=35)
        current=replace(old,bars=old.bars[1:],
                        source_rows_observed=34,raw_source_sha256="c"*64)
        old_atr,old_rvol=compute_private_d1_math(old,as_of_utc=NOW)
        new_atr,new_rvol=compute_private_d1_math(current,as_of_utc=NOW)
        self.assertEqual(old_rvol.value,new_rvol.value)
        self.assertEqual(old_atr.value,new_atr.value)
        self.assertEqual(len(old.bars),35)  # no mutation/deletion
        self.assertEqual(len(current.bars),34)
        self.assertNotEqual(old_atr.source_digest_sha256,new_atr.source_digest_sha256)

    def test_20_prior_volumes_exclude_target_and_zero_denominator_blocks(self):
        s=snap(n=35,volume_target=10000)
        a,r=compute_private_d1_math(s,as_of_utc=NOW)
        self.assertEqual(r.value,Decimal(10))
        bars=list(s.bars)
        for i in range(14,34):
            bars[i]=replace(bars[i],volume_shares=0)
        z=replace(s,bars=tuple(bars),raw_source_sha256="c"*64)
        _,r=compute_private_d1_math(z,as_of_utc=NOW)
        self.assertEqual(r.state,ReferenceMathState.BLOCKED)
        self.assertIsNone(r.value)
        self.assertEqual(r.reason,"ZERO_PRIOR_20_VOLUME_DENOMINATOR")

    def test_a_different_provider_price_basis_or_symbol_is_not_folded_in(self):
        for provider in ("SSI","DNSE","VCBS"):
            s=snap(provider=provider)
            bars=list(s.bars)
            bars[-1]=replace(bars[-1],provider="OTHER")
            with self.subTest(provider=provider),self.assertRaisesRegex(
                    PrivateSourceDenied,"SERIES_CONTEXT_INVALID"):
                compute_private_d1_math(replace(s,bars=tuple(bars)),as_of_utc=NOW)
        s=snap()
        bars=list(s.bars)
        bars[-1]=replace(bars[-1],reported_price_basis=PriceBasis.RAW)
        with self.assertRaisesRegex(PrivateSourceDenied,"SERIES_CONTEXT_INVALID"):
            compute_private_d1_math(replace(s,bars=tuple(bars)),as_of_utc=NOW)

    def test_capture_date_is_not_backcast_into_fake_first_known(self):
        s=snap(n=35)
        earlier=datetime(2026,11,12,23,59,tzinfo=timezone.utc)
        with self.assertRaisesRegex(PrivateSourceDenied,"REFERENCE_AUTHORITY_INVALID"):
            compute_private_d1_math(s,as_of_utc=earlier)
        for field in ("eligible_for_signals","eligible_for_backtest",
                      "source_is_appowned_publisher","venue_close_attested",
                      "issuer_first_known_attested"):
            with self.subTest(field=field),self.assertRaises(
                    PrivateSourceDenied):
                compute_private_d1_math(replace(s,**{field:True}),as_of_utc=NOW)
        with self.assertRaises(ValueError):
            compute_private_d1_math(s,as_of_utc=datetime(2026,11,14,12))

    def test_future_session_unsorted_bar_or_wrong_identity_denied(self):
        s=snap(n=35)
        out_of_order=replace(s,bars=tuple(reversed(s.bars)))
        wrong_symbol=replace(s,bars=(replace(s.bars[0],symbol="DCM"),)+s.bars[1:])
        with self.assertRaises(PrivateSourceDenied):
            compute_private_d1_math(out_of_order,as_of_utc=NOW)
        with self.assertRaises(PrivateSourceDenied):
            compute_private_d1_math(wrong_symbol,as_of_utc=NOW)
        future=replace(s,bars=s.bars[:-1]+(
            replace(s.bars[-1],trading_date=date(2026,11,15)),))
        with self.assertRaises(PrivateSourceDenied):
            compute_private_d1_math(future,as_of_utc=NOW)

    def test_actual_native_envelope_api_remains_quarantined_even_when_short(self):
        for provider in ("SSI","DNSE","VCBS"):
            with self.subTest(provider=provider):
                native=source(provider)
                ref,values=inspect_and_compute_private_d1(
                    native,as_of_utc=NOW)
                self.assertEqual(ref.provider,provider)
                self.assertEqual(len(values),2)
                self.assertTrue(all(x.state is ReferenceMathState.BLOCKED
                                    for x in values))
                self.assertTrue(all(x.value is None for x in values))
                self.assertTrue(all(not x.actionable for x in values))

    def test_result_objects_cannot_claim_official_source_or_trading(self):
        a,r=compute_private_d1_math(snap(),as_of_utc=NOW)
        for flag in ("first_known_attested","venue_close_attested",
                     "data_certified","history_complete_certified",
                     "comparator_policy_certified",
                     "parameter_approved","actionable"):
            for value in (True,1):
                with self.subTest(flag=flag,value=value),self.assertRaises(
                    PrivateSourceDenied
                ):
                    replace(a,**{flag:value})
        with self.assertRaises(PrivateSourceDenied):
            replace(a,value=Decimal("-1"))


if __name__=="__main__":
    unittest.main()
