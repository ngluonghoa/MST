"""A02 second eight V1 runtime tranche: source-rights-to-cache trust boundary.

ACTUAL inherited original module code, never replacement stubs. Uses
manufactured observation metadata, EPHEMERAL Ed25519 keys, an empty
reference journal, and disposable offline SQLite. No account, provider,
real credentials/quotes, Google Drive market bytes, broker or trade.

Passing demonstrates conditional integrity AND refusal to promote
unverified evidence or local snapshot/chunk state into rights.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from swing_trading.native_minute_bar_source_plan import BarProduct
from swing_trading.provider_rights_review import (
    EvidenceKind, RightsScope, UnverifiedRightsClaim,
    review_unverified_source_claims, require_authorized_source,
)
from swing_trading.source_capability_evidence import (
    ProbeEndpoint, summarize_source_capability, audit_backtest_evidence,
)
from swing_trading.provider_signed_event_chain import (
    EventKind, RightsChainState, SignedRightsEvent, ClaimedExternalLedgerPin,
    verify_pinned_rights_event_chain, require_rights_chain_authorization,
)
from swing_trading.provider_head_custody import (
    CustodyProduct, ClaimedCustodianKey, ClaimedMonotonicFloor,
    SignedCustodyHead, CustodyRejected, audit_conditional_custody_head,
    require_authenticated_provider_rights,
)
from swing_trading.reference_journal import ReferenceJournal, ZERO
from swing_trading.reference_journal_recovery import (
    create_candidate_journal_checkpoint,
    verify_journal_backup_against_pinned, restore_journal_from_pinned,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore
from swing_trading.cache_snapshot_bundle import (
    create_fixture_snapshot, verify_fixture_snapshot, restore_fixture_snapshot,
    require_approved_cache_transport,
)
from swing_trading.partition_chunk_cache import (
    PartitionWrite, SyntheticDrivePartitionIndex,
    require_real_market_cache_transport,
)
from scripts.m2_a02_incremental_cache_oracle_lab import identity, bar

SCHEMA = "mst.a02.original-eight-source-custody-cache-execution.synthetic.v1"
EIGHT = (
    "provider_rights_review", "source_capability_evidence",
    "provider_signed_event_chain", "provider_head_custody",
    "reference_journal", "reference_journal_recovery",
    "cache_snapshot_bundle", "partition_chunk_cache",
)
BASE = datetime(2026, 11, 10, 3, 0, tzinfo=timezone.utc)
SOURCE_SHA = "cd90c1babae8912db31490ad614fc2ad2f868042"
MAIN_SHA = "4048f91beaaa3410116d97e35896c8b688384e19"
SIGNATURE_PLACEHOLDER = base64.b64encode(bytes(64)).decode("ascii")


def _public(private: Ed25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


def _sign(private: Ed25519PrivateKey, message: bytes) -> str:
    return base64.b64encode(private.sign(message)).decode("ascii")


def _denied(callable_, expected_exception=PermissionError):
    try:
        callable_()
    except expected_exception:
        return True
    raise AssertionError("V1_CONDITIONAL_FIXTURE_PROMOTED_TO_REAL_AUTHORITY")


def _event(private: Ed25519PrivateKey, *,
           number: int, previous: str, kind: EventKind) -> SignedRightsEvent:
    candidate = kind is EventKind.GRANT_CANDIDATE
    published = BASE - timedelta(minutes=3-number)
    e = SignedRightsEvent(
        product=BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
        sequence=number, previous_sha256=previous,
        event_id=f"EVNT-2026SIMUL{number:04d}",
        evidence_id="EVID-2026RIGHT1",
        kind=kind, key_id="KEY-SIMRIGHT01",
        nonce_hex=f"{number:032x}",
        published_at_utc=published,
        effective_at_utc=published,
        expires_at_utc=BASE + timedelta(hours=1) if candidate else None,
        scope_claims=(RightsScope.READ_HISTORICAL,
                      RightsScope.RESEARCH_BACKTEST) if candidate else (),
        signature_base64=SIGNATURE_PLACEHOLDER,
    )
    return replace(e, signature_base64=_sign(private, e.signing_bytes()))


def _pin(events: tuple[SignedRightsEvent, ...], event_pub: bytes,
         issued_at: datetime) -> ClaimedExternalLedgerPin:
    return ClaimedExternalLedgerPin(
        product=BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
        head_id="HEAD-2026SIMUL001", key_id="KEY-SIMRIGHT01",
        public_key_raw=event_pub,
        expected_public_key_sha256=sha256(event_pub).hexdigest(),
        expected_sequence=len(events),
        expected_tail_sha256=events[-1].chain_hash(),
        pinned_at_utc=issued_at,
    )


def _custody(event_pub: bytes, custody_private: Ed25519PrivateKey,
             events: tuple[SignedRightsEvent, ...], *,
             prior_sequence: int = 1):
    custody_pub = _public(custody_private)
    custodian = ClaimedCustodianKey(
        CustodyProduct.SSI_FASTCONNECT_OHLC, "KEY-SIMCUST01", 1,
        custody_pub, sha256(custody_pub).hexdigest(), "EVID-2026CUST01",
    )
    issuance = BASE - timedelta(seconds=20)
    head = SignedCustodyHead(
        product=CustodyProduct.SSI_FASTCONNECT_OHLC,
        head_id="HEAD-2026SIMUL001",
        custody_key_id=custodian.key_id, custody_epoch=1,
        event_key_id="KEY-SIMRIGHT01",
        event_public_key_sha256=sha256(event_pub).hexdigest(),
        sequence=len(events), tail_sha256=events[-1].chain_hash(),
        account_binding_sha256_claim="b" * 64,
        issued_at_utc=issuance, expires_at_utc=BASE + timedelta(minutes=3),
        signature_base64=SIGNATURE_PLACEHOLDER,
    )
    head = replace(head, signature_base64=_sign(custody_private, head.signing_bytes()))
    floor = ClaimedMonotonicFloor(
        product=CustodyProduct.SSI_FASTCONNECT_OHLC,
        custody_key_id=custodian.key_id,
        custody_key_sha256=custodian.public_key_sha256,
        custody_epoch=1,
        sequence=prior_sequence,
        tail_sha256=events[prior_sequence - 1].chain_hash(),
        account_binding_sha256_claim="b"*64,
        last_issued_at_utc=BASE-timedelta(minutes=1),
        observed_at_utc=BASE-timedelta(seconds=40),
        custody_evidence_id="EVID-2026FLOOR1",
    )
    return custodian, head, floor, issuance


def evaluate_source_custody_cache_matrix() -> dict:
    # 1. Positive *self-declared* rights scope never grants provider rights.
    product = BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC
    rights = UnverifiedRightsClaim(
        product, "EVID-2026RIGHT1", EvidenceKind.ACCOUNT_ENTITLEMENT_CLAIM,
        BASE-timedelta(minutes=5), tuple(RightsScope), "SIM1",
        30, BASE+timedelta(days=1),
    )
    report = review_unverified_source_claims(
        product, (rights,), reviewed_at_utc=BASE,
    )
    rights_all_claimed_but_unverified = (
        len(report.claimed_scopes_unverified) == len(RightsScope)
        and report.missing_scope_claims == ()
        and not report.provider_authorization_verified
        and not report.production_authorized
        and _denied(lambda: require_authorized_source(report))
    )
    if not rights_all_claimed_but_unverified:
        raise AssertionError("PROVIDER_SELF_CLAIM_PROMOTED_TO_LICENSE")

    # 2. Parse a fabricated SSI response; rows are counts, not real market bars.
    observation = summarize_source_capability(
        ProbeEndpoint.SSI_INTRADAY,
        {"status":"ok","data":{"ticks":[
            {"symbol":"FPT","trading_date":"2026-11-10"}
        ]}},
        symbol="FPT", checked_at_utc=BASE,
    )
    blockers = audit_backtest_evidence((observation,))
    probe_rows_not_entitlement = (
        observation.observed_rows == 1
        and not observation.source_rights_verified
        and not observation.historical_first_known_verified
        and not observation.eligible_for_backtest
        and not blockers.ready_for_historical_backtest
        and not blockers.actionable
    )
    if not probe_rows_not_entitlement:
        raise AssertionError("SSI_RESPONSE_SHAPE_PROMOTED_TO_SOURCE_AUTHORITY")

    # 3+4. TWO different fresh fixture signers, both controlled in ONE CI job.
    # Their signatures prove integrity under supplied keys but never vendor
    # identity, genuine external custody, revocation freshness or remote floor.
    event_private = Ed25519PrivateKey.generate()
    custody_private = Ed25519PrivateKey.generate()
    event_pub = _public(event_private)
    grant = _event(event_private, number=1, previous="0"*64,
                   kind=EventKind.GRANT_CANDIDATE)
    chain = (grant,)
    signer, head, floor, issued = _custody(
        event_pub, custody_private, chain,
    )
    pin = _pin(chain, event_pub, issued)
    rights_result = verify_pinned_rights_event_chain(
        chain, pin, checked_at_utc=BASE,
    )
    conditional = audit_conditional_custody_head(
        head, signer, floor, checked_at_utc=BASE,
        event_pin=pin, events=chain,
    )
    signed_grant_is_still_untrusted = (
        rights_result.state is RightsChainState.SIGNED_CANDIDATE_UNAUTHORIZED
        and rights_result.signature_integrity_verified
        and not rights_result.signer_authority_verified
        and not rights_result.permission_to_read_or_cache
        and conditional.custodian_signature_integrity
        and conditional.relative_floor_held
        and conditional.conditional_event_chain_integrity
        and not conditional.vendor_key_origin_verified
        and not conditional.anti_rollback_across_restarts_verified
        and not conditional.rights_to_read_or_cache
        and _denied(lambda: require_rights_chain_authorization(rights_result))
        and _denied(lambda: require_authenticated_provider_rights(conditional))
    )
    if not signed_grant_is_still_untrusted:
        raise AssertionError("TWO_FIXTURE_SIGNATURES_FALSLY_ATTESTED_PROVIDER")

    revoke = _event(event_private, number=2, previous=grant.chain_hash(),
                    kind=EventKind.PROVIDER_REVOKE)
    revoked_chain = (grant, revoke)
    signer2, head2, floor2, issued2 = _custody(
        event_pub, custody_private, revoked_chain,
    )
    pin2 = _pin(revoked_chain, event_pub, issued2)
    revoked_result = verify_pinned_rights_event_chain(
        revoked_chain, pin2, checked_at_utc=BASE,
    )
    revoked_custody = audit_conditional_custody_head(
        head2, signer2, floor2, checked_at_utc=BASE,
        event_pin=pin2, events=revoked_chain,
    )
    signed_revoke_still_blocks = (
        revoked_result.state is RightsChainState.SIGNED_HOLD_UNAUTHORIZED
        and not revoked_result.permission_to_read_or_cache
        and revoked_custody.conditional_event_chain_integrity
        and revoked_custody.event_chain_state == RightsChainState.SIGNED_HOLD_UNAUTHORIZED.value
        and not revoked_custody.rights_to_read_or_cache
    )
    if not signed_revoke_still_blocks:
        raise AssertionError("SIGNED_REVOKE_IMPROPERLY_REGRANTED_RIGHTS")
    # A stronger claimed floor refuses older signed but valid G1; this is
    # NOT a durable external floor: the SAME script controls all input claims.
    stale_head_rejected = _denied(
        lambda: audit_conditional_custody_head(
            head, signer, replace(floor, sequence=2, tail_sha256=revoke.chain_hash()),
            checked_at_utc=BASE, event_pin=pin, events=chain,
        ), CustodyRejected,
    )

    # 5+6. Metadata-only reference journal and recovery: no quote payload.
    with TemporaryDirectory(prefix="mst-a02-source-rights-journal-") as td:
        path = Path(td)
        journal = ReferenceJournal(path/"journal.sqlite")
        journal.initialize()
        initial_count, initial_tip = journal.verify()
        cp = create_candidate_journal_checkpoint(
            journal, path/"journal-backup.sqlite", "cp-A", "store-A", BASE,
        )
        pinned = type(cp).parse_json(cp.canonical_json())  # self-held, NOT independent.
        recovered = restore_journal_from_pinned(
            path/"journal-backup.sqlite", path/"journal-restored.sqlite",
            pinned, expected_store_id="store-A",
        )
        journal_recovery_metadata_only = (
            (initial_count, initial_tip) == (0, ZERO)
            and verify_journal_backup_against_pinned(
                path/"journal-backup.sqlite", pinned,
                expected_store_id="store-A",
            ) == (0, ZERO)
            and recovered.verify() == (0, ZERO)
            and cp.omitted_cache_rows == 0
            and cp.snapshot_kind == "METADATA_ONLY"
        )
        if not journal_recovery_metadata_only:
            raise AssertionError("REFERENCE_JOURNAL_RECOVERY_METADATA_PARITY_FAILED")

        # 7. WAL-aware empty fixture snapshot, never a physical Drive backup.
        store = SyntheticIncrementalStore(path/"synthetic.sqlite")
        store.initialize()
        snapshot = path/"snapshot.sqlite"
        mfpath = path/"snapshot.json"
        manifest = create_fixture_snapshot(
            store, snapshot, mfpath,
            snapshot_id="fixture1", generation=1,
            previous_manifest_sha256=None, created_at_utc=BASE,
        )
        checked = verify_fixture_snapshot(
            snapshot, mfpath.read_text(encoding="utf-8"),
            pinned_manifest_sha256=manifest.digest,
        )
        restored = restore_fixture_snapshot(
            snapshot, path/"restored.sqlite",
            mfpath.read_text(encoding="utf-8"),
            pinned_manifest_sha256=manifest.digest,
        )
        snapshot_empty_roundtrip = (
            checked == manifest and len(restored.read_bars(identity())) == 0
            and not manifest.live_market_data_authorized
            and not manifest.drive_upload_performed
            and _denied(require_approved_cache_transport)
        )
        if not snapshot_empty_roundtrip:
            raise AssertionError("OFFLINE_SNAPSHOT_TRUST_SCOPE_DRIFT")

    # 8. Synthetic in-memory chunk index, *not* actual Google Drive I/O.
    index = SyntheticDrivePartitionIndex()
    key = identity()
    closed = (bar(0),)
    created = index.stage_and_publish(
        key, closed, expected_head_sha256=None,
        created_at_utc=BASE,
    )
    pin_chunk = index.active_manifest_sha(key)
    loaded = index.load(key, pinned_manifest_sha256=pin_chunk)
    reused = index.stage_and_publish(
        key, closed, expected_head_sha256=pin_chunk,
        created_at_utc=BASE,
    )
    stale_writer_rejected = _denied(
        lambda: index.stage_and_publish(
            key, (bar(0, close=Decimal("150")),),
            expected_head_sha256=None, created_at_utc=BASE,
        ), ValueError,
    )
    partition_local_only = (
        created is PartitionWrite.CREATED
        and reused is PartitionWrite.REUSED
        and loaded == closed
        and stale_writer_rejected
        and _denied(require_real_market_cache_transport)
    )
    if not partition_local_only:
        raise AssertionError("SYNTHETIC_CHUNK_STATE_PROMOTED_TO_DRIVE_OR_RIGHTS")

    observations = {
        "self_claimed_all_rights_scopes_not_provider_license": rights_all_claimed_but_unverified,
        "ssi_response_shape_row_not_entitlement": probe_rows_not_entitlement,
        "two_ephemeral_signatures_not_independent_vendor_root": signed_grant_is_still_untrusted,
        "signed_revoke_is_hold_no_regrant": signed_revoke_still_blocks,
        "stale_signed_head_rejected_against_stronger_self_claimed_floor": stale_head_rejected,
        "journal_metadata_only_checkpoint_restore": journal_recovery_metadata_only,
        "offline_synthetic_snapshot_roundtrip_no_drive": snapshot_empty_roundtrip,
        "synthetic_partition_chunk_pin_and_stale_writer": partition_local_only,
    }
    if not all(observations.values()):
        raise AssertionError("A02_SECOND_EIGHT_V1_RUNTIME_SECURITY_MATRIX_FAILED")
    result = {
        "schema": SCHEMA,
        "status": "EIGHT_SOURCE_CUSTODY_CACHE_REAL_V1_RUNTIME_GUARDS_PASS_PRODUCTION_NO_GO",
        "source_upstream": SOURCE_SHA,
        "source_main": MAIN_SHA,
        "executed_original_modules": list(EIGHT),
        "executed_count": len(EIGHT),
        "scenario_count": len(observations),
        "scenarios": observations,
        "actual_private_source_identity_or_vendor_auth": False,
        "two_independently_controlled_real_signers": False,
        "external_monotonic_floor_proven": False,
        "real_provider_revocation_freshness_proven": False,
        "physical_google_drive_cache_read_write": False,
        "actual_reference_market_quotes_retained": False,
        "a02_owner_signed_modules": 0,
        "a03_full_v2_behavior_abi_parity": False,
        "g01_g08_independent_owner_gates_closed": False,
        "production_market_data_read_authorized": False,
        "production_market_data_write_authorized": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }
    result["scenario_receipt_sha256"] = sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = evaluate_source_custody_cache_matrix()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
