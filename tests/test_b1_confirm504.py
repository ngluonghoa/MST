"""§504 fictional D1 higher-low and BOS_UP regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_confirm504 import B1ConfirmPlan504
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_reclaim502 import fixture as reclaim_fixture
from test_b1_bos_up503 import fixture as bos_fixture
from test_b1_decline499 import run
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter


def fixture(variant="B1/E_RECLAIM",*,close=D(21),low=D(8),epsilon=D("0.1")):
    inputs,p=(reclaim_fixture if variant=="B1/E_RECLAIM" else bos_fixture)()
    early=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    p=replace(p,expires_at_utc=early.verified_at_utc+timedelta(days=10))
    rows=inputs.snapshots_for(Timeframe.D1)
    path=tuple(snap(make_bar(1200+i,start=early.verified_at_utc+timedelta(days=i+1),
        high=h,low=l,close=c)) for i,(h,l,c) in enumerate(
        ((D(14),D(9),D(12)),(D(18),D(10),D(15)),(D(15),D(9),D(12)),
         (D(14),low,D(11)),(D(15),D(10),D(12)),(D(17),D(11),D(15)),
         (D(22),D(10),close))))
    n=len(rows)
    return alter(inputs,Timeframe.D1,rows+path),B1ConfirmPlan504(p,n,n+6,1,3,1,1,
        TiePolicy.STRICT_V1,0,n+6,epsilon)


def proof(inputs,p,variant="B1/E_RECLAIM",strategy=Strategy.SHORT,mode=EngineMode.RESEARCH):
    r,s=run(inputs,p,strategy,variant,mode)
    return r.private_preview.assessments[-1][1],s


class B1Confirm504Tests(unittest.TestCase):
    def test_both_branches_strategies(self):
        for strategy in Strategy:
            for variant in ("B1/E_RECLAIM","B1/E_BOS_UP"):
                inputs,p=fixture(variant)
                g,s=proof(inputs,p,variant,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual((g.private_higher_low,g.private_key_high),(D(8),D(18)))
                self.assertFalse(s["publication_allowed"])

    def test_closed_cross_higher_low_and_explicit_threshold(self):
        for kw,state in ((dict(close=D(18)),S1State439.NONMATCH),(dict(low=D(6)),S1State439.NONMATCH),
                         (dict(epsilon=None),S1State439.DISTANCE),(dict(epsilon=D(10)),S1State439.NONMATCH)):
            inputs,p=fixture(**kw)
            self.assertIs(proof(inputs,p)[0].state,state)

    def test_missing_and_prior_gate(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.D1)
        self.assertIs(proof(alter(inputs,Timeframe.D1,rows[:-1]),p)[0].state,S1State439.MISSING)
        p=replace(p,early=replace(p.early,candidate_epsilon=D(10)))
        self.assertIs(proof(inputs,p)[0].state,S1State439.BLOCKED)

    def test_expiry_and_m15_invalidation(self):
        inputs,p=fixture()
        early=inputs.snapshots_for(Timeframe.M15)[p.early.target_index].selected
        q=replace(p,early=replace(p.early,expires_at_utc=early.verified_at_utc))
        self.assertIs(proof(inputs,q)[0].state,S1State439.BLOCKED)
        m15=inputs.snapshots_for(Timeframe.M15)
        b=snap(make_bar(1299,timeframe=Timeframe.M15,start=early.verified_at_utc+timedelta(minutes=5),low=D(4),close=D(5)))
        self.assertIs(proof(alter(inputs,Timeframe.M15,m15+(b,)),p)[0].state,S1State439.NONMATCH)

    def test_exact_branch_and_config(self):
        inputs,p=fixture()
        for q,variant in ((p,"B1/E_BOS_UP"),(p,"B1/F_MAJOR_REVERSAL_PENDING"),(replace(p,low_index=True),"B1/E_RECLAIM")):
            r,_=run(inputs,q,variant=variant)
            self.assertIsNone(r.private_preview)

    def test_shared_modes_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            g,s=proof(inputs,p,mode=mode)
            self.assertIs(g.state,S1State439.MATCH)
            for k in ("private_higher_low","private_key_high",p.early.event_id):
                self.assertNotIn(k,json.dumps(s))
            self.assertFalse(s["production_qualified"])
