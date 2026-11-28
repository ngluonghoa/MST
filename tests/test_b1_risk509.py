"""§509 fictional structural risk, no fill or publication authority."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_risk509 import B1RiskPlan509,B1RiskTerms509
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_market507 import fixture as regular_fixture
from test_b1_major508 import fixture as major_fixture,MAJOR
from test_b1_market506 import proof
from test_b1_decline499 import run
from test_causal_indicators import snap
from test_s2_rally449 import alter


def fixture(early="B1/E_RECLAIM",major=False):
    inputs,p=(major_fixture if major else regular_fixture)(early)
    weeks=inputs.snapshots_for(Timeframe.W1)
    weeks=weeks[:1]+(snap(replace(weeks[1].selected,high=D(40))),)+weeks[2:]
    inputs=alter(inputs,Timeframe.W1,weeks)
    risk=B1RiskTerms509("fictional-risk-v1",weeks[0].selected.verified_at_utc,1,
        D("0.2"),D("0.001"),D("0.001"),D("0.001"),D("0.5"))
    return inputs,B1RiskPlan509(p,risk)


class B1Risk509Tests(unittest.TestCase):
    def test_regular_and_major_use_distinct_causal_reference(self):
        for early in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for major in (False,True):
                for strategy in Strategy:
                    inputs,p=fixture(early,major)
                    a,s=proof(inputs,p,MAJOR if major else early,strategy)
                    r=a[-1][1]
                    self.assertIs(r.state,S1State439.MATCH)
                    self.assertEqual(r.private_reference,D(22) if major else D(21))
                    self.assertEqual(r.private_target,D(40))
                    self.assertLess(r.private_stop,r.private_reference)
                    self.assertFalse(s["publication_allowed"])

    def test_cost_math(self):
        inputs,p=fixture()
        r=proof(inputs,p)[0][-1][1]
        self.assertEqual(r.private_net_reward,D(40)*D("0.998")-D(21)*D("1.001"))
        self.assertGreater(r.private_net_risk,D(21)-r.private_stop)

    def test_no_invented_target_or_threshold(self):
        inputs,p=fixture()
        for risk,state in ((replace(p.risk,weekly_high_index=5),S1State439.NONMATCH),
                           (replace(p.risk,candidate_min_net_rr=None),S1State439.DISTANCE),
                           (replace(p.risk,candidate_min_net_rr=D(10)),S1State439.NONMATCH)):
            self.assertIs(proof(inputs,replace(p,risk=risk))[0][-1][1].state,state)

    def test_late_policy_and_invalid_config(self):
        inputs,p=fixture()
        late=replace(p.risk,known_at_utc=inputs.as_of_utc+timedelta(seconds=1))
        self.assertIs(proof(inputs,replace(p,risk=late))[0][-1][1].state,S1State439.BLOCKED)
        for risk in (replace(p.risk,weekly_high_index=2),replace(p.risk,buy_fee_rate=D(1)),
                     replace(p.risk,candidate_stop_buffer_atr=D("-1"))):
            r,_=run(inputs,replace(p,risk=risk))
            self.assertIsNone(r.private_preview)

    def test_prior_gate(self):
        inputs,p=fixture()
        q=replace(p,prior=replace(p.prior,market=replace(p.prior.market,candidate_min_return=D(2))))
        self.assertIsNot(proof(inputs,q)[0][-1][1].state,S1State439.MATCH)

    def test_modes_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,mode=mode)
            self.assertIs(a[-1][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            self.assertNotIn("private_net_rr",json.dumps(s))
