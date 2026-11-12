# MST M4 — G01/G02 independent signer / monotonic floor architecture and owner-decision QA

**QA ID:** MST-M4-ADR-G01G02-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**VERDICT:** ADR proposal and blocking validations **PASS**, G01/G02 architecture **NOT SELECTED / NOT IMPLEMENTED / NO PRODUCTION AUTHORITY**.

## 1. Scope and source invariants

Original Swing Trading 1.8 source commit `cd90c1babae8912db31490ad614fc2ad2f868042`. Protected MST main remains `4048f91beaaa3410116d97e35896c8b688384e19`, original source tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`; all 63 inherited v1 modules and existing V2 candidate source are untouched. Scope is the *Draft, unmerged* [PR #8](https://github.com/ngluonghoa/MST/pull/8). No Mac, MOCHI, local project execution, new managed cloud provisioning, owner credentials, production GitHub ruleset/ref action, licensed SSI/DNSE/VCBS market bytes or actual Google Drive chunk writes.

## 2. Actual work added

- `docs/MST_M4_ADR_G01_G02_TRUST_ROOT_MONOTONIC_FLOOR_20261109.md`: detailed architecture decision record for independent signer root, durable partition/rights scoped monotonic floor, CAS, key rotation/revocation, 2-service reader barrier, source-data rights and explicit owner approval. Includes 3 alternatives, 8 owner decisions, 13 independently verifiable test requirements, crash/recovery protocol, admin/root bypass threat and links to vendor documents. Proposals **NOT APPROVED**.
- `docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json`: machine-readable decision draft, exactly 8 decisions `D01..D08` OPEN, 3 options unselected, all rights FALSE, 13 real witness acceptance test identifiers. Absolute GitHub+Drive-only design option A is `CONDITIONAL_UNPROVEN`; new Cloud KMS+Firestore option B is `REQUIRES_EXPLICIT_SCOPE_EXTENSION`; Actions cache as trust root option C is `REJECTED_UNSAFE`.
- `scripts/m4_owner_architecture_preflight.py`: *strictly blocked draft schema* validator. Any new/unknown approval fields, changed source SHA/63 modules, unreviewed options, self-selected provider, owner-approved flags, fake proof URLs, removed tests, or disabled security invariant FAIL CLOSED. It never approves an option by itself; a separately governed process and NEW schema would be required for owner signoff.
- `tests/test_m4_owner_architecture_preflight.py`: **36 new cases** asserting all options unselected, all gates open, no GCP scope extension without approval, no self-attestation, pin protection, root/admin/revocation and correction policy invariants, and strict safety on altered JSON.
- `.github/workflows/m4-owner-architecture-review.yml`: dedicated hosted PR #8 (same-repo) workflow with `contents:read` only, validates the draft, uploads the ADR, JSON decision record and an *UNAPPROVED* machine-readable blocking receipt to a temporary CI artifact with 14-day retention.

## 3. Architecture findings: explicit implementation choices

**A. GitHub+Drive only:** separate owner-controlled GitHub witness and trust registry, protected signed commits and Git ref readback, verified bypass inventory and independent watcher, licensed Drive chunks. Still **NOT PROVEN** against shared admins/force-push/cached floor reset, true independent CAS authority or cross-GitHub/Drive atomicity. A green signed-commit check is not provider-origin truth and a fast-forward can carry stale content. The owner can keep the GitHub+Drive-only constraint, but cannot close G01/G02 until actual independent tests demonstrate those conditions.

**B. Cloud KMS+Firestore** (Google Cloud services outside approved GitHub+Drive-only runtime): separates key management and transactional monotonic floor; Cloud KMS supports Ed25519 at supported protection levels; Firestore transactions are serializable. **No selection/provisioning**: needs owner permission for extra services, IAM role/administrator separation, OIDC identity, budget, regional/log retention governance. Firestore does not itself remove admin-reset threats or atomically span GitHub+Drive; independent audit/WORM/recovery still required.

**C. Actions cache or self-hashed Drive claims as root:** **REJECT**, because it is evictable, forgeable by the writer and not server-atomic/non-resettable.

Owner decision questions D01–D08 remain OPEN: (01) absolute cloud scope or extension; (02) independent custodian and bypass control; (03) protected registry+receipt floor/CAS; (04) two writer/reader identity; (05) actual vendor license, correction and retention; (06) global key revoke and failure recovery; (07) budget and data residency; (08) owner A02/A03/M3/M4/M8 release signoffs.

## 4. Exact hosted validation evidence

**Code/ADR/contract HEAD:** `7fd97624a901db7014b543c70d5c0d62eab21b77`.

- [Foundation CI #42615400854](https://github.com/ngluonghoa/MST/actions/runs/42615400854) **SUCCESS 3/3**; Python 3.11 **1804/1804**, Python 3.12 **1804/1804**, engineering contract **63/63**, H2/H3 source-boundary/parity checks and lint/wheel PASS.
- [Architecture draft guard #42615401073](https://github.com/ngluonghoa/MST/actions/runs/42615401073) **SUCCESS**. Output `G01_G02_ARCHITECTURE_REVIEW_ONLY_BLOCKED`, `owner_options_unselected=3`, `owner_decisions_open=8`, `independent_witness_tests_required=13`, `g01_verified=false`, `g02_verified=false`, `new_cloud_services_authorized=false`, `production_cache_read_authorized=false`, `production_cache_write_authorized=false`, `trading_authorized=false`. Created temporary artifact [13671688214](https://github.com/ngluonghoa/MST/actions/runs/42615401073/artifacts/13671688214), name `mst-m4-g01-g02-owner-architecture-draft-unapproved`, 14-day retention, NOT durable external owner trust.
- [Read-only GitHub ref check #42615400859](https://github.com/ngluonghoa/MST/actions/runs/42615400859), [Reader readiness block #42615401061](https://github.com/ngluonghoa/MST/actions/runs/42615401061), [synthetic cross-run registry #42615401282](https://github.com/ngluonghoa/MST/actions/runs/42615401282), and [synthetic cross-run journal #42615400860](https://github.com/ngluonghoa/MST/actions/runs/42615400860) all SUCCESS.

**After adding this report** a *new final HEAD* must be verified separately before declaring the entire documentation state current-green.

## 5. Open owner gates and follow-up

SIGNED-G01 independent owner trust root, SIGNED-G02 durable external monotonic floor, SIGNED-G03 true two-credential CAS, SIGNED-G04 legally licensed vendor first-known/correction/retention, SIGNED-G05 real Google Drive physical bytes plus protected Git ref/tree/crash recovery, SIGNED-G06 global revocation, SIGNED-G07 authentic evidence tiers, SIGNED-G08 owner parity/ABI/release remain **OPEN**. So do [issue #16](https://github.com/ngluonghoa/MST/issues/16), [witness #15](https://github.com/ngluonghoa/MST/issues/15), [multiwriter #13](https://github.com/ngluonghoa/MST/issues/13), [cross-service #14](https://github.com/ngluonghoa/MST/issues/14), [real Drive #10](https://github.com/ngluonghoa/MST/issues/10), [source rights #9](https://github.com/ngluonghoa/MST/issues/9), [A02 #4](https://github.com/ngluonghoa/MST/issues/4), and [A03 #6](https://github.com/ngluonghoa/MST/issues/6).

**No action taken:** no new cloud resources, production policy/ruleset, signer key, writer account, vendor onboarding or broker order. The architecture is ready for owner REVIEW but **not approval**. No release, no PR merge.
