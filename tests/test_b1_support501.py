"""§501 fictional B1 post-bottom support checks."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_bottom500 import B1SupportPlan501
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_bottom500 import fixture as bottom_fixture
from test_b1_decline499 import run,VARIANTS
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter


def fixture(*,low=D(6),close=D(10),threshold=D("0.2"),missing=False):
    inputs,p=bottom_fixture()
    rows=inputs.snapshots_for(Timeframe.D1)
    anchor=inputs.snapshots_for(Timeframe.M15)[p.evaluation_index].selected
    start=anchor.market_bar_key.bar_start_utc+timedelta(days=1)
    if not missing:
        rows+=(snap(make_bar(980,start=start,low=low,close=close)),)
    return alter(inputs,Timeframe.D1,rows),B1SupportPlan501(p,18,0,18,threshold)


def proof(inputs,p,strategy=Strategy.SHORT,variant=VARIANTS[0],mode=EngineMode.RESEARCH):
    r,s=run(inputs,p,strategy,variant,mode)
    return r.private_preview.assessments[-1][1],s


class B1Support501Tests(unittest.TestCase):
    def test_all_strategies_variants(self):
        for strategy in Strategy:
            for variant in VARIANTS:
                inputs,p=fixture()
                g,s=proof(inputs,p,strategy,variant)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_distance,D(0))
                self.assertFalse(s["publication_allowed"])

    def test_far_and_closed_support_failure(self):
        for kwargs in (dict(low=D(4)),dict(low=D(4),close=D(5))):
            inputs,p=fixture(**kwargs)
            self.assertIs(proof(inputs,p)[0].state,S1State439.NONMATCH)

    def test_no_default_and_missing(self):
        for kwargs,state in ((dict(threshold=None),S1State439.DISTANCE),(dict(missing=True),S1State439.MISSING)):
            inputs,p=fixture(**kwargs)
            self.assertIs(proof(inputs,p)[0].state,state)

    def test_no_prior_bottom_bypass(self):
        inputs,p=fixture()
        p=replace(p,context=replace(p.context,candidate_k_touch=None))
        self.assertIs(proof(inputs,p)[0].state,S1State439.BLOCKED)

    def test_exact_target_and_atr_scope(self):
        inputs,p=fixture()
        for bad in (replace(p,target_index=19,atr_stop=19),replace(p,atr_stop=17)):
            r,_=run(inputs,bad)
            self.assertIsNone(r.private_preview)
        p=replace(p,context=replace(p.context,stop=17))
        self.assertIs(proof(inputs,replace(p,target_index=17,atr_stop=17))[0].state,S1State439.BLOCKED)

    def test_shared_modes_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            g,s=proof(inputs,p,mode=mode)
            self.assertIs(g.state,S1State439.MATCH)
            for key in ("private_distance","private_support","private_bottom"):
                self.assertNotIn(key,json.dumps(s))
            self.assertFalse(s["production_qualified"])
