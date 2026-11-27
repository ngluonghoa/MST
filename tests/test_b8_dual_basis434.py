"""§434 fictional dual-basis RS stream alignment."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.b8_rs_stock434 import B8RSStockPlan434
from swing_trading.contracts import Strategy
from swing_trading.market_data import PriceBasis, Timeframe
from test_b8_rf_rs422 import fixture
from test_b8_base415 import run
from test_b8_r0_band433 import bind as r0_band
from test_b8_band426 import bind as rf_band
from test_causal_indicators import snap


def rekey(row,basis,stream,**kw):
    key=replace(row.market_bar_key,price_basis=basis,**kw)
    obs=replace(row.observation_key,market_bar_key=key,source_stream_id=stream)
    rev=replace(row.observation_revision,observation_key=obs)
    return snap(replace(row,market_bar_key=key,observation_key=obs,observation_revision=rev))


def model(tf=Timeframe.D1):
    inputs,p=fixture(tf)
    adj=tuple(rekey(x.selected,PriceBasis.ADJUSTED,"adjusted-stream")
              for x in inputs.snapshots_for(Timeframe.D1))
    buckets=tuple((f,tuple(rekey(x.selected,PriceBasis.RAW,"raw-stream") for x in rows))
                  for f,rows in inputs.buckets)
    inputs=replace(inputs,buckets=buckets)
    return inputs,replace(p,rs_stock=B8RSStockPlan434(adj,"fixture-dual-basis-v1"))


class B8DualBasis434Tests(unittest.TestCase):
    def test_raw_price_band_with_adjusted_rs_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=model(tf)
                    row,safe=run(inputs,rf_band(inputs,r0_band(inputs,p)),strategy=strategy,variant=variant)
                    base,rf=row.private_preview.assessments[0][1],row.private_preview.assessments[-1][1]
                    self.assertTrue(base.rs.candidate_match)
                    self.assertTrue(rf.rs.candidate_match)
                    self.assertIsNotNone(base.band)
                    self.assertIsNotNone(rf.band)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wrong_instrument_session_or_stream(self):
        inputs,p=model()
        plan=p.rs_stock
        x=plan.adjusted_daily[10].selected
        for changed in (rekey(x,PriceBasis.ADJUSTED,"adjusted-stream",instrument_id="other"),
                        rekey(x,PriceBasis.ADJUSTED,"adjusted-stream",session_period_id="other"),
                        rekey(x,PriceBasis.ADJUSTED,"raw-stream")):
            rows=plan.adjusted_daily[:10]+(changed,)+plan.adjusted_daily[11:]
            _,safe=run(inputs,replace(p,rs_stock=replace(plan,adjusted_daily=rows)))
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_late_adjusted_and_missing_window(self):
        inputs,p=model()
        plan=p.rs_stock
        rows=plan.adjusted_daily
        late=snap(replace(rows[14].selected,verified_at_utc=inputs.as_of_utc))
        _,safe=run(inputs,replace(p,rs_stock=replace(plan,adjusted_daily=rows[:14]+(late,)+rows[15:])))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,rs_stock=replace(plan,adjusted_daily=rows[:14])))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")

    def test_no_implicit_basis_fallback(self):
        inputs,p=model()
        _,safe=run(inputs,replace(p,rs_stock=None))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        legacy,p=fixture()
        row,_=run(legacy,p)
        self.assertTrue(row.private_preview.assessments[-1][1].rs.candidate_match)

    def test_invalid_explicit_alignment(self):
        inputs,p=model()
        for changed in (replace(p.rs_stock,alignment_policy=""),True):
            _,safe=run(inputs,replace(p,rs_stock=changed))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,rs=None))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redacted_no_authority(self):
        inputs,p=model()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("adjusted-stream","raw-stream","fixture-dual-basis-v1",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
