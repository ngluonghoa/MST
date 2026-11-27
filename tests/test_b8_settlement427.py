"""§427 hypothetical settlement timing, fictional."""
from dataclasses import replace
from datetime import timedelta
from zoneinfo import ZoneInfo
import json
import unittest

from swing_trading.b8_settlement427 import B8SettlementPlan427
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.session_calendar import TradingSession, SessionType
from test_b8_rf418 import fixture
from test_b8_base415 import run


def bind(inputs,p,strategy=Strategy.SHORT,**kwargs):
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    key=target.market_bar_key
    entry=target.verified_at_utc+timedelta(days=1)
    release=entry+timedelta(days=4)
    def session(t,id):
        return TradingSession(key.exchange,t.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date(),
            id,SessionType.CONTINUOUS,t,t+timedelta(hours=1),key.calendar_version,
            "fixture-rule","fixture-source",True)
    plan=B8SettlementPlan427(key.instrument_id,strategy,"fixture-policy",target.verified_at_utc,
        session(entry,"entry"),session(release,"release"),entry,release,release)
    return replace(p,rf=replace(p.rf,settlement=replace(plan,**kwargs)))


class B8Settlement427Tests(unittest.TestCase):
    def test_both_strategies_frames_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(tf=tf)
                    row,safe=run(inputs,bind(inputs,p,strategy),strategy=strategy,variant=variant)
                    self.assertTrue(row.private_preview.assessments[-1][1].settlement.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_required_exit_before_release(self):
        inputs,p=fixture()
        p=bind(inputs,p)
        plan=p.rf.settlement
        p=replace(p,rf=replace(p.rf,settlement=replace(plan,
                         required_exit_from_utc=plan.hypothetical_entry_utc+timedelta(hours=1))))
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.assessments[-1][1].settlement.candidate_match)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_wrong_scope_and_late_policy(self):
        inputs,p=fixture()
        for kwargs in ({"instrument_id":"other"},{"strategy":Strategy.SWING},
                       {"known_at_utc":inputs.as_of_utc}):
            _,safe=run(inputs,bind(inputs,p,**kwargs))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_session_missing_verification_or_wrong_interval(self):
        inputs,p=fixture()
        p=bind(inputs,p)
        plan=p.rf.settlement
        for session in (replace(plan.release_session,verified=False),
                        replace(plan.release_session,calendar_version="other"),
                        replace(plan.release_session,session_type=SessionType.AUCTION)):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,settlement=replace(plan,release_session=session))))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_invalid_and_legacy(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].settlement)
        for kwargs in ({"policy_version":""},{"strategy":"SHORT"}):
            _,safe=run(inputs,bind(inputs,p,**kwargs))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_no_authority_or_private_leakage(self):
        inputs,p=fixture()
        row,safe=run(inputs,bind(inputs,p))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fixture-policy","externally_supplied_release_utc",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
