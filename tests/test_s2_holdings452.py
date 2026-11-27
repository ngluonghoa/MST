"""§452 S2 hypothetical settled long holdings, not actual sell authorization."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_holdings445 import S1HoldingsPlan445
from swing_trading.s2_context448 import S2State448
from test_s2_context448 import run
from test_s2_confirm451 import fixture


def holdings(inputs,p,strategy):
    t=inputs.snapshots_for(p.rf.timeframe)[p.rf.target_index].selected
    return S1HoldingsPlan445(t.market_bar_key.instrument_id,strategy,"fixture-settled-v1",
                            t.verified_at_utc,60,100,70,20,50)


def with_holdings(p,h):
    return replace(p,rf=replace(p.rf,holdings=h))


class S2Holdings452Tests(unittest.TestCase):
    def test_exact_available_boundary_all_frames_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for strategy in Strategy:
                inputs,p=fixture(tf)
                row,safe=run(inputs,with_holdings(p,holdings(inputs,p,strategy)),strategy)
                result=row.private_preview.assessments[-1][1].holdings
                self.assertEqual((result.available_shares,result.requested_shares),(50,50))
                self.assertTrue(result.candidate_match)
                self.assertFalse(result.action_eligible)
                self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_no_short_or_unsettled_or_reserved_balance(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for changed in (replace(h,sell_shares=51),
                        replace(h,open_shares=0,settled_shares=0,reserved_shares=0),
                        replace(h,settled_shares=0,reserved_shares=0),
                        replace(h,reserved_shares=70)):
            row,safe=run(inputs,with_holdings(p,changed))
            self.assertIs(row.private_preview.assessments[-1][1].state,S2State448.NONMATCH)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_scope_clock_and_freshness(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for changed in (replace(h,instrument_id="other"),replace(h,strategy=Strategy.SWING),
                        replace(h,known_at_utc=h.known_at_utc+timedelta(seconds=1)),
                        replace(h,known_at_utc=h.known_at_utc-timedelta(seconds=61))):
            row,safe=run(inputs,with_holdings(p,changed))
            self.assertIs(row.private_preview.assessments[-1][1].state,S2State448.BLOCKED)
            self.assertIsNone(row.private_preview.assessments[-1][1].holdings)

    def test_explicit_counts_policy_and_timezone(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for bad in (replace(h,sell_shares=0),replace(h,sell_shares=True),
                    replace(h,settled_shares=101),replace(h,reserved_shares=71),
                    replace(h,policy_version=""),replace(h,max_age_seconds=0),
                    replace(h,known_at_utc=h.known_at_utc.replace(tzinfo=None))):
            _,safe=run(inputs,with_holdings(p,bad))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_no_prior_phase_promotion_and_optional_volume_not_required(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        row,_=run(inputs,with_holdings(replace(p,early=replace(p.early,candidate_k_rejection=None)),h))
        self.assertIs(row.private_preview.assessments[-1][1].state,S2State448.BLOCKED)
        self.assertIsNone(row.private_preview.assessments[-1][1].holdings)
        row,_=run(inputs,with_holdings(p,h))
        self.assertTrue(row.private_preview.assessments[-1][1].holdings.candidate_match)

    def test_legacy_private_and_no_sell_authority(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].holdings)
        row,safe=run(inputs,with_holdings(p,holdings(inputs,p,Strategy.SHORT)))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("available_shares","requested_shares","fixture-settled-v1",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
