"""§377 engine redacted phase projection: fictional fixtures only."""
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.engine import (
    B5EnginePlan375, S7EnginePlan375, StructuralEnginePlan376, evaluate_baseline_preview,
)
from swing_trading.market_data import Timeframe
import test_baseline_engine375 as prev
import test_engine_structural376 as struct
import test_bound_structure370 as bound


def projected(model, req=None, zone="B2", strategy=Strategy.SHORT):
    result = evaluate_baseline_preview(model, requests=() if req is None else (req,))
    summary = result.safe_phase_summary()
    return next(x for x in summary["zones"]
                if x["zone_id"] == zone and x["strategy"] == strategy.value)


def states(row):
    return [x["ingredient_state"] for x in row["phases"]]


class EnginePhase377Tests(unittest.TestCase):
    def test_legacy_summary_unchanged_and_all_128_phases_fail_closed(self):
        m = prev.b2.model("B2")
        result = evaluate_baseline_preview(m)
        old, new = result.safe_summary(), result.safe_phase_summary()
        self.assertNotEqual(old["schema"], new["schema"])
        self.assertEqual(len(new["zones"]), 32)
        for before, after in zip(old["zones"], new["zones"]):
            self.assertEqual(before, {k: v for k, v in after.items() if k != "phases"})
            self.assertEqual(states(after), ["NOT_CONFIGURED"]*4)
            self.assertEqual([p["phase"] for p in after["phases"]], ["R0","R_C","R_E","R_F"])
            self.assertTrue(all(p["phase_verified"] is False and p["action_eligible"] is False
                                for p in after["phases"]))
        self.assertEqual(new["decision"], "NO_TRADE")
        self.assertEqual(new["publication_state"], "INCOMPLETE_REPORT")

    def test_independent_b2s2_observed_and_missing(self):
        for zone in ("B2","S2"):
            for strategy in Strategy:
                req = prev.request(zone, prev.b2.config(), strategy)
                row = projected(prev.b2.model(zone, missing_h1=True), req, zone, strategy)
                self.assertEqual(states(row), ["GEOMETRY_MATCH_ONLY","DISTANCE_ONLY",
                                               "GEOMETRY_MATCH_ONLY","MISSING_INPUT"])
                self.assertEqual(row["phases"][3]["input_state"], "MISSING_REQUIRED_INPUT")

    def test_conflict_isolated_and_no_configuration_error_text(self):
        m = prev.b2.model("B2", conflict=True)
        row = projected(m, prev.request("B2",prev.b2.config()))
        self.assertEqual(states(row)[0], "GEOMETRY_MATCH_ONLY")
        self.assertEqual(states(row)[2], "BLOCKED")
        self.assertEqual(row["phases"][2]["input_state"], "BLOCKED_REQUIRED_INPUT")
        bad = projected(m, prev.request("B2",object()))
        self.assertEqual(states(bad), ["CONFIG_REJECTED"]*4)

    def test_every_structural_route_only_requested_phase_observed(self):
        for key, (_, frames) in struct.ROUTES.items():
            tf = frames[0]
            req = prev.request(key[0],StructuralEnginePlan376((struct.plan(key[2],tf),)),
                               variant=key[1])
            row = projected(bound.model(key,tf),req,key[0])
            self.assertEqual([p["ingredient_state"] for p in row["phases"]
                              if p["phase"] == key[2]],["GEOMETRY_MATCH_ONLY"])
            self.assertEqual(states(row).count("NOT_REQUESTED"),3)

    def test_b5_combined_chain_not_individual_phase_approval(self):
        for variant in (prev.b5.RECLAIM,prev.b5.FAILED):
            m,p,f = prev.b5.fixture(variant)
            row = projected(m,prev.request("B5",B5EnginePlan375(p,f),variant=variant),"B5")
            self.assertEqual(states(row), ["CHAIN_GEOMETRY_ONLY"]*4)
            self.assertTrue(all(not x["phase_verified"] for x in row["phases"]))

    def test_s7_continuation_pending_not_micro_or_missing_fallback(self):
        for later in (False, True):
            m,o,f,_ = prev.s7.fixture(later)
            for variant, micro, final in ((prev.s7.MICRO,f,"CHAIN_GEOMETRY_ONLY"),
                                          (prev.s7.CONT,None,"SPEC_PENDING")):
                row = projected(m,prev.request("S7",S7EnginePlan375(o,micro),
                                               variant=variant),"S7")
                self.assertEqual(states(row),["CHAIN_GEOMETRY_ONLY","CHAIN_GEOMETRY_ONLY",
                                              "GEOMETRY_MATCH_ONLY",final])

    def test_projection_has_fixed_redacted_fields(self):
        m,p,f = prev.b5.fixture()
        req = prev.request("B5",B5EnginePlan375(p,f),variant=prev.b5.RECLAIM)
        row = projected(m,req,"B5")
        for phase in row["phases"]:
            self.assertEqual(set(phase),{"phase","ingredient_state","input_state",
                                        "phase_verified","action_eligible"})
        wire = json.dumps(row)
        for forbidden in (m.instrument_id,"preview_id","raw_digest","candidate_epsilon",
                          "micro_high_price","source_revision","volume_reason"):
            self.assertNotIn(forbidden,wire)
