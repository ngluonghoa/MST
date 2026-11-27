"""§447 full strict S1 candidate matrix, fictional only."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_s1_context439 import run,fixture as context_fixture
from test_s1_rf_volume444 import fixture as rf_fixture,FAILED,CHOCH
from test_s1_holdings445 import holdings
from test_s1_major446 import fixture as major_fixture,MAJOR


def full(tf=Timeframe.M15,context=Timeframe.D1,strategy=Strategy.SHORT,early=FAILED,major=False):
    inputs,p=(major_fixture(tf,context,early) if major else rf_fixture(tf,context,early))
    h=holdings(inputs,p,strategy)
    p=replace(p,rf=replace(p.rf,holdings=h),strict_candidate_evidence=True)
    if major:
        w=inputs.snapshots_for(Timeframe.W1)[p.major.target_index].selected
        p=replace(p,major=replace(p.major,holdings=replace(h,known_at_utc=w.verified_at_utc)))
    return inputs,p


class S1Strict447Tests(unittest.TestCase):
    def test_full_matrix_32_paths(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    for early in (FAILED,CHOCH):
                        for major in (False,True):
                            inputs,p=full(tf,context,strategy,early,major)
                            row,safe=run(inputs,p,strategy,MAJOR if major else early)
                            proofs=[g for _,g in row.private_preview.assessments]
                            self.assertEqual([g.candidate_evidence_complete for g in proofs],[True]*4,
                                             [(g.state,g.reason,g.mandatory_gaps) for g in proofs])
                            self.assertEqual([x["ingredient_state"] for x in safe["phases"]],["GEOMETRY_MATCH_ONLY"]*4)
                            self.assertEqual(proofs[-1].holdings.available_shares,50)
                            if major:
                                self.assertTrue(proofs[-1].major.weekly_holdings.candidate_match)

    def test_strict_missing_explicit_phase(self):
        inputs,p=context_fixture()
        row,safe=run(inputs,replace(p,strict_candidate_evidence=True))
        self.assertEqual([g.candidate_evidence_complete for _,g in row.private_preview.assessments],
                         [True,False,False,False])
        self.assertEqual([x["ingredient_state"] for x in safe["phases"]],
                         ["GEOMETRY_MATCH_ONLY","MISSING_INPUT","MISSING_INPUT","MISSING_INPUT"])

    def test_strict_rf_missing_volume_and_holdings(self):
        inputs,p=full()
        for rf in (replace(p.rf,holdings=None),replace(p.rf,volume=None,holdings=None)):
            row,safe=run(inputs,replace(p,rf=rf))
            g=row.private_preview.assessments[-1][1]
            self.assertFalse(g.candidate_evidence_complete)
            self.assertIn("RF_SETTLED_HOLDINGS_SCENARIO",g.mandatory_gaps)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_major_requires_separate_weekly_holdings(self):
        inputs,p=full(major=True)
        row,safe=run(inputs,replace(p,major=replace(p.major,holdings=None)),variant=MAJOR)
        self.assertIn("RF_W1_SETTLED_HOLDINGS_SCENARIO",row.private_preview.assessments[-1][1].mandatory_gaps)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        for h in (p.rf.holdings,replace(p.major.holdings,sell_shares=51),
                  replace(p.major.holdings,known_at_utc=p.major.holdings.known_at_utc+timedelta(seconds=1))):
            row,safe=run(inputs,replace(p,major=replace(p.major,holdings=h)),variant=MAJOR)
            self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)
            self.assertIn(safe["phases"][3]["ingredient_state"],("BLOCKED","GEOMETRY_NONMATCH_ONLY"))

    def test_prior_nonmatch_and_strict_flag_validation(self):
        inputs,p=full()
        row,safe=run(inputs,replace(p,candidate_min_span_bars=100))
        self.assertTrue(all(not g.candidate_evidence_complete for _,g in row.private_preview.assessments))
        _,safe=run(inputs,replace(p,strict_candidate_evidence=1))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_determinism_redaction_and_legacy(self):
        inputs,p=full(major=True)
        a,sa=run(inputs,p,variant=MAJOR)
        b,sb=run(inputs,p,variant=MAJOR)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("candidate_evidence_complete","mandatory_gaps","weekly_holdings","requested_shares",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        row,safe=run(inputs,replace(p,strict_candidate_evidence=False,major=replace(p.major,holdings=None)),variant=MAJOR)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertFalse(row.private_preview.assessments[-1][1].candidate_evidence_complete)
