"""§456 S3 M15 micro CHoCH candidate, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3ChochPlan456,S3State454
from test_s3_near455 import setup
from test_s3_context454 import run
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap

VARIANT="S3/E_MICRO_CHOCH"


def fixture(tf=Timeframe.D1,*,fall=False,close=D(13),prior=D(16)):
    inputs,p=setup(tf)
    rows=inputs.snapshots_for(Timeframe.M15)
    begin=rows[-1].selected.verified_at_utc+timedelta(minutes=1)
    bars=[]
    for i in range(9):
        h=D(18 if i==1 else (17 if fall else 19) if i==5 else 17)
        l=D(12 if i==3 else (11 if fall else 14) if i==7 else 15)
        bars.append(snap(make_bar(3500+i,timeframe=Timeframe.M15,
             start=begin+timedelta(minutes=20*i),open_price=D(16),close=D(16),high=h,low=l)))
    for i,c in enumerate((prior,close),9):
        bars.append(snap(make_bar(3500+i,timeframe=Timeframe.M15,
             start=begin+timedelta(minutes=20*i),open_price=c,close=c,high=max(D(17),c),low=min(D(12),c))))
    p=replace(p,choch=S3ChochPlan456(Timeframe.M15,len(rows)+10,len(rows),(1,5),(3,7),
              1,1,TiePolicy.STRICT_V1,0,15,D(0)))
    return alter(inputs,Timeframe.M15,rows+tuple(bars)),p


class S3Choch456Tests(unittest.TestCase):
    def test_both_frames_and_strategies(self):
        for tf in (Timeframe.D1,Timeframe.W1):
            for strategy in Strategy:
                inputs,p=fixture(tf)
                row,safe=run(inputs,p,strategy,VARIANT)
                route,g=row.private_preview.assessments[2]
                self.assertIn(Timeframe.M15,route.fixed_frames)
                self.assertIs(g.state,S3State454.MATCH)
                self.assertEqual((g.private_higher_low,g.private_micro_hl),(D(8),D(14)))
                self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_no_rising_no_cross_or_major_loss(self):
        for kw in ({"fall":True},{"close":D(14)},{"prior":D(13)},{"close":D(7)}):
            inputs,p=fixture(**kw)
            row,_=run(inputs,p,variant=VARIANT)
            self.assertIs(row.private_preview.assessments[2][1].state,S3State454.NONMATCH)

    def test_missing_or_late_right_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        row,_=run(alter(inputs,Timeframe.M15,rows[:-1]),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[2][1].state,S3State454.MISSING)
        i=p.choch.history_start+8
        late=snap(replace(rows[i].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        row,_=run(alter(inputs,Timeframe.M15,rows[:i]+(late,)+rows[i+1:]),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[2][1].state,S3State454.BLOCKED)

    def test_context_invalidated_and_no_near(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.M15)
        i=p.choch.history_start
        breached=snap(replace(rows[i].selected,high=D(21),close=D(21)))
        row,_=run(alter(inputs,Timeframe.M15,rows[:i]+(breached,)+rows[i+1:]),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[2][1].state,S3State454.NONMATCH)
        _,safe=run(inputs,replace(p,near=None),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")

    def test_explicit_threshold_and_variant(self):
        inputs,p=fixture()
        for e,state in ((None,S3State454.DISTANCE),(D(100),S3State454.NONMATCH)):
            row,_=run(inputs,replace(p,choch=replace(p.choch,candidate_epsilon=e)),variant=VARIANT)
            self.assertIs(row.private_preview.assessments[2][1].state,state)
        for variant in ("S3/E_TP","S3/F_MICRO_BREAK","S3/F_TP"):
            _,safe=run(inputs,p,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_legacy_and_no_authority(self):
        inputs,p=fixture()
        a,sa=run(inputs,p,variant=VARIANT)
        b,sb=run(inputs,p,variant=VARIANT)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        for secret in ("private_micro_hl","private_atr","high_indices",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        old,_=run(inputs,replace(p,choch=None),variant=VARIANT)
        self.assertEqual(len(old.private_preview.assessments),2)
