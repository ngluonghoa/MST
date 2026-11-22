"""§213 source-locked R_F CLOSED structural *ingredient* replay tests.

These are fabricated OHLCV streams, not a real licensed source, complete
R_F predicate, original detector, calibrated trade, position or release.
Existing §207 R_E identities remain unchanged.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.contracts import DecisionStatus, Strategy, ZONE_IDS
from swing_trading.causal_structure_geometry import StructureSide, TiePolicy
from swing_trading.market_data import Timeframe
from swing_trading.source_quality import QualityState
from swing_trading.structural_phase_evidence import (
    ROUTES, PhaseEvidenceDenied, PhaseEvidenceState,
    inspect_phase_bos_evidence, project_unverified_16_zone_evidence,
)
from test_causal_indicators import make_bar, snap
from test_causal_structure_geometry import AS_OF, PIVOT0, atr_d1


HIGH_ITEMS=(
    ("12","8","10"),("13","8","11"),("16","8","14"),
    ("14","8","12"),("16","8","16"),("20","8","18"),
)
LOW_ITEMS=(
    ("12","7","10"),("12","6","10"),("12","3","5"),
    ("12","5","8"),("12","4","4"),("12","1","1"),
)
R_F_KEYS=(
    ("B1","B1/E_BOS_UP","R_F"),
    ("B2","B2/BASE","R_F"),
    ("B4","B4/BASE","R_F"),
    ("B6","B6/C_TWO_CONTRACTIONS","R_F"),
    ("B7","B7/E_RECLAIM","R_F"),
    ("B8","B8/BASE","R_F"),
    ("S1","S1/E_CHOCH_DOWN","R_F"),
    ("S2","S2/BASE","R_F"),
    ("S3","S3/F_MICRO_BREAK","R_F"),
    ("S4","S4/E_BOS_DOWN","R_F"),
    ("S5","S5/BASE","R_F"),
    ("S6","S6/BASE","R_F"),
    ("S7","S7/F_MICRO_BREAK","R_F"),
    ("S8","S8/BASE","R_F"),
)


def bars_for(side, tf):
    """Fabricated but non-overlapping M15/H1/D1 closed intervals."""
    items=HIGH_ITEMS if side is StructureSide.HIGH else LOW_ITEMS
    result=[]
    for i,(high,low,close) in enumerate(items):
        if tf is Timeframe.D1:
            begin=PIVOT0+timedelta(days=i)
        elif tf is Timeframe.H1:
            begin=PIVOT0+timedelta(hours=i*2)
        else:
            begin=PIVOT0+timedelta(minutes=i*30)
        row=make_bar(
            i+200, timeframe=tf, start=begin,
            high=D(high),low=D(low),close=D(close),
            open_price=D("10"),
        )
        if tf is Timeframe.H1:
            end=begin+timedelta(hours=1)
            retrieved=end+timedelta(minutes=1)
            verified=end+timedelta(minutes=2)
            revision=replace(
                row.observation_revision,
                first_known_time_utc=end,
                retrieved_at_utc=retrieved,
            )
            row=replace(
                row, bar_end_utc=end, observation_revision=revision,
                retrieved_at_utc=retrieved, verified_at_utc=verified,
            )
        result.append(snap(row))
    return tuple(result)


def proof(zone,variant,phase="R_F", *, timeframe=None, as_of=AS_OF,
          epsilon=D("0.25"), side=None, **changes):
    declared=ROUTES[(zone,variant,phase)]
    side=declared[0] if side is None else side
    tf=declared[1][0] if timeframe is None else timeframe
    bars=bars_for(side,tf)
    params=dict(
        zone_id=zone, strategy=Strategy.SHORT,
        variant_id=variant, phase=phase,
        pivot_history=bars[:4],pivot_index=2,left_count=1,right_count=1,
        previous=bars[4],breakout=bars[5],
        atr_d1_history=atr_d1(), tie_policy=TiePolicy.STRICT_V1,
        candidate_epsilon=epsilon, as_of_utc=as_of,
    )
    params.update(changes)
    return inspect_phase_bos_evidence(**params)


class ClosedBreakRF213Tests(unittest.TestCase):
    def test_all_fourteen_routes_exact_source_and_direction(self):
        observed=tuple(k for k in ROUTES if k[2]=="R_F")
        self.assertEqual(observed,R_F_KEYS)
        self.assertEqual(len(observed),14)
        for zone,variant,phase in observed:
            with self.subTest(zone=zone):
                self.assertIn(zone,ZONE_IDS)
                self.assertEqual(
                    ROUTES[(zone,variant,phase)][0],
                    StructureSide.HIGH if zone.startswith("B")
                    else StructureSide.LOW,
                )
                self.assertTrue(all(
                    tf in (Timeframe.M15,Timeframe.H1,Timeframe.D1)
                    for tf in ROUTES[(zone,variant,phase)][1]
                ))

    def test_all_fourteen_closed_breaks_are_executable_geometry_only(self):
        for key in R_F_KEYS:
            with self.subTest(key=key):
                candidate=proof(*key)
                self.assertIs(candidate.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
                self.assertEqual(candidate.phase,"R_F")
                self.assertTrue(candidate.predicate_ref.startswith(key[0]+".RF."))
                self.assertTrue(candidate.bos_preview_id.startswith("MST_BOS_PREVIEW_V1:"))
                self.assertEqual(candidate.status,DecisionStatus.UNVERIFIED)
                self.assertFalse(candidate.detector_approved)
                self.assertFalse(candidate.source_independently_attested)
                self.assertFalse(candidate.action_eligible)

    def test_supported_alternative_timeframes_have_actual_closed_cross_geometry(self):
        for key in R_F_KEYS:
            for tf in ROUTES[key][1]:
                with self.subTest(key=key,tf=tf):
                    result=proof(*key,timeframe=tf)
                    self.assertIs(result.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
                    self.assertEqual(result.timeframe,tf)
                    self.assertLessEqual(result.witness_known_at_utc,result.as_of_utc)

    def test_b2_s2_mirror_uses_separate_up_down_structural_boundaries(self):
        b=proof("B2","B2/BASE")
        s=proof("S2","S2/BASE")
        self.assertIs(b.side,StructureSide.HIGH)
        self.assertIs(s.side,StructureSide.LOW)
        self.assertNotEqual(b.bos_preview_id,s.bos_preview_id)
        self.assertEqual(b.phase,s.phase)
        self.assertFalse(b.action_eligible)
        self.assertFalse(s.action_eligible)

    def test_no_intrabar_wick_or_exact_boundary_counts_as_closed_cross(self):
        for key in R_F_KEYS:
            tf=ROUTES[key][1][0]
            side=ROUTES[key][0]
            bars=bars_for(side,tf)
            original=bars[5].selected
            # Candidate crosses by wick but CLOSE does not cross.
            bad_close=D("16") if side is StructureSide.HIGH else D("3")
            target=snap(replace(original,close=bad_close))
            result=proof(*key,breakout=target)
            self.assertIs(result.state,PhaseEvidenceState.NONCROSS_GEOMETRY_ONLY)
            self.assertIsNone(result.bos_preview_id)
            self.assertIs(result.status,DecisionStatus.UNVERIFIED)

    def test_unsupported_timeframe_and_no_h4_without_session_proof(self):
        for key in R_F_KEYS:
            with self.subTest(key=key),self.assertRaisesRegex(
                PhaseEvidenceDenied,"TIMEFRAME_MISMATCH"
            ):
                proof(*key,timeframe=Timeframe.H4)
        with self.assertRaisesRegex(PhaseEvidenceDenied,"TIMEFRAME_MISMATCH"):
            proof("B1","B1/E_BOS_UP",timeframe=Timeframe.M15)

    def test_unsupported_or_tp_variants_are_not_silently_accepted(self):
        for zone,variant in (
            ("S3","S3/E_TP"),
            ("S3","S3/F_TP"),
            ("B6","B6/C_COMPRESSION"),
            ("B1","B1/F_MAJOR_REVERSAL_PENDING"),
            ("S1","S1/F_MAJOR_CYCLE_TOP_PENDING"),
        ):
            with self.subTest(zone=zone,variant=variant):
                with self.assertRaisesRegex(
                    PhaseEvidenceDenied,"UNSUPPORTED_ZONE"
                ):
                    inspect_phase_bos_evidence(
                        zone_id=zone,strategy=Strategy.SHORT,
                        variant_id=variant,phase="R_F",
                        pivot_history=(),pivot_index=0,left_count=1,right_count=1,
                        previous=bars_for(StructureSide.HIGH,Timeframe.M15)[4],
                        breakout=bars_for(StructureSide.HIGH,Timeframe.M15)[5],
                        atr_d1_history=atr_d1(),tie_policy=TiePolicy.STRICT_V1,
                        candidate_epsilon=D("0.25"),as_of_utc=AS_OF,
                    )

    def test_source_not_qualified_or_missing_buffer_blocks_geometry(self):
        for key in R_F_KEYS:
            with self.subTest(key=key):
                blocked=proof(*key,epsilon=None)
                self.assertIs(blocked.state,PhaseEvidenceState.BLOCKED)
                self.assertIsNone(blocked.bos_preview_id)
        tf=ROUTES[R_F_KEYS[0]][1][0]
        snaps=bars_for(StructureSide.HIGH,tf)
        fake=snap(replace(snaps[5].selected,quality_state=QualityState.UNVERIFIED))
        result=proof(*R_F_KEYS[0],breakout=fake)
        self.assertIs(result.state,PhaseEvidenceState.BLOCKED)

    def test_future_asof_fails_closed_not_retroactive(self):
        key=R_F_KEYS[0]
        bars=bars_for(StructureSide.HIGH,Timeframe.D1)
        cutoff=bars[5].selected.bar_end_utc-timedelta(minutes=1)
        result=proof(*key,as_of=cutoff)
        self.assertIs(result.state,PhaseEvidenceState.BLOCKED)
        self.assertIsNone(result.bos_preview_id)

    def test_source_revision_correction_changes_identity(self):
        key=("S1","S1/E_CHOCH_DOWN","R_F")
        initial=proof(*key)
        selected=bars_for(StructureSide.LOW,Timeframe.D1)[5].selected
        revision=replace(
            selected.observation_revision,
            source_revision_or_payload_digest="revised-s1-d1",
        )
        amended=snap(replace(
            selected,observation_revision=revision,raw_digest_sha256="c"*64,
        ))
        changed=proof(*key,breakout=amended)
        self.assertIs(changed.state,PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED)
        self.assertNotEqual(changed.bos_preview_id,initial.bos_preview_id)

    def test_public_zone_overlay_stays_sixteen_unverified_without_price(self):
        for key in (R_F_KEYS[1],R_F_KEYS[7]):
            candidate=proof(*key)
            out=project_unverified_16_zone_evidence(
                Strategy.SHORT,as_of_utc=AS_OF,candidate=candidate,
            )
            self.assertEqual(len(out),16)
            self.assertTrue(all(r.status is DecisionStatus.UNVERIFIED for r in out))
            self.assertTrue(all(r.action_eligible is False for r in out))
            attached=[r for r in out if r.preview_id is not None]
            self.assertEqual(len(attached),1)
            self.assertEqual(attached[0].zone_id,key[0])
            self.assertEqual(attached[0].phase,"R_F")
            self.assertFalse(hasattr(attached[0],"price"))

    def test_per_strategy_event_ids_isolate_short_swing(self):
        key=R_F_KEYS[1]
        short=proof(*key)
        swing=proof(*key,strategy=Strategy.SWING)
        self.assertEqual(short.pivot_preview_id,swing.pivot_preview_id)
        self.assertNotEqual(short.bos_preview_id,swing.bos_preview_id)
        self.assertFalse(short.action_eligible or swing.action_eligible)


if __name__=="__main__":
    unittest.main()
