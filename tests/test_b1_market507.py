"""§507 fictional RF market continuity."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_market507 import B1MarketPlan507
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_market506 import fixture as r0_fixture,benchmark,proof
from test_causal_indicators import snap


def fixture(variant="B1/E_RECLAIM",*,end=D(11)):
    inputs,p=r0_fixture(variant)
    i=p.prior.geometry.target_index
    rows=inputs.snapshots_for(Timeframe.D1)[i-2:i+1]
    bench=tuple(benchmark(s.selected,v) for s,v in zip(rows,(D(10),D(10),end)))
    return inputs,B1MarketPlan507(p,replace(p.market,stock_start=i-2,stock_stop=i+1,benchmark_rows=bench))


class B1Market507Tests(unittest.TestCase):
    def test_both_variants_and_strategies(self):
        for v in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for strategy in Strategy:
                inputs,p=fixture(v)
                a,s=proof(inputs,p,v,strategy)
                self.assertEqual(len(a),4)
                self.assertIs(a[-1][1].state,S1State439.MATCH)
                self.assertEqual(a[-1][1].private_market.private_market_return,D("0.1"))
                self.assertFalse(s["publication_allowed"])

    def test_nonmatch_and_prior_gate(self):
        inputs,p=fixture(end=D(9))
        self.assertIs(proof(inputs,p)[0][-1][1].state,S1State439.NONMATCH)
        inputs,p=fixture()
        q=replace(p,prior=replace(p.prior,market=replace(p.prior.market,candidate_min_return=D(1))))
        a,_=proof(inputs,q)
        self.assertEqual(len(a),1)
        self.assertIs(a[0][1].state,S1State439.NONMATCH)

    def test_same_definition(self):
        inputs,p=fixture()
        for m in (replace(p.market,policy_version="changed"),replace(p.market,candidate_min_return=D(0))):
            self.assertIs(proof(inputs,replace(p,market=m))[0][-1][1].state,S1State439.BLOCKED)

    def test_wrong_stream_or_late(self):
        inputs,p=fixture()
        b=p.market.benchmark_rows[-1].selected
        late=snap(replace(b,verified_at_utc=b.verified_at_utc+timedelta(seconds=1)))
        self.assertIs(proof(inputs,replace(p,market=replace(p.market,benchmark_rows=p.market.benchmark_rows[:-1]+(late,))))[0][-1][1].state,S1State439.BLOCKED)
        rows=[]
        for s in p.market.benchmark_rows:
            r=s.selected
            o=replace(r.observation_key,source_stream_id="other-stream")
            rows.append(snap(replace(r,observation_key=o,observation_revision=replace(r.observation_revision,observation_key=o))))
        self.assertIs(proof(inputs,replace(p,market=replace(p.market,benchmark_rows=tuple(rows))))[0][-1][1].state,S1State439.BLOCKED)

    def test_stale_and_bad_config(self):
        inputs,p=fixture()
        self.assertIs(proof(inputs,replace(p,market=p.prior.market))[0][-1][1].state,S1State439.BLOCKED)
        from test_b1_decline499 import run
        r,_=run(inputs,replace(p,market=replace(p.market,benchmark_rows=())))
        self.assertIsNone(r.private_preview)

    def test_modes_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,mode=mode)
            self.assertIs(a[-1][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            for k in ("private_market","fixture-b1-market","fixture-market-stream"):
                self.assertNotIn(k,json.dumps(s))
