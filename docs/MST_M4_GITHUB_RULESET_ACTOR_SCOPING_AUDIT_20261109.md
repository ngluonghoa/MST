# MST M4 — Real GitHub ruleset scope, token-dependent bypass metadata and witness policy gap

**Date:** 2026-11-09 · **Scope:** read-only GitHub REST metadata inspection from the connected GitHub account **and** a separate GitHub Actions runner token, plus offline negative contract tests. No force/delete/bypass attempt on any branch, no role/credential elevation, no actual Google Drive market cache, no provider entitlements.

## Immutable MST source / branch boundary

- Original Swing Trading 1.8 source pin `cd90c1babae8912db31490ad614fc2ad2f868042`; MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, original tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, **63 inherited Python modules unmodified**.
- [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8) remains OPEN/DRAFT/UNMERGED. No code paths or default V1/V2 cache logic changed, only a PR-only GitHub ruleset inspection script, offline tests, and a new read-only Actions job.
- Prior [two parallel-issued GitHub ref experiments](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_M4_PARALLEL_REMOTE_REF_TRIAL_20261109.md) proved GitHub non-force sibling overwrite rejection with HTTP422, but **did not** establish durable protection of the test branches.

## Actual GitHub ruleset observations

Official GitHub REST reads via connected GitHub:
- [Repository ruleset #26801439, MST - Protect Main](https://github.com/ngluonghoa/MST/rules/26801439) returned **active**, target **branch**, source **repository `ngluonghoa/MST`**, reference condition `include=["~DEFAULT_BRANCH"]`, `exclude=[]`. This policy selects the default branch, not arbitrary `mst/m4-witness-test-only/*` refs.
- Active rules list contained `deletion`, `non_fast_forward`, `pull_request`, and `required_status_checks`. Required CI contexts: `unittest (3.11)`, `unittest (3.12)`, `Contract, source-boundary and wheel checks` (reported integration ID `15368`). A separate `GET /branches/main` reports `protected:true`, SHA `4048f91beaaa3410116d97e35896c8b688384e19`. The legacy branch-protection `protection.enabled=false` field is not enough to contradict an **active ruleset**. No mutation of main was attempted.
- **Material review limitation:** `pull_request.parameters.required_approving_review_count=0`. Requiring the PR mechanism does **not** mean that ruleset itself demands any positive human/owner approval. A02 63 individual module signoffs are therefore still **manual process gates**, not demonstrated GitHub enforced ownership signoff.
- **Material CI freshness limitation:** `required_status_checks.parameters.strict_required_status_checks_policy=false`. The configured checks are required, but this ruleset alone does not mandate a strictly up-to-date head relative to base. This is distinct from the source lock and does not claim the ruleset is broken.
- Connected GitHub account response exposed `bypass_actors=[]` and `current_user_can_bypass="never"`. This is **scoped to that response and authenticated connection**, not proof of every future account or privilege.
- `GET /branches/mst/m4-witness-test-only/race-20261109-r1` and `...r2` each returned **`protected:false`** with preserved expected commit heads `eb74a8c9cbfaa1fc6376b9b02ff837bfb7e7b19f` and `3487a1c08faa404aab311ff6fff719f8ba9b8b6a`. Neither of the trial refs is currently authorized as a protected M4 witness.

### Substantive per-token difference discovered by real CI (not a vendor attack)

The first read-only hosted GitHub Actions audit on [run #42591723486](https://github.com/ngluonghoa/MST/actions/runs/42591723486) failed closed because its separate `GITHUB_TOKEN` GitHub ruleset response **did not expose a populated `bypass_actors` array**, even though `current_user_can_bypass` was `never`. An explicitly narrowed diagnostic run [#42591927684](https://github.com/ngluonghoa/MST/actions/runs/42591927684) confirmed `debug_ruleset_actor_bypass="never"`, `debug_configured_bypass_actor_count="<unavailable>"`, with no token/key material logged. We must not turn a missing/unavailable response field into an asserted empty bypass list.

Repair (PR-only `scripts/m4_github_ruleset_audit.py`):
- If the caller token sees `bypass_actors=[]`, `bypass_actor_list_verified_for_this_token=true`.
- If `bypass_actors` is omitted or null, **do not** infer it is empty. Retain `bypass_actor_list_verified_for_this_token=false` and status `MAIN_RULESET_ACTIVE_TEST_REFS_UNPROTECTED_BYPASS_LIST_UNVERIFIED`.
- Fail if a **nonempty** bypass list is exposed or `current_user_can_bypass` is not `never`.
- Require exactly the main ruleset identity, active scope, main baseline SHA, actual `protected:true`, anti-delete and anti-non-fast-forward rules, required PR and exact three CI contexts, and exact two test-branch names/heads still `protected:false`; fail on policy drift.
- Explicitly surface `main_required_approving_review_count=0`, `main_requires_positive_review=false`, and `main_required_ci_strict_up_to_date=false`. Do not silently declare owner-reviewed or fully anti-rollback protected.

[Code-only exact HEAD GitHub Actions run #42592600153](https://github.com/ngluonghoa/MST/actions/runs/42592600153) **PASS 3/3 read-only jobs**: actual hosted ruleset audit emitted the narrower `...BYPASS_LIST_UNVERIFIED` status, with seven authority fields false, plus the prior sequential and parallel-attempt remote ref readback checks. [Foundation CI run #42592601190](https://github.com/ngluonghoa/MST/actions/runs/42592601190) **PASS 3/3**: Python 3.11 `1,644/1,644`, Python 3.12 `1,644/1,644`, engineering `63/63`, H2/H3/lint/wheel. [Cross-run synthetic workflow #42592600249](https://github.com/ngluonghoa/MST/actions/runs/42592600249) **PASS 2/2**.

The report-containing final commit must have its own exact-head CI readback before recording a finished checkpoint.

## Candidate owner acceptance gates — OPEN, not implemented

1. **POLICY-G01 — Separate protected witness ref:** Create a ruleset scoped specifically to a **canonical M4 witness branch prefix**, not just `~DEFAULT_BRANCH`; independently verify active ref scope and protection on a newly provisioned, not fixture, branch. A fixture ref with `protected:false` cannot be promoted to production.
2. **POLICY-G02 — No-force/no-delete/no-bypass including future identities:** Confirm force/delete/recreate restrictions and actor-specific + globally configured bypass list from an authenticated owner/admin policy read, including future repo admins, Actions installations and GitHub Apps. The read-only Actions `bypass_actors` field is unavailable in this CI context; mark unverified, never `[]` by assumption.
3. **POLICY-G03 — Owner approvals and CI strictness:** Formal policy decision on required human/owner review count (currently 0) and strict up-to-date CI (currently false). These observations **do not authorize changing existing main policy** without explicit owner approval; do not automatically enable/administer these flags.
4. **POLICY-G04 — Two distinct principals and server CAS:** Future **separately authorized actor identities** must race siblings of one protected head using verified server semantics, observe exactly one winner and one definite loser, and prove no bypass/force/delete under adversarial retry/crash across GitHub Actions runs.
5. **POLICY-G05 — Independent durable signed floor and Google Drive:** Immutable original source clocks, legitimate rights/revocation, real physical Drive chunk bytes+retention and two-service crash journal/readback, signer epoch and per-partition externally protected monotonic floor. A GitHub ruleset on its own is **not** the full market-data custody protocol.
6. **POLICY-G06 — Fail-closed evidence:** Expose `ruleset_verified`, `bypass_actor_list_verified_for_this_token`, `main_review_count`, `main_ci_strictness`, `m4_witness_ref_protected`, `vendor_license_verified`, `independent_floor_verified`, and `production_trading_authorized` as separate states in a future machine-readable release receipt. Synthetic/unattested observations must never confer rights.

**No multi-account write token was provisioned.** GitHub Actions jobs use `permissions: contents: read`; PR-controlled workflows have not been granted branch write authority. No force-push/deletion attempts, credential secret material, Mac/MOCHI/local compute, vendor data or real Drive market-cache data.

**Remaining blocking work:** A02 manual 63/63 owner dispositions, A03 V2 ABI owner approval, M3 authenticated SSI/DNSE/VCBS entitlement and first-known clocks, M4 protected physically authenticated cache/floor/writer/Drive, M5/M8 release. Prior Issue #10/#13/#14 remain OPEN. Do not merge PR #8.
