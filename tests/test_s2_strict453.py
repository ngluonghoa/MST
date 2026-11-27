"""§453 cumulative S2 strict candidate matrix, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s2_context448 import S2State448
from test_causal_indicators import make_bar,snap
from test_s2_context448 import fixture as context_fixture,run
from test_s2_confirm451 import fixture
from test_s2_holdings452 import holdings,with_holdings
from test_s2_rally449 import alter


def full(tf=Timeframe.M15,strategy=Strategy.SHORT):
    inputs,p=fixture(tf)
    p=with_holdings(p,holdings(inputs,p,strategy))
    return inputs,replace(p,strict_candidate_evidence=True)


class S2Strict453Tests(unittest.TestCase):
    def test_full_matrix_four_paths(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for strategy in Strategy:
                inputs,p=full(tf,strategy)
                row,safe=run(inputs,p,strategy)
                proofs=[g for _,g in row.private_preview.assessments]
                self.assertEqual([g.candidate_evidence_complete for g in proofs],[True]*4,
                                 [(g.state,g.reason,g.mandatory_gaps) for g in proofs])
                self.assertEqual([x["ingredient_state"] for x in safe["phases"]],["GEOMETRY_MATCH_ONLY"]*4)
                self.assertEqual(proofs[-1].holdings.available_shares,50)

    def test_missing_plans_and_holdings(self):
        inputs,p=context_fixture()
        row,safe=run(inputs,replace(p,strict_candidate_evidence=True))
        self.assertEqual([g.candidate_evidence_complete for _,g in row.private_preview.assessments],
                         [True,False,False,False])
        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                         ["GEOMETRY_MATCH_ONLY","MISSING_INPUT","MISSING_INPUT","MISSING_INPUT"])
        inputs,p=full()
        row,safe=run(inputs,with_holdings(p,None))
        g=row.private_preview.assessments[-1][1]
        self.assertEqual(g.mandatory_gaps,("RF_SETTLED_HOLDINGS_SCENARIO",))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_intervening_m15_reclaim_rejects_h1_rf(self):
        inputs,p=full(Timeframe.H1)
        rows=inputs.snapshots_for(Timeframe.M15)
        start=rows[-1].selected.verified_at_utc+timedelta(minutes=20)
        added=snap(make_bar(2800,timeframe=Timeframe.M15,start=start,high=D(15),close=D(15)))
        inputs=alter(inputs,Timeframe.M15,rows+(added,))
        row,safe=run(inputs,p)
        g=row.private_preview.assessments[-1][1]
        self.assertIs(g.state,S2State448.NONMATCH)
        self.assertFalse(g.candidate_evidence_complete)
        old,_=run(inputs,replace(p,strict_candidate_evidence=False))
        self.assertIs(old.private_preview.assessments[-1][1].state,S2State448.MATCH)

    def test_intervening_m15_late_observation_blocks_h1_rf(self):
        inputs,p=full(Timeframe.H1)
        rows=inputs.snapshots_for(Timeframe.M15)
        start=rows[-1].selected.verified_at_utc+timedelta(minutes=20)
        target=inputs.snapshots_for(Timeframe.H1)[p.rf.target_index].selected
        added=snap(make_bar(2801,timeframe=Timeframe.M15,start=start,
                           verified=target.market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,Timeframe.M15,rows+(added,)),p)
        self.assertIs(row.private_preview.assessments[-1][1].state,S2State448.BLOCKED)

    def test_prior_nonmatch_and_invalid_strict_flag(self):
        inputs,p=full()
        row,_=run(inputs,replace(p,rally=replace(p.rally,candidate_k_near=D(0))))
        self.assertEqual([g.candidate_evidence_complete for _,g in row.private_preview.assessments],
                         [True,False,False,False])
        _,safe=run(inputs,replace(p,strict_candidate_evidence=1))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_determinism_legacy_no_authority(self):
        inputs,p=full()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("candidate_evidence_complete","mandatory_gaps","requested_shares",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        row,safe=run(inputs,replace(with_holdings(p,None),strict_candidate_evidence=False))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)
