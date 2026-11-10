"""A02 source-locked V1 SQLite late-revision and session-membership negative QA.

Only manufactured UTC sessions in GitHub-hosted temporary SQLite. Never a real
provider, official VN calendar, approved data cache or trading system.
"""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import inspect
import json

from scripts.m2_a02_incremental_cache_oracle_lab import identity
from swing_trading.incremental_cache import FixtureBar, SyntheticIncrementalStore, full_recompute
from swing_trading.replay import ReplayClock

SCHEMA = "mst.a02.v1-late-revision-cross-session-source-membership.negative.v1"
BASE = datetime(2026,11,9,2,0,tzinfo=timezone.utc)
NEXT = BASE + timedelta(days=1)
FIVE = timedelta(minutes=5)
DENIED = ("original_v1_modified","real_vendor_revision_attested",
          "official_session_calendar_verified","signed_source_first_known_verified",
          "historical_asof_reader_qualified","independent_session_membership_verified",
          "real_google_drive_cache_authorized","a02_63_owner_signed",
          "a03_v2_8_owner_signed","a03_14_owner_signed",
          "production_authorized","trading_authorized")


def at(t,minutes):
    return t + timedelta(minutes=minutes)


def bar(t,i,price,revision="r1",known=None):
    start=at(t,i*5)
    p=Decimal(str(price))
    return FixtureBar(start,start+FIVE,p-1,p+2,p-2,p,
                      1000+i,revision,start+FIVE if known is None else known)


def apply(store,key,rows,now,start,end,complete=False,full=False):
    return store.apply_fixture_window(
        key,tuple(rows),observed_at_utc=now,scope_start_utc=start,
        scope_end_utc=end,complete_scope=complete,full_session_reconciled=full)


def evaluate():
    key_a=replace(identity(),session_id="SYNTHETIC.SESSION.A")
    key_b=replace(identity(),session_id="SYNTHETIC.SESSION.B")
    aa=tuple(bar(BASE,i,100+i) for i in range(4))
    bb=tuple(bar(NEXT,i,200+i) for i in range(3))
    correction_known=at(NEXT,21)
    correction=bar(BASE,1,250,"r2",correction_known)
    checked=[]

    def test(name,condition):
        if not condition:
            raise AssertionError("ORIGINAL_V1_SESSION_ASOF_ASSERTION_DRIFT_"+name)
        checked.append(name)

    with TemporaryDirectory(prefix="mst-github-synthetic-crosssession-") as folder:
        store=SyntheticIncrementalStore(Path(folder)/"fixture.sqlite")
        store.initialize()
        a0=apply(store,key_a,aa,at(BASE,30),BASE,at(BASE,20),True,True)
        test("A_INITIAL_FOUR_BARS",a0.inserted==4)
        test("A_INITIAL_COLD_ORACLE",store.read_checkpoints(key_a)==full_recompute(aa))
        old=store.read_bars(key_a)
        b0=apply(store,key_b,bb,at(NEXT,20),NEXT,at(NEXT,15),True,True)
        test("B_INITIAL_THREE_BARS",b0.inserted==3)
        test("A_B_FINGERPRINTS_DISTINCT",key_a.fingerprint!=key_b.fingerprint)
        test("B_INITIAL_COLD_ORACLE",store.read_checkpoints(key_b)==full_recompute(bb))
        revised=apply(store,key_a,(correction,),at(NEXT,25),
                      correction.start_utc,correction.end_utc)
        after=store.read_bars(key_a)
        test("OLD_A_CORRECTION_REVISED",revised.revised==1 and
             revised.first_dirty_utc==correction.start_utc)
        test("THREE_A_TAIL_CHECKPOINTS_REBUILT",revised.indicator_bars_recomputed==3)
        test("A_CORRECTED_COLD_ORACLE",store.read_checkpoints(key_a)==full_recompute(after))
        test("B_UNTOUCHED_BY_OLD_A_REVISION",store.read_bars(key_b)==bb)
        test("OLD_A_PAYLOAD_REPLACED_IN_LATEST_READER",
             len(after)==4 and after[1]==correction and old[1]!=correction)
        test("LATE_FIRST_KNOWN_RETAINED",after[1].first_known_utc==correction_known)
        old_clock=ReplayClock(correction_known-timedelta(microseconds=1))
        exact_clock=ReplayClock(correction_known)
        test("BEFORE_FIRST_KNOWN_REPLAY_CLOCK_EXCLUDES",not old_clock.known(correction_known))
        test("EXACT_FIRST_KNOWN_REPLAY_CLOCK_INCLUDES",exact_clock.known(correction_known))
        test("LATEST_RAW_READER_NOT_ASOF_FILTERED",
             store.read_bars(key_a)[1]==correction and not old_clock.known(correction_known))
        test("READ_BARS_HAS_NO_ASOF_PARAMETER",
             "as_of_utc" not in inspect.signature(store.read_bars).parameters)

        # Deliberately hand the *B session* bar to A's partition with a
        # caller-supplied B range. No externally authenticated session rule.
        wrong=bb[0]
        cross=apply(store,key_a,(wrong,),at(NEXT,30),
                    wrong.start_utc,wrong.end_utc)
        mixed=store.read_bars(key_a)
        test("WRONG_SESSION_B_BAR_ACCEPTED_UNDER_A",
             cross.inserted==1 and len(mixed)==5 and mixed[-1]==wrong)
        test("MISLABELLED_A_STILL_INTERNAL_COLD_PARITY",
             cross.indicator_bars_recomputed==1 and
             store.read_checkpoints(key_a)==full_recompute(mixed))
        test("ACTUAL_B_PARTITION_REMAINS_UNCHANGED",
             store.read_bars(key_b)==bb and
             store.read_checkpoints(key_b)==full_recompute(bb))
        test("BAR_HAS_NO_OFFICIAL_SESSION_MEMBER_PROOF",
             not hasattr(wrong,"session_id") and
             not hasattr(wrong,"official_calendar_proof"))
        test("SESSION_A_IS_ONLY_CALLER_PROVIDED_LABEL",
             key_a.session_id=="SYNTHETIC.SESSION.A")
        test("INTERNAL_COLD_PARITY_CANNOT_AUTHENTICATE_SESSION",
             wrong in mixed and store.read_checkpoints(key_a)==full_recompute(mixed))
        counts={
            "a_initial":len(aa),"b_initial":len(bb),
            "a_after_late_revision":len(after),
            "a_after_mislabeled_b":len(mixed),
            "a_revised_checkpoint_tail":revised.indicator_bars_recomputed,
            "a_mislabeled_checkpoint_tail":cross.indicator_bars_recomputed,
        }
    if len(checked)!=21:
        raise AssertionError("EXPECTED_EXACT_TWENTY_ONE_NEGATIVE_ASSERTIONS")
    result={
        "schema":SCHEMA,
        "status":"SCOPE_ONLY_OLD_REVISION_RECOMPUTES_BUT_SESSION_MEMBERSHIP_UNVERIFIED",
        "assertions":checked,"assertion_count":len(checked),"counts":counts,
        "late_revision_tail_recompute_matches_cold_oracle":True,
        "distinct_proper_session_keys_remain_isolated":True,
        "latest_only_reader_does_not_preserve_historical_asof_payload":True,
        "wrong_session_candle_can_be_written_into_caller_labeled_partition":True,
        **{k:False for k in DENIED},
    }
    raw=json.dumps(result,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    result["synthetic_digest_sha256"]=sha256(raw.encode()).hexdigest()
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    report=evaluate()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="assertions"},sort_keys=True))


if __name__=="__main__":
    main()
