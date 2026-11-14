"""Read an authenticated prior DNSE D1 candidate and plan a source delta.

Imports are deliberately late to avoid circularity with the manual Drive
pipeline. No writer or publisher: the owning staging path handles the single
private upload only after this strictly verified pre-read.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from scripts.mst_d1_incremental_cache_delta import DeltaDenied, plan_d1_delta

MAX_PRIOR_BYTES = 1_500_000


def _snapshot(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    return {
        "schema": "mst.private_connector_d1_cache_capture.v1",
        "project": "MST", "provider": "DNSE", "symbol": symbol,
        "timeframe": "D1", "source_rows_observed": len(payload["t"]),
        "native_source_data": payload,
    }


def plan_prior_dnse_d1_from_private_drive(
    session: Any, env: Mapping[str, str], parent_id: str,
    current_payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Owner-gated read of a single named, private prior source candidate.

    The prior ID is a manual lookup hint, not a trusted capability. Verify
    Drive ownership, exact parent/name census, media checksums and version,
    source identity and D1 shape before comparing. Never publish the result.
    """
    from scripts import mst_mfx_style_appowned_pipeline as cloud

    mode, _ = cloud.guard(env)
    supplied = env.get("MST_DNSE_PREVIOUS_SOURCE_FILE_ID", "")
    if not supplied:
        return None
    if supplied == "auto":
        from scripts.mst_dnse_d1_auto_prior import discover_previous_dnse_d1
        supplied = discover_previous_dnse_d1(session, env, parent_id)
        if supplied is None:
            return None
    if (mode not in (cloud.MODE_STAGE, cloud.MODE_STAGE_NATIVE)
            or env.get("MST_SOURCE_TF", "D1") != "D1"):
        raise cloud.CloudGateDenied("MST_MFX_PREVIOUS_D1_STAGE_ONLY")
    if type(supplied) is not str or not cloud.DRIVE_ID_RE.fullmatch(supplied):
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_ID_INVALID")
    if type(parent_id) is not str or not cloud.DRIVE_ID_RE.fullmatch(parent_id):
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_FOLDER_ID_INVALID")

    try:
        response = session.get(cloud.DRIVE_URL + supplied, params={
            "fields": "id,name,mimeType,parents,trashed,shared,ownedByMe,"
                      "isAppAuthorized,md5Checksum,size,version,appProperties",
        }, timeout=25)
        if response.status_code != 200 or type(response.json()) is not dict:
            raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_METADATA_INVALID")
        info = response.json()
        name = info.get("name")
        if (info.get("id") != supplied or type(name) is not str
                or not re.fullmatch(
                    r"MST_UNPUBLISHED_DNSE_(?:D1|NATIVE_D1)_[1-9][0-9]{5,19}_1\.json", name)
                or info.get("mimeType") != "application/json"
                or info.get("parents") != [parent_id]
                or info.get("trashed") is not False
                or info.get("shared") is not False
                or info.get("ownedByMe") is not True
                or info.get("isAppAuthorized") is not True
                or type(info.get("size")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,6}", info["size"])
                or not 0 < int(info["size"]) <= MAX_PRIOR_BYTES
                or type(info.get("version")) is not str
                or not re.fullmatch(r"[1-9][0-9]{0,19}", info["version"])
                or type(info.get("appProperties")) is not dict
                or info["appProperties"].get("mst_unpublished") != "true"):
            raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_PRIVATE_SCOPE_FAILURE")
        # Re-list the precise prior name; a Drive ID alone is not sufficient.
        if cloud._exact_named_quarantine(session, parent_id, name) != [supplied]:
            raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_CENSUS_CHANGED")
        prior_bytes = None
        for _ in range(2):
            media = session.get(cloud.DRIVE_URL + supplied,
                                params={"alt": "media"}, timeout=35,
                                allow_redirects=False)
            if (media.status_code != 200 or type(media.content) is not bytes
                    or len(media.content) != int(info["size"])):
                raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_READBACK_FAILED")
            if prior_bytes is not None and media.content != prior_bytes:
                raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_MUTATED")
            prior_bytes = media.content
            if cloud._quarantine_metadata(
                session, supplied, parent_id, name, prior_bytes
            ) != info["version"]:
                raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_VERSION_CHANGED")
        if (hashlib.sha256(prior_bytes).hexdigest()
                != info["appProperties"].get("source_sha256")):
            raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_DIGEST_MISMATCH")
        prior = json.loads(prior_bytes)
    except cloud.CloudGateDenied:
        raise
    except Exception:
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_READ_FAILED") from None

    if (type(prior) is not dict
            or prior.get("schema") not in (
                "mst.cloud.dnse_unpublished_source_candidate.v0.1",
                "mst.cloud.dnse_native_unpublished_candidate.v0.1")
            or prior.get("project") != "MST"
            or prior.get("source") != "DNSE_OFFICIAL_OPENAPI"
            or prior.get("symbol") != env["MST_DNSE_SYMBOL"]
            or prior.get("source_native_tf") != "D1"
            or prior.get("resolution") != "1D"
            or prior.get("issuer_first_known_verified") is not False
            or prior.get("official_venue_closed_verified") is not False
            or prior.get("independent_publish_cas_verified") is not False
            or prior.get("eligible_for_signals") is not False
            or type(prior.get("from_unix")) is not int
            or type(prior.get("to_unix")) is not int):
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_IDENTITY_MISMATCH")
    try:
        cloud.validate_dnse_native(
            prior.get("raw_native"), prior["from_unix"], prior["to_unix"],
            timeframe="D1",
        )
        delta = plan_d1_delta(
            _snapshot(prior["raw_native"], prior["symbol"]),
            _snapshot(current_payload, env["MST_DNSE_SYMBOL"]),
            provider="DNSE", symbol=env["MST_DNSE_SYMBOL"],
        )
    except (cloud.CloudGateDenied, DeltaDenied, KeyError, TypeError, ValueError):
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_DELTA_INVALID") from None

    # Without overlap we cannot prove continuity; use separate first captures.
    if delta["unchanged_overlap"] + len(delta["revised"]) < 1:
        raise cloud.CloudGateDenied("MST_MFX_PRIOR_SOURCE_NO_OVERLAP")
    return {
        "schema": "mst.cloud.dnse_d1_prior_source_delta_candidate.v0.1",
        "prior_private_file_id": supplied,
        "prior_source_sha256": hashlib.sha256(prior_bytes).hexdigest(),
        "delta": delta,
        "prior_and_current_issuer_closed_verified": False,
        "eligible_for_signals": False,
    }
