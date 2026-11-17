"""§208 synthetic-only real call-path integration: private D1 → engine → UI1.0.

The two source fixtures are intentionally DIFFERENT instruments/sources.
The structure preview MUST be labelled unbound to D1, never signal evidence.
No external provider payload, vendor rights, production publish or trading.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.locked_ui10_binding import (
    LockedUi10Denied, LockedUi10DiagnosticViewModel,
    attach_unbound_structural_previews,
)
from swing_trading.private_cache_signal_ui_preview import (
    PrivateCacheUiPreview, PrivateCacheUiPreviewDenied,
    render_private_d1_cache_signal_ui_preview,
)
from swing_trading.structural_phase_evidence import (
    PhaseEvidenceState, PhaseStructureEvidence,
)
from test_private_cache_source_bridge import source, NOW
from test_structural_phase_evidence import evidence
from test_causal_structure_geometry import highs, snap


def run(provider="SSI", structural=(), *, source_doc=None, run_id="fixture208"):
    return render_private_d1_cache_signal_ui_preview(
        source(provider) if source_doc is None else source_doc,
        as_of_utc=NOW, run_id=run_id, exchange="HOSE",
        structure_previews=structural,
    )


def preview_candidate(strategy=Strategy.SHORT, zone="B1"):
    return evidence(zone=zone, strategy=strategy, asof=NOW)


class PrivateD1StructureOverlay208Tests(unittest.TestCase):
    def test_empty_optional_preview_keeps_existing_locked_ui_html(self):
        original=render_private_d1_cache_signal_ui_preview(
            source(),as_of_utc=NOW,run_id="fixture208",exchange="HOSE",
        )
        copy=run()
        self.assertEqual(original.html,copy.html)
        self.assertEqual(original.html_sha256,copy.html_sha256)
        self.assertEqual(copy.safe_summary["unbound_structural_preview_count"],0)
        self.assertNotIn("structural_preview_diagnostics",copy.viewmodel.data)
        self.assertNotIn('data-structure-preview="unbound"',copy.html)

    def test_three_provider_reference_bridges_preserve_16_zone_no_trade(self):
        short=preview_candidate()
        for provider in ("SSI","DNSE","VCBS"):
            with self.subTest(provider=provider):
                result=run(provider,(short,))
                self.assertEqual(result.safe_summary["source_provider"],provider)
                self.assertEqual(result.safe_summary["decision"],"NO_TRADE")
                self.assertEqual(result.safe_summary["publication_state"],"INCOMPLETE_REPORT")
                self.assertIs(result.eligible_for_signals,False)
                self.assertIs(result.report_published,False)
                self.assertEqual(result.broker_orders,0)
                self.assertIs(result.viewmodel.data["report_published"],False)
                self.assertIs(result.viewmodel.data["step08_atomic_commit_verified"],False)
                self.assertEqual(result.viewmodel.data["zone_verified_count"],0)
                zones=result.viewmodel.data["zone_rows"]
                self.assertEqual(tuple(z["zone_id"] for z in zones),ZONE_IDS)
                self.assertTrue(all(z["status"]=="UNVERIFIED" for z in zones))
                self.assertTrue(all(z["eligible_for_signal"] is False for z in zones))
                self.assertTrue(all(z["evidence"]==[] for z in zones))
                self.assertEqual(result.safe_summary["unbound_structural_preview_count"],1)
                self.assertIn('data-structure-preview="unbound"',result.html)
                self.assertIn("Chưa đối chiếu các nến M15/H1",result.html)
                self.assertIn("NO_TRADE",result.html)
                self.assertNotIn("ACTION_ELIGIBLE",result.html)

    def test_both_strategies_have_separate_overlay_with_no_trade(self):
        a=preview_candidate(Strategy.SHORT,"B1")
        b=preview_candidate(Strategy.SWING,"S4")
        result=run("SSI",(a,b))
        rows=result.viewmodel.data["structural_preview_diagnostics"]
        self.assertEqual(len(rows),2)
        self.assertEqual([r["strategy"] for r in rows],["SHORT","SWING"])
        self.assertEqual([r["zone_id"] for r in rows],["B1","S4"])
        self.assertTrue(all(r["source_relation"]=="UNBOUND_TO_PRIVATE_D1"
                            for r in rows))
        self.assertTrue(all(r["status"]=="UNVERIFIED"
                            and r["action_eligible"] is False for r in rows))
        self.assertEqual(result.safe_summary["unbound_structural_preview_count"],2)
        self.assertIn("MST · INCOMPLETE_REPORT · UI-1.0",result.html)

    def test_html_A_through_I_sections_unchanged_and_csp_locked(self):
        r=run(structural=(preview_candidate(),))
        self.assertEqual(
            tuple(k for k in "ABCDEFGHI" if f'data-ui-section="{k}"' in r.html),
            tuple("ABCDEFGHI"),
        )
        self.assertEqual(r.html.count('data-ui-section="'),9)
        self.assertIn("script-src &#39;none&#39;",r.html)
        self.assertNotIn("<script",r.html)
        self.assertNotIn("<form",r.html)
        self.assertNotIn("<button",r.html)

    def test_candidate_fingerprint_is_run_scoped_but_not_verified_source(self):
        candidate=preview_candidate()
        a=run("SSI",(candidate,),run_id="fixture208_a")
        b=run("SSI",(candidate,),run_id="fixture208_a")
        changed=run("SSI",(candidate,),run_id="fixture208_b")
        self.assertEqual(a.html,b.html)
        self.assertEqual(a.html_sha256,b.html_sha256)
        self.assertEqual(a.safe_summary_sha256,b.safe_summary_sha256)
        x=a.viewmodel.data["structural_preview_diagnostics"][0]
        self.assertEqual(len(x["preview_digest_sha256"]),64)
        self.assertNotEqual(
            x["preview_digest_sha256"],
            changed.viewmodel.data["structural_preview_diagnostics"][0]
               ["preview_digest_sha256"],
        )
        self.assertEqual(x["source_relation"],"UNBOUND_TO_PRIVATE_D1")

    def test_source_d1_correction_rebinds_preview_without_qualifying_candle(self):
        raw=source("SSI")
        a=run("SSI",(preview_candidate(),),source_doc=raw)
        altered=deepcopy(raw)
        altered["native_source_data"][0]["close"]="50800"
        b=run("SSI",(preview_candidate(),),source_doc=altered)
        x=a.viewmodel.data["structural_preview_diagnostics"][0]["preview_digest_sha256"]
        y=b.viewmodel.data["structural_preview_diagnostics"][0]["preview_digest_sha256"]
        self.assertNotEqual(x,y)
        self.assertNotEqual(a.viewmodel.reference_sha256,b.viewmodel.reference_sha256)
        self.assertEqual(b.safe_summary["decision"],"NO_TRADE")
        self.assertFalse(b.safe_summary["source_production_qualified"])

    def test_corrected_structural_close_rebinds_fingerprint_but_no_trade(self):
        bar=highs()[5].selected
        changed=replace(bar,close=Decimal("19"))
        candidate=evidence(asof=NOW,breakout=snap(changed))
        a=run(structural=(preview_candidate(),))
        b=run(structural=(candidate,))
        self.assertNotEqual(a.html_sha256,b.html_sha256)
        self.assertEqual(b.safe_summary["decision"],"NO_TRADE")
        self.assertEqual(b.viewmodel.data["zone_verified_count"],0)

    def test_wrong_asof_future_preview_blocked(self):
        candidate=evidence(asof=NOW+timedelta(days=1))
        with self.assertRaisesRegex(LockedUi10Denied,"NOT_UNBOUND_OR_CAUSAL"):
            run(structural=(candidate,))

    def test_wrong_shape_three_repeated_or_wrong_type_denied(self):
        a=preview_candidate(Strategy.SHORT)
        b=preview_candidate(Strategy.SWING)
        for bad in ([a],(a,a),(a,b,a),None,("UNTRUSTED",)):
            with self.subTest(bad=repr(type(bad))),self.assertRaises(LockedUi10Denied):
                run(structural=bad)

    def test_blocked_or_noncross_cannot_become_displayed_structure(self):
        blocked=evidence(asof=NOW,eps=None)
        self.assertIs(blocked.state,PhaseEvidenceState.BLOCKED)
        close=highs()[5].selected
        noncross=evidence(asof=NOW,breakout=snap(replace(
            close,close=Decimal("16"),
        )))
        self.assertIs(noncross.state,PhaseEvidenceState.NONCROSS_GEOMETRY_ONLY)
        for candidate in (blocked,noncross):
            with self.subTest(state=candidate.state),self.assertRaises(
                LockedUi10Denied
            ):
                run(structural=(candidate,))

    def test_preview_cannot_assert_source_qualifications_or_trade(self):
        base=preview_candidate()
        for update in (
            {"action_eligible":True},
            {"source_independently_attested":True},
            {"detector_approved":True},
            {"status":DecisionStatus.DETECTED},
        ):
            with self.subTest(update=update),self.assertRaises(Exception):
                replace(base,**update)

    def test_source_or_simulated_prices_not_exposed_in_html(self):
        model=run("VCBS",(preview_candidate(),))
        for forbidden in (
            "50500","50750","51000","52000",
            "native_source_data","source_revision_or_payload_digest",
            "synthetic://bars","fixture-session",
            "price_basis","source_stream_id","raw_digest_sha256",
            "MST_BOS_PREVIEW_V1:","FIRST_KNOWN_VERIFIED",
        ):
            self.assertNotIn(forbidden,model.html)
        row=model.viewmodel.data["structural_preview_diagnostics"][0]
        self.assertEqual(set(row),{
            "strategy","zone_id","phase","timeframe","predicate_ref",
            "preview_digest_sha256","source_relation","status","action_eligible",
        })
        self.assertEqual(len(row["preview_digest_sha256"]),64)

    def test_forged_preview_json_with_rehash_cannot_promote_status(self):
        good=run(structural=(preview_candidate(),))
        for field,value in (
            ("status","DETECTED"),
            ("source_relation","BOUND_TO_D1_VERIFIED"),
            ("action_eligible",True),
            ("timeframe","H4"),
            ("preview_digest_sha256","not_sha256"),
        ):
            changed=deepcopy(good.viewmodel.data)
            changed["structural_preview_diagnostics"][0][field]=value
            wire=json.dumps(changed,sort_keys=True,separators=(",",":"),
                            ensure_ascii=False,allow_nan=False).encode()
            with self.subTest(field=field),self.assertRaises(LockedUi10Denied):
                LockedUi10DiagnosticViewModel(changed,sha256(wire).hexdigest())

    def test_rehashing_summary_count_cannot_hide_or_fabricate_preview(self):
        good=run(structural=(preview_candidate(),))
        for count in (0,2,-1,"1",True):
            fake=deepcopy(good.safe_summary)
            fake["unbound_structural_preview_count"]=count
            wire=json.dumps(fake,sort_keys=True,separators=(",",":"),
                            allow_nan=False,ensure_ascii=True).encode()
            with self.subTest(count=count),self.assertRaises(
                PrivateCacheUiPreviewDenied
            ):
                PrivateCacheUiPreview(
                    good.html,good.html_sha256,good.viewmodel,
                    fake,sha256(wire).hexdigest(),
                )

    def test_ui_mutation_after_creation_is_revalidated_before_renderer(self):
        result=run(structural=(preview_candidate(),))
        result.viewmodel.data["structural_preview_diagnostics"][0]["status"]="DETECTED"
        with self.assertRaises(LockedUi10Denied):
            PrivateCacheUiPreview(
                result.html,result.html_sha256,result.viewmodel,
                result.safe_summary,result.safe_summary_sha256,
            )

    def test_invariant_reference_D1_is_not_claimed_as_licensed_M15_or_H1(self):
        r=run("SSI",(preview_candidate(),))
        self.assertEqual(
            [x["status"] for x in r.safe_summary["required_tf_coverage"]],
            ["MISSING"]*5+["D1_REFERENCE_ONLY"],
        )
        self.assertIs(r.safe_summary["h4_native_provider_supported"],False)
        self.assertIs(r.safe_summary["w1_context_attested"],False)
        self.assertIs(r.safe_summary["verified_16_zone_rules"],False)
        self.assertIs(r.safe_summary["source_production_qualified"],False)
        self.assertIs(r.safe_summary["step08_committed"],False)


if __name__=="__main__":
    unittest.main()
