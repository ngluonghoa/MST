"""MST M4 P0 Cloud-only Google Drive OIDC *metadata-only* preflight.

GITHUB hosted PR QA uses fake file IDs and an injected in-memory metadata
reader. There are NO vendor data, tokens, local-machine resources or market
OHLCV in repository code/artifacts.

The optional live mode is exclusively a post-merge, MAIN-only, manual
GitHub Actions OIDC/WIF read-only metadata probe. It never reads Docs
contents, requests provider endpoints, lists arbitrary Drive files, persists
quotes, grants cloud retention rights or promotes the production cache.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Callable
from urllib.parse import quote

SCHEMA="mst.m4.oidc-drive-metadata-preflight.v1"
STATUS="SERVICE_IDENTITY_METADATA_PREFLIGHT_ONLY_PRODUCTION_INGEST_DENIED"
REPO="ngluonghoa/MST"
BRANCH="refs/heads/main"
DOC_MIME="application/vnd.google-apps.document"
FOLDER_MIME="application/vnd.google-apps.folder"
PROVIDERS=("SSI","DNSE","VCBS")
SCOPES=("https://www.googleapis.com/auth/drive.metadata.readonly",)
_ID=re.compile(r"^[A-Za-z0-9_-]{8,128}$")
EXPECTED_ORDER=("folder","manifest","SSI","DNSE","VCBS")
REQUEST_TIMEOUT_SECONDS=20

def _valid_id(value):
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError("EXACT_GOOGLE_DRIVE_FILE_ID_REQUIRED")
    return value

@dataclass(frozen=True)
class ReadOnlyIntent:
    folder_id:str
    manifest_doc_id:str
    source_doc_ids:dict[str,str]
    repo:str
    git_ref:str
    trigger:str
    allow_content_download:bool=False
    allow_drive_write:bool=False
    allow_licensed_ohlcv_ingestion:bool=False
    allow_cache_activation:bool=False
    def __post_init__(self):
        ids=[_valid_id(self.folder_id),_valid_id(self.manifest_doc_id)]
        if type(self.source_doc_ids) is not dict or set(self.source_doc_ids)!=set(PROVIDERS):
            raise ValueError("EXACT_SSI_DNSE_VCBS_SOURCE_DOC_IDS_REQUIRED")
        ids.extend(_valid_id(self.source_doc_ids[p]) for p in PROVIDERS)
        if len(set(ids))!=len(ids):
            raise ValueError("DUPLICATED_DRIVE_CUSTODY_OBJECT_IDS")
        if self.repo!=REPO or self.git_ref!=BRANCH or self.trigger!="workflow_dispatch":
            raise PermissionError("LIVE_PREFLIGHT_REQUIRES_MANUAL_DEFAULT_MAIN_REPO")
        for val in (self.allow_content_download,self.allow_drive_write,
                    self.allow_licensed_ohlcv_ingestion,self.allow_cache_activation):
            if type(val) is not bool or val:
                raise PermissionError("GOOGLE_DRIVE_PREFLIGHT_MUST_STAY_METADATA_READ_ONLY")
    @property
    def ordered_targets(self):
        return (("folder",self.folder_id),
                ("manifest",self.manifest_doc_id),
                *tuple((p,self.source_doc_ids[p]) for p in PROVIDERS))


def _guard_metadata(obj:object,*,target:str,target_id:str,folder_id:str)->dict:
    if type(obj) is not dict or obj.get("id")!=target_id or type(obj.get("parents",[])) is not list:
        raise PermissionError("MISMATCHED_OR_INCOMPLETE_DRIVE_METADATA_DENIED")
    if obj.get("trashed") is not False:
        raise PermissionError("TRASHED_OR_UNKNOWN_DRIVE_OBJECT_DENIED")
    if target=="folder":
        if obj.get("mimeType")!=FOLDER_MIME:
            raise PermissionError("EXPECTED_PRIVATE_CACHE_FOLDER_MIME_REQUIRED")
    else:
        if obj.get("mimeType")!=DOC_MIME or obj.get("parents")!=[folder_id]:
            raise PermissionError("DOC_MIME_OR_EXACT_PRIVATE_CACHE_PARENT_DRIFT")
    return {"kind":target,"mime_verified":True,
            "parent_scope_verified":target=="folder" or obj["parents"]==[folder_id],
            "id_reported_to_logs":False,"quote_content_downloaded":False}


def audit_metadata_only(intent:ReadOnlyIntent,
                        read_metadata:Callable[[str],dict])->dict:
    if type(intent) is not ReadOnlyIntent or not callable(read_metadata):
        raise TypeError("TYPED_READ_ONLY_INTENT_AND_READER_REQUIRED")
    checks=[]
    for target,file_id in intent.ordered_targets:
        checks.append(_guard_metadata(read_metadata(file_id),target=target,
                                      target_id=file_id,folder_id=intent.folder_id))
    if len(checks)!=len(EXPECTED_ORDER) or [r["kind"] for r in checks]!=list(EXPECTED_ORDER):
        raise AssertionError("EXPECTED_FIVE_METADATA_OBJECTS_DRIFT")
    return {
        "schema":SCHEMA,"status":STATUS,
        "folder_metadata_access_verified":True,
        "manifest_doc_metadata_access_verified":True,
        "three_source_docs_metadata_access_verified":True,
        "provider_namespaces_checked":list(PROVIDERS),
        "metadata_object_count":len(checks),
        "metadata_checks":checks,
        "actual_docs_content_read":False,
        "vendor_market_api_called":False,
        "market_ohlcv_downloaded":False,
        "google_drive_write_performed":False,
        "cloud_cache_automatic_refresh_active":False,
        "external_source_retention_license_attested":False,
        "issuer_first_known_and_official_calendar_attested":False,
        "external_signer_highwater_or_two_writer_cas_attested":False,
        "production_cache_or_trading_enabled":False,
    }


def read_google_file_metadata(file_id:str,session):
    """Single exact files.get allowlisted metadata request, no content or listing.

    The injected session in live mode is an AuthorizedSession using Google
    Workload Identity Federation credentials from GitHub Actions.
    """
    _valid_id(file_id)
    try:
        response=session.get(
            "https://www.googleapis.com/drive/v3/files/"+quote(file_id,safe=""),
            params={"fields":"id,mimeType,parents,trashed",
                    "supportsAllDrives":"true"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code!=200:
            raise PermissionError("DRIVE_READ_ONLY_METADATA_RESOURCE_NOT_ACCESSIBLE")
        body=response.json()
        if type(body) is not dict:
            raise PermissionError("DRIVE_METADATA_JSON_EXPECTED")
        return body
    except PermissionError:
        raise
    except Exception:
        # Never include Google authorization headers, request bodies or raw
        # exception text in a public GitHub Actions log.
        raise PermissionError("DRIVE_OIDC_METADATA_ACCESS_FAILED_CLOSED") from None


def intent_from_env(environ:dict)->ReadOnlyIntent:
    if type(environ) is not dict:
        raise TypeError("EXPLICIT_CLOUD_ENVIRONMENT_MAPPING_REQUIRED")
    raw=environ.get("MST_PILOT_SOURCE_DOC_IDS_JSON","")
    if type(raw) is not str or len(raw)>1000:
        raise ValueError("SCOPED_SOURCE_DOC_MAP_REQUIRED")
    try:
        mapping=json.loads(raw)
    except (ValueError,TypeError):
        raise ValueError("INVALID_CLOUD_SOURCE_DOC_MAP") from None
    return ReadOnlyIntent(
        folder_id=environ.get("MST_PILOT_FOLDER_ID",""),
        manifest_doc_id=environ.get("MST_PILOT_MANIFEST_ID",""),
        source_doc_ids=mapping,repo=environ.get("GITHUB_REPOSITORY",""),
        git_ref=environ.get("GITHUB_REF",""),trigger=environ.get("GITHUB_EVENT_NAME",""),
    )


def run_live_oidc(env:dict)->dict:
    intent=intent_from_env(env)
    # Strict GitHub Actions OIDC context gate (not a cryptographic assertion by
    # itself; Google must independently exchange/check the signed OIDC token).
    if not env.get("ACTIONS_ID_TOKEN_REQUEST_URL") or not env.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        raise PermissionError("GITHUB_ACTIONS_OIDC_REQUEST_CONTEXT_NOT_AVAILABLE")
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds,_=google.auth.default(scopes=list(SCOPES))
        session=AuthorizedSession(creds)
    except Exception:
        raise PermissionError("GOOGLE_WIF_DEFAULT_CREDENTIALS_NOT_AVAILABLE") from None
    audit=audit_metadata_only(intent,lambda id:read_google_file_metadata(id,session))
    audit["source"]="MAIN_ONLY_MANUAL_GITHUB_RUNNER_WIF_METADATA"
    audit["oidc_identity_exchanged_and_drive_metadata_accessed"]=True
    return audit


def synthetic_fixture():
    ids={p:"FAKE_DOC_"+p+"_00001" for p in PROVIDERS}
    folder="FAKE_FOLDER_MST_00001"
    manifest="FAKE_MANIFEST_MST_00001"
    intent=ReadOnlyIntent(folder,manifest,ids,REPO,BRANCH,"workflow_dispatch")
    items={folder:{"id":folder,"mimeType":FOLDER_MIME,"parents":[],"trashed":False}}
    for k,v in [("manifest",manifest),*[(p,ids[p]) for p in PROVIDERS]]:
        items[v]={"id":v,"mimeType":DOC_MIME,"parents":[folder],"trashed":False}
    return intent,items


def run_synthetic()->dict:
    intent,items=synthetic_fixture()
    received=[]
    def getter(file_id):
        received.append(file_id)
        return items[file_id]
    result=audit_metadata_only(intent,getter)
    if len(received)!=5 or result["metadata_object_count"]!=5:
        raise AssertionError("SYNTHETIC_METADATA_PROBE_COUNT_DRIFT")
    result["scope"]="FULLY_FAKE_FILE_IDS_ONLY_NOT_GOOGLE_AUTH_OR_REAL_PILOT"
    result["real_google_drive_credentials_exchanged"]=False
    result["real_google_drive_resource_metadata_retrieved"]=False
    result["actual_live_github_identity_configured"]=False
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("synthetic","live-readonly"),default="synthetic")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=run_synthetic() if args.mode=="synthetic" else run_live_oidc(dict(os.environ))
    # The receipt deliberately contains no file IDs, source prices, user
    # addresses, credential values, JWT, signatures or provider OHLCV.
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("status","metadata_object_count",
         "actual_docs_content_read","google_drive_write_performed",
         "production_cache_or_trading_enabled")},sort_keys=True))


if __name__=="__main__":
    main()
