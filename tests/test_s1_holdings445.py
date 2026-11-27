"""§445 fictional holdings, settlement and strategy boundaries."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_holdings445 import S1HoldingsPlan445
from test_s1_rf_volume444 import fixture,FAILED,CHOCH
from test_s1_context439 import run


def holdings(inputs,p,strategy):
    t=inputs.snapshots_for(Timeframe.D1)[p.rf.target_index].selected
    return S1HoldingsPlan445(t.market_bar_key.instrument_id,strategy,"fixture-settled-v1",
                            t.verified_at_utc,60,100,70,20,50)


def with_holdings(p,h):
    return replace(p,rf=replace(p.rf,holdings=h))


class S1Holdings445Tests(unittest.TestCase):
    def test_exact_available_boundary_all_branches(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for context in (Timeframe.W1,Timeframe.D1):
                for strategy in Strategy:
                    for variant in (FAILED,CHOCH):
                        inputs,p=fixture(tf,context,variant)
                        row,safe=run(inputs,with_holdings(p,holdings(inputs,p,strategy)),strategy,variant)
                        result=row.private_preview.assessments[-1][1].holdings
                        self.assertEqual((result.available_shares,result.requested_shares),(50,50))
                        self.assertTrue(result.candidate_match)
                        self.assertFalse(result.action_eligible)
                        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_no_open_or_settled_or_unreserved_balance(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for changed in (replace(h,sell_shares=51),replace(h,open_shares=0,settled_shares=0,reserved_shares=0),
                        replace(h,settled_shares=0,reserved_shares=0),replace(h,reserved_shares=70)):
            _,safe=run(inputs,with_holdings(p,changed))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_wrong_scope_or_future_or_stale(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for changed in (replace(h,instrument_id="other"),replace(h,strategy=Strategy.SWING),
                        replace(h,known_at_utc=h.known_at_utc+timedelta(seconds=1)),
                        replace(h,known_at_utc=h.known_at_utc-timedelta(seconds=61))):
            _,safe=run(inputs,with_holdings(p,changed))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_validated_counts_and_policy(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        for changed in (replace(h,sell_shares=0),replace(h,sell_shares=True),
                        replace(h,settled_shares=101),replace(h,reserved_shares=71),
                        replace(h,policy_version=""),replace(h,max_age_seconds=0),
                        replace(h,known_at_utc=h.known_at_utc.replace(tzinfo=None))):
            _,safe=run(inputs,with_holdings(p,changed))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_missing_volume_or_nonmatch_never_promoted(self):
        inputs,p=fixture()
        h=holdings(inputs,p,Strategy.SHORT)
        row,safe=run(inputs,with_holdings(replace(p,rf=replace(p.rf,volume=None)),h))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        self.assertIsNone(row.private_preview.assessments[-1][1].holdings)
        inputs,p=fixture(volume=214)
        row,safe=run(inputs,with_holdings(p,holdings(inputs,p,Strategy.SHORT)))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertIsNone(row.private_preview.assessments[-1][1].holdings)

    def test_legacy_redaction_and_no_sell_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].holdings)
        row,safe=run(inputs,with_holdings(p,holdings(inputs,p,Strategy.SHORT)))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("available_shares","requested_shares","fixture-settled-v1",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
