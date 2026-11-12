"""A02 6th group: 40 executed ORIGINAL V1 replay/migration/evidence/cache cases.

All data are fabricated. No independently controlled approved checkpoint,
vendor rights, production cache, live signals, broker, or owner A02/A03 grant.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.m2_a02_sixth_eight_replay_evidence_migration_runtime_lab import (
    EIGHT, SCHEMA, execute_sixth_eight_runtime,
)
from swing_trading.replay_batch import replay_frame, replay_sequence
from swing_trading.quality_audit import (
    QualityFindingRegistry, FindingSeverity, ResolutionStatus,
)
from swing_trading.legacy_migration import migrate_batch
from swing_trading.migration_archive import archive_migration_batch, RawSourceBinding
from swing_trading.durable_evidence import EvidenceStore, EvidenceItem, EvidenceCorrupt, State, ZERO
from swing_trading.evidence_recovery import backup_verified, restore_verified
from swing_trading.evidence_checkpoint import (
    EvidenceCheckpoint, create_candidate_checkpoint,
    verify_backup_against_pinned, verify_history_prefix, restore_from_pinned,
)
from swing_trading.segmented_cache import (
    SyntheticWeeklyChunkStore, require_authorized_window_cache,
)
from swing_trading.source_quality import QualityState, CoverageState
from swing_trading.market_data import BarClosure
from test_replay_batch import m5_fixture
from test_source_quality import candle, m
from test_quality_audit import finding, manifest, at as quality_at
from test_legacy_migration import row as legacy_row, at as legacy_at
from test_migration_archive import sample
from test_evidence_checkpoint import T as CHECKPOINT_TIME
from test_segmented_cache import key as weekly_key, fake, NOW as WEEKLY_NOW

class SixthEightRealLegacyRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=execute_sixth_eight_runtime()

    def test_01_eight_distinct_original_modules(self):
        self.assertEqual(len(EIGHT),8)
        self.assertEqual(len(set(EIGHT)),8)
        self.assertEqual(self.r["original_modules_executed"],list(EIGHT))

    def test_02_cumulative_48_distinct_remaining_15(self):
        self.assertEqual((self.r["prior_distinct_originals"],
                          self.r["cumulative_originals_with_scoped_runtime_qa"],
                          self.r["originals_not_yet_in_this_tranche_style_review"]),
                         (40,48,15))

    def test_03_original_source_boundary_no_go_schema(self):
        self.assertEqual(self.r["schema"],SCHEMA)
        self.assertIn("NO_GO",self.r["status"])

    def test_04_sixteen_joined_behavior_invariants(self):
        self.assertEqual(self.r["linked_safety_count"],16)
        self.assertTrue(all(self.r["linked_safety_checks"].values()))

    def test_05_no_owner_or_v2_acceptance(self):
        self.assertEqual(self.r["human_owner_a02_module_dispositions"],0)
        self.assertFalse(self.r["a03_v2_full_abi_owner_approved"])
        self.assertFalse(self.r["original_v1_to_v2_full_behavior_equivalence_approved"])

    def test_06_no_market_credential_crypto_or_drive_authority(self):
        for k in ("actual_external_evidence_custodian_authenticated",
                  "vendor_raw_source_bytes_authenticated",
                  "self_held_checkpoint_is_external_monotonic_floor",
                  "actual_drive_market_cache_read_write",
                  "real_multiwriter_server_cas_verified",
                  "real_provider_market_license_verified",
                  "g01_g08_independent_security_gates_closed",
                  "production_release_authorized","trading_authorized"):
            with self.subTest(k=k):
                self.assertFalse(self.r[k])

    def test_07_replay_late_known_m5_not_visible_at_m18(self):
        x=m5_fixture()
        r=replay_frame((x.market_bar_key,),(x,),m(18))
        self.assertEqual(r.bars[0].resolution.reason,"NO_VISIBLE_REVISION")

    def test_08_replay_m15_known_but_not_yet_verified(self):
        x=candle()
        r=replay_frame((x.market_bar_key,),(x,),m(21))
        self.assertFalse(r.bars[0].source_prerequisites_at(m(21)))
        self.assertTrue(replay_frame((x.market_bar_key,),(x,),m(28))
                        .bars[0].source_prerequisites_at(m(28)))

    def test_09_replay_exact_resends_removed(self):
        b=m5_fixture()
        x=replay_frame((b.market_bar_key,),(b,b,b),m(30)).bars[0]
        self.assertEqual(x.exact_retransmissions_removed,2)
        self.assertEqual(x.resolution.visible_candidate_count,1)

    def test_10_replay_same_revision_identity_different_raw_digest_conflicts(self):
        b=m5_fixture()
        bad=replace(b,close=Decimal("11.5"),raw_digest_sha256="c"*64)
        x=replay_frame((b.market_bar_key,),(b,bad),m(30)).bars[0]
        self.assertTrue(x.revision_identity_collision)
        self.assertEqual(x.resolution.reason,"SOURCE_OR_REVISION_CONFLICT")

    def test_11_replay_future_revision_never_backdates_before_first_known(self):
        b=m5_fixture()
        rev=replace(b.observation_revision,
                    source_revision_or_payload_digest="r2",
                    first_known_time_utc=m(40),retrieved_at_utc=m(41))
        late=replace(b,observation_revision=rev,
                     retrieved_at_utc=m(41),verified_at_utc=m(42),
                     close=Decimal("11.5"))
        frames=replay_sequence((b.market_bar_key,),(b,late),(m(30),m(39),m(40)))
        self.assertEqual(frames[0].bars[0].resolution.selected,b)
        self.assertEqual(frames[1].bars[0].resolution.selected,b)
        self.assertEqual(frames[2].bars[0].resolution.reason,"SOURCE_OR_REVISION_CONFLICT")

    def test_12_replay_rejects_decreasing_snapshot_clock(self):
        b=m5_fixture()
        with self.assertRaises(ValueError):
            replay_sequence((b.market_bar_key,),(b,),(m(30),m(29)))

    def test_13_replay_missing_key_is_unknown_not_negative_signal(self):
        k=m5_fixture().market_bar_key
        r=replay_frame((k,),(),m(30))
        self.assertEqual(r.bars[0].resolution.reason,"NO_VISIBLE_REVISION")
        self.assertFalse(r.bars[0].source_prerequisites_at(m(30)))

    def test_14_quality_registry_is_append_only_and_blocker_remains(self):
        f=finding()
        a=QualityFindingRegistry()
        b=a.append(f)
        self.assertEqual(a.findings,())
        self.assertEqual(b.open_blockers(),(f,))

    def test_15_quality_waiver_label_not_independent_approval(self):
        f=finding(resolution_status=ResolutionStatus.WAIVED_WITH_APPROVAL,
                  resolution_reference="fixture-claim")
        x=manifest(quality_findings=(f,))
        self.assertFalse(x.structural_prerequisites(quality_at(120)))

    def test_16_quality_unverified_clock_blocks_even_after_fetch(self):
        x=manifest(verified_at_utc=None)
        self.assertFalse(x.structural_prerequisites(quality_at(120)))

    def test_17_quality_open_finding_blocks_synthetic_manifest(self):
        x=manifest(quality_findings=(finding(),))
        self.assertFalse(x.structural_prerequisites(quality_at(120)))

    def test_18_quality_structural_true_does_not_grant_vendor_rights(self):
        x=manifest()
        self.assertTrue(x.structural_prerequisites(quality_at(120)))
        self.assertFalse(self.r["real_provider_market_license_verified"])

    def test_19_legacy_verified_yields_v12_unverified(self):
        r=migrate_batch((legacy_row(),),legacy_at(30))
        self.assertEqual(r.migrated[0].quality_state,QualityState.UNVERIFIED)
        self.assertEqual(r.migrated[0].coverage_state,CoverageState.UNKNOWN)
        self.assertFalse(r.migrated[0].confirmation_prerequisites(legacy_at(50)))

    def test_20_legacy_unknown_lifecycle_quarantined(self):
        e=legacy_row()
        bad=replace(e,legacy=replace(e.legacy,closure=BarClosure.UNKNOWN))
        r=migrate_batch((bad,),legacy_at(30))
        self.assertEqual(r.counts["quarantined"],1)

    def test_21_legacy_future_revision_quarantined(self):
        e=legacy_row()
        rev=replace(e.legacy.revision,
                    first_known_time_utc=legacy_at(40),
                    retrieved_at_utc=legacy_at(41))
        r=migrate_batch((replace(e,legacy=replace(e.legacy,revision=rev)),),
                        legacy_at(30))
        self.assertEqual(r.counts["quarantined"],1)

    def test_22_raw_migration_archive_persists_original_binary(self):
        with TemporaryDirectory() as td:
            store=EvidenceStore(Path(td)/"e.sqlite");store.initialize()
            e,b=sample(b"\x00raw-fabricated\xff")
            r=archive_migration_batch(store,"batch",(e,),(b,),
                                      legacy_at(30),expected_tip_sha256=ZERO)
            self.assertEqual(r.receipts[0].state,State.STAGED_UNVERIFIED)
            self.assertEqual(store.read_verified_bytes("batch","row-1"),b.raw_bytes)

    def test_23_raw_binding_wrong_digest_denied(self):
        e,b=sample()
        with self.assertRaises(ValueError):
            RawSourceBinding(b.row_reference,b.source_record_id,
                             b.source_snapshot_id,b"tampered",b.declared_sha256)

    def test_24_wrong_snapshot_identity_does_not_write_evidence(self):
        with TemporaryDirectory() as td:
            s=EvidenceStore(Path(td)/"e.sqlite");s.initialize()
            e,b=sample()
            with self.assertRaises(ValueError):
                archive_migration_batch(
                    s,"bad",(e,),(replace(b,source_snapshot_id="wrong"),),
                    legacy_at(30),expected_tip_sha256=ZERO)
            self.assertEqual(s.verify(),(0,ZERO))

    def test_25_stale_tip_migration_denied_atomically(self):
        with TemporaryDirectory() as td:
            s=EvidenceStore(Path(td)/"e.sqlite");s.initialize()
            e,b=sample()
            archive_migration_batch(s,"one",(e,),(b,),
                                    legacy_at(30),expected_tip_sha256=ZERO)
            old=s.verify()
            with self.assertRaises(EvidenceCorrupt):
                archive_migration_batch(s,"two",(e,),(b,),
                                        legacy_at(30),expected_tip_sha256=ZERO)
            self.assertEqual(s.verify(),old)

    def test_26_evidence_empty_genesis_is_exact_zero(self):
        with TemporaryDirectory() as td:
            s=EvidenceStore(Path(td)/"e.sqlite");s.initialize()
            self.assertEqual(s.verify(),(0,ZERO))

    def test_27_evidence_item_raw_tamper_denied(self):
        with self.assertRaises(EvidenceCorrupt):
            EvidenceItem("row","fixture",b"mismatch","0"*64,
                         State.QUARANTINED,"BAD_DIGEST")

    def test_28_evidence_verification_state_cannot_be_forged(self):
        raw=b"fixture"
        with self.assertRaises(TypeError):
            EvidenceItem("row","fixture",raw,sha256(raw).hexdigest(),
                         "VERIFIED","NOT_ALLOWED")

    def test_29_evidence_duplicate_batch_ref_rejected(self):
        with TemporaryDirectory() as td:
            s=EvidenceStore(Path(td)/"e.sqlite");s.initialize()
            raw=b"synthetic"
            item=EvidenceItem("one","fixture",raw,sha256(raw).hexdigest(),
                              State.STAGED_UNVERIFIED,"UNKNOWN_LICENSE")
            with self.assertRaises(ValueError):
                s.append_batch("same",(item,item),CHECKPOINT_TIME)
            self.assertEqual(s.verify(),(0,ZERO))

    def test_30_evidence_online_backup_roundtrips_synthetic_empty(self):
        with TemporaryDirectory() as td:
            root=Path(td);store=EvidenceStore(root/"source.sqlite");store.initialize()
            backup_verified(store,root/"backup.sqlite")
            r=restore_verified(root/"backup.sqlite",root/"restored.sqlite")
            self.assertEqual(r.verify(),(0,ZERO))

    def test_31_evidence_restore_cannot_overwrite_destination(self):
        with TemporaryDirectory() as td:
            root=Path(td);store=EvidenceStore(root/"source.sqlite");store.initialize()
            backup_verified(store,root/"backup.sqlite")
            restore_verified(root/"backup.sqlite",root/"restored.sqlite")
            with self.assertRaises(FileExistsError):
                restore_verified(root/"backup.sqlite",root/"restored.sqlite")

    def test_32_checkpoint_exact_backup_restore_with_selfheld_pin(self):
        with TemporaryDirectory() as td:
            root=Path(td);s=EvidenceStore(root/"source.sqlite");s.initialize()
            raw=b"synthetic"
            e=EvidenceItem("row","source",raw,sha256(raw).hexdigest(),
                           State.QUARANTINED,"NO_VENDOR_ATTESTATION")
            s.append_batch("batch",(e,),CHECKPOINT_TIME)
            cp=create_candidate_checkpoint(s,root/"backup.sqlite",
                                           "cp-1","store-1",CHECKPOINT_TIME)
            pinned=EvidenceCheckpoint.parse_json(cp.canonical_json())
            self.assertEqual(
                verify_backup_against_pinned(root/"backup.sqlite",pinned,
                                             expected_store_id="store-1"),
                (1,cp.chain_tip_sha256))
            r=restore_from_pinned(root/"backup.sqlite",root/"restore.sqlite",
                                  pinned,expected_store_id="store-1")
            self.assertEqual(r.read_verified_bytes("batch","row"),raw)

    def test_33_wrong_checkpoint_store_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td);s=EvidenceStore(root/"source.sqlite");s.initialize()
            cp=create_candidate_checkpoint(s,root/"backup.sqlite",
                                           "cp-1","store-1",CHECKPOINT_TIME)
            with self.assertRaises(EvidenceCorrupt):
                verify_backup_against_pinned(root/"backup.sqlite",cp,
                                             expected_store_id="other")

    def test_34_checkpoint_tampered_backup_byte_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td);s=EvidenceStore(root/"source.sqlite");s.initialize()
            cp=create_candidate_checkpoint(s,root/"backup.sqlite",
                                           "cp-1","store-1",CHECKPOINT_TIME)
            raw=(root/"backup.sqlite").read_bytes()
            (root/"tampered.sqlite").write_bytes(raw[:17]+bytes([raw[17]^1])+raw[18:])
            with self.assertRaises(EvidenceCorrupt):
                verify_backup_against_pinned(root/"tampered.sqlite",cp,
                                             expected_store_id="store-1")

    def test_35_history_prefix_one_snapshot_plus_new_suffix(self):
        with TemporaryDirectory() as td:
            root=Path(td);s=EvidenceStore(root/"source.sqlite");s.initialize()
            raw=b"old";old=EvidenceItem("old","fixture",raw,sha256(raw).hexdigest(),
                                         State.QUARANTINED,"UNKNOWN")
            s.append_batch("a",(old,),CHECKPOINT_TIME)
            cp=create_candidate_checkpoint(s,root/"backup.sqlite",
                                           "cp-1","store-1",CHECKPOINT_TIME)
            newraw=b"new"
            new=EvidenceItem("new","fixture",newraw,sha256(newraw).hexdigest(),
                              State.QUARANTINED,"UNVERIFIED")
            s.append_batch("b",(new,),CHECKPOINT_TIME+timedelta(seconds=1),
                           expected_tip_sha256=cp.chain_tip_sha256)
            self.assertEqual(verify_history_prefix(
                s,cp,expected_store_id="store-1")[0],2)

    def test_36_weekly_cache_first_three_windows_synthetic(self):
        s=SyntheticWeeklyChunkStore()
        k=weekly_key()
        res=s.commit(k,tuple(fake(i) for i in range(15)),
                     expected_head=None,observed_at_utc=WEEKLY_NOW)
        self.assertEqual((res.created_windows,res.reused_windows),(3,0))
        self.assertFalse(res.live_cache_approved)

    def test_37_weekly_cache_reuse_is_noop(self):
        s=SyntheticWeeklyChunkStore();k=weekly_key()
        rows=tuple(fake(i) for i in range(15))
        s.commit(k,rows,expected_head=None,observed_at_utc=WEEKLY_NOW)
        x=s.commit(k,rows,expected_head=s.head(k),observed_at_utc=WEEKLY_NOW)
        self.assertEqual((x.created_windows,x.reused_windows),(0,3))
        self.assertFalse(x.manifest_changed)

    def test_38_weekly_cache_stale_writer_denied(self):
        s=SyntheticWeeklyChunkStore();k=weekly_key()
        rows=tuple(fake(i) for i in range(15))
        s.commit(k,rows,expected_head=None,observed_at_utc=WEEKLY_NOW)
        with self.assertRaises(ValueError):
            s.commit(k,rows,expected_head=None,observed_at_utc=WEEKLY_NOW)

    def test_39_weekly_cache_permission_boundary_denied(self):
        with self.assertRaises(PermissionError):
            require_authorized_window_cache()

    def test_40_receipt_has_no_private_root_and_is_deterministic(self):
        self.assertEqual(execute_sixth_eight_runtime(),self.r)
        self.assertEqual(self.r["human_owner_a02_module_dispositions"],0)
        self.assertFalse(self.r["trading_authorized"])


if __name__=="__main__":
    unittest.main()

