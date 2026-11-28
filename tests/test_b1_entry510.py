"""§510 fictional entry cap; no execution or publication authority."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b1_entry510 import B1EntryPlan510,B1EntryTerms510
from swing_trading.contracts import Strategy
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.unified_mode459 import EngineMode
from test_b1_risk509 import fixture as risk_fixture
from test_b1_major508 import MAJOR
from test_b1_market506 import proof
from test_b1_decline499 import run


def fixture(early="B1/E_RECLAIM",major=False):
    inputs,p=risk_fixture(early,major)
    return inputs,B1EntryPlan510(p,B1EntryTerms510("fictional-entry-v1",p.risk.known_at_utc,D(10)))


class B1Entry510Tests(unittest.TestCase):
    def test_all_variants_and_strategies(self):
        for early in ("B1/E_RECLAIM","B1/E_BOS_UP"):
            for major in (False,True):
                for strategy in Strategy:
                    inputs,p=fixture(early,major)
                    a,s=proof(inputs,p,MAJOR if major else early,strategy)
                    r=a[-1][1]
                    self.assertIs(r.state,S1State439.MATCH)
                    self.assertEqual(r.private_prior.private_reference,D(22) if major else D(21))
                    self.assertFalse(s["publication_allowed"])

    def test_minimum_of_caps(self):
        inputs,p=fixture()
        r=proof(inputs,p)[0][-1][1]
        self.assertEqual(r.private_max_entry,min(r.private_no_chase_cap,r.private_rr_cap))
        self.assertLessEqual(r.private_max_entry,r.private_prior.private_target)

    def test_no_chase_and_missing(self):
        inputs,p=fixture()
        for k,state in ((D(0),S1State439.NONMATCH),(None,S1State439.DISTANCE)):
            r=proof(inputs,replace(p,entry=replace(p.entry,candidate_max_extension_atr=k)))[0][-1][1]
            self.assertIs(r.state,state)

    def test_late_and_invalid(self):
        inputs,p=fixture()
        late=replace(p.entry,known_at_utc=inputs.as_of_utc+timedelta(seconds=1))
        self.assertIs(proof(inputs,replace(p,entry=late))[0][-1][1].state,S1State439.BLOCKED)
        r,_=run(inputs,replace(p,entry=replace(p.entry,candidate_max_extension_atr=D(-1))))
        self.assertIsNone(r.private_preview)

    def test_prior_gate(self):
        inputs,p=fixture()
        q=replace(p,prior=replace(p.prior,risk=replace(p.prior.risk,candidate_min_net_rr=D(10))))
        self.assertIsNot(proof(inputs,q)[0][-1][1].state,S1State439.MATCH)

    def test_modes_and_redaction(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            a,s=proof(inputs,p,mode=mode)
            self.assertIs(a[-1][1].state,S1State439.MATCH)
            self.assertFalse(s["production_qualified"])
            self.assertNotIn("private_max_entry",json.dumps(s))
