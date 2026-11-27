"""§441 explicit fictional failed breakout after distribution."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_failed_break441 import S1FailedBreakPlan441
from test_s1_distribution440 import fixture as distribution,run
from test_causal_indicators import make_bar,snap


def intraday(tf,i,begin,close):
    bar=make_bar(i,timeframe=tf,start=begin,open_price=close,close=close,
                 high=max(D(23),close),low=min(D(14),close))
    if tf is Timeframe.H1:
        end=begin+timedelta(hours=1)
        rev=replace(bar.observation_revision,first_known_time_utc=end,
                    retrieved_at_utc=end+timedelta(minutes=1))
        bar=replace(bar,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                    verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
    return snap(bar)


def fixture(tf=Timeframe.M15,context=Timeframe.D1,*,prior=D(21),close=D(19)):
    inputs,p=distribution(context)
    rc=inputs.snapshots_for(Timeframe.D1)[p.distribution.target_index].selected
    begin=rc.verified_at_utc+timedelta(days=1)
    rows=inputs.snapshots_for(tf)
    rows=rows+(intraday(tf,1100,begin,prior),intraday(tf,1101,begin+timedelta(hours=2),close))
    inputs=replace(inputs,buckets=tuple((f,rows if f is tf else s) for f,s in inputs.buckets))
    return inputs,replace(p,failed=S1FailedBreakPlan441(tf,len(rows)-1,6,21,D(0)))


class S1FailedBreak441Tests(unittest.TestCase):
    def test_all_frames_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    inputs,p=fixture(tf,context)
                    row,safe=run(inputs,p,strategy)
                    route,g=row.private_preview.assessments[2]
                    self.assertIs(route.selected_frame,tf)
                    self.assertGreater(g.private_atr,D(0))
                    self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_strict_close_and_prior_break_not_wick(self):
        for kw in ({"prior":D(20)},{"close":D(20)},{"close":D(21)}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_epsilon_no_default_and_explicit_buffer(self):
        inputs,p=fixture()
        for epsilon,state in ((None,"DISTANCE_ONLY"),(D(1),"GEOMETRY_NONMATCH_ONLY")):
            _,safe=run(inputs,replace(p,failed=replace(p.failed,candidate_epsilon=epsilon)))
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)

    def test_missing_and_prior_or_distribution_not_matched(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,failed=replace(p.failed,target_index=p.failed.target_index+1)))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"MISSING_INPUT")
        _,safe=run(inputs,replace(p,distribution=None))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,distribution=replace(p.distribution,candidate_min_rvol=D(3))))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")

    def test_late_pair_stale_atr_and_wrong_variant(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.failed.timeframe)
        prior=rows[-2].selected
        late=snap(replace(prior,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        data=replace(inputs,buckets=tuple((f,rows[:-2]+(late,rows[-1]) if f is p.failed.timeframe else s)
                                         for f,s in inputs.buckets))
        _,safe=run(data,p)
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,failed=replace(p.failed,atr_start=5,atr_stop=20)))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,p,variant="S1/E_CHOCH_DOWN")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_redacted_no_authority(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,failed=None))
        self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_atr","candidate_epsilon",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
