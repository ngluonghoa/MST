"""MST A03 synthetic PREPARED/COMMITTED/READER-VISIBLE read-barrier lab.

All simulated "cloud" objects are volatile Python memory on GitHub Actions.
Receipts, payload SHA256 and floors are SELF-ATTESTED; they do not constitute
Google Drive CAS, externally signed vendor source, independent writer identity,
non-resettable rollback floor, durable recovery, release or trading permission.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal as D
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.m2_a02_incremental_cache_oracle_lab import _apply, bar, instant
from scripts.m2_a03_v2_cache_consumer_contract import _hash, _hex_sha, fixture_scope
from scripts.m2_a03_tombstone_backfill_recovery_lab import (
    SyntheticMaterializedFrame, SyntheticRevisionEvent,
    create_frame, verify_local_event_chain,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore

SCHEMA = "mst.a03.reader-visibility-barrier.synthetic.v1"


@dataclass(frozen=True)
class Prepared:
    generation: int
    frame_sha256: str
    parent_sha256: str | None
    rights_scope_sha256: str

    @property
    def sha256(self) -> str:
        return _hash({
            "schema": SCHEMA, "phase": "PREPARED",
            "generation": self.generation, "frame": self.frame_sha256,
            "parent": self.parent_sha256, "rights": self.rights_scope_sha256,
        })


@dataclass(frozen=True)
class Committed:
    prepared: Prepared

    @property
    def sha256(self) -> str:
        return _hash({
            "schema": SCHEMA, "phase": "COMMITTED",
            "prepared_sha256": self.prepared.sha256,
        })


@dataclass(frozen=True)
class Visible:
    generation: int
    frame_sha256: str
    commit_sha256: str

    @classmethod
    def from_commit(cls, receipt: Committed) -> "Visible":
        return cls(receipt.prepared.generation, receipt.prepared.frame_sha256,
                   receipt.sha256)


@dataclass(frozen=True)
class Observed:
    """One caller-supplied synthetic snapshot; NOT an atomic remote Drive read."""
    visible: Visible | None
    frames: tuple[SyntheticMaterializedFrame, ...]
    commits: tuple[Committed, ...]


class SyntheticPublisher:
    """Three-phase, review-only state model; no remote bytes or actual CAS."""

    def __init__(self, genesis: SyntheticMaterializedFrame):
        verify_local_event_chain((genesis,))
        self.published = (genesis,)
        self.objects: dict[str, SyntheticMaterializedFrame] = {genesis.digest: genesis}
        initial = Prepared(1, genesis.digest, None, genesis.scope_binding_sha256)
        self.commits = {1: Committed(initial)}
        self.visible = Visible.from_commit(self.commits[1])
        self.pending: tuple[Prepared, SyntheticMaterializedFrame] | None = None
        self.in_doubt = False

    def observe(self) -> Observed:
        """Simulate a coherent read; tests may replace fields to mimic stale/torn I/O."""
        return Observed(
            self.visible, self.published,
            tuple(self.commits[x.generation] for x in self.published),
        )

    def prepare(self, frame: SyntheticMaterializedFrame) -> Prepared:
        if self.in_doubt:
            raise PermissionError("UNRESOLVED_COMMITTED_NOT_VISIBLE_QUARANTINE")
        if self.pending is not None:
            raise ValueError("ONLY_ONE_PREPARED_GENERATION")
        if len(self.commits) != len(self.published):
            raise PermissionError("UNPUBLISHED_COMMIT_REQUIRES_OWNER_RECOVERY")
        verify_local_event_chain((*self.published, frame))
        if frame.generation != self.visible.generation + 1:
            raise ValueError("PREPARE_MUST_EXTEND_VISIBLE_HEAD")
        pending = Prepared(
            frame.generation, frame.digest, frame.parent_digest,
            frame.scope_binding_sha256,
        )
        self.pending = (pending, frame)
        return pending

    def materialize(self) -> None:
        """Simulated object write. Preparing alone never exposes a payload."""
        if self.pending is None:
            raise ValueError("NO_PREPARED_MANIFEST")
        self.objects[self.pending[0].frame_sha256] = self.pending[1]

    def commit(self) -> Committed:
        if self.pending is None:
            raise ValueError("NO_PREPARED_MANIFEST")
        prepared, frame = self.pending
        materialized = self.objects.get(prepared.frame_sha256)
        if materialized is None or materialized != frame or materialized.digest != prepared.frame_sha256:
            raise PermissionError("MATERIALIZED_PAYLOAD_MISSING_OR_TAMPERED")
        if prepared.parent_sha256 != self.published[-1].digest:
            raise PermissionError("PREPARED_PARENT_NOT_VISIBLE_HEAD")
        verify_local_event_chain((*self.published, materialized))
        receipt = Committed(prepared)
        if prepared.generation in self.commits:
            raise ValueError("COMMIT_GENERATION_ALREADY_EXISTS")
        self.commits[prepared.generation] = receipt
        return receipt

    def publish_visible(self) -> Visible:
        if self.pending is None:
            raise PermissionError("NO_ACTIVE_PREPARED_INTENT_FOR_VISIBILITY")
        prepared, frame = self.pending
        commit = self.commits.get(prepared.generation)
        if commit is None or commit.prepared != prepared:
            raise PermissionError("VISIBLE_REQUIRES_MATCHING_COMMIT_RECEIPT")
        materialized = self.objects.get(prepared.frame_sha256)
        if materialized is None or materialized != frame or materialized.digest != prepared.frame_sha256:
            raise PermissionError("VISIBLE_REQUIRES_EXACT_PAYLOAD_READBACK")
        verify_local_event_chain((*self.published, materialized))
        self.published += (materialized,)
        self.visible = Visible.from_commit(commit)
        self.pending = None
        return self.visible

    def simulated_crash(self) -> None:
        """Lose volatile intent; never auto-promote or repair an orphan commit."""
        if self.pending is not None and self.pending[0].generation in self.commits:
            self.in_doubt = True
        self.pending = None


class SyntheticReader:
    """Per-session floor: useful against stale reads, RESETTABLE by caller."""

    def __init__(self, pinned_genesis_sha256: str, rights_scope_sha256: str):
        _hex_sha(pinned_genesis_sha256)
        _hex_sha(rights_scope_sha256)
        self.genesis_sha256 = pinned_genesis_sha256
        self.rights_scope_sha256 = rights_scope_sha256
        self.floor_generation = 0
        self.floor_frame_sha256: str | None = None

    def admit(self, observed: Observed, *, require_generation: int = 1) -> dict:
        if type(observed) is not Observed or type(observed.visible) is not Visible:
            raise PermissionError("NO_READER_VISIBLE_HEAD")
        head = observed.visible
        if type(require_generation) is not int or require_generation < 1:
            raise ValueError("INVALID_REQUIRED_GENERATION")
        if head.generation < require_generation:
            raise PermissionError("REQUIRED_READER_VISIBLE_GENERATION_ABSENT")
        if head.generation < self.floor_generation:
            raise PermissionError("STALE_READ_BELOW_SESSION_FLOOR")
        frames = observed.frames
        receipts = observed.commits
        if (type(frames) is not tuple or len(frames) != head.generation
                or type(receipts) is not tuple or len(receipts) != head.generation):
            raise PermissionError("INCOMPLETE_VISIBLE_CHAIN_OR_RECEIPTS")
        if frames[0].digest != self.genesis_sha256:
            raise PermissionError("PINNED_GENESIS_MISMATCH")
        if frames[0].scope_binding_sha256 != self.rights_scope_sha256:
            raise PermissionError("RIGHTS_SCOPE_MISMATCH")
        try:
            verify_local_event_chain(frames)
        except (ValueError, TypeError) as exc:
            raise PermissionError("VISIBLE_SOURCE_LINEAGE_INVALID") from exc
        for gen, (frame, committed) in enumerate(zip(frames, receipts), 1):
            if type(committed) is not Committed or type(committed.prepared) is not Prepared:
                raise PermissionError("UNTYPED_COMMIT_RECEIPT")
            p = committed.prepared
            if (p.generation != gen or p.frame_sha256 != frame.digest
                    or p.parent_sha256 != frame.parent_digest
                    or p.rights_scope_sha256 != self.rights_scope_sha256):
                raise PermissionError("COMMIT_RECEIPT_DOES_NOT_BIND_FRAME")
        tail = receipts[-1]
        if (head.frame_sha256 != frames[-1].digest or
                head.commit_sha256 != tail.sha256):
            raise PermissionError("VISIBLE_POINTER_WITHOUT_EXACT_COMMIT")
        if self.floor_generation:
            anchored = frames[self.floor_generation - 1]
            if anchored.digest != self.floor_frame_sha256:
                raise PermissionError("SESSION_FLOOR_FORK_OR_REWRITE")
        self.floor_generation = head.generation
        self.floor_frame_sha256 = head.frame_sha256
        return {
            "status": "SYNTHETIC_READER_VISIBLE_ADMITTED_NO_EXTERNAL_TRUST",
            "generation": head.generation,
            "frame_sha256": head.frame_sha256,
            "rights_scope_sha256": self.rights_scope_sha256,
            "session_floor_only": True,
            "independent_witness_or_signer": False,
            "real_drive_atomic_snapshot": False,
            "real_server_cas": False,
            "durable_cross_run_rollback_floor": False,
            "vendor_source_rights_verified": False,
            "production_reader_authorized": False,
            "trading_authorized": False,
        }


def real_v1_synthetic_frames() -> tuple[SyntheticMaterializedFrame, ...]:
    """Retain the existing four-stage REAL V1 temporary SQLite/Decimal oracle."""
    with TemporaryDirectory(prefix="mst-a03-readbarrier-gh-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "sqlite.db")
        store.initialize()
        scope = fixture_scope()
        _apply(store, scope.legacy, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = create_frame(store, scope, at=instant(20),
                            stage="COLD", parent=None, event=None)
        prior = cold.revisions[11]
        tomb = SyntheticRevisionEvent(
            "TOMBSTONE", prior.start_utc, instant(30), prior.content_sha256,
        )
        delta = _apply(store, scope.legacy, (bar(10), bar(12)), now=30,
                       start=10, end=13, complete=True)
        if delta.deleted != 1 or delta.indicator_bars_recomputed != 8:
            raise AssertionError("SOURCE_SQLITE_TOMBSTONE_PARITY_DRIFT")
        deleted = create_frame(store, scope, at=instant(30),
                               stage="TOMBSTONE", parent=cold, event=tomb)
        restored = replace(bar(11, close=D("150"), revision="r2"),
                           first_known_utc=instant(40))
        event = SyntheticRevisionEvent(
            "BACKFILL", prior.start_utc, instant(40),
            prior.content_sha256, restored.normalized_digest, "r2",
        )
        delta = _apply(store, scope.legacy, (restored,), now=40,
                       start=11, end=12)
        if delta.inserted != 1 or delta.indicator_bars_recomputed != 9:
            raise AssertionError("SOURCE_SQLITE_BACKFILL_PARITY_DRIFT")
        backfilled = create_frame(store, scope, at=instant(40),
                                  stage="BACKFILL", parent=deleted, event=event)
        warm = create_frame(store, scope, at=instant(41),
                            stage="WARM", parent=backfilled, event=None)
        frames = (cold, deleted, backfilled, warm)
        verify_local_event_chain(frames)
        return frames


def run_lab() -> dict:
    frames = real_v1_synthetic_frames()
    pub = SyntheticPublisher(frames[0])
    reader = SyntheticReader(frames[0].digest, frames[0].scope_binding_sha256)
    first = reader.admit(pub.observe())
    transitions = []
    for frame in frames[1:]:
        pub.prepare(frame)
        try:
            reader.admit(pub.observe(), require_generation=frame.generation)
        except PermissionError as exc:
            if "REQUIRED_READER_VISIBLE" not in str(exc):
                raise
        else:
            raise AssertionError("PREPARED_FRAME_WAS_READ")
        pub.materialize()
        pub.commit()
        try:
            reader.admit(pub.observe(), require_generation=frame.generation)
        except PermissionError as exc:
            if "REQUIRED_READER_VISIBLE" not in str(exc):
                raise
        else:
            raise AssertionError("COMMITTED_UNPUBLISHED_FRAME_WAS_READ")
        pub.publish_visible()
        admitted = reader.admit(pub.observe(), require_generation=frame.generation)
        transitions.append({
            "phase": "PREPARED_COMMITTED_READER_VISIBLE",
            "generation": frame.generation, "stage": frame.stage,
            "admitted_generation": admitted["generation"],
        })
    stale = SyntheticPublisher(frames[0]).observe()
    try:
        reader.admit(stale)
    except PermissionError as exc:
        if "STALE_READ" not in str(exc):
            raise
    else:
        raise AssertionError("STALE_SESSION_READ_NOT_FENCED")

    # Crash after prepare/object and before commit: orphan is not visible.
    uncommitted = SyntheticPublisher(frames[0])
    uncommitted.prepare(frames[1])
    uncommitted.materialize()
    uncommitted.simulated_crash()
    assert uncommitted.observe().visible.generation == 1
    # Crash after commit but before visibility: remains quarantined.
    orphan = SyntheticPublisher(frames[0])
    orphan.prepare(frames[1])
    orphan.materialize()
    orphan.commit()
    orphan.simulated_crash()
    try:
        orphan.publish_visible()
    except PermissionError:
        pass
    else:
        raise AssertionError("ORPHAN_COMMIT_AUTO_PROMOTED")
    assert orphan.in_doubt and orphan.observe().visible.generation == 1

    return {
        "schema": SCHEMA,
        "verdict": "PASS_SYNTHETIC_ONLY_NOT_PRODUCTION_AUTHORIZATION",
        "v1_frames": 4,
        "readbarrier_transitions": transitions,
        "prepared_only_hidden": True,
        "committed_not_visible_hidden": True,
        "stale_session_read_fenced": True,
        "prepare_crash_not_promoted": True,
        "commit_crash_quarantined_not_promoted": True,
        "oracle_source": "UNCHANGED_REAL_V1_TEMP_SQLITE_DECIMAL_EMA20_ATR14",
        "signed_source_witness_or_external_floor": False,
        "real_google_drive_cas_or_bytes": False,
        "owner_release_or_trading": False,
        "final_review_only_generation": first["generation"] + len(transitions),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = run_lab()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
