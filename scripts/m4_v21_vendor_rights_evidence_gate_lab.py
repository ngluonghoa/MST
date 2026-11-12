"""MST M3/M4 P0 public source-evidence inventory and fail-closed rights gate.

Only reference identifiers and factual public-document metadata are enumerated.
No credentials, vendor data, HTTP requests, storage, signed issuer evidence,
Cloud authentication, Google Drive quote cache or real entitlements exist.
A PUBLIC page or user-supplied 'approved' field NEVER grants data use/retention.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "mst.m3.p0.vendor-public-evidence-rights-gate.synthetic.v1"
STATUS = "PUBLIC_DOCS_REVIEWED_NO_LIVE_PROVIDER_LICENSE_OR_CLOUD_CACHE_AUTH"
RESEARCH_DATE = date(2026, 11, 11)
PROVIDERS = ("SSI", "DNSE", "VCBS")
_HOSTS = {
    "SSI": frozenset(("developers.ssi.com.vn",)),
    "DNSE": frozenset(("developers.dnse.com.vn",)),
    "VCBS": frozenset(("ai.vcbs.com.vn",)),
    "HNX": frozenset(("www.gov.hnx.vn",)),
}

class DocumentRole(str, Enum):
    CAPABILITY = "PUBLIC_CAPABILITY"
    PROVIDER_TERMS = "PUBLIC_PROVIDER_TERMS"
    MCP_INTERFACE = "PUBLIC_CHAT_MCP_INTERFACE"
    VENUE_ANNOUNCEMENT = "PUBLIC_VENUE_CALENDAR_NOTICE"

class IntendedUse(str, Enum):
    MARKET_DATA_READ = "MARKET_DATA_READ"
    DERIVED_INDICATORS = "DERIVED_INDICATORS"
    HISTORICAL_BACKTEST = "HISTORICAL_BACKTEST"
    GOOGLE_DRIVE_RETENTION = "GOOGLE_DRIVE_RETENTION"
    GITHUB_ACTIONS_TRANSPORT = "GITHUB_ACTIONS_TRANSPORT"

def fingerprint(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()

def _asof(value: datetime) -> datetime:
    if type(value) is not datetime or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise TypeError("EXPLICIT_ZERO_OFFSET_UTC_ASOF_REQUIRED")
    return value

@dataclass(frozen=True)
class PublicDocument:
    doc_id: str
    scope: str
    role: DocumentRole
    url: str
    observed_on: date
    synopsis: str
    grants_account_access: bool = False
    grants_cache_retention: bool = False
    proves_first_known: bool = False
    official_full_history_authenticated: bool = False

    def __post_init__(self):
        if type(self.doc_id) is not str or not self.doc_id.startswith("MST_PUBLIC_"):
            raise ValueError("REVIEWED_PUBLIC_DOCUMENT_ID_REQUIRED")
        if type(self.scope) is not str or self.scope not in _HOSTS:
            raise ValueError("EXACT_KNOWN_PUBLIC_ISSUER_SCOPE_REQUIRED")
        if type(self.role) is not DocumentRole:
            raise TypeError("EXPLICIT_PUBLIC_EVIDENCE_ROLE_REQUIRED")
        if type(self.url) is not str:
            raise TypeError("EXPLICIT_STATIC_SOURCE_URL_REQUIRED")
        url = urlsplit(self.url)
        if (url.scheme != "https" or url.hostname not in _HOSTS[self.scope]
                or url.username is not None or url.password is not None
                or url.port is not None or not url.path.startswith("/")
                or url.fragment or url.query):
            raise ValueError("SOURCE_URL_MUST_MATCH_APPROVED_OFFICIAL_HOST_NO_QUERY")
        if type(self.observed_on) is not date or self.observed_on > RESEARCH_DATE:
            raise ValueError("EXPLICIT_REVIEW_DATE_MUST_NOT_BE_FUTURE")
        if type(self.synopsis) is not str or not (15 <= len(self.synopsis) <= 400):
            raise ValueError("REVIEWED_SCOPE_SUMMARY_REQUIRED")
        if (type(self.grants_account_access) is not bool
                or type(self.grants_cache_retention) is not bool
                or type(self.proves_first_known) is not bool
                or type(self.official_full_history_authenticated) is not bool):
            raise TypeError("EXPLICIT_BOOLEAN_EXTERNAL_PROOF_FLAGS_REQUIRED")
        if (self.grants_account_access is not False
                or self.grants_cache_retention is not False
                or self.proves_first_known is not False
                or self.official_full_history_authenticated is not False):
            raise PermissionError("PUBLIC_DOC_CANNOT_SELF_GRANT_SOURCE_OR_LICENSE_PROOF")
        if self.scope == "HNX" and self.role is not DocumentRole.VENUE_ANNOUNCEMENT:
            raise ValueError("HNX_NOTICE_NOT_VENDOR_LICENSE_OR_MARKET_API")
        if self.scope != "HNX" and self.role is DocumentRole.VENUE_ANNOUNCEMENT:
            raise ValueError("VENDOR_PAGE_NOT_OFFICIAL_EXCHANGE_ISSUER")
        if self.scope == "VCBS" and self.role is not DocumentRole.MCP_INTERFACE:
            # VCBS review here is explicitly only the documented AI MCP surface.
            raise ValueError("VCBS_MCP_PUBLIC_PAGE_NOT_NON_MCP_DATA_LICENSE")

    @property
    def source_digest(self) -> str:
        return fingerprint({
            "schema": SCHEMA,
            "scope": self.scope, "role": self.role.value,
            "doc_id": self.doc_id,
            "url": self.url,
            "observed_on": self.observed_on.isoformat(),
            "synopsis": self.synopsis,
            "source_is_public_unlicensed_capability_note": True,
        })


def public_catalog() -> tuple[PublicDocument, ...]:
    """Static URL-only research notes, not downloaded in CI or accepted contract."""
    return (
        PublicDocument("MST_PUBLIC_SSI_OVERVIEW", "SSI", DocumentRole.CAPABILITY,
                       "https://developers.ssi.com.vn/docs/getting-started/overview",
                       RESEARCH_DATE, "SSI FastConnect V3 publicly describes market-data and OHLCV API capabilities."),
        PublicDocument("MST_PUBLIC_SSI_TERMS", "SSI", DocumentRole.PROVIDER_TERMS,
                       "https://developers.ssi.com.vn/en/term-condition",
                       RESEARCH_DATE, "SSI terms restrict API information to client securities-trading purpose and restrict third-party sharing, including processed information."),
        PublicDocument("MST_PUBLIC_SSI_ENVIRONMENT", "SSI", DocumentRole.CAPABILITY,
                       "https://developers.ssi.com.vn/docs/getting-started/terms-and-environments",
                       RESEARCH_DATE, "SSI publication describes registration, environments, indicative sessions, rate-limit headers and historical-depth notes."),
        PublicDocument("MST_PUBLIC_DNSE_OHLC", "DNSE", DocumentRole.CAPABILITY,
                       "https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/",
                       RESEARCH_DATE, "DNSE public history OHLC endpoint describes requested symbols and candle resolutions, but not contract retention rights."),
        PublicDocument("MST_PUBLIC_DNSE_FAQ", "DNSE", DocumentRole.CAPABILITY,
                       "https://developers.dnse.com.vn/docs/guide/faq/",
                       RESEARCH_DATE, "DNSE public documentation describes API registration, signed request headers and separate streaming candle-closure events."),
        PublicDocument("MST_PUBLIC_VCBS_MCP", "VCBS", DocumentRole.MCP_INTERFACE,
                       "https://ai.vcbs.com.vn/mcp",
                       RESEARCH_DATE, "VCBS AI describes a user-authorized read-only chat MCP connection, not GitHub Actions transport or cache licenses."),
        PublicDocument("MST_PUBLIC_HNX_2026_HOLIDAYS", "HNX", DocumentRole.VENUE_ANNOUNCEMENT,
                       "https://www.gov.hnx.vn/vi-vn/chi-tiet-lich-nghi-gd-60021971.html",
                       RESEARCH_DATE, "HNX official 2026 market holiday notice is contextual venue evidence, not a full historical source-issuer calendar or feed license."),
    )


@dataclass(frozen=True)
class ReviewRequest:
    provider: str
    intended_use: IntendedUse
    as_of_utc: datetime
    symbol: str
    owner_release_approved: bool = False
    live_source_credential_verified: bool = False
    contract_rights_verified: bool = False
    external_custody_verified: bool = False

    def __post_init__(self):
        if type(self.provider) is not str or self.provider not in PROVIDERS:
            raise ValueError("EXPLICIT_PROVIDER_SSI_DNSE_VCBS_REQUIRED")
        if type(self.intended_use) is not IntendedUse:
            raise TypeError("TYPED_INTENDED_USE_REQUIRED")
        _asof(self.as_of_utc)
        if type(self.symbol) is not str or not self.symbol or not self.symbol.isascii() or len(self.symbol)>16 or not all(c.isupper() or c.isdigit() or c=="-" for c in self.symbol):
            raise ValueError("NORMALIZED_SYNTHETIC_SYMBOL_REQUIRED")
        if any(type(v) is not bool for v in (
                self.owner_release_approved, self.live_source_credential_verified,
                self.contract_rights_verified, self.external_custody_verified)):
            raise TypeError("EXPLICIT_BOOLEAN_SOURCE_APPROVAL_FLAGS_REQUIRED")
        if any((self.owner_release_approved,
                self.live_source_credential_verified,
                self.contract_rights_verified,
                self.external_custody_verified)):
            raise PermissionError("CALLER_FLAGS_CANNOT_ENROLL_EXTERNAL_SOURCE_PROOF")


@dataclass(frozen=True)
class AdmissionDecision:
    provider: str
    intended_use: str
    as_of_utc: str
    status: str
    public_docs_digest: str
    reviewed_public_doc_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    read_live_provider_allowed: bool = False
    write_cloud_cache_allowed: bool = False
    run_real_backtest_allowed: bool = False
    use_market_data_for_trading_allowed: bool = False

    def __post_init__(self):
        if self.status != "DENIED_UNVERIFIED_RIGHTS":
            raise PermissionError("ONLY_DENY_DECISION_SUPPORTED_BEFORE_REAL_ISSUER_ENROLLMENT")
        if any(type(v) is not bool for v in (
                self.read_live_provider_allowed, self.write_cloud_cache_allowed,
                self.run_real_backtest_allowed, self.use_market_data_for_trading_allowed)):
            raise TypeError("EXPLICIT_BOOLEAN_ADMISSION_FLAGS_REQUIRED")
        if any((self.read_live_provider_allowed, self.write_cloud_cache_allowed,
                self.run_real_backtest_allowed, self.use_market_data_for_trading_allowed)):
            raise PermissionError("LOCAL_PUBLIC_DOCS_CANNOT_PROMOTE_TO_REAL_MARKET_GRANT")
        if not self.blockers:
            raise ValueError("FAIL_CLOSED_REQUIRES_EXPLICIT_BLOCKERS")


BASE_BLOCKERS = (
    "ACTUAL_ACCOUNT_AND_ENDPOINT_CREDENTIAL_SCOPE_NOT_INDEPENDENTLY_VERIFIED",
    "EXECUTED_TERMS_AND_CLOUD_RETENTION_RIGHTS_NOT_INDEPENDENTLY_PROVEN",
    "DERIVED_INDICATOR_BACKTEST_AND_THIRD_PARTY_PERMISSIONS_NOT_PROVEN",
    "OFFICIAL_HISTORICAL_VENUE_CALENDAR_AND_AUCTION_CORRECTIONS_NOT_ATTESTED",
    "SOURCE_FIRST_KNOWN_AND_REVISION_ISSUER_PROVENANCE_NOT_ATTESTED",
    "GITHUB_ACTIONS_CLOUD_IDENTITY_AND_ALLOWED_TRANSPORT_NOT_VERIFIED",
    "PROTECTED_EXTERNAL_SIGNER_HIGH_WATER_AND_TWO_WRITER_CAS_NOT_VERIFIED",
    "OWNER_APPROVED_V2_ABI_AND_RELEASE_GATES_STILL_OPEN",
)
PROVIDER_BLOCKERS = {
    "SSI": "SSI_FASTCONNECT_TERMS_RESTRICT_PURPOSE_AND_THIRD_PARTY_DATA_SHARING",
    "DNSE": "DNSE_PUBLIC_OHLC_ENDPOINT_DOES_NOT_GRANT_CLOUD_RETENTION_OR_H4_AGGREGATION_RIGHTS",
    "VCBS": "VCBS_USER_CHAT_MCP_IS_NOT_AUTHORIZED_GITHUB_ACTIONS_OR_DRIVE_PIPELINE",
}

def review(request: ReviewRequest, *, catalog: tuple[PublicDocument,...] | None = None) -> AdmissionDecision:
    if type(request) is not ReviewRequest:
        raise TypeError("EXACT_REVIEW_REQUEST_REQUIRED")
    docs = public_catalog() if catalog is None else catalog
    if type(docs) is not tuple or any(type(d) is not PublicDocument for d in docs):
        raise TypeError("EXACT_IMMUTABLE_REVIEWED_PUBLIC_SOURCE_DOCS_REQUIRED")
    if len({d.doc_id for d in docs}) != len(docs):
        raise ValueError("DUPLICATE_PUBLIC_EVIDENCE_DOC_ID_DENIED")
    if len({(d.scope,d.url) for d in docs}) != len(docs):
        raise ValueError("DUPLICATE_OFFICIAL_SOURCE_URL_DENIED")
    own = tuple(sorted((d for d in docs if d.scope == request.provider), key=lambda d:d.doc_id))
    hnx = tuple(d for d in docs if d.scope=="HNX")
    if not own:
        raise ValueError("NO_PROVIDER_PUBLIC_INTERFACE_DOCS_REVIEWED")
    # A known provider doc and one exchange notice cannot establish an executed
    # data-rights agreement or the full effective venue historical calendar.
    if not hnx:
        raise ValueError("MISSING_EXCHANGE_PUBLIC_CALENDAR_CONTEXT")
    ids=tuple(sorted(d.doc_id for d in own + hnx))
    relevant=tuple(sorted((d.source_digest for d in own + hnx)))
    return AdmissionDecision(
        request.provider, request.intended_use.value,
        request.as_of_utc.isoformat(), "DENIED_UNVERIFIED_RIGHTS",
        fingerprint({"doc_sha256s":relevant,"provider":request.provider,"schema":SCHEMA}),
        ids,
        BASE_BLOCKERS + (PROVIDER_BLOCKERS[request.provider],),
    )


def require_live_permission(decision: AdmissionDecision) -> None:
    if type(decision) is not AdmissionDecision:
        raise TypeError("EXACT_UNTRUSTED_ADMISSION_DECISION_REQUIRED")
    raise PermissionError("M3_M4_EXTERNAL_ACCOUNT_LICENSE_CALENDAR_CUSTODY_NOT_VERIFIED_NO_LIVE_IO")


def build_report() -> dict:
    asof=datetime(2026,11,11,5,0,tzinfo=timezone.utc)
    catalog=public_catalog()
    if len(catalog)!=7:
        raise AssertionError("EXPLICIT_SEVEN_PUBLIC_DOC_INVENTORY_DRIFT")
    summaries={}
    for provider in PROVIDERS:
        per_use={}
        for intended_use in IntendedUse:
            decision=review(ReviewRequest(provider,intended_use,asof,"FAKE001"),catalog=catalog)
            if (decision.status!="DENIED_UNVERIFIED_RIGHTS" or
                    len(decision.blockers)!=len(BASE_BLOCKERS)+1 or
                    decision.read_live_provider_allowed or decision.write_cloud_cache_allowed):
                raise AssertionError("PUBLIC_MARKET_DOCS_WRONGLY_PROMOTED_TO_DATA_RIGHTS")
            per_use[intended_use.value]={
                "status":decision.status,
                "reviewed_doc_ids":list(decision.reviewed_public_doc_ids),
                "public_docs_sha256":decision.public_docs_digest,
                "provider_specific_blocker":PROVIDER_BLOCKERS[provider],
                "data_rights_or_live_access_approved":False,
            }
        summaries[provider]=per_use
    return {
        "schema":SCHEMA,"status":STATUS,
        "reviewed_on":RESEARCH_DATE.isoformat(),
        "provider_namespaces":list(PROVIDERS),
        "public_source_documents": [
            {"doc_id":d.doc_id,"scope":d.scope,"url":d.url,
             "role":d.role.value,"sha256":d.source_digest} for d in catalog
        ],
        "reviewed_public_document_count":len(catalog),
        "intended_use_probes_per_provider":len(IntendedUse),
        "total_denied_probes":len(PROVIDERS)*len(IntendedUse),
        "per_provider_use_denials":summaries,
        "ssi_published_restriction_not_contract_waiver":True,
        "dnse_ohlc_api_discovery_not_cloud_retention_permission":True,
        "vcbs_mcp_chat_user_connection_not_ci_service_account":True,
        "hnx_2026_notice_not_full_historical_exchange_attestation":True,
        "public_references_fetched_in_github_ci":False,
        "actual_vendor_market_ohlcv_requested_or_retained":False,
        "gdrive_quote_cache_read_write":False,
        "verified_external_issuer_or_license_evidence":False,
        "protected_signer_cas_high_water":False,
        "owner_approved_live_release_or_trading":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    result=build_report()
    if args.out is not None:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":STATUS,"reviewed_public_docs":7,
        "denied_provider_intent_probes":result["total_denied_probes"],
        "live_cache_or_trading":False},sort_keys=True))

if __name__=="__main__":
    main()
