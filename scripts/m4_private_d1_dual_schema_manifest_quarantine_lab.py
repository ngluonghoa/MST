"""MST M4: dual private D1 snapshot schema + manifest consistency audit, QA only.

Never reads Google Drive, never fetches market data. The caller supplies private
JSON documents via a separately authorized cloud reader. Public GitHub CI uses
only fictional mock documents; output omits all prices/timestamps/source bytes.

Important SOURCE-METADATA DRIFT: pilot FPT, DCM and HPG used two snapshot
schemas and two manifest schemas. DNSE unverified-unit labels differ from their
manifest labels; this validator QUARANTINES those differences, never silently
authorizes a unit conversion, data-rights upgrade, or production Cache write.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

STATUS = "MULTISYMBOL_REAL_SHAPE_AUDIT_UNIT_TOKEN_CONFLICT_QUARANTINE_NO_GO"
SCHEMAS = (
    "mst.chatgpt_mcp_source_snapshot.quarantine.v0.1",
    "mst.private_chatgpt_mcp_multi_symbol_daily_snapshot.v0.1",
)
MANIFESTS = (
    "mst.chatgpt_mcp_private_drive_cache_manifest.v0.1",
    "mst.private_connected_mcp_multiple_symbols_daily_manifest.v0.1",
)
PROVIDERS = ("SSI", "DNSE", "VCBS")
OHLC = ("open", "high", "low", "close")
FPT_FLAGS = (
    "vendor_license_for_external_retention_independently_verified",
    "official_vendor_first_known_or_revision_attested",
    "cloud_git_hub_actions_service_account_authenticated",
    "external_protected_cas_or_monotone_floor",
    "automatic_refresh_enabled",
    "production_cache_approved",
    "trading_authorized",
)
BATCH_FLAGS = (
    "independent_source_cloud_retention_license_verified",
    "issuer_first_known_signed",
    "official_venue_calendar_full_history_verified",
    "github_actions_identity_verified",
    "automated_refresh_running",
    "production_cache_writer_approved",
    "protected_cas_high_water_verified",
    "trade_authorized",
)
FPT_META = {
    "SSI": ("source_reported_adjusted", "VND_per_share"),
    "DNSE": ("source_price_basis_unverified", "source_native_DNSE_units_unverified"),
    "VCBS": ("adjusted", "VND_per_share"),
}
BATCH_META = {
    "SSI": ("source_adjusted_reported", "VND_per_share"),
    "DNSE": ("source_native_basis_unverified", "source_native_scale_unverified"),
    "VCBS": ("adjusted", "VND_per_share"),
}
# These are 3 distinct unverified metadata aliases, NOT unit conversions.
# No unknown unit alias can ever be used for a signal/production cache.
KNOWN_UNVERIFIED_DNSE_TOKEN_PAIRS = frozenset({
    ("source_native_DNSE_units_unverified", "source_native_units_unverified"),
    ("source_native_scale_unverified", "native_scale_unverified"),
})
FPT_MANIFEST_DENIED = (
    "vendor_cloud_retention_rights_independently_verified",
    "issuer_signed_first_known",
    "official_market_calendar_certified",
    "github_actions_service_account_can_access_chatgpt_mcp",
    "github_actions_automatic_refresh_configured",
    "content_addressed_atomic_cache_implemented",
    "remote_cas_signed_floor_implemented",
    "production_cache_approved",
    "trading_enabled",
)
BATCH_MANIFEST_DENIED = (
    "independent_vendor_retention_licenses_proven",
    "official_provider_first_known_or_calendar_proven",
    "github_actions_independent_mcp_access_proven",
    "github_actions_independent_google_wif_drive_access_proven",
    "automatic_refresh_or_sched_run_active",
    "atomic_drive_cache_cas_publisher_implemented",
    "cross_provider_unit_canonicalization_approved",
    "trading_released",
)


def parse_native_google_doc_text(text: str) -> dict:
    """Supports EXACT JSON or one native Doc heading followed by JSON.

    A heading is metadata, not an executable or free-form parser directive.
    """
    if type(text) is not str or len(text)>500_000:
        raise ValueError("BOUNDED_NATIVE_DOC_TEXT_REQUIRED")
    stripped=text.strip()
    if stripped.startswith("{"):
        raw=stripped
    else:
        header,sep,raw=stripped.partition("\n")
        if not sep or not header.startswith("MST ") or len(header)>140 or not raw.lstrip().startswith("{"):
            raise ValueError("ONE_MST_TITLE_LINE_THEN_JSON_REQUIRED")
    try:
        obj=json.loads(raw)
    except (ValueError,TypeError) as exc:
        raise ValueError("STRICT_SOURCE_JSON_REQUIRED") from exc
    if type(obj) is not dict:
        raise ValueError("EXACT_SOURCE_OBJECT_REQUIRED")
    return obj


def _day(token):
    if type(token) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",token):
        raise ValueError("STRICT_ISO_SOURCE_DAY_REQUIRED")
    try:
        d=date.fromisoformat(token)
    except ValueError as exc:
        raise ValueError("IMPOSSIBLE_SOURCE_DAY") from exc
    if d.isoformat()!=token:
        raise ValueError("NONCANONICAL_SOURCE_DAY")
    return d


def _num(value, *, positive=False):
    if type(value) not in (str,int,float):
        raise TypeError("EXPLICIT_SOURCE_NUMERIC_VALUE_REQUIRED")
    if type(value) is str and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?",value):
        raise ValueError("CANONICAL_NONNEGATIVE_SOURCE_NUMBER_REQUIRED")
    try:
        n=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("FINITE_SOURCE_NUMBER_REQUIRED") from exc
    if not n.is_finite() or (n<=0 if positive else n<0):
        raise ValueError("NONPOSITIVE_NONFINITE_SOURCE_NUMBER_DENIED")
    return n


def _flags_false(flags, names, label):
    if type(flags) is not dict or set(flags)!=set(names) or any(flags.get(k) is not False for k in names):
        raise PermissionError("EXACT_NO_GO_FLAGS_REQUIRED_"+label)


def check_snapshot(snapshot: dict, *, symbol: str, provider: str,
                   cutoff: str="2026-11-10") -> dict:
    if type(snapshot) is not dict or provider not in PROVIDERS or type(symbol) is not str or not re.fullmatch(r"[A-Z0-9-]{3,10}",symbol):
        raise ValueError("EXACT_PROVIDER_SYMBOL_SOURCE_REQUIRED")
    schema=snapshot.get("schema")
    if schema not in SCHEMAS:
        raise ValueError("UNREGISTERED_PRIVATE_SNAPSHOT_SCHEMA")
    pilot=schema==SCHEMAS[0]
    if pilot:
        scope=snapshot.get("scope")
        if (type(scope) is not dict or snapshot.get("snapshot_kind")!="ONE_TIME_USER_REQUESTED_CLOUD_PILOT_NOT_PRODUCTION"
            or scope.get("project")!="MST" or scope.get("symbol")!=symbol
            or scope.get("provider")!=provider or scope.get("timeframe")!="D1"
            or scope.get("source_method")!="ChatGPT connected MCP"):
            raise PermissionError("FPT_PILOT_SOURCE_SCOPE_DENIED")
        if (scope.get("basis"),scope.get("unit"))!=FPT_META[provider]:
            raise PermissionError("FPT_SOURCE_NATIVE_BASIS_UNIT_DRIFT")
        _flags_false(snapshot.get("governance"),FPT_FLAGS,"FPT")
        queried=_day(scope.get("queried_on_local_date"))
        first=_day(snapshot["rows"][0]["date"]) if type(snapshot.get("rows")) is list and snapshot["rows"] else None
        last=_day(scope.get("max_closed_session_date"))
        basis,unit=scope["basis"],scope["unit"]
    else:
        scope=snapshot
        if (snapshot.get("status")!="SOURCE_OBSERVED_PRIVATE_DRIVE_QUARANTINE_NOT_PRODUCTION"
            or snapshot.get("project")!="MST" or snapshot.get("symbol")!=symbol
            or snapshot.get("provider")!=provider or snapshot.get("timeframe")!="D1"
            or snapshot.get("source_method")!={"SSI":"marketdata_list_stock_daily_data",
                                               "DNSE":"price_get_history",
                                               "VCBS":"vcbs_get_history"}[provider]):
            raise PermissionError("BATCH_SOURCE_SCOPE_DENIED")
        if (scope.get("price_basis"),scope.get("price_unit"))!=BATCH_META[provider]:
            raise PermissionError("BATCH_SOURCE_NATIVE_BASIS_UNIT_DRIFT")
        _flags_false(snapshot.get("governance"),BATCH_FLAGS,"BATCH")
        queried=_day(scope.get("query_local_date"))
        first=_day(scope.get("first_session"))
        last=_day(scope.get("last_session"))
        basis,unit=scope["price_basis"],scope["price_unit"]
    end=_day(cutoff)
    if queried<=end or last>end or (first is not None and first>last):
        raise PermissionError("SOURCE_DAY_OPEN_OR_CUTOFF_MISMATCH")
    rows=snapshot.get("rows")
    if type(rows) is not list or len(rows)!=20 or type(snapshot.get("row_count")) is not int or snapshot["row_count"]!=len(rows):
        raise ValueError("TWENTY_REAL_SHAPED_PILOT_ROWS_REQUIRED")
    if type(first) is not date or _day(rows[0].get("date"))!=first or _day(rows[-1].get("date"))!=last:
        raise ValueError("SOURCE_ROW_RANGE_METADATA_MISMATCH")
    previous=None
    result=[]
    provisional_ambiguous=0
    for row in rows:
        if type(row) is not dict:
            raise TypeError("EXPLICIT_TYPED_SOURCE_ROW_REQUIRED")
        dt=_day(row.get("date"))
        if previous is not None and dt<=previous:
            raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_SOURCE_DAY_DENIED")
        if dt>end:
            raise PermissionError("SOURCE_DAILY_OPEN_OR_FUTURE_DENIED")
        previous=dt
        v={field:_num(row.get(field),positive=True) for field in OHLC}
        volume=_num(row.get("volume"))
        if v["low"]>min(v["open"],v["close"]) or v["high"]<max(v["open"],v["close"]) or v["low"]>v["high"]:
            raise ValueError("SOURCE_OHLC_ENVELOPE_INVALID")
        if provider=="SSI":
            if any(type(row.get(k)) is not str for k in (*OHLC,"volume")):
                raise ValueError("SSI_NATIVE_NUMERIC_STRING_POLICY_REQUIRED")
        if provider=="DNSE":
            t=row.get("source_unix_time")
            if type(t) is not int or not 100_000_000<=t<=4_000_000_000:
                raise ValueError("EXACT_DNSE_UNIX_SECONDS_REQUIRED")
            if datetime.fromtimestamp(t,timezone.utc).date()!=dt:
                raise PermissionError("DNSE_TIMESTAMP_DATE_MISMATCH")
        if provider=="VCBS":
            if row.get("priceBasis")!="adjusted" or row.get("volumeScope")!="matched" or row.get("price_unit")!="VND":
                raise PermissionError("VCBS_ROW_BASIS_UNIT_OR_VOLUME_SCOPE_DENIED")
            _num(row.get("raw_close"),positive=True)
            if pilot:
                if row.get("provisional") is not False:
                    raise PermissionError("VCBS_PILOT_EXPLICIT_PROVISIONAL_DENIED")
            else:
                if "provisional_source_flag" not in row or row["provisional_source_flag"] is not None:
                    raise PermissionError("VCBS_BATCH_UNKNOWN_PROVISIONAL_MUST_STAY_QUARANTINED")
                _num(row.get("adjFactor"),positive=True)
                provisional_ambiguous+=1
        result.append({"date":dt.isoformat(),"ohlc":v,"volume":volume})
    return {
        "symbol":symbol,"provider":provider,"basis":basis,"unit":unit,"schema":schema,
        "rows":result,"count":len(result),"first":result[0]["date"],"last":result[-1]["date"],
        "vcbs_provisional_unknown_rows":provisional_ambiguous,
        "provider_production_license_attested":False,
        "calendar_and_issuer_first_known_attested":False,
    }


def audit_private_dataset(partitions: dict, manifests: dict, *, cutoff="2026-11-10")->dict:
    """Partitions key (symbol,provider) -> (private File ID, parsed snapshot).

    Report ONLY counts and metadata conflicts; no quote row, hash of quote,
    raw timestamp, or per-symbol price data is returned.
    """
    if type(partitions) is not dict or type(manifests) is not dict or set(manifests)!={"pilot","batch"}:
        raise ValueError("EXACT_PRIVATE_MANIFEST_AND_PARTITIONS_REQUIRED")
    expected={(s,p) for s in ("AAA","BBB","CCC") for p in PROVIDERS}
    # Symbol set is an explicit caller-supplied three-symbol set; no hardcoded
    # real market instruments in public repository fixture or logic.
    symbols={key[0] for key in partitions if type(key) is tuple and len(key)==2}
    if len(symbols)!=3 or len(partitions)!=9:
        raise ValueError("EXACT_THREE_SYMBOL_NINE_SOURCE_PARTITIONS_REQUIRED")
    symbol_list=sorted(symbols)
    pilot_symbol=symbol_list[0]
    # Locate pilot by its pilot-schema, never assume alphabetical order.
    pilot_symbols={symbol for (symbol,provider),pair in partitions.items()
                   if type(pair) is tuple and len(pair)==2 and type(pair[1]) is dict
                   and pair[1].get("schema")==SCHEMAS[0]}
    if len(pilot_symbols)!=1:
        raise ValueError("EXACT_ONE_PILOT_SCHEMA_SYMBOL_REQUIRED")
    pilot_symbol=next(iter(pilot_symbols))
    if set(partitions)!={(s,p) for s in symbols for p in PROVIDERS}:
        raise ValueError("EXACT_ONE_PER_PROVIDER_PER_SYMBOL_REQUIRED")
    first_manifest=manifests["pilot"]
    batch_manifest=manifests["batch"]
    if (type(first_manifest) is not dict or first_manifest.get("schema")!=MANIFESTS[0]
        or first_manifest.get("status")!="ONE_TIME_READBACK_VERIFIED_QUARANTINED_PILOT_NOT_PRODUCTION"
        or first_manifest.get("project")!="MST" or first_manifest.get("symbol")!=pilot_symbol
        or first_manifest.get("timeframe")!="D1" or first_manifest.get("total_rows")!=60):
        raise PermissionError("PILOT_MANIFEST_OR_COUNTS_NOT_ATTESTED")
    if (type(batch_manifest) is not dict or batch_manifest.get("schema")!=MANIFESTS[1]
        or batch_manifest.get("status")!="QUARANTINED_PRIVATE_GOOGLE_DOCS_PILOT_NOT_PRODUCTION"
        or batch_manifest.get("project")!="MST" or batch_manifest.get("timeframe")!="D1"
        or batch_manifest.get("source_row_count")!=120
        or batch_manifest.get("rows_per_partition")!=20
        or batch_manifest.get("provider_partition_count")!=6
        or set(batch_manifest.get("symbols",[]))!=symbols-{pilot_symbol}):
        raise PermissionError("BATCH_MANIFEST_OR_COUNTS_NOT_ATTESTED")
    if (first_manifest.get("authority",{}).get("user_directed_one_time_capture") is not True
        or type(first_manifest.get("authority")) is not dict
        or set(first_manifest["authority"])!=set(FPT_MANIFEST_DENIED)|{"user_directed_one_time_capture"}):
        raise PermissionError("PILOT_MANIFEST_AUTHORITY_SCOPE_DENIED")
    _flags_false({k:first_manifest["authority"][k] for k in FPT_MANIFEST_DENIED},
                 FPT_MANIFEST_DENIED,"PILOT_MANIFEST")
    _flags_false(batch_manifest.get("authority"),BATCH_MANIFEST_DENIED,"BATCH_MANIFEST")
    pilot_entries=first_manifest.get("providers")
    batch_entries=batch_manifest.get("files")
    if (type(pilot_entries) is not list or type(batch_entries) is not list
        or len(pilot_entries)!=3 or len(batch_entries)!=6):
        raise ValueError("EXACT_MANIFEST_PROVIDER_FILE_ENTRIES_REQUIRED")
    parsed={}
    for (symbol,provider),(file_id,snapshot) in partitions.items():
        if type(file_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{15,100}",file_id):
            raise ValueError("EXACT_PRIVATE_SOURCE_FILE_ID_REQUIRED")
        checked=check_snapshot(snapshot,symbol=symbol,provider=provider,cutoff=cutoff)
        if (symbol==pilot_symbol)!=(checked["schema"]==SCHEMAS[0]):
            raise ValueError("PILOT_AND_BATCH_SCHEMAS_CANNOT_MIX_PER_SYMBOL")
        parsed[(symbol,provider)]=(file_id,checked)
    conflicts=[]
    total=0
    diag={}
    for symbol in symbols:
        controls=[]
        for provider in PROVIDERS:
            file_id,item=parsed[(symbol,provider)]
            entries=pilot_entries if symbol==pilot_symbol else batch_entries
            found=[x for x in entries if x.get("provider")==provider and
                   (symbol==pilot_symbol or x.get("symbol")==symbol)]
            if len(found)!=1:
                raise ValueError("EXACT_MANIFEST_ENTRY_MISSING_OR_DUPLICATE")
            entry=found[0]
            if entry.get("fileId")!=file_id or entry.get("rows")!=item["count"]:
                raise PermissionError("SOURCE_DOC_ID_OR_ROW_COUNT_MANIFEST_MISMATCH")
            if symbol==pilot_symbol:
                if entry.get("private") is not True or entry.get("readback_verified") is not True:
                    raise PermissionError("FPT_PRIVATE_READBACK_MANIFEST_NOT_CONFIRMED")
                basis=entry.get("price_basis")
                unit=entry.get("unit")
                first,last=first_manifest.get("first_session"),first_manifest.get("last_session")
            else:
                if entry.get("physical_private_doc_readback") is not True or entry.get("timeframe")!="D1":
                    raise PermissionError("BATCH_PRIVATE_READBACK_MANIFEST_NOT_CONFIRMED")
                basis=entry.get("basis")
                unit=entry.get("unit")
                first,last=entry.get("first_session"),entry.get("last_session")
            if basis!=item["basis"] or first!=item["first"] or last!=item["last"]:
                raise PermissionError("SOURCE_BASIS_OR_SESSION_MANIFEST_MISMATCH")
            if _num(entry.get("last_close"),positive=True)!=item["rows"][-1]["ohlc"]["close"]:
                raise PermissionError("MANIFEST_LAST_CLOSE_TAMPER_DENIED")
            if unit!=item["unit"]:
                if provider!="DNSE" or (item["unit"],unit) not in KNOWN_UNVERIFIED_DNSE_TOKEN_PAIRS:
                    raise PermissionError("UNRECOGNIZED_UNIT_METADATA_CONFLICT_DENIED")
                conflicts.append({"symbol":symbol,"provider":provider,"field":"unit",
                                  "status":"UNVERIFIED_UNIT_ALIAS_QUARANTINE"})
            total+=item["count"]
            controls.append(item)
        if any([r["date"] for r in controls[0]["rows"]]!=[z["date"] for z in c["rows"]] for c in controls[1:]):
            raise PermissionError("THREE_PROVIDER_DAILY_DATE_PARITY_INCOMPLETE")
        different_ssi_vcbs=0
        different_dnse_hypothesis=0
        different_volumes=0
        for a,b,c in zip(*(x["rows"] for x in controls)):
            if any(a["ohlc"][k]!=c["ohlc"][k] for k in OHLC):
                different_ssi_vcbs+=1
            # This multiplication is a DIAGNOSTIC HYPOTHESIS, NOT authorized
            # price unit normalization or approved indicator input.
            if any(a["ohlc"][k]!=Decimal(1000)*b["ohlc"][k] for k in OHLC):
                different_dnse_hypothesis+=1
            if a["volume"]!=b["volume"] or a["volume"]!=c["volume"]:
                different_volumes+=1
        diag[symbol]={
            "common_dates":len(controls[0]["rows"]),
            "ssi_vcbs_ohlc_mismatch_days":different_ssi_vcbs,
            "dnse_unapproved_1000_diagnostic_mismatch_days":different_dnse_hypothesis,
            "volume_mismatch_days":different_volumes,
        }
    return {
        "status":STATUS,
        "actual_private_docs_read_by_validator":False,
        "snapshot_schema_count":{SCHEMAS[0]:3,SCHEMAS[1]:6},
        "source_partition_count":len(parsed),
        "source_ohlcv_rows_structurally_checked":total,
        "source_manifests_checked":2,
        "source_manifest_unit_alias_conflicts":len(conflicts),
        "unit_alias_conflicts":sorted(conflicts,key=lambda x:(x["symbol"],x["provider"])),
        "source_diagnostics":diag,
        "all_original_unit_labels_preserved":True,
        "dnse_price_basis_and_scale_issuer_authenticated":False,
        "official_holiday_halt_and_exchange_calendar_verified":False,
        "source_first_known_and_corrections_attested":False,
        "authenticated_github_runner_drive_reader":False,
        "vendor_cloud_storage_rights_verified":False,
        "content_addressed_atomic_cache_or_trade_authorized":False,
        "production_admission":"DENIED_UNIT_LABEL_CONFLICT_AND_EXTERNAL_RIGHTS",
    }


def synthetic_three_source_fixture():
    """All symbols, rows and numbers fictional. NO quote data from real users."""
    symbols=("AAA","BBB","CCC")
    snapshots={}
    manifests={"pilot":{
        "schema":MANIFESTS[0],
        "status":"ONE_TIME_READBACK_VERIFIED_QUARANTINED_PILOT_NOT_PRODUCTION",
        "project":"MST","symbol":"AAA","timeframe":"D1","total_rows":60,
        "first_session":"2025-04-01","last_session":"2025-04-28",
        "authority":{"user_directed_one_time_capture":True,
                     **{k:False for k in FPT_MANIFEST_DENIED}},
        "providers":[],
    },"batch":{
        "schema":MANIFESTS[1],
        "status":"QUARANTINED_PRIVATE_GOOGLE_DOCS_PILOT_NOT_PRODUCTION",
        "project":"MST","timeframe":"D1","source_row_count":120,
        "rows_per_partition":20,"provider_partition_count":6,
        "symbols":["BBB","CCC"],
        "authority":{k:False for k in BATCH_MANIFEST_DENIED},
        "files":[],
    }}
    # April 2025 contains 22 weekdays. Use only invented 20 weekdays.
    days=[d.isoformat() for d in (date(2025,4,1).fromordinal(k) for k in range(date(2025,4,1).toordinal(),date(2025,4,29).toordinal())) if d.weekday()<5][:20]
    for symbol in symbols:
        for provider in PROVIDERS:
            pilot=symbol=="AAA"
            basis,unit=(FPT_META if pilot else BATCH_META)[provider]
            rows=[]
            for ix,day in enumerate(days):
                price=100+ix
                scale=1000 if provider!="DNSE" else 1
                row={
                    "date":day,"open":str(price*scale) if provider=="SSI" else price*scale,
                    "high":str((price+2)*scale) if provider=="SSI" else (price+2)*scale,
                    "low":str((price-1)*scale) if provider=="SSI" else (price-1)*scale,
                    "close":str((price+1)*scale) if provider=="SSI" else (price+1)*scale,
                    "volume":str(100+ix) if provider=="SSI" else 100+ix,
                }
                if provider=="DNSE":
                    row["source_unix_time"]=int(datetime.fromisoformat(day+"T00:00:00+00:00").timestamp())
                if provider=="VCBS":
                    row.update(raw_close=(price+1)*scale,priceBasis="adjusted",
                               volumeScope="matched",price_unit="VND")
                    if pilot:row["provisional"]=False
                    else:row.update(adjFactor=1,provisional_source_flag=None)
                rows.append(row)
            if pilot:
                snapshot={"schema":SCHEMAS[0],
                          "snapshot_kind":"ONE_TIME_USER_REQUESTED_CLOUD_PILOT_NOT_PRODUCTION",
                          "scope":{"project":"MST","symbol":symbol,"provider":provider,
                                   "timeframe":"D1","basis":basis,"unit":unit,
                                   "source_method":"ChatGPT connected MCP",
                                   "queried_on_local_date":"2025-04-30",
                                   "max_closed_session_date":"2025-04-28"},
                          "governance":{k:False for k in FPT_FLAGS},"row_count":20,"rows":rows}
            else:
                snapshot={"schema":SCHEMAS[1],
                          "status":"SOURCE_OBSERVED_PRIVATE_DRIVE_QUARANTINE_NOT_PRODUCTION",
                          "project":"MST","symbol":symbol,"provider":provider,"timeframe":"D1",
                          "source_method":{"SSI":"marketdata_list_stock_daily_data",
                                           "DNSE":"price_get_history","VCBS":"vcbs_get_history"}[provider],
                          "query_local_date":"2025-04-30",
                          "price_basis":basis,"price_unit":unit,
                          "first_session":days[0],"last_session":days[-1],
                          "governance":{k:False for k in BATCH_FLAGS},"row_count":20,"rows":rows}
            file_id=f"completely_fake_{symbol}_{provider}_source_doc_v1"
            snapshots[(symbol,provider)]=(file_id,snapshot)
            if pilot:
                manifests["pilot"]["providers"].append({
                    "provider":provider,"fileId":file_id,"rows":20,
                    "price_basis":basis,
                    "unit":("source_native_units_unverified" if provider=="DNSE" else unit),
                    "last_close":rows[-1]["close"],
                    "private":True,"readback_verified":True,
                })
            else:
                manifests["batch"]["files"].append({
                    "symbol":symbol,"provider":provider,"fileId":file_id,
                    "rows":20,"timeframe":"D1","first_session":days[0],
                    "last_session":days[-1],"basis":basis,
                    "unit":("native_scale_unverified" if provider=="DNSE" else unit),
                    "last_close":rows[-1]["close"],
                    "physical_private_doc_readback":True,
                })
    return snapshots,manifests


def synthetic_receipt():
    parts,manifests=synthetic_three_source_fixture()
    # The fixture explicitly does not model real market sessions.
    out=audit_private_dataset(parts,manifests,cutoff="2025-04-28")
    if out["source_ohlcv_rows_structurally_checked"]!=180 or out["source_manifest_unit_alias_conflicts"]!=3:
        raise AssertionError("PRIVATE_SCHEMA_COMPATIBILITY_FIXTURE_CHANGED")
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=synthetic_receipt()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":STATUS,"fictional_only":True,
                      "three_known_unverified_unit_aliases_stay_quarantined":True,
                      "cache_writer_enabled":False},sort_keys=True))


if __name__=="__main__":
    main()
