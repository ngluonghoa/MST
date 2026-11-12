# MST Option A — real administrator-root feasibility and full legacy Git-tree 1:1 QA

**Checkpoint:** 2026-11-09 Asia/Ho_Chi_Minh · **Security result: NO-GO for independent G01/G02 production acceptance on current evidence.**  
**Source parity result: PASS for pinned full upstream/main Git tree and 63 unchanged inherited Python modules on Draft PR #8; exactly 8 known additive V2 sidecar modules are present.**  
**Authorized platforms:** GitHub + Google Drive only. No other cloud, Mac, MOCHI or local project executor.

## 1. Why this checkpoint was necessary

Previous M4 work proved synthetic signed receipts, repository read-only ruleset observations and a 10-step owner change packet. No source showed an independently non-resettable G02 rollback floor or owner-approved signer G01. Adding more synthetic "approval" tests would not resolve the real issue: who can alter the repository's root trust policy and Google Drive custody.

This checkpoint independently checks **real GitHub metadata** and **full cross-repository source tree objects** while leaving actual administrative privilege and protected refs untouched. Drive findings are a separate, timestamp-scoped **connected Drive metadata observation**, not a GitHub Actions live Drive scan.

## 2. Live, token-scoped administrator and Drive observations

- GitHub connected app repository metadata for `ngluonghoa/MST` reports `owner.type=User` (personal repository), `default_branch=main`, `private=false`, and **`permissions.admin=true`** for the current connected actor. This shows that *this connector has an administrator-capable view* of this repository, **not** that two separate humans or independently governed administrator roots exist; it also does not imply any admin mutation has occurred. Do not publish actor logins, IDs or personal emails in this public repo.
- GitHub branch readback still shows `main.protected=true` with pinned SHA `4048f91beaaa3410116d97e35896c8b688384e19`. The read-only ruleset `MST - Protect Main` #26801439 is active, has PR + 3 foundation checks and deletion/non-FF rules, but requires **zero positive reviews**, has non-strict status freshness, and does not require signed commits in the observed rule.
- Proposed authoritative `refs/heads/mst/m4-witness/v1` is **absent (404)**; historical `test-only` refs do not count. No independent second protected witness root was found or installed.
- Connected GitHub app sees main ruleset bypass list empty for its token, but GitHub-hosted PR token cannot read that list; classic branch protection REST endpoint yields integration **403**. This is a **visibility limitation**, not evidence that all possible administrator/recovery bypasses are absent.
- Connected Drive `files.get` views for MST root, source-lock, canonical Docs, QA, synthetic staging folders returned `shared=false` with **one owner-role permission visible per folder**. Do not conclude that these are five separate humans, or that a single user controls both services; neither inference is proven. No externally governed WORM retention, independent Drive ACL watcher, actual licensed vendor chunk immutable bytes or separate approved verifier was demonstrated.

**Conservative risk verdict:** `ONE_OR_MORE_ADMINISTRATORS_MAY_HAVE_THE_ABILITY_TO_CHANGE_ROOT_POLICY; INDEPENDENT_CONTROLLER_AND_NONRESETTABLE_G02_FLOOR_NOT_VERIFIED`. Having `admin=true` in an app connection is a **reason to investigate root separation**, not evidence that an administrator compromised or rewound data. Do **not** call option A impossible as a general theorem; it is **NOT PROVEN SUFFICIENT** with presently observable owner identities.

## 3. GitHub full-tree source parity, not just 63 spot checks

Actually observed through GitHub REST:
- Upstream repo `ngluonghoa/swing-trading-1-8` pinned source commit `cd90c1babae8912db31490ad614fc2ad2f868042` has Git tree SHA `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- MST protected `main` commit `4048f91beaaa3410116d97e35896c8b688384e19` points to **the exact same tree SHA** despite its different commit/parent history.
- Both recursively inspected Git trees contain **216 entries: 208 blobs and 8 tree objects**, including **63 inherited Python files under `src/swing_trading/`**. There is **zero blob/path/mode difference** between the original and MST `main` source trees.
- Draft PR #8 **retains all 63 original V1 Python blobs byte-identical**; this candidate *intentionally adds precisely eight V2 modules under the same package namespace*, not eight modified V1 modules:

| Known additive V2 filename | Classification |
| --- | --- |
| `strict_contract_v2.py` | Opt-in V2 contract |
| `v2_cache_fencing_lab.py` | Synthetic/cache fencing research |
| `v2_cache_partition_plan.py` | Partition planning |
| `v2_cloud_publish_verify_lab.py` | Cloud publication/verifier research |
| `v2_cloud_ref_witness_plan.py` | GitHub witness planning |
| `v2_provider_readiness.py` | Provider readiness |
| `v2_replay_port.py` | V2 replay contract |
| `v2_source_adapter.py` | V2 source adapter |

The new `scripts/mst_remote_legacy_tree_lock.py` runner verifies actual live protected main SHA, fetches both original/main Git commits and full recursive Git tree objects from GitHub, compares every original path/type/mode/object SHA, then compares the candidate's **63 legacy objects exactly** while enforcing an explicit allowlist for the 8 V2 module paths. The sidecars are not being promoted to V1 or considered behaviorally certified.

The original first strict workflow [#42630657805](https://github.com/ngluonghoa/MST/actions/runs/42630657805) **FAILED BY DESIGN of an overly broad candidate invariant**: it found 8 additive V2 modules inside `src/swing_trading/`. GitHub cross-check proved none of the 63 original V1 modules had been changed or deleted. The validator was refined to explicitly allow **only** the 8 already-known V2 paths, while rejecting unknown files, legacy mutations, deletion, mode changes, fake Git SHA, invalid tree, source drift and moved/unprotected live main. This is not a security bypass: the strict gate now implements the actual source-lock promise (preserve V1, add opt-in V2).

Files:
- `scripts/mst_remote_legacy_tree_lock.py`.
- `tests/test_mst_remote_legacy_tree_lock.py`, 29 targeted synthetic negative/positive controls.
- `.github/workflows/mst-remote-legacy-tree-parity.yml`, GitHub-hosted read-only remote upstream/main/live PR audit, `contents:read`, exact PR #8 only, temporary JSON artifact.

**What a PASS proves:** original MST main full tree equals original Swing source and 63 original V1 modules on PR8 have exact Git bytes; eight recognized V2 additive files are present. **What a PASS does NOT prove:** 1:1 V2 behavioral/ABI parity, all 63 A02 manual owner dispositions, licensed market feed clocks, actual physical Drive cache, real G01 signer root, G02 independent floor, or production release/trading authorization.

## 4. Security gates and next actionable steps

| Workstream | Evidenced today | Required to advance |
| --- | --- | --- |
| A02 source preservation | Full original/main tree and V1 candidate bytes objectively verified | Owner per-module 63 dispositions, ABI and behavioral parity before signoff |
| M4 G01 | No approved independent signer, only role proposal | Owner-controlled root/issuer identity, independent revoker and actual signed registry |
| M4 G02 | Protected main GitHub policy exists, but owner/admin reset threat unverified | Separate effective controller/root/bypass graph, independent durable high-water witness and tamper response |
| M4 G03 | Hypothetical two-writer CAS tests only | Two genuinely separate authenticated low-privilege GitHub writers |
| M4 G04/G05 | Drive staging/metadata visible; no approved vendor bytes | SSI/DNSE/VCBS licensing, first-known/correction rights, real Drive byte SHA and crash recovery |
| M4 G06/G07/G08 | Review-only attestations and canonical docs | Global revocation; external evidence tiers; owner A02/A03/M3/M4/M8 signoffs |

**Priority choice:** Do not accumulate synthetic M4 security gates in lieu of an independent owner root. Keep G01–G08 **OPEN** and continue work permitted without elevated access, especially **A02 full source-lock and V2 behavioral/ABI parity**. A real witness ruleset/ref or a distinct signer is a **separate privileged owner decision**, not implied by choosing GitHub+Drive. If the owner can only operate with a shared privileged controller, record the G02 limitation as OPEN/NO-GO rather than lower the acceptance standard or add another cloud service without user consent.

## 5. GitHub-hosted evidence and durability limits

- [First corrected remote full-tree run #42630989382](https://github.com/ngluonghoa/MST/actions/runs/42630989382) **SUCCESS**: `original_git_tree_entry_count=216`, `original_git_blob_count=208`, `original_python_module_count=63`, `approved_opt_in_v2_sidecar_module_count=8`, `all_original_tree_entries_match_between_source_and_main=true`, `inherited_python_source_unchanged_on_pr=true`, all production/owner gates false. [Temporary artifact 13680527890](https://github.com/ngluonghoa/MST/actions/runs/42630989382/artifacts/13680527890).
- A follow-up hardened the remote check to require the **current** main branch is both protected and exactly pinned; source behavior remained unchanged. See exact-HEAD workflow evidence when this report is finalized.
- GitHub Actions artifacts are 14-day review copies, **not** durable independent signed floors or valid producer rights.
- Never merge Draft PR #8, modify `main`/rulesets/witness ref, grant owner keys/Drive sharing, or trade based on this source-only evidence.

**Disposition:** `REMOTE_SOURCE_1TO1_LOCK_PASS; OPTION_A_ADMIN_ROOT_INDEPENDENCE_UNVERIFIED; G01_G08_ALL_OPEN; PR8_DRAFT; M5_M8_BLOCKED`.

## 6. Hosted QA status after hardened live-main guard and corrected assertion

At code HEAD `997180580c4e512ad5c6a5930a539d4dec956ce7`, [Foundation CI #42631740281](https://github.com/ngluonghoa/MST/actions/runs/42631740281) **SUCCESS 3/3** (Python3.11 **1985/1985**, Python3.12 **1985/1985**, engineering **63/63**, H2/H3/lint/wheel PASS). [Live GitHub remote full-tree source audit #42631740484](https://github.com/ngluonghoa/MST/actions/runs/42631740484) **SUCCESS**, current main protected and pinned, original tree 216 Git entries, 208 blobs, 63 unchanged V1 Python objects, exactly 8 V2 additions allowed. Other eight workflows SUCCESS: **10/10 exact-code-head PASS**. A temporary GitHub artifact retains the source tree receipt only for the configured CI retention; it does not count as owner-signed custody.

The first full-tree design rejected all extra modules, and was corrected after real GitHub identified the eight pre-existing opt-in V2 sidecars. The next Foundation run failed one *test assertion on expected status text* (the security evaluator itself still passed live remote verification); the test assertion was corrected without altering acceptance. Latest full source/parity and Foundation CI both PASS.

[Google Drive QA — Option A administrator-root feasibility and 1:1 source evidence](https://docs.google.com/document/d/1IpFra3Xu4nVDizjB6w6iZjwFYkjT-hi3sKALiD11l7c/edit) resides in the MST `02_QA_RELEASE_EVIDENCE` folder. This documentation-only update creates another PR head and must be separately rechecked before calling that final head green. All G01–G08 external owner/production gates remain OPEN.
