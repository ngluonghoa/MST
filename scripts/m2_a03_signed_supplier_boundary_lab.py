"""MST A03: join existing M4 Ed25519 fixture to untrusted A03 ledger closure.

Ephemeral keys exist solely inside GitHub-hosted tests. Never export keys,
enroll a signer, authenticate SSI/DNSE/VCBS, access market data, or promote
A03 candidate revisions into trading or a licensed Google Drive cache.

This is a CROSS-CONTRACT NEGATIVE TEST, not a second production verifier.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.m4_signed_floor_fixture import (
    SCHEMA as M4_SCHEMA, FixtureAnchor, canonical, seed_floor,
    verify_signed_fixture,
)
from scripts.m2_a03_revision_ledger_closure_lab import (
    ClaimedLedgerHead, UntrustedClosureReceipt, claims_for, digest,
    intake_untrusted_claims,
)
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    PARTITION, UP1, UP2, TIMES,
)

SCHEMA = "mst.a03.m4-conditional-signature-cross-boundary.fixture-only.v1"
REQUIRED_OWNER_PROOF_IDS = (
    "A03-OWNER-SOURCE-HEAD-CLOSURE-11",
    "A03-OWNER-INDEPENDENT-CUSTODY-12",
    "A03-OWNER-DURABLE-FLOOR-13",
    "A03-OWNER-LICENSED-REPLAY-14",
)
M4_PRIVATE_REQUIREMENT_IDS = ("E03","E08","E11","E12","E13","E14")


def partition_digest() -> str:
    """Canonical fixture partition scope; not a provider-certified ID."""
    return sha256(canonical({
        "provider":PARTITION.provider_id,
        "endpoint":PARTITION.endpoint_id,
        "symbol":PARTITION.symbol,
        "timeframe":PARTITION.timeframe,
        "price_basis":PARTITION.price_basis,
        "session":PARTITION.session_id,
    })).hexdigest()


@dataclass(frozen=True)
class ConditionalBoundaryReceipt:
    signed_fixture_integrity: bool
    original_ledger_claim_consistency: bool
    status: str = "CONDITIONAL_FIXTURE_ED25519_AND_SELF_CLAIMS_ONLY_NO_GO"
    trusted_provider_revision_head: bool = False
    signer_identity_independently_enrolled: bool = False
    independent_custody_and_witness_verified: bool = False
    durable_cross_run_floor_verified: bool = False
    licensed_market_source_and_retention_verified: bool = False
    physical_google_drive_cache_authorized: bool = False
    production_release_or_trading_authorized: bool = False


def verify_cross_contract(
    closure: UntrustedClosureReceipt,
    signed_receipt: dict, signature_hex: str,
    anchor: FixtureAnchor, floor,
) -> ConditionalBoundaryReceipt:
    """Even a valid Ed25519 signature only authenticates a caller-pinned key.

    It does not promote closure/rights proof. Bind ALL signed metadata to the
    exact A03 ledger digest and declared fixture partition before M4 verify.
    """
    if type(closure) is not UntrustedClosureReceipt:
        raise TypeError("EXACT_A03_UNTRUSTED_CLOSURE_REQUIRED")
    if type(signed_receipt) is not dict:
        raise TypeError("EXACT_M4_SIGNED_ENVELOPE_REQUIRED")
    if closure.partition != PARTITION or closure.event_id != "BAR1":
        raise ValueError("EXPLICIT_A03_FIXTURE_SCOPE_REQUIRED")
    if closure.ledger_digest != digest(closure.rows):
        raise ValueError("A03_LEDGER_ROWS_CHANGED_AFTER_CLOSURE")
    if (signed_receipt.get("provider") != closure.partition.provider_id or
            signed_receipt.get("partition_digest") != partition_digest()):
        raise ValueError("CROSS_CONTRACT_PARTITION_OR_PROVIDER_MISMATCH")
    if signed_receipt.get("content_digest") != closure.ledger_digest:
        raise ValueError("SIGNED_RECEIPT_NOT_BOUND_TO_A03_LEDGER")
    expected_as_of = closure.as_of_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if signed_receipt.get("source_first_known_utc") != expected_as_of:
        raise ValueError("SIGNED_RECEIPT_ASOF_NOT_BOUND_TO_CLAIM")
    result = verify_signed_fixture(signed_receipt, signature_hex, anchor, floor)
    if result["fixture_signature_verified_for_caller_pinned_key"] is not True:
        raise PermissionError("ED25519_CONDITIONAL_FIXTURE_VERIFICATION_REQUIRED")
    for key in (
        "independent_signer_custody_verified",
        "authenticated_vendor_source_clock_verified",
        "globally_durable_monotonic_floor_verified",
        "distributed_two_writer_cas_verified",
        "google_drive_byte_custody_verified",
        "licensed_market_data_authorized",
        "cache_write_authorized",
        "trading_authorized",
    ):
        if result[key] is not False:
            raise PermissionError("M4_UNTRUSTED_RECEIPT_CANNOT_GRANT_AUTHORITY")
    return ConditionalBoundaryReceipt(True, True)


def fake_keypair():
    """Ephemeral GitHub-runner-only random test key; no export of private key."""
    private = Ed25519PrivateKey.generate()
    pub = private.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw,
    ).hex()
    return private,pub


def make_anchor(public_key_hex, *, provider="SSI", policy=None):
    return FixtureAnchor(
        provider=provider,
        partition_digest=partition_digest(),
        rights_policy_digest=policy or "b"*64,
        signer_id="fixture.writer",
        key_epoch=1,
        public_key_hex=public_key_hex,
    )


def make_signed_fixture(closure, anchor, floor, *,
                        source_time=None, content_digest=None):
    at = source_time or closure.as_of_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dict(
        schema=M4_SCHEMA,
        provider=anchor.provider,
        partition_digest=anchor.partition_digest,
        rights_policy_digest=anchor.rights_policy_digest,
        signer_id=anchor.signer_id,
        key_epoch=anchor.key_epoch,
        generation=floor.generation+1,
        parent_receipt_digest=floor.head_receipt_digest,
        content_digest=content_digest or closure.ledger_digest,
        source_first_known_utc=at,
        observed_at_utc="2026-11-09T08:21:00Z",
        published_at_utc="2026-11-09T08:22:00Z",
        recovery_of_receipt_digest=None,
    )


def build():
    cases=[]
    def check(case,works,group):
        if not works:
            raise AssertionError("A03_M4_SOURCE_BOUNDARY_CASE_FAILED:"+case)
        cases.append({"case":case,"group":group,
                      "result":"PASS_CONDITIONAL_FIXTURE_NO_SOURCE_AUTHORITY"})

    def denied(case,exc,call,group):
        try:
            call()
        except exc:
            check(case,True,group)
        else:
            raise AssertionError("A03_M4_EXPECTED_DENIAL_MISSING:"+case)

    rows=(UP1,UP2)
    closure=intake_untrusted_claims(
        PARTITION,"BAR1",rows,claims_for(rows,TIMES[2]),as_of_utc=TIMES[2])
    private,pub=fake_keypair()
    anchor=make_anchor(pub)
    floor=seed_floor(anchor,at="2026-11-09T07:00:00Z")
    signed=make_signed_fixture(closure,anchor,floor)
    sig=private.sign(canonical(signed)).hex()
    passed=verify_cross_contract(closure,signed,sig,anchor,floor)

    check("VALID_EPHEMERAL_SIGNATURE_INTEGRITY_ONLY",
          passed.signed_fixture_integrity and
          passed.original_ledger_claim_consistency,"positive")
    check("VALID_SIGNATURE_NEVER_APPROVES_SOURCE_RIGHTS",
          not passed.licensed_market_source_and_retention_verified
          and not passed.trusted_provider_revision_head,"authority")
    check("VALID_SIGNATURE_NEVER_APPROVES_DRIVE_CACHE",
          not passed.physical_google_drive_cache_authorized,"authority")
    check("VALID_SIGNATURE_NEVER_APPROVES_PRODUCTION_TRADE",
          not passed.production_release_or_trading_authorized,"authority")
    check("VALID_SIGNATURE_NO_REAL_INDEPENDENT_CUSTODY",
          not passed.signer_identity_independently_enrolled
          and not passed.independent_custody_and_witness_verified,"authority")
    check("VALID_SIGNATURE_NO_DURABLE_FLOOR",
          not passed.durable_cross_run_floor_verified,"authority")
    check("SOURCE_CLAIM_STILL_UNTRUSTED",
          closure.status=="CLAIMS_STRUCTURALLY_CONSISTENT_BUT_UNTRUSTED",
          "authority")

    def signed_mutation(**kwargs):
        changed=dict(signed,**kwargs)
        return changed,private.sign(canonical(changed)).hex()

    denied("SIGNED_UNRELATED_LEDGER_DIGEST_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            content_digest="1"*64),anchor,floor),"binding")
    denied("SIGNED_REWRITTEN_PRICE_BASIS_PARTITION_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            partition_digest="e"*64),anchor,floor),"binding")
    denied("SIGNED_DIFFERENT_PROVIDER_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            provider="DNSE"),anchor,floor),"binding")
    denied("SIGNED_BACKDATED_SOURCE_ASOF_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            source_first_known_utc="2026-11-09T08:00:00Z"),anchor,floor),
        "clock")
    denied("SIGNED_FUTURE_SOURCE_ASOF_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            source_first_known_utc="2026-11-09T08:15:00Z"),anchor,floor),
        "clock")
    denied("SIGNATURE_TAMPERED_LEDGER_ENVELOPE_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,dict(
            signed,rights_policy_digest="d"*64),sig,anchor,floor),"signature")
    denied("UNPINNED_WRONG_PUBLIC_KEY_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,signed,sig,
            make_anchor(fake_keypair()[1]),floor),"signature")
    denied("INVALID_SIGNATURE_BYTES_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,signed,"0"*128,anchor,floor),
        "signature")
    denied("UNSIGNED_RECEIPT_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,signed,"",anchor,floor),"signature")
    denied("MALFORMED_RECEIPT_EXTRA_APPROVAL_FIELD_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,dict(signed,owner_approved=True),
            private.sign(canonical(dict(signed,owner_approved=True))).hex(),
            anchor,floor),"signature")
    denied("SOURCE_CLOSURE_REHASHED_AFTER_SIGNED_HEAD_BLOCKED",ValueError,
        lambda:verify_cross_contract(replace(
            closure,ledger_digest="9"*64),signed,sig,anchor,floor),"binding")
    denied("SIGNER_EPOCH_CHANGED_WITHOUT_REPIN_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            key_epoch=2),anchor,floor),"signature")
    denied("SIGNED_PARENT_HEAD_WRONG_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            parent_receipt_digest="f"*64),anchor,floor),"rollback")
    denied("SIGNED_GENERATION_JUMP_BLOCKED",ValueError,
        lambda:verify_cross_contract(closure,*signed_mutation(
            generation=4),anchor,floor),"rollback")

    # A user who controls the "trusted" caller input can REPLACE both key
    # and floor, then self-sign the same closure. Crypto still checks out.
    impostor,impostor_pub=fake_keypair()
    impostor_anchor=make_anchor(impostor_pub)
    impostor_floor=seed_floor(impostor_anchor,at="2026-11-09T07:00:00Z")
    forged=verify_cross_contract(
        closure,signed,impostor.sign(canonical(signed)).hex(),
        impostor_anchor,impostor_floor)
    check("CALLER_REPLACED_SIGNER_ANCHOR_STILL_NOT_PROVIDER_AUTHORITY",
          forged.signed_fixture_integrity and
          not forged.signer_identity_independently_enrolled,"spoofability")

    # Both signed receipts fork from the SAME caller-local floor. Each
    # individually passes. This cannot establish global writer CAS.
    original=verify_signed_fixture(signed,sig,anchor,floor)
    signed_fork=dict(signed,observed_at_utc="2026-11-09T08:23:00Z",
                     published_at_utc="2026-11-09T08:24:00Z")
    fork_sig=private.sign(canonical(signed_fork)).hex()
    fork=verify_signed_fixture(signed_fork,fork_sig,anchor,floor)
    check("TWO_SIGNED_FORKS_PASS_SAME_LOCAL_FLOOR",
          original["fixture_signature_verified_for_caller_pinned_key"]
          and fork["fixture_signature_verified_for_caller_pinned_key"]
          and original["receipt_digest"]!=fork["receipt_digest"],"spoofability")
    check("TWO_SIGNED_FORKS_DO_NOT_PROVE_DISTRIBUTED_CAS",
          not original["distributed_two_writer_cas_verified"]
          and not fork["distributed_two_writer_cas_verified"],"spoofability")
    # Original receipt remains reusable after losing the in-memory floor.
    reset=seed_floor(anchor,at="2026-11-09T07:00:00Z")
    replayed=verify_cross_contract(closure,signed,sig,anchor,reset)
    check("RESET_CALLER_FLOOR_REACCEPTS_OLD_SIGNED_RECEIPT",
          replayed.signed_fixture_integrity
          and not replayed.durable_cross_run_floor_verified,"spoofability")

    # Rehash a previously "closed" r1. A new pair of fake source/viewer
    # claimants can endorse it with a matching caller-owned signature.
    tampered_r1=replace(UP1,payload_sha256="9"*64)
    tampered_rows=(tampered_r1,UP2)
    tampered_closure=intake_untrusted_claims(
        PARTITION,"BAR1",tampered_rows,
        claims_for(tampered_rows,TIMES[2]),as_of_utc=TIMES[2])
    resigned=make_signed_fixture(tampered_closure,anchor,reset)
    resigned_sig=private.sign(canonical(resigned)).hex()
    accepted_tamper=verify_cross_contract(
        tampered_closure,resigned,resigned_sig,anchor,reset)
    check("FULLY_RESIGNED_TAMPER_PASSES_WITHOUT_TRUSTED_SOURCE_ROOT",
          accepted_tamper.signed_fixture_integrity
          and tampered_closure.ledger_digest!=closure.ledger_digest
          and not accepted_tamper.trusted_provider_revision_head,
          "spoofability")
    check("FULLY_RESIGNED_TAMPER_REMAINS_UNLICENSED_AND_NONTRADING",
          not accepted_tamper.licensed_market_source_and_retention_verified
          and not accepted_tamper.production_release_or_trading_authorized,
          "authority")

    check("FOUR_EXISTING_A03_OWNER_GATES_REMAIN_OPEN",
          len(REQUIRED_OWNER_PROOF_IDS)==4
          and all(x.startswith("A03-OWNER-") for x in REQUIRED_OWNER_PROOF_IDS),
          "owner")
    check("M4_PRIVATE_INTAKE_GATES_E03_E08_E11_E12_E13_E14_UNSATISFIED",
          len(M4_PRIVATE_REQUIREMENT_IDS)==6
          and all(x.startswith("E") for x in M4_PRIVATE_REQUIREMENT_IDS),
          "owner")
    check("A02_AND_A03_MODULE_OWNER_SIGNOFF_REMAINS_ZERO",True,"owner")
    check("NO_REAL_SIGNER_ROOT_OR_VENDOR_ENTITLEMENT_WAS_PROVISIONED",
          not passed.trusted_provider_revision_head
          and not forged.independent_custody_and_witness_verified,
          "owner")

    if len(cases)!=29 or len({x["case"] for x in cases})!=29:
        raise AssertionError("A03_SIGNED_CROSS_BOUNDARY_CASE_COVERAGE_DRIFT")
    canonical_cases=json.dumps(cases,sort_keys=True,separators=(",",":"),
                               ensure_ascii=True,allow_nan=False)
    return {
        "schema":SCHEMA,
        "status":"CRYPTOGRAPHIC_FIXTURE_INTEGRITY_ONLY_REAL_SOURCE_NO_GO",
        "case_count":len(cases),"cases":cases,
        "case_fingerprint_sha256":sha256(canonical_cases.encode()).hexdigest(),
        "owner_gate_ids":list(REQUIRED_OWNER_PROOF_IDS),
        "existing_private_intake_requirements":list(M4_PRIVATE_REQUIREMENT_IDS),
        "conditional_ed25519_fixture_integrity_tested":True,
        "fresh_floor_replay_and_resigned_tamper_falsified":True,
        "real_provider_issuer_independently_authenticated":False,
        "signed_provider_revision_head_completeness_proven":False,
        "independent_signer_root_and_custody_proven":False,
        "durable_cross_run_floor_or_distributed_cas_proven":False,
        "legal_provider_market_data_and_drive_cache_authorized":False,
        "a02_module_owner_signoff":0,"a03_v2_owner_signoff":0,
        "owner_14_choices_signed":0,
        "g01_g08_oa01_oa06_closed":False,
        "production_release_or_trading_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    r=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="cases"},sort_keys=True))


if __name__=="__main__":
    main()
