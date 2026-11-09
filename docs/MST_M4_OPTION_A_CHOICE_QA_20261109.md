# MST M4 — explicit Option A (GitHub + Google Drive only) scope selection and QA

**QA ID:** MST-M4-OPTION-A-SELECT-001  
**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Verdict:** **ARCHITECTURE OPTION A RECORDED FROM EXPLICIT USER CHAT MESSAGE.** No production signer/custody/market-data approval. G01–G08 and all owner-gated witness actions stay OPEN.  
**Source lock:** Swing Trading 1.8 `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, inherited 63 V1 source files untouched.

## 1. User decision and narrow scope

In the MST conversation on 2026-11-09 the user explicitly answered **"Đồng ý phương án A"** to continuing on **GitHub + Google Drive only**. This is a valid **platform/architecture choice instruction**, not an authenticated owner security signature or authorization to deploy a privileged witness, enroll a signer, enable actual licensed SSI/DNSE/VCBS data, write market cache bytes or trade.

**Current source of truth for platform selection:**
`docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json` (`mst.m4.option-a.scope-decision.v1`), with `selected_architecture=A_GITHUB_DRIVE_ONLY`, `allowed_platforms=["GitHub","Google Drive"]`, `architecture_choice_scope_approved=true`, `decision_origin_integrity=CHAT_INSTRUCTION_RECORDED_NOT_INDEPENDENTLY_SIGNED`.

**Historical source to preserve:** `docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json` remains the original **unselected proposal snapshot**. It is NOT current architecture-choice status, but retains its frozen all-gates-open checks as an audit baseline. The amended ADR explicitly identifies this versioned overlay and its precedence **only for platform selection**.

**Option B (Cloud KMS+Firestore): NOT SELECTED / NOT IN APPROVED SCOPE.** Do not silently add a cloud service; any future change requires a new explicit user instruction and a new decision record. Option C (Actions cache/self-hash as root) remains REJECTED UNSAFE.

## 2. Cloud-only work completed

- `docs/MST_M4_OPTION_A_SCOPE_SELECTION_20261109.json`: versioned choice overlay, fixed source hash/63-module count, allowed platform pair, 9 future Option A trust controls, 7 explicitly blocked privileged actions, all 8 SIGNED-G security gates OPEN and all operational rights FALSE.
- `scripts/m4_option_a_selection_preflight.py`: strictly typed source-lock and exactly pinned selection validator. Detects any fabricated signer/producer/data rights, production admission, new cloud platform, removed gate/control, changed decision source or legacy source pin. `owner_architecture_scope_choice_recorded=true` is **not** `independent_owner_authentication_attested`.
- `tests/test_m4_option_a_selection_preflight.py`: **33 new cases** covering valid user choice, historical draft preservation, B/C selection attacks, unapproved platform/credential/merge changes, missing/null/true production privileges, malformed data types, float-coerced source module count, stripped protected-floor / admin-bypass safeguards, removed gate and PR merge guards.
- `docs/MST_M4_OPTION_A_GITHUB_DRIVE_TRUST_CUSTODY_PLAN_20261109.md`: concrete proposed custody separation, protected witness, signer registry, Google Drive physical chunk readback, publisher CAS, reader re-verification, idempotent recovery and 9 owner acceptance rows. Explicit caution that GitHub protection is **not** an indestructible external monotonic floor under admin/bypass threat.
- Amended `docs/MST_M4_ADR_G01_G02_TRUST_ROOT_MONOTONIC_FLOOR_20261109.md`: tracks A selection, defers B and retains G01/G02 security gates.
- Updated `.github/workflows/m4-owner-architecture-review.yml`: **same PR #8 only**, `permissions: contents:read`. Runs both historical draft guard and the current A-only selected-scope guard; uploads their JSON verdicts and architecture documents as a temporary review artifact. No Git ref, ruleset, signer, real market cache or admin writes.

This work is executed **only through GitHub and Google Drive**. No Mac/MOCHI/local state; no new infrastructure provider. The existing v1 modules, earlier V2 code and protected main have not changed.

## 3. Real exact-code-HEAD GitHub Actions evidence

**Code/selection/ADR/blueprint HEAD:** `ee64f8263565e27fada154828933dd64ef550d1b`.

- [Foundation CI #42618597631](https://github.com/ngluonghoa/MST/actions/runs/42618597631): **SUCCESS 3/3**; Python 3.11 **1837/1837**, Python 3.12 **1837/1837**, engineering **63/63**. H2/H3 source-boundary, lint and wheel PASS.
- [Option A scope guard #42618597598](https://github.com/ngluonghoa/MST/actions/runs/42618597598): **SUCCESS**. Two independent JSON outputs in same job: historical `G01_G02_ARCHITECTURE_REVIEW_ONLY_BLOCKED` (snapshot remains frozen); current `OPTION_A_SCOPE_SELECTED_M4_CUSTODY_AND_PRODUCTION_BLOCKED`. Current `architecture_option_selected=A_GITHUB_DRIVE_ONLY`, `allowed_platforms=["GitHub","Google Drive"]`, `signed_gates_open_count=8`, `independent_owner_authentication_attested=false`, `real_witness_or_signer_provisioning_authorized=false`, `new_cloud_services_authorized=false`, `cache_read_authorized=false`, `cache_write_authorized=false`, `trading_authorized=false`. GitHub artifact [13672639537](https://github.com/ngluonghoa/MST/actions/runs/42618597598/artifacts/13672639537), `mst-m4-option-a-scope-selected-production-blocked`; **14-day retention** only, NOT durable independent custody. User-choice JSON self-hash is `fe4bb44933b597f2a853026532c6732019397062cedcce5f68e7a7e7918004d3`, checksum only, NOT user signature.
- Other exact-code-head workflows success: [M4 reader readiness](https://github.com/ngluonghoa/MST/actions/runs/42618597588), [GitHub remote ref](https://github.com/ngluonghoa/MST/actions/runs/42618597596), [untrusted registry cross-run](https://github.com/ngluonghoa/MST/actions/runs/42618597646), [untrusted journal cross-run](https://github.com/ngluonghoa/MST/actions/runs/42618597625).

**Documentation-only final PR HEAD** must be reverified separately after this report commit; do not automatically treat any earlier run as its status.

## 4. What selection A enables and does NOT enable

**Enabled now:** Continue architecture design, read-only GitHub/Drive verification, negative tests and QA on PR #8, preserving locked v1 behavior and cloud-only engineering. A proposed separate owner-controlled GitHub witness domain may be designed but **must NOT be provisioned without explicit privileged-action approval**.

**Still BLOCKED:** security signing key enrollment; independent admin-controlled witness ref/ruleset; proof of two independently authenticated writers/atomic CAS; non-resettable G02 high-water mark; global revocation; real licensed vendor source clock/correction/retention; physical Google Drive market-cache chunks and cross-service crash recovery; final A02 63-module disposition, A03 ABI signoff, M3/M4/M8 release and any trading action.

No evidence at this checkpoint proves Option A can defend against an unrestricted GitHub administrator rollback. This is a fundamental OPEN design threat and must be tested rather than relabeled as PASS. If Option A fails G01/G02 controls, report the precise failure to the user instead of weakening the acceptance contract or silently adding Cloud KMS/Firestore.

**Tracking issues:** [#16 signed G01..G08](https://github.com/ngluonghoa/MST/issues/16), [#15 owner-gated witness](https://github.com/ngluonghoa/MST/issues/15), [#13 multiwriter](https://github.com/ngluonghoa/MST/issues/13), [#14 cross-service](https://github.com/ngluonghoa/MST/issues/14), [#10 Drive cache](https://github.com/ngluonghoa/MST/issues/10), [#9 licensed vendor](https://github.com/ngluonghoa/MST/issues/9), [#4 A02](https://github.com/ngluonghoa/MST/issues/4), [#6 A03](https://github.com/ngluonghoa/MST/issues/6).

**Next:** Option A GitHub+Drive-only read-only custody/ACL feasibility inventory and owner-controlled witness threat review. No automatic privilege escalation, cloud scope expansion, PR merge or production release.
