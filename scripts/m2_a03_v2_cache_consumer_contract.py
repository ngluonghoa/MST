"""MST A03 versioned, READ-ONLY V1→V2 synthetic cache consumer contract.

Bind every V1 cache policy dimension to a separately typed V2 candidate
partition and compare persisted V1 checkpoint bytes to an independently coded
EMA20 / Wilder ATR14 oracle. This is NOT a V2 Drive cache implementation.

No real vendor data, Drive API, provider token, signing root, CAS or trading.
A current materialized V1 store cannot reconstruct prior historical revisions;
any attempt to use an old as-of time fails closed rather than inventing them.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.incremental_cache import (
    CacheIdentity, SyntheticIncrementalStore, full_recompute,
)
from swing_trading.v2_cache_partition_plan import (
    FixtureHeadV2, FixturePartitionV2, plan_fixture_refresh,
)
from scripts.m2_a02_incremental_cache_oracle_lab import (
    _apply, bar, identity, independent_ema_atr_oracle, instant,
)

SCHEMA = "mst.a03.v2-cache-consumer-readonly-contract.synthetic.v1"
STATUS = "CANDIDATE_V2_SCOPE_BOUND_TO_ACTUAL_V1_FIXTURE_NOT_PRODUCTION_PARITY"


def _hex_sha(value: object) -> str:
    if type(value) is not str or len(value) != 64 or any(
        ch not in "0123456789abcdef" for ch in value
    ):
        raise ValueError("CANONICAL_SHA256_REQUIRED")
    return value


def _hash(payload: object) -> str:
    return sha256(json.dumps(
        payload, ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.utcoffset() is None:
        raise TypeError("EXPLICIT_UTC_CLOCK_REQUIRED")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError("UTC_ZERO_OFFSET_REQUIRED")
    return value


@dataclass(frozen=True)
class FixtureV2ConsumerScope:
    """A typed explicit legacy→candidate map, NOT a real provider mapping."""

    legacy: CacheIdentity
    candidate: FixturePartitionV2
    accepted_legacy_instrument: str
    mapped_candidate_symbol: str

    def __post_init__(self) -> None:
        if (type(self.legacy) is not CacheIdentity
                or type(self.candidate) is not FixturePartitionV2):
            raise TypeError("TYPED_V1_AND_V2_SCOPE_REQUIRED")
        if (self.legacy.environment != "SYNTHETIC_TEST_ONLY"
                or self.legacy.project_id != "SwingTrading1.8"):
            raise PermissionError("LEGACY_PRODUCTION_CACHE_CONSUMER_DENIED")
        if (type(self.accepted_legacy_instrument) is not str
                or type(self.mapped_candidate_symbol) is not str
                or self.legacy.instrument_id != self.accepted_legacy_instrument
                or self.candidate.symbol != self.mapped_candidate_symbol):
            raise ValueError("EXPLICIT_INSTRUMENT_MAPPING_REQUIRED")
        checks = (
            ("provider", self.legacy.provider.value, self.candidate.provider_id),
            ("endpoint", self.legacy.endpoint_id, self.candidate.endpoint_id),
            ("timeframe", self.legacy.timeframe, self.candidate.timeframe),
            ("basis", self.legacy.price_basis, self.candidate.price_basis),
            ("revision", self.legacy.adjustment_revision,
             self.candidate.source_revision_namespace),
        )
        for name, original, proposed in checks:
            if original != proposed:
                raise ValueError("V1_V2_CACHE_SCOPE_MISMATCH_" + name.upper())
        if self.legacy.session_id != (
            "SYNTHETIC." + self.candidate.session_date_local.strftime("%Y%m%d")
        ):
            raise ValueError("V1_V2_SESSION_MAP_NOT_EXPLICITLY_LOCKED")

    @property
    def binding_sha256(self) -> str:
        """Must include all legacy policy dimensions absent from V2 partition."""
        original = asdict(self.legacy)
        original["provider"] = self.legacy.provider.value
        return _hash({
            "schema": SCHEMA,
            "original_full_identity": original,
            "original_fingerprint": self.legacy.fingerprint,
            "candidate_partition": self.candidate.digest,
            "candidate_symbol": self.candidate.symbol,
            "legacy_instrument": self.legacy.instrument_id,
        })


def preview_v2_consumer(
    store: SyntheticIncrementalStore,
    scope: FixtureV2ConsumerScope,
    *, as_of_utc: datetime,
    proposed_head: FixtureHeadV2 | None,
) -> dict:
    """No writes. Fail closed when V1 materialized state cannot prove as-of."""
    if type(store) is not SyntheticIncrementalStore:
        raise TypeError("INHERITED_V1_SYNTHETIC_STORE_REQUIRED")
    if type(scope) is not FixtureV2ConsumerScope:
        raise TypeError("VERSIONED_CONSUMER_SCOPE_REQUIRED")
    as_of = _utc(as_of_utc)
    cursor = store.cursor(scope.legacy)
    if cursor is None:
        raise PermissionError("CURRENT_LEGACY_SCOPE_NOT_MATERIALIZED")
    if as_of < cursor.last_checked_utc:
        raise PermissionError("HISTORICAL_MATERIALIZED_STATE_UNAVAILABLE")
    if proposed_head is not None and type(proposed_head) is not FixtureHeadV2:
        raise TypeError("ONLY_UNTRUSTED_TYPED_V2_HEAD_ALLOWED")

    candles = store.read_bars(scope.legacy)
    checkpoints = store.read_checkpoints(scope.legacy)
    if not candles or len(candles) != len(checkpoints):
        raise ValueError("INCOMPLETE_V1_CANDLE_CHECKPOINT_SNAPSHOT")
    if (any(not b.closed or b.end_utc > as_of
            or b.first_known_utc > as_of for b in candles)):
        raise PermissionError("FUTURE_KNOWN_OR_OPEN_CANDLE_IN_SNAPSHOT")
    if len({b.start_utc for b in candles}) != len(candles):
        raise ValueError("DUPLICATE_V1_SNAPSHOT_TIME")
    if checkpoints != full_recompute(candles):
        raise ValueError("V1_CHECKPOINT_COLD_PARITY_FAILED")
    if checkpoints != independent_ema_atr_oracle(candles):
        raise ValueError("V1_CHECKPOINT_INDEPENDENT_NUMERIC_ORACLE_FAILED")

    # V2 planner is intentionally not a source-authorized read: its head is
    # caller-controlled, never an independently enrolled key or data receipt.
    refresh = plan_fixture_refresh(
        scope.candidate, proposed_head, checked_at_utc=as_of,
    )
    bars_payload = [
        {
            "bar_start_utc": b.start_utc.isoformat(),
            "bar_end_utc": b.end_utc.isoformat(),
            "first_known_utc": b.first_known_utc.isoformat(),
            "revision": b.revision,
            "content_digest": _hex_sha(b.normalized_digest),
        }
        for b in candles
    ]
    indicator_payload = [
        {
            "bar_start_utc": x.start_utc.isoformat(),
            "ema20": str(x.ema20),
            "atr14": str(x.atr14) if x.atr14 is not None else None,
            "atr_seen": x.atr_seen,
            "atr_seed_sum": str(x.atr_seed_sum),
            "last_close": str(x.last_close),
        }
        for x in checkpoints
    ]
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "fixture_as_of_utc": as_of.isoformat(),
        "legacy_source_project": scope.legacy.project_id,
        "legacy_identity_sha256": scope.legacy.fingerprint,
        "v2_candidate_partition_sha256": scope.candidate.digest,
        "all_legacy_policies_bound_sha256": scope.binding_sha256,
        "legacy_policy_versions": {
            "rights": scope.legacy.source_rights_policy_version,
            "resolution": scope.legacy.source_resolution_policy_version,
            "quality": scope.legacy.quality_policy_version,
            "adjustment": scope.legacy.adjustment_revision,
            "calendar": scope.legacy.calendar_version,
            "aggregation": scope.legacy.aggregation_policy_version,
            "indicator": scope.legacy.indicator_version,
            "indicator_parameters": scope.legacy.indicator_parameter_version,
        },
        "bar_count": len(candles),
        "first_valid_atr14_bar_index_1_based": next(
            (i for i, x in enumerate(checkpoints, start=1) if x.atr14 is not None),
            None,
        ),
        "v1_bar_revisions_digest": _hash(bars_payload),
        "v1_ema20_atr14_checkpoint_digest": _hash(indicator_payload),
        "v1_observation_cursor_checked_utc": cursor.last_checked_utc.isoformat(),
        "v2_untrusted_head_generation": (
            proposed_head.generation if proposed_head else None
        ),
        "v2_refresh_hint": refresh.hint.value,
        "legacy_materialized_current_state_only": True,
        "can_reconstruct_historical_as_of_from_latest_materialized": False,
        "source_entitlement_independently_verified": False,
        "v2_real_drive_manifest_or_bytes_read": False,
        "v2_cache_publisher_or_cas_implemented": False,
        "v2_authoritative_consumer_parity_verified": False,
        "owner_a02_a03_release_signed_off": False,
        "licensed_cache_read_authorized": False,
        "drive_write_authorized": False,
        "trading_authorized": False,
    }


def fixture_scope(legacy: CacheIdentity | None = None) -> FixtureV2ConsumerScope:
    old = identity() if legacy is None else legacy
    return FixtureV2ConsumerScope(
        old,
        FixturePartitionV2(
            old.provider.value, old.endpoint_id, "FAKE001", old.timeframe,
            instant(0).date(), old.price_basis, old.adjustment_revision,
        ),
        "SYN_A02_ORACLE", "FAKE001",
    )


def run_v2_consumer_contract_lab() -> dict:
    """Cold, warm, lineage-only, correction and rights-evolution previews."""
    from dataclasses import replace
    with TemporaryDirectory(prefix="mst-github-v2-readonly-consumer-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "fixture.sqlite")
        store.initialize()
        scope = fixture_scope()
        key = scope.legacy
        _apply(store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = preview_v2_consumer(
            store, scope, as_of_utc=instant(20), proposed_head=None,
        )
        untrusted_head = FixtureHeadV2(
            scope.candidate.digest, 1,
            cold["v1_bar_revisions_digest"], instant(20),
        )
        _apply(store, key, (bar(19),), now=21, start=19, end=20)
        warm = preview_v2_consumer(
            store, scope, as_of_utc=instant(21),
            proposed_head=untrusted_head,
        )
        _apply(store, key, (bar(8, revision="r2"),),
               now=22, start=8, end=9)
        metadata = preview_v2_consumer(
            store, scope, as_of_utc=instant(22),
            proposed_head=untrusted_head,
        )
        _apply(store, key, (bar(5, close=200, revision="r2"),),
               now=23, start=5, end=6)
        corrected = preview_v2_consumer(
            store, scope, as_of_utc=instant(23),
            proposed_head=untrusted_head,
        )
        if not (
            cold["v1_bar_revisions_digest"] == warm["v1_bar_revisions_digest"]
            and cold["v1_ema20_atr14_checkpoint_digest"] == warm[
                "v1_ema20_atr14_checkpoint_digest"
            ] and metadata["v1_bar_revisions_digest"] != warm[
                "v1_bar_revisions_digest"
            ] and metadata["v1_ema20_atr14_checkpoint_digest"] == warm[
                "v1_ema20_atr14_checkpoint_digest"
            ] and corrected["v1_bar_revisions_digest"] != metadata[
                "v1_bar_revisions_digest"
            ] and corrected["v1_ema20_atr14_checkpoint_digest"] != metadata[
                "v1_ema20_atr14_checkpoint_digest"
            ]
        ):
            raise AssertionError("V1_V2_CONSUMER_VERSIONED_DIGEST_DIFFERENTIAL_DRIFT")
        changed_rights = replace(key, source_rights_policy_version="RIGHTS.REVOKED")
        rights_scope = fixture_scope(changed_rights)
        if (rights_scope.candidate.digest != scope.candidate.digest
                or rights_scope.binding_sha256 == scope.binding_sha256):
            raise AssertionError("FULL_LEGACY_RIGHTS_POLICY_BINDING_DRIFT")
        try:
            preview_v2_consumer(
                store, rights_scope, as_of_utc=instant(23),
                proposed_head=untrusted_head,
            )
        except PermissionError as e:
            if "NOT_MATERIALIZED" not in str(e):
                raise
        else:
            raise AssertionError("REVOKED_RIGHTS_REUSED_OLD_V1_CACHED_BARS")
        try:
            preview_v2_consumer(
                store, scope, as_of_utc=instant(21),
                proposed_head=untrusted_head,
            )
        except PermissionError as e:
            if "HISTORICAL_MATERIALIZED" not in str(e):
                raise
        else:
            raise AssertionError("LATEST_MATERIALIZED_CACHE_REPLAYED_OLD_ASOF")
        snapshots = [
            {"stage": stage,
             "bar_revisions_digest": record["v1_bar_revisions_digest"],
             "ema20_atr14_digest": record["v1_ema20_atr14_checkpoint_digest"],
             "v2_refresh_hint": record["v2_refresh_hint"],
             "read_rights_verified": record["licensed_cache_read_authorized"]}
            for stage, record in (
                ("COLD", cold), ("WARM", warm),
                ("LINEAGE_ONLY", metadata), ("CORRECTION", corrected),
            )
        ]
        return {
            "schema": SCHEMA,
            "status": "V2_CONSUMER_DRAFT_CONTRACT_AND_V1_GOLDEN_DIFFERENTIAL_PASS",
            "stages": snapshots,
            "stages_checked": len(snapshots),
            "bar_count": 20,
            "atr_first_valid_bar_index_1_based": 14,
            "v1_current_materialized_oracle_verified": True,
            "unchanged_warm_content_digests": True,
            "metadata_revision_changes_bar_digest_not_indicators": True,
            "old_price_correction_changes_ema_atr_tail": True,
            "v2_partition_hash_omits_rights_version": True,
            "full_binding_digest_changes_on_rights_revocation": True,
            "revoked_rights_cannot_reuse_existing_legacy_scope": True,
            "historical_as_of_from_latest_state_denied": True,
            "v2_metadata_head_is_untrusted": True,
            "v2_complete_drive_consumer_implemented": False,
            "external_source_or_rollback_floor_verified": False,
            "production_cache_authorized": False,
            "trading_authorized": False,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run_v2_consumer_contract_lab()
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
