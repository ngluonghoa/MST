"""MST M4 P0 immutable GitHub OIDC to Google WIF trust PREVIEW only.

No external JWT, Google Cloud IAM, Drive/market data or GitHub settings
operations. A GitHub numeric repository/owner ID reduces namespace
re-registration attacks. All pass/fail logic is local synthetic evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import json
import re

SCHEMA = "mst.m4.wif.github-immutable-identity-trust-policy.synthetic.v1"
STATUS = "GCP_WIF_IMMUTABLE_REPO_WORKFLOW_TRUST_PREVIEW_NO_REAL_BINDING"
OWNER = "ngluonghoa"
REPO = "ngluonghoa/MST"
OWNER_ID = "353049266"
REPO_ID = "1450356304"
REF = "refs/heads/main"
EVENT = "workflow_dispatch"
WORKFLOW_PATH = ".github/workflows/m4-drive-wif-metadata-only-manual.yml"
WORKFLOW_REF = f"{REPO}/{WORKFLOW_PATH}@{REF}"
ISSUER = "https://token.actions.githubusercontent.com"
SOURCE_LOCK_MAIN = "4048f91beaaa3410116d97e35896c8b688384e19"
EXPECTED_CLAIMS = {
    "repository_id": REPO_ID,
    "repository_owner_id": OWNER_ID,
    "repository": REPO,
    "repository_owner": OWNER,
    "ref": REF,
    "event_name": EVENT,
    "workflow_ref": WORKFLOW_REF,
}
ATTRIBUTE_MAPPING = {
    "google.subject": "assertion.sub",
    "attribute.repository_id": "assertion.repository_id",
    "attribute.repository_owner_id": "assertion.repository_owner_id",
    "attribute.workflow_ref": "assertion.workflow_ref",
}
ORDERED_CLAIM_KEYS = tuple(EXPECTED_CLAIMS)


def candidate_attribute_condition() -> str:
    # Every token is constant from a GitHub-retrieved immutable identity
    # or a code-owned workflow path. Do not concatenate caller-supplied claims.
    return " && ".join(
        f"assertion.{name}=='{EXPECTED_CLAIMS[name]}'"
        for name in ORDERED_CLAIM_KEYS
    )


def evaluate_synthetic_claims(claims: object) -> dict:
    """Compare untrusted fake claims; NEVER verify or accept an actual JWT."""
    if type(claims) is not dict:
        raise TypeError("EXACT_FAKE_OIDC_CLAIMS_MAPPING_REQUIRED")
    comparisons={
        k:type(claims.get(k)) is str and claims[k]==expected
        for k,expected in EXPECTED_CLAIMS.items()
    }
    return {
        "synthetic_claims_satisfy_candidate_condition":all(comparisons.values()),
        "checked_fields":len(comparisons),
        "matched_fields":sum(comparisons.values()),
        "externally_signed_oidc_token_verified":False,
        "real_google_sts_token_exchanged":False,
        "drive_access_granted":False,
    }


def example_principalset(project_number: str, pool_id: str) -> str:
    """Format the IAM binding principalSet, but do not grant any IAM role."""
    if type(project_number) is not str or not re.fullmatch(r"[0-9]{6,20}",project_number):
        raise ValueError("REAL_GCP_PROJECT_NUMBER_FORMAT_REQUIRED")
    if type(pool_id) is not str or not re.fullmatch(r"[a-z][a-z0-9-]{3,30}[a-z0-9]",pool_id):
        raise ValueError("CANONICAL_GCP_WIF_POOL_ID_REQUIRED")
    return (
        f"principalSet://iam.googleapis.com/projects/{project_number}"
        f"/locations/global/workloadIdentityPools/{pool_id}"
        f"/attribute.repository_id/{REPO_ID}"
    )


def static_manual_workflow_audit(source: object) -> dict:
    """One-purpose deny-by-default workflow text audit, not GitHub execution."""
    if type(source) is not str:
        raise TypeError("WORKFLOW_TEXT_SOURCE_REQUIRED")
    body=source.replace("\r\n","\n")
    checks={
        "manual_name":body.startswith("name: MST M4 Drive WIF Metadata Preflight - MANUAL READ ONLY"),
        "manual_trigger_only":"on:\n  workflow_dispatch:\n" in body,
        "no_automatic_or_pr_triggers":re.search(r"(?m)^\s+(pull_request|pull_request_target|schedule|push):\s*$",body) is None,
        "contents_read":re.search(r"(?m)^\s+contents:\s+read\s*$",body) is not None,
        "id_token_write":re.search(r"(?m)^\s+id-token:\s+write\s*$",body) is not None,
        "exact_repo":"github.repository == 'ngluonghoa/MST'" in body,
        "exact_main":"github.ref == 'refs/heads/main'" in body,
        "exact_trigger":"github.event_name == 'workflow_dispatch'" in body,
        "uses_google_wif_action":"uses: google-github-actions/auth@v2" in body,
        "uses_provider_variable":"vars.MST_GCP_WIF_PROVIDER" in body,
        "uses_service_account_variable":"vars.MST_GCP_DRIVE_SA_EMAIL" in body,
        "no_json_service_key":"credentials_json:" not in body and "GOOGLE_APPLICATION_CREDENTIALS_JSON" not in body,
        "only_live_readonly":"--mode live-readonly" in body and "drive.files.update" not in body,
        "no_vendor_tools":all(x not in body for x in ("MCP_SSI","MCP_DNSE","MCP_VCBS")),
        "no_cron":"cron:" not in body,
        "no_quote_publisher":"MST_M4_PRODUCTION_CACHE" not in body,
    }
    if not all(checks.values()):
        raise PermissionError("MANUAL_WIF_WORKFLOW_STATIC_GATE_FAIL_CLOSED")
    return {
        "static_workflow_contract_pass":True,
        "conditions":checks,
        "actual_main_workflow_run_completed":False,
        "gcp_federation_provider_authenticity_proven":False,
    }


@dataclass(frozen=True)
class PendingCloudReadiness:
    gcp_pool_and_provider_exists_with_expected_mapping:bool=False
    provider_condition_installed:bool=False
    provider_admin_and_audience_trust_reviewed:bool=False
    exact_service_account_impersonation_binding:bool=False
    github_variables_configured:bool=False
    google_drive_pilot_shared_with_exact_service_account:bool=False
    workflow_approved_and_present_on_protected_main:bool=False
    manual_oidc_sts_and_drive_files_get_success:bool=False
    vendor_cloud_retention_license_proven:bool=False
    production_cache_or_trading_approved:bool=False
    def __post_init__(self):
        if any(type(v) is not bool or v for v in self.__dict__.values()):
            raise PermissionError("LOCAL_REPORT_CANNOT_SELF_ATTEST_GCP_READINESS")


def run_lab(workflow_source: str | None=None)->dict:
    condition=candidate_attribute_condition()
    if set(condition.split(" && ")) != set(
        f"assertion.{name}=='{value}'" for name,value in EXPECTED_CLAIMS.items()
    ):
        raise AssertionError("WIF_CONDITION_CONSTANTS_DRIFT")
    accepted=evaluate_synthetic_claims(dict(EXPECTED_CLAIMS))
    wrong=evaluate_synthetic_claims({**EXPECTED_CLAIMS,"repository_id":"0"})
    if not accepted["synthetic_claims_satisfy_candidate_condition"] or wrong["synthetic_claims_satisfy_candidate_condition"]:
        raise AssertionError("FAKE_OIDC_CLAIM_MATRIX_DRIFT")
    policy=static_manual_workflow_audit(workflow_source) if workflow_source is not None else None
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "github_immutable_owner_id":OWNER_ID,
        "github_immutable_repository_id":REPO_ID,
        "protected_main_baseline_sha_unchanged":SOURCE_LOCK_MAIN,
        "candidate_issuer":ISSUER,
        "candidate_attribute_condition":condition,
        "candidate_attribute_mapping":ATTRIBUTE_MAPPING,
        "candidate_workflow_ref":WORKFLOW_REF,
        "candidate_principalset_requires_actual_gcp_project_number":True,
        "synthetic_accepted_claims":accepted,
        "synthetic_wrong_repo_id_rejection":wrong,
        "static_workflow_audit":policy,
        "cloud_readiness":PendingCloudReadiness().__dict__,
        "actual_google_cloud_or_github_settings_modified":False,
        "real_gcp_oidc_credentials_or_drive_metadata_accessed":False,
        "real_market_data_or_private_quote_cache_retrieved":False,
        "production_cache_and_trading_enabled":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-file",type=Path,
        default=Path(".github/workflows/m4-drive-wif-metadata-only-manual.yml"))
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    receipt=run_lab(args.workflow_file.read_text(encoding="utf-8"))
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":STATUS,"synthetic_claim_matrix":True,
                      "workflow_static_validation":True,
                      "real_google_identity_access":False},sort_keys=True))


if __name__=="__main__":
    main()
