"""§506 fictional causal benchmark context."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_market506 import B1MarketPlan506,B1MarketWindow506
from swing_trading.contracts import Strategy
from swing_trading.market_data import InstrumentClass,Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_rf_volume505 import fixture as volume_fixture
from test_b1_decline499 import run
from test_causal_indicators import snap


def benchmark(row,price):
    key=replace(row.market_bar_key,instrument_id="fixture-b1-market",instrument_class=InstrumentClass.INDEX)
    obs=replace(row.observation_key,market_bar_key=key,source_stream_id="fixture-market-stream")
    rev=replace(row.observation_revision,observation_key=obs)
    return snap(replace(row,market_bar_key=key,observation_key=obs,observation_revision=rev,
                        open=price,close=price,high=price+D(1),low=price-D(1)))


def fixture(variant="B1/E_RECLAIM",*,end=D(11),threshold=D("0.05")):
    inputs,p=volume_fixture(variant)
    stop=p.geometry.early.context.context.stop
    rows=inputs.snapshots_for(Timeframe.D1)[stop-3:stop]
    bench=tuple(benchmark(s.selected,v) for s,v in zip(rows,(D(10),D(10),end)))
    return inputs,B1MarketPlan506(p,B1MarketWindow506("fixture-b1-market","fixture-policy",stop-3,stop,bench,threshold))


def proof(inputs,p,variant="B1/E_RECLAIM",strategy=Strategy.SHORT,mode=EngineMode.RESEARCH):
    r,s=run(inputs,p,strategy,variant,mode)
    return r.private_preview.assessments,s


class B1Market506Tests(unittest.TestCase):
    def test_both_variants_and_strategies(self):
        for v in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for strategy in Strategy:
                inputs,p=fixture(v)
                a,s=proof(inputs,p,v,strategy)
                self.assertEqual(len(a),4)
                self.assertIs(a[0][1].state,S1State439.MATCH)
                self.assertEqual(a[0][1].private_market_return,D("0.1"))
                self.assertFalse(s["publication_allowed"])

    def test_no_default_and_negative_market(self):
        for kw,state in ((dict(end=D(9)),S1State439.NONMATCH),(dict(threshold=None),S1State439.DISTANCE)):
            inputs,p=fixture(**kw)
            a,_=proof(inputs,p)
            self.assertEqual(len(a),1)
            self.assertIs(a[0][1].state,state)

    def test_wrong_identity_and_order(self):
        inputs,p=fixture()
        for m in (replace(p.market,benchmark_id="wrong"),replace(p.market,benchmark_rows=p.market.benchmark_rows[::-1])):
            self.assertIs(proof(inputs,replace(p,market=m))[0][0][1].state,S1State439.BLOCKED)

    def test_late_and_wrong_window(self):
        inputs,p=fixture()
        m=p.market
        b=m.benchmark_rows[-1].selected
        late=snap(replace(b,verified_at_utc=inputs.as_of_utc))
        for bad in (replace(m,benchmark_rows=m.benchmark_rows[:-1]+(late,)),replace(m,stock_start=m.stock_start-1,stock_stop=m.stock_stop-1)):
            self.assertIs(proof(inputs,replace(p,market=bad))[0][0][1].state,S1State439.BLOCKED)

    def test_bad_config(self):
        inputs,p=fixture()
        for bad in (replace(p.market,policy_version=""),replace(p.market,candidate_min_return=D(-1)),replace(p.market,benchmark_rows=())):
            r,_=run(inputs,replace(p,market=bad))
            self.assertIsNone(r.private_preview)

    def test_modes_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,mode=mode)
            self.assertIs(a[0][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            for k in ("private_market_return","fixture-b1-market","fixture-market-stream","fixture-policy"):
                self.assertNotIn(k,json.dumps(s))
