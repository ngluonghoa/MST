"""MST Cache V2.1: synthetic AM/PM gap and actual inherited V1 EMA20/ATR14 parity.

Cloud CI fixture only. Two invented 2-hour continuous segments, a 2-hour
nontrading gap and optional non-continuous auction tests. M15/M30/H1 never
straddle the gap. H4 and D1 are *explicitly fictitious* stitched
trading-minute-group candidates, not official market/provider OHLCV.
All writes are ephemeral GitHub Actions SQLite, NEVER Google Drive/market data.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal as D
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.incremental_cache import (
    FixtureBar, SyntheticIncrementalStore, full_recompute,
)
from swing_trading.session_calendar import SessionType
from scripts.m2_a02_incremental_cache_oracle_lab import (
    identity, independent_ema_atr_oracle,
)
from scripts.m2_a03_multi_segment_session_gap_lab import (
    CandidateSegment, UntrustedMultiSegmentDay, candidate_screen,
    records_at, vn_utc,
)
from scripts.m2_a03_v2_session_pit_screen_lab import UntrustedSessionSlot
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture
from scripts.m4_v21_six_tf_causal_slices import TIMEFRAMES

SCHEMA = "mst.m4.v21-gapped-six-tf-inherited-v1-numeric-parity.synthetic.v1"
STATUS = "GAPPED_M5_SIX_TF_V1_EMA_ATR_NUMERIC_PARITY_FIXTURE_ONLY"
FIVE = timedelta(minutes=5)
COUNT_PER_PHASE = 24
SOURCE_COUNT = 48
RATIOS = {"M5":1, "M15":3, "M30":6, "H1":12, "H4":48, "D1":48}
SOURCE_MUTATION_INDEX = 20
METADATA_MUTATION_INDEX = 30
AM_START = vn_utc(9, 0)
PM_START = vn_utc(13, 0)
DAY_END = PM_START + COUNT_PER_PHASE * FIVE
COLD_AT = DAY_END + timedelta(minutes=1)
PRICE_KNOWN = DAY_END + timedelta(minutes=5)
METADATA_KNOWN = DAY_END + timedelta(minutes=10)


def legacy_key(tf: str):
    if type(tf) is not str or tf not in TIMEFRAMES:
        raise ValueError("SIX_TYPED_TIMEFRAMES_ONLY")
    return replace(identity(), timeframe=tf, calendar_version="FAKEGAPCAL1",
                   aggregation_policy_version="FAKESTITCH1")


def full_binding(tf: str) -> str:
    return FullPolicyFixture(fixture_scope(legacy_key(tf))).binding


def start_for(i: int):
    if type(i) is not int or i < 0 or i >= SOURCE_COUNT:
        raise ValueError("SOURCE_M5_INDEX_MUST_BE_IN_DECLARED_SEGMENT")
    return (AM_START + FIVE*i) if i < COUNT_PER_PHASE else (
        PM_START + FIVE*(i-COUNT_PER_PHASE)
    )


def source_bar(i: int):
    ts=start_for(i)
    close=D(100+i//4)+D(i%4)/D(10)
    return FixtureBar(ts, ts+FIVE, close-D(1), close+D(2), close-D(2),
                      close, 500+i, "r1", ts+FIVE)


def expected_members(tf: str):
    if tf not in RATIOS:
        raise ValueError("UNDECLARED_TF")
    ratio=RATIOS[tf]
    if tf in ("H4","D1"):
        # Trading-minute stitch across AM+PM; unqualified for real H4/D1.
        return (tuple(range(SOURCE_COUNT)),)
    return tuple(
        tuple(range(segment*COUNT_PER_PHASE+offset,
                    segment*COUNT_PER_PHASE+offset+ratio))
        for segment in (0,1)
        for offset in range(0,COUNT_PER_PHASE,ratio)
    )


@dataclass(frozen=True)
class ToyGroup:
    tf: str
    ordinal: int
    members: tuple[int,...]
    binding_sha256: str
    crosses_declared_break: bool
    closed_complete: bool = True

    def __post_init__(self):
        if type(self.tf) is not str or self.tf not in TIMEFRAMES:
            raise ValueError("TYPED_SIX_TF_GROUP_REQUIRED")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("NONNEGATIVE_TF_GROUP_ORDINAL_REQUIRED")
        if type(self.members) is not tuple or not self.members:
            raise TypeError("EXPLICIT_NONEMPTY_MEMBER_TUPLE_REQUIRED")
        if any(type(i) is not int or i < 0 or i >= SOURCE_COUNT for i in self.members):
            raise ValueError("EXACT_VALID_M5_SOURCE_MEMBERS_REQUIRED")
        if type(self.binding_sha256) is not str or len(self.binding_sha256)!=64:
            raise ValueError("FULL_POLICY_BINDING_REQUIRED")
        if type(self.crosses_declared_break) is not bool or type(self.closed_complete) is not bool:
            raise TypeError("EXPLICIT_QUALIFIED_GROUP_FLAGS_REQUIRED")
        if not self.closed_complete:
            raise PermissionError("PARTIAL_OR_OPEN_HIGHER_TF_GROUP_DENIED")


@dataclass(frozen=True)
class ToyGapGrid:
    day: UntrustedMultiSegmentDay
    source: tuple[FixtureBar,...]
    groups: tuple[ToyGroup,...]
    official_source_calendar_verified: bool = False

    def __post_init__(self):
        if type(self.day) is not UntrustedMultiSegmentDay:
            raise TypeError("REUSE_EXISTING_A03_SEGMENT_SCREEN_REQUIRED")
        if self.official_source_calendar_verified is not False:
            raise PermissionError("CALLER_MAY_NOT_DECLARE_OFFICIAL_CALENDAR")
        if len(self.day.segments)!=2 or [s.label for s in self.day.segments]!=["AM","PM"]:
            raise ValueError("EXACT_FAKE_AM_PM_PHASES_REQUIRED")
        if any(s.kind is not SessionType.CONTINUOUS for s in self.day.segments):
            raise PermissionError("AUCTION_OR_AFTER_HOURS_NOT_CONTINUOUS_M5")
        slots=self.day.segments
        if slots[0].slot.starts_at_utc!=AM_START or slots[0].slot.ends_at_utc!=AM_START+FIVE*COUNT_PER_PHASE:
            raise ValueError("AM_SLOT_MISMATCH")
        if slots[1].slot.starts_at_utc!=PM_START or slots[1].slot.ends_at_utc!=DAY_END:
            raise ValueError("PM_SLOT_MISMATCH")
        if type(self.source) is not tuple or len(self.source)!=SOURCE_COUNT or any(type(b) is not FixtureBar for b in self.source):
            raise ValueError("EXACT_48_TYPED_M5_SOURCE_ROWS_REQUIRED")
        for i,b in enumerate(self.source):
            if (not b.closed or b.start_utc!=start_for(i) or
                    b.end_utc!=b.start_utc+FIVE or
                    b.first_known_utc < b.end_utc):
                raise ValueError("M5_BAR_NOT_DECLARED_CLOSED_SEGMENT_OR_TIME")
            slot=slots[0 if i<COUNT_PER_PHASE else 1].slot
            if b.start_utc not in slot.permitted_bar_starts_utc:
                raise ValueError("GAP_OR_UNDECLARED_PHASE_M5_NOT_ALLOWED")
        if type(self.groups) is not tuple or any(type(g) is not ToyGroup for g in self.groups):
            raise TypeError("EXACT_TYPED_GROUPS_REQUIRED")
        expected={(tf,i):members for tf in TIMEFRAMES
                  for i,members in enumerate(expected_members(tf))}
        actual={}
        for g in self.groups:
            k=(g.tf,g.ordinal)
            if k in actual:
                raise ValueError("DUPLICATE_DERIVED_GROUP")
            actual[k]=g.members
            if g.binding_sha256!=full_binding(g.tf):
                raise PermissionError("INHERITED_V1_RIGHTS_CALENDAR_INDICATOR_SCOPE_DRIFT")
            if g.crosses_declared_break != (g.tf in ("H4","D1")):
                raise PermissionError("UNATTESTED_CROSS_BREAK_AGGREGATION_CLAIM")
        if actual != expected:
            raise ValueError("INCOMPLETE_DUPLICATE_OR_CROSS_GAP_MEMBERSHIP")

    def for_tf(self,tf):
        return tuple(g for g in self.groups if g.tf==tf)


def fabricate_grid():
    scope=fixture_scope(legacy_key("M5"))
    def segment(label,start):
        slot=UntrustedSessionSlot(scope.candidate,start,start+FIVE*COUNT_PER_PHASE,
                                  tuple(start+i*FIVE for i in range(COUNT_PER_PHASE)))
        return CandidateSegment(slot,SessionType.CONTINUOUS,"HOSE",label)
    day=UntrustedMultiSegmentDay(
        scope, scope.candidate.session_date_local,
        (segment("AM",AM_START),segment("PM",PM_START))
    )
    groups=tuple(ToyGroup(tf,i,members,full_binding(tf),tf in ("H4","D1"))
                 for tf in TIMEFRAMES for i,members in enumerate(expected_members(tf)))
    return ToyGapGrid(day,tuple(source_bar(i) for i in range(SOURCE_COUNT)),groups)


def aggregate(group: ToyGroup, source: tuple[FixtureBar,...]) -> FixtureBar:
    if type(group) is not ToyGroup or type(source) is not tuple:
        raise TypeError("EXACT_TYPED_FAKE_GROUP_AND_SOURCE")
    items=tuple(source[i] for i in group.members)
    if not all(b.closed for b in items):
        raise PermissionError("OPEN_SOURCE_CANNOT_BE_AGGREGATED")
    latest=max(items,key=lambda b:b.first_known_utc)
    return FixtureBar(
        items[0].start_utc,items[-1].end_utc,
        items[0].open,max(b.high for b in items),
        min(b.low for b in items),items[-1].close,
        sum(b.volume for b in items),latest.revision,
        latest.first_known_utc,
    )


def materialize_tf(grid:ToyGapGrid,tf:str):
    if type(grid) is not ToyGapGrid:
        raise TypeError("EXACT_QUALIFIED_SYNTHETIC_GRID_REQUIRED")
    return tuple(aggregate(g,grid.source) for g in grid.for_tf(tf))


def amended_source(grid:ToyGapGrid,kind:str,index:int):
    if type(grid) is not ToyGapGrid:
        raise TypeError("SYNTHETIC_GRID_REQUIRED")
    if kind not in ("PRICE","METADATA"):
        raise ValueError("TYPED_TEST_REVISION_KIND_REQUIRED")
    if type(index) is not int or index < 0 or index >= SOURCE_COUNT:
        raise ValueError("DECLARED_SOURCE_INDEX_REQUIRED")
    rows=list(grid.source)
    old=rows[index]
    if kind=="PRICE":
        # Drastic manufactured high change makes even full-day toy group numeric.
        value=old.close+D(150)
        rows[index]=replace(old,close=value,high=value+D(2),
                            revision="r2",first_known_utc=PRICE_KNOWN)
    else:
        rows[index]=replace(old,revision="r3",first_known_utc=METADATA_KNOWN)
    return replace(grid,source=tuple(rows))


def actual_v1_numeric_fixture() -> dict:
    grid=fabricate_grid()
    # Reuse previously proven A03 segment admission and its auction block.
    am=records_at(start_for(SOURCE_MUTATION_INDEX),grid.day.scope,event="TEST_AM")
    pm=records_at(start_for(METADATA_MUTATION_INDEX),grid.day.scope,event="TEST_PM")
    if (candidate_screen(grid.day,(am,),claimed_segment="AM",
                         as_of_utc=am.bar.first_known_utc)["candidate_revision_id"]!="r1"
        or candidate_screen(grid.day,(pm,),claimed_segment="PM",
                            as_of_utc=pm.bar.first_known_utc)["candidate_revision_id"]!="r1"):
        raise AssertionError("EXISTING_A03_AM_PM_SOURCE_SEGMENT_SCREEN_DRIFT")
    with TemporaryDirectory(prefix="mst-gh-only-gap-numeric-") as temp:
        store=SyntheticIncrementalStore(Path(temp)/"synthetic-test-only.sqlite")
        store.initialize()
        baseline={}
        keys={}
        summary={}
        for tf in TIMEFRAMES:
            key=legacy_key(tf)
            keys[tf]=key
            bars=materialize_tf(grid,tf)
            update=store.apply_fixture_window(
                key,bars,observed_at_utc=COLD_AT,
                scope_start_utc=bars[0].start_utc,scope_end_utc=bars[-1].end_utc,
                complete_scope=True,full_session_reconciled=True,
            )
            checkpoints=store.read_checkpoints(key)
            if update.inserted!=len(bars) or update.indicator_bars_recomputed!=len(bars):
                raise AssertionError("V1_INITIAL_GROUPED_COLD_RECOMPUTE_DRIFT")
            if checkpoints!=full_recompute(bars) or checkpoints!=independent_ema_atr_oracle(bars):
                raise AssertionError("V1_COLD_SIX_TF_DECIMAL_ORACLE_PARITY_DRIFT")
            baseline[tf]=checkpoints
            summary[tf]={"toy_closed_windows":len(bars),
                         "full_v1_scope_sha256":full_binding(tf),
                         "cold_indicator_values_equal_independent_oracle":True,
                         "revised_group_index":None,
                         "price_correction_checkpoint_suffix_count":None,
                         "metadata_only_zero_recompute":False}
        changed=amended_source(grid,"PRICE",SOURCE_MUTATION_INDEX)
        for tf in TIMEFRAMES:
            groups=changed.for_tf(tf)
            g=next(g for g in groups if SOURCE_MUTATION_INDEX in g.members)
            index=g.ordinal
            candle=aggregate(g,changed.source)
            before=baseline[tf]
            upd=store.apply_fixture_window(keys[tf],(candle,),
                observed_at_utc=PRICE_KNOWN,
                scope_start_utc=candle.start_utc,scope_end_utc=candle.end_utc,
                complete_scope=False)
            rows=store.read_bars(keys[tf])
            after=store.read_checkpoints(keys[tf])
            oracle=independent_ema_atr_oracle(rows)
            if (upd.revised!=1 or upd.first_dirty_utc!=candle.start_utc
                or upd.indicator_bars_recomputed!=len(rows)-index
                or after[:index]!=before[:index]
                or after[index:]==before[index:]
                or after!=oracle or after!=full_recompute(rows)):
                raise AssertionError("V1_DIRTY_SUFFIX_OR_DECIMAL_ORACLE_PARITY_DRIFT_"+tf)
            summary[tf]["revised_group_index"]=index
            summary[tf]["price_correction_checkpoint_suffix_count"]=upd.indicator_bars_recomputed
            summary[tf]["corrected_numeric_indicators_equal_independent_oracle"]=True
        metadata=amended_source(changed,"METADATA",METADATA_MUTATION_INDEX)
        for tf in TIMEFRAMES:
            group=next(g for g in metadata.for_tf(tf)
                       if METADATA_MUTATION_INDEX in g.members)
            b=aggregate(group,metadata.source)
            unchanged_checks=store.read_checkpoints(keys[tf])
            upd=store.apply_fixture_window(keys[tf],(b,),
                observed_at_utc=METADATA_KNOWN,
                scope_start_utc=b.start_utc,scope_end_utc=b.end_utc,
                complete_scope=False)
            rows=store.read_bars(keys[tf])
            checks=store.read_checkpoints(keys[tf])
            if (upd.lineage_only!=1 or upd.indicator_bars_recomputed!=0
                or checks!=unchanged_checks or checks!=full_recompute(rows)
                or checks!=independent_ema_atr_oracle(rows)):
                raise AssertionError("V1_METADATA_ONLY_SHOULD_PRESERVE_NUMERIC_CHECKPOINTS_"+tf)
            summary[tf]["metadata_only_zero_recompute"]=True
            summary[tf]["final_ema_atr_equal_independent_oracle"]=True
        if sum(v["price_correction_checkpoint_suffix_count"] for v in summary.values())!=48:
            raise AssertionError("CROSS_SEGMENT_CAUSAL_TAIL_COUNT_DRIFT")
        if any(not v["metadata_only_zero_recompute"] for v in summary.values()):
            raise AssertionError("METADATA_AUDIT_NUMERIC_BOUNDARY_DRIFT")
        return {
            "schema":SCHEMA,"status":STATUS,
            "source_m5_count":SOURCE_COUNT,
            "artificial_segments":["AM","PM"],
            "nontrading_break_minutes":int((PM_START-AM_START-COUNT_PER_PHASE*FIVE).total_seconds()/60),
            "toy_tf_window_counts":{tf:len(grid.for_tf(tf)) for tf in TIMEFRAMES},
            "toy_grouped_window_count":sum(len(grid.for_tf(tf)) for tf in TIMEFRAMES),
            "source_price_correction_index":SOURCE_MUTATION_INDEX,
            "source_metadata_only_revision_index":METADATA_MUTATION_INDEX,
            "total_price_correction_checkpoint_suffix_positions":48,
            "tf_evidence":summary,
            "inherited_v1_sqlite_incremental_numerically_matches_independent_ema20_atr14":True,
            "two_existing_a03_fake_segment_screens_passed":True,
            "cross_gap_m15_m30_h1_groups_denied_by_membership":True,
            "h4_and_d1_purely_artificial_stitched_trade_minutes":True,
            "source_license_verified":False,
            "official_hose_hnx_upcom_historical_calendar_verified":False,
            "real_provider_aggregation_and_correction_proven":False,
            "real_source_first_known_verified":False,
            "physical_google_drive_quote_cache_read_write":False,
            "cross_run_authenticated_writer_or_protected_cas_floor":False,
            "live_signal_release_or_trading_authorized":False,
        }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=actual_v1_numeric_fixture()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":STATUS,
        "six_tf_numeric_v1_oracle_parity":True,
        "tf_counts":result["toy_tf_window_counts"],
        "corrected_checkpoints":result["total_price_correction_checkpoint_suffix_positions"],
        "authorized_real_cache":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
