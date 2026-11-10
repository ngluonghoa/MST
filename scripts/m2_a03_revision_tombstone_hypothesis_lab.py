"""MST A03 untrusted revision/tombstone *hypothesis* and causal replay lab.

Nothing here authenticates an SSI/DNSE/VCBS revision or source sequence.
Candidate winning revisions are a fixture-only model, NOT source facts.
No inherited 63 V1 or eight opt-in V2 files are modified or activated.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import re

from swing_trading.causal import CausalMarketEvent
from scripts.m2_a03_adapter_revision_replay_lab import (
    BoundedTupleFixtureAdapter, GeneratorFixtureSource, v1_harness, v2_harness,
)

SCHEMA = "mst.a03.revision-tombstone-hypothesis-untrusted.v1"
T0 = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)
TIMES = tuple(T0 + timedelta(minutes=5 * n) for n in range(5))
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


def utc(t: datetime) -> datetime:
    if type(t) is not datetime or t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("UTC-aware datetime required")
    return t


def name(s: str) -> str:
    if type(s) is not str or not _NAME.fullmatch(s):
        raise ValueError("Explicit nonempty fixture identifier required")
    return s


class RevisionKind(str, Enum):
    UPSERT = "UPSERT"
    TOMBSTONE = "TOMBSTONE"


@dataclass(frozen=True)
class FixturePartition:
    provider_id: str
    endpoint_id: str
    symbol: str
    timeframe: str
    price_basis: str
    session_id: str

    def __post_init__(self):
        for x in (self.provider_id,self.endpoint_id,self.symbol,
                  self.timeframe,self.price_basis,self.session_id):
            name(x)
        if self.price_basis not in ("RAW","ADJUSTED"):
            raise ValueError("Price basis must be explicit")


@dataclass(frozen=True)
class FixtureRevision:
    partition: FixturePartition
    event_id: str
    revision_id: str
    sequence: int
    kind: RevisionKind
    event_time_utc: datetime
    first_known_utc: datetime
    supersedes_revision_id: str | None = None
    payload_sha256: str | None = None

    def __post_init__(self):
        if type(self.partition) is not FixturePartition:
            raise TypeError("Exact fixture partition required")
        name(self.event_id)
        name(self.revision_id)
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("Positive exact integer sequence required")
        if type(self.kind) is not RevisionKind:
            raise TypeError("Explicit revision kind required")
        utc(self.event_time_utc)
        utc(self.first_known_utc)
        if self.first_known_utc < self.event_time_utc:
            raise ValueError("Revision cannot be known before event-time")
        if self.sequence == 1:
            if self.supersedes_revision_id is not None:
                raise ValueError("Root cannot claim predecessor")
        elif self.supersedes_revision_id is None:
            raise ValueError("Correction/tombstone must state predecessor")
        if self.supersedes_revision_id is not None:
            name(self.supersedes_revision_id)
            if self.supersedes_revision_id == self.revision_id:
                raise ValueError("Revision cannot supersede itself")
        if self.kind is RevisionKind.UPSERT:
            if type(self.payload_sha256) is not str or not _HASH.fullmatch(self.payload_sha256):
                raise ValueError("Upsert requires opaque fixture payload digest")
        elif self.payload_sha256 is not None:
            raise ValueError("Tombstone cannot contain a payload digest")


@dataclass(frozen=True)
class FixtureCandidate:
    event_id: str
    status: str
    candidate_revision_id: str | None
    visible_revision_ids: tuple[str, ...]
    independently_source_verified: bool = False
    market_data_rights_authorized: bool = False
    physical_drive_cache_authorized: bool = False
    trading_authorized: bool = False


def resolve_untrusted_fixture(
    partition: FixturePartition, event_id: str,
    revisions: tuple[FixtureRevision, ...], *, as_of_utc: datetime,
) -> FixtureCandidate:
    """Fail-closed *hypothesis*. Visible sequence cannot confer source rights.

    The complete untrusted batch is not a vendor authenticated revision ledger.
    An absent earlier revision in a visible prefix is an ERROR, not "r3 wins".
    """
    if type(partition) is not FixturePartition:
        raise TypeError("Exact partition required")
    name(event_id)
    if type(revisions) is not tuple:
        raise TypeError("Immutable fixture revision tuple required")
    at = utc(as_of_utc)
    for r in revisions:
        if type(r) is not FixtureRevision:
            raise TypeError("Exact revision fixture required")
        if r.partition != partition:
            raise ValueError("CROSS_SOURCE_PARTITION_REPLAY_DENIED")
        if r.event_id != event_id:
            raise ValueError("CROSS_EVENT_ID_REPLAY_DENIED")
    visible = sorted(
        (r for r in revisions
         if r.first_known_utc <= at and r.event_time_utc <= at),
        key=lambda r: r.sequence,
    )
    if not visible:
        return FixtureCandidate(event_id, "UNVERIFIED_EMPTY", None, ())
    revision_ids = set()
    for i,r in enumerate(visible):
        if r.revision_id in revision_ids:
            raise ValueError("DUPLICATE_VISIBLE_REVISION_ID")
        revision_ids.add(r.revision_id)
        if r.sequence != i + 1:
            raise ValueError("GAPPED_OR_DUPLICATE_REVISION_SEQUENCE")
        if r.event_time_utc != visible[0].event_time_utc:
            raise ValueError("MIXED_EVENT_TIMES")
        if i:
            prev = visible[i-1]
            if r.supersedes_revision_id != prev.revision_id:
                raise ValueError("UNPROVEN_OR_WRONG_PREDECESSOR")
            if r.first_known_utc <= prev.first_known_utc:
                raise ValueError("AMBIGUOUS_OR_REGRESSED_REVISION_KNOWLEDGE")
            if prev.kind is RevisionKind.TOMBSTONE:
                raise ValueError("TOMBSTONE_RESURRECTION_REQUIRES_OWNER_POLICY")
    latest = visible[-1]
    if latest.kind is RevisionKind.TOMBSTONE:
        return FixtureCandidate(
            event_id, "UNVERIFIED_TOMBSTONED", None,
            tuple(r.revision_id for r in visible),
        )
    return FixtureCandidate(
        event_id, "UNVERIFIED_CANDIDATE_UPSERT", latest.revision_id,
        tuple(r.revision_id for r in visible),
    )


PARTITION = FixturePartition("SSI", "fixture.ssi.d1", "TEST", "M5", "RAW", "TESTSESSION")
UP1 = FixtureRevision(PARTITION,"BAR1","r1",1,RevisionKind.UPSERT,T0,T0,
                      payload_sha256="1"*64)
UP2 = FixtureRevision(PARTITION,"BAR1","r2",2,RevisionKind.UPSERT,T0,TIMES[2],
                      supersedes_revision_id="r1",payload_sha256="2"*64)
TOMB = FixtureRevision(PARTITION,"BAR1","r3",3,RevisionKind.TOMBSTONE,T0,TIMES[3],
                       supersedes_revision_id="r2")
RECORDS = (TOMB,UP1,UP2)


def to_events(rs: tuple[FixtureRevision,...]) -> tuple[CausalMarketEvent,...]:
    return tuple(
        CausalMarketEvent(
            r.event_id,r.revision_id,r.event_time_utc,r.first_known_utc,
            {"kind":r.kind.value,"sequence":r.sequence,
             "opaque_fixture_digest":r.payload_sha256},
        )
        for r in rs
    )


OWNER_CHOICES = (
    {"id":"A03-OWNER-SOURCE-SEQUENCE-07",
     "open_question":"Who authenticates provider revision sequence, missing revisions and stable head?",
     "owner_signed":False},
    {"id":"A03-OWNER-TOMBSTONE-08",
     "open_question":"What is the licensed vendor deletion/tombstone and resurrection contract?",
     "owner_signed":False},
    {"id":"A03-OWNER-CORRECTION-CONFLICT-09",
     "open_question":"Which signed provider evidence resolves ties, conflicts, corrections and crossed sessions?",
     "owner_signed":False},
    {"id":"A03-OWNER-RECONCILIATION-10",
     "open_question":"Which source rights/calendar/reconciliation and historical snapshot policy is approved?",
     "owner_signed":False},
)


def build():
    cases = []
    def check(case, condition, group):
        if not condition:
            raise AssertionError("A03_REVISION_TOMBSTONE_FAIL:"+case)
        cases.append({"case":case,"group":group,"result":"PASS_UNTRUSTED_FIXTURE_ONLY"})

    expected = (("UNVERIFIED_CANDIDATE_UPSERT","r1",("r1",)),
                ("UNVERIFIED_CANDIDATE_UPSERT","r1",("r1",)),
                ("UNVERIFIED_CANDIDATE_UPSERT","r2",("r1","r2")),
                ("UNVERIFIED_TOMBSTONED",None,("r1","r2","r3")),
                ("UNVERIFIED_TOMBSTONED",None,("r1","r2","r3")))
    observations=[]
    events=to_events(RECORDS)
    for i,at in enumerate(TIMES):
        view=resolve_untrusted_fixture(PARTITION,"BAR1",RECORDS,as_of_utc=at)
        check("AS_OF_"+str(i)+"_UNTRUSTED_CANDIDATE_STATE",
              (view.status,view.candidate_revision_id,view.visible_revision_ids)
              == expected[i],"as_of")
        old=v1_harness(at,BoundedTupleFixtureAdapter(
            GeneratorFixtureSource(events),exact_base_type=True)).visible_events()
        new=v2_harness(at,BoundedTupleFixtureAdapter(
            GeneratorFixtureSource(events),exact_base_type=True)).visible_events()
        check("AS_OF_"+str(i)+"_RAW_V1_V2_VISIBILITY_PARITY",
              old==new and tuple(x.revision_id for x in old)==expected[i][2],
              "as_of")
        check("AS_OF_"+str(i)+"_NO_FUTURE_KNOWLEDGE",
              all(x.first_known_time_utc<=at and x.event_time_utc<=at
                  for x in old),"as_of")
        check("AS_OF_"+str(i)+"_NO_AUTHORITY_CLAIM",
              not (view.independently_source_verified
                   or view.market_data_rights_authorized
                   or view.physical_drive_cache_authorized
                   or view.trading_authorized),"as_of")
        observations.append({"as_of_utc":at.isoformat(),"status":view.status,
              "candidate_revision_id":view.candidate_revision_id,
              "raw_visible_revisions":list(view.visible_revision_ids)})

    check("FRESH_EARLY_REPLAY_NOT_REPAINTED",
          resolve_untrusted_fixture(PARTITION,"BAR1",RECORDS,
              as_of_utc=TIMES[0]).candidate_revision_id=="r1","correction")
    check("OUT_OF_ORDER_INPUT_IS_SORTED_BY_DECLARED_SEQUENCE_ONLY",
          tuple(r.revision_id for r in RECORDS)==("r3","r1","r2")
          and observations[3]["raw_visible_revisions"]==["r1","r2","r3"],
          "correction")
    check("TOMBSTONE_SUPPRESSES_FIXTURE_CANDIDATE",
          observations[3]["candidate_revision_id"] is None,"tombstone")
    check("V1_V2_RETURN_RAW_TOMBSTONE_AS_EVENT",
          len(v1_harness(TIMES[3],BoundedTupleFixtureAdapter(
              GeneratorFixtureSource(events))).visible_events())==3,"tombstone")
    check("EMPTY_SOURCE_IS_UNVERIFIED_NOT_SOURCE_CERTIFIED",
          resolve_untrusted_fixture(PARTITION,"BAR1",(),
            as_of_utc=T0).status=="UNVERIFIED_EMPTY","correction")

    def fail(case,exc,fn,group):
        try:
            fn()
        except exc:
            check(case,True,group)
        else:
            raise AssertionError("A03_EXPECTED_REJECTION_MISSING:"+case)

    def mk(**kw):
        args=dict(partition=PARTITION,event_id="BAR1",revision_id="r4",
                  sequence=4,kind=RevisionKind.UPSERT,
                  event_time_utc=T0,first_known_utc=TIMES[4],
                  supersedes_revision_id="r3",payload_sha256="4"*64)
        args.update(kw)
        return FixtureRevision(**args)

    fail("BOOLEAN_SEQUENCE_REJECTED",ValueError,
         lambda:mk(sequence=True),"validation")
    fail("ZERO_SEQUENCE_REJECTED",ValueError,
         lambda:mk(sequence=0),"validation")
    fail("NAIVE_KNOWLEDGE_TIMESTAMP_REJECTED",ValueError,
         lambda:mk(first_known_utc=datetime(2026,11,9,8,20)),"validation")
    fail("FIRST_KNOWN_BEFORE_EVENT_REJECTED",ValueError,
         lambda:mk(first_known_utc=T0-timedelta(seconds=1)),"validation")
    fail("NONENUM_KIND_REJECTED",TypeError,
         lambda:mk(kind="UPSERT"),"validation")
    fail("TOMBSTONE_WITH_PAYLOAD_REJECTED",ValueError,
         lambda:mk(kind=RevisionKind.TOMBSTONE),"validation")
    fail("UPSERT_WITHOUT_DIGEST_REJECTED",ValueError,
         lambda:mk(payload_sha256=None),"validation")
    fail("SELF_SUPERSESSION_REJECTED",ValueError,
         lambda:mk(supersedes_revision_id="r4"),"validation")
    fail("NONROOT_WITHOUT_PREDECESSOR_REJECTED",ValueError,
         lambda:mk(supersedes_revision_id=None),"validation")
    fail("ROOT_WITH_PREDECESSOR_REJECTED",ValueError,
         lambda:mk(sequence=1),"validation")
    fail("BOOL_AS_OF_REJECTED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",RECORDS,
               as_of_utc=True),"validation")
    fail("UNVERIFIED_CROSS_PROVIDER_REJECTED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
               (mk(partition=FixturePartition(
                   "DNSE","fixture.dnse.d1","TEST","M5","RAW","TESTSESSION")),),
               as_of_utc=TIMES[4]),"isolation")
    fail("UNVERIFIED_CROSS_PRICE_BASIS_REJECTED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
               (mk(partition=FixturePartition(
                   "SSI","fixture.ssi.d1","TEST","M5","ADJUSTED","TESTSESSION")),),
               as_of_utc=TIMES[4]),"isolation")
    fail("UNVERIFIED_CROSS_EVENT_ID_REJECTED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
               (mk(event_id="BAR2"),),as_of_utc=TIMES[4]),"isolation")
    fail("LIST_INSTEAD_OF_IMMUTABLE_TUPLE_REJECTED",TypeError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",list(RECORDS),
               as_of_utc=TIMES[4]),"validation")
    fail("UNTYPED_EVENT_OBJECT_REJECTED",TypeError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",(object(),),
               as_of_utc=TIMES[4]),"validation")
    fail("MISSING_ROOT_SEQUENCE_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",(UP2,),
               as_of_utc=TIMES[2]),"chain")
    fail("DUPLICATE_SEQUENCE_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",(UP1,UP1),
               as_of_utc=TIMES[2]),"chain")
    fail("DUPLICATE_REVISION_ID_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             (UP1,UP2,mk(sequence=3,revision_id="r1",
                      supersedes_revision_id="r2",first_known_utc=TIMES[3])),
             as_of_utc=TIMES[3]),
         "chain")
    fail("GAPPED_CHAIN_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",(UP1,TOMB),
               as_of_utc=TIMES[3]),"chain")
    fail("WRONG_PARENT_REVISION_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             (UP1,mk(sequence=2,supersedes_revision_id="OTHER",
                      first_known_utc=TIMES[2])),as_of_utc=TIMES[2]),
         "chain")
    fail("SAME_KNOWLEDGE_INSTANT_AMBIGUOUS",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             (UP1,mk(sequence=2,supersedes_revision_id="r1",
                      first_known_utc=T0)),as_of_utc=TIMES[2]),
         "chain")
    fail("REGRESSED_KNOWLEDGE_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             (FixtureRevision(PARTITION,"BAR1","r1",1,RevisionKind.UPSERT,
                       T0,TIMES[2],payload_sha256="1"*64),
              mk(sequence=2,supersedes_revision_id="r1",
                 first_known_utc=TIMES[1])),
             as_of_utc=TIMES[2]),"chain")
    fail("MIXED_EVENT_START_TIMES_BLOCKED",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             (UP1,mk(sequence=2,supersedes_revision_id="r1",
                      event_time_utc=T0+timedelta(minutes=1),
                      first_known_utc=TIMES[2])),
             as_of_utc=TIMES[2]),"chain")
    fail("TOMBSTONE_RESURRECTION_REQUIRES_POLICY",ValueError,
         lambda:resolve_untrusted_fixture(PARTITION,"BAR1",
             RECORDS+(mk(),),as_of_utc=TIMES[4]),"tombstone")

    check("FUTURE_TOMBSTONE_NOT_BACKDATED",
          resolve_untrusted_fixture(PARTITION,"BAR1",RECORDS,
            as_of_utc=TIMES[2]).candidate_revision_id=="r2","tombstone")
    check("EMPTY_CANDIDATE_NEVER_MEANS_NOT_DETECTED",
          resolve_untrusted_fixture(PARTITION,"BAR1",(),
            as_of_utc=TIMES[0]).status!="NOT_DETECTED","governance")
    check("FOUR_NEW_OWNER_DECISIONS_REMAIN_UNSIGNED",
          len(OWNER_CHOICES)==4 and all(x["owner_signed"] is False
              for x in OWNER_CHOICES),"governance")
    check("NO_EXTERNAL_SEQUENCE_ATTESTATION_IN_FIXTURE",
          PARTITION.provider_id=="SSI" and not any(
              x["owner_signed"] for x in OWNER_CHOICES),"governance")

    if len(cases)!=54 or len({x["case"] for x in cases})!=54:
        raise AssertionError("A03_REVISION_TOMBSTONE_COVERAGE_TOO_SMALL")
    fingerprint=sha256(json.dumps(
        {"cases":cases,"snapshots":observations,"owner_choices":OWNER_CHOICES},
        sort_keys=True,separators=(",",":"),allow_nan=False
    ).encode("utf-8")).hexdigest()
    return {
        "schema":SCHEMA,"status":"UNTRUSTED_TOMBSTONE_WINNER_HYPOTHESIS_NO_GO",
        "case_count":len(cases),"cases":cases,
        "case_and_snapshot_sha256":fingerprint,
        "as_of_snapshots":observations,
        "owner_review_choices":list(OWNER_CHOICES),
        "fixture_revision_candidate_only":True,
        "v1_v2_native_supersession_or_tombstone_semantics_implemented":False,
        "provider_revision_sequence_independently_attested":False,
        "real_market_data_source_authority_or_entitlement_proven":False,
        "legal_google_drive_market_cache_or_durable_cas_proven":False,
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
