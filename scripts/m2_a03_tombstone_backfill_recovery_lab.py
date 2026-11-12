"""MST A03 synthetic-only tombstone/backfill and crash-quarantine protocol.

Build versioned, complete materialization snapshots from the *unchanged* V1
SQLite fixture, cross-check checkpoint EMA20/Wilder ATR14 against an
independent Decimal oracle, and require explicit first-known deletion and
restoration events. All hashes are SELF-ATTESTED and in-process only.

No real vendor sources, Google Drive cache, protected witness, independent
signer, durable rollback floor, real two-identity CAS or production rights.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal as D
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.m2_a02_incremental_cache_oracle_lab import _apply, bar, instant
from scripts.m2_a03_v2_cache_consumer_contract import (
    FixtureV2ConsumerScope, _hash, _hex_sha, _utc,
    fixture_scope, preview_v2_consumer,
)
from scripts.m2_a03_v2_full_policy_manifest_draft import (
    MaterializedBarRevision,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore

SCHEMA = "mst.a03.tombstone-backfill-recovery.synthetic.v1"
STAGES = ("COLD", "TOMBSTONE", "BACKFILL", "WARM")
EVENTS = ("TOMBSTONE", "BACKFILL")


@dataclass(frozen=True)
class SyntheticRevisionEvent:
    action: str
    bar_start_utc: datetime
    first_known_utc: datetime
    previous_content_sha256: str
    restored_content_sha256: str | None = None
    restored_revision_id: str | None = None

    def __post_init__(self):
        if type(self.action) is not str or self.action not in EVENTS:
            raise ValueError("UNKNOWN_SOURCE_EVENT_KIND")
        if _utc(self.bar_start_utc) >= _utc(self.first_known_utc):
            raise ValueError("EVENT_FIRST_KNOWN_MUST_FOLLOW_BAR_START")
        _hex_sha(self.previous_content_sha256)
        if self.action == "TOMBSTONE":
            if self.restored_content_sha256 is not None or self.restored_revision_id is not None:
                raise ValueError("TOMBSTONE_CANNOT_CARRY_RESTORED_PAYLOAD")
        else:
            _hex_sha(self.restored_content_sha256)
            if type(self.restored_revision_id) is not str or not self.restored_revision_id:
                raise ValueError("BACKFILL_REQUIRES_TYPED_REVISION")

    def canonical(self):
        return {
            "action": self.action,
            "bar_start_utc": self.bar_start_utc.isoformat(),
            "first_known_utc": self.first_known_utc.isoformat(),
            "previous_content_sha256": self.previous_content_sha256,
            "restored_content_sha256": self.restored_content_sha256,
            "restored_revision_id": self.restored_revision_id,
            "evidence_type": "SYNTHETIC_UNATTESTED_EVENT_ONLY",
        }


@dataclass(frozen=True)
class SyntheticMaterializedFrame:
    generation: int
    parent_digest: str | None
    stage: str
    as_of_utc: datetime
    scope_binding_sha256: str
    partition_sha256: str
    legacy_identity_sha256: str
    policy_versions: tuple[tuple[str, str], ...]
    revisions: tuple[MaterializedBarRevision, ...]
    bar_revisions_digest: str
    ema_atr_digest: str
    event: SyntheticRevisionEvent | None = None

    def __post_init__(self):
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("INVALID_FRAME_GENERATION")
        if (self.generation == 1) != (self.parent_digest is None):
            raise ValueError("FRAME_GENESIS_PARENT_INCONSISTENT")
        if self.parent_digest is not None:
            _hex_sha(self.parent_digest)
        for digest in (
            self.scope_binding_sha256, self.partition_sha256,
            self.legacy_identity_sha256, self.bar_revisions_digest,
            self.ema_atr_digest,
        ):
            _hex_sha(digest)
        _utc(self.as_of_utc)
        if type(self.stage) is not str or self.stage not in STAGES:
            raise ValueError("UNKNOWN_FRAME_STAGE")
        if self.generation == 1 and self.stage != "COLD":
            raise ValueError("GENESIS_MUST_BE_COLD")
        if type(self.policy_versions) is not tuple or len(self.policy_versions) != 8:
            raise ValueError("COMPLETE_EIGHT_POLICY_VERSIONS_REQUIRED")
        if tuple(sorted(self.policy_versions)) != self.policy_versions or (
            set(k for k, _ in self.policy_versions) != {
                "rights", "resolution", "quality", "adjustment",
                "calendar", "aggregation", "indicator", "indicator_parameters",
            }
        ):
            raise ValueError("FULL_POLICY_FIELDS_MUST_BE_CANONICAL")
        if any(type(k) is not str or type(v) is not str or not v for k, v in self.policy_versions):
            raise ValueError("FULL_POLICY_VALUES_REQUIRED")
        if type(self.revisions) is not tuple or not self.revisions or any(
            type(x) is not MaterializedBarRevision for x in self.revisions
        ):
            raise TypeError("TYPED_NONEMPTY_MATERIALIZATION_REQUIRED")
        starts = [x.start_utc for x in self.revisions]
        if starts != sorted(set(starts)):
            raise ValueError("UNSORTED_OR_DUPLICATE_MATERIALIZED_BAR")
        if any(x.first_known_utc > self.as_of_utc for x in self.revisions):
            raise ValueError("FUTURE_KNOWN_MATERIALIZATION_DENIED")
        if _hash([x.canonical() for x in self.revisions]) != self.bar_revisions_digest:
            raise ValueError("MATERIALIZED_REVISION_DIGEST_MISMATCH")
        if self.event is not None and type(self.event) is not SyntheticRevisionEvent:
            raise TypeError("TYPED_REVISION_EVENT_REQUIRED")
        if (self.stage in EVENTS) != (self.event is not None):
            raise ValueError("STAGED_EVENT_OR_EMPTY_EVENT_MISMATCH")
        if self.event is not None and (
            self.event.action != self.stage or
            self.event.first_known_utc > self.as_of_utc
        ):
            raise ValueError("EVENT_STAGE_OR_ASOF_MISMATCH")

    def canonical(self):
        return {
            "schema": SCHEMA, "test_only": True,
            "generation": self.generation, "parent_digest": self.parent_digest,
            "stage": self.stage, "as_of_utc": self.as_of_utc.isoformat(),
            "scope_binding_sha256": self.scope_binding_sha256,
            "partition_sha256": self.partition_sha256,
            "legacy_identity_sha256": self.legacy_identity_sha256,
            "policy_versions": dict(self.policy_versions),
            "materialized_revisions": [x.canonical() for x in self.revisions],
            "bar_revisions_digest": self.bar_revisions_digest,
            "ema_atr_digest": self.ema_atr_digest,
            "event": None if self.event is None else self.event.canonical(),
        }

    @property
    def digest(self):
        return _hash(self.canonical())


def create_frame(
    store: SyntheticIncrementalStore,
    scope: FixtureV2ConsumerScope,
    *, at: datetime, stage: str,
    parent: SyntheticMaterializedFrame | None,
    event: SyntheticRevisionEvent | None,
) -> SyntheticMaterializedFrame:
    """Observe real current V1 materialization and independent indicator oracle."""
    preview = preview_v2_consumer(store, scope, as_of_utc=at, proposed_head=None)
    bars = store.read_bars(scope.legacy)
    frame = SyntheticMaterializedFrame(
        generation=1 if parent is None else parent.generation + 1,
        parent_digest=None if parent is None else parent.digest,
        stage=stage, as_of_utc=_utc(at),
        scope_binding_sha256=scope.binding_sha256,
        partition_sha256=scope.candidate.digest,
        legacy_identity_sha256=scope.legacy.fingerprint,
        policy_versions=tuple(sorted(preview["legacy_policy_versions"].items())),
        revisions=tuple(MaterializedBarRevision(
            b.start_utc, b.end_utc, b.first_known_utc,
            b.revision, b.normalized_digest,
        ) for b in bars),
        bar_revisions_digest=preview["v1_bar_revisions_digest"],
        ema_atr_digest=preview["v1_ema20_atr14_checkpoint_digest"],
        event=event,
    )
    return frame


def verify_local_event_chain(chain: tuple[SyntheticMaterializedFrame, ...]) -> dict:
    """Validate FULL caller-supplied history; NEVER certify durable provenance."""
    if type(chain) is not tuple or not chain:
        raise ValueError("NONEMPTY_LOCAL_CHAIN_REQUIRED")
    genesis = chain[0]
    if type(genesis) is not SyntheticMaterializedFrame or (
        genesis.generation != 1 or genesis.stage != "COLD" or
        genesis.parent_digest is not None
    ):
        raise ValueError("FULL_LOCAL_GENESIS_REQUIRED")
    prior_tombstones = {}
    for idx, frame in enumerate(chain):
        if type(frame) is not SyntheticMaterializedFrame:
            raise TypeError("TYPED_CHAIN_FRAME_REQUIRED")
        if frame.generation != idx + 1:
            raise ValueError("GENERATION_SKIP_OR_REWIND_DENIED")
        if (frame.scope_binding_sha256 != genesis.scope_binding_sha256
                or frame.partition_sha256 != genesis.partition_sha256
                or frame.legacy_identity_sha256 != genesis.legacy_identity_sha256
                or frame.policy_versions != genesis.policy_versions):
            raise ValueError("FULL_RIGHTS_OR_POLICY_SCOPE_DRIFT_DENIED")
        if idx == 0:
            continue
        parent = chain[idx - 1]
        if frame.parent_digest != parent.digest:
            raise ValueError("PARENT_DIGEST_MISMATCH")
        if frame.as_of_utc <= parent.as_of_utc:
            raise ValueError("LOCAL_FRAME_TIME_REWIND_DENIED")
        before = {x.start_utc: x for x in parent.revisions}
        after = {x.start_utc: x for x in frame.revisions}
        gone = set(before) - set(after)
        added = set(after) - set(before)
        modified = {
            k for k in set(before) & set(after) if before[k] != after[k]
        }
        if modified:
            raise ValueError("UNVERSIONED_EXISTING_BAR_REWRITE_DENIED")
        if frame.stage == "WARM":
            if gone or added or frame.event is not None or (
                frame.ema_atr_digest != parent.ema_atr_digest or
                frame.bar_revisions_digest != parent.bar_revisions_digest
            ):
                raise ValueError("WARM_MUST_PRESERVE_FULL_MATERIALIZATION")
            continue
        event = frame.event
        if event is None or event.action != frame.stage:
            raise ValueError("TYPED_EVENT_REQUIRED_FOR_SOURCE_MUTATION")
        if not (parent.as_of_utc < event.first_known_utc <= frame.as_of_utc):
            raise ValueError("RETROACTIVE_OR_FUTURE_SOURCE_EVENT_DENIED")
        if frame.stage == "TOMBSTONE":
            if gone != {event.bar_start_utc} or added:
                raise ValueError("DELETE_MUST_MATCH_EXACT_ONE_TOMBSTONE_EVENT")
            prior = before[event.bar_start_utc]
            if prior.content_sha256 != event.previous_content_sha256:
                raise ValueError("TOMBSTONE_PRIOR_CONTENT_SHA_MISMATCH")
            if event.bar_start_utc in prior_tombstones:
                raise ValueError("DUPLICATE_PENDING_TOMBSTONE_DENIED")
            prior_tombstones[event.bar_start_utc] = event
            if frame.ema_atr_digest == parent.ema_atr_digest:
                raise ValueError("DELETE_MUST_INVALIDATE_INDICATOR_CHECKPOINTS")
        elif frame.stage == "BACKFILL":
            if added != {event.bar_start_utc} or gone:
                raise ValueError("RESTORE_MUST_MATCH_EXACT_ONE_BACKFILL_EVENT")
            tombstone = prior_tombstones.get(event.bar_start_utc)
            if tombstone is None:
                raise ValueError("BACKFILL_WITHOUT_PRIOR_TOMBSTONE_DENIED")
            if (tombstone.previous_content_sha256 != event.previous_content_sha256
                    or event.first_known_utc <= tombstone.first_known_utc):
                raise ValueError("BACKFILL_TOMBSTONE_CAUSAL_LINK_MISMATCH")
            restored = after[event.bar_start_utc]
            if (restored.content_sha256 != event.restored_content_sha256
                    or restored.revision_id != event.restored_revision_id
                    or restored.first_known_utc != event.first_known_utc):
                raise ValueError("BACKFILL_NEW_REVISION_NOT_BOUND")
            if frame.ema_atr_digest == parent.ema_atr_digest:
                raise ValueError("BACKFILL_MUST_RECOMPUTE_INDICATOR_TAIL")
            del prior_tombstones[event.bar_start_utc]
        else:
            raise ValueError("UNKNOWN_MUTATING_FRAME_STAGE")
    return {
        "schema": SCHEMA,
        "status": "LOCAL_TOMBSTONE_BACKFILL_CAUSAL_CHAIN_VALID_UNATTESTED",
        "committed_generations": len(chain),
        "last_local_head_digest": chain[-1].digest,
        "pending_tombstones": len(prior_tombstones),
        "complete_full_rights_identity_bound": True,
        "first_known_tombstone_and_backfill_checked": True,
        "versioned_history_local_only": True,
        "independently_authenticated_source_receipts": False,
        "independent_signer_or_remote_floor_proven": False,
        "real_two_writer_cas_proven": False,
        "physical_google_drive_market_cache_written": False,
        "production_recovery_approved": False,
        "trading_authorized": False,
    }


class LocalCrashReviewJournal:
    """Volatile in-process review journal, NOT an independent recovery service."""

    def __init__(self, genesis: SyntheticMaterializedFrame) -> None:
        verify_local_event_chain((genesis,))
        self._committed = (genesis,)
        self._pending = None

    @property
    def head(self):
        return self._committed[-1]

    def prepare(self, candidate: SyntheticMaterializedFrame) -> None:
        if self._pending is not None:
            raise ValueError("ONE_PENDING_CANDIDATE_AT_A_TIME")
        verify_local_event_chain((*self._committed, candidate))
        self._pending = candidate

    def commit(self, store: SyntheticIncrementalStore,
               scope: FixtureV2ConsumerScope) -> None:
        if self._pending is None:
            raise ValueError("NO_PREPARED_CANDIDATE")
        now = self._pending.as_of_utc
        preview = preview_v2_consumer(
            store, scope, as_of_utc=now, proposed_head=None,
        )
        if (preview["all_legacy_policies_bound_sha256"]
                != self._pending.scope_binding_sha256
                or preview["v1_bar_revisions_digest"]
                != self._pending.bar_revisions_digest
                or preview["v1_ema20_atr14_checkpoint_digest"]
                != self._pending.ema_atr_digest):
            raise PermissionError("LOCAL_STORE_DIVERGED_FROM_PENDING_MANIFEST")
        verify_local_event_chain((*self._committed, self._pending))
        self._committed += (self._pending,)
        self._pending = None

    def recover_review_only(self, store: SyntheticIncrementalStore,
                            scope: FixtureV2ConsumerScope,
                            *, now: datetime):
        """Discard prepared candidate, deny dirty DB, no auto-repair or publish."""
        snapshot = preview_v2_consumer(
            store, scope, as_of_utc=now, proposed_head=None,
        )
        expected = self.head
        if (snapshot["all_legacy_policies_bound_sha256"] != expected.scope_binding_sha256
                or snapshot["v1_bar_revisions_digest"] != expected.bar_revisions_digest
                or snapshot["v1_ema20_atr14_checkpoint_digest"] != expected.ema_atr_digest):
            raise PermissionError("UNCOMMITTED_SQLITE_MATERIALIZATION_QUARANTINED")
        verify_local_event_chain(self._committed)
        discarded = self._pending is not None
        self._pending = None
        return {
            "status": "LOCAL_PREPARED_INTENT_DISCARDED_COMMITTED_FIXTURE_UNCHANGED",
            "committed_generation": expected.generation,
            "committed_digest": expected.digest,
            "uncommitted_candidate_discarded": discarded,
            "durable_cross_run_recovery_proven": False,
            "production_auto_repair_authorized": False,
        }


def build_synthetic_fixture():
    """Use real V1 SQLite deletion, backfill, and warm read on GH runner."""
    with TemporaryDirectory(prefix="mst-a03-tombstone-review-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "temporary.sqlite")
        store.initialize()
        scope = fixture_scope()
        key = scope.legacy
        _apply(store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = create_frame(
            store, scope, at=instant(20), stage="COLD",
            parent=None, event=None,
        )
        target = cold.revisions[11]
        tomb = SyntheticRevisionEvent(
            "TOMBSTONE", target.start_utc, instant(30),
            target.content_sha256,
        )
        update = _apply(store, key, (bar(10), bar(12)),
                        now=30, start=10, end=13, complete=True)
        if update.deleted != 1 or update.indicator_bars_recomputed != 8:
            raise AssertionError("V1_REAL_SQLITE_TOMBSTONE_DIRTY_TAIL_DRIFT")
        deleted = create_frame(
            store, scope, at=instant(30), stage="TOMBSTONE",
            parent=cold, event=tomb,
        )
        journal = LocalCrashReviewJournal(cold)
        journal.prepare(deleted)
        # Crash *before* local commit; actual SQLite now differs from committed.
        try:
            journal.recover_review_only(store, scope, now=instant(30))
        except PermissionError as e:
            if "QUARANTINED" not in str(e):
                raise
        else:
            raise AssertionError("UNCOMMITTED_DB_CHANGED_WITHOUT_HEAD_WAS_ADOPTED")
        journal.commit(store, scope)
        restored_bar = bar(11, close=D("150"), revision="r2")
        from dataclasses import replace
        restored_bar = replace(restored_bar, first_known_utc=instant(40))
        rest_event = SyntheticRevisionEvent(
            "BACKFILL", target.start_utc, instant(40),
            target.content_sha256,
            restored_bar.normalized_digest, restored_bar.revision,
        )
        update = _apply(store, key, (restored_bar,),
                        now=40, start=11, end=12)
        if update.inserted != 1 or update.indicator_bars_recomputed != 9:
            raise AssertionError("V1_REAL_SQLITE_BACKFILL_DIRTY_TAIL_DRIFT")
        backfilled = create_frame(
            store, scope, at=instant(40), stage="BACKFILL",
            parent=deleted, event=rest_event,
        )
        journal.prepare(backfilled)
        journal.commit(store, scope)
        # Prepare an unchanged warm snapshot but crash before any write.
        warm = create_frame(
            store, scope, at=instant(41), stage="WARM",
            parent=backfilled, event=None,
        )
        journal.prepare(warm)
        recovered = journal.recover_review_only(
            store, scope, now=instant(41),
        )
        if journal.head != backfilled or not recovered["uncommitted_candidate_discarded"]:
            raise AssertionError("UNCOMMITTED_WARM_HEAD_PROMOTED_AFTER_CRASH")
        journal.prepare(warm)
        journal.commit(store, scope)
        result = verify_local_event_chain((cold, deleted, backfilled, warm))
        return {
            **result,
            "stages": [
                {
                    "stage": f.stage, "generation": f.generation,
                    "bar_count": len(f.revisions), "local_digest": f.digest,
                    "parent_digest": f.parent_digest,
                    "bar_revisions_digest": f.bar_revisions_digest,
                    "ema_atr_digest": f.ema_atr_digest,
                }
                for f in (cold, deleted, backfilled, warm)
            ],
            "v1_deleted_bars": 1,
            "v1_delete_indicator_tail_recomputed": 8,
            "v1_backfilled_bars": 1,
            "v1_backfill_indicator_tail_recomputed": 9,
            "uncommitted_dirty_sqlite_quarantined": True,
            "clean_prepared_intent_discarded": True,
            "all_indicator_snapshots_independent_oracle_verified": True,
            "external_owner_evidence_missing": True,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = build_synthetic_fixture()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
