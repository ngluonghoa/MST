"""§442 fictional selected CHoCH down, exact microstructure."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_choch442 import S1ChochPlan442
from test_s1_distribution440 import fixture as distribution,run
from test_s1_failed_break441 import intraday
from test_causal_indicators import snap

VARIANT="S1/E_CHOCH_DOWN"


def fixture(tf=Timeframe.M15,context=Timeframe.D1,*,fall=False,close=D(7),prior=D(10)):
    inputs,p=distribution(context)
    rc=inputs.snapshots_for(Timeframe.D1)[p.distribution.target_index].selected
    begin=rc.verified_at_utc+timedelta(days=1)
    rows=inputs.snapshots_for(tf)
    start=len(rows)
    added=[]
    for i in range(9):
        high=D(16 if i==1 else (14 if fall else 20) if i==5 else 12)
        low=D(6 if i==3 else (5 if fall else 8) if i==7 else 9)
        s=intraday(tf,1200+i,begin+timedelta(hours=2*i),D(10))
        added.append(snap(replace(s.selected,high=high,low=low)))
    added.append(intraday(tf,1209,begin+timedelta(hours=18),prior))
    added.append(intraday(tf,1210,begin+timedelta(hours=20),close))
    rows=rows+tuple(added)
    inputs=replace(inputs,buckets=tuple((f,rows if f is tf else s) for f,s in inputs.buckets))
    return inputs,replace(p,choch=S1ChochPlan442(tf,len(rows)-1,start,(1,5),(3,7),
                      1,1,TiePolicy.STRICT_V1,6,21,D(0)))


class S1Choch442Tests(unittest.TestCase):
    def test_both_frames_contexts_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    inputs,p=fixture(tf,context)
                    row,safe=run(inputs,p,strategy,VARIANT)
                    route,g=row.private_preview.assessments[2]
                    self.assertIs(route.selected_frame,tf)
                    self.assertEqual(g.private_higher_low,D(8))
                    self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_nonrising_or_no_closed_break(self):
        for kw in ({"fall":True},{"close":D(8)},{"prior":D(7)}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p,variant=VARIANT)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_no_default_and_explicit_epsilon(self):
        inputs,p=fixture()
        for e,state in ((None,"DISTANCE_ONLY"),(D(1),"GEOMETRY_NONMATCH_ONLY")):
            _,safe=run(inputs,replace(p,choch=replace(p.choch,candidate_epsilon=e)),variant=VARIANT)
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)

    def test_late_right_bar_and_wrong_pivot(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.choch.timeframe)
        i=p.choch.history_start+8
        late=snap(replace(rows[i].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+
                         timedelta(seconds=1)))
        data=replace(inputs,buckets=tuple((f,rows[:i]+(late,)+rows[i+1:] if f is p.choch.timeframe else s)
                                         for f,s in inputs.buckets))
        _,safe=run(data,p,variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,choch=replace(p.choch,low_indices=(3,8))),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")

    def test_missing_context_wrong_variant_and_invalid(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,distribution=None),variant=VARIANT)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,p)
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        for changed in (replace(p.choch,high_indices=(True,5)),replace(p.choch,history_start=True)):
            _,safe=run(inputs,replace(p,choch=changed),variant=VARIANT)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p,variant=VARIANT)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_higher_low","private_atr","high_indices",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
