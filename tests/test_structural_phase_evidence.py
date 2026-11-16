"""§207 fictional-only versioned BOS→16-zone phase attachment tests.

No provider-origin or exchange-time attestation, confirmed detector, trade,
broker order, full UI publication, or source-licensed data is asserted.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.causal_structure_geometry import StructureSide, TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import QualityState, resolve_as_known
from swing_trading.structural_phase_evidence import (
    PhaseEvidenceDenied, PhaseEvidenceState, ROUTES, SCHEMA,
    inspect_phase_bos_evidence, project_unverified_16_zone_evidence,
)
from test_causal_structure_geometry import highs, lows, atr_d1, AS_OF, snap


def evidence(
    zone="B1", strategy=Strategy.SHORT, variant=None, phase="R_E",
    *, asof=AS_OF, eps=D("0.25"), **changes,
):
    if variant is None:
        variant = {
            "B1": "B1/E_BOS_UP",
            "B3": "B3/E_BOS_UP",
            "S4": "S4/E_BOS_DOWN",
            "B8": "B8/BASE",
        }.get(zone, "B5/E_RECLAIM")
    bars = lows() if zone == "S4" else highs()
    data = dict(
        zone_id=zone, strategy=strategy, variant_id=variant, phase=phase,
        pivot_history=bars[:4], pivot_index=2, left_count=1,
        right_count=1, previous=bars[4], breakout=bars[5],
        atr_d1_history=atr_d1(), tie_policy=TiePolicy.STRICT_V1,
        candidate_epsilon=eps, as_of_utc=asof,
    )
    data.update(changes)
    return inspect_phase_bos_evidence(**data)


class PhaseStructureEvidence207Tests(unittest.TestCase):
    def test_exact_original_four_bos_phase_routes_only(self):
        self.assertEqual(
            tuple(ROUTES),
            (("B1","B1/E_BOS_UP","R_E"),
             ("B3","B3/E_BOS_UP","R_E"),
             ("S4","S4/E_BOS_DOWN","R_E"),
             ("B8","B8/BASE","R_E")),
        )
        for z,v,p in ROUTES:
            self.assertEqual(p,"R_E")
            self.assertIn(z,ZONE_IDS)
            self.assertEqual(
                ROUTES[(z,v,p)][0],
                StructureSide.LOW if z == "S4" else StructureSide.HIGH,
            )

    def test_b1_b3_b8_bullish_and_s4_bearish_attach_as_unverified(self):
        for zone in ("B1","B3","B8","S4"):
            with self.subTest(zone=zone):
                result=evidence(zone=zone)
                self.assertIs(result.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
                self.assertIs(result.status,DecisionStatus.UNVERIFIED)
                self.assertEqual(result.phase,"R_E")
                self.assertEqual(result.schema,SCHEMA)
                self.assertTrue(result.predicate_ref.startswith(zone+".RE."))
                self.assertTrue(result.pivot_preview_id.startswith("MST_PIVOT_PREVIEW_V1:"))
                self.assertTrue(result.bos_preview_id.startswith("MST_BOS_PREVIEW_V1:"))
                self.assertLessEqual(result.witness_known_at_utc,result.as_of_utc)
                self.assertFalse(result.source_independently_attested)
                self.assertFalse(result.detector_approved)
                self.assertFalse(result.action_eligible)

    def test_bullish_event_is_not_the_bearish_pivot(self):
        self.assertIs(evidence("S4").side,StructureSide.LOW)
        for zone in ("B1","B3","B8"):
            self.assertIs(evidence(zone).side,StructureSide.HIGH)

    def test_identical_replay_unchanged_event_identity_and_later_asof(self):
        a=evidence()
        b=evidence()
        future=evidence(asof=AS_OF+timedelta(days=1))
        self.assertEqual(a.pivot_preview_id,b.pivot_preview_id)
        self.assertEqual(a.bos_preview_id,b.bos_preview_id)
        self.assertEqual(a.bos_preview_id,future.bos_preview_id)
        self.assertEqual(a.pivot_preview_id,future.pivot_preview_id)

    def test_strategy_remains_separate_in_event_fingerprint(self):
        short=evidence(strategy=Strategy.SHORT)
        swing=evidence(strategy=Strategy.SWING)
        self.assertEqual(short.pivot_preview_id,swing.pivot_preview_id)
        self.assertNotEqual(short.bos_preview_id,swing.bos_preview_id)

    def test_rule_variant_namespaces_prevent_accidental_crossover(self):
        ids=[evidence(zone=z).bos_preview_id for z in ("B1","B3","B8","S4")]
        self.assertEqual(len(set(ids)),4)

    def test_candidate_epsilon_revision_alters_event_identity(self):
        old=evidence(eps=D("0.25"))
        new=evidence(eps=D("0.30"))
        self.assertIs(new.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
        self.assertEqual(old.pivot_preview_id,new.pivot_preview_id)
        self.assertNotEqual(old.bos_preview_id,new.bos_preview_id)

    def test_tie_policy_version_changes_event_identity(self):
        a=evidence()
        b=evidence(tie_policy=TiePolicy.ALLOW_EQUAL_V1)
        self.assertNotEqual(a.pivot_preview_id,b.pivot_preview_id)
        self.assertNotEqual(a.bos_preview_id,b.bos_preview_id)

    def test_source_revision_changes_event_identity_not_previous_identity(self):
        originals=highs()
        original=originals[5].selected
        rev=replace(
            original.observation_revision,
            source_revision_or_payload_digest="correction-rev-2",
        )
        corrected=replace(
            original,observation_revision=rev,
            raw_digest_sha256="c"*64,
            normalized_digest_sha256="d"*64,
            close=D("19"),
        )
        fresh=evidence(breakout=snap(corrected))
        old=evidence()
        self.assertIs(fresh.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
        self.assertEqual(fresh.pivot_preview_id,old.pivot_preview_id)
        self.assertNotEqual(fresh.bos_preview_id,old.bos_preview_id)

    def test_pivot_source_correction_changes_both_fingerprints(self):
        originals=highs()
        base=originals[2].selected
        rev=replace(
            base.observation_revision,
            source_revision_or_payload_digest="corrected-pivot",
        )
        corrected=replace(
            base,observation_revision=rev,
            normalized_digest_sha256="e"*64,
        )
        history=originals[:2]+(snap(corrected),)+originals[3:4]
        fresh=evidence(pivot_history=history)
        old=evidence()
        self.assertIs(fresh.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
        self.assertNotEqual(fresh.pivot_preview_id,old.pivot_preview_id)
        self.assertNotEqual(fresh.bos_preview_id,old.bos_preview_id)

    def test_no_right_bars_returns_blocked_not_a_negative_signal(self):
        result=evidence(pivot_history=highs()[:3])
        self.assertEqual(result.state,PhaseEvidenceState.BLOCKED)
        self.assertIs(result.status,DecisionStatus.UNVERIFIED)
        self.assertIsNone(result.pivot_preview_id)
        self.assertIsNone(result.bos_preview_id)

    def test_unknown_buffer_is_blocked_not_zero_buffer(self):
        result=evidence(eps=None)
        self.assertIs(result.state,PhaseEvidenceState.BLOCKED)
        self.assertEqual(result.reason,"UNAPPROVED_EPSILON_NOT_SUPPLIED")
        self.assertIsNone(result.bos_preview_id)

    def test_non_crossing_close_no_event_and_never_not_detected(self):
        original=highs()[5].selected
        changed=replace(original,close=D("16"))
        result=evidence(breakout=snap(changed))
        self.assertIs(result.state,PhaseEvidenceState.NONCROSS_GEOMETRY_ONLY)
        self.assertIs(result.status,DecisionStatus.UNVERIFIED)
        self.assertIsNone(result.bos_preview_id)

    def test_future_close_and_fake_source_quality_fail_closed(self):
        row=highs()[5].selected
        before=row.bar_end_utc-timedelta(seconds=1)
        r=evidence(asof=before)
        self.assertIs(r.state,PhaseEvidenceState.BLOCKED)
        unknown=snap(replace(row,quality_state=QualityState.UNVERIFIED))
        r=evidence(breakout=unknown)
        self.assertIs(r.state,PhaseEvidenceState.BLOCKED)
        self.assertIsNone(r.bos_preview_id)

    def test_future_revision_in_candidate_is_not_used(self):
        original=highs()[5].selected
        revised_revision=replace(
            original.observation_revision,
            first_known_time_utc=AS_OF+timedelta(days=2),
            retrieved_at_utc=AS_OF+timedelta(days=2),
        )
        revised=replace(
            original,observation_revision=revised_revision,
            retrieved_at_utc=revised_revision.retrieved_at_utc,
            verified_at_utc=revised_revision.retrieved_at_utc+timedelta(minutes=1),
        )
        ref=resolve_as_known(
            original.market_bar_key,(original,revised),AS_OF
        )
        r=evidence(breakout=ref)
        self.assertEqual(r.bos_preview_id,evidence().bos_preview_id)
        conflict=resolve_as_known(
            original.market_bar_key,(original,revised),
            AS_OF+timedelta(days=3),
        )
        after=evidence(breakout=conflict,asof=AS_OF+timedelta(days=3))
        self.assertIs(after.state,PhaseEvidenceState.BLOCKED)

    def test_unapproved_h4_and_wrong_phase_tf_are_rejected(self):
        d=highs()
        last=d[5].selected
        key=replace(last.market_bar_key,timeframe=Timeframe.H4)
        obs=replace(last.observation_key,market_bar_key=key)
        rev=replace(last.observation_revision,observation_key=obs)
        adjusted=replace(
            last,market_bar_key=key,observation_key=obs,
            observation_revision=rev,
        )
        with self.assertRaisesRegex(PhaseEvidenceDenied,"TIMEFRAME_MISMATCH"):
            evidence(breakout=snap(adjusted))
        with self.assertRaisesRegex(PhaseEvidenceDenied,"UNSUPPORTED_ZONE"):
            evidence(variant="B1/E_RECLAIM")
        with self.assertRaises(PhaseEvidenceDenied):
            evidence(phase="R_F")
        with self.assertRaises(PhaseEvidenceDenied):
            evidence(zone="S6")
        with self.assertRaises(PhaseEvidenceDenied):
            evidence(strategy="SHORT")

    def test_source_provider_conflict_prevents_fingerprint(self):
        base=highs()[4].selected
        obs=replace(base.observation_key,provider_id="OTHER")
        revised=replace(
            base,observation_key=obs,
            observation_revision=replace(
                base.observation_revision,observation_key=obs,
            ),
        )
        r=evidence(previous=snap(revised))
        self.assertIs(r.state,PhaseEvidenceState.BLOCKED)
        self.assertIsNone(r.bos_preview_id)

    def test_no_signature_or_raw_source_price_is_exported_as_overlay(self):
        candidate=evidence()
        rows=project_unverified_16_zone_evidence(
            Strategy.SHORT,as_of_utc=AS_OF,candidate=candidate,
        )
        self.assertEqual(len(rows),16)
        self.assertEqual(tuple(r.zone_id for r in rows),ZONE_IDS)
        self.assertTrue(all(r.status is DecisionStatus.UNVERIFIED for r in rows))
        self.assertTrue(all(r.action_eligible is False for r in rows))
        annotated=[r for r in rows if r.preview_id is not None]
        self.assertEqual(len(annotated),1)
        self.assertEqual(annotated[0].zone_id,"B1")
        self.assertEqual(annotated[0].phase,"R_E")
        wire=json.dumps([
            {"zone":r.zone_id,"preview":r.preview_id,"phase":r.phase}
            for r in rows
        ])
        for forbidden in ("native_source_data","synthetic://bars",
                          "source_revision_or_payload_digest",'"ohlc"', '"price"'):
            self.assertNotIn(forbidden,wire)

    def test_missing_preview_is_all_sixteen_unverified(self):
        for strategy in (Strategy.SHORT,Strategy.SWING):
            rows=project_unverified_16_zone_evidence(
                strategy,as_of_utc=AS_OF
            )
            self.assertEqual(len(rows),16)
            self.assertTrue(all(r.preview_id is None for r in rows))

    def test_blocked_and_noncross_preview_does_not_claim_zone(self):
        for result in (
            evidence(eps=None),
            evidence(breakout=snap(replace(highs()[5].selected,close=D("16")))),
        ):
            rows=project_unverified_16_zone_evidence(
                Strategy.SHORT,as_of_utc=AS_OF,candidate=result,
            )
            self.assertTrue(all(r.preview_id is None for r in rows))
            self.assertTrue(all(r.phase is None for r in rows))

    def test_overlay_rejects_cross_strategy_and_clock(self):
        candidate=evidence()
        with self.assertRaisesRegex(PhaseEvidenceDenied,"CROSS_STRATEGY"):
            project_unverified_16_zone_evidence(
                Strategy.SWING,as_of_utc=AS_OF,candidate=candidate,
            )
        with self.assertRaisesRegex(PhaseEvidenceDenied,"CROSS_STRATEGY"):
            project_unverified_16_zone_evidence(
                Strategy.SHORT,as_of_utc=AS_OF+timedelta(days=1),
                candidate=candidate,
            )

    def test_unverified_preview_type_cannot_be_relabelled_approved(self):
        initial=evidence()
        for updates in (
            {"detector_approved":True}, {"action_eligible":True},
            {"source_independently_attested":True},
            {"status":DecisionStatus.DETECTED},
            {"status":DecisionStatus.NOT_DETECTED},
            {"witness_known_at_utc":AS_OF+timedelta(days=1)},
            {"bos_preview_id":"FORGED_CONFIRMED"},
            {"phase":"R_F"},
        ):
            with self.subTest(updates=updates),self.assertRaises(
                PhaseEvidenceDenied
            ):
                replace(initial,**updates)

    def test_fabricated_blocked_event_id_is_forbidden(self):
        blocked=evidence(eps=None)
        with self.assertRaises(PhaseEvidenceDenied):
            replace(blocked,bos_preview_id=evidence().bos_preview_id)


if __name__=="__main__":
    unittest.main()
