"""§429 fictional same-size risk budget regression."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_portfolio429 import B8PortfolioPlan429
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run
from test_b8_entry_cap425 import combined
from test_b8_liquidity428 import bind as liquid


def bind(inputs,p,strategy=Strategy.SHORT,**kw):
    target=inputs.snapshots_for(p.rf.timeframe)[p.rf.breakout_index].selected
    plan=B8PortfolioPlan429(target.market_bar_key.instrument_id,strategy,target.verified_at_utc,
        60,"fixture-currency-v1",D(1),D(10000),D(170),D(50),D(".01"),D(".015"))
    return replace(p,rf=replace(p.rf,portfolio=replace(plan,**kw)))


def model(strategy=Strategy.SHORT,tf=Timeframe.H1,**kw):
    inputs,p=fixture(tf=tf)
    inputs,p=liquid(inputs,combined(p),strategy)
    return inputs,bind(inputs,p,strategy,**kw)


class B8Portfolio429Tests(unittest.TestCase):
    def test_both_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=model(strategy,tf)
                    row,safe=run(inputs,p,strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[-1][1].portfolio
                    self.assertEqual((proof.cash_required,proof.added_risk,proof.total_risk),
                                     (D(170),D(100),D(150)))
                    self.assertTrue(proof.candidate_match)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_independent_budget_nonmatch(self):
        for kw in ({"available_cash":D(169)},{"candidate_trade_risk_fraction":D(".009")},
                   {"reserved_risk":D(51)}):
            inputs,p=model(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_risk_and_liquidity(self):
        inputs,p=model()
        for kw in ({"risk":None},{"liquidity":None}):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,**kw)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_scope_and_time(self):
        inputs,p=model()
        plan=p.rf.portfolio
        for changed in (replace(plan,instrument_id="other"),replace(plan,strategy=Strategy.SWING),
                        replace(plan,known_at_utc=plan.known_at_utc-timedelta(seconds=61)),
                        replace(plan,known_at_utc=plan.known_at_utc+timedelta(seconds=1))):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,portfolio=changed)))
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_units_and_validation(self):
        inputs,p=model(price_unit_multiplier=D(1000))
        row,safe=run(inputs,p)
        self.assertEqual(row.private_preview.assessments[-1][1].portfolio.cash_required,D(170000))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")
        for kw in ({"equity":D(0)},{"currency_policy":""},{"candidate_trade_risk_fraction":D(2)}):
            inputs,p=model(**kw)
            _,safe=run(inputs,p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_redaction(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[-1][1].portfolio)
        inputs,p=model()
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("cash_required","added_risk","fixture-currency-v1",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
