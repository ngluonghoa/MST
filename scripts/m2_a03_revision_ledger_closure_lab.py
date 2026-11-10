"""MST A03 two-claim revision-ledger closure *falsification*, NOT verification.

Two self-described source/viewer metadata claims are untrusted even when all
fields agree. This isolated GitHub-hosted fixture never calls a vendor, verifies
cryptographic attestations, provisions a signer/CAS or authorizes market cache.
Existing 63 inherited V1 and eight pre-existing V2 sources are unchanged.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path

from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    PARTITION, UP1, UP2, TOMB, FixturePartition, FixtureRevision, T0, TIMES,
    resolve_untrusted_fixture, utc, name,
)

SCHEMA = "mst.a03.claimed-revision-ledger-closure-untrusted.v1"


class ClaimRole(str, Enum):
    SOURCE = "SOURCE"
    VIEWER = "VIEWER"


def canonical_rows(rows: tuple[FixtureRevision, ...]) -> str:
    """Deterministic hash input, NOT a provider-signed Merkle commitment."""
    if type(rows) is not tuple or not rows:
        raise TypeError("Nonempty immutable revision tuple required")
    if any(type(r) is not FixtureRevision for r in rows):
        raise TypeError("Only exact typed fixture revisions")
    return json.dumps(
        [{
            "partition": {
                "provider": r.partition.provider_id,
                "endpoint": r.partition.endpoint_id,
                "symbol": r.partition.symbol,
                "timeframe": r.partition.timeframe,
                "price_basis": r.partition.price_basis,
                "session": r.partition.session_id,
            },
            "event_id": r.event_id,
            "revision_id": r.revision_id,
            "sequence": r.sequence,
            "kind": r.kind.value,
            "event_time_utc": r.event_time_utc.isoformat(),
            "first_known_utc": r.first_known_utc.isoformat(),
            "supersedes": r.supersedes_revision_id,
            "payload_digest": r.payload_sha256,
        } for r in rows], ensure_ascii=True, sort_keys=True,
        allow_nan=False, separators=(",", ":"),
    )


def digest(rows: tuple[FixtureRevision, ...]) -> str:
    return sha256(canonical_rows(rows).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class ClaimedLedgerHead:
    """Untrusted declaration. Actor IDs and custody domains are self-supplied."""

    role: ClaimRole
    actor_id: str
    custody_domain: str
    partition: FixturePartition
    event_id: str
    snapshot_as_of_utc: datetime
    observed_at_utc: datetime
    head_sequence: int
    head_revision_id: str
    ledger_digest: str
    claimed_closed_through_utc: datetime

    def __post_init__(self):
        if type(self.role) is not ClaimRole:
            raise TypeError("Explicit source or viewer claim role required")
        name(self.actor_id)
        name(self.custody_domain)
        name(self.event_id)
        name(self.head_revision_id)
        if type(self.partition) is not FixturePartition:
            raise TypeError("Exact partition identity required")
        at = utc(self.snapshot_as_of_utc)
        observed = utc(self.observed_at_utc)
        closed = utc(self.claimed_closed_through_utc)
        if observed < at or closed != at:
            raise ValueError("Claim custody/as-of closure timestamps conflict")
        if type(self.head_sequence) is not int or self.head_sequence < 1:
            raise ValueError("Head sequence must be positive exact integer")
        if type(self.ledger_digest) is not str or len(self.ledger_digest) != 64:
            raise ValueError("Full opaque SHA256 digest required")
        if any(x not in "0123456789abcdef" for x in self.ledger_digest):
            raise ValueError("Lowercase hex digest required")


@dataclass(frozen=True)
class UntrustedClosureReceipt:
    partition: FixturePartition
    event_id: str
    as_of_utc: datetime
    rows: tuple[FixtureRevision, ...]
    head_sequence: int
    head_revision_id: str
    ledger_digest: str
    candidate_status: str
    status: str = "CLAIMS_STRUCTURALLY_CONSISTENT_BUT_UNTRUSTED"
    verified_provider_signature: bool = False
    verified_independent_custody: bool = False
    verified_server_cas: bool = False
    trusted_nonresettable_floor: bool = False
    actual_source_history_complete: bool = False
    real_source_rights_or_cache_authorized: bool = False
    production_or_trading_authorized: bool = False


def intake_untrusted_claims(
    partition: FixturePartition, event_id: str,
    rows: tuple[FixtureRevision, ...],
    claims: tuple[ClaimedLedgerHead, ClaimedLedgerHead],
    *, as_of_utc: datetime,
    prior: UntrustedClosureReceipt | None = None,
) -> UntrustedClosureReceipt:
    """Fail closed for mismatching declarations, never authenticate them.

    Two different fixture IDs/domains prove only that strings differ, NOT that
    independent human principals, permissions or trust roots actually exist.
    """
    if type(partition) is not FixturePartition:
        raise TypeError("Exact typed partition required")
    name(event_id)
    at = utc(as_of_utc)
    if type(rows) is not tuple or not rows:
        raise ValueError("EMPTY_OR_NONIMMUTABLE_LOG_CANNOT_PROVE_CLOSURE")
    if any(type(row) is not FixtureRevision for row in rows):
        raise TypeError("Untyped revision row")
    if type(claims) is not tuple or len(claims) != 2:
        raise ValueError("EXACT_SOURCE_AND_VIEWER_CLAIMS_REQUIRED")
    if any(type(claim) is not ClaimedLedgerHead for claim in claims):
        raise TypeError("Exact untrusted claims required")
    source, viewer = claims
    if (source.role is not ClaimRole.SOURCE or viewer.role is not ClaimRole.VIEWER):
        raise ValueError("SOURCE_VIEWER_ROLES_MUST_BE_EXPLICIT")
    if source.actor_id == viewer.actor_id or source.custody_domain == viewer.custody_domain:
        raise ValueError("DECLARED_INDEPENDENCE_NOT_DISTINCT")
    if (source.actor_id == source.custody_domain or
            viewer.actor_id == viewer.custody_domain):
        raise ValueError("AMBIGUOUS_ID_AND_CUSTODY_DOMAIN")
    for claim in claims:
        if claim.partition != partition or claim.event_id != event_id:
            raise ValueError("CROSS_SCOPE_CLAIM_DENIED")
        if claim.snapshot_as_of_utc != at or claim.claimed_closed_through_utc != at:
            raise ValueError("SNAPSHOT_OR_CLOSURE_ASOF_MISMATCH")
    if any(r.partition != partition or r.event_id != event_id for r in rows):
        raise ValueError("MIXED_PARTITION_OR_EVENT_ROWS")
    if any(r.first_known_utc > at or r.event_time_utc > at for r in rows):
        raise ValueError("FUTURE_KNOWN_REVISION_IN_CLOSED_SNAPSHOT")
    ordered = tuple(sorted(rows, key=lambda r: r.sequence))
    # The existing separate A03 fixture resolver checks contiguous revisions,
    # exact predecessors and strict first-known progress. NOT provider proof.
    candidate = resolve_untrusted_fixture(partition,event_id,ordered,as_of_utc=at)
    if len(candidate.visible_revision_ids) != len(ordered):
        raise ValueError("UNEXPECTED_HIDDEN_ROW_IN_CLOSED_SNAPSHOT")
    calculated = digest(ordered)
    latest = ordered[-1]
    for claim in claims:
        if claim.head_sequence != len(ordered) or latest.sequence != len(ordered):
            raise ValueError("CLAIMED_HEAD_SEQUENCE_DOES_NOT_CLOSE_LOG")
        if claim.head_revision_id != latest.revision_id:
            raise ValueError("HEAD_REVISION_ID_MISMATCH")
        if claim.ledger_digest != calculated:
            raise ValueError("SELF_REPORTED_DIGEST_MISMATCH")
    if prior is not None:
        if type(prior) is not UntrustedClosureReceipt:
            raise TypeError("Prior closure must be exact typed fixture receipt")
        if prior.partition != partition or prior.event_id != event_id:
            raise ValueError("CROSS_SCOPE_PRIOR_HEAD")
        if at < prior.as_of_utc:
            raise ValueError("SNAPSHOT_CLOCK_REWIND_DENIED")
        if len(ordered) < prior.head_sequence:
            raise ValueError("LOCAL_MEMORY_HEAD_ROLLBACK_DENIED")
        if ordered[:prior.head_sequence] != prior.rows:
            raise ValueError("HISTORICAL_PREFIX_MUTATION_DENIED")
        if digest(prior.rows) != prior.ledger_digest:
            raise ValueError("PRIOR_SELF_REPORTED_DIGEST_INCONSISTENT")
        if len(ordered) == prior.head_sequence and calculated != prior.ledger_digest:
            raise ValueError("SAME_HEIGHT_CHANGING_DIGEST_DENIED")
    return UntrustedClosureReceipt(
        partition,event_id,at,ordered,len(ordered),latest.revision_id,
        calculated,candidate.status,
    )


SOURCE_ACTOR = "fixture.source.claimant"
VIEWER_ACTOR = "fixture.viewer.claimant"
SOURCE_DOMAIN = "fixture.source.custody"
VIEWER_DOMAIN = "fixture.viewer.custody"


def claims_for(
    rows: tuple[FixtureRevision, ...], at: datetime,
    *, source_changes: dict | None = None, viewer_changes: dict | None = None,
) -> tuple[ClaimedLedgerHead, ClaimedLedgerHead]:
    """Construct fake metadata receipts with independent-looking strings."""
    ordered=tuple(sorted(rows,key=lambda r:r.sequence))
    head=ordered[-1]
    common=dict(partition=PARTITION,event_id="BAR1",snapshot_as_of_utc=at,
                observed_at_utc=TIMES[-1],head_sequence=len(ordered),
                head_revision_id=head.revision_id,ledger_digest=digest(ordered),
                claimed_closed_through_utc=at)
    sc=dict(common,role=ClaimRole.SOURCE,actor_id=SOURCE_ACTOR,
            custody_domain=SOURCE_DOMAIN)
    vc=dict(common,role=ClaimRole.VIEWER,actor_id=VIEWER_ACTOR,
            custody_domain=VIEWER_DOMAIN)
    sc.update(source_changes or {})
    vc.update(viewer_changes or {})
    return ClaimedLedgerHead(**sc),ClaimedLedgerHead(**vc)


OWNER_CHOICES=(
    {"id":"A03-OWNER-SOURCE-HEAD-CLOSURE-11",
     "required":"External provider-authenticated closure/root and revision export scope",
     "owner_signed":False},
    {"id":"A03-OWNER-INDEPENDENT-CUSTODY-12",
     "required":"Independent signer/viewer provenance beyond claimed actor/domain strings",
     "owner_signed":False},
    {"id":"A03-OWNER-DURABLE-FLOOR-13",
     "required":"Nonresettable durable cross-run source high-watermark and prior receipt recovery",
     "owner_signed":False},
    {"id":"A03-OWNER-LICENSED-REPLAY-14",
     "required":"Live provider entitlement/retention, historical correction semantics and Drive cache rights",
     "owner_signed":False},
)


def build() -> dict:
    cases=[]
    def check(label,ok,group):
        if not ok:
            raise AssertionError("A03_UNTRUSTED_LEDGER_CLOSURE_CASE:"+label)
        cases.append({"case":label,"group":group,"result":"PASS_FIXTURE_NO_AUTHORITY"})

    def rejects(label,expected,action,group):
        try:
            action()
        except expected:
            check(label,True,group)
        else:
            raise AssertionError("A03_FAIL_CLOSED_EXPECTED:"+label)

    ordered=(UP1,UP2,TOMB)
    s1=tuple(ordered[:1])
    s2=tuple(ordered[:2])
    r1=intake_untrusted_claims(PARTITION,"BAR1",s1,claims_for(s1,TIMES[0]),
                                as_of_utc=TIMES[0])
    check("SINGLE_ROOT_NO_AUTHORITY",r1.head_revision_id=="r1"
          and not r1.actual_source_history_complete,"positive")
    r1_later=intake_untrusted_claims(PARTITION,"BAR1",s1,claims_for(s1,TIMES[1]),
                                    as_of_utc=TIMES[1],prior=r1)
    check("UNCHANGED_HEAD_NEXT_ASOF_ALLOWED_STRUCTURALLY",
          r1_later.head_sequence==1 and r1_later.ledger_digest==r1.ledger_digest,
          "positive")
    r2=intake_untrusted_claims(PARTITION,"BAR1",s2,claims_for(s2,TIMES[2]),
                               as_of_utc=TIMES[2],prior=r1_later)
    check("NEW_REVISION_EXTENDS_PREVIOUS_PREFIX",r2.head_revision_id=="r2"
          and r2.head_sequence==2,"positive")
    r3=intake_untrusted_claims(PARTITION,"BAR1",ordered,
                               claims_for(ordered,TIMES[3]),
                               as_of_utc=TIMES[3],prior=r2)
    check("TOMBSTONE_STAYS_UNVERIFIED",r3.candidate_status=="UNVERIFIED_TOMBSTONED"
          and r3.head_revision_id=="r3","positive")
    later=intake_untrusted_claims(PARTITION,"BAR1",ordered,
                                  claims_for(ordered,TIMES[4]),
                                  as_of_utc=TIMES[4],prior=r3)
    check("NO_REPAINT_ON_SAME_HEAD",later.ledger_digest==r3.ledger_digest,
          "positive")
    check("EXPLICIT_TWO_CLAIMS_NOT_TRUE_INDEPENDENCE",
          not r3.verified_independent_custody and not r3.verified_provider_signature,
          "authority")
    check("NEVER_GRANTS_MARKET_RIGHTS_CACHE_OR_TRADE",
          not any(getattr(r3,k) for k in (
              "verified_server_cas","trusted_nonresettable_floor",
              "actual_source_history_complete","real_source_rights_or_cache_authorized",
              "production_or_trading_authorized")),"authority")
    check("REPORT_CANDIDATE_IS_NOT_TRADING_SIGNAL",
          r2.candidate_status=="UNVERIFIED_CANDIDATE_UPSERT"
          and r3.candidate_status=="UNVERIFIED_TOMBSTONED","authority")

    rejects("ONLY_ONE_CLAIM_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  (claims_for(s1,TIMES[0])[0],),as_of_utc=TIMES[0]),"claims")
    rejects("SWAPPED_SOURCE_VIEWER_ROLES_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  tuple(reversed(claims_for(s1,TIMES[0]))),
                  as_of_utc=TIMES[0]),"claims")
    rejects("SAME_ACTOR_STRING_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],
                      viewer_changes={"actor_id":SOURCE_ACTOR}),
                  as_of_utc=TIMES[0]),"claims")
    rejects("SAME_CUSTODY_DOMAIN_STRING_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],
                      viewer_changes={"custody_domain":SOURCE_DOMAIN}),
                  as_of_utc=TIMES[0]),"claims")
    rejects("ACTOR_CUSTODY_AMBIGUITY_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],
                      source_changes={"actor_id":SOURCE_DOMAIN}),
                  as_of_utc=TIMES[0]),"claims")
    rejects("CLAIMED_PROVIDER_DIFFERENT_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],viewer_changes={
                      "partition":FixturePartition("DNSE","fixture.dnse.d1",
                         "TEST","M5","RAW","TESTSESSION")}),
                  as_of_utc=TIMES[0]),"scope")
    rejects("CLAIMED_DIFFERENT_EVENT_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],viewer_changes={"event_id":"BAR2"}),
                  as_of_utc=TIMES[0]),"scope")
    rejects("CLAIMED_PRICE_BASIS_CHANGED_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],viewer_changes={
                      "partition":FixturePartition("SSI","fixture.ssi.d1",
                         "TEST","M5","ADJUSTED","TESTSESSION")}),
                  as_of_utc=TIMES[0]),"scope")
    rejects("CLAIMED_CLOSURE_BEFORE_SNAPSHOT_DENIED",ValueError,
            lambda:claims_for(s1,TIMES[0],viewer_changes={
                 "claimed_closed_through_utc":T0-timedelta(minutes=1)}),"clock")
    rejects("CLAIMED_OBSERVED_BEFORE_SNAPSHOT_DENIED",ValueError,
            lambda:claims_for(s1,TIMES[0],viewer_changes={
                 "observed_at_utc":T0-timedelta(minutes=1)}),"clock")
    rejects("CLAIMED_SNAPSHOT_ASOF_MISMATCH_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],
                     viewer_changes={"snapshot_as_of_utc":TIMES[1],
                                     "claimed_closed_through_utc":TIMES[1]}),
                  as_of_utc=TIMES[0]),"clock")
    rejects("CLAIMED_HEAD_SEQUENCE_LOWER_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[2],viewer_changes={"head_sequence":1}),
                  as_of_utc=TIMES[2]),"head")
    rejects("CLAIMED_HEAD_SEQUENCE_GREATER_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[2],viewer_changes={"head_sequence":3}),
                  as_of_utc=TIMES[2]),"head")
    rejects("CLAIMED_HEAD_REVISION_MISMATCH_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[2],viewer_changes={"head_revision_id":"r9"}),
                  as_of_utc=TIMES[2]),"head")
    rejects("CLAIMED_VIEWER_DIGEST_MISMATCH_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[2],viewer_changes={"ledger_digest":"f"*64}),
                  as_of_utc=TIMES[2]),"head")
    rejects("CLAIMED_SOURCE_DIGEST_MISMATCH_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[2],source_changes={"ledger_digest":"0"*64}),
                  as_of_utc=TIMES[2]),"head")
    rejects("BAD_NONHEX_CLAIMED_DIGEST_DENIED",ValueError,
            lambda:claims_for(s1,TIMES[0],source_changes={"ledger_digest":"g"*64}),
            "validation")
    rejects("BOOLEAN_HEAD_SEQUENCE_DENIED",ValueError,
            lambda:claims_for(s1,TIMES[0],source_changes={"head_sequence":True}),
            "validation")
    rejects("EMPTY_CLOSED_SNAPSHOT_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",(),
                  claims_for(s1,TIMES[0]),as_of_utc=TIMES[0]),"head")
    rejects("LIST_REVISION_ROWS_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",list(s1),
                  claims_for(s1,TIMES[0]),as_of_utc=TIMES[0]),"validation")
    rejects("UNTYPED_REVISION_ROW_DENIED",TypeError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",(object(),),
                  claims_for(s1,TIMES[0]),as_of_utc=TIMES[0]),"validation")
    rejects("FUTURE_ROW_IN_HISTORICAL_CLOSURE_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s2,
                  claims_for(s2,TIMES[0]),as_of_utc=TIMES[0]),"clock")
    rejects("MISSING_ROOT_WITH_HIGH_HEAD_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",(UP2,),
                  claims_for((UP2,),TIMES[2]),as_of_utc=TIMES[2]),"head")
    rejects("MISSING_MIDDLE_REVISION_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",(UP1,TOMB),
                  claims_for((UP1,TOMB),TIMES[3]),as_of_utc=TIMES[3]),"head")
    rejects("DUPLICATE_REVISION_HEAD_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",(UP1,UP1),
                  claims_for((UP1,UP1),TIMES[1]),as_of_utc=TIMES[1]),"head")
    rejects("LOCAL_HIGH_WATERMARK_ROLLBACK_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[3]),as_of_utc=TIMES[3],prior=r2),"rollback")
    rejects("SNAPSHOT_CLOCK_REWIND_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0]),as_of_utc=TIMES[0],prior=r2),"rollback")
    # Validly chained, same r1/r2, but older r1 payload is mutated and every
    # new claimant repeats the changed digest: local prior prefix catches it.
    from dataclasses import replace
    tampered_r1=replace(UP1,payload_sha256="9"*64)
    tampered_s2=(tampered_r1,UP2)
    rejects("TAMPERED_HISTORICAL_PREFIX_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",tampered_s2,
                  claims_for(tampered_s2,TIMES[3]),as_of_utc=TIMES[3],
                  prior=r2),"rollback")
    rejects("CROSS_EVENT_PRIOR_HEAD_DENIED",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR2",s2,
                  claims_for(s2,TIMES[3]),as_of_utc=TIMES[3],prior=r2),"scope")
    rejects("CROSS_PROVIDER_PRIOR_HEAD_DENIED",ValueError,
            lambda:intake_untrusted_claims(
                  FixturePartition("DNSE","fixture.dnse.d1","TEST","M5","RAW",
                                   "TESTSESSION"),
                  "BAR1",s2,claims_for(s2,TIMES[3]),
                  as_of_utc=TIMES[3],prior=r2),"scope")
    rejects("TRADING_CANNOT_BE_INFERRED_FROM_UNTRUSTED_CLAIMS",ValueError,
            lambda:intake_untrusted_claims(PARTITION,"BAR1",s1,
                  claims_for(s1,TIMES[0],
                      source_changes={"head_sequence":0}),as_of_utc=TIMES[0]),
            "authority")
    check("ALL_FOUR_NEW_OWNER_GATE_ROWS_UNSIGNED",
          len(OWNER_CHOICES)==4 and
          len({x["id"] for x in OWNER_CHOICES})==4 and
          all(x["owner_signed"] is False for x in OWNER_CHOICES),"owner")
    check("FRESH_RUN_CANNOT_PROVE_PRIOR_DURABLE_FLOOR",
          not r3.trusted_nonresettable_floor,"owner")
    check("CLAIM_ROLE_DIFFERENCE_NOT_CRYPTOGRAPHIC_SIGNATURE",
          not r3.verified_provider_signature and not r3.verified_independent_custody,
          "owner")

    if len(cases)!=42 or len({row["case"] for row in cases})!=42:
        raise AssertionError("A03_CLAIM_LEDGER_CASE_COUNT_DRIFT")
    snapshots=[{
        "as_of_utc":r.as_of_utc.isoformat(),"head_sequence":r.head_sequence,
        "head_revision_id":r.head_revision_id,"ledger_digest":r.ledger_digest,
        "candidate_status":r.candidate_status,
        "independently_qualified":False,
    } for r in (r1,r1_later,r2,r3,later)]
    fingerprint=sha256(json.dumps(
        {"cases":cases,"snapshots":snapshots,"owners":OWNER_CHOICES},
        sort_keys=True,separators=(",",":"),allow_nan=False,
    ).encode("ascii")).hexdigest()
    return {
        "schema":SCHEMA,
        "status":"TWO_DECLARED_CLAIMS_CONSISTENT_UNTRUSTED_NO_GO",
        "case_count":len(cases),"cases":cases,
        "snapshots":snapshots,"case_and_snapshot_sha256":fingerprint,
        "new_unsigned_owner_gates":list(OWNER_CHOICES),
        "provider_signature_cryptographically_verified":False,
        "independent_trust_root_or_custody_verified":False,
        "cross_run_nonresettable_floor_verified":False,
        "source_closed_head_or_complete_history_verified":False,
        "real_provider_entitlement_or_google_drive_cache_authorized":False,
        "owner_a02_signed":0,"owner_a03_signed":0,
        "g01_g08_oa01_oa06_closed":False,
        "production_release_or_trading_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    report=build()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},sort_keys=True))


if __name__=="__main__":
    main()
