"""§499 synthetic dual-frame decline regressions."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.b1_decline499 import B1DeclinePlan499,B1DeclineWindow499
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s1_context439 import fixture as context_fixture
from test_causal_indicators import snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

VARIANTS=("B1/E_RECLAIM","B1/E_BOS_UP","B1/F_MAJOR_REVERSAL_PENDING")


def fixture(*,weekly_fall=True,daily_fall=True):
    inputs,d=context_fixture(Timeframe.D1,fall=daily_fall)
    w_inputs,w=context_fixture(Timeframe.W1,fall=weekly_fall)
    inputs=alter(inputs,Timeframe.W1,w_inputs.snapshots_for(Timeframe.W1))
    def window(p):
        return B1DeclineWindow499(p.start,p.stop,p.high_indices,p.low_indices,
                                  p.left_count,p.right_count,p.tie_policy,p.candidate_min_span_bars)
    return inputs,B1DeclinePlan499(0,window(w),window(d))


def run(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0],mode=EngineMode.RESEARCH):
    r=evaluate_candidate(inputs,mode=mode,profile=profile((request("B1",p,strategy=strategy,variant=variant),)))
    return row(r.private_preview,"B1",strategy),r.safe_summary()


class B1Decline499Tests(unittest.TestCase):
    def test_dual_frame_both_strategies_variants(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                inputs,p=fixture()
                r,s=run(inputs,p,strategy,variant)
                self.assertIs(r.private_preview.assessments[0][1].state,S1State439.MATCH)
                self.assertFalse(r.private_preview.action_eligible)
                self.assertFalse(s["publication_allowed"])

    def test_no_single_frame_or_rising_fallback(self):
        for kwargs in (dict(weekly_fall=False),dict(daily_fall=False)):
            inputs,p=fixture(**kwargs)
            r,_=run(inputs,p)
            self.assertIs(r.private_preview.assessments[0][1].state,S1State439.NONMATCH)

    def test_missing_frame(self):
        inputs,p=fixture()
        for tf in (Timeframe.W1,Timeframe.D1,Timeframe.M15):
            r,_=run(alter(inputs,tf,()),p)
            self.assertIs(r.private_preview.assessments[0][1].state,S1State439.MISSING)

    def test_no_default_and_span(self):
        inputs,p=fixture()
        for k,state in ((None,S1State439.DISTANCE),(8,S1State439.NONMATCH)):
            r,_=run(inputs,replace(p,weekly=replace(p.weekly,candidate_min_span_bars=k)))
            self.assertIs(r.private_preview.assessments[0][1].state,state)

    def test_late_stale_and_malformed(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.W1)
        anchor=inputs.snapshots_for(Timeframe.M15)[0].selected
        late=snap(replace(rows[-1].selected,verified_at_utc=anchor.market_bar_key.bar_start_utc+timedelta(minutes=1)))
        r,_=run(alter(inputs,Timeframe.W1,rows[:-1]+(late,)),p)
        self.assertIs(r.private_preview.assessments[0][1].state,S1State439.BLOCKED)
        r,_=run(inputs,replace(p,weekly=replace(p.weekly,stop=8)))
        self.assertIs(r.private_preview.assessments[0][1].state,S1State439.BLOCKED)
        r,_=run(inputs,replace(p,anchor_index=True))
        self.assertIsNone(r.private_preview)

    def test_shared_modes_and_private_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r,s=run(inputs,p,mode=mode)
            self.assertIs(r.private_preview.assessments[0][1].state,S1State439.MATCH)
            self.assertNotIn("private_frame_states",json.dumps(s))
            self.assertFalse(s["production_qualified"])
