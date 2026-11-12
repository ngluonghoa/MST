# MST M4 — Effective Root / Admin Bypass / Drive Custody Threat Review (Option A)

QA ID: MST-M4-OPTION-A-EFFECTIVE-AUTHORITY-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: **PASS for read-only fail-closed threat-review validation only; PRODUCTION NO-GO.**
Work branch: existing Draft PR #8 (never merge automatically).
Architecture: GitHub + Google Drive ONLY (Option A). This scope is selected, NOT a signer/ACL/administrator-privilege deployment approval.

## 1. Scope and unchanged Swing parity

Original pinned Swing upstream cd90c1babae8912db31490ad614fc2ad2f868042; protected MST main 4048f91beaaa3410116d97e35896c8b688384e19 with exact source tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. All original 63 V1 source modules and eight earlier V2 source modules unchanged. Only GitHub Draft PR #8 receives additive review files (JSON, Python, 41 tests, read-only workflow and this QA report).

No Mac, MOCHI, local machine, new Cloud vendor, licensed real OHLCV, physical Google Drive market cache, signer/secret, account permission changes, witness ref/ruleset creation, main merge, release or trade.

## 2. Actual connected metadata, each trust scope distinguished

- Connected GitHub repository metadata gives current connected caller an **admin permission** on public ngluonghoa/MST. This alone does NOT enumerate effective administrator/bypass paths for other accounts or prove an independently controlled root. Do not make public repo identity assertions from it.
- Actual GitHub read-only Actions token REST observes active default-branch ruleset 26801439, main pin 4048f91..., PR + three Foundation job checks, zero required positive approving reviews, exact proposed witness refs/heads/mst/m4-witness/v1 absent (404). CI token cannot read complete bypass actor inventory; classic branch-protection endpoint can return 403. **Unknown != empty or safe.**
- Connected Google Drive API read-only metadata (2026-11-10) on MST root + four project folders shows shared=false, one visible owner permission role per folder, but never proves independent signer custody, physical byte immutability or effective admin independence. This is a separate Drive connector observation; the hosted GitHub workflow does **not** authenticate to Drive and re-read these permissions.
- Existing unapproved Option A proposal: eight designed roles and 25 required pairwise distinct-principal constraints, zero real independently bound identities. Six owner decisions OA01–OA06 and all eight G01–G08 security gates remain OPEN.
- A03 synthetic dual-reader/two-writer previously demonstrated isolated split-brain same-generation alternatives and reset-reader rollback: a local writer label and SHA chain cannot prove a remote two-auth CAS or nonresettable independent floor.

## 3. Twelve owner-root threats recorded — ALL UNVERIFIED/BLOCKED

| ID | Threat being reviewed | Next independently required proof |
| --- | --- | --- |
| T01 | A root administrator changes the witness ruleset | Separate effective admin/bypass inventory |
| T02 | Witness branch is deleted/recreated or rolled backward | Owner-approved protected, durable monotonic head |
| T03 | Root signer and writer share a controller | Independent private account/key custody |
| T04 | Root admin rewinds signer epoch or genesis | External registry antirollback and recovery checks |
| T05 | Google Drive owner replaces/deletes accepted bytes | Independent custody, rights and physical-byte readback |
| T06 | Two writer aliases use the same credential | Two genuinely distinct restricted principals |
| T07 | Untrusted PR workflow obtains privileged writer key | PR CI isolation from signer/writer secrets |
| T08 | Missing bypass metadata treated as an empty list | Independent owner/admin ruleset bypass readback |
| T09 | Same controller self-signs policy and signer root | Separate owner approval and revocation controller |
| T10 | Fresh reader accepts older but consistent G1 | Highest externally anchored accepted floor |
| T11 | GitHub ref/Drive bytes diverge across failure | Two-service read barrier and quarantine recovery |
| T12 | GitHub Actions token view mistaken for global root | Multiple authenticated evidence scopes and provenance |

These are **threat-model scenarios and control requirements**, not claims that any specific person has exploited GitHub or Google Drive. T10 is directly demonstrated with synthetic fixtures; others cannot be closed without separately authorized owner/security evidence.

## 4. Additive implementation and tests

- docs/MST_M4_OPTION_A_EFFECTIVE_AUTHORITY_THREAT_REGISTER_20261110.json — schema mst.m4.option-a.effective-authority-threat-register.unattested.v1, exact 12 scenario/control/owner mappings, identity and credential fields forbidden, production flags false.
- scripts/m4_option_a_effective_authority_threat_preflight.py — reuse the existing G01–G03 owner bridge, eight-role/25-pair validation, connected Drive historical snapshot and GitHub live custody+readiness outputs. No new privilege model. Deny drift, missing controls, fabricated G01/G02/G03 grants, self-approvals, hidden bypass promotion, modified source lock and expanded Cloud scope.
- tests/test_m4_option_a_effective_authority_threat_preflight.py — **41 tests**. API-shaped unit fixtures are mocked and NOT live evidence; hosted CI separately retrieves real token-limited GitHub REST status for final cross-check.
- .github/workflows/m4-option-a-effective-root-acl-review-readonly.yml — same-repo PR8, GitHub-hosted Python3.12, contents:read only; run 41 tests, invoke existing live GitHub read-only custody/readiness commands, validate all 12 threats remain blocked, upload 14-day nonauthoritative review JSON. No Google Drive production API calls, real secret, ACL or ref mutations.

**Verified code-and-workflow HEAD:** 036e95aa3800c0bf7cb8bf744e904727ca2b5317.

- [Dedicated effective authority / ACL workflow run 42757159557](https://github.com/ngluonghoa/MST/actions/runs/42757159557): **SUCCESS, 41/41 tests**, token-limited real GitHub custody+readiness readback; verdict TWELVE_ROOT_AND_IDENTITY_THREATS_REVIEWED_ALL_OPEN_PRODUCTION_NO_GO.
- [Foundation CI run 42757159244](https://github.com/ngluonghoa/MST/actions/runs/42757159244): **SUCCESS 3/3 jobs**, Python 3.11 **2354/2354**, Python3.12 **2354/2354**, engineering source63/63 with H2/H3/lint/wheel checks.
- All **20/20 workflows completed SUCCESS** at exact code/workflow HEAD. This QA file is a subsequent documentation commit, so its exact report-containing HEAD requires another CI readback.

## 5. Owner decisions still required (no implied signoff)

OA01: real distinct controller/account and root-admin/bypass graph (G01).  
OA02: signer root, protected witness/genesis/floor and owner-controlled recovery (G01/G02).  
OA03: two independently authenticated publishers, independent read-only verifier and actual server one-winner/loser CAS (G03).  
OA04: licensed Drive data source/retention, physical byte custody, two-service crash/revocation (G04/G05/G06).  
OA05: accept/reject/mitigate shared GitHub+Drive platform-root threat model without silently downgrading invariant G02.  
OA06: A02 **0/63 formal owner dispositions**, A03 ABI, M3/M4, G07/G08 final release approval.

All stay OPEN. No new owner principals or private names are written to this public repository; full effective admin identities must be collected privately and independently verified by the owner. If Option A cannot meet the accepted compromise model, production remains NO-GO, rather than treating SHA signatures or a read-only CI green status as immutable custody.

## 6. Next safe checkpoint

Owner-facing PRIVATE, READ-ONLY evidence intake plan for independently authenticated GitHub and Google Drive administrators, separate account/service identity proof, bypass/recovery graph and residual common-root decision. Do not ask users to put secrets or personal identity proofs in public GitHub; do not enable owner/writer privileges, create witnesses, merge PR or write physical vendor cache until specific independent approvals are received.

Current A02/A03/G01–G08/M3/M4/M5/M8 production or trading gates remain **OPEN/BLOCKED**.
