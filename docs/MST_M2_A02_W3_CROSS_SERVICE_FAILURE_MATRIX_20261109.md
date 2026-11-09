# MST M2/A02 W3 — GitHub ↔ Google Drive publish failure windows and partition-floor scoping

**Source-locked scoped audit date:** 2026-11-09. **Scope:** V2 opt-in synthetic-only metadata tests, 63 inherited v1 modules untouched. **Status:** Acceptance candidates only, NOT production Cloud custody proof.

## Immutable baseline and inspected inputs

MST `main@4048f91beaaa3410116d97e35896c8b688384e19` and original 63 inherited Swing Trading 1.8 Python source blobs remain unmodified; source pin `cd90c1babae8912db31490ad614fc2ad2f868042`, Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. No original module/`pyproject.toml` edits and no merge.

Scoped inspected V2 candidate original-on-PR blobs:

| Code | Git blob | Key boundary |
| --- | --- | --- |
| `src/swing_trading/v2_cloud_publish_verify_lab.py` | `33aa30fb1a1d3a9010006972deeb088f6898c636` | `FixtureReaderFloorV2`, `audit_fixture_cloud_publish`: read barrier checks caller-claimed commit, Drive, ref and floor |
| `src/swing_trading/v2_cloud_ref_witness_plan.py` | `a67240de25e25f09369b45213d31ca5f01424d4e` | `FixtureGitRefProposalV2`, `FixtureGitRefReadbackV2`: untrusted metadata-only Git ref intent/readback |
| `src/swing_trading/v2_cache_fencing_lab.py` | `f5fdc6d3cbbd235a48887aab0053ce96455c1089` | In-memory witness; independent multiwriter/CAS/floor limits from [Issue #13](https://github.com/ngluonghoa/MST/issues/13) |

Reviewed existing `tests/test_m4_v2_cloud_publish_verify_lab.py` and `tests/test_m4_v2_cloud_ref_witness_plan.py`. Added **nine distinct chronological negative-path tests** only in `tests/test_m2_a02_w3_cross_service_failure_windows.py`. They call the original opt-in v2 functions; they do **not** substitute an invented real network operation.

## Failure-window matrix: state → expected deterministic reaction → missing production proof

| Fault/observation sequence | V2 synthetic result | Required production gate |
| --- | --- | --- |
| T3 Drive chunk already staged but Git ref still at old head | `REF_NOT_PROMOTED` | Treat staged immutable content as **orphan**, not published; independently authenticated ref promotion required |
| Git ref candidate visible, Drive object absent | `DRIVE_OBJECT_NOT_READY` | No reads/consumer action; retry/rollback/quarantine with bounded recovery |
| Unknown server write outcome; second readback absent | `FINAL_REF_READBACK_MISSING` | Unknown must not be reported as success; independent eventual reconciliation and idempotency key |
| Final readback shows old SHA or competitor after candidate was first observed | `FINAL_REF_CHANGED_OR_UNKNOWN` | One winner under genuine external CAS; loser forbidden from publishing any derived data |
| Final ref initially appears stable, but later separately observed competitor | First snapshot remains `CONSISTENT_CLAIMS_UNATTESTED`, later snapshot `FINAL_REF_CHANGED_OR_UNKNOWN` | Point-in-time metadata claims cannot guarantee future stability; protect head/read lease or use immutable pinned verified version |
| Drive object content digest changes after earlier matching observation | Old snapshot remains `CONSISTENT_CLAIMS_UNATTESTED`, new one `DRIVE_OBJECT_DIGEST_MISMATCH` | Physically immutable chunk identity, authenticated byte-level readback, no stale metadata cache accepted |
| Last ref observation predates Drive/commit observation | `FINAL_REF_READBACK_STALE` | Guarantee ordered post-Drive ref recheck; protect against TOCTOU window |
| Caller may omit/downgrade `FixtureReaderFloorV2` | Returns `CONSISTENT_CLAIMS_UNATTESTED`, not authorized, even with weakened floor; stricter floor rejects lower generation | Floor must be independently protected, mandatory and monotonic per partition |
| Same complete invented observation repeated | Identical immutable report, no transaction/idempotency receipt | Re-running a pure classifier **does not** implement distributed idempotent publishing/recovery |

### Material additional scoping defect: a reader floor is NOT partition-bound

`FixtureReaderFloorV2` has only `min_generation`, `manifest_digest`, `observed_at_utc` and **no `partition_digest`, rights-policy digest, key epoch or independent signer**. The existing verifier correctly checks that commit/Drive/ref claims match the proposal's partition; it **does not** check that the optional reader floor belongs to that same partition. A new regression demonstrates an otherwise internally consistent candidate for unrelated partition B can use the **same** G1 floor originally claimed for A. Both remain `CONSISTENT_CLAIMS_UNATTESTED` with **all rights/atomicity flags false**, so there is NO demonstrated production authorization bypass. But if this fixture type were upgraded without binding the floor to canonical identity and independent custody, the floor could silently guard the wrong partition, or leave a replay window. This is an owner-facing spec/ABI gap, **not a claim that existing project source performs live writes**.

## Proposed objective acceptance criteria (OPEN; no implementation yet)

- **W3-XSRV-G01 — Phase and failure journal:** stage immutable Drive bytes in separate candidate namespace; persist intent with unique globally replay-safe operation ID, expected parent head, canonical partition, signer epoch, rights/retention policy, payload digest and planned generation **before** attempted remote publication. On interruption, fetch durable journal and independently read both services to classify `STAGED_ORPHAN`, `GIT_ONLY`, `DRIVE_ONLY`, `COMMITTED_VERIFIED`, `UNKNOWN_RETRY`, `COMPETING_WRITER`. Never manufacture success on ambiguous timeout.
- **W3-XSRV-G02 — Floor binding:** signed and externally stored per-partition accepted head/floor must bind project, provider, endpoint, instrument, timeframe, basis, calendar, revision namespace, rights-policy digest, manifest generation, commit SHA and observed source timestamp; reject cross-partition transplant and weak-floor omission/downgrade.
- **W3-XSRV-G03 — Exact winner test:** two independent GitHub-hosted writer accounts racing to publish different children of the *same observed protected head* must yield **exactly one accepted protected head**, no false success from losing writer, durable readback after both processes restart. This requires true server-side conditional update/privilege isolation; local fixture CAS is insufficient.
- **W3-XSRV-G04 — Ordered read barrier:** after last Drive byte/hash verification, independently re-read protected GitHub ref + commit parent/tree + partition manifest; reject or retry if any version moved, even if stale readback had matched earlier. Require authenticated source rights/retention and separately attested first-known before data consumers can proceed.
- **W3-XSRV-G05 — Crash replay:** force termination after Drive stage, after Git ref request, during unknown API response, after Git ref promotion before Drive visibility, and just before final ref readback. Each restart must deterministically converge to the one accepted head or fail closed; no duplicate generation, false event chronology or orphan promoted without ownership.
- **W3-XSRV-G06 — Content and time non-regression:** a higher generation/signed manifest alone does not prove current vendor facts; explicitly verify historical correction/restore authorization, independent monotonic source clocks, allowed recovery-of and immutable original as-of payload custody. Relates to [#11](https://github.com/ngluonghoa/MST/issues/11) and [#12](https://github.com/ngluonghoa/MST/issues/12).
- **W3-XSRV-G07 — Rights/revocation and partition changes:** real provider-scoped data access, Drive retention legality, capability/custody epoch and revocation propagation across all accounts; fail closed on old signing key, transferred source namespace or entitlement downgrade.
- **W3-XSRV-G08 — Measurable CI receipt:** publish independently authenticated before/after state, writer and source actor IDs, expected/actual CAS heads, chunk SHA256 from actual bytes, floor revision, crash point and post-restart convergence, with machine-readable pass/fail for all 6 relevant fault phases. Synthetic CI alone may prove classifier behavior, but must never be tagged production-validated.

### CI provenance and limitations

Code-only test HEAD `7d4a0879f4041b1137c7a1a911d93120c4bf2ff9`; [GitHub Actions run #42581401478](https://github.com/ngluonghoa/MST/actions/runs/42581401478) **SUCCESS 3/3**: Python3.11 **1,588/1,588**, Python3.12 **1,588/1,588**, engineering **63/63**, H2/H3/lint/wheel. The code-and-report HEAD `53d2daa0c1a7c26081c902450b9ca10c6fff9d38` separately passed [GitHub Actions #42581685914](https://github.com/ngluonghoa/MST/actions/runs/42581685914) **SUCCESS 3/3**: Python 3.11/3.12 **1,588 each**, engineering **63**. Dedicated [Issue #14](https://github.com/ngluonghoa/MST/issues/14) tracks the partition-bound floor and cross-service recovery gates. Reverify this evidence-only follow-up HEAD before the canonical Drive checkpoint.

**Governance:** A02 63 final owner-reviewed per-module dispositions OPEN; A03 V2 ABI owner acceptance OPEN; M3 actual data entitlement and Google Drive retention/source-clock authenticity UNVERIFIED; M4 protected real GitHub+Drive writer, signed per-partition floor, distributed conditional CAS and crash replay NOT IMPLEMENTED; real market outcomes, M5/M8 release BLOCKED. Draft PR #8 stays unmerged. No Mac, MOCHI, user-local environment, real vendor payload, keys, live Cloud writes or trading.
