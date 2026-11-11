"""MST M4 P0: private pilot D1 snapshot contract and closed-session refresh planner.

The public GitHub PR CI uses wholly fictional source snapshots, never licensed
OHLCV or Google Drive bytes. Physical user-directed FPT D1 pilot evidence is
private in Google Drive, not encoded into the repository or workflow artifacts.

This module deliberately has NO network, vendor credentials or Drive writes.
It validates a per-provider payload and proposes idempotent candidate changes.
It cannot approve source rights, external issuer authority, real calendar
finality, auto-refresh, CAS, production cache, trade signals or orders.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path

SCHEMA="mst.chatgpt_mcp_source_snapshot.quarantine.v0.1"
MANIFEST_SCHEMA="mst.chatgpt_mcp_private_drive_cache_manifest.v0.1"
STATUS="PRIVATE_D1_SNAPSHOT_CONTRACT_AND_REFRESH_PLAN_NO_PRODUCTION_APPROVAL"
PROVIDERS=("SSI","DNSE","VCBS")
PRICE_FIELDS=("open","high","low","close")
SOURCE_META={
    "SSI":("source_reported_adjusted","VND_per_share"),
    "DNSE":("source_price_basis_unverified","source_native_DNSE_units_unverified"),
    "VCBS":("adjusted","VND_per_share"),
}
DENIED_FLAGS=(
    "vendor_license_for_external_retention_independently_verified",
    "issuer_signed_first_known","official_market_calendar_certified",
    "github_actions_service_account_can_access_chatgpt_mcp",
    "github_actions_automatic_refresh_configured",
    "content_addressed_atomic_cache_implemented",
    "remote_cas_signed_floor_implemented",
    "production_cache_approved","trading_authorized",
)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",",":"),
                      ensure_ascii=True,allow_nan=False)


def _fingerprint(value:object)->str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _closed_date(value: str)->date:
    if type(value) is not str:
        raise TypeError("EXPLICIT_ISO_DATE_REQUIRED")
    if len(value)!=10 or value[4]!="-" or value[7]!="-":
        raise ValueError("YYYY_MM_DD_DATE_REQUIRED")
    d=date.fromisoformat(value)
    if d.isoformat()!=value:
        raise ValueError("CANONICAL_YYYY_MM_DD_REQUIRED")
    return d


def _decimal(value:object, *, allow_zero:bool=False)->Decimal:
    if type(value) not in (str,int,float,Decimal) or type(value) is bool:
        raise TypeError("SOURCE_PRICE_OR_VOLUME_EXPLICIT_NUMBER_REQUIRED")
    try:
        x=Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("INVALID_NUMERIC_VALUE") from exc
    if not x.is_finite() or (x<0 if allow_zero else x<=0):
        raise ValueError("NEGATIVE_ZERO_OR_NONFINITE_SOURCE_PRICE")
    return x


def validate_snapshot(obj:dict,*, expected_provider:str,
                      historical_cutoff:str)->dict:
    """Strict structural validation of a private Google Docs JSON row payload."""
    if type(obj) is not dict or type(expected_provider) is not str or expected_provider not in PROVIDERS:
        raise TypeError("EXACT_PROVIDER_SCOPED_SNAPSHOT_REQUIRED")
    if obj.get("schema")!=SCHEMA:
        raise ValueError("UNSUPPORTED_PRIVATE_PILOT_SCHEMA")
    if obj.get("snapshot_kind")!="ONE_TIME_USER_REQUESTED_CLOUD_PILOT_NOT_PRODUCTION":
        raise PermissionError("UNAPPROVED_SNAPSHOT_KIND")
    scope=obj.get("scope")
    if type(scope) is not dict or scope.get("provider")!=expected_provider:
        raise PermissionError("CROSS_PROVIDER_OR_MISSING_SCOPE")
    if (scope.get("project")!="MST" or scope.get("symbol")!="FPT"
            or scope.get("timeframe")!="D1"
            or scope.get("source_method")!="ChatGPT connected MCP"):
        raise PermissionError("UNAPPROVED_PILOT_SYMBOL_TF_TRANSPORT")
    if (scope.get("basis"),scope.get("unit"))!=SOURCE_META[expected_provider]:
        raise PermissionError("SOURCE_PRICE_BASIS_OR_UNIT_UNQUALIFIED")
    queried=_closed_date(scope.get("queried_on_local_date"))
    source_cutoff=_closed_date(scope.get("max_closed_session_date"))
    asked_cutoff=_closed_date(historical_cutoff)
    if asked_cutoff>source_cutoff or source_cutoff>=queried:
        raise PermissionError("FUTURE_OPEN_OR_UNQUALIFIED_ASOF_CUTOFF")
    governance=obj.get("governance")
    if type(governance) is not dict or any(
        type(governance.get(k)) is not bool or governance.get(k) is not False
        for k in DENIED_FLAGS
    ):
        raise PermissionError("CALLER_CANNOT_CLAIM_REAL_DATA_RIGHTS_OR_RELEASE")
    rows=obj.get("rows")
    if type(rows) is not list or not rows or type(obj.get("row_count")) is not int or obj["row_count"]!=len(rows):
        raise ValueError("EXACT_NONEMPTY_SOURCE_ROW_COUNT_REQUIRED")
    if len(rows)>5000:
        raise ValueError("TOO_MANY_PILOT_SOURCE_ROWS")
    seen=set()
    ordered=[]
    checked=[]
    for row in rows:
        if type(row) is not dict or type(row.get("date")) is not str:
            raise TypeError("TYPED_SESSION_ROW_REQUIRED")
        day=_closed_date(row["date"])
        if day>asked_cutoff:
            raise PermissionError("OPEN_OR_FUTURE_SESSION_BAR_NOT_ALLOWED")
        if day in seen:
            raise ValueError("DUPLICATED_SOURCE_SESSION_DATE")
        if ordered and day<=ordered[-1]:
            raise ValueError("SOURCE_SESSIONS_NOT_STRICTLY_ASCENDING")
        seen.add(day)
        ordered.append(day)
        vals={k:_decimal(row.get(k)) for k in PRICE_FIELDS}
        vol=_decimal(row.get("volume"),allow_zero=True)
        if vals["low"]>min(vals["open"],vals["close"]) or vals["high"]<max(vals["open"],vals["close"]) or vals["high"]<vals["low"]:
            raise ValueError("SOURCE_OHLC_PRICE_ENVELOPE_INVALID")
        if expected_provider=="SSI":
            if any(type(row[k]) is not str for k in (*PRICE_FIELDS,"volume")):
                raise TypeError("SSI_NATIVE_NUMERIC_STRING_POLICY_REQUIRED")
        elif expected_provider=="DNSE":
            ts=row.get("source_unix_time")
            if type(ts) is not int:
                raise TypeError("DNSE_SOURCE_UNIX_TIMESTAMP_REQUIRED")
            if datetime.fromtimestamp(ts,timezone.utc).date()!=day:
                raise PermissionError("DNSE_SOURCE_UNIX_DATE_MISMATCH")
        elif expected_provider=="VCBS":
            if row.get("provisional") is not False or row.get("priceBasis")!="adjusted" or row.get("price_unit")!="VND" or row.get("volumeScope")!="matched":
                raise PermissionError("VCBS_PROVISIONAL_BASIS_UNIT_OR_VOLUME_SCOPE_NOT_QUALIFIED")
            if _decimal(row.get("raw_close"))<=0:
                raise ValueError("VCBS_RAW_CLOSE_REQUIRED")
        checked.append({
            "date":day.isoformat(),
            "values":{k:str(vals[k]) for k in PRICE_FIELDS},
            "volume":str(vol),
        })
    return {
        "provider":expected_provider,
        "namespace":f"MST|{expected_provider}|FPT|D1|{scope['basis']}|{scope['unit']}",
        "first_session":ordered[0].isoformat(),
        "last_session":ordered[-1].isoformat(),
        "row_count":len(rows),
        "scope_fingerprint_sha256":_fingerprint(scope),
        "rows_fingerprint_sha256":_fingerprint(rows),
        "numeric_rows":checked,
        "real_source_rights_approved":False,
        "auto_cache_refresh_enabled":False,
        "production_consumption_allowed":False,
    }


def verify_manifest(manifest:dict, snap_by_provider:dict[str,dict],
                    *, historical_cutoff:str)->dict:
    if type(manifest) is not dict or manifest.get("schema")!=MANIFEST_SCHEMA:
        raise ValueError("UNSUPPORTED_PRIVATE_PILOT_MANIFEST")
    if (manifest.get("status")!="ONE_TIME_READBACK_VERIFIED_QUARANTINED_PILOT_NOT_PRODUCTION"
            or manifest.get("project")!="MST" or manifest.get("symbol")!="FPT"
            or manifest.get("timeframe")!="D1"):
        raise PermissionError("SOURCE_PILOT_MANIFEST_NOT_ALLOWED")
    providers=manifest.get("providers")
    if type(providers) is not list or len(providers)!=3 or [p.get("provider") for p in providers]!=list(PROVIDERS):
        raise ValueError("EXACT_THREE_SOURCE_MANIFEST_REQUIRED")
    if type(snap_by_provider) is not dict or set(snap_by_provider)!=set(PROVIDERS):
        raise PermissionError("ALL_THREE_PROVIDER_SNAPSHOTS_REQUIRED")
    a=manifest.get("authority")
    if type(a) is not dict or any(a.get(k) is not False for k in (
        "vendor_cloud_retention_rights_independently_verified",
        "issuer_signed_first_known","official_market_calendar_certified",
        "github_actions_service_account_can_access_chatgpt_mcp",
        "github_actions_automatic_refresh_configured",
        "content_addressed_atomic_cache_implemented",
        "remote_cas_signed_floor_implemented",
        "production_cache_approved","trading_enabled",
    )):
        raise PermissionError("MANIFEST_AUTHORITY_MUST_NOT_SELF_PROMOTE")
    audits={}
    for p in providers:
        provider=p["provider"]
        if (type(p.get("fileId")) is not str or not p.get("fileId")
                or type(p.get("private")) is not bool or p["private"] is not True
                or type(p.get("readback_verified")) is not bool or p["readback_verified"] is not True):
            raise PermissionError("PRIVATE_READBACK_PROVENANCE_REQUIRED")
        audit=validate_snapshot(snap_by_provider[provider],expected_provider=provider,
                                historical_cutoff=historical_cutoff)
        if (audit["row_count"]!=p.get("rows") or
                snap_by_provider[provider]["scope"]["basis"]!=p.get("price_basis") or
                snap_by_provider[provider]["scope"]["unit"]!=p.get("unit") or
                str(snap_by_provider[provider]["rows"][-1]["close"])!=str(p.get("last_close"))):
            raise ValueError("MANIFEST_SOURCE_ROWS_BASIS_OR_LAST_CLOSE_MISMATCH")
        audits[provider]=audit
    dates=[[x["date"] for x in audits[p]["numeric_rows"]] for p in PROVIDERS]
    if dates[0]!=dates[1] or dates[1]!=dates[2]:
        raise PermissionError("CROSS_PROVIDER_DATE_PARITY_INCOMPLETE")
    if (manifest.get("total_rows")!=sum(a["row_count"] for a in audits.values()) or
            manifest.get("first_session")!=dates[0][0] or
            manifest.get("last_session")!=dates[0][-1]):
        raise ValueError("MANIFEST_GLOBAL_DATE_OR_ROW_COUNT_MISMATCH")
    # No automatic vendor unit normalization: comparisons remain explicit
    # diagnostic hypotheses rather than authoritative equality grants.
    compare={
        "equal_dates_count":len(dates[0]),
        "ssi_vcbs_native_ohlcv_equal":all(
            all(
                _decimal(audits["SSI"]["numeric_rows"][i]["values"][k])==
                _decimal(audits["VCBS"]["numeric_rows"][i]["values"][k])
                for k in PRICE_FIELDS
            ) and audits["SSI"]["numeric_rows"][i]["volume"]==
                  audits["VCBS"]["numeric_rows"][i]["volume"]
            for i in range(len(dates[0]))
        ),
        "dnse_factor_1000_observed_but_not_approved":all(
            all(
                _decimal(audits["DNSE"]["numeric_rows"][i]["values"][k])*Decimal(1000)==
                _decimal(audits["SSI"]["numeric_rows"][i]["values"][k])
                for k in PRICE_FIELDS
            ) for i in range(len(dates[0]))
        ),
        "dnse_unit_and_price_basis_authenticated":False,
        "independent_license_or_github_cloud_auth_verified":False,
        "automatic_refresh_or_production_cache":False,
    }
    return {
        "status":STATUS,
        "project":"MST", "symbol":"FPT","timeframe":"D1",
        "total_verified_rows":sum(a["row_count"] for a in audits.values()),
        "providers":{p:{
            "rows":audits[p]["row_count"],
            "namespace":audits[p]["namespace"],
            "sha256":audits[p]["rows_fingerprint_sha256"],
        } for p in PROVIDERS},
        "cross_source_diagnostic":compare,
        "production_and_trading_no_go":True,
    }


def plan_closed_day_refresh(before:dict, after:dict, *,
                            provider:str,historical_cutoff:str)->dict:
    left=validate_snapshot(before,expected_provider=provider,historical_cutoff=historical_cutoff)
    right=validate_snapshot(after,expected_provider=provider,historical_cutoff=historical_cutoff)
    if left["namespace"]!=right["namespace"]:
        raise PermissionError("INCREMENTAL_SOURCE_NAMESPACE_DRIFT")
    old={x["date"]:x for x in left["numeric_rows"]}
    new={x["date"]:x for x in right["numeric_rows"]}
    missing=sorted(set(old)-set(new))
    if missing:
        raise PermissionError("SOURCE_LOST_PREVIOUSLY_CACHED_SESSIONS_DENIED")
    appended=sorted(set(new)-set(old))
    revised=sorted(d for d in set(new)&set(old) if new[d]!=old[d])
    unchanged=sorted(d for d in set(new)&set(old) if new[d]==old[d])
    # Numeric-only is not sufficient for issuer revision custody.
    return {
        "provider":provider,
        "namespace":left["namespace"],
        "proposed_new_closed_sessions":appended,
        "observed_value_revision_dates_require_issuer_verification":revised,
        "unchanged_numeric_sessions":len(unchanged),
        "requires_source_license_and_revision_proof":bool(appended or revised),
        "drive_write_or_manifest_promotion_authorized":False,
        "production_and_trading_no_go":True,
    }


def fabricated_fixture() -> tuple[dict,dict]:
    """Two imaginary dates and 3 completely fabricated namespaces; NO real FPT prices."""
    def snapshot(provider):
        meta=SOURCE_META[provider]
        rows=[]
        for i,d in enumerate(("2026-11-02","2026-11-03")):
            v=100+i
            if provider=="DNSE":
                price=[v/1000,(v+2)/1000,(v-1)/1000,(v+1)/1000]
                row={"date":d,"open":price[0],"high":price[1],
                     "low":price[2],"close":price[3],"volume":200+i,
                     "source_unix_time":int(datetime.fromisoformat(d+"T02:00:00+00:00").timestamp())}
            elif provider=="SSI":
                row={"date":d,"open":str(v),"high":str(v+2),"low":str(v-1),
                     "close":str(v+1),"volume":str(200+i)}
            else:
                row={"date":d,"open":v,"high":v+2,"low":v-1,
                     "close":v+1,"raw_close":v+1,"volume":200+i,
                     "provisional":False,"priceBasis":"adjusted","volumeScope":"matched","price_unit":"VND"}
            rows.append(row)
        return {
            "schema":SCHEMA,
            "snapshot_kind":"ONE_TIME_USER_REQUESTED_CLOUD_PILOT_NOT_PRODUCTION",
            "scope":{"project":"MST","provider":provider,"symbol":"FPT","timeframe":"D1",
                     "basis":meta[0],"unit":meta[1],"source_method":"ChatGPT connected MCP",
                     "queried_on_local_date":"2026-11-05","max_closed_session_date":"2026-11-03"},
            "governance":{k:False for k in DENIED_FLAGS},
            "row_count":len(rows),"rows":rows,
        }
    snapshots={p:snapshot(p) for p in PROVIDERS}
    manifest={
        "schema":MANIFEST_SCHEMA,
        "status":"ONE_TIME_READBACK_VERIFIED_QUARANTINED_PILOT_NOT_PRODUCTION",
        "project":"MST","symbol":"FPT","timeframe":"D1",
        "first_session":"2026-11-02","last_session":"2026-11-03",
        "total_rows":6,
        "providers":[{
            "provider":p,"rows":2,
            "fileId":"FAKE_DOC_"+p,"private":True,"readback_verified":True,
            "price_basis":SOURCE_META[p][0],"unit":SOURCE_META[p][1],
            "last_close":snapshots[p]["rows"][-1]["close"],
        } for p in PROVIDERS],
        "authority":{
            "vendor_cloud_retention_rights_independently_verified":False,
            "issuer_signed_first_known":False,"official_market_calendar_certified":False,
            "github_actions_service_account_can_access_chatgpt_mcp":False,
            "github_actions_automatic_refresh_configured":False,
            "content_addressed_atomic_cache_implemented":False,
            "remote_cas_signed_floor_implemented":False,
            "production_cache_approved":False,"trading_enabled":False,
        },
    }
    return manifest,snapshots


def run_lab()->dict:
    manifest,snapshots=fabricated_fixture()
    audited=verify_manifest(manifest,snapshots,historical_cutoff="2026-11-03")
    planner=plan_closed_day_refresh(snapshots["SSI"],snapshots["SSI"],
                                    provider="SSI",historical_cutoff="2026-11-03")
    if (audited["total_verified_rows"]!=6 or
        audited["cross_source_diagnostic"]["equal_dates_count"]!=2 or
        planner["proposed_new_closed_sessions"]!=[] or
        not audited["production_and_trading_no_go"]):
        raise AssertionError("PRIVATE_PILOT_CONTRACT_CLOSED_DAY_DENIAL_DRIFT")
    return {
        "schema":"mst.m4.private_pilot_d1_contract.synthetic.v1",
        "status":STATUS,
        "source_records_are_completely_fabricated":True,
        "original_real_mcp_market_data_in_github_artifacts":False,
        "pilot_contract_validation":audited,
        "idempotent_same_snapshot_refresh_plan":planner,
        "github_actions_account_authentication_performed":False,
        "real_drive_docs_read_write_performed_in_ci":False,
        "automatic_live_provider_ingestion_active":False,
        "all_production_gates_no_go":True,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args(argv)
    r=run_lab()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":STATUS,"synthetic_source_rows":r["pilot_contract_validation"]["total_verified_rows"],"real_cloud_reuse_authorized":False},sort_keys=True))

if __name__=="__main__":
    main()
