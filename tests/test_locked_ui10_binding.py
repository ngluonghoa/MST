"""UI-1.0 locked A-I diagnostic binding regression, fabricated bars only."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import unittest

from swing_trading.contracts import DecisionStatus, SignalDecision, Strategy, ZONE_IDS
from swing_trading.locked_ui10_binding import (
    LockedUi10Denied, LockedUi10DiagnosticViewModel,
    SECTION_IDS, ZONE_LEGEND, PIPELINE_STEPS, AUDIT_TOPICS, UI_VERSION,
    build_private_d1_ui10_diagnostic,
)
from swing_trading.private_cache_source_bridge import (
    diagnose_private_d1_without_signals,
)
from test_private_cache_source_bridge import source, NOW


def views(provider="SSI"):
    doc=source(provider)
    return (
        diagnose_private_d1_without_signals(doc,strategy=Strategy.SHORT,as_of_utc=NOW),
        diagnose_private_d1_without_signals(doc,strategy=Strategy.SWING,as_of_utc=NOW),
    )


def build(provider="SSI",**kwargs):
    short,swing=views(provider)
    return build_private_d1_ui10_diagnostic(short,swing,
        run_id="mst-diagnostic-187",exchange="HOSE",**kwargs)


class LockedUi10BindingTests(unittest.TestCase):
    def test_all_provider_shapes_give_locked_incomplete_not_no_signal(self):
        for provider in ("SSI","DNSE","VCBS"):
            with self.subTest(provider=provider):
                result=build(provider)
                m=result.data
                self.assertEqual(m["ui_version"],"UI-1.0")
                self.assertEqual(m["section_ids"],list("ABCDEFGHI"))
                self.assertEqual(tuple(m["sections"]),tuple("ABCDEFGHI"))
                self.assertEqual(m["publication_state"],"INCOMPLETE_REPORT")
                self.assertFalse(m["report_published"])
                self.assertFalse(m["step08_atomic_commit_verified"])
                self.assertFalse(m["action_eligible"])
                self.assertFalse(result.all_source_rules_verified)
                self.assertFalse(result.user_trade_eligible)
                self.assertFalse(result.report_published)
                self.assertEqual(m["zone_evaluated_count"],16)
                self.assertEqual(m["zone_verified_count"],0)
                self.assertEqual(m["pipeline_verified_count"],0)
                self.assertEqual(len(m["zone_rows"]),16)
                self.assertEqual(len(m["pipeline_steps"]),8)
                self.assertEqual(len(m["audit_topics"]),8)
                self.assertEqual([z["zone_id"] for z in m["zone_rows"]],
                                 list(ZONE_IDS))
                self.assertEqual([x["locked_legend"] for x in m["zone_rows"]],
                                 [n for _,n in ZONE_LEGEND])
                self.assertEqual([x["step_name"] for x in m["pipeline_steps"]],
                                 list(PIPELINE_STEPS))
                self.assertEqual([x["topic"] for x in m["audit_topics"]],
                                 list(AUDIT_TOPICS))
                self.assertEqual([s["step_id"] for s in m["pipeline_steps"]],
                                 list(range(1,9)))
                self.assertEqual([s["audit_id"] for s in m["audit_topics"]],
                                 list(range(1,9)))
                self.assertEqual({k for k in m["strategies"]},
                                 {"SHORT","SWING"})
                for branch in m["strategies"].values():
                    self.assertEqual(branch["state"],"BLOCKED")
                    self.assertEqual(branch["decision"],"NO_TRADE")
                    self.assertIsNone(branch["entry"])
                    self.assertIsNone(branch["stop_loss"])
                    self.assertIsNone(branch["take_profit_1"])
                    self.assertIsNone(branch["take_profit_2"])
                    self.assertIsNone(branch["risk_reward"])
                    self.assertIsNone(branch["primary_zone"])
                    self.assertFalse(branch["confirmed"])
                self.assertTrue(all(x["status"]=="UNVERIFIED"
                                    for x in m["zone_rows"]))
                self.assertTrue(all(x["status"]!="COMPLETE"
                                    for x in m["pipeline_steps"]))
                self.assertEqual(m["pipeline_steps"][0]["status"],"BLOCKED")
                self.assertEqual(m["pipeline_steps"][1]["status"],"BLOCKED")
                self.assertEqual(m["pipeline_steps"][7]["status"],"NOT_STARTED")
                self.assertTrue(all(x["status"]=="WARN" and x["hard_fail"]
                                    for x in m["audit_topics"]))
                self.assertEqual(m["position_context_status"],"NOT_PROVIDED")
                self.assertIsNone(m["step04_result"])
                self.assertEqual(m["position_context_wording"],
                                 "Không có vị thế được cung cấp")
                self.assertFalse(m["cache_metrics_measured"])
                self.assertIsNone(m["cache_hit_rate"])
                self.assertFalse(m["rendered_ui"])
                self.assertEqual(m["trading_or_broker_calls"],0)
                self.assertNotIn("NO_SIGNAL",json.dumps(m))

    def test_invariant_digest_is_deterministic_and_read_only(self):
        a=build("VCBS")
        b=build("VCBS")
        self.assertEqual(a.reference_sha256,b.reference_sha256)
        self.assertRegex(a.reference_sha256,r"^[0-9a-f]{64}$")
        self.assertEqual(a.data,b.data)
        self.assertNotIn("native_source_data",a.data)
        self.assertNotIn("market_credentials",a.data)
        self.assertNotIn("source_close_price",a.data)
        self.assertEqual(a.data["source_rows_observed"],2)

    def test_source_mismatch_between_strategies_refused(self):
        a,_=views("SSI")
        _,b=views("DNSE")
        with self.assertRaisesRegex(LockedUi10Denied,"CROSS_SOURCE"):
            build_private_d1_ui10_diagnostic(a,b,
                run_id="test187",exchange="HOSE")
        a,_=views("SSI")
        _,b=views("SSI")
        b=replace(b,as_of_utc=NOW.replace(hour=5))
        with self.assertRaisesRegex(LockedUi10Denied,"CROSS_SOURCE"):
            build_private_d1_ui10_diagnostic(a,b,
                run_id="test187",exchange="HOSE")
        a,_=views("SSI")
        partial=source("SSI")
        partial["native_source_data"]=partial["native_source_data"][:1]
        partial["source_rows_observed"]=1
        b=diagnose_private_d1_without_signals(
            partial,strategy=Strategy.SWING,as_of_utc=NOW)
        with self.assertRaisesRegex(LockedUi10Denied,"CROSS_SOURCE"):
            build_private_d1_ui10_diagnostic(a,b,
                run_id="test187",exchange="HOSE")

    def test_missing_duplicated_zone_wrong_strategy_or_false_detection_blocked(self):
        short,swing=views("SSI")
        for bad in (
            replace(short,decisions=short.decisions[:15]),
            replace(short,decisions=(short.decisions[0],)*16),
            replace(short,decisions=tuple(reversed(short.decisions))),
        ):
            with self.subTest(count=len(bad.decisions)),self.assertRaises(
                LockedUi10Denied
            ):
                build_private_d1_ui10_diagnostic(bad,swing,
                    run_id="test187",exchange="HOSE")
        with self.assertRaises(LockedUi10Denied):
            build_private_d1_ui10_diagnostic(swing,short,
                run_id="test187",exchange="HOSE")

    def test_detected_with_fabricated_verified_evidence_is_still_denied(self):
        from swing_trading.contracts import Evidence
        short,swing=views("SSI")
        claimed=SignalDecision("B1",Strategy.SHORT,DecisionStatus.DETECTED,
            (Evidence("fictional-rule",NOW,True),))
        forged=replace(short,decisions=(claimed,)+short.decisions[1:])
        with self.assertRaisesRegex(LockedUi10Denied,"16_ZONE"):
            build_private_d1_ui10_diagnostic(forged,swing,
                run_id="test187",exchange="HOSE")

    def test_unverified_view_cannot_flip_to_full_analysis_or_action(self):
        r=build()
        for key,value in (
            ("publication_state","FULL_ANALYSIS"),
            ("ui_version","UI-1.1"),
            ("report_published",True),
            ("action_eligible",True),
        ):
            doc=deepcopy(r.data)
            doc[key]=value
            digest=sha256(json.dumps(doc,sort_keys=True,separators=(",",":"),
                                ensure_ascii=False,allow_nan=False
                                ).encode("utf-8")).hexdigest()
            with self.subTest(key=key),self.assertRaises(LockedUi10Denied):
                LockedUi10DiagnosticViewModel(doc,digest)

    def test_bad_run_identity_and_unattested_exchange_blocked(self):
        short,swing=views()
        for run in ("","../secrets","has spaces","x"*100,12):
            with self.subTest(run=run),self.assertRaises(LockedUi10Denied):
                build_private_d1_ui10_diagnostic(short,swing,
                    run_id=run,exchange="HOSE")
        for exchange in ("","NASDAQ","hose",None):
            with self.subTest(exchange=exchange),self.assertRaises(LockedUi10Denied):
                build_private_d1_ui10_diagnostic(short,swing,
                    run_id="test187",exchange=exchange)


if __name__=="__main__":
    unittest.main()
