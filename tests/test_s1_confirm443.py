"""§443 fictional full S1 candidate D1 structural HL break."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_confirm443 import S1ConfirmPlan443
from test_s1_failed_break441 import fixture as failed
from test_s1_choch442 import fixture as choch
from test_s1_context439 import run
from test_causal_indicators import make_bar,snap

FAILED="S1/E_FAILED_BREAK"
CHOCH="S1/E_CHOCH_DOWN"


def fixture(tf=Timeframe.M15,context=Timeframe.D1,variant=FAILED,*,close=D(7),prior=D(10),fall=False):
    inputs,p=(failed(tf,context) if variant==FAILED else choch(tf,context))
    e=p.failed if variant==FAILED else p.choch
    early=inputs.snapshots_for(tf)[e.target_index].selected
    begin=early.verified_at_utc+timedelta(days=1)
    rows=inputs.snapshots_for(Timeframe.D1)
    start=len(rows)
    added=[]
    for i in range(9):
        high=D(16 if i==1 else (14 if fall else 20) if i==5 else 12)
        low=D(6 if i==3 else (5 if fall else 8) if i==7 else 9)
        added.append(snap(make_bar(1300+i,start=begin+timedelta(days=i),high=high,low=low)))
    for i,c in ((9,prior),(10,close)):
        added.append(snap(make_bar(1300+i,start=begin+timedelta(days=i),open_price=c,
                                    close=c,high=max(D(12),c),low=min(D(6),c))))
    rows=rows+tuple(added)
    inputs=replace(inputs,buckets=tuple((f,rows if f is Timeframe.D1 else s) for f,s in inputs.buckets))
    target=len(rows)-1
    return inputs,replace(p,rf=S1ConfirmPlan443(Timeframe.D1,target,start,(1,5),(3,7),
                                     1,1,TiePolicy.STRICT_V1,target-15,target,D(0)))


class S1Confirm443Tests(unittest.TestCase):
    def test_all_selected_branches_frames_and_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    for variant in (FAILED,CHOCH):
                        inputs,p=fixture(tf,context,variant)
                        row,safe=run(inputs,p,strategy,variant)
                        proof=row.private_preview.assessments[-1][1]
                        self.assertEqual(proof.private_higher_low,D(8))
                        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                                         ["GEOMETRY_MATCH_ONLY"]*4)

    def test_no_close_break_or_prior_rising_structure(self):
        for kw in ({"close":D(8)},{"prior":D(7)},{"fall":True}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_or_unmatched_early(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,failed=None))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,failed=replace(p.failed,candidate_epsilon=D(10))))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,target_index=p.rf.target_index+1)))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_late_right_bar_and_stale_atr(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.D1)
        i=p.rf.history_start+8
        late=snap(replace(rows[i].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+
                         timedelta(seconds=1)))
        data=replace(inputs,buckets=tuple((f,rows[:i]+(late,)+rows[i+1:] if f is Timeframe.D1 else s)
                                         for f,s in inputs.buckets))
        _,safe=run(data,p)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,atr_start=p.rf.atr_start-1,atr_stop=p.rf.atr_stop-1)))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_epsilon_invalid_frame_and_major_variant(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,rf=replace(p.rf,candidate_epsilon=None)))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,timeframe=Timeframe.H1)))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,failed=None),variant="S1/F_MAJOR_CYCLE_TOP_PENDING")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_higher_low","private_atr","high_indices",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
