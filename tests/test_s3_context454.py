"""§454 S3 R0 causal rising D1 with explicit structural target, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375,evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3ContextPlan454,S3Resistance454,S3TrendWindow454,S3State454
from test_s1_context439 import fixture as rising_fixture
from test_s2_rally449 import alter
from test_causal_indicators import snap


VARIANTS=("S3/E_MICRO_CHOCH","S3/E_TP","S3/F_MICRO_BREAK","S3/F_TP")


def fixture(tf=Timeframe.D1,*,fall=False):
    inputs,_=rising_fixture(Timeframe.D1,fall=fall)
    if tf is Timeframe.W1:
        weekly,_=rising_fixture(Timeframe.W1)
        inputs=alter(inputs,Timeframe.W1,weekly.snapshots_for(Timeframe.W1))
    d=S3TrendWindow454(0,9,(1,5),(3,7),1,1,TiePolicy.STRICT_V1)
    r=S3Resistance454(tf,0,9,5,1,1,TiePolicy.STRICT_V1)
    return inputs,S3ContextPlan454(0,d,r)


def run(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0]):
    result=evaluate_baseline_preview(inputs,requests=(BaselinePreviewRequest375("S3",strategy,variant,p),))
    row=next(r for r in result.rows if r.decision.zone_id=="S3" and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="S3" and r["strategy"]==strategy.value)
    return row,safe


class S3Context454Tests(unittest.TestCase):
    def test_both_structural_target_frames_strategies_variants(self):
        for tf in (Timeframe.D1,Timeframe.W1):
            for strategy in Strategy:
                for variant in VARIANTS:
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,p,strategy,variant)
                    g=row.private_preview.assessments[0][1]
                    self.assertIs(g.state,S3State454.MATCH)
                    self.assertEqual((g.private_d1_hh,g.private_higher_low,g.private_resistance),(D(20),D(8),D(20)))
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_falling_d1_or_anchor_beyond_target(self):
        inputs,p=fixture(fall=True)
        row,_=run(inputs,p)
        self.assertIs(row.private_preview.assessments[0][1].state,S3State454.NONMATCH)
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        a=snap(replace(rows[0].selected,high=D(21),close=D(21)))
        row,_=run(alter(inputs,Timeframe.M15,(a,)+rows[1:]),p)
        self.assertIs(row.private_preview.assessments[0][1].state,S3State454.NONMATCH)

    def test_missing_d1_resistance_anchor_no_fallback(self):
        inputs,p=fixture(Timeframe.W1)
        for tf in (Timeframe.D1,Timeframe.W1,Timeframe.M15):
            row,_=run(alter(inputs,tf,()),p)
            self.assertIs(row.private_preview.assessments[0][1].state,S3State454.MISSING)

    def test_late_witness_and_stale_window(self):
        inputs,p=fixture(Timeframe.W1)
        rows=inputs.snapshots_for(Timeframe.W1)
        cutoff=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
        late=snap(replace(rows[-1].selected,verified_at_utc=cutoff+timedelta(minutes=1)))
        for a,b in ((alter(inputs,Timeframe.W1,rows[:-1]+(late,)),p),
                    (inputs,replace(p,resistance=replace(p.resistance,stop=8)))):
            row,_=run(a,b)
            self.assertIs(row.private_preview.assessments[0][1].state,S3State454.BLOCKED)

    def test_wrong_scope_and_invalid_config(self):
        inputs,p=fixture()
        for bad in (replace(p,anchor_index=True),replace(p,d1=replace(p.d1,high_indices=(True,5))),
                    replace(p,resistance=replace(p.resistance,timeframe=Timeframe.H1)),
                    replace(p,resistance=replace(p.resistance,pivot_index=True))):
            _,safe=run(inputs,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        with self.assertRaisesRegex(ValueError,"MST_375_UNSUPPORTED_REQUEST"):
            evaluate_baseline_preview(inputs,requests=(BaselinePreviewRequest375("S1",Strategy.SHORT,"S1/E_FAILED_BREAK",p),))

    def test_legacy_and_redaction_no_tp_or_sell_authority(self):
        inputs,p=fixture()
        a,sa=run(inputs,p,variant=VARIANTS[-1])
        b,sb=run(inputs,p,variant=VARIANTS[-1])
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("private_d1_hh","private_higher_low","private_resistance",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        self.assertEqual(len(a.private_preview.assessments),1)
