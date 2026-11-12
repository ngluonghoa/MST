# MST M4 — Real GitHub non-force fast-forward rejection and independent hosted readback

**Observed:** 2026-11-09, GitHub connected account + GitHub Actions hosted runner.  
**Scope:** one **isolated test-only Git ref** and two tiny synthetic commits; no vendor data, Cloud Google Drive cache, protected signer or trade.  
**Working governance:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), always unmerged; 63 inherited Swing Trading v1 Python source files and `main@4048f91beaaa3410116d97e35896c8b688384e19` **unchanged**.

## Why this is a materially different result from earlier fixtures

Prior [multiwriter in-memory audit](https://github.com/ngluonghoa/MST/issues/13), [synthetic cross-service read barrier](https://github.com/ngluonghoa/MST/issues/14), and [real inter-run untrusted cache continuity](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_M4_CROSS_RUN_CACHE_PROOF_20261109.md) did not perform a real GitHub remote ref write. This experiment uses authenticated GitHub connector **real Git data create + ref update** actions; it then uses a separate GitHub-hosted Actions run with a **contents:read-only** token to independently re-query the remote ref and its two commits.

## Controlled remote experiment: real Git server, test-only branch

Original `main` (and the exact parent `P`) was already pinned:
- Source baseline `P = 4048f91beaaa3410116d97e35896c8b688384e19`, original tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.
- Fresh isolated branch/ref: `refs/heads/mst/m4-witness-test-only/cas-proof-20261109-1543`. Absence was checked via GitHub GET returning 404 before branch creation.
- Created branch from `P`; verified ref initially pointed exactly to `P`.
- Two distinct tiny **invented metadata** Git blob objects, with all authority flags false, were committed to different trees derived from original source tree; both candidates had EXACTLY ONE identical Git parent `P`. No legacy source files touched:
  - [Candidate A commit `c3e4e91670766d416d9eaedfce36ba12189a9427`](https://github.com/ngluonghoa/MST/commit/c3e4e91670766d416d9eaedfce36ba12189a9427), tree `e40b8463438eb359145a3d027a7aaa74a8df3a4c`; fixture blob `c19a2f922f1c3cd4b1e85e9798e133904c78583b`.
  - [Candidate B commit `e4faef0f83bc925ec8b511fc1aa5ad321fa79f74`](https://github.com/ngluonghoa/MST/commit/e4faef0f83bc925ec8b511fc1aa5ad321fa79f74), tree `4bd4a4a7585ec54ab668cb327af2a55638aeb376`; fixture blob `1e876339faab5ac1efd893f9208ce0be0e15d3e4`.
- Issued REAL `update_ref(branch, sha=A, expected_sha=P, force=false)`: **SUCCESS**. This connector's `expected_sha` may be a client-side check, so the experiment **does not** claim server-side compare-and-swap based on that parameter.
- Issued REAL `update_ref(branch, sha=B, force=false)` **without an `expected_sha` precheck** so GitHub's server must evaluate the sibling transition. GitHub REST replied **HTTP 422**: `Update is not a fast forward`. This is empirical non-force **server rejection of a non-descendant commit**, NOT evidence that two requests were simultaneous.
- Immediately after, independently fetched GitHub ref: head remained **A**. Fetched both Git commit objects: A and B each have parent `P`, distinct trees, and are siblings. Original PR head, original `main`, and original tree preserved. No branch protection/ruleset, external key custody or forced-write-denial evidence has been established.

**Narrow statement proven:** GitHub server enforced non-force fast-forward ancestry on this isolated, sequentially tested ref. Candidate A was accepted; sibling Candidate B was refused; readback still showed A. It is **NOT** a two-account simultaneous writer race or a lock-free conditional CAS proving no stale lost updates from all writers.

## Independent hosted GitHub Actions readback (real remote GET)

New opt-in candidate files on Draft PR #8:
- `scripts/m4_github_ref_readback.py` uses only GitHub REST **GET** for the exact isolated test ref and its A/B Git commits, through the GitHub-hosted runner's `GITHUB_TOKEN`. It requires `GITHUB_ACTIONS=true`, exact `GITHUB_REPOSITORY=ngluonghoa/MST`, and a PR event. It does not write or request Drive/provider data.
- `.github/workflows/m4-github-ref-readback.yml`: **permissions: contents: read**; only executes for PR #8 from same repository; runner Python 3.12. The workflow is separately triggered on relevant PR file changes.
- `tests/test_m4_github_ref_readback.py`: **10 offline negative/positive tests** for exact ref, A/B SHA, single-parent ancestry, tree integrity, tampering, and all production-authority flags remaining false.

[First independently hosted readback run #42588680589](https://github.com/ngluonghoa/MST/actions/runs/42588680589) **SUCCESS 1/1**. The real GitHub API receipt is `REMOTE_GITHUB_REF_AND_SIBLING_COMMITS_VERIFIED_TEST_ONLY`, with `observed_head=A`, `losing_candidate=B`, `shared_parent=P`. Its field `remote_non_fast_forward_denial_proven_by_this_read=false` correctly distinguishes the **separate connector write's HTTP 422** from a mere read-only observation.

[Same candidate HEAD Foundation CI #42588680575](https://github.com/ngluonghoa/MST/actions/runs/42588680575) **SUCCESS 3/3**: Python 3.11 **1,619/1,619**, Python 3.12 **1,619/1,619**, engineering **63/63**, H2/H3/lint/wheel. [Existing cross-run cache workflow #42588680607](https://github.com/ngluonghoa/MST/actions/runs/42588680607) also **SUCCESS 2/2**, with all authority flags false. The report-containing final PR HEAD must be separately checked against Foundation and new read-only workflow.

## Honest boundary and next measurable gates

1. **M4-REF-G01 (PASS, narrow):** real GitHub server prevents sibling non-force fast-forward overwrite on isolated ref, with A success, B HTTP 422, A unchanged after readback.
2. **M4-REF-G02 (PASS, narrow):** separate GitHub-hosted read-only job rereads the exact ref and both commits, verifies head and ancestry. This job does **not** attest that the prior API write rejected B; the two independent observations are separately recorded.
3. **M4-REF-G03 (OPEN):** independently authenticated actual 2-writer **simultaneous** race against same old head, server-side conditional compare-and-swap/linearization, across different authorized actors and runner identities, with exactly one final accepted head and repeatable race/fault-injection logs.
4. **M4-REF-G04 (OPEN):** protect no-force invariant against alternate credentials, force updates, branch deletion/recreation, ruleset bypass and admin privilege changes. Existing *unprotected test ref* must not be misrepresented as independent immutable witness.
5. **M4-REF-G05 (OPEN):** independent, durable, signed **per-partition/rights-policy** monotonic floor and source-clock proof, with old-payload/backdated generation/recovery guard from Issues [#11](https://github.com/ngluonghoa/MST/issues/11), [#12](https://github.com/ngluonghoa/MST/issues/12), [#13](https://github.com/ngluonghoa/MST/issues/13), [#14](https://github.com/ngluonghoa/MST/issues/14).
6. **M4-REF-G06 (OPEN):** physical Google Drive immutable/cache chunk bytes, independent signed publisher/readback, entitlements SSI/DNSE/VCBS, staged-orphan crash replay, no false success, antirollback and retention policy; true M4 Cloud closure requires all these, not just GitHub ref proof.

Every field `vendor_rights_verified`, `source_clock_authenticated`, `google_drive_payload_verified`, `independently_protected_floor`, `distributed_multiaccount_cas_verified`, `production_write_authorized`, `trading_authorized` is **false**. The test ref remains separate from the PR; it has not been merged into main or promoted to provider/Drive permissions.

**Governance:** A02 63 manual per-module owner dispositions OPEN, A03 ABI owner approval [#6](https://github.com/ngluonghoa/MST/issues/6) OPEN, M3 source/legal retention and clocks unverified, M4 operational signed/protected writer missing, M5/M8 no trading/production release approval. Work remained Cloud-only; no Mac/MOCHI/local compute.
