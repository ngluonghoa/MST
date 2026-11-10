# MST M4 — Option A G01–G03 Owner Custody / Root / Floor / CAS Decision

**QA ID:** MST-M4-OPTION-A-G01-G03-OWNER-BRIDGE-001
**Date:** 2026-11-10, Asia/Ho_Chi_Minh
**Verdict:** **36/36 synthetic negative tests PASS, 19/19 exact code-HEAD GitHub workflows PASS. All owner/security gates OPEN; production NO-GO.**
**Surface:** https://github.com/ngluonghoa/MST/pull/8 — Draft, unmerged.

## 1. Scope and source lock

- User selected **Option A: GitHub + Google Drive ONLY**, NOT an approval to issue keys, change ACL/rulesets, initialize a witness or release.
- Source-locked Swing Trading upstream cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19; original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e identical. All 63 original V1 and eight existing V2 modules unchanged.
- This is additive GitHub-hosted code/tests/QA and connected read-only Drive metadata, **no Mac/MOCHI/local, no third Cloud, no real licensed provider market data, no Drive production cache, no signer/secret, no protected ref/ACL/ruleset write, no merge, release or trade**.

## 2. Reconciled actual observations and limitations

| Item | Observed and validated | Critical limit |
| --- | --- | --- |
| GitHub main | Active ruleset ID 26801439, PR + three required Foundation jobs; required approving reviews **0** | Source baseline control is not human owner approval. No automatic change to main |
| Proposed GitHub witness | Exact refs/heads/mst/m4-witness/v1 **404/not found** | No independently protected rollback floor |
| Ruleset bypass | GitHub Actions token omits bypass actor list and returns 403 for classic branch-protection endpoint | **UNVERIFIED**, not a proven empty global bypass list or independent admin custody |
| Role proposal | 8 roles, 25 required distinct-principal pairs, **0 actually bound identities** | Strings/names are not authenticated independent controllers |
| Google Drive | Connected API 10/11/2026 showed root + four project folders have one visible owner role each; shared=false | Snapshot of metadata for caller, not immutable custody or GitHub Actions live Drive read |
| A03 negative fixtures | 48/48 synthetic tests; isolated sequencers each accept conflicting G2 and reset reader can accept stale G1 | Counterexample to local hashes as remote CAS/nonresettable floor, not independent authentication |
| Release readiness | All G01–G08 OPEN and production cache/trading blocked | Green CI = correct denial, NOT release |

Source readbacks on previous exact commit: M4 live ruleset https://github.com/ngluonghoa/MST/actions/runs/42754471257 ; reader readiness https://github.com/ngluonghoa/MST/actions/runs/42754471316 ; role topology https://github.com/ngluonghoa/MST/actions/runs/42754471547 ; A03 two-reader/writer https://github.com/ngluonghoa/MST/actions/runs/42754471450 . All are token-limited evidence, not privileged independent witness.

## 3. G01 independent signer root — OPEN

Owner must privately approve real separate POLICY_CONTROLLER, SIGNER_ROOT_CUSTODIAN and REVOCATION_CONTROLLER, two restricted WITNESS_WRITER_A/B, DRIVE_CHUNK_WRITER and READ_ONLY_VERIFIER, preserving the already defined 25 pairwise identity constraints. PULL_REQUEST_CI remains read-only and must not obtain signer keys, real vendor credentials or owner approval privileges.

Acceptance would require independently reviewed actual admin/bypass/recovery graph, signer key lifecycle and enrollment, independent custody, adversarial denial of signer/policy escalation and owner-signed evidence. The currently public 8-role model has **0/8 assigned**. Even genuine signed commits are not evidence of vendor source truth. An administrator with capability to replace both witness policy and registry remains a shared-root rollback threat unless separately controlled.

**Owner decisions OA01/OA02 OPEN**. Do not publish actual owner names, account IDs, private signer data or credential secrets in this public repository.

## 4. G02 non-resettable monotonic floor — OPEN

Proposed dedicated witness ref is absent. In-memory reader floors, A03 synthetic Committed/Visible markers and SHA history cannot establish an externally protected, independently non-resettable high-water mark. New or reset reader admits an older G1; unrelated isolated publishers can manufacture distinct G2 chains.

Future gated acceptance: owner-approved real witness genesis bound to actual source rights/partition and signer epoch, effective non-force/non-delete/no-unreviewed-bypass witness protection, independent monotonic head across reader restarts, key rotations, revoked writers, admin recovery/restore, missing Drive bytes and old signed manifest replay. Fresh reader must learn the **highest independently accepted external floor**, not a caller-supplied value. If platform-root administrators can still reset the floor, explicitly record unmitigated risk and keep production **BLOCKED**.

**Owner decisions OA02/OA05 OPEN**. No witness genesis creation or GitHub ruleset modification authorized.

## 5. G03 two authenticated publishers / server CAS — OPEN

The new A03 in-process WriterClaim uses strings as actor labels. A single Python sequencer can reject competing claims, but two isolated sequencers each accept separate conflicting G2 children. That test demonstrates that local exclusivity is **not** a real two-credential, server-enforced CAS.

Future gated acceptance: two separately authenticated and restricted writer principals, independently read-only verifier, owner-approved protected witness branch, two sibling-head proposals submitted in separate real runner/session contexts, exactly one winner and definite loser, loser re-fetch and quarantine, ambiguous response/retry/crash, reset floor/unsigned ref bypass and signer revocation tests. GitHub ref force=false checks fast-forward ancestry but does **not** make a Google Drive+GitHub transaction or prove source authenticity (official GitHub ref API: https://docs.github.com/en/rest/git/refs). Reader must separately verify accepted protected witness, signer, current rights, and actual Drive bytes, re-read the head and reject any inconsistent cross-service view.

**Owner decisions OA03/OA04 OPEN**. Never reinterpret a locally self-attested hash or a CI PASS as production publication authority.

## 6. Owner decisions in the new bridge (NOT new roles)

| ID | Decision required | Status |
| --- | --- | --- |
| OA01 | Privately review actual role principals and root-admin/bypass graph (existing C01 / R01–R02) | OPEN |
| OA02 | Approve signer root, witness/genesis scope and durable G02 floor (existing C02–C04/ADR) | OPEN |
| OA03 | Approve two authenticated writers, independent reader and server CAS acceptance (C05–C06) | OPEN |
| OA04 | Approve licensed Drive data custody and two-service crash/revocation plan (C07) | OPEN |
| OA05 | Explicitly resolve or record residual shared-root rollback/admin threat | OPEN |
| OA06 | Preserve all A02/A03/G04–G08/M3/M4/M5/M8 owner release gates (C08) | OPEN |

All owner choice, attestation-URI and role principal binding fields in the public packet remain **NULL**. This preserves the original eight-role, 25-distinct-pair architecture instead of creating a competing authorization policy.

## 7. Implemented read-only bridge and test evidence

- docs/MST_M4_OPTION_A_G01_G03_OWNER_DECISION_BRIDGE_20261110.json: exact fact/decision matrix, three G01–G03 acceptance requirements, all authority flags false, six owner decisions unsigned.
- scripts/m4_option_a_g01_g03_owner_packet_preflight.py: validates original Option A choice, 8-role proposal, historical Drive metadata, and **two independently executed live GitHub read-only REST receipts**. Any changed witness, unverified bypass promotion, premature gate closure, unauthorized role binding or source pin drift fails closed requiring new owner review. It never authorizes production.
- tests/test_m4_option_a_g01_g03_owner_packet_preflight.py: **36 tests**, which use only mocked negative receipts; the workflow separately fetches actual GitHub REST data before its final bridge check. Tests deliberately reject forgery of G01 signer, G02 floor, G03 CAS, owner approvals, withheld rights and changed GitHub main.
- .github/workflows/m4-option-a-g01-g03-owner-decision-bridge-readonly.yml: same-repo Draft PR #8 and **contents:read** only, Python 3.12, 36 tests, executes existing real read-only M4 live custody and reader-readiness scripts with token, then validates both, stores 14-day review-only untrusted artifacts.

**Verified code/workflow HEAD:** d5e59b8944580755d03942b68455316481cfd0d6.

- Dedicated new owner G01–G03 preflight https://github.com/ngluonghoa/MST/actions/runs/42755918373 **SUCCESS; 36/36 tests**, live GitHub token-limited readback; outcome G01_G02_G03_OWNER_DECISION_PACKET_BLOCKED_BUT_INTERNALLY_RECONCILED, all production flags false.
- Foundation https://github.com/ngluonghoa/MST/actions/runs/42755918282 **SUCCESS 3/3**, Python3.11 **2,313/2,313** and Python3.12 **2,313/2,313**, original engineering63/63, H2/H3 source checks, lint/wheel PASS.
- **19/19 exact code-HEAD GitHub workflows SUCCESS**. This QA document creates a subsequent documentation commit; **verify exact report-containing HEAD separately**.

## 8. Owner safety / decision semantics

A green result means *"all three G01–G03 gates are still blocked and our evidence agrees"*. This is not independent owner custody, a signer, a non-resettable floor, actual Drive bytes, two authenticated writers, source rights or an authorized release. Google Drive ACL metadata and capabilities depend on current viewer scopes/roles; a file-owner count does not grant immutable custody (official Drive guidance: https://developers.google.com/workspace/drive/api/guides/manage-sharing).

**A02 0/63 formal owner module signoffs, A03 production V2 ABI unapproved, G01–G08 OPEN, M3/M4/M5/M8 production BLOCKED, no trading.** Next safe step is owner/private review of effective role identities, admin bypass and root threat model under Option A, followed only by separately authorized independent evidence. Preserve protected main and Draft PR #8. No automatic privilege writes or production deployment.
