# MST M2/A02 W3 — Crash/restart publication journal reference contract

**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Scope:** Synthetic GitHub Actions fixture-only, source-locked A02/V2 contract testing; **NOT** a production cloud publisher, authorized Drive write, cryptographic custody or independent rollback floor.  
**Working branch:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), never merged to main.

## Exact provenance and original source audit

- Swing Trading 1.8 original source commit `cd90c1babae8912db31490ad614fc2ad2f868042`; MST `main@4048f91beaaa3410116d97e35896c8b688384e19` and tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. All original **63 source-locked Python modules** remain identical; `pyproject.toml` unchanged.
- Inspected candidate `src/swing_trading/v2_cloud_publish_verify_lab.py` blob `33aa30fb1a1d3a9010006972deeb088f6898c636`: `audit_fixture_cloud_publish` classifies caller-claimed Git commit/ref/Drive object observations, returns false authorization flags even for consistent claims.
- Inspected candidate `src/swing_trading/v2_cloud_ref_witness_plan.py` blob `a67240de25e25f09369b45213d31ca5f01424d4e`: no GitHub API or cryptographic witness; accepts ref readback metadata claims.
- Inspected candidate `src/swing_trading/v2_cache_fencing_lab.py` blob `f5fdc6d3cbbd235a48887aab0053ce96455c1089`: one in-memory witness; no persistence/distributed locking.
- Grounded existing relevant tests `test_m4_v2_cloud_publish_verify_lab.py`, `test_m2_a02_w3_cross_service_failure_windows.py` and `test_m2_a02_w3_multiwriter_rollback_custody.py`. Added tests ONLY in `tests/test_m2_a02_w3_crash_restart_journal_contract.py`; original v1 and existing opt-in V2 source untouched.

## Journal and restart oracle — deliberately limited

An `EphemeralJournalOracle` exists **only in the new test file**. It writes an operation-ID-keyed compact JSON fixture into a temporary directory of the **ephemeral GitHub Actions runner**, using a local replacement of a `.next` file. Re-instantiating the Python object can read the same file, emulating *one writer process restarting on the same runner*; it does not prove any data survives a different GitHub Actions job, runner, token, service or regional failure. `os.replace`-style local file replacement is NOT a distributed compare-and-swap. The JSON is unsigned, caller-editable, deletable and not an independent source of truth.

Test-only journal phases: `INTENT`, `DRIVE_STAGED`, `GIT_REQUESTED_UNKNOWN`, `REF_OBSERVED`, `DRIVE_VISIBLE`, `FINAL_REF_OBSERVED`. These are artificial milestones, **not** real remote operations; the only program under evaluation for publish read outcomes is original `audit_fixture_cloud_publish` with fake metadata.

## Eleven deterministic acceptance / negative tests

| Test case | Actual fixture outcome and assertion | Remaining production gap |
| --- | --- | --- |
| Six crash cutpoints (subtests within one unittest) | Existing opt-in V2 returns `REF_NOT_PROMOTED` before ref changes, `FINAL_REF_READBACK_MISSING` after an opaque Git request / before final verification, `DRIVE_OBJECT_NOT_READY` if ref observed before Drive visibility, `CONSISTENT_CLAIMS_UNATTESTED` even after final claims. No authorization flag ever becomes true. | Independent remote Git+Drive verification and a protected terminal publish receipt |
| Restart after Drive stage | Fixture journal re-loads `DRIVE_STAGED`; Git ref remains old, staged bytes are NOT a successful publication. | Durable staged-orphan cleanup/quarantine and legal retention |
| Restart after opaque Git API result | Journal retains `GIT_REQUESTED_UNKNOWN`; missing final ref or competing ref is blocked. | Recover actual server-side result with authenticated readback and idempotent op ID |
| Restart after Git ref visible but Drive missing | Journal re-loads `REF_OBSERVED`; `DRIVE_OBJECT_NOT_READY` blocks reads. | Multi-service convergence/crash recovery with real physical object bytes |
| Crash after final metadata claim | Journal re-loads `FINAL_REF_OBSERVED`, yet V2 still `CONSISTENT_CLAIMS_UNATTESTED`. | Verified independent signer/rights/floor, NOT synthetic state promotion |
| Repeat same op ID and unchanged fields after restart | Single test file oracle record preserved; phase remains unchanged and bytes reproducible. | **Local journal dedupe is NOT remote exactly-once/CAS** |
| Retry existing op ID with changed payload or partition | Oracle rejects `OP_ID_COLLISION_OR_PAYLOAD_DRIFT`. | Server-protected op ID + payload/owner/partition + policy binding |
| Missing intent, unsupported phase or local phase rewind | Explicit fail-fast in test oracle, phase cannot rewind while file exists. | Authenticated append-only event journal with monotonic event clocks |
| Two different operation IDs claim same parent and partition | Both intents are permitted in local oracle: **no shared linearization**. | One independently observed CAS winner; definitive loser result |
| Delete replaceable local journal after a terminal phase | New oracle accepts the same op ID as fresh `INTENT`, proving **on-runner file cannot be a durable cross-run rollback floor**. | Witness/epoch/head/floor stored independently and protected from caller replacement |
| Supply stricter then weaker/absent reader floor after journal reload | Strong floor blocks; lower or missing caller floor yields only `CONSISTENT_CLAIMS_UNATTESTED`. | Mandatory, signed, canonical partition- and rights-bound un-downgradable reader floor |

## Objective owner-controlled M4 release gates (OPEN)

**CRASH-G01 — Journal write-ahead:** before physical side effect, persist authenticated stable operation ID, writer/epoch, canonical partition+source policy, expected parent Git/ref/head, manifest content digest, source observation clock, and bounded retry/deadline. A fresh new runner can recover it without trusting a caller-supplied file.

**CRASH-G02 — Injection matrix and statuses:** forced termination before Drive stage, after Drive stage, after attempted Git ref write, after unknown API response, after ref visibility before Drive, and after final readback before local receipt. Every resumed run must classify `ORPHAN_STAGED`, `UNKNOWN`, `REF_ONLY`, `DRIVE_NOT_READY`, `COMPETING_WRITER` or `VERIFIED_COMMITTED` based on actual separately authenticated services, never invented success.

**CRASH-G03 — Exactly-once logical publish:** the same op ID and same payload may resume without generating a second new head, source revision or event; the same ID with changed partition/rights/payload is permanently rejected. Different op IDs racing the same protected old head must produce one accepted, non-forced transition.

**CRASH-G04 — Independently protected floor:** per-partition, per-policy signed head/generation/source-clock/epoch floor cannot reset when Actions runner, local files or connected account change. The floor must be **mandatory**, not an optional caller parameter, and updated only by an authenticated writer after physical readback.

**CRASH-G05 — Publication sequencing:** stage immutable authorized Drive chunk, verify **bytes**, update canonical protected Git ref with server-side concurrency control, reread Git ref/tree/commit/manifest plus Drive payload, validate protected floor & rights, commit terminal receipt. Do not allow consumers to read `REF_ONLY` or `DRIVE_ONLY`.

**CRASH-G06 — Provider/rights and historical revisions:** no authentic SSI/DNSE/VCBS source clock, calendar, licensed retention or vendor correction rights are proven. Cross-account revocation and explicit source recovery-of are required; avoid conflating as-of provenance and commit publication time.

**CRASH-G07 — Measurable CI:** Cloud-hosted end-to-end matrix needs independent writer identities, 2+ GitHub hosted runs or genuinely separate concurrent runners, authenticated before/after remote proof, crash points, effective ref updates, actual chunk SHA256, no duplicate accepted generations, proper orphan policy and terminal outcomes. The current **single-run test fixture** does not satisfy this.

**CRASH-G08 — Negative authority receipts:** all synthetic V2 checks remain non-authorizing. No code generation, tests, signed vendor keys, trade execution or cache reader permission may be inferred from `CONSISTENT_CLAIMS_UNATTESTED`, current test journal phases, or an internally consistent digest.

## Evidence and protected next steps

Code-only candidate HEAD `f1702ba9120441ec522eece38dae664c4ab65139`: eleven added fixture-only `unittest` test methods, with a six-cutpoint subtest matrix. The test-containing commit passed [GitHub Actions #42584364283](https://github.com/ngluonghoa/MST/actions/runs/42584364283) **SUCCESS 3/3**: Python 3.11 **1,599/1,599**, Python 3.12 **1,599/1,599**, engineering **63/63**, H2/H3/lint/wheel. Confirm the subsequent report-evidence commit's *own* exact-head CI separately before marking the final checkpoint.

Open blockers: [#14 cross-service floor/reader barrier](https://github.com/ngluonghoa/MST/issues/14), [#13 multiwriter](https://github.com/ngluonghoa/MST/issues/13), [#10 real M4 storage](https://github.com/ngluonghoa/MST/issues/10), [#11 first-known](https://github.com/ngluonghoa/MST/issues/11), [#12 historical-as-of](https://github.com/ngluonghoa/MST/issues/12), A02 63 manual final owner approvals [#4](https://github.com/ngluonghoa/MST/issues/4) and A03 V2 ABI approval [#6](https://github.com/ngluonghoa/MST/issues/6). No real Drive cache, GitHub ref write, signer, source entitlement, data rights, market payload, local Mac/MOCHI compute or production release. Draft PR #8 remains open and unmerged.
