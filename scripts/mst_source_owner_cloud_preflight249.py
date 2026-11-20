#!/usr/bin/env python3
"""§249 owner-only GitHub Actions SOURCE CONFIG preflight. ZERO network/write.

Presence of a secret and a literal 'true' owner declaration DOES NOT validate
the vendor API key, vendor storage licence, first-known bars, protected signer,
published market cache, signed CAS, or trading eligibility.
Only fixed non-sensitive codes go to public GitHub Actions logs.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

OWNER_CONTEXT = {
    "GITHUB_REPOSITORY": "ngluonghoa/MST",
    "GITHUB_REPOSITORY_ID": "1450356304",
    "GITHUB_REPOSITORY_OWNER_ID": "353049266",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_WORKFLOW_REF": (
        "ngluonghoa/MST/.github/workflows/"
        "mst-source-owner-config-preflight-manual.yml@refs/heads/main"
    ),
    "GITHUB_RUN_ATTEMPT": "1",
    "MST_SOURCE_PREFLIGHT_CONFIRM": "CHECK_ONLY",
}
SSI_KEYS = ("MST_SSI_API_KEY", "MST_SSI_API_SECRET")
DNSE_KEYS = ("MST_DNSE_API_KEY", "MST_DNSE_API_SECRET")
GDRIVE_KEYS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
SSI_RIGHTS = (
    "MST_SSI_READONLY_OWNER_ACCEPTED",
    "MST_SSI_SOURCE_RIGHTS_CONFIRMED",
)
DNSE_RIGHTS = (
    "MST_DNSE_READONLY_OWNER_ACCEPTED",
    "MST_DNSE_SOURCE_RIGHTS_CONFIRMED",
)


class PreflightDenied(ValueError):
    """Only static error codes; never repr/str a credential or OS environment."""


def _present(env: Mapping[str, str], names: tuple[str, ...]) -> bool:
    return all(type(env.get(key)) is str and bool(env[key].strip())
               for key in names)


def _declared(env: Mapping[str, str], names: tuple[str, ...]) -> bool:
    return all(env.get(key) == "true" for key in names)


def _gate(
    env: Mapping[str, str], *,
    rights: tuple[str, ...],
    secrets: tuple[str, ...],
    special: tuple[tuple[str, bool, str], ...] = (),
) -> dict[str, Any]:
    """Report names of missing categories, never values nor individual keys."""
    errors: list[str] = []
    if not _declared(env, rights):
        errors.append("OWNER_DECLARATION_NOT_TRUE")
    if not _present(env, secrets):
        errors.append("SECRET_GROUP_NOT_PROVISIONED")
    for name, accepted, code in special:
        if (env.get(name) == "true") is not accepted:
            errors.append(code)
    # These are purely syntactic, never real provider/Drive authorization.
    return {
        "configuration_status": "DECLARED_ONLY_UNVERIFIED" if not errors else "HOLD",
        "fixed_block_reasons": errors,
        "credentials_validated_with_provider": False,
        "vendor_rights_independently_attested": False,
        "eligible_for_real_data_storage": False,
        "eligible_for_cache_publication": False,
    }


def source_owner_preflight(env: Mapping[str, str]) -> dict[str, Any]:
    """Main-only, first-attempt, zero network, immutable verdict for this run."""
    if (not isinstance(env, Mapping)
        or any(env.get(k) != v for k, v in OWNER_CONTEXT.items())
        or type(env.get("GITHUB_RUN_ID")) is not str
        or re.fullmatch(r"[1-9][0-9]{5,19}", env["GITHUB_RUN_ID"]) is None
    ):
        raise PreflightDenied("MST_249_PROTECTED_MANUAL_FIRST_ATTEMPT_REQUIRED")
    ssi = _gate(env, rights=SSI_RIGHTS, secrets=SSI_KEYS)
    dnse = _gate(env, rights=DNSE_RIGHTS, secrets=DNSE_KEYS)
    chunks = _gate(
        env, rights=SSI_RIGHTS + (
            "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED",
            "MST_SOURCE_RETENTION_RIGHTS_CONFIRMED",
        ), secrets=SSI_KEYS + GDRIVE_KEYS,
        special=((
            "MST_OAUTH_BOOTSTRAP_ACCEPTED", False,
            "STANDALONE_OAUTH_BOOTSTRAP_FLAG_MUST_BE_DISABLED",
        ),),
    )
    manifest = _gate(
        env, rights=SSI_RIGHTS + (
            "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED",
            "MST_SOURCE_RETENTION_RIGHTS_CONFIRMED",
            "MST_PRIVATE_MANIFEST_WRITE_ACCEPTED",
        ), secrets=SSI_KEYS + GDRIVE_KEYS,
        special=((
            "MST_OAUTH_BOOTSTRAP_ACCEPTED", False,
            "STANDALONE_OAUTH_BOOTSTRAP_FLAG_MUST_BE_DISABLED",
        ),),
    )
    return {
        "schema": "mst.cloud.owner_source_config_preflight.v0.1",
        "mode": "CONFIGURATION_PRESENCE_ONLY_ZERO_HTTP",
        "main_first_attempt_guard": "PASSED",
        "ssi_native_readonly": ssi,
        "dnse_native_readonly": dnse,
        "ssi_private_chunk_stage": chunks,
        "ssi_private_unpublished_manifest_stage": manifest,
        "market_source_http_attempted": False,
        "google_drive_http_attempted": False,
        "google_oauth_refreshed": False,
        "github_highwater_private_repo_checked": False,
        "independent_signed_monotone_cas_verified": False,
        "market_cache_head_published": False,
        "source_rights_independently_attested": False,
        "signals_or_trades_eligible": False,
    }


def main() -> None:
    result = source_owner_preflight(os.environ)
    # Fixed static codes only: absolutely no printing environment/secrets.
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except PreflightDenied as exc:
        raise SystemExit(str(exc)) from None
