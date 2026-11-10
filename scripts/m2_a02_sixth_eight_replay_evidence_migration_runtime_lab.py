"""MST A02 sixth eight distinct ORIGINAL inherited V1 runtime boundaries.

Eight original domain modules execute, with existing test fixture constructors
providing manufactured data only. Linux ephemeral GitHub Actions SQLite files
and in-process weekly-chunk doubles are NOT physical Google Drive market cache.

The checkpoint is self-held within this ONE fixture runner, not an independently
approved external custody head. Green tests cannot grant historical source
rights, V2 ABI signoff, broker authorization or production release.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.replay_batch import replay_frame, replay_sequence
from swing_trading.quality_audit import (
    QualityFindingRegistry, FindingSeverity,
    ResolutionStatus,
)
from swing_trading.legacy_migration import migrate_batch
from swing_trading.migration_archive import archive_migration_batch
from swing_trading.durable_evidence import (
    EvidenceStore, EvidenceItem, EvidenceCorrupt, State, ZERO,
)
from swing_trading.evidence_recovery import backup_verified, restore_verified
from swing_trading.evidence_checkpoint import (
    EvidenceCheckpoint, create_candidate_checkpoint, file_sha256,
    verify_backup_against_pinned, restore_from_pinned, verify_history_prefix,
)
from swing_trading.segmented_cache import (
    SyntheticWeeklyChunkStore, require_authorized_window_cache,
)
from swing_trading.market_data import BarClosure
from swing_trading.source_quality import QualityState, CoverageState

# Existing synthetic test INPUT creators, not V1 module mocks.
from test_replay_batch import m5_fixture
from test_source_quality import candle, m
from test_quality_audit import finding, manifest, at as quality_at
from test_legacy_migration import row as legacy_row, at as legacy_at
from test_migration_archive import sample
from test_evidence_checkpoint import T as CHECKPOINT_TIME
from test_segmented_cache import key as weekly_key, fake, NOW as WEEKLY_NOW

SCHEMA = "mst.a02.sixth-original-v1-replay-evidence-migration-cache.synthetic.no-go.v1"
EIGHT = (
    "replay_batch", "quality_audit", "legacy_migration", "migration_archive",
    "durable_evidence", "evidence_recovery", "evidence_checkpoint",
    "segmented_cache",
)


def _need(value, msg):
    if not value:
        raise AssertionError(msg)


def _denied(action, error, label):
    try:
        action()
    except error:
        return True
    raise AssertionError(label)


def execute_sixth_eight_runtime():
    checks = {}

    # Replay exact retransmissions, new revisions, known-at and verified-at
    # must be distinct. NEVER infer a B/S trade from candle availability.
    m15 = candle()
    m5 = m5_fixture()
    keys = (m5.market_bar_key, m15.market_bar_key)
    frames = replay_sequence(keys, (m5, m15),
                             (m(14), m(18), m(21), m(28)))
    _need(len(frames) == 4
          and frames[0].find(m15.market_bar_key).resolution.reason == "NO_VISIBLE_REVISION"
          and frames[1].find(m5.market_bar_key).resolution.reason == "NO_VISIBLE_REVISION"
          and not frames[2].find(m15.market_bar_key).source_prerequisites_at(m(21))
          and frames[-1].find(m5.market_bar_key).source_prerequisites_at(m(28))
          and frames[-1].find(m15.market_bar_key).source_prerequisites_at(m(28)),
          "REPLAY_USED_UNAVAILABLE_OR_NOT_VERIFIED_SOURCE")
    checks["M5_M15_replay_separate_first_known_retrieval_verification"] = True

    retransmitted = replay_frame((m5.market_bar_key,), (m5,m5,m5), m(30)).bars[0]
    conflicted = replay_frame(
        (m5.market_bar_key,),
        (m5,replace(m5, close=Decimal("11.5"), raw_digest_sha256="c"*64)),
        m(30),
    ).bars[0]
    _need(retransmitted.exact_retransmissions_removed == 2
          and retransmitted.resolution.visible_candidate_count == 1
          and not retransmitted.revision_identity_collision
          and conflicted.revision_identity_collision
          and conflicted.resolution.reason == "SOURCE_OR_REVISION_CONFLICT"
          and conflicted.resolution.selected is None,
          "REPLAY_LATEST_WINS_REPAIRED_CONFLICT_OR_COUNTED_EXACT_RESENDS")
    checks["exact_retransmit_dedup_but_same_revision_diff_payload_conflicts"] = True

    revision = replace(
        m5.observation_revision, source_revision_or_payload_digest="r2",
        first_known_time_utc=m(40), retrieved_at_utc=m(41),
    )
    future = replace(m5, observation_revision=revision,
                     retrieved_at_utc=m(41), verified_at_utc=m(42),
                     close=Decimal("11.5"))
    future_frames = replay_sequence(
        (m5.market_bar_key,), (m5,future),
        (m(30), m(39), m(40), m(50)),
    )
    _need(future_frames[0].bars[0].resolution.selected == m5
          and future_frames[1].bars[0].resolution.selected == m5
          and future_frames[2].bars[0].resolution.reason == "SOURCE_OR_REVISION_CONFLICT"
          and not future_frames[-1].bars[0].source_prerequisites_at(m(50)),
          "FUTURE_REPLAY_CORRECTION_RETROACTIVE_OR_SILENT_OVERRIDE")
    checks["late_revision_never_rewrites_prior_asof_replay_frame"] = True

    # Structural manifest conditions are never equivalent to vendor rights.
    clean = manifest()
    blocking = finding()
    waived = finding(
        resolution_status=ResolutionStatus.WAIVED_WITH_APPROVAL,
        resolution_reference="SELF_REPORTED_FIXTURE_WAIVER",
    )
    reg0 = QualityFindingRegistry()
    reg1 = reg0.append(blocking)
    _need(clean.structural_prerequisites(quality_at(120))
          and reg0.findings == () and reg1.open_blockers() == (blocking,)
          and not replace(clean,quality_findings=(blocking,))
                   .structural_prerequisites(quality_at(120))
          and not replace(clean,quality_findings=(waived,))
                   .structural_prerequisites(quality_at(120))
          and not replace(clean,verified_at_utc=None)
                   .structural_prerequisites(quality_at(120)),
          "QUALITY_MANIFEST_OPEN_BLOCK_OR_WAIVER_PROMOTED_TO_SOURCE")
    checks["quality_append_only_block_and_unverified_waiver_never_release"] = True

    # Legacy "VERIFIED" cannot be upgraded into v1.2 quality. Missing or
    # future/unknown lifecycle is quarantined with the original source bytes.
    migrated = migrate_batch((legacy_row(),), legacy_at(30))
    _need(migrated.counts["staged_unverified"] == 1
          and migrated.counts["quarantined"] == 0
          and migrated.migrated[0].quality_state is QualityState.UNVERIFIED
          and migrated.migrated[0].coverage_state is CoverageState.UNKNOWN
          and not migrated.migrated[0].confirmation_prerequisites(legacy_at(50)),
          "LEGACY_VERIFIED_FALSELY_UPGRADED_TO_V12_CERTIFIED")
    checks["legacy_verified_to_v12_is_staged_unverified_never_trade"] = True

    with TemporaryDirectory(prefix="mst-a02-sixth-inherited-v1-fixture-") as td:
        root=Path(td)
        evidence=EvidenceStore(root/"source_evidence.sqlite")
        evidence.initialize()
        e1,b1=sample(b"\x00synthetic-raw-A\xff",ref="a")
        e2,b2=sample(b"\x00synthetic-raw-B\xfe",ref="b",
                     revision="r2",closure=BarClosure.UNKNOWN)
        archive = archive_migration_batch(
            evidence,"migration-fixture", (e1,e2), (b1,b2),
            legacy_at(30),expected_tip_sha256=ZERO,
        )
        _need(
            archive.record_count == 2
            and archive.migration.counts["staged_unverified"] == 1
            and archive.migration.counts["quarantined"] == 1
            and tuple(x.state for x in archive.receipts)
                == (State.STAGED_UNVERIFIED, State.QUARANTINED)
            and evidence.read_verified_bytes("migration-fixture","a") == b1.raw_bytes
            and evidence.read_verified_bytes("migration-fixture","b") == b2.raw_bytes
            and evidence.verify() == (2,archive.chain_tip_sha256),
            "RAW_MIGRATION_QUARANTINE_OR_BYTES_NOT_PRESERVED",
        )
        checks["raw_migration_mixed_staged_quarantine_keeps_exact_bytes"] = True

        # Negative: caller-provided raw source mismatch must reject whole
        # batch before ANY writes; stale tip must reject a second append.
        e3,b3=sample(b"raw-C",ref="c",revision="r3")
        bad_binding = replace(b3,source_snapshot_id="wrong-fixture-snapshot")
        snapshot_tip=evidence.verify()
        rejects_wrong_binding=_denied(
            lambda: archive_migration_batch(
                evidence,"reject-snapshot",(e3,),(bad_binding,),legacy_at(30),
                expected_tip_sha256=snapshot_tip[1]),
            ValueError,"MIGRATION_WRONG_RAW_SOURCE_BOUND_TO_DIFFERENT_SNAPSHOT",
        )
        rejects_stale_tip=_denied(
            lambda: archive_migration_batch(
                evidence,"reject-stale",(e3,),(b3,),legacy_at(30),
                expected_tip_sha256=ZERO),
            EvidenceCorrupt,"MIGRATION_STALE_EVIDENCE_TIP_ACCEPTED",
        )
        _need(rejects_wrong_binding and rejects_stale_tip
              and evidence.verify()==snapshot_tip,
              "MIGRATION_REJECTED_UPDATE_WROTE_PARTIAL_STATE")
        checks["mismatched_binding_and_stale_tip_never_partially_write"] = True

        # P0.4 recovery and P0.4C checkpoint run against the ACTUAL
        # EvidenceStore containing both staged + quarantined raw bytes.
        checkpoint=create_candidate_checkpoint(
            evidence,root/"checkpoint-backup.sqlite",
            "checkpoint-fixture-1","store-fixture-1",CHECKPOINT_TIME,
        )
        claimed_pin=EvidenceCheckpoint.parse_json(checkpoint.canonical_json())
        _need(claimed_pin==checkpoint
              and checkpoint.record_count==2
              and checkpoint.chain_tip_sha256==archive.chain_tip_sha256
              and file_sha256(root/"checkpoint-backup.sqlite")==checkpoint.backup_sha256
              and verify_backup_against_pinned(
                  root/"checkpoint-backup.sqlite",claimed_pin,
                  expected_store_id="store-fixture-1") == snapshot_tip,
              "CHECKPOINT_LOCAL_PIN_OR_CHAIN_MISMATCH",
        )
        checks["checkpoint_sha_and_chain_match_local_untrusted_pin"] = True
        _need(_denied(
                  lambda:verify_backup_against_pinned(
                      root/"checkpoint-backup.sqlite",claimed_pin,
                      expected_store_id="DIFFERENT"),
                  EvidenceCorrupt,"WRONG_STORE_PIN_ACCEPTED")
              and _denied(
                  lambda:verify_backup_against_pinned(
                      root/"checkpoint-backup.sqlite",
                      replace(claimed_pin,chain_tip_sha256="f"*64),
                      expected_store_id="store-fixture-1"),
                  EvidenceCorrupt,"FORGED_CHAIN_TIP_ACCEPTED"),
              "PIN_STORE_OR_TIP_REJECTED_NOT_DENIED")
        checks["wrong_checkpoint_store_and_tail_denied"] = True

        # Actual evidence_recovery independently exercised; never overwrite.
        recovered=restore_from_pinned(
            root/"checkpoint-backup.sqlite",root/"restored-by-pin.sqlite",
            claimed_pin,expected_store_id="store-fixture-1",
        )
        _need(recovered.verify()==snapshot_tip
              and recovered.read_verified_bytes("migration-fixture","a")==b1.raw_bytes
              and recovered.read_verified_bytes("migration-fixture","b")==b2.raw_bytes
              and _denied(
                  lambda:restore_from_pinned(
                      root/"checkpoint-backup.sqlite",root/"restored-by-pin.sqlite",
                      claimed_pin,expected_store_id="store-fixture-1"),
                  FileExistsError,"RESTORE_OVERWROTE_EXISTING_FILE"),
              "RECOVERY_DID_NOT_PRESERVE_FULL_BINARY_RAW_LINEAGE")
        checks["checkpoint_restore_roundtrip_binary_bytes_no_clobber"] = True

        backup_verified(evidence,root/"backup-no-self-pin.sqlite")
        recovered2=restore_verified(
            root/"backup-no-self-pin.sqlite",root/"restored-direct.sqlite",
        )
        _need(recovered2.verify()==snapshot_tip
              and recovered2.read_verified_bytes("migration-fixture","a")==b1.raw_bytes
              and _denied(
                  lambda:backup_verified(evidence,root/"backup-no-self-pin.sqlite"),
                  FileExistsError,"ONLINE_BACKUP_OVERWROTE_EVIDENCE"),
              "EVIDENCE_ONLINE_SQLITE_BACKUP_NOT_RECOVERABLE")
        checks["online_sqlite_backup_and_restore_are_no_overwrite"] = True

        tampered=root/"tampered-copy.sqlite"
        raw=(root/"checkpoint-backup.sqlite").read_bytes()
        tampered.write_bytes(raw[:17]+bytes([raw[17]^0xff])+raw[18:])
        rejects_tamper=_denied(
            lambda:verify_backup_against_pinned(
                tampered,claimed_pin,expected_store_id="store-fixture-1"),
            EvidenceCorrupt,"CORRUPTED_BACKUP_ACCEPTED",
        )
        _need(rejects_tamper,
              "BACKUP_BYTE_CORRUPTION_DID_NOT_DETECT")
        checks["tampered_backup_byte_rejected_before_restore"] = True

        # Real prefix lock checks old tip with new suffix atomically in one
        # read snapshot, not a cross-run authenticated external witness.
        payload=b"synthetic-future-evidence"
        entry=EvidenceItem(
            "new-row","fixture-source",payload,sha256(payload).hexdigest(),
            State.QUARANTINED,"NOT_VENDOR_AUTHENTICATED",
        )
        count,tip=evidence.append_batch(
            "future-batch",(entry,),CHECKPOINT_TIME+timedelta(minutes=1),
            expected_tip_sha256=checkpoint.chain_tip_sha256,
        )
        _need(count==3 and tip!=checkpoint.chain_tip_sha256
              and verify_history_prefix(
                  evidence,claimed_pin,
                  expected_store_id="store-fixture-1")==(count,tip)
              and verify_backup_against_pinned(
                  root/"checkpoint-backup.sqlite",claimed_pin,
                  expected_store_id="store-fixture-1")==snapshot_tip,
              "HISTORIC_PREFIX_PIN_CHANGED_AFTER_VALID_NEW_SUFFIX")
        checks["pinned_old_prefix_persists_when_new_unapproved_suffix_appended"] = True

        unrelated=EvidenceStore(root/"different-chain.sqlite")
        unrelated.initialize()
        _need(_denied(
            lambda:verify_history_prefix(
                unrelated,claimed_pin,expected_store_id="store-fixture-1"),
            EvidenceCorrupt,"EMPTY_OTHER_STORE_ACCEPTED_AS_PINNED_CHAIN"),
            "EXTERNAL_UNRELATED_STORE_DID_NOT_REJECT_OLD_FLOOR")
        checks["truncated_or_unrelated_evidence_chain_rejected_by_local_pin"] = True

    # C4A in-process weekly segments reuse by UTC Monday storage buckets,
    # never official VN trading-week boundaries or authenticated Drive CAS.
    cache=SyntheticWeeklyChunkStore()
    identity=weekly_key()
    bars=tuple(fake(i) for i in range(15))
    first=cache.commit(identity,bars,expected_head=None,
                       observed_at_utc=WEEKLY_NOW)
    head=cache.head(identity)
    reused=cache.commit(identity,bars,expected_head=head,
                        observed_at_utc=WEEKLY_NOW)
    # The synthetic correction must preserve fixture OHLC invariants.
    modified=fake(1,price="901.5",revision="r2")
    corrected=bars[:1]+(modified,)+bars[2:]
    revision=cache.commit(identity,corrected,
                          expected_head=cache.head(identity),
                          observed_at_utc=WEEKLY_NOW)
    _need(first.created_windows==3
          and first.reused_windows==0 and first.manifest_changed
          and reused.created_windows==0 and reused.reused_windows==3
          and not reused.manifest_changed
          and revision.created_windows==1 and revision.reused_windows==2
          and cache.load(identity,pinned_head=cache.head(identity))==corrected,
          "WEEKLY_WINDOW_UNMODIFIED_REUSE_OR_DIRTY_TAIL_REVISION_DRIFT")
    checks["weekly_chunk_cold_warm_reuse_then_historic_revision_one_window"] = True
    _need(_denied(
          lambda:cache.commit(
              identity,corrected,expected_head=None,observed_at_utc=WEEKLY_NOW),
          ValueError,"SYNTHETIC_STALE_WRITER_ACCEPTED")
          and _denied(lambda:require_authorized_window_cache(),
                      PermissionError,"LOCAL_SEGMENTED_CACHE_AUTHORIZED_REAL_DRIVE"),
          "WEEKLY_LOCAL_CAS_FALSELY_PROMOTED_TO_REAL_CLOUD")
    checks["stale_weekly_writer_denied_but_no_real_drive_access"] = True

    _need(len(checks)==16 and all(checks.values()),
          "SIXTH_EIGHT_EXECUTED_ORIGINAL_RUNTIME_INVARIANTS_FAILED")
    return {
        "schema": SCHEMA,
        "status": "SIXTH_EIGHT_REAL_LEGACY_V1_REPLAY_EVIDENCE_MIGRATION_WEEKLY_GUARDS_PASS_NO_GO",
        "original_upstream_sha": "cd90c1babae8912db31490ad614fc2ad2f868042",
        "protected_main_sha": "4048f91beaaa3410116d97e35896c8b688384e19",
        "original_modules_executed": list(EIGHT),
        "distinct_originals_this_tranche": 8,
        "prior_distinct_originals": 40,
        "cumulative_originals_with_scoped_runtime_qa": 48,
        "originals_not_yet_in_this_tranche_style_review": 15,
        "linked_safety_checks": checks,
        "linked_safety_count": len(checks),
        "synthetic_evidence_checkpoint_count": checkpoint.record_count,
        "synthetic_prefix_with_unapproved_suffix_count": count,
        "synthetic_weekly_windows_first": first.created_windows,
        "synthetic_reused_weekly_windows": reused.reused_windows,
        "synthetic_revised_weekly_windows_created": revision.created_windows,
        "actual_external_evidence_custodian_authenticated": False,
        "vendor_raw_source_bytes_authenticated": False,
        "self_held_checkpoint_is_external_monotonic_floor": False,
        "actual_drive_market_cache_read_write": False,
        "real_multiwriter_server_cas_verified": False,
        "real_provider_market_license_verified": False,
        "original_v1_to_v2_full_behavior_equivalence_approved": False,
        "human_owner_a02_module_dispositions": 0,
        "a03_v2_full_abi_owner_approved": False,
        "g01_g08_independent_security_gates_closed": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=execute_sixth_eight_runtime()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ("linked_safety_checks",)},sort_keys=True))


if __name__=="__main__":
    main()
