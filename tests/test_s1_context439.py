"""§439 fictional S1 R0 scoped rising geometry."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.s1_context_preview439 import S1ContextPlan439
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375,evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import model
from test_causal_indicators import AS_OF,make_bar,snap


VARIANTS=("S1/E_FAILED_BREAK","S1/E_CHOCH_DOWN","S1/F_MAJOR_CYCLE_TOP_PENDING")


def fixture(tf=Timeframe.D1,*,fall=False):
    inputs=model()
    target=inputs.snapshots_for(Timeframe.M15)[0].selected
    start=target.market_bar_key.bar_start_utc
    days=7 if tf is Timeframe.W1 else 1
    rows=[]
    for i in range(9):
        h=D(16 if i==1 else (14 if fall else 20) if i==5 else 12)
        l=D(6 if i==3 else (5 if fall else 8) if i==7 else 9)
        begin=start-timedelta(days=(10-i)*days)
        row=make_bar(800+i,timeframe=tf,start=begin,high=h,low=l)
        if tf is Timeframe.W1:
            end=begin+timedelta(days=5)
            rev=replace(row.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            row=replace(row,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(snap(row))
    inputs=replace(inputs,buckets=tuple((f,tuple(rows) if f is tf else s)
                                       for f,s in inputs.buckets))
    return inputs,S1ContextPlan439(tf,0,0,9,(1,5),(3,7),1,1,TiePolicy.STRICT_V1,7)


def run(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    result=evaluate_baseline_preview(inputs,requests=(BaselinePreviewRequest375("S1",strategy,variant,p),))
    row=next(r for r in result.rows if r.decision.zone_id=="S1" and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="S1" and r["strategy"]==strategy.value)
    return row,safe


class S1Context439Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.W1,Timeframe.D1):
            for strategy in Strategy:
                for variant in VARIANTS:
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,p,strategy,variant)
                    route,g=row.private_preview.assessments[0]
                    self.assertIs(route.selected_frame,tf)
                    self.assertEqual((g.private_resistance,g.private_higher_low,g.observed_span_bars),(D(20),D(8),7))
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_falling_or_short_span_nonmatch(self):
        inputs,p=fixture(fall=True)
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,candidate_min_span_bars=8))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_no_default_and_invalid(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,candidate_min_span_bars=None))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"DISTANCE_ONLY")
        for changed in (replace(p,timeframe=Timeframe.H1),replace(p,candidate_min_span_bars=True),
                        replace(p,high_indices=(True,5))):
            _,safe=run(inputs,changed)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_late_right_witness_and_stale_window(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.timeframe)
        cutoff=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
        late=snap(replace(rows[-1].selected,verified_at_utc=cutoff+timedelta(minutes=1)))
        altered=replace(inputs,buckets=tuple((f,rows[:-1]+(late,) if f is p.timeframe else s)
                                            for f,s in inputs.buckets))
        for a,b in ((altered,p),(inputs,replace(p,stop=8))):
            _,safe=run(a,b)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_no_frame_fallback(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,timeframe=Timeframe.W1))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")

    def test_redaction_no_major_or_sell_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p,variant=VARIANTS[-1])
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_resistance","private_higher_low","observed_span_bars",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
