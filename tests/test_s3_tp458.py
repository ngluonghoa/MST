"""§458 fictional TP plan context, never user holdings or approval."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3State454
from swing_trading.s3_tp458 import S3TPPlan458,S3TargetScenario458
from test_s3_near455 import setup
from test_s3_context454 import run
from test_s2_rally449 import alter
from test_causal_indicators import snap

VARIANT="S3/E_TP"


def fixture(strategy=Strategy.SHORT,*,close=D(20),k=D(0)):
    inputs,p=setup(close=close,k=k)
    a=inputs.snapshots_for(Timeframe.M15)[0].selected
    target=S3TargetScenario458(inputs.instrument_id,strategy,"fictional-plan-458","v1",
        a.market_bar_key.bar_start_utc-timedelta(hours=1),
        a.market_bar_key.bar_start_utc+timedelta(days=1),D(20))
    return inputs,S3TPPlan458(p.anchor_index,p.d1,target,p.near)


class S3TP458Tests(unittest.TestCase):
    def test_both_explicit_tp_variants_strategies(self):
        for strategy in Strategy:
            for variant in ("S3/E_TP","S3/F_TP"):
                inputs,p=fixture(strategy)
                row,safe=run(inputs,p,strategy,variant)
                self.assertTrue(all(g.state is S3State454.MATCH for _,g in row.private_preview.assessments))
                self.assertEqual(row.private_preview.assessments[1][1].private_target,D(20))
                self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
                self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")

    def test_posthoc_scope_expiry(self):
        inputs,p=fixture()
        a=inputs.snapshots_for(Timeframe.M15)[0].selected
        for changed in (replace(p.target,known_at_utc=a.market_bar_key.bar_start_utc+timedelta(seconds=1)),
                        replace(p.target,instrument_id="other-instrument"),
                        replace(p.target,strategy=Strategy.SWING),
                        replace(p.target,expires_at_utc=a.verified_at_utc-timedelta(seconds=1))):
            row,_=run(inputs,replace(p,target=changed),variant=VARIANT)
            self.assertIs(row.private_preview.assessments[0][1].state,S3State454.BLOCKED)
        row,_=run(inputs,replace(p,target=replace(p.target,expires_at_utc=a.verified_at_utc)),variant=VARIANT)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.BLOCKED)

    def test_far_over_target_or_unset(self):
        for close,k,state in ((D(19),D(0),S3State454.NONMATCH),(D(21),D(1),S3State454.NONMATCH),
                              (D(20),None,S3State454.DISTANCE)):
            inputs,p=fixture(close=close,k=k)
            row,_=run(inputs,p,variant=VARIANT)
            self.assertIs(row.private_preview.assessments[1][1].state,state)

    def test_missing_and_late_context(self):
        inputs,p=fixture()
        row,_=run(alter(inputs,Timeframe.D1,()),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[0][1].state,S3State454.MISSING)
        rows=inputs.snapshots_for(Timeframe.M15)
        late=snap(replace(rows[0].selected,verified_at_utc=rows[1].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        row,_=run(alter(inputs,Timeframe.M15,(late,rows[1])),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[1][1].state,S3State454.BLOCKED)

    def test_wrong_branch_and_invalid_plan(self):
        inputs,p=fixture()
        for variant in ("S3/E_MICRO_CHOCH","S3/F_MICRO_BREAK"):
            _,safe=run(inputs,p,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        for changed in (replace(p.target,plan_id=""),replace(p.target,target_price=True),
                        replace(p.target,target_price=D("NaN"))):
            _,safe=run(inputs,replace(p,target=changed),variant=VARIANT)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_determinism_no_authority(self):
        inputs,p=fixture()
        a,sa=run(inputs,p,variant=VARIANT)
        b,sb=run(inputs,p,variant=VARIANT)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        for secret in ("fictional-plan-458","private_target","target_price",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        old,_=run(inputs,replace(p,near=None),variant=VARIANT)
        self.assertEqual(len(old.private_preview.assessments),1)
