"""§450 explicit S2 M15 micro LH and rejection fictional tests."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s2_context448 import S2EarlyPlan450,S2State448
from test_s2_context448 import run
from test_s2_rally449 import alter,setup as rally_setup
from test_causal_indicators import make_bar,snap


def setup(*,higher=False,close=D(11),high=D(14),k=D(0)):
    inputs,p=rally_setup()
    rows=inputs.snapshots_for(Timeframe.M15)
    start=rows[0].market_bar_key.bar_start_utc
    extra=[]
    for i,h in enumerate((15,12,12,16 if higher else 14,12),2):
        extra.append(snap(make_bar(2500+i,timeframe=Timeframe.M15,
                     start=start+timedelta(minutes=20*i),high=D(h),close=D(11))))
    target=snap(make_bar(2507,timeframe=Timeframe.M15,
                start=start+timedelta(minutes=140),open_price=D(12),high=high,close=close))
    inputs=alter(inputs,Timeframe.M15,rows+tuple(extra)+(target,))
    p=replace(p,early=S2EarlyPlan450(7,1,(1,4),1,1,TiePolicy.STRICT_V1,k))
    return inputs,p


class S2Early450Tests(unittest.TestCase):
    def test_both_strategies_exact_rejection(self):
        for strategy in Strategy:
            inputs,p=setup()
            row,safe=run(inputs,p,strategy)
            proof=row.private_preview.assessments[2][1]
            self.assertIs(proof.state,S2State448.MATCH)
            self.assertEqual(proof.private_micro_lh,D(14))
            self.assertEqual(proof.private_distance,D(0))
            self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_no_higher_high_or_bullish_candle_or_far_rejection(self):
        for kw in ({"higher":True},{"close":D(13)},{"high":D(15)}):
            inputs,p=setup(**kw)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[2][1].state,S2State448.NONMATCH)

    def test_missing_target_and_late_right_bar(self):
        inputs,p=setup()
        rows=inputs.snapshots_for(Timeframe.M15)
        row,_=run(alter(inputs,Timeframe.M15,rows[:-1]),p)
        self.assertIs(row.private_preview.assessments[2][1].state,S2State448.MISSING)
        late=snap(replace(rows[-2].selected,verified_at_utc=rows[-1].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.M15,rows[:-2]+(late,rows[-1])),p)
        self.assertIs(row.private_preview.assessments[2][1].state,S2State448.BLOCKED)

    def test_prior_phase_dependency_and_resistance_break(self):
        inputs,p=setup()
        row,_=run(inputs,replace(p,rally=replace(p.rally,candidate_k_near=D(0))))
        self.assertIs(row.private_preview.assessments[2][1].state,S2State448.BLOCKED)
        rows=inputs.snapshots_for(Timeframe.M15)
        changed=snap(replace(rows[2].selected,close=D(15)))
        row,_=run(alter(inputs,Timeframe.M15,rows[:2]+(changed,)+rows[3:]),p)
        self.assertIs(row.private_preview.assessments[2][1].state,S2State448.NONMATCH)

    def test_explicit_threshold_and_config(self):
        inputs,p=setup(k=None)
        row,_=run(inputs,p)
        self.assertIs(row.private_preview.assessments[2][1].state,S2State448.DISTANCE)
        for plan in (replace(p.early,candidate_k_rejection=True),replace(p.early,history_start=0),
                     replace(p.early,high_indices=(True,4))):
            _,safe=run(inputs,replace(p,early=plan))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_redacted_determinism(self):
        inputs,p=setup()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertNotIn("private_micro_lh",json.dumps(sa))
        old,_=run(inputs,replace(p,early=None))
        self.assertEqual(len(old.private_preview.assessments),2)
