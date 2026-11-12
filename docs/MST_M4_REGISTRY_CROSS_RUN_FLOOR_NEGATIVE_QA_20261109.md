# MST M4 — Cross-run signer registry / reader floor continuity; untrusted cache counterexample

**QA ID:** MST-M4-REGISTRY-XRUN-001  
**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Scope:** TEST-ONLY GitHub-hosted ephemeral runners and GitHub Actions cache.  
**Verdict:** Two consecutive real workflow runs successfully exchanged **synthetic registry bytes**, but durable/protected trust roots, authoritative signer rotation/revocation, independent floor, multi-actor CAS, vendor licensing and actual Google Drive data remain **NOT VERIFIED/NOT IMPLEMENTED**.

## Fixed source and permissions

- Original Swing Trading source SHA `cd90c1babae8912db31490ad614fc2ad2f868042`; MST protected main `4048f91beaaa3410116d97e35896c8b688384e19`, original Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- Work performed on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), not main. Exactly 63 inherited original source modules remain unmodified; previous V2 source modules, release version, ruleset, actual protected M4 witness and Google Drive persistent market cache remain unchanged.
- Added `scripts/m4_registry_cross_run_fixture.py`, `tests/test_m4_registry_cross_run_fixture.py` (15 negative/golden unittest cases) and `.github/workflows/m4-registry-cross-run-fixture.yml`. Existing GitHub Actions CI continues to enforce source module and package boundaries.
- Workflow token is `contents:read`; PR #8 only, same-repo guard. It cannot write protected Git refs or market data, sign as owner, update Drive objects or grant vendor entitlements. No Mac/MOCHI/personal local compute was used.

## What was executed on actual GitHub-hosted infrastructure

**A. Bootstrap run:** [GitHub Actions #42603032545](https://github.com/ngluonghoa/MST/actions/runs/42603032545) completed SUCCESS 2/2 jobs. Runner A confirmed `Cache not found` and reported `BOOTSTRAP_NO_PRIOR_REGISTRY_CACHE_UNATTESTED`. A second, distinct GitHub-hosted job (runner B) emitted synthetic claim `producer_run_id=42603032545` with provider-namespace test SHA, caller-only registry revision 1, signer epoch 1, `floor_generation=0`, false rights and a self-computed SHA. `actions/cache/save` confirmed key `mst-m4-registry-pr8-run42603032545`.

**B. Strict successor run:** [GitHub Actions #42603228364](https://github.com/ngluonghoa/MST/actions/runs/42603228364) completed SUCCESS 2/2 jobs after changing workflow to require a prior record. Runner A obtained a true `Cache restored successfully` message from exactly `mst-m4-registry-pr8-run42603032545` and verified `prior_run_id=42603032545` versus `current_run_id=42603228364`, namespace/schema, strictly older source-run identity, claim digest and all false authority flags. Output status `CROSS_RUN_REGISTRY_CACHE_BYTES_VERIFIED_UNATTESTED` with `registry_digest=7b075914a823e3c87e4345f8ed5c77d9e37ffaa80da112be54b41c1875a3a32f`. The next hosted runner B wrote a new cache key `mst-m4-registry-pr8-run42603228364`. This proves byte-level cross-run continuity on the real GitHub Actions platform, **not** any monotonic protection, authorization or guaranteed cache retention.

**C. Exact code/workflow HEAD:** `15197bfc25281097d2a83cbe831f7bb0d8737c93`. [Foundation CI #42603228366](https://github.com/ngluonghoa/MST/actions/runs/42603228366) SUCCESS 3/3, Python3.11 **1716/1716**, Python3.12 **1716/1716**, engineering suite **63/63**, H2 source inventory/H3 exact module matrix, lint, wheel isolated install PASS. [Read-only remote GitHub audit #42603228384](https://github.com/ngluonghoa/MST/actions/runs/42603228384) SUCCESS, [existing untrusted cross-run journal #42603228375](https://github.com/ngluonghoa/MST/actions/runs/42603228375) SUCCESS. This report commit will require independent final-HEAD CI readback.

## Fifteen test cases and falsification boundary

New `recover_fixture` protocol denies malformed envelopes/schema, changed bytes without matching SHA, self-rehashed attempts to assert owner/vendor/cache permission, foreign provider+rights partition, duplicate/same or future run, wrong PR identity, fake registry revision/key epoch/signer and floor generation/head, unsupported fields, boolean IDs and nonexistent prior cache in strict mode. It does **not** consume keys, vendors or Google Drive objects.

Five critical limits:
1. The **same valid prior synthetic cache** may be replayed into two later runs because no protected minimum generation/head exists.
2. Supplying a *caller-defined* minimum-run floor can block an old artifact but **resetting that input** immediately re-accepts the old cache; it is not a durable external antirollback floor.
3. A writer can regenerate a different well-formed self-hashed artifact with different run metadata; SHA protects accidental tamper only, not signer authenticity.
4. `actions/cache` can evict/replace/omit caches and has no signer lifecycle, source-clock, multi-account CAS or vendor rights guarantees. A cache restore from one particular prior run does **not** mean the newest authoritative state was selected.
5. Neither the registry nor the floor is protected outside the caller's own fixture and GitHub Actions cache. The original read-only main ruleset covers **main**, not any real authoritative M4 signer/witness ref.

No production/root/rights status is ever inferred from an observed cache hit: `independent_owner_root_verified=false`, `global_revocation_verified=false`, `protected_registry_floor_verified=false`, `protected_receipt_floor_verified=false`, `two_authenticated_writer_cas_verified=false`, `licensed_vendor_first_known_verified=false`, `physical_google_drive_bytes_verified=false`, `trading_authorized=false`.

## Remaining owner-gated acceptance

- [Issue #16](https://github.com/ngluonghoa/MST/issues/16) SIGNED-G01..G08: independent owner-managed trust root and signer enrollment, externally protected monotonic registry + rights-bound receipt floor, atomic two-account CAS, authenticated provider first-known/revision/license, real Drive physical byte/SHA and 2-service recovery, global revocation/rotation, explicit trust tiers and source/ABI release signoff.
- [Issue #15](https://github.com/ngluonghoa/MST/issues/15) WITNESS-PROV-G01..G06: real protected ref/ruleset scopes/bypass/actor visibility, owner-approved signer/writer/bootstrap. Not provisioned.
- [Issues #13](https://github.com/ngluonghoa/MST/issues/13) and [#14](https://github.com/ngluonghoa/MST/issues/14): true distributed writer arbitration, fail-closed cross GitHub–Drive reading/recovery. No actual writer admission without owner scope and authenticated privileges.
- [Issue #9](https://github.com/ngluonghoa/MST/issues/9) and [#10](https://github.com/ngluonghoa/MST/issues/10): genuine provider rights/Cloud retention and physically stored immutable Google Drive chunks. No real data accessed.
- [Issue #4](https://github.com/ngluonghoa/MST/issues/4) owner per-module 63 signoffs and [#6](https://github.com/ngluonghoa/MST/issues/6) public V2 ABI owner acceptance OPEN; M5/M8 release/trading blocked.

**Next permitted step without owner production approval:** keep narrowing read-only cross-run negative evidence and draft a provable owner-controlled trust-root/reader protocol with explicit independent evidence and rollback safety. DO NOT install a production ruleset/ref, register real signing keys, promote cache manifests, access licensed OHLCV, merge PR8 or trade.
