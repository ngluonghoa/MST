"""§194 Strict *new-format* private candidate identity readback.

Prevents a self-consistent source-body SHA and native SHA from accidentally
turning inconsistent Drive name/properties/archive identities into valid
source history. Does not authenticate the vendor or mint a Cache head.
Legacy unpublished archives lacking native SHA keep existing read-only
compatibility; they never gain the new-format verified status.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN = re.compile(r"[1-9][0-9]{5,19}\Z")
SYMBOL = re.compile(r"[A-Z]{3}\Z")
DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
TF = frozenset(("D1", "M5", "M15", "M30", "H1"))
DNSE_SOURCE = "DNSE_OFFICIAL_OPENAPI"
SSI_SOURCE = "SSI_FASTCONNECT_V3_MARKET_DATA"
DNSE_LEGACY = "mst.cloud.dnse_unpublished_source_candidate.v0.1"
DNSE_NATIVE = "mst.cloud.dnse_native_unpublished_candidate.v0.1"
SSI_NATIVE = "mst.cloud.ssi_native_unpublished_candidate.v0.1"

DNSE_FIELDS = frozenset((
    "schema","project","source","symbol","resolution","source_native_tf",
    "from_unix","to_unix","local_receive_utc",
    "issuer_first_known_verified","official_venue_closed_verified",
    "independent_publish_cas_verified","eligible_for_signals",
    "native_canonical_sha256","raw_native",
))
SSI_FIELDS = frozenset((
    "schema","project","source","symbol","resolution","source_native_tf",
    "from_date","to_date","issuer_first_known_verified",
    "official_venue_closed_verified","price_unit_adjusted_basis_verified",
    "independent_publish_cas_verified","eligible_for_signals",
    "native_canonical_sha256","raw_native",
))
OPTIONAL = frozenset(("prior_source_incremental_delta","source_ingress_binding"))


class CandidateIdentityDenied(ValueError):
    """One fixed, non-sensitive code for a forged or inconsistent identity."""


def verify_new_candidate_identity(
    archive: Any, metadata: Any,
) -> bool:
    """Strict provider/symbol/TF/run/file-name/schema/raw-bar proof.

    False = legacy no native SHA, not checked and never publishable.
    True  = new-format identity self-consistent, still UNPUBLISHED.
    """
    if type(archive) is not dict or type(metadata) is not dict:
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_IDENTITY_INVALID")
    props = metadata.get("appProperties")
    if type(props) is not dict:
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_IDENTITY_INVALID")
    if "native_canonical_sha256" not in archive:
        if "source_ingress_binding" in archive:
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_IDENTITY_INVALID")
        return False

    symbol, tf = archive.get("symbol"), archive.get("source_native_tf")
    source, schema = archive.get("source"), archive.get("schema")
    run = props.get("source_run_id")
    if (archive.get("project") != "MST"
            or type(symbol) is not str or SYMBOL.fullmatch(symbol) is None
            or type(tf) is not str or tf not in TF
            or type(run) is not str or RUN.fullmatch(run) is None
            or type(archive.get("native_canonical_sha256")) is not str
            or SHA.fullmatch(archive["native_canonical_sha256"]) is None
            or props.get("source_symbol") != symbol
            or props.get("source_native_tf") != tf
            or props.get("native_canonical_sha256")
                != archive["native_canonical_sha256"]
            or props.get("mst_unpublished") != "true"
            or archive.get("issuer_first_known_verified") is not False
            or archive.get("official_venue_closed_verified") is not False
            or archive.get("independent_publish_cas_verified") is not False
            or archive.get("eligible_for_signals") is not False):
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_IDENTITY_INVALID")

    if source == DNSE_SOURCE:
        if schema == DNSE_LEGACY and tf == "D1":
            namespace = "DNSE_D1"
            props_schema = "dnse_source_candidate_v1"
        elif schema == DNSE_NATIVE:
            namespace = "DNSE_NATIVE_" + tf
            props_schema = "dnse_native_candidate_v1"
        else:
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_SCHEMA_INVALID")
        required = DNSE_FIELDS
        if (type(archive.get("from_unix")) is not int
                or type(archive.get("to_unix")) is not int
                or archive["from_unix"] >= archive["to_unix"]
                or type(archive.get("local_receive_utc")) is not str):
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_WINDOW_INVALID")
    elif source == SSI_SOURCE and schema == SSI_NATIVE:
        namespace = "SSI_NATIVE_" + tf
        props_schema = "ssi_native_candidate_v1"
        required = SSI_FIELDS
        if archive.get("price_unit_adjusted_basis_verified") is not False:
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_SOURCE_CLAIM_INVALID")
        try:
            a,b=archive.get("from_date"),archive.get("to_date")
            if (type(a) is not str or type(b) is not str
                    or date.fromisoformat(a) > date.fromisoformat(b)):
                raise ValueError()
        except (TypeError,ValueError):
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_WINDOW_INVALID") from None
    else:
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_SCHEMA_INVALID")

    expect_name = "MST_UNPUBLISHED_" + namespace + "_" + run + "_1.json"
    if (metadata.get("name") != expect_name
            or props.get("schema") != props_schema
            or set(archive) - OPTIONAL != required
            or not set(archive).issubset(required | OPTIONAL)):
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_FILENAME_OR_FIELDS_INVALID")

    if "prior_source_incremental_delta" in archive:
        link = archive["prior_source_incremental_delta"]
        if (type(link) is not dict
                or type(link.get("prior_private_file_id")) is not str
                or DRIVE_ID.fullmatch(link["prior_private_file_id"]) is None
                or type(link.get("prior_source_sha256")) is not str
                or SHA.fullmatch(link["prior_source_sha256"]) is None
                or type(link.get("delta")) is not dict
                or link.get("eligible_for_signals") is not False
                or link["delta"].get("eligible_for_signals") is not False):
            raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_PRIOR_LINK_INVALID")

    try:
        from scripts.mst_mfx_native_timeframes import provider_resolution
        if source == DNSE_SOURCE:
            from scripts.mst_mfx_style_appowned_pipeline import validate_dnse_native
            if archive["resolution"] != provider_resolution("DNSE",tf):
                raise ValueError()
            validate_dnse_native(
                archive.get("raw_native"),
                archive["from_unix"], archive["to_unix"],timeframe=tf,
            )
        else:
            from scripts.mst_ssi_native_stage import _normal_rows
            if archive["resolution"] != provider_resolution("SSI",tf):
                raise ValueError()
            rows=_normal_rows(
                archive.get("raw_native"),symbol=symbol,tf=tf,
                first=date.fromisoformat(archive["from_date"]),
                last=date.fromisoformat(archive["to_date"]),
            )
            if archive["raw_native"] != [rows[k] for k in sorted(rows)]:
                raise ValueError()
    except Exception:
        raise CandidateIdentityDenied("MST_SOURCE_CANDIDATE_NATIVE_INVALID") from None
    return True
