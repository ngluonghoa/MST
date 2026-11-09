# MST M2/A02 — W2/W3 scoped manual security review: custody-head and cache forks

**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Status:** SCOPED MANUAL INSPECTION / FIVE SYNTHETIC NEGATIVE CONTROLS ADDED / NOT 63-MODULE FINAL SIGNOFF  
**GitHub:** [MST Draft PR #8](https://github.com/ngluonghoa/MST/pull/8). **Do not merge**.  
**Baseline:** `main@4048f91beaaa3410116d97e35896c8b688384e19`; tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, identical to pinned Swing source `cd90c1babae8912db31490ad614fc2ad2f868042`.

## Scope and exact source identity

This review inspects **three original, untouched v1 modules** and relevant tests; additional tests are on the opt-in candidate branch only. No original source file is edited.

| Original module | Pinned Git blob SHA-1 | Source flow and risk |
| --- | --- | --- |
| `provider_head_custody.py` | `d937ea91bb70e811c038fef3fb4d48f2a3f2d662` | Signed self-claimed custody head, self-claimed high-watermark, key rotation and event-chain linkage; risk of treating valid Ed25519 math as authenticated source ownership |
| `partition_chunk_cache.py` | `30f4dd112a42c91905bf9abe95114dc7c58f70d9` | Synthetic content-addressed per-partition chunk and monotonic manifest chain; in-memory `_active`/history, NOT an independent distributed CAS |
| `reference_pinned_fd.py` | `deb5c1ca6ce4bae083a948935ba843ff5819533e` | POSIX dirfd/O_NOFOLLOW read-only path inspection, not a safe subsequent `sqlite3.connect(path)`; preserved exception handling and descriptor lifetime required |

Relevant test consumers: `tests/test_provider_head_custody.py`, `tests/test_partition_chunk_cache.py`, `tests/test_h3_pinned_fd_guard_regression.py`, `tests/test_reference_pinned_signature.py`. Broader imports, full code owners and external client migrations remain subject to A02 final review.

## W2: provider-head custody independent observations

1. `audit_conditional_custody_head` verifies a head signature against a **caller-supplied** `ClaimedCustodianKey`, with freshness against a **caller-supplied** time and floor. `ConditionalHeadAudit` truthy fields such as `relative_floor_held` are *conditional* statements, not authenticated proof of vendor identity.
2. Two distinct heads with valid signatures, the **same sequence** and **different tail digests**, can each satisfy the same old claimed floor when no separately verified complete event chain is supplied. New negative control explicitly demonstrates this fork. It is a missing operational attestation, not a discovered permission escalation.
3. Replaying an older, correctly signed head against a deliberately weaker floor passes local relative checks, but an advanced floor rejects it. This proves that security depends on an **external persistent monotonic anchor**, which this module does not provide.
4. A self-generated Ed25519 key and a matching self-claimed floor can satisfy conditional cryptography while **key origin remains unverified**. Even a manually constructed `ConditionalHeadAudit` with a forged empty `unresolved` tuple cannot grant market rights: `require_authenticated_provider_rights` always raises and all authorization properties stay false.

**Disposition for this bounded review:** preserve original source; retain A02 final approval OPEN. Formalize external vendor key enrolment, writer/custodian identification, signed replay floor and revocation evidence before M3/M4 production admission. Do not promote the legacy source as a Cloud authorization provider.

## W3: original source fixture cache partition independence

1. `SyntheticDrivePartitionIndex` checks content-addressed chunk bytes, per-partition generation and previous-manifest lineage **within one object**. It explicitly labels data `SYNTHETIC_TEST_ONLY` and reports zero real Drive/source API calls.
2. Two independent indexes can accept **different genesis chunks** for the same partition, both with generation 1 and valid local manifests. Each readback succeeds within its own object, but heads disagree. The additional test preserves this counterexample for future M4 architecture decisions.
3. Existing tests cover corrupt/missing chunks, changed identity, bad source/provider, open bars, revisions, stale local head, crash-orphan simulation and 5→20 selected-symbol reuse. These tests are valuable **fixture regressions**, not remote, cross-account or licensed Google Drive verification.

**Disposition for this bounded review:** preserve v1 source and its encoding. M4 requires independently authenticated cloud writer and *protected* ref, antirollback, verified physical Drive bytes and cross-service recovery protocol. No production permission is inferred from a passed test.

## W6: pinned-FD exception audit (existing coverage, no new source edits)

The apparent `SILENT_EXCEPT` H3 flag originates from narrowly catching `FileNotFoundError` for **absent** SQLite sidecars and Git markers. `PermissionError`/I/O failures are not silently swallowed; previously existing `test_h3_pinned_fd_guard_regression.py` exercises this, symlink appearance and file descriptor lifetime. Maintain the deliberate absence semantics. The module itself warns that independently reopening a SQLite pathname can race; it cannot secure arbitrary `sqlite3.connect` calls or qualify Cloud persistence. Review priority and final 63-module dispositions stay OPEN.

## New independent negative/golden tests, zero legacy-source code changes

- `test_same_claimed_floor_allows_two_distinct_signed_forks`
- `test_older_signed_head_replays_against_weaker_self_claimed_floor`
- `test_attacker_enrolled_self_claimed_key_cannot_grant_vendor_rights`
- `test_forged_conditional_report_flags_cannot_grant_permissions`
- `test_two_independent_indexes_accept_conflicting_genesis_heads`

Expected **+5 tests** on top of previous 1536 in each Python 3.11 and 3.12 suite, pending exact-head GitHub Actions validation. Existing 63 v1 Python blob SHA pins and original package metadata remain protected by `tests/test_m2_a03_legacy_blob_parity.py`. No new source modules; H3 remains 71 modules (63 v1 + 8 opt-in v2) and should not change. Test fixtures generate only synthetic local ephemeral SQLite under GitHub hosted CI runners, not user Mac, MOCHI or a persistent local deployment.

## Explicit boundaries and exit gates

- These tests **prove important negative counterexamples**. Their existence does **not** certify external attestation, distributed linearizability, vendor contracts or license rights.
- A02 total inventory 63/63 is verified, but *final* individual owner-reviewed dispositions remain OPEN; this report covers three scoped modules, not blanket signoff.
- M3 real vendor rights, retention on Google Drive, revocation, credential ownership: UNVERIFIED.
- M4 private protected control refs, external signer, durable monotonic floor, Google Drive physical chunks, parallel multiple-account CAS and crash recovery: NOT IMPLEMENTED.
- M2/A03 v2 API/version acceptance, PR #8 merge and production release: NOT APPROVED.
- If these extra negative tests change behavior unexpectedly, revert the test-only additions on the Draft PR. Do not reset, rewrite or force-push protected main. Full CI and QA readback required before promotion.
