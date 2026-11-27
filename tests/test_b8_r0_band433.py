"""§433 explicit R0 raw price-band witness, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_price_band426 import B8PriceBand426
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b8_rf418 import fixture
from test_b8_base415 import run


def bind(inputs,p,**kw):
    row=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    k=row.market_bar_key
    band=B8PriceBand426(k.instrument_id,k.exchange,k.calendar_version,k.session_period_id,
                       "fixture-r0-band",k.bar_start_utc,D(1),D(30),D(1))
    return replace(p,r0_band=replace(band,**kw))


class B8R0Band433Tests(unittest.TestCase):
    def test_both_base_frames_strategies_variants(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                    inputs,p=fixture(base_tf=tf)
                    row,safe=run(inputs,bind(inputs,p),strategy=strategy,variant=variant)
                    proof=row.private_preview.assessments[0][1]
                    self.assertEqual(proof.band.state,"COMPUTED_UNCALIBRATED")
                    self.assertIsNone(proof.band.grid_entry_ceiling)
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wrong_scope_blocks_base_and_later_phases(self):
        inputs,p=fixture()
        for kw in ({"instrument_id":"other"},{"session_period_id":"other"},{"calendar_version":"other"}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_late_policy_and_ohlc(self):
        inputs,p=fixture()
        row=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
        for kw in ({"known_at_utc":row.market_bar_key.bar_start_utc+timedelta(seconds=1)},
                   {"upper":D(9)},{"lower":D(3),"tick":D(3)}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_explicit_invalid(self):
        inputs,p=fixture()
        for kw in ({"tick":D(0)},{"policy_version":""},{"lower":D(31)}):
            _,safe=run(inputs,bind(inputs,p,**kw))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_and_distinct_rf_scope(self):
        inputs,p=fixture()
        row,_=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[0][1].band)
        row,_=run(inputs,bind(inputs,p))
        self.assertIsNotNone(row.private_preview.assessments[0][1].band)
        self.assertIsNone(row.private_preview.assessments[-1][1].band)

    def test_redaction_no_authority(self):
        inputs,p=fixture()
        row,safe=run(inputs,bind(inputs,p))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("fixture-r0-band","grid_entry_ceiling",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
