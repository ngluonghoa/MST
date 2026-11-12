"""MST V2.1 P0 synthetic 16-day six-TF ATR14 causal replay (NO real market).

An invented 16-consecutive-calendar-day fixture, including weekends, repeats
the previous explicitly fictional AM/PM two-hour segments. H4/D1 are toy
stitched groups across a nontrading break, NOT official exchange bars.
All numerical writes use inherited Swing V1 ephemeral SQLite in GitHub Actions.
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
    FixtureBar, Provider, SyntheticIncrementalStore, full_recompute,
)
from scripts.m2_a02_incremental_cache_oracle_lab import independent_ema_atr_oracle
from scripts.m2_a03_v2_cache_consumer_contract import fixture_scope
from scripts.m4_v21_layered_invalidation_lab import FullPolicyFixture
from scripts.m4_v21_gap_v1_numeric_parity_lab import (
    TIMEFRAMES, ToyGroup, fabricate_grid, legacy_key, aggregate,
    source_bar, start_for, COUNT_PER_PHASE, SOURCE_COUNT, DAY_END,
)

SCHEMA="mst.m4.cache-v2-1-16-day-six-tf-atr14-replay.synthetic.v1"
STATUS="SIX_TF_ALL_ATR14_NUMERIC_ORACLE_MULTIDAY_FIXTURE_ONLY_NO_GO"
FAKE_DAYS=16
CHANGE_DAY=13  # 14th fabricated day; first D1/H4 ATR14 seed
CHANGE_M5_IN_DAY=20
META_DAY=14
META_M5_IN_DAY=30
PRICE_DELTA=D(250)
KIND_PER_DAY={"M5":48,"M15":16,"M30":8,"H1":4,"H4":1,"D1":1}
EXPECTED_TOTAL={k:v*FAKE_DAYS for k,v in KIND_PER_DAY.items()}
EXPECTED_SUFFIX={"M5":124,"M15":42,"M30":21,"H1":11,"H4":3,"D1":3}
BASE_END=DAY_END+(FAKE_DAYS-1)*timedelta(days=1)
COLD_AT=BASE_END+timedelta(minutes=1)
CORRECTION_KNOWN=BASE_END+timedelta(minutes=7)
METADATA_KNOWN=BASE_END+timedelta(minutes=12)
FIVE=timedelta(minutes=5)


def multi_key(tf:str):
    if type(tf) is not str or tf not in TIMEFRAMES:
        raise ValueError("SIX_EXPLICIT_TFS_REQUIRED")
    return replace(
        legacy_key(tf),
        session_id="SYNTHETIC.16CONSECUTIVE.CALENDARDAYS",
        calendar_version="FAKE.16D.MULTISESSION.V1",
        aggregation_policy_version="FAKE.GAPPED.SESSIONSTITCH.V1",
    )


def binding(tf:str):
    # V1-only full-policy fingerprint: the actual opt-in V1→V2 typed map
    # requires exactly one session_date_local and MUST reject this 16-day
    # composite synthetic history. Never misrepresent it as a valid V2 binding.
    return multi_key(tf).fingerprint


@dataclass(frozen=True)
class FakeDay:
    ordinal:int
    m5:tuple[FixtureBar,...]
    official_day_provenance:bool=False

    def __post_init__(self):
        if type(self.ordinal) is not int or not 0<=self.ordinal<FAKE_DAYS:
            raise ValueError("EXPLICIT_FABRICATED_DAY_ORDINAL_REQUIRED")
        if self.official_day_provenance is not False:
            raise PermissionError("NO_CALLER_OFFICIAL_EXCHANGE_DAY_CLAIM")
        if type(self.m5) is not tuple or len(self.m5)!=SOURCE_COUNT or any(type(x) is not FixtureBar for x in self.m5):
            raise TypeError("EXACT_48_TYPED_FAKE_M5_REQUIRED")
        shift=timedelta(days=self.ordinal)
        for i,bar in enumerate(self.m5):
            start=start_for(i)+shift
            if (bar.start_utc != start or bar.end_utc!=start+FIVE or
                bar.first_known_utc<bar.end_utc or not bar.closed):
                raise ValueError("BROKEN_GAPPED_M5_DAY_MEMBERSHIP_OR_CLOSE")
        if self.m5[COUNT_PER_PHASE].start_utc - self.m5[COUNT_PER_PHASE-1].end_utc != timedelta(hours=2):
            raise ValueError("GAP_EXPECTED_NO_M5_BAR")
        if self.m5[0].start_utc.astimezone(self.m5[0].start_utc.tzinfo).date() is None:
            raise AssertionError("DAY_UTC_CLOCK_ERROR")


@dataclass(frozen=True)
class FakeHistory:
    days:tuple[FakeDay,...]
    official_historical_exchange_calendar_verified:bool=False

    def __post_init__(self):
        if self.official_historical_exchange_calendar_verified is not False:
            raise PermissionError("NO_INDEPENDENT_HISTORICAL_VENUE_CALENDAR_PROOF")
        if type(self.days) is not tuple or len(self.days)!=FAKE_DAYS or any(type(d) is not FakeDay for d in self.days):
            raise TypeError("SIXTEEN_TYPED_FABRICATED_DAYS_REQUIRED")
        if tuple(d.ordinal for d in self.days)!=tuple(range(FAKE_DAYS)):
            raise ValueError("NONCONSECUTIVE_OR_DUPLICATE_FABRICATED_DAYS")
        for before,after in zip(self.days,self.days[1:]):
            if after.m5[0].start_utc-before.m5[0].start_utc!=timedelta(days=1):
                raise ValueError("DECLARED_24H_ARTIFICIAL_DAY_STEP_REQUIRED")


def fabricated_history():
    days=[]
    for day in range(FAKE_DAYS):
        shift=timedelta(days=day)
        offset=D(day*3)
        candles=[]
        for i in range(SOURCE_COUNT):
            b=source_bar(i)
            candles.append(replace(
                b,start_utc=b.start_utc+shift,
                end_utc=b.end_utc+shift,
                first_known_utc=b.first_known_utc+shift,
                open=b.open+offset,high=b.high+offset,
                low=b.low+offset,close=b.close+offset,
            ))
        days.append(FakeDay(day,tuple(candles)))
    return FakeHistory(tuple(days))


def per_day_groups(tf:str):
    template=fabricate_grid()
    if tf not in TIMEFRAMES:
        raise ValueError("UNSUPPORTED_TOY_TIMEFRAME")
    groups=template.for_tf(tf)
    if len(groups)!=KIND_PER_DAY[tf]:
        raise AssertionError("EXPLICIT_GAPPED_TF_GROUP_COUNT_DRIFT")
    return tuple(ToyGroup(tf,g.ordinal,g.members,binding(tf),g.crosses_declared_break) for g in groups)


def materialize_history(history:FakeHistory,tf:str):
    if type(history) is not FakeHistory:
        raise TypeError("EXACT_MULTISESSION_TYPED_FIXTURE_REQUIRED")
    groups=per_day_groups(tf)
    bars=[]
    for day in history.days:
        for group in groups:
            if group.binding_sha256!=binding(tf):
                raise PermissionError("MULTISESSION_FULL_V1_RIGHTS_POLICY_DRIFT")
            if group.crosses_declared_break != (tf in ("H4","D1")):
                raise PermissionError("FICTIONAL_H4_D1_STITCH_REQUIRED")
            bars.append(aggregate(group,day.m5))
    if len(bars)!=EXPECTED_TOTAL[tf] or tuple(sorted(b.start_utc for b in bars))!=tuple(b.start_utc for b in bars):
        raise ValueError("INCOMPLETE_OR_UNSORTED_MULTISESSION_BARS")
    return tuple(bars)


def changed_group(tf:str,day:int,index:int):
    groups=per_day_groups(tf)
    return next((day*KIND_PER_DAY[tf]+g.ordinal for g in groups if index in g.members),None)


def changed(history:FakeHistory,kind:str,day:int,index:int):
    if type(history) is not FakeHistory:
        raise TypeError("EXACT_MULTIDAY_FIXTURE_REQUIRED")
    if kind not in ("PRICE","METADATA"):
        raise ValueError("ONLY_TYPED_FAKE_CHANGE_TYPES")
    if type(day) is not int or not 0<=day<FAKE_DAYS or type(index) is not int or not 0<=index<SOURCE_COUNT:
        raise ValueError("DECLARED_DAY_AND_M5_INDEX_REQUIRED")
    days=list(history.days)
    rows=list(days[day].m5)
    old=rows[index]
    if kind=="PRICE":
        c=old.close+PRICE_DELTA
        b=replace(old,close=c,high=c+D(2),revision="r2",first_known_utc=CORRECTION_KNOWN)
    else:
        b=replace(old,revision="r3",first_known_utc=METADATA_KNOWN)
    rows[index]=b
    days[day]=replace(days[day],m5=tuple(rows))
    return FakeHistory(tuple(days))


def execute_oracle():
    original=fabricated_history()
    with TemporaryDirectory(prefix="mst-actions-16day-atr14-synthetic-") as directory:
        path=Path(directory)/"unlicensed-fixture.sqlite"
        db=SyntheticIncrementalStore(path)
        db.initialize()
        keys={}
        initial={}
        details={}
        for tf in TIMEFRAMES:
            key=multi_key(tf)
            rows=materialize_history(original,tf)
            if len(rows)!=EXPECTED_TOTAL[tf]:
                raise AssertionError("SIX_TF_COLD_WINDOW_COUNT_DRIFT")
            stat=db.apply_fixture_window(key,rows,observed_at_utc=COLD_AT,
                scope_start_utc=rows[0].start_utc,scope_end_utc=rows[-1].end_utc,
                complete_scope=True,full_session_reconciled=True)
            checkpoints=db.read_checkpoints(key)
            if stat.inserted!=len(rows) or stat.indicator_bars_recomputed!=len(rows):
                raise AssertionError("COLD_INCREMENTAL_BAR_COUNT_DRIFT_"+tf)
            if checkpoints!=full_recompute(rows) or checkpoints!=independent_ema_atr_oracle(rows):
                raise AssertionError("COLD_EMA_ATR_NUMERIC_ORACLE_DRIFT_"+tf)
            if (checkpoints[12].atr14 is not None or checkpoints[13].atr14 is None
                or checkpoints[-1].atr14 is None):
                raise AssertionError("SIX_TF_ATR14_INITIAL_SEED_WARMUP_DRIFT_"+tf)
            keys[tf]=key
            initial[tf]=checkpoints
            details[tf]={
                "closed_synthetic_windows":len(rows),
                "first_atr14_ordinal_zero_based":13,
                "atr14_actual_numeric_seed_and_last_value_verified":True,
                "cold_v1_incremental_equals_full_and_independent_decimal_oracle":True,
                "full_policy_binding_sha256":binding(tf),
            }

        # Reopen the exact same ephemeral GitHub-hosted SQLite file to prove
        # persistent synthetic checkpoint replay, not physical Drive custody.
        db=SyntheticIncrementalStore(path)
        for tf in TIMEFRAMES:
            if db.read_checkpoints(keys[tf])!=initial[tf]:
                raise AssertionError("SYNTHETIC_SQLITE_REOPEN_PARITY_DRIFT_"+tf)

        amended=changed(original,"PRICE",CHANGE_DAY,CHANGE_M5_IN_DAY)
        count=0
        for tf in TIMEFRAMES:
            index=changed_group(tf,CHANGE_DAY,CHANGE_M5_IN_DAY)
            if index is None:
                raise AssertionError("CHANGED_M5_CANNOT_MAP_TO_TF_"+tf)
            candidate=materialize_history(amended,tf)[index]
            oldbars=db.read_bars(keys[tf])
            if candidate.normalized_digest==oldbars[index].normalized_digest:
                raise AssertionError("PRICE_CHANGE_DID_NOT_REACH_TF_OHLCV_"+tf)
            stat=db.apply_fixture_window(keys[tf],(candidate,),
                observed_at_utc=CORRECTION_KNOWN,
                scope_start_utc=candidate.start_utc,scope_end_utc=candidate.end_utc,
                complete_scope=False)
            bars=db.read_bars(keys[tf])
            cp=db.read_checkpoints(keys[tf])
            expected_tail=len(bars)-index
            if (stat.revised!=1 or stat.indicator_bars_recomputed!=expected_tail
                or stat.first_dirty_utc!=candidate.start_utc or
                cp[:index]!=initial[tf][:index] or
                cp[index:]==initial[tf][index:]):
                raise AssertionError("SIX_TF_ACTUAL_CAUSAL_DIRTY_CHECKPOINT_SUFFIX_DRIFT_"+tf)
            if (cp!=full_recompute(bars) or cp!=independent_ema_atr_oracle(bars)
                or cp[-1].atr14 is None or cp[13].atr14 is None
                or cp[13].atr14==initial[tf][13].atr14 and tf in ("H4","D1")):
                raise AssertionError("SIX_TF_COLD_V1_AND_INDEPENDENT_ATR14_PARITY_DRIFT_"+tf)
            if expected_tail!=EXPECTED_SUFFIX[tf]:
                raise AssertionError("SIX_TF_EXPECTED_CORRECTION_REPLAY_COUNT_DRIFT_"+tf)
            details[tf].update({
                "changed_tf_group_ordinal":index,
                "numeric_checkpoint_suffix_recomputed":expected_tail,
                "late_history_revision_v1_full_and_independent_oracle_equal":True,
                "atr14_numerically_verified_after_correction":True,
                "unaffected_older_checkpoints_preserved":True,
            })
            count+=expected_tail

        lineage=changed(amended,"METADATA",META_DAY,META_M5_IN_DAY)
        for tf in TIMEFRAMES:
            idx=changed_group(tf,META_DAY,META_M5_IN_DAY)
            candidate=materialize_history(lineage,tf)[idx]
            before=db.read_bars(keys[tf])
            if candidate.normalized_digest!=before[idx].normalized_digest:
                raise AssertionError("META_ONLY_SOURCE_BAR_CHANGED_OHLCV_"+tf)
            before_cp=db.read_checkpoints(keys[tf])
            stat=db.apply_fixture_window(keys[tf],(candidate,),
                observed_at_utc=METADATA_KNOWN,
                scope_start_utc=candidate.start_utc,scope_end_utc=candidate.end_utc,
                complete_scope=False)
            bars=db.read_bars(keys[tf])
            cp=db.read_checkpoints(keys[tf])
            if (stat.lineage_only!=1 or stat.indicator_bars_recomputed!=0
                or cp!=before_cp or cp!=full_recompute(bars)
                or cp!=independent_ema_atr_oracle(bars)):
                raise AssertionError("MULTISESSION_META_ONLY_NUMERIC_CHECKPOINT_DRIFT_"+tf)
            details[tf]["metadata_only_indicator_recompute_zero"]=True
            details[tf]["reopened_sqlite_checkpoint_numeric_parity"]=True

        if count!=sum(EXPECTED_SUFFIX.values()) or count!=204:
            raise AssertionError("TOTAL_ACTUAL_MULTISESSION_INDICATOR_SUFFIX_COUNT_DRIFT")
        if db.read_bars(replace(keys["M5"],provider=Provider.DNSE)):
            raise PermissionError("CROSS_PROVIDER_SOURCE_CACHE_ISOLATION_FAILED")
        if db.read_bars(replace(keys["M5"],source_rights_policy_version="RIGHTS.REVOKED")):
            raise PermissionError("CROSS_RIGHTS_EPOCH_ISOLATION_FAILED")

    return {
        "schema":SCHEMA,"status":STATUS,
        "fake_consecutive_calendar_days_including_weekends":FAKE_DAYS,
        "official_exchange_trading_dates_claimed":False,
        "toy_day_declared_continuous_segments":["AM","PM"],
        "toy_nontrading_gap_minutes_each_day":120,
        "source_m5_total":FAKE_DAYS*SOURCE_COUNT,
        "timeframes":list(TIMEFRAMES),
        "window_counts":EXPECTED_TOTAL,
        "total_toy_closed_derived_windows":sum(EXPECTED_TOTAL.values()),
        "price_revision_day_ordinal":CHANGE_DAY,
        "price_revision_m5_ordinal_within_day":CHANGE_M5_IN_DAY,
        "all_six_tf_atr14_has_numerical_values_after_fourteen_closed_bars":True,
        "all_six_tf_independent_ema20_atr14_oracle_equal":True,
        "actual_v1_indicator_checkpoint_suffix_recomputed":count,
        "metadata_only_zero_numeric_indicator_recompute_all_six":True,
        "per_tf":details,
        "v2_multiday_candidate_scope_approved":False,
        "sixteen_day_v1_fingerprint_only_not_v2_manifest":True,
        "history_source_issuer_verified":False,
        "official_vn_exchange_historical_calendar_verified":False,
        "official_h4_d1_provider_aggregation_verified":False,
        "licensed_market_data_retention_or_cache_approved":False,
        "google_drive_market_ohlcv_io_performed":False,
        "independent_multiwriter_cas_signer_highwater_floor_verified":False,
        "release_or_trading_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    out=execute_oracle()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "schema":SCHEMA,"status":STATUS,
        "actual_v1_numeric_atr14_parity_six_tf":True,
        "cumulative_synthetic_closed_windows":out["total_toy_closed_derived_windows"],
        "corrected_checkpoints":out["actual_v1_indicator_checkpoint_suffix_recomputed"],
        "licensed_google_drive_quote_cache_enabled":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
