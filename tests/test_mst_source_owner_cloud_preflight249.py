"""§249 offline no-network owner configuration preflight QA."""
from __future__ import annotations

from pathlib import Path
import json
import unittest
from scripts import mst_source_owner_cloud_preflight249 as m

SENTINEL = "MST_PRIVATE_FAKE_SECRET_DO_NOT_OUTPUT"


def good():
    e = {
        **m.OWNER_CONTEXT,
        "GITHUB_RUN_ID": "44799999999",
        "MST_SSI_READONLY_OWNER_ACCEPTED": "true",
        "MST_SSI_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_DNSE_READONLY_OWNER_ACCEPTED": "true",
        "MST_DNSE_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED": "true",
        "MST_SOURCE_RETENTION_RIGHTS_CONFIRMED": "true",
        "MST_PRIVATE_MANIFEST_WRITE_ACCEPTED": "true",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED": "false",
        "MST_HIGHWATER_CUSTODY_REPO": "owner/private-secret",
    }
    for name in m.SSI_KEYS + m.DNSE_KEYS + m.GDRIVE_KEYS:
        e[name] = SENTINEL + name
    return e


class SourceOwnerPreflight249(unittest.TestCase):
    def test_all_present_means_only_declared_not_approved(self):
        r = m.source_owner_preflight(good())
        self.assertEqual(r["main_first_attempt_guard"], "PASSED")
        for k in ("ssi_native_readonly", "dnse_native_readonly",
                  "ssi_private_chunk_stage",
                  "ssi_private_unpublished_manifest_stage"):
            self.assertEqual(r[k]["configuration_status"], "DECLARED_ONLY_UNVERIFIED")
            self.assertEqual(r[k]["fixed_block_reasons"], [])
            self.assertFalse(r[k]["credentials_validated_with_provider"])
            self.assertFalse(r[k]["eligible_for_real_data_storage"])
        for key in ("google_drive_http_attempted", "market_source_http_attempted",
                    "github_highwater_private_repo_checked",
                    "market_cache_head_published",
                    "signals_or_trades_eligible",
                    "independent_signed_monotone_cas_verified"):
            self.assertIs(r[key], False)
        receipt = json.dumps(r)
        for private in (SENTINEL, "owner/private-secret", "44799999999",
                        "MST_SSI_API_KEY"):
            self.assertNotIn(private, receipt)

    def test_missing_ssi_keys_but_dnse_still_syntactically_ready(self):
        e=good()
        for key in m.SSI_KEYS:
            e[key] = ""
        r=m.source_owner_preflight(e)
        self.assertEqual(r["ssi_native_readonly"]["configuration_status"], "HOLD")
        self.assertIn("SECRET_GROUP_NOT_PROVISIONED",
                      r["ssi_native_readonly"]["fixed_block_reasons"])
        self.assertEqual(r["dnse_native_readonly"]["configuration_status"],
                         "DECLARED_ONLY_UNVERIFIED")
        self.assertEqual(r["ssi_private_chunk_stage"]["configuration_status"], "HOLD")

    def test_missing_gdrive_only_blocks_staging(self):
        e=good()
        e["MST_GDRIVE_OAUTH_REFRESH_TOKEN"]=""
        r=m.source_owner_preflight(e)
        self.assertEqual(r["ssi_native_readonly"]["configuration_status"],
                         "DECLARED_ONLY_UNVERIFIED")
        self.assertEqual(r["ssi_private_chunk_stage"]["configuration_status"], "HOLD")
        self.assertEqual(r["ssi_private_unpublished_manifest_stage"]["configuration_status"], "HOLD")

    def test_owner_rights_and_storage_separation(self):
        for key in ("MST_SSI_SOURCE_RIGHTS_CONFIRMED",
                    "MST_DNSE_SOURCE_RIGHTS_CONFIRMED",
                    "MST_SOURCE_RETENTION_RIGHTS_CONFIRMED",
                    "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED"):
            e=good()
            e[key]="false"
            with self.subTest(key=key):
                r=m.source_owner_preflight(e)
                if key.startswith("MST_SSI"):
                    self.assertEqual(r["ssi_native_readonly"]["configuration_status"], "HOLD")
                if key.startswith("MST_DNSE"):
                    self.assertEqual(r["dnse_native_readonly"]["configuration_status"], "HOLD")
                if key in ("MST_SOURCE_RETENTION_RIGHTS_CONFIRMED",
                           "MST_PRIVATE_CHUNKS_WRITE_ACCEPTED"):
                    self.assertEqual(r["ssi_native_readonly"]["configuration_status"],
                                     "DECLARED_ONLY_UNVERIFIED")
                expected = ("DECLARED_ONLY_UNVERIFIED"
                            if key == "MST_DNSE_SOURCE_RIGHTS_CONFIRMED"
                            else "HOLD")
                self.assertEqual(r["ssi_private_chunk_stage"]["configuration_status"], expected)

    def test_optional_manifest_write_gate_not_inherited(self):
        e=good()
        e["MST_PRIVATE_MANIFEST_WRITE_ACCEPTED"]="false"
        r=m.source_owner_preflight(e)
        self.assertEqual(r["ssi_private_chunk_stage"]["configuration_status"],
                         "DECLARED_ONLY_UNVERIFIED")
        self.assertEqual(r["ssi_private_unpublished_manifest_stage"]["configuration_status"],
                         "HOLD")

    def test_bootstrap_write_switch_stale_prevents_source_stage_only(self):
        e=good()
        e["MST_OAUTH_BOOTSTRAP_ACCEPTED"]="true"
        r=m.source_owner_preflight(e)
        self.assertEqual(r["ssi_native_readonly"]["configuration_status"],
                         "DECLARED_ONLY_UNVERIFIED")
        for key in ("ssi_private_chunk_stage",
                    "ssi_private_unpublished_manifest_stage"):
            self.assertIn("STANDALONE_OAUTH_BOOTSTRAP_FLAG_MUST_BE_DISABLED",
                          r[key]["fixed_block_reasons"])

    def test_strict_main_first_attempt_with_run_id(self):
        for key,val in (
            ("GITHUB_REPOSITORY", "attacker/MST"),
            ("GITHUB_REPOSITORY_ID", "1"),
            ("GITHUB_REPOSITORY_OWNER_ID", "2"),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_WORKFLOW_REF", "invalid"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("MST_SOURCE_PREFLIGHT_CONFIRM", "NO"),
            ("GITHUB_RUN_ID", "0"),
        ):
            e=good()
            e[key]=val
            with self.subTest(key=key), self.assertRaisesRegex(
                m.PreflightDenied, "^MST_249_PROTECTED_MANUAL_FIRST_ATTEMPT_REQUIRED$"
            ):
                m.source_owner_preflight(e)

    def test_no_secret_values_exposed_on_failure(self):
        e=good()
        e["MST_SSI_API_SECRET"]=SENTINEL+"\nBearer FAKE"
        e["MST_DNSE_API_SECRET"]=""
        e["MST_SOURCE_RETENTION_RIGHTS_CONFIRMED"]="false"
        result=json.dumps(m.source_owner_preflight(e))
        for secret in (SENTINEL, "Bearer", "owner/private-secret",
                       "MST_SSI_API_SECRET"):
            self.assertNotIn(secret, result)

    def test_workflow_is_manual_only_and_does_not_contact_provider(self):
        workflow=(Path(__file__).resolve().parents[1] /
                  ".github/workflows/mst-source-owner-config-preflight-manual.yml").read_text()
        module=(Path(__file__).resolve().parents[1] /
                "scripts/mst_source_owner_cloud_preflight249.py").read_text()
        for needed in ("workflow_dispatch:", 'default: "NO"', "CHECK_ONLY",
                       "persist-credentials: false", "permissions:\n  contents: read",
                       "secrets.MST_SSI_API_KEY",
                       "secrets.MST_DNSE_API_SECRET",
                       "python -m scripts.mst_source_owner_cloud_preflight249"):
            self.assertIn(needed,workflow)
        for forbidden in ("schedule:", "pull_request:", "pull_request_target:",
                          "push:", "curl ", "wget ", "pip install"):
            self.assertNotIn(forbidden,workflow)
        for forbidden in ("requests", "urllib", "socket", "http.client",
                          "subprocess", "session.post", "session.get",
                          "open(", "write(", "Ed25519PrivateKey"):
            self.assertNotIn(forbidden,module)


if __name__=="__main__":
    unittest.main()
