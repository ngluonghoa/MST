# MST A02 — Complete 63 Inherited Module Static API / Dependency Owner-Review Packet

QA ID: MST-A02-LEGACY-63-STATIC-INTERFACE-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: PASS for actual 63-module source-byte identity and AST interface/dependency extraction. OWNER SIGNOFF **0/63**; FULL V1↔V2 BEHAVIOR/ABI PARITY **NOT ACCEPTED**. All production/trading gates BLOCKED.
Project: Option A GitHub+Google Drive cloud-only. Work PR: https://github.com/ngluonghoa/MST/pull/8 (Draft/unmerged).

## 1. Purpose — productive progress without fake owner-root authority

The preceding G01–G03 cross-viewer investigation proved that three observable API/metadata views do not establish two independently controlled principals. No more synthetic security evidence should be mistaken for production readiness. A02's separate open owner gate is the module-by-module review of the original Swing Trading behavior and compatibility. Existing docs/H3_MODULE_DISPOSITION_PROVISIONAL.md listed static complexity, fan-in and provisional KEEP/IMPROVE/REPLACE/REMOVE labels but they were NOT 63 human signoffs. This checkpoint provides a fresh programmatically generated *owner-ready review packet* from the actual full V1 source, without modifying any V1/V2 source module.

## 2. Independent live GitHub source lock (not inferred from AST)

GitHub Actions read the REAL remote upstream ngluonghoa/swing-trading-1-8 commit cd90c1babae8912db31490ad614fc2ad2f868042 and protected MST main@4048f91beaaa3410116d97e35896c8b688384e19. The full original Git tree is d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e: **216 Git entries, 208 blobs, 63 inherited V1 Python modules**. The candidate PR HEAD preserves every inherited source path/blob/mode and includes precisely the 8 previously known V2 opt-in sidecars (no unknown new package modules). Original source remains 1:1.

That remote tree inspection is run separately from the new AST parser. AST alone cannot detect behavioral body changes that leave public signatures identical. The workflow requires BOTH remote source-byte tree equality and successful static module inspection.

## 3. What was actually inspected

On the GitHub-hosted runner (not on a user Mac or MOCHI), scripts/m2_a02_legacy_63_interface_review.py:
- Parses the actual src/swing_trading directory; accepts only 71 total Python modules = 63 original V1 plus the preapproved 8 V2 sidecars excluded from V1 review.
- Cross-checks the exact 71 module names against the existing H3 provisional Markdown table (not trusted owner endorsements).
- Parses each actual original module using Python AST without import/execute of trading domain code. Extracts public module-level functions, public classes, exposed method signatures and selected dataclass annotated field names, direct internal imports, SHA256 of checkout file bytes and a per-module interface fingerprint (argument AST, annotations, defaults and method decorators).
- Counts direct internal module consumers and adds H3 group/flag/provisional status to each of 63 review rows.
- Issues an aggregate deterministic package API fingerprint: **20eb42b4266511ebb6578fc7bf686165eac5c291dae50a752909866d4166dfe6**.
- Produces a 63-row JSON review artifact with per-module owner_decision=NOT_SIGNED, owner_abi_approved=false and owner_behavior_parity_approved=false. Nothing in the AST inventory verifies original external vendor rights, real market behavior, runtime reflection, dynamic call graphs, source authenticity beyond the separate remote Git lock, broker fills, or production authorization.

Eight first-priority modules for owner-side substantive ABI review: contracts, engine, replay, market_data, source_quality, incremental_cache, cache_fetch_planner, vn_backtest_execution_fixture. Selection is review prioritization, not evidence that other modules may skip review. All 63 still require owner disposition.

## 4. Additive files

- scripts/m2_a02_legacy_63_interface_review.py — deterministic actual-source AST review crosswalk (no source import, remote writes, secret, vendor or local environment).
- tests/test_m2_a02_legacy_63_interface_review.py — **35 tests**: 63 and 8 exact package separation, real H3 71-name crosswalk, public callables, method annotation/default/decorator/class-field drift, direct dependency, fake H3 row, missing/deleted/renamed/new source module in temporary GitHub-hosted test copies, body-only change not misrepresented as ABI change, zero owner signoffs, no production approval.
- .github/workflows/m2-a02-legacy-63-static-api-review.yml — same-repo Draft PR #8, contents:read, GitHub-hosted Python3.12, independently fetches upstream/main/PR Git object trees via existing scripts/mst_remote_legacy_tree_lock.py, runs 35 tests and static AST analysis, stores both 14-day review-only JSON receipts.
- docs/MST_A02_63_INTERFACE_REVIEW_QA_20261110.md — this report and a mirrored Google Drive QA document.

No changes whatsoever to original src/swing_trading V1 modules or eight already-existing opt-in V2 modules.

## 5. Exact observed GitHub Actions results on code/workflow HEAD

Code/workflow HEAD f8fc101f590395e2ff01bd7d10cb3ea5bff425ba.
- Dedicated A02 source review and remote source parity: https://github.com/ngluonghoa/MST/actions/runs/42761347660 **SUCCESS**, **35/35 tests PASS**, live GitHub tree readback: ORIGINAL_TREE_1TO1_LEGACY_63_UNCHANGED_AND_EIGHT_V2_SIDECARS. AST review receipt: V1_63_MODULE_AST_API_DEPENDENCY_PACKET_COMPLETE_OWNER_NOT_SIGNED, 63 rows, eight excluded, H3=71, ABI fingerprint above, owner signoffs=0.
- Foundation: https://github.com/ngluonghoa/MST/actions/runs/42761346969 **SUCCESS**: Python3.11 **2495/2495**, Python3.12 **2495/2495**, engineering source-boundary 63/63 plus H2/H3/lint/wheel.
- All **23/23 GitHub workflows SUCCESS** on code/workflow HEAD. The subsequent report-containing HEAD must be checked separately before claiming 23/23 for that final commit.

## 6. Remaining owner decisions and security boundaries

A02 human individual 63 module dispositions: **0/63 signed**. Existing H3 labels are provisional complexity suggestions only. A03 full V2 ABI/behavior parity: OPEN. G01 signer independence, G02 nonresettable protected monotonic floor, G03 real authenticated two-writer CAS, G04 vendor rights, G05 actual physical Google Drive market cache, G06 revocation, G07 independent provenance, G08 final release: OPEN. OA01–OA06 owner decisions and M3/M4/M5/M8 production/trading BLOCKED.

No Mac/MOCHI/local runtime, third-party Cloud, actual vendor quotes, Drive real market-cache, crypto signer, privileged GitHub/Drive ACL/ref/witness changes, PR merge, broker operation, release or trading.

Next SAFE engineering progress: use owner-ready A02 review packet to write exact per-module compatibility checkpoints for the first eight high-impact modules, testing against real inherited code and synthetic source inputs in GitHub CI, but do not mark owner approval or claim V2 full parity without explicit separately authenticated owner review.
