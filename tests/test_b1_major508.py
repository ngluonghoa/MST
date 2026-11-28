"""§508 fictional separate W1 major reversal candidate."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_major508 import B1MajorPlan508
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import PrivateMultiTfDenied
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_market507 import fixture as rf_fixture
from test_b1_market506 import proof
from test_b1_decline499 import run
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter

MAJOR="B1/F_MAJOR_REVERSAL_PENDING"


def fixture(early="B1/E_RECLAIM",*,low=D(7)):
    inputs,p=rf_fixture(early)
    g=p.prior.prior.geometry
    d1=inputs.snapshots_for(Timeframe.D1)[g.target_index].selected
    weeks=inputs.snapshots_for(Timeframe.W1)
    begin=d1.verified_at_utc+timedelta(days=1)
    end=begin+timedelta(days=5)
    r=make_bar(1700,timeframe=Timeframe.W1,start=begin,high=D(24),low=low,open_price=D(10),close=D(22))
    rev=replace(r.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
    r=replace(r,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
              verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
    return alter(inputs,Timeframe.W1,weeks+(snap(r),)),B1MajorPlan508(p,early,len(weeks))


class B1Major508Tests(unittest.TestCase):
    def test_both_explicit_branches_strategies(self):
        for early in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for strategy in Strategy:
                inputs,p=fixture(early)
                a,s=proof(inputs,p,MAJOR,strategy)
                self.assertEqual(len(a),4)
                self.assertIs(a[-1][1].state,S1State439.MATCH)
                self.assertEqual(a[-1][1].private_weekly_floor,D(5))
                self.assertIn(Timeframe.W1,a[-1][0].fixed_frames)
                self.assertFalse(s["publication_allowed"])

    def test_new_structural_low_even_wick(self):
        inputs,p=fixture(low=D(4))
        a,_=proof(inputs,p,MAJOR)
        self.assertIs(a[-1][1].state,S1State439.NONMATCH)

    def test_no_weekly_fallback(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.W1)
        a,_=proof(alter(inputs,Timeframe.W1,rows[:-1]),p,MAJOR)
        self.assertIs(a[-1][1].state,S1State439.MISSING)
        a,_=proof(inputs,replace(p,weekly_target_index=p.weekly_target_index-1),MAJOR)
        self.assertIs(a[-1][1].state,S1State439.BLOCKED)

    def test_late_or_wrong_source(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.W1)
        r=rows[-1].selected
        o=replace(r.observation_key,source_stream_id="fixture-other")
        wrong=snap(replace(r,observation_key=o,observation_revision=replace(r.observation_revision,observation_key=o)))
        with self.assertRaisesRegex(PrivateMultiTfDenied,"MST_368_MIXED_BUCKET_SOURCE_REVISION"):
            alter(inputs,Timeframe.W1,rows[:-1]+(wrong,))
        late=snap(replace(r,verified_at_utc=inputs.as_of_utc+timedelta(seconds=1)))
        with self.assertRaisesRegex(PrivateMultiTfDenied,"MST_368_SELECTED_REVISION_LOOKAHEAD"):
            alter(inputs,Timeframe.W1,rows[:-1]+(late,))

    def test_exact_variant_and_no_prior_bypass(self):
        inputs,p=fixture()
        for q,v in ((p,"B1/E_RECLAIM"),(replace(p,early_variant="B1/E_BOS_UP"),MAJOR),(replace(p,weekly_target_index=True),MAJOR)):
            r,_=run(inputs,q,variant=v)
            self.assertIsNone(r.private_preview)
        q=replace(p,prior=replace(p.prior,market=replace(p.prior.market,candidate_min_return=D(2))))
        a,_=proof(inputs,q,MAJOR)
        self.assertIsNot(a[-1][1].state,S1State439.MATCH)

    def test_modes_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,MAJOR,mode=mode)
            self.assertIs(a[-1][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            self.assertNotIn("private_weekly_floor",json.dumps(s))
