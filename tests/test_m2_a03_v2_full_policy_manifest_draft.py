"""Synthetic full-policy V2 manifest chain: provenance/rights/as-of negative tests.

A passing local SHA256 history is NOT an independent G01 signer, protected G02
floor, source entitlement or real two-writer GitHub/Drive CAS.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.m2_a02_incremental_cache_oracle_lab import _apply, bar, instant
from scripts.m2_a03_v2_cache_consumer_contract import _hash, fixture_scope
from scripts.m2_a03_v2_full_policy_manifest_draft import (
    SCHEMA, ManifestDraft, MaterializedBarRevision,
    create_manifest, run_manifest_chain_fixture, verify_manifest_chain,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore


def chain_fixture():
    with TemporaryDirectory(prefix="mst-gh-full-policy-candidate-test-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "test.sqlite")
        store.initialize()
        scope = fixture_scope()
        key = scope.legacy
        _apply(store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = create_manifest(
            store, scope, as_of_utc=instant(20), stage="COLD", parent=None,
        )
        _apply(store, key, (bar(19),), now=21, start=19, end=20)
        warm = create_manifest(
            store, scope, as_of_utc=instant(21), stage="WARM", parent=cold,
        )
        meta = replace(bar(8, revision="r2"), first_known_utc=instant(22))
        _apply(store, key, (meta,), now=22, start=8, end=9)
        lineage = create_manifest(
            store, scope, as_of_utc=instant(22), stage="LINEAGE_ONLY", parent=warm,
        )
        correction = replace(bar(5, close=D(200), revision="r2"),
                             first_known_utc=instant(23))
        _apply(store, key, (correction,), now=23, start=5, end=6)
        changed = create_manifest(
            store, scope, as_of_utc=instant(23),
            stage="PRICE_CORRECTION", parent=lineage,
        )
        return cold, warm, lineage, changed


def with_revision_changed(manifest, target_index, **fields):
    revisions = list(manifest.revisions)
    revisions[target_index] = replace(revisions[target_index], **fields)
    return replace(manifest, revisions=tuple(revisions),
                   bars_digest=_hash([r.canonical() for r in revisions]))


class VersionedManifestPositiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chain = chain_fixture()
        cls.proof = verify_manifest_chain(cls.chain)

    def test_four_stage_real_v1_fixture_chain(self):
        self.assertEqual(self.proof["schema"], SCHEMA)
        self.assertEqual(self.proof["generations"], 4)
        self.assertEqual(self.proof["last_generation"], 4)
        self.assertEqual(self.proof["status"],
                         "LOCAL_CANDIDATE_CHAIN_CONSISTENT_NO_EXTERNAL_ATTESTATION")

    def test_four_stage_names_and_strictly_increasing_clock(self):
        self.assertEqual(tuple(m.stage for m in self.chain),
                         ("COLD", "WARM", "LINEAGE_ONLY", "PRICE_CORRECTION"))
        self.assertEqual(tuple(m.generation for m in self.chain), (1, 2, 3, 4))
        self.assertEqual(tuple(m.as_of_utc for m in self.chain),
                         tuple(instant(n) for n in (20, 21, 22, 23)))

    def test_exact_sha256_parent_chain(self):
        self.assertIsNone(self.chain[0].parent_digest)
        for i in (1, 2, 3):
            self.assertEqual(self.chain[i].parent_digest, self.chain[i-1].digest)
        self.assertRegex(self.proof["last_manifest_digest"], "^[0-9a-f]{64}$")

    def test_all_full_legacy_policy_versions_are_explicit(self):
        names = {"rights", "resolution", "quality", "adjustment",
                 "calendar", "aggregation", "indicator", "indicator_parameters"}
        for m in self.chain:
            self.assertEqual(set(dict(m.policy_versions)), names)
            self.assertEqual(m.policy_versions, tuple(sorted(m.policy_versions)))
            self.assertEqual(len(m.revisions), 20)
            self.assertTrue(self.proof["full_rights_and_indicator_policy_scope_bound"])

    def test_warm_exact_reuse_of_bars_and_indicators(self):
        a, b = self.chain[:2]
        self.assertEqual(a.bars_digest, b.bars_digest)
        self.assertEqual(a.indicators_digest, b.indicators_digest)
        self.assertEqual(a.revisions, b.revisions)

    def test_metadata_only_revision_preserves_ema_atr(self):
        a, b = self.chain[1:3]
        self.assertNotEqual(a.bars_digest, b.bars_digest)
        self.assertEqual(a.indicators_digest, b.indicators_digest)
        self.assertEqual(b.revisions[8].revision_id, "r2")
        self.assertEqual(b.revisions[8].first_known_utc, instant(22))

    def test_price_correction_invalidates_ema_atr(self):
        a, b = self.chain[2:4]
        self.assertNotEqual(a.bars_digest, b.bars_digest)
        self.assertNotEqual(a.indicators_digest, b.indicators_digest)
        self.assertEqual(b.revisions[5].first_known_utc, instant(23))

    def test_revisions_sorted_closed_and_current(self):
        for manifest in self.chain:
            starts = [r.start_utc for r in manifest.revisions]
            self.assertEqual(starts, sorted(starts))
            self.assertEqual(len(starts), len(set(starts)))
            for rev in manifest.revisions:
                self.assertLess(rev.start_utc, rev.end_utc)
                self.assertLessEqual(rev.end_utc, rev.first_known_utc)
                self.assertLessEqual(rev.first_known_utc, manifest.as_of_utc)

    def test_manifest_digest_changes_with_correction(self):
        self.assertEqual(len({m.digest for m in self.chain}), 4)
        self.assertNotEqual(self.chain[0].digest, self.chain[-1].digest)

    def test_report_reproducible_without_network(self):
        first = run_manifest_chain_fixture()
        second = run_manifest_chain_fixture()
        self.assertEqual(first, second)
        self.assertEqual(first["fixture_bar_count"], 20)
        self.assertEqual(first["generations"], 4)
        self.assertEqual([r["stage"] for r in first["four_stage_golden"]],
                         ["COLD", "WARM", "LINEAGE_ONLY", "PRICE_CORRECTION"])

    def test_no_permission_or_independent_floor_claimed(self):
        for m in self.chain:
            self.assertFalse(m.licensed_source_verified)
            self.assertFalse(m.google_drive_write_authorized)
            self.assertFalse(m.production_consumer_authorized)
            self.assertFalse(m.trading_authorized)
        for k in ("external_g01_signer_authorized",
                  "external_g02_floor_or_admin_protection_verified",
                  "real_two_writer_server_cas_proven",
                  "licensed_gdrive_chunk_bytes_read_or_written",
                  "real_historical_as_of_reconstruction_verified",
                  "production_publisher_authorized", "trading_authorized"):
            self.assertFalse(self.proof[k])


class VersionedManifestFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cold, cls.warm, cls.lineage, cls.changed = chain_fixture()

    def assert_bad(self, chain, message):
        with self.assertRaisesRegex((ValueError, TypeError), message):
            verify_manifest_chain(tuple(chain))

    def test_empty_chain_denied(self):
        self.assert_bad((), "NONEMPTY_TYPED")

    def test_non_genesis_start_denied(self):
        self.assert_bad((self.warm, self.lineage), "LOCAL_GENESIS")

    def test_removed_intermediate_generation_denied(self):
        self.assert_bad((self.cold, self.lineage, self.changed), "GENERATION")

    def test_reordered_manifest_denied(self):
        self.assert_bad((self.cold, self.lineage, self.warm, self.changed),
                        "GENERATION")

    def test_wrong_parent_digest_denied(self):
        wrong = replace(self.lineage, parent_digest="f" * 64)
        self.assert_bad((self.cold, self.warm, wrong), "WRONG_PARENT")

    def test_duplicated_generation_denied(self):
        wrong = replace(self.lineage, generation=2)
        self.assert_bad((self.cold, self.warm, wrong), "GENERATION")

    def test_chain_as_of_clock_rewind_denied(self):
        wrong = replace(self.lineage, as_of_utc=instant(21))
        self.assert_bad((self.cold, self.warm, wrong), "NONMONOTONIC")

    def test_unchanged_as_of_duplicate_generation_denied(self):
        wrong = replace(self.lineage, as_of_utc=self.warm.as_of_utc)
        self.assert_bad((self.cold, self.warm, wrong), "NONMONOTONIC")

    def test_full_rights_scope_digest_drift_denied(self):
        wrong = replace(self.lineage, scope_binding_sha256="f" * 64)
        self.assert_bad((self.cold, self.warm, wrong), "CROSS_RIGHTS")

    def test_legacy_source_identity_scope_drift_denied(self):
        wrong = replace(self.lineage, legacy_identity_sha256="f" * 64)
        self.assert_bad((self.cold, self.warm, wrong), "SCOPE_AND_POLICY")

    def test_candidate_partition_scope_drift_denied(self):
        wrong = replace(self.lineage, partition_sha256="f" * 64)
        self.assert_bad((self.cold, self.warm, wrong), "SCOPE_AND_POLICY")

    def test_rights_policy_field_drift_denied(self):
        p = dict(self.lineage.policy_versions)
        p["rights"] = "RIGHTS.REVOKED"
        wrong = replace(self.lineage, policy_versions=tuple(sorted(p.items())))
        self.assert_bad((self.cold, self.warm, wrong), "SCOPE_AND_POLICY")

    def test_indicator_parameters_policy_drift_denied(self):
        p = dict(self.lineage.policy_versions)
        p["indicator_parameters"] = "EMA12.ATR14"
        wrong = replace(self.lineage, policy_versions=tuple(sorted(p.items())))
        self.assert_bad((self.cold, self.warm, wrong), "SCOPE_AND_POLICY")

    def test_missing_policy_dimension_denied_at_construction(self):
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_FULL_V1_POLICY"):
            replace(self.lineage, policy_versions=self.lineage.policy_versions[:-1])

    def test_duplicate_policy_dimension_denied_at_construction(self):
        pol = self.lineage.policy_versions
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_FULL_V1_POLICY"):
            replace(self.lineage, policy_versions=pol[:-1] + (pol[0],))

    def test_noncanonical_policy_sort_denied(self):
        with self.assertRaisesRegex(ValueError, "CANONICALLY_SORTED"):
            replace(self.lineage, policy_versions=tuple(reversed(self.lineage.policy_versions)))

    def test_future_known_revision_denied(self):
        with self.assertRaisesRegex(ValueError, "FUTURE_KNOWN"):
            with_revision_changed(self.lineage, 8, first_known_utc=instant(24))

    def test_retroactive_metadata_revision_denied(self):
        bad = with_revision_changed(self.lineage, 8, first_known_utc=instant(21))
        self.assert_bad((self.cold, self.warm, bad), "RETROACTIVE_SOURCE_CORRECTION")

    def test_retroactive_price_correction_denied(self):
        bad = with_revision_changed(self.changed, 5, first_known_utc=instant(22))
        self.assert_bad((self.cold, self.warm, self.lineage, bad),
                        "RETROACTIVE_SOURCE_CORRECTION")

    def test_same_revision_identity_with_rewritten_payload_denied(self):
        source = self.changed.revisions[5]
        before = self.lineage.revisions[5]
        bad = with_revision_changed(
            self.changed, 5,
            revision_id=before.revision_id,
            first_known_utc=before.first_known_utc,
            content_sha256=source.content_sha256,
        )
        self.assert_bad((self.cold, self.warm, self.lineage, bad),
                        "RETROACTIVE_SOURCE_CORRECTION")

    def test_unattested_deletion_denied(self):
        remaining = tuple(x for i, x in enumerate(self.changed.revisions) if i != 11)
        bad = replace(self.changed, revisions=remaining,
                      bars_digest=_hash([x.canonical() for x in remaining]))
        self.assert_bad((self.cold, self.warm, self.lineage, bad),
                        "UNATTESTED_HISTORICAL_BAR_DELETION")

    def test_unattested_early_backfill_denied(self):
        newrev = MaterializedBarRevision(
            instant(40), instant(41), instant(41), "r1", "a" * 64,
        )
        after = tuple(sorted((*self.changed.revisions, newrev),
                             key=lambda x: x.start_utc))
        # The immutable model should reject first-known > current as-of first.
        with self.assertRaisesRegex(ValueError, "FUTURE_KNOWN"):
            replace(self.changed, revisions=after,
                    bars_digest=_hash([x.canonical() for x in after]))

    def test_warm_unexpected_indicators_denied(self):
        bad = replace(self.warm, indicators_digest="f" * 64)
        self.assert_bad((self.cold, bad), "WARM_REUSE")

    def test_lineage_only_unexpected_indicator_recompute_denied(self):
        bad = replace(self.lineage, indicators_digest="f" * 64)
        self.assert_bad((self.cold, self.warm, bad), "LINEAGE_ONLY")

    def test_lineage_only_no_change_denied(self):
        bad = replace(self.lineage, revisions=self.warm.revisions,
                      bars_digest=self.warm.bars_digest)
        self.assert_bad((self.cold, self.warm, bad), "LINEAGE_ONLY")

    def test_price_correction_missing_indicator_invalidations_denied(self):
        bad = replace(self.changed, indicators_digest=self.lineage.indicators_digest)
        self.assert_bad((self.cold, self.warm, self.lineage, bad), "PRICE_CORRECTION")

    def test_bar_content_digest_mismatch_denied_at_construction(self):
        with self.assertRaisesRegex(ValueError, "MATERIALIZED_BAR_REVISION_DIGEST"):
            replace(self.changed, bars_digest="a" * 64)

    def test_duplicate_bar_timestamp_denied(self):
        r = self.changed.revisions
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_UNSORTED"):
            replace(self.changed, revisions=(r[0], *r))

    def test_unsorted_bar_timestamp_denied(self):
        r = self.changed.revisions
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_UNSORTED"):
            replace(self.changed, revisions=(r[1], r[0], *r[2:]))

    def test_nonhex_digest_denied_at_construction(self):
        with self.assertRaisesRegex(ValueError, "CANONICAL_SHA256"):
            replace(self.changed, indicators_digest="Z" * 64)

    def test_wrong_first_manifest_stage_denied(self):
        bad = replace(self.cold, stage="WARM")
        self.assert_bad((bad,), "FIRST_MANIFEST_MUST_BE_COLD")

    def test_genesis_parent_type_consistency_denied(self):
        with self.assertRaisesRegex(ValueError, "GENESIS_PARENT_GENERATION"):
            replace(self.cold, parent_digest="f" * 64)

    def test_unknown_stage_denied(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_VERSIONED_MANIFEST_STAGE"):
            replace(self.changed, stage="PRODUCTION")

    def test_not_implicitly_network_authorized_by_reproducible_hash(self):
        self.assertFalse(self.changed.production_consumer_authorized)
        self.assertFalse(self.changed.google_drive_write_authorized)


if __name__ == "__main__":
    unittest.main()
