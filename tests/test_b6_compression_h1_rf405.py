"""§405 B6 compression explicit H1 RF and legacy D1 preservation."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_compression_breakout404 import CompressionH1RFPlan405
from swing_trading.b6_baseline_preview387 import B6State387, B6RFVolumePlan389, B6H1VolumePlan394
from swing_trading.b6_rf_volume405 import B6RFVolumePlan389 as DailyPlan, B6H1VolumePlan394 as HourPlan
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from swing_trading.source_quality import ObservationOrigin
from test_b6_compression_d1_rf404 import data as d1_data, config as d1_config, rf
from test_b6_compression_early403 import plan
from test_b6_compression_rc396 import run
from test_causal_indicators import make_bar, snap


def data(*, price=D(113), prior=D(109), missing=False, late=False, mixed=False, **kwargs):
    base=d1_data(**kwargs)
    m15=base.snapshots_for(Timeframe.M15)
    start=base.snapshots_for(Timeframe.D1)[20].market_bar_key.bar_start_utc+timedelta(hours=10)
    pair=[]
    for i,p in enumerate((prior,price)):
        row=make_bar(400+i,timeframe=Timeframe.H1,start=start+timedelta(hours=2*i),
                    open_price=p,close=p,high=max(D(114),p+1),low=p-1)
        obs=replace(row.observation_key,source_stream_id="fictional-h1",
                    origin=ObservationOrigin.IMPORT if mixed else row.observation_key.origin)
        row=replace(row,observation_key=obs,observation_revision=replace(row.observation_revision,observation_key=obs))
        pair.append(snap(row))
    if late:
        m15=m15[:-1]+(snap(replace(m15[-1].selected,verified_at_utc=pair[-1].selected.bar_end_utc)),)
    return BaselineResolvedInputs(base.instrument_id,base.exchange,base.as_of_utc,False,
        tuple((tf,() if missing else tuple(pair)) if tf is Timeframe.H1 else
              (tf,m15 if tf is Timeframe.M15 else bucket) for tf,bucket in base.buckets))


def config(index=1,eps=D("0.05")):
    return replace(plan(),rf=CompressionH1RFPlan405(index,eps))


class CompressionH1RF405Tests(unittest.TestCase):
    def test_both_strategies_exact_h1_route(self):
        for strategy in Strategy:
            row,safe=run(data(),config(),strategy=strategy)
            route,proof=row.private_preview.assessments[-1]
            self.assertIs(route.selected_frame,Timeframe.H1)
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertEqual(proof.reason,"COMPRESSION_SAME_PIVOT_H1_CROSS_ONLY")
            self.assertEqual(proof.volume_state,"H1_VOLUME_SPEC_PENDING")
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_no_h1_to_d1_fallback_and_legacy_d1(self):
        inputs=data(missing=True)
        row,safe=run(inputs,config())
        self.assertIs(rf(row).state,B6State387.MISSING)
        row,_=run(inputs,d1_config())
        self.assertIs(rf(row).state,B6State387.MATCH)
        self.assertEqual(rf(row).volume_state,"D1_VOLUME_SPEC_PENDING")
        self.assertIs(B6RFVolumePlan389,DailyPlan)
        self.assertIs(B6H1VolumePlan394,HourPlan)

    def test_wick_and_prior_cross_nonmatch(self):
        for inputs in (data(price=D(110)),data(prior=D(113))):
            row,_=run(inputs,config())
            self.assertIs(rf(row).state,B6State387.NONMATCH)

    def test_late_m15_far_or_source_mismatch_blocks(self):
        for inputs in (data(late=True),data(far=True),data(mixed=True)):
            row,safe=run(inputs,config())
            self.assertIs(rf(row).state,B6State387.BLOCKED)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"BLOCKED")

    def test_invalid_and_missing_explicit_pair(self):
        for p in (config(index=True),config(index=0),config(eps=None)):
            _,safe=run(data(),p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        row,_=run(data(),config(index=2))
        self.assertIs(rf(row).state,B6State387.MISSING)
        row,_=run(data(),replace(config(),early=None))
        self.assertIs(rf(row).state,B6State387.MISSING)

    def test_redacted_no_authority(self):
        row,safe=run(data(),config())
        self.assertFalse(row.private_preview.action_eligible)
        self.assertIsNone(rf(row).rvol)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fictional-h1","candidate_epsilon","113","pivot_price","breakout_index"):
            self.assertNotIn(secret,json.dumps(safe))
