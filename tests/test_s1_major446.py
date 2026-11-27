"""§446 fictional W1 major candidate, explicit selected early branch."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_major446 import S1MajorPlan446
from test_s1_context439 import fixture as context_fixture,run
from test_s1_rf_volume444 import fixture as rf_fixture,FAILED,CHOCH
from test_causal_indicators import make_bar,snap

MAJOR="S1/F_MAJOR_CYCLE_TOP_PENDING"


def fixture(tf=Timeframe.M15,context=Timeframe.D1,early=FAILED,*,close=D(7)):
    inputs,p=rf_fixture(tf,context,early)
    daily=inputs.snapshots_for(Timeframe.D1)
    d1=daily[p.rf.target_index].selected
    weeks=(inputs.snapshots_for(Timeframe.W1) if context is Timeframe.W1 else
           context_fixture(Timeframe.W1)[0].snapshots_for(Timeframe.W1))
    added=[]
    for i,c in ((0,D(10)),(1,close)):
        begin=d1.verified_at_utc+timedelta(days=1+8*(i-1))
        end=begin+timedelta(days=5)
        row=make_bar(1600+i,timeframe=Timeframe.W1,start=begin,open_price=c,
                     close=c,high=max(D(12),c),low=min(D(6),c))
        rev=replace(row.observation_revision,first_known_time_utc=end,
                    retrieved_at_utc=end+timedelta(minutes=1))
        row=replace(row,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                    verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        added.append(snap(row,asof=inputs.as_of_utc))
    weeks=weeks+tuple(added)
    inputs=replace(inputs,buckets=tuple((f,weeks if f is Timeframe.W1 else rows) for f,rows in inputs.buckets))
    return inputs,replace(p,major=S1MajorPlan446(early,Timeframe.W1,len(weeks)-1,0,(1,5),(3,7),
                                               1,1,TiePolicy.STRICT_V1,len(daily)-15,len(daily),D(0)))


class S1Major446Tests(unittest.TestCase):
    def test_all_major_combinations(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    for early in (FAILED,CHOCH):
                        inputs,p=fixture(tf,context,early)
                        row,safe=run(inputs,p,strategy,MAJOR)
                        proof=row.private_preview.assessments[-1][1]
                        self.assertEqual(proof.major.weekly_higher_low,D(8))
                        self.assertTrue(proof.major.candidate_match)
                        self.assertFalse(proof.major.action_eligible)
                        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],["GEOMETRY_MATCH_ONLY"]*4)

    def test_no_w1_closed_break_or_epsilon(self):
        inputs,p=fixture(close=D(8))
        _,safe=run(inputs,p,variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,major=replace(p.major,candidate_epsilon=None)),variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"DISTANCE_ONLY")

    def test_no_w1_fallback_or_volume_reuse(self):
        inputs,p=fixture()
        missing=replace(inputs,buckets=tuple((f,() if f is Timeframe.W1 else rows) for f,rows in inputs.buckets))
        _,safe=run(missing,p,variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=None)),variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_late_right_witness_and_stale_atr(self):
        inputs,p=fixture()
        weeks=inputs.snapshots_for(Timeframe.W1)
        late=snap(replace(weeks[8].selected,verified_at_utc=weeks[-2].market_bar_key.bar_start_utc+
                          timedelta(minutes=1)),asof=inputs.as_of_utc)
        altered=replace(inputs,buckets=tuple((f,weeks[:8]+(late,)+weeks[9:] if f is Timeframe.W1 else rows)
                                              for f,rows in inputs.buckets))
        _,safe=run(altered,p,variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,major=replace(p.major,atr_start=p.major.atr_start-1,atr_stop=p.major.atr_stop-1)),variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_branch_and_frame_no_implicit_promotion(self):
        inputs,p=fixture()
        for changed,variant in ((p,FAILED),(replace(p,major=replace(p.major,early_variant=CHOCH)),MAJOR),
                                (replace(p,major=replace(p.major,timeframe=Timeframe.D1)),MAJOR),
                                (replace(p,major=None),MAJOR)):
            _,safe=run(inputs,changed,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_major_label_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p,variant=MAJOR)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("weekly_higher_low","weekly_atr_d1","candidate_match",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
