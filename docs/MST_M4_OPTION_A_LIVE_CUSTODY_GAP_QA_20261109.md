# MST M4 — Option A live read-only GitHub + Google Drive custody inventory

**QA-ID:** MST-M4-OPTION-A-ACL-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**Verdict:** **REAL METADATA OBSERVED; G01/G02/G03/G05 INDEPENDENT CUSTODY NOT PROVEN. M4 REMAINS BLOCKED.**  
**Selected scope:** Option A GitHub + Google Drive ONLY, as explicitly authorized for architecture. This QA reads actual remote metadata and performs NO privileged writes, no new Cloud service, no source or trading access.

## 1. Fixed source, branch and privileges

- Source lock Swing Trading 1.8 commit `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. Original 63 inherited V1 source files and existing V2 modules unchanged.
- Work is confined to **Draft PR #8**, unmerged. No Mac/MOCHI/local project execution. No signer key issued, production branch/ruleset modified, privileged GitHub actor created, GitHub secret uploaded, actual Google Drive candle cache promoted or vendor OHLCV ingested.
- Added `scripts/m4_option_a_live_custody_audit.py`, `tests/test_m4_option_a_live_custody_audit.py` (**33 Python tests**), `docs/MST_M4_OPTION_A_DRIVE_ACL_OBSERVATION_20261109.json` (sanitized, no owner email/name) and `.github/workflows/m4-option-a-live-custody-readonly.yml`.
- This new GitHub-hosted workflow reads **live GitHub REST** under its **`contents: read`** token. Google Drive ACL observations were acquired separately via the connected Drive metadata API **at the time of this QA** and saved as an explicitly historical metadata snapshot. GitHub Actions did **not** authenticate to or inspect live Google Drive in this workflow. Do not confuse the two evidence origins.

## 2. GitHub actual remote ruleset / custody findings

A separate read-only GitHub connector observation showed:
- Repository `ngluonghoa/MST` is **public** with default branch `main`; main HEAD is pinned and GitHub shows `main.protected=true`.
- Actual active repository ruleset **`MST - Protect Main`**, GitHub rule ID `26801439`, targets `~DEFAULT_BRANCH`. Its visible rules are `deletion`, `non_fast_forward`, `pull_request`, and `required_status_checks`. It requires 3 foundation CI job contexts: `unittest (3.11)`, `unittest (3.12)` and `Contract, source-boundary and wheel checks`.
- The `pull_request` rule has `required_approving_review_count=0`, so **a pull request is required, but no approving review is required by this rule**. The inspected rule does **not** include `required_signatures`; therefore no main-branch signed-commit requirement is demonstrated by this specific rule.
- For the connector's read identity, the main ruleset's `bypass_actors=[]` and `current_user_can_bypass=never` were visible. **That is not proof that no root administrator could later change, disable or replace policy.** It is also **not** a private M4 witness policy.
- Exact witness `refs/heads/mst/m4-witness/v1` returns GitHub HTTP 404 / absent. Existing test-only `mst/m4-witness-test-only/*` branches are NOT authoritative witness.
- The legacy `/branches/main/protection` endpoint returned **HTTP 403 Resource not accessible by integration** to the connector. This may be a token permission boundary; it is *not evidence that main is unprotected*. The separate active ruleset/branch metadata do support current default-branch protection.

**Independent verification on actual GitHub Actions PR token:**
[Option A live-ACL hosted run #42620470380](https://github.com/ngluonghoa/MST/actions/runs/42620470380) SUCCESS. Its direct REST JSON has `main_pin_verified=true`, `main_ruleset_active=true`, `main_required_approval_count=0`, `all_three_foundation_checks_required=true`, `main_requires_signed_commits_in_visible_rule=false`, `witness_ref_exists_in_readback=false`, `classic_branch_protection_endpoint_status=INACCESSIBLE_TO_TOKEN_403`, `current_token_can_bypass=never`.

**Token visibility caveat:** the GitHub Actions token reported `main_bypass_actor_list_visible=false`, whereas the connected GitHub app observed an empty list for its different identity. This illustrates why **reader-specific visibility must not be promoted to independent authority**: there is no globally authenticated bypass inventory available from these results. No actual independent admin/writer ACL graph or root-bypass safety test was performed.

## 3. Google Drive real metadata, safely reported

Actual connected Google Drive `files.get` metadata on these **five MST folders**:
1. MST project root.
2. `00_SOURCE_BASELINE_SNAPSHOT — READ ONLY` (name, not verified enforced immutability).
3. `01_MST_CANONICAL_DESIGN_AND_HANDOFF`.
4. `02_QA_RELEASE_EVIDENCE`.
5. `03_CACHE_STAGING_SYNTHETIC_ONLY`.

Each returned `shared=false`, full visible `permissions` containing **one `role=owner` user**, permission metadata available, and `canShare=true` for the querying account. The public repository contains only sanitized **counts/roles**, not individual owner's email or display name. Parent and child folder metadata cannot prove account isolation, owner key custody, service identity, true immutability or independent two-actor approval.

The staging area presently contains subfolders `00_MANIFESTS_AND_INDEX__STAGING`, `01_IMMUTABLE_CHUNKS__STAGING`, `02_AUDIT_AND_QUARANTINE__STAGING` — **staging structure only**, not proof of physical licensed vendor cache or a protected external rollback floor.

These permission observations were made by the **Google Drive connector**, NOT by the GitHub-hosted workflow. They can change later and have no non-repudiation signature. The read-only GitHub workflow validated their schema and explicitly reported `drive_observation_is_historical_not_live_ci=true`.

## 4. Test and workflow evidence

**Code/workflow HEAD before this report:** `cd8e7223c7f0cb9d490bba9a9f7493b07499f2b6`.

- [Live GitHub + historical Drive ACL workflow #42620470380](https://github.com/ngluonghoa/MST/actions/runs/42620470380) SUCCESS: `OPTION_A_READONLY_METADATA_OBSERVED_REAL_CUSTODY_BLOCKED`. Temporary GitHub Actions [artifact 13676306047](https://github.com/ngluonghoa/MST/actions/runs/42620470380/artifacts/13676306047), 14-day retention, NOT a protected floor/attestation.
- [Foundation CI #42620470657](https://github.com/ngluonghoa/MST/actions/runs/42620470657): exact code-HEAD CI (verify in final report/readback for status and test counts).
- [Option A selection-only #42620470308](https://github.com/ngluonghoa/MST/actions/runs/42620470308), [remote ref #42620470300](https://github.com/ngluonghoa/MST/actions/runs/42620470300), [reader denial #42620470409](https://github.com/ngluonghoa/MST/actions/runs/42620470409), [untrusted cross-run registry #42620470382](https://github.com/ngluonghoa/MST/actions/runs/42620470382), [untrusted journal #42620470310](https://github.com/ngluonghoa/MST/actions/runs/42620470310): all are **test-only** checkpoints and do not authorize production.
- 33 new tests assert precise rule/PR/CI/signed-commit/bypass/403 visibility, unavailable witness, unknown admin authority, and sanity of five historical Drive ACL records. No claim is made that this is a two-account authenticated CAS or real Drive data proof.

## 5. Concrete Option A gaps and priority

| ID | Concrete gap from real observations | Current | Next proof |
| --- | --- | --- | --- |
| A-ACL-01 | Current main PR ruleset requires **0 approving reviewers** | OBSERVED | Owner selects authorized reviewers/required review count and verifies changed settings, **separate approval** |
| A-ACL-02 | Main inspected ruleset has no signed-commit requirement | OBSERVED | Owner chooses key-custody and enforcement; this main gap does NOT mean protected M4 signer is configured |
| A-ACL-03 | Witness M4 actual branch and corresponding owner ruleset do not exist | CONFIRMED MISSING | Owner-approved separate witness custody and ref/ruleset bootstrap, with independent actor and bypass test |
| A-ACL-04 | Branch protection classic API 403 / Actions bypass list not visible | VISIBILITY GAP | Authorized administrative readback from a distinct actor; do not equate 403 with absence |
| A-ACL-05 | 5 Drive folders show only one visible owner role per item | OBSERVED IN CONNECTOR | Owner reviews sharing/IAM model and independent reader/writer custody; no public identity details |
| A-ACL-06 | Drive staging folders exist but no certified immutable licensed vendor data | OPEN | Provider license, physical Drive byte/SHA, cross-account readback, correction and retention |
| A-ACL-07 | Monotonic G02 floor/admin reset/root bypass and two-real-writer CAS not proven | OPEN | Independently governed adversarial test using only GitHub+Drive, no downgrade/rollback accepted |
| A-ACL-08 | Source parity/ABI/release policy still owner-gated | OPEN | A02 63 owner module dispositions, A03 opt-in ABI, M3/M4/M8 signoffs |

**Recommended engineering order under Option A:** first owner-reviewed identity/admin/bypass inventory and witness reference policy design; then authorized source-agnostic GitHub witness head/2-actor test; only after provider rights are clear perform physical Drive chunk readbacks and two-service crash/rollback experiments. If non-resettable floor cannot be proved against root admin using only GitHub+Drive, keep G01/G02 blocked and present the limitation; **do not silently introduce Cloud KMS/Firestore or weaken requirements**.

**Important:** Any approval to develop within GitHub+Drive does not approve **changing the real main ruleset**, making a separate privileged witness repository, issuing real signer keys, using vendor OHLCV or merging PR #8. Those changes require discrete owner consent. There are no credential or permission changes from this QA.

## 6. Production admission status

`MAIN_BASELINE_PROTECTED_BY_ACTIVE_RULESET=OBSERVED`; `MAIN_APPROVALS_REQUIRED=0`; `MAIN_SIGNED_COMMITS_IN_RULESET=FALSE`; `M4_INDEPENDENT_WITNESS=ABSENT`; `GITHUB_CLASSIC_PROTECTION_ACCESS=403`; `GITHUB_CI_BYPASS_VISIBILITY=UNKNOWN`; `DRIVE_FOLDERS_OBSERVED=5_SINGLE_VISIBLE_OWNER_PER_FOLDER`; `G01_OWNER_SIGNER_ROOT=UNATTESTED`; `G02_DURABLE_NONRESETTABLE_FLOOR=UNATTESTED`; `G03_TWO_AUTHENTICATED_WRITER_CAS=UNPROVEN`; `G04_LICENSED_VENDOR_SOURCE=UNVERIFIED`; `G05_ACTUAL_DRIVE_DATA=UNVERIFIED`; `G06_GLOBAL_REVOKE=UNPROVEN`; `G07_INDEPENDENT_EVIDENCE=UNPROVEN`; `G08_OWNER_RELEASE=OPEN`; `M5/M8_TRADING=BLOCKED`.

All eight SIGNED-G01..G08 in [Issue #16](https://github.com/ngluonghoa/MST/issues/16), owner witness [#15](https://github.com/ngluonghoa/MST/issues/15) and subsidiary [#13](https://github.com/ngluonghoa/MST/issues/13), [#14](https://github.com/ngluonghoa/MST/issues/14), [#10](https://github.com/ngluonghoa/MST/issues/10), [#9](https://github.com/ngluonghoa/MST/issues/9), [#4](https://github.com/ngluonghoa/MST/issues/4), [#6](https://github.com/ngluonghoa/MST/issues/6) stay OPEN.
