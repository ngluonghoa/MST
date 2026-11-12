# MST M4 — Two parallel-issued real GitHub non-force ref update experiments

**Date:** 2026-11-09, Vietnam. **Status:** Real remote GitHub Git-data test and independent read-only Actions verification. **NOT** multi-account CAS signoff, privileged branch-protection test, protected rollback-floor approval, real Google Drive cache or licensed market-data publication. Work occurs **Cloud-only** on GitHub and Google Docs.

## Source-locked boundary

- Swing Trading 1.8 original source pin: commit `cd90c1babae8912db31490ad614fc2ad2f868042`. MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, all **63 inherited original Python module Git blobs unchanged**; `pyproject.toml` unchanged. Keep [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8) open/unmerged. No live provider or production Drive access.
- These trials extend [Handoff §40's sequential non-force experiment](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_M4_REAL_GITHUB_FAST_FORWARD_EVIDENCE_20261109.md). They do not replace earlier M4 audit cases.
- Only synthetic JSON metadata files were committed on **two separate isolated test branches**, never to `main` or the production cache branch. Each new candidate's exactly one parent is baseline `P=4048f91beaaa3410116d97e35896c8b688384e19`. All mock rights/writer/Drive flags are explicitly false.
- Each experiment's client invoked `Promise.allSettled([update_ref(childA, force=false), update_ref(childB, force=false)])` in ONE JavaScript orchestration call. There was no `expected_sha` parameter (avoid confusing a connector-side precheck with server CAS). Both operations were **issued in parallel from the same connected GitHub account**. The tool/transport may serialize requests; this is **NOT** proof their packets reached GitHub concurrently. The authoritative outcome is the remote GitHub update result and later ref GET.

## Two real isolated experiments and results

| | Trial r1 | Trial r2 |
| --- | --- | --- |
| Isolated ref | `refs/heads/mst/m4-witness-test-only/race-20261109-r1` | `refs/heads/mst/m4-witness-test-only/race-20261109-r2` |
| Initially read head | `P` | `P` |
| Candidate A commit | `eb74a8c9cbfaa1fc6376b9b02ff837bfb7e7b19f` | `8cf9b8340de70422ff7ecc714d11b172df438273` |
| Candidate B commit | `98d01322aa057de429f4cf24afb9ecbd7ee1ae13` | `3487a1c08faa404aab311ff6fff719f8ba9b8b6a` |
| Winner | **A**, non-force REST update succeeded | **B**, non-force REST update succeeded |
| Loser | B, GitHub HTTP **422** `Update is not a fast forward` | A, GitHub HTTP **422** `Update is not a fast forward` |
| Final remote ref GET | `eb74a8c9cbfaa1fc6376b9b02ff837bfb7e7b19f` | `3487a1c08faa404aab311ff6fff719f8ba9b8b6a` |

Git commit/tree evidence:
- r1 winner A tree `ff390765d3e21a89be29167e39607dbd5be59565`, loser B tree `80f999f5dfe28a47699e417f275f37ad517b1372`.
- r2 winner B tree `0a1dc89f5f284b7e9891da4d75ec8f4be46ce027`, loser A tree `bd44cd6315d178a179b023977b508558129699c4`.
- All **four** commits have precisely one identical original parent `P`. The file `docs/MST_M4_GITHUB_REMOTE_CONCURRENT_REF_TEST_ONLY.json` differs between candidates. No original source blob was changed.

## Independent external remote evidence

New Draft-PR-only components:
1. `scripts/m4_github_parallel_ref_readback.py`: strictly validates r1/r2 ref head, both candidate commit SHA1s, exactly one shared parent and correct individual tree SHA. Live usage is **GitHub REST GET only** via the GitHub-hosted runner's read-only token. It explicitly emits eight false authority flags, including `distributed_multiaccount_cas_proven`, `simultaneous_server_arrival_proven`, `server_http_422_proven_by_readback_alone`, `independently_protected_rollback_floor`, `real_google_drive_payload_verified` and `trading_authorized`.
2. `tests/test_m4_github_parallel_ref_readback.py`: **11** newly added source-locked negative/positive tests over both trials: wrong trial, branch, unexpected head, noncommit ref, winner/loser SHA/parent/tree mismatch, multi-parent and wrong typed shape, fail-closed authority.
3. Updated `.github/workflows/m4-github-ref-readback.yml`: added second **read-only**, same-repository gated GitHub Actions job (no write token), preserving prior §40 test job and `permissions: contents: read`.

[Read-only hosted workflow #42590248216](https://github.com/ngluonghoa/MST/actions/runs/42590248216) **SUCCESS 2/2**: first job verified original sequential test ref, second job independently fetched six remote resources (r1/r2 ref + two commit objects each) and emitted **two** `REMOTE_GITHUB_PARALLEL_ATTEMPT_REF_READBACK_VERIFIED_UNATTESTED` receipts with r1 head A and r2 head B, matching the connector update results. The separate read-only receipt **does not** attest the HTTP 422 responses; those were separately observed during actual connector write calls.

[Foundation CI #42590248215](https://github.com/ngluonghoa/MST/actions/runs/42590248215) **SUCCESS 3/3**: Python 3.11 **1,630/1,630** unittest, Python 3.12 **1,630/1,630**, engineering **63/63**, H2/H3/lint/wheel PASS. [Cross-run synthetic cache workflow #42590248329](https://github.com/ngluonghoa/MST/actions/runs/42590248329) **SUCCESS 2/2**. These are code/workflow-head results from commit `fd5938da679f7d2fe9fc2ca40d5fd9e3c1105986`; verify final report-containing HEAD's own runs before marking the final checkpoint.

## Measurable gates and remaining gaps

- **M4-REF-G01 — PASS, narrow:** *actual* GitHub non-force fast-forward validation rejects a sibling overwrite under both parallel-issued request batches; each test ref ends at exactly one of the two siblings.
- **M4-REF-G02 — PASS, narrow:** independent GitHub-hosted read-only job re-GETs both ref heads and each candidate's parent/tree; no production permissions are granted.
- **M4-REF-G03 — PARTIAL:** two parallel-issued calls from *the same GitHub connected account* produced one accepted update and one HTTP 422 in each of two rounds. **OPEN:** genuinely separate authenticated writer accounts, simultaneous attempt timing at server, server-side conditional compare-and-swap/linearizable winner election across actors and crash/retry cases. It would be unsafe to grant a write-scoped `GITHUB_TOKEN` to unreviewed PR-controlled workflows just to manufacture an apparent multi-account race.
- **M4-REF-G04 — OPEN:** ensure branch protection/rulesets (including force/delete/recreate and admin bypass) actually enforce the intended invariant for the future protected witness ref. The present isolated test ref is not protected authority.
- **M4-REF-G05 — OPEN:** independently signed/verified per-partition+rights-policy monotonic head/floor, vendor source/first-known clock and authorized recovery, durable across runner/account changes.
- **M4-REF-G06 — OPEN:** real physical Google Drive chunk bytes SHA256, licensed SSI/DNSE/VCBS entitlements and retention, independently authenticated GitHub+Drive signer/custody, stage/publish crash recovery, cross-account revocation.

**No promotions:** `SIMULTANEOUS_SERVER_REQUESTS_PROVEN=NO`, `TWO_DISTINCT_WRITER_ACCOUNTS_PROVEN=NO`, `PROTECTED_EXTERNAL_ROLLBACK_FLOOR=NO`, `REAL_DRIVE_CHUNK_READBACK=NO`, `M4_RELEASE_APPROVED=NO`. A02 63 manual final owner-approved module dispositions, A03 ABI Issue #6, M3 real provider rights and M4 Issues #10/#13/#14 remain OPEN. M5/M8 live trading and production release blocked. Keep every existing original source module and main commit pinned, PR #8 Draft/unmerged.
