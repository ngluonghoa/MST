"""§503 fictional B1 BOS_UP event and causal geometry regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_bos_up503 import B1BosUpPlan503
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_support501 import fixture as support_fixture
from test_b1_decline499 import run
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter


def fixture(*,target_close=D(16),prior_close=D(10),epsilon=D("0.2"),missing=False):
    inputs,p=support_fixture()
    origin=inputs.snapshots_for(Timeframe.D1)[p.target_index].selected
    start=origin.verified_at_utc+timedelta(minutes=1)
    rows=inputs.snapshots_for(Timeframe.M15)
    path=tuple(snap(make_bar(1100+i,timeframe=Timeframe.M15,start=start+timedelta(minutes=20*i),
                high=h,low=D(8),close=c)) for i,(h,c) in enumerate(
                ((D(12),D(10)),(D(14),D(12)),(D(12),D(10)),(D(16),prior_close),(D(16),target_close))))
    target=path[-1].selected
    inputs=alter(inputs,Timeframe.M15,rows+(path[:-1] if missing else path))
    return inputs,B1BosUpPlan503(p,2,6,1,1,1,TiePolicy.STRICT_V1,
        target.source_event_ids[0],target.observation_revision.source_revision_or_payload_digest,
        target.verified_at_utc,target.verified_at_utc+timedelta(minutes=1),0,19,epsilon)


def proof(inputs,p,strategy=Strategy.SHORT,mode=EngineMode.RESEARCH):
    r,s=run(inputs,p,strategy,"B1/E_BOS_UP",mode)
    return r.private_preview.assessments[-1][1],s


class B1BosUp503Tests(unittest.TestCase):
    def test_both_strategies(self):
        for strategy in Strategy:
            inputs,p=fixture()
            g,s=proof(inputs,p,strategy)
            self.assertIs(g.state,S1State439.MATCH)
            self.assertEqual(g.private_micro_high,D(14))
            self.assertFalse(s["publication_allowed"])

    def test_wick_only_earlier_cross_and_no_default(self):
        for kwargs,state in ((dict(target_close=D(14)),S1State439.NONMATCH),
                             (dict(prior_close=D(15)),S1State439.NONMATCH),
                             (dict(epsilon=None),S1State439.DISTANCE)):
            inputs,p=fixture(**kwargs)
            self.assertIs(proof(inputs,p)[0].state,state)

    def test_event_revision_and_clock(self):
        inputs,p=fixture()
        for bad in (replace(p,event_id="wrong"),replace(p,event_revision="wrong"),
                    replace(p,event_known_at_utc=p.event_known_at_utc-timedelta(seconds=1))):
            self.assertIs(proof(inputs,bad)[0].state,S1State439.BLOCKED)

    def test_missing_and_no_prior_bypass(self):
        inputs,p=fixture(missing=True)
        self.assertIs(proof(inputs,p)[0].state,S1State439.MISSING)
        inputs,p=fixture()
        p=replace(p,context=replace(p.context,candidate_k_near=None))
        self.assertIs(proof(inputs,p)[0].state,S1State439.BLOCKED)

    def test_exact_variant_and_distinct_witness(self):
        inputs,p=fixture()
        for bad,variant in ((p,"B1/E_RECLAIM"),(replace(p,high_index=2),"B1/E_BOS_UP")):
            r,_=run(inputs,bad,variant=variant)
            self.assertIsNone(r.private_preview)

    def test_shared_modes_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            g,s=proof(inputs,p,mode=mode)
            self.assertIs(g.state,S1State439.MATCH)
            for key in ("private_event_id","private_micro_high",p.event_id,p.event_revision):
                self.assertNotIn(key,json.dumps(s))
            self.assertFalse(s["production_qualified"])
