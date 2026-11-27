"""§449 S2 causal rally candidate fictional regression."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s2_context448 import S2RallyPlan449,S2State448
from test_s2_context448 import fixture,run
from test_causal_indicators import make_bar,snap


def alter(inputs,frame,rows):
    return replace(inputs,buckets=tuple((f,rows if f is frame else old) for f,old in inputs.buckets))


def setup(close=D(13),k=D(1)):
    inputs,p=fixture()
    daily=inputs.snapshots_for(Timeframe.D1)
    anchor=inputs.snapshots_for(Timeframe.M15)[0]
    start=daily[0].market_bar_key.bar_start_utc
    prefix=tuple(snap(make_bar(2200+i,start=start-timedelta(days=6-i))) for i in range(6))
    inputs=alter(inputs,Timeframe.D1,prefix+daily)
    p=replace(p,d1=replace(p.d1,start=6,stop=15),rally=S2RallyPlan449(1,0,15,k))
    target=snap(make_bar(2300,timeframe=Timeframe.M15,
                start=anchor.market_bar_key.bar_start_utc+timedelta(minutes=20),
                high=max(D(14),close),low=D(8),close=close))
    return alter(inputs,Timeframe.M15,(anchor,target)),p


class S2Rally449Tests(unittest.TestCase):
    def test_both_strategies_and_exact_boundary(self):
        for strategy in Strategy:
            inputs,p=setup(close=D(14),k=D(0))
            row,safe=run(inputs,p,strategy)
            rc=row.private_preview.assessments[1][1]
            self.assertIs(rc.state,S2State448.MATCH)
            self.assertEqual(rc.private_distance,D(0))
            self.assertGreater(rc.private_atr,D(0))
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_far_above_and_nonrally(self):
        for close,k in ((D(13),D(0)),(D(15),D(1)),(D(10),D(1))):
            inputs,p=setup(close,k)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[1][1].state,S2State448.NONMATCH)

    def test_missing_target_and_late_prior(self):
        inputs,p=setup()
        rows=inputs.snapshots_for(Timeframe.M15)
        row,_=run(alter(inputs,Timeframe.M15,rows[:1]),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.MISSING)
        target=rows[1].selected
        other=replace(target.observation_key,source_stream_id="other-fixture-stream")
        mixed=snap(replace(target,observation_key=other,
                           observation_revision=replace(target.observation_revision,observation_key=other)))
        row,_=run(alter(inputs,Timeframe.M15,(rows[0],mixed)),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.BLOCKED)
        late=snap(replace(rows[0].selected,verified_at_utc=rows[1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.M15,(late,rows[1])),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.BLOCKED)

    def test_stale_context_and_late_atr(self):
        inputs,p=setup()
        daily=inputs.snapshots_for(Timeframe.D1)
        cutoff=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
        new=snap(make_bar(2400,start=cutoff-timedelta(hours=6)+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.D1,daily+(new,)),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.BLOCKED)
        late=snap(replace(daily[0].selected,verified_at_utc=cutoff+timedelta(hours=1)))
        row,_=run(alter(inputs,Timeframe.D1,(late,)+daily[1:]),p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.BLOCKED)

    def test_explicit_threshold_and_invalid_plan(self):
        inputs,p=setup(k=None)
        row,_=run(inputs,p)
        self.assertIs(row.private_preview.assessments[1][1].state,S2State448.DISTANCE)
        for bad in (True,D(-1),D("NaN")):
            _,safe=run(inputs,replace(p,rally=replace(p.rally,candidate_k_near=bad)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_redaction(self):
        inputs,p=setup()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertNotIn("private_distance",json.dumps(sa))
        old,_=run(inputs,replace(p,rally=None))
        self.assertEqual(len(old.private_preview.assessments),1)
