"""MST A03 candidate versioned cache-manifest chain — synthetic draft, NO DRIVE I/O.

Hash a FULL V1 rights/quality/indicator policy scope, first-known-time-bounded
materialized candle revisions, and two separate data/EMA20-ATR14 digests into
a locally verifiable proposed V2 manifest lineage.

Caller-generated hashes and the in-memory chain are NOT a trusted source,
independent monotonically protected floor, authenticated writer, Drive object
or production CAS. Historical as-of reconstruction is explicitly unavailable.
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
from swing_trading.incremental_cache import SyntheticIncrementalStore

SCHEMA = "mst.a03.v2-cache-manifest-full-policy.synthetic.v1"
STAGES = ("COLD", "WARM", "LINEAGE_ONLY", "PRICE_CORRECTION")
POLICIES = frozenset((
    "rights", "resolution", "quality", "adjustment", "calendar",
    "aggregation", "indicator", "indicator_parameters",
))


@dataclass(frozen=True)
class MaterializedBarRevision:
    start_utc: datetime
    end_utc: datetime
    first_known_utc: datetime
    revision_id: str
    content_sha256: str

    def __post_init__(self):
        start, end, known = (_utc(x) for x in (
            self.start_utc, self.end_utc, self.first_known_utc
        ))
        if not (start < end <= known):
            raise ValueError("CLOSED_BAR_FIRST_KNOWN_AFTER_END_REQUIRED")
        if type(self.revision_id) is not str or not self.revision_id or len(self.revision_id) > 128:
            raise ValueError("TYPED_SOURCE_REVISION_ID_REQUIRED")
        _hex_sha(self.content_sha256)

    def canonical(self):
        return {
            "bar_start_utc": self.start_utc.isoformat(),
            "bar_end_utc": self.end_utc.isoformat(),
            "first_known_utc": self.first_known_utc.isoformat(),
            "revision": self.revision_id,
            "content_digest": self.content_sha256,
        }


@dataclass(frozen=True)
class ManifestDraft:
    generation: int
    parent_digest: str | None
    scope_binding_sha256: str
    partition_sha256: str
    legacy_identity_sha256: str
    policy_versions: tuple[tuple[str, str], ...]
    as_of_utc: datetime
    stage: str
    revisions: tuple[MaterializedBarRevision, ...]
    bars_digest: str
    indicators_digest: str

    def __post_init__(self):
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("POSITIVE_MANIFEST_GENERATION_REQUIRED")
        if (self.generation == 1) != (self.parent_digest is None):
            raise ValueError("GENESIS_PARENT_GENERATION_INCONSISTENT")
        if self.parent_digest is not None:
            _hex_sha(self.parent_digest)
        for digest in (
            self.scope_binding_sha256, self.partition_sha256,
            self.legacy_identity_sha256, self.bars_digest,
            self.indicators_digest,
        ):
            _hex_sha(digest)
        _utc(self.as_of_utc)
        if self.stage not in STAGES or type(self.stage) is not str:
            raise ValueError("UNKNOWN_VERSIONED_MANIFEST_STAGE")
        if type(self.policy_versions) is not tuple or set(k for k, _ in self.policy_versions) != POLICIES:
            raise ValueError("INCOMPLETE_FULL_V1_POLICY_BINDING")
        if len(self.policy_versions) != len(POLICIES) or tuple(sorted(self.policy_versions)) != self.policy_versions:
            raise ValueError("POLICY_VERSIONS_MUST_BE_CANONICALLY_SORTED")
        if any(type(k) is not str or type(v) is not str or not v for k, v in self.policy_versions):
            raise ValueError("MALFORMED_V1_POLICY_VERSIONS")
        if type(self.revisions) is not tuple or not self.revisions:
            raise ValueError("NONEMPTY_TYPED_MATERIALIZED_REVISION_SET_REQUIRED")
        if any(type(r) is not MaterializedBarRevision for r in self.revisions):
            raise TypeError("TYPED_BAR_REVISIONS_REQUIRED")
        starts = [r.start_utc for r in self.revisions]
        if starts != sorted(set(starts)):
            raise ValueError("DUPLICATE_OR_UNSORTED_BAR_REVISION")
        if any(r.first_known_utc > self.as_of_utc for r in self.revisions):
            raise ValueError("FUTURE_KNOWN_REVISION_IN_MANIFEST")
        if _hash([r.canonical() for r in self.revisions]) != self.bars_digest:
            raise ValueError("MATERIALIZED_BAR_REVISION_DIGEST_MISMATCH")

    def canonical(self) -> dict:
        return {
            "schema": SCHEMA, "test_only": True, "project": "MST",
            "generation": self.generation, "parent_digest": self.parent_digest,
            "scope_binding_sha256": self.scope_binding_sha256,
            "partition_sha256": self.partition_sha256,
            "legacy_identity_sha256": self.legacy_identity_sha256,
            "policy_versions": dict(self.policy_versions),
            "as_of_utc": self.as_of_utc.isoformat(),
            "stage": self.stage, "bar_revisions": [x.canonical() for x in self.revisions],
            "bars_digest": self.bars_digest,
            "indicators_digest": self.indicators_digest,
        }

    @property
    def digest(self):
        return _hash(self.canonical())

    @property
    def licensed_source_verified(self):
        return False

    @property
    def google_drive_write_authorized(self):
        return False

    @property
    def production_consumer_authorized(self):
        return False

    @property
    def trading_authorized(self):
        return False


def create_manifest(
    store: SyntheticIncrementalStore,
    scope: FixtureV2ConsumerScope,
    *, as_of_utc: datetime,
    stage: str,
    parent: ManifestDraft | None,
) -> ManifestDraft:
    """Compare the actual materialized V1 snapshot with independent oracle."""
    if type(scope) is not FixtureV2ConsumerScope:
        raise TypeError("VERSIONED_V2_CONSUMER_SCOPE_REQUIRED")
    if parent is not None and type(parent) is not ManifestDraft:
        raise TypeError("TYPED_MANIFEST_PARENT_REQUIRED")
    preview = preview_v2_consumer(
        store, scope, as_of_utc=as_of_utc, proposed_head=None,
    )
    bars = store.read_bars(scope.legacy)
    revisions = tuple(MaterializedBarRevision(
        b.start_utc, b.end_utc, b.first_known_utc, b.revision, b.normalized_digest,
    ) for b in bars)
    manifest = ManifestDraft(
        generation=1 if parent is None else parent.generation + 1,
        parent_digest=None if parent is None else parent.digest,
        scope_binding_sha256=scope.binding_sha256,
        partition_sha256=scope.candidate.digest,
        legacy_identity_sha256=scope.legacy.fingerprint,
        policy_versions=tuple(sorted(preview["legacy_policy_versions"].items())),
        as_of_utc=_utc(as_of_utc),
        stage=stage,
        revisions=revisions,
        bars_digest=preview["v1_bar_revisions_digest"],
        indicators_digest=preview["v1_ema20_atr14_checkpoint_digest"],
    )
    # Full G1..Gn chain validation is mandatory at the reviewer boundary.
    # Two adjacent manifests alone cannot establish local genesis continuity.
    return manifest


def verify_manifest_chain(chain: tuple[ManifestDraft, ...]) -> dict:
    """Only proves self-consistency of caller-supplied local draft lineage.

    All generations must be supplied for any verification that starts at G1.
    No purported cross-run trust: a malicious writer could fabricate the
    entire chain, thus external G01/G02/G03 remain OPEN.
    """
    if type(chain) is not tuple or not chain:
        raise ValueError("NONEMPTY_TYPED_MANIFEST_CHAIN_REQUIRED")
    first = chain[0]
    if type(first) is not ManifestDraft or first.generation != 1 or first.parent_digest is not None:
        raise ValueError("LOCAL_GENESIS_REQUIRED_NOT_EXTERNAL_FLOOR")
    if first.stage != "COLD":
        raise ValueError("FIRST_MANIFEST_MUST_BE_COLD")
    scope = first.scope_binding_sha256
    for idx, manifest in enumerate(chain):
        if type(manifest) is not ManifestDraft:
            raise TypeError("TYPED_CANDIDATE_MANIFEST_REQUIRED")
        if manifest.scope_binding_sha256 != scope:
            raise ValueError("CROSS_RIGHTS_OR_POLICY_SCOPE_CHAIN_DENIED")
        if (manifest.partition_sha256 != first.partition_sha256 or
                manifest.legacy_identity_sha256 != first.legacy_identity_sha256 or
                manifest.policy_versions != first.policy_versions):
            raise ValueError("SCOPE_AND_POLICY_CAN_CHANGE_ONLY_IN_NEW_LINEAGE")
        if manifest.generation != idx + 1:
            raise ValueError("SKIPPED_OR_REWOUND_LOCAL_MANIFEST_GENERATION")
        if idx == 0:
            continue
        previous = chain[idx - 1]
        if manifest.parent_digest != previous.digest:
            raise ValueError("WRONG_PARENT_CHAIN_DIGEST")
        if manifest.as_of_utc <= previous.as_of_utc:
            raise ValueError("NONMONOTONIC_AS_OF_MANIFEST_LINEAGE")
        before = {r.start_utc: r for r in previous.revisions}
        after = {r.start_utc: r for r in manifest.revisions}
        # Deletion is NOT a supported event type in this four-stage draft.
        # Otherwise an attacker could drop an old bar and relabel a correction.
        if set(before) - set(after):
            raise ValueError("UNATTESTED_HISTORICAL_BAR_DELETION_DENIED")
        # Local named correction must become known AFTER the prior as-of.
        for start, revision in after.items():
            prior = before.get(start)
            if (prior is not None and prior != revision
                    and not (
                        prior.first_known_utc < revision.first_known_utc
                        and previous.as_of_utc < revision.first_known_utc
                        <= manifest.as_of_utc
                    )):
                raise ValueError("RETROACTIVE_SOURCE_CORRECTION_REWRITE_DENIED")
            if prior is None and revision.first_known_utc <= previous.as_of_utc:
                raise ValueError("RETROACTIVE_BACKFILL_WITHOUT_HISTORY_DENIED")
        if manifest.stage == "WARM" and (
            before != after or manifest.bars_digest != previous.bars_digest or
            manifest.indicators_digest != previous.indicators_digest
        ):
            raise ValueError("WARM_REUSE_MUST_NOT_CHANGE_BAR_OR_INDICATOR")
        if manifest.stage == "LINEAGE_ONLY" and (
            before == after or
            manifest.bars_digest == previous.bars_digest or
            manifest.indicators_digest != previous.indicators_digest
        ):
            raise ValueError("LINEAGE_ONLY_MUST_PRESERVE_INDICATORS")
        if manifest.stage == "PRICE_CORRECTION" and (
            manifest.bars_digest == previous.bars_digest or
            manifest.indicators_digest == previous.indicators_digest
        ):
            raise ValueError("PRICE_CORRECTION_MUST_INVALIDATE_INDICATORS")
    return {
        "schema": SCHEMA,
        "status": "LOCAL_CANDIDATE_CHAIN_CONSISTENT_NO_EXTERNAL_ATTESTATION",
        "generations": len(chain),
        "last_generation": chain[-1].generation,
        "last_manifest_digest": chain[-1].digest,
        "scope_binding_sha256": scope,
        "full_rights_and_indicator_policy_scope_bound": True,
        "first_known_correction_boundary_checked": True,
        "revisions_are_current_materialized_only": True,
        "external_g01_signer_authorized": False,
        "external_g02_floor_or_admin_protection_verified": False,
        "real_two_writer_server_cas_proven": False,
        "licensed_gdrive_chunk_bytes_read_or_written": False,
        "real_historical_as_of_reconstruction_verified": False,
        "production_publisher_authorized": False,
        "trading_authorized": False,
    }


def run_manifest_chain_fixture() -> dict:
    """Four cloud-hosted synthetic stages with explicit first-known corrections."""
    from dataclasses import replace
    with TemporaryDirectory(prefix="mst-gh-v2-manifest-draft-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "temporary-v1.sqlite")
        store.initialize()
        scope = fixture_scope()
        key = scope.legacy
        _apply(store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = create_manifest(store, scope, as_of_utc=instant(20), stage="COLD", parent=None)
        _apply(store, key, (bar(19),), now=21, start=19, end=20)
        warm = create_manifest(store, scope, as_of_utc=instant(21), stage="WARM", parent=cold)
        # Delayed first-known timestamp is NOT fabricated as an old observation.
        meta = replace(bar(8, revision="r2"), first_known_utc=instant(22))
        _apply(store, key, (meta,), now=22, start=8, end=9)
        lineage = create_manifest(store, scope, as_of_utc=instant(22),
                                  stage="LINEAGE_ONLY", parent=warm)
        correction = replace(bar(5, close=D("200"), revision="r2"),
                             first_known_utc=instant(23))
        _apply(store, key, (correction,), now=23, start=5, end=6)
        changed = create_manifest(store, scope, as_of_utc=instant(23),
                                  stage="PRICE_CORRECTION", parent=lineage)
        chain = (cold, warm, lineage, changed)
        verified = verify_manifest_chain(chain)
        if not (cold.bars_digest == warm.bars_digest
                and cold.indicators_digest == warm.indicators_digest
                and lineage.bars_digest != warm.bars_digest
                and lineage.indicators_digest == warm.indicators_digest
                and changed.bars_digest != lineage.bars_digest
                and changed.indicators_digest != lineage.indicators_digest):
            raise AssertionError("FOUR_STAGE_MANIFEST_NUMERIC_REVISIONS_DRIFT")
        return {
            **verified,
            "four_stage_golden": [
                {"stage": x.stage, "generation": x.generation,
                 "bar_revisions_digest": x.bars_digest,
                 "indicator_digest": x.indicators_digest,
                 "local_manifest_digest": x.digest,
                 "parent_digest": x.parent_digest,
                 "first_known_max_utc": max(r.first_known_utc for r in x.revisions).isoformat()}
                for x in chain
            ],
            "fixture_bar_count": len(changed.revisions),
            "previous_correction_not_retroactively_visible": True,
            "original_ema20_atr14_oracle_invoked_at_every_stage": True,
            "all_guards_remain_false_for_production": True,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = run_manifest_chain_fixture()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
