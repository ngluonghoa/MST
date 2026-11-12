"""MST A03 two-reader/two-writer synthetic interleaving and reset falsification.

This is a **single-process** race explorer over the *unchanged* V1 SQLite /
independent Decimal EMA20-ATR14 synthetic frames. Actor labels are strings,
not authenticated principals. The in-memory sequencer is NOT a remote
linearizable compare-and-swap. Separate replicas can elect conflicting heads.
No physical Drive data, GitHub ref mutation, vendor rights or production IO.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
from pathlib import Path

from scripts.m2_a02_incremental_cache_oracle_lab import instant
from scripts.m2_a03_v2_cache_consumer_contract import _hex_sha
from scripts.m2_a03_reader_visibility_barrier_lab import (
    Observed, SyntheticPublisher, SyntheticReader, real_v1_synthetic_frames,
)
from scripts.m2_a03_tombstone_backfill_recovery_lab import (
    SyntheticMaterializedFrame, verify_local_event_chain,
)

SCHEMA = "mst.a03.dual-reader-writer-race.synthetic.v1"


@dataclass(frozen=True)
class WriterClaim:
    """Observed-head hint, NEVER a credential or a remote server CAS lease."""

    actor_label: str
    expected_generation: int
    expected_frame_sha256: str
    candidate_frame_sha256: str

    def __post_init__(self):
        if type(self.actor_label) is not str or not self.actor_label.strip():
            raise ValueError("SYNTHETIC_WRITER_ACTOR_LABEL_REQUIRED")
        if type(self.expected_generation) is not int or self.expected_generation < 1:
            raise ValueError("INVALID_EXPECTED_GENERATION")
        _hex_sha(self.expected_frame_sha256)
        _hex_sha(self.candidate_frame_sha256)

    @classmethod
    def from_observation(
        cls, actor_label: str, observed: Observed,
        candidate: SyntheticMaterializedFrame,
    ) -> "WriterClaim":
        if type(observed) is not Observed or observed.visible is None:
            raise PermissionError("CLAIM_REQUIRES_VISIBLE_OBSERVATION")
        if type(candidate) is not SyntheticMaterializedFrame:
            raise TypeError("CLAIM_REQUIRES_TYPED_FRAME")
        return cls(actor_label, observed.visible.generation,
                   observed.visible.frame_sha256, candidate.digest)


class SingleMemorySequencer:
    """Exactly one active writer in ONE memory image; no distributed guarantee."""

    def __init__(self, genesis: SyntheticMaterializedFrame):
        self.publisher = SyntheticPublisher(genesis)
        self.active_actor: str | None = None

    def observe(self) -> Observed:
        return self.publisher.observe()

    def claim(
        self, intent: WriterClaim, frame: SyntheticMaterializedFrame,
    ) -> None:
        if type(intent) is not WriterClaim or type(frame) is not SyntheticMaterializedFrame:
            raise TypeError("TYPED_WRITER_CLAIM_AND_FRAME_REQUIRED")
        if self.publisher.in_doubt:
            raise PermissionError("COMMITTED_INVISIBLE_HEAD_QUARANTINED")
        if self.active_actor is not None or self.publisher.pending is not None:
            raise PermissionError("VOLATILE_WRITER_ALREADY_ACTIVE")
        visible = self.publisher.visible
        if (intent.expected_generation != visible.generation or
                intent.expected_frame_sha256 != visible.frame_sha256):
            raise PermissionError("STALE_WRITER_EXPECTED_HEAD_DENIED")
        if intent.candidate_frame_sha256 != frame.digest:
            raise PermissionError("CANDIDATE_PAYLOAD_DIGEST_CHANGED")
        if frame.generation != visible.generation + 1:
            raise PermissionError("NONCONTIGUOUS_WRITER_GENERATION")
        # Reuse exact inherited tombstone/backfill/full-scope chain guard.
        self.publisher.prepare(frame)
        self.active_actor = intent.actor_label

    def _require_owner(self, actor_label: str) -> None:
        if type(actor_label) is not str or actor_label != self.active_actor:
            raise PermissionError("INPROCESS_WRITER_OWNER_MISMATCH")

    def materialize(self, actor_label: str) -> None:
        self._require_owner(actor_label)
        self.publisher.materialize()

    def commit(self, actor_label: str) -> None:
        self._require_owner(actor_label)
        self.publisher.commit()

    def expose(self, actor_label: str) -> None:
        self._require_owner(actor_label)
        self.publisher.publish_visible()
        self.active_actor = None

    def crash(self) -> None:
        """Crash injection only. Do not resolve a committed invisible intent."""
        self.publisher.simulated_crash()
        self.active_actor = None


def competing_frames():
    """Two valid but incompatible G2 histories with identical source G1."""
    full = real_v1_synthetic_frames()
    fork = replace(full[1], as_of_utc=instant(31))
    verify_local_event_chain((full[0], full[1]))
    verify_local_event_chain((full[0], fork))
    if full[1].digest == fork.digest or full[1].parent_digest != fork.parent_digest:
        raise AssertionError("FORK_FIXTURE_MUST_SHARE_PARENT_NOT_HEAD")
    return full, fork


def run_race_lab() -> dict:
    frames, rival = competing_frames()
    genesis = frames[0]
    shared = SingleMemorySequencer(genesis)
    reader_a = SyntheticReader(genesis.digest, genesis.scope_binding_sha256)
    reader_b = SyntheticReader(genesis.digest, genesis.scope_binding_sha256)
    start = shared.observe()
    reader_a.admit(start)
    reader_b.admit(start)
    writer_a = WriterClaim.from_observation("writer-A", start, frames[1])
    writer_b = WriterClaim.from_observation("writer-B", start, rival)

    shared.claim(writer_a, frames[1])
    # Two writers observed exactly the same head; B cannot prepare in this
    # SINGLE volatile coordinator. This does NOT prove remote CAS.
    try:
        shared.claim(writer_b, rival)
    except PermissionError as exc:
        if "VOLATILE_WRITER_ALREADY_ACTIVE" not in str(exc):
            raise
    else:
        raise AssertionError("TWO_ACTIVE_WRITERS_IN_ONE_MEMORY_IMAGE")
    shared.materialize("writer-A")
    # Even after physical-like object materialization, an uncommitted head is
    # not visible to either reader.
    if reader_b.admit(shared.observe())["generation"] != 1:
        raise AssertionError("PRECOMMIT_DATA_EXPOSED")
    shared.commit("writer-A")
    try:
        reader_b.admit(shared.observe(), require_generation=2)
    except PermissionError as exc:
        if "REQUIRED_READER_VISIBLE" not in str(exc):
            raise
    else:
        raise AssertionError("COMMITTED_INVISIBLE_DATA_EXPOSED")
    shared.expose("writer-A")
    head = shared.observe()
    if reader_a.admit(head)["generation"] != 2:
        raise AssertionError("A_DID_NOT_OBSERVE_COMMITTED_HEAD")
    try:
        shared.claim(writer_b, rival)
    except PermissionError as exc:
        if "STALE_WRITER_EXPECTED_HEAD" not in str(exc):
            raise
    else:
        raise AssertionError("STALE_RIVAL_WRITER_ACCEPTED")

    # B has not yet observed G2 and is permitted to read a once-valid G1
    # snapshot by its own local floor. A mandatory target G2 check does deny.
    if reader_b.admit(start)["generation"] != 1:
        raise AssertionError("INDEPENDENT_READER_OLD_HEAD_REVIEW_DRIFT")
    try:
        reader_b.admit(start, require_generation=2)
    except PermissionError as exc:
        if "REQUIRED_READER_VISIBLE" not in str(exc):
            raise
    else:
        raise AssertionError("READER_REQUIRE_NEWER_GENERATION_WAS_BYPASSED")
    reader_b.admit(head)
    try:
        reader_b.admit(start)
    except PermissionError as exc:
        if "STALE_READ_BELOW_SESSION_FLOOR" not in str(exc):
            raise
    else:
        raise AssertionError("SESSION_STALE_AFTER_ADVANCE_ACCEPTED")

    # A completely isolated memory image (not the actual shared service)
    # can select writer-B as its own competing G2 winner.
    isolated = SingleMemorySequencer(genesis)
    independent_b = WriterClaim.from_observation(
        "writer-B", isolated.observe(), rival,
    )
    isolated.claim(independent_b, rival)
    isolated.materialize("writer-B")
    isolated.commit("writer-B")
    isolated.expose("writer-B")
    alternate = isolated.observe()
    if alternate.visible.frame_sha256 == head.visible.frame_sha256:
        raise AssertionError("SPLIT_BRAIN_FORK_NOT_DISTINCT")

    # A previously advanced reader detects same-generation fork via its
    # local anchored SHA. Fresh readers have no external floor/authority.
    try:
        reader_a.admit(alternate)
    except PermissionError as exc:
        if "SESSION_FLOOR_FORK_OR_REWRITE" not in str(exc):
            raise
    else:
        raise AssertionError("KNOWN_READER_ACCEPTED_SAME_GEN_FORK")
    new_reader = SyntheticReader(genesis.digest, genesis.scope_binding_sha256)
    if new_reader.admit(alternate)["generation"] != 2:
        raise AssertionError("FRESH_READER_SHOULD_SHOW_RESET_VULNERABILITY")
    reset_reader = SyntheticReader(genesis.digest, genesis.scope_binding_sha256)
    if reset_reader.admit(start)["generation"] != 1:
        raise AssertionError("RESET_READER_ROLLBACK_FALSIFICATION_FAILED")

    # The original V1 G3 backfill references the original G2 digest and
    # cannot be appended to rival G2 without an explicit new versioned event.
    try:
        verify_local_event_chain((genesis, rival, frames[2]))
    except ValueError as exc:
        if "PARENT_DIGEST_MISMATCH" not in str(exc):
            raise
    else:
        raise AssertionError("FORKED_G3_UNVERSIONED_MERGE_ACCEPTED")

    return {
        "schema": SCHEMA,
        "verdict": "SYNTHETIC_NEGATIVE_PROOF_ONLY_PRODUCTION_NO_GO",
        "v1_unchanged_sqlite_decimal_oracle": True,
        "shared_memory_one_writer_at_a_time": True,
        "stale_writer_ticket_denied_after_head_change": True,
        "reader_old_head_without_global_required_floor_possible": True,
        "reader_local_floor_rejects_stale_after_advancing": True,
        "reset_reader_accepts_old_valid_genesis": True,
        "isolated_coordinator_split_brain_valid_local_forks": True,
        "prior_reader_rejects_same_generation_fork": True,
        "fresh_reader_accepts_self_attested_rival_fork": True,
        "original_g3_cannot_follow_unapproved_g2_fork": True,
        "winning_shared_generation": head.visible.generation,
        "same_parent_distinct_g2_digests": [
            frames[1].digest, rival.digest,
        ],
        "independent_external_signer_verified": False,
        "nonresettable_external_floor_verified": False,
        "real_two_principal_server_cas_verified": False,
        "real_drive_cache_or_atomic_cross_service_read": False,
        "licensed_market_source_first_known_verified": False,
        "production_reader_writer_or_trading_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run_race_lab()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
