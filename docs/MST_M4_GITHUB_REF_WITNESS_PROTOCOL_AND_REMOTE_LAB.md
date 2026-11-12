# MST M4 — GitHub reference witness candidate: Cloud-only optimistic publish

**Status:** LAB_SOURCE_AND_REMOTE_METADATA_TEST_PASS_PARTIAL / NO_DISTRIBUTED_DRIVE_TRANSACTION / NOT_APPROVED_FOR_LIVE_DATA  
**Implementation branch:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8)  
**Immutable v1 source:** MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` exactly matching pinned Swing Trading 1.8 commit `cd90c1babae8912db31490ad614fc2ad2f868042`.

## 1. Candidate decision — GitHub ref as *control plane*, Google Drive as *data plane*

MST requires Google Drive for data cache, but Google Drive ordinary file overwrites do **not** provide a proven general distributed compare-and-swap that can arbitrate two independent writers and out-of-band operations. A separate GitHub Git branch/ref is an interesting **candidate witness** because [GitHub REST Update a reference](https://docs.github.com/en/rest/git/refs#update-a-reference) documents `force=false` as a fast-forward-only update. A Git ref update has one server-side current pointer, and a second fork created from the same old parent is not an ancestor-descendant continuation. The **optional connector `expected_sha` preflight is not a substitute for the server's fast-forward constraint**; do not use `force=true` or treat client-side check/read as a durable CAS.

**Critical qualifications:**
- This only helps serialize one Git ref's ancestry *if* GitHub server enforces non-forced fast-forward updates, the correct ref is used and unauthorized writers cannot modify/delete it. It does NOT authenticate manifest contents, data source licences, GitHub App writer identity, account privacy or legal storage permissions.
- Updating a Git ref and uploading a Google Drive chunk are **two different services and not an atomic two-phase transaction**. Crash after Drive upload may leave an orphan immutable chunk; crash or ambiguous error after Git ref update requires independent ref/commit readback and reconciliation before any readers see new data.
- The repository `ngluonghoa/MST` is public. Production cache control metadata might reveal private portfolio symbols, scan cadence, vendor identity or positions. A distinct access-controlled private GitHub control repo (or a separately assessed protected control strategy) needs explicit owner/privacy approval. Do NOT create real cache metadata refs in the public MST repo.
- Branch count, API quota, request burst limits and 5-minute scans across multiple symbols/timeframes must be measured. One branch per partition is a **LAB proposal**, not a proven production-scaling architecture. Consider sharded metadata logs or dedicated private control repo after authorization.
- A GitHub branch name protected for `main` does not prove all new dynamic `mst/m4-witness-*` refs are protected. Exact ruleset scope, authorization/write identity, bypass list, force-push prevention, deletion prohibition, and negative access tests MUST be verified on the actual control refs.

## 2. Actual Cloud-only Git ref probe — metadata only, NO Drive data

A separate **unprotected, test-only** branch was created in GitHub: `mst/m4-ref-cas-lab-20261109`, from exact original `main@4048f91beaaa3410116d97e35896c8b688384e19`. The test made three empty-tree Git commits (all point to original tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`), without source file changes or market data:

- Competing writer ALPHA commit `39263a20f9f39cef047968f5f154943aec99c4b6`, parent `4048f91beaaa3410116d97e35896c8b688384e19`.
- Competing writer BETA commit `4d089017ffad2a6989e705a7a295ff28ff7b9cc7`, **same original parent**.
- ALPHA `update_ref(force=false, expected_sha=original)` reported success; BETA's competing update returned `GithubGraphQLAPIError: Something went wrong while executing your query`, an **opaque server/connector error**, NOT a clean verified 409/non-fast-forward reason. A subsequent BETA retry likewise returned an opaque error. Branch readback after this step showed ALPHA's commit and NOT BETA's.
- Next ALPHA descendant commit `869b64d348b88ceb272408d1a1dabd668ba720d6`, parent `39263a20f9f39cef047968f5f154943aec99c4b6`, updated the same ref via `force=false` and expected ALPHA head, returning success.
- Independent final readback of `refs/heads/mst/m4-ref-cas-lab-20261109` showed head `869b64d348b88ceb272408d1a1dabd668ba720d6`; Git commit API confirmed direct parent chain `original → ALPHA → ALPHA-child`. BETA is a separate fork but never became the observed head.

This is **evidence that the Cloud API update/readback path works for a metadata-only lab and observed one conflicting candidate fail to advance**, but NOT a robust, instrumented concurrent-stress proof of linearizable CAS across accounts, and NOT evidence of a production protected ref. Error handling MUST distinguish known 409/422 from opaque 5xx/GraphQL unknown, which remains INDETERMINATE until verified against independently authenticated fresh readback and commit lineage. Preserve this lab branch for QA audit; no force update, deletion or merge to `main` was performed.

## 3. Proposed future publish protocol — design only

1. M3 validates account-specific vendor entitlement and explicit Google Drive **retention, derived indicators and backtest rights** before any network call, data cache read or write; independently verify provider time, source revisions and calendar.
2. A Cloud writer authenticates to a separately protected GitHub **control** namespace and authorized Google Drive folder. No credentials in public repo, no Mac/MOCHI/local compute or secret management.
3. Reader fetches the current trusted Git ref and its signed/authorized manifest commit, validates tree schema/partition hash/generation/provider rights, checks an externally protected anti-rollback floor and read-only previous-head lineage.
4. Writer uploads a new, immutable **rights-eligible** content-addressed chunk to an isolated Google Drive partition, independently reads/verifies checksum and source provenance. Never overwrite existing chunks.
5. Writer constructs one new Git commit whose **single expected parent** is the last observed control ref head and whose tree binds canonical manifest digest and source metadata. No Git merge commit, shortcuts, force update or silent provider fallback.
6. Writer calls GitHub Update a reference with `force=false`, `expected_sha=<observed-head>` as optional local preflight, always relying on server fast-forward ancestry. On conflict/unknown error, **DO NOT mark success**; independently fetch ref + commit tree/parent (not just ref SHA) and evaluate source rights/manifest generation against durable state.
7. Reader promotes only after authorized ref, immutable Drive chunk, independent version-floor/replay guard and source rights all match. If control ref points at a missing/unauthorized chunk, fail closed, do not fall back to an older or alternative provider silently. Orphan chunks from failed updates require controlled expiry/cleanup with retention compliance.
8. Demonstrate 2+ simultaneous writers, process crash before/after Git ref update, stale writers, ambiguous GitHub errors, force-push from external user, branch deletion, out-of-band Drive changes, revoked vendor rights, stale/unsigned manifest and source identity collision using real authorized Cloud staging before production.

## 4. Python contract and tests

`src/swing_trading/v2_cloud_ref_witness_plan.py` is an **offline versioned protocol sketch**:
- `FixtureGitRefProposalV2` requires canonical partition SHA256, exact 40-hex Git head/new SHA/parent values, direct candidate-parent equality to expected head, positive generation, explicit opaque writer ID, UTC; the produced `update_intent` always has `force=False`.
- `FixtureGitRefReadbackV2` requires exact TEST_ONLY source partition branch namespace, 40-hex observed head and timestamp not older than proposal.
- `reconcile_fixture_ref` classifies observed candidate, unchanged old head or competing/unknown head. **All classes explicitly deny live licence, Cloud writes and independent CAS certification** even if the observed SHA equals the proposed SHA. The result is not independently authenticated GitHub evidence.
- `tests/test_m4_v2_cloud_ref_witness_plan.py` has **20** synthetic tests for same-parent forks, forced/non-force intent, Git hex identity, expiry/UTC and type controls, source partition separation, ambiguous readback and fail-closed cases.

Together with inherited/earlier tests, candidate CI should be **1,503 tests** each Python 3.11/3.12, engineering 63, H2/H3 source matrix 70 modules (63 legacy pinned blob SHA + 7 new opt-in v2), lint/wheel. Must cite exact HEAD final GitHub Actions run after all updates. All tests are fixture-based; the one real ref lab is separate manual Cloud API evidence and NOT automated in regular CI.

## 5. Acceptance gates / rollback

- `M4_GITHUB_TEST_ONLY_REF_UPDATE=OBSERVED_SUCCESS_ALPHA_AND_CHILD`
- `M4_COMPETING_WRITER_BETA=OPAQUE_GRAPHQL_ERROR_NOT_A_CERTIFIED_409`
- `M4_REF_READBACK_PARENT_CHAIN=OBSERVED`
- `M4_DURABLE_PROTECTED_REF_CAS=UNPROVEN`
- `M4_INDEPENDENT_WRITER_IDENTITY=NOT_IMPLEMENTED`
- `M4_DRIVE_ATOMIC_CROSS_SERVICE_PUBLISH=NOT_POSSIBLE_FROM_GIT_REF_ALONE`
- `M4_LICENSED_DRIVE_DATA_RETENTION=NOT_AUTHORIZED`
- `M4_PRODUCTION_CACHE_AND_RELEASE=BLOCKED`

Do not change MST protected `main`, never merge this lab branch. Draft PR #8 may be closed unmerged before owner acceptance, leaving exact v1 source baseline intact; future authorized releases require protected PR, new full CI, signed domain separation and N/N−1 consumer rollback.

**Issue tracking:** [M4 #10](https://github.com/ngluonghoa/MST/issues/10) for distributed cache control and data plane; [M3 #9](https://github.com/ngluonghoa/MST/issues/9) for provider licences/Cloud credentials; [A03 #6](https://github.com/ngluonghoa/MST/issues/6) for opt-in versioned contracts; [A02 #4](https://github.com/ngluonghoa/MST/issues/4) for 63-module final signoffs.
