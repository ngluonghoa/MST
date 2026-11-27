"""§464 distinct closed TP confirmation, fictional inputs only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3State454
from swing_trading.s3_tp_event463 import S3TPEvent463,S3TPConfirmPlan464
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s3_tp_event463 import setup as event_setup
from test_s3_context454 import run
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def setup(strategy=Strategy.SHORT,close=D(20)):
    inputs,p=event_setup(strategy)
    rows=inputs.snapshots_for(Timeframe.M15)
    target=snap(make_bar(3600,timeframe=Timeframe.M15,
        start=rows[-1].market_bar_key.bar_start_utc+timedelta(minutes=20),
        high=max(D(21),close),low=D(8),close=close))
    b=target.selected
    rf=S3TPEvent463(len(rows),p.early.plan_id,p.early.plan_version,
        b.source_event_ids[0],b.observation_revision.source_revision_or_payload_digest,
        b.market_bar_key.bar_start_utc,b.verified_at_utc,p.early.d1)
    plan=S3TPConfirmPlan464(p,rf,p.early.source_event_id,p.early.revision_digest,p.early.bar_start_utc)
    return alter(inputs,Timeframe.M15,rows+(target,)),plan


def confirm(inputs,p,strategy=Strategy.SHORT):
    r,s=run(inputs,p,strategy,"S3/F_TP")
    return r.private_preview.assessments[3][1],s


class S3TPConfirm464Tests(unittest.TestCase):
    def test_distinct_closed_confirm_both_strategies(self):
        for strategy in Strategy:
            for close in (D(20),D(21)):
                inputs,p=setup(strategy,close)
                g,s=confirm(inputs,p,strategy)
                self.assertIs(g.state,S3State454.MATCH)
                self.assertEqual(s["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_only_and_missing(self):
        inputs,p=setup(close=D(19))
        self.assertIs(confirm(inputs,p)[0].state,S3State454.NONMATCH)
        rows=inputs.snapshots_for(Timeframe.M15)
        self.assertIs(confirm(alter(inputs,Timeframe.M15,rows[:-1]),p)[0].state,S3State454.MISSING)

    def test_exact_prior_link_and_confirm_identity(self):
        inputs,p=setup()
        for changed in (replace(p,linked_early_event_id="wrong"),
                        replace(p,linked_early_revision_digest="wrong"),
                        replace(p,linked_early_start_utc=p.linked_early_start_utc+timedelta(seconds=1)),
                        replace(p,confirmation=replace(p.confirmation,revision_digest="wrong")),
                        replace(p,confirmation=replace(p.confirmation,plan_version="wrong")),
                        replace(p,confirmation=replace(p.confirmation,source_event_id=p.event.early.source_event_id))):
            self.assertIs(confirm(inputs,changed)[0].state,S3State454.BLOCKED)

    def test_no_backdated_confirmation_or_unmatched_early(self):
        inputs,p=setup()
        late=replace(p.event.early,event_known_at_utc=p.confirmation.bar_start_utc+timedelta(seconds=1))
        self.assertIs(confirm(inputs,replace(p,event=replace(p.event,early=late)))[0].state,S3State454.BLOCKED)
        wrong=replace(p.event.early,revision_digest="wrong")
        self.assertIs(confirm(inputs,replace(p,event=replace(p.event,early=wrong)))[0].state,S3State454.BLOCKED)
        for changed,variant in ((replace(p,confirmation=p.event.early),"S3/F_TP"),(p,"S3/E_TP")):
            _,s=run(inputs,changed,variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_no_late_confirmation_event_or_expired_plan(self):
        inputs,p=setup()
        late=replace(p.confirmation,event_known_at_utc=inputs.as_of_utc+timedelta(seconds=1))
        self.assertIs(confirm(inputs,replace(p,confirmation=late))[0].state,S3State454.BLOCKED)
        target=replace(p.event.context.target,expires_at_utc=p.confirmation.bar_start_utc)
        context=replace(p.event.context,target=target)
        self.assertIs(confirm(inputs,replace(p,event=replace(p.event,context=context)))[0].state,S3State454.BLOCKED)

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=setup()
        candidate=profile((request("S3",p,variant="S3/F_TP"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            result=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(result.private_preview,"S3").private_preview.assessments[3][1].state,S3State454.MATCH)
            s=result.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for private in (p.linked_early_event_id,p.confirmation.source_event_id,
                            p.confirmation.revision_digest,p.confirmation.plan_id,"private_target_close"):
                self.assertNotIn(private,json.dumps(s))
        old,s=run(inputs,p.event,variant="S3/F_TP")
        self.assertEqual(len(old.private_preview.assessments),3)
        self.assertEqual(s["phases"][3]["ingredient_state"],"NOT_REQUESTED")
