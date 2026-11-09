# MST M4 — Cross-service publish/read barrier and Cloud witness recovery (ADR candidate)

**Status:** OPT-IN V2 SYNTHETIC LAB / NO REAL GOOGLE DRIVE DATA WRITES / NO LIVE PROVIDER RIGHTS / NO RELEASE APPROVAL  
**Owner gate:** [M4 Issue #10](https://github.com/ngluonghoa/MST/issues/10)  
**Branch:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), `main` unchanged and exact 1:1 Swing Trading 1.8 at `4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.

## Decision: use a deny-by-default read barrier; do NOT treat two cloud services as one atomic store

Google Drive may eventually store licensed immutable candle chunks if the *actual* SSI/DNSE/VCBS agreement permits Cloud persistence. A separately authorized private GitHub control repository/ref might eventually record a single current manifest digest, but GitHub ref advancement and Drive chunk publication are **two different operations with no shared atomic transaction**. Never infer safety solely from a successful Git ref update.

The Cloud-only candidate `src/swing_trading/v2_cloud_publish_verify_lab.py` adds a **pure Python metadata classifier**, not a GitHub/Drive connector. It accepts typed but *caller-supplied* Git ref, commit, chunk and optional reader-floor observations and classifies which consistency check would fail. It cannot independently attest source, GitHub App identity, account entitlement, Drive object bytes, signed metadata or monotonic floor. Thus **EVERY result**, including `CONSISTENT_CLAIMS_UNATTESTED`, has `licensed_drive_read_authorized=False`, `drive_write_authorized=False`, `trading_authorized=False`, `distributed_atomicity_verified=False` and `independent_source_verified=False`.

### Expected future publish transaction stages — conceptual only

1. **M3 gate:** verify actual provider/account right-to-read, right-to-retain on Google Drive, permissible derived indicators/backtests and exact endpoint/timeframe/rate/window. Never copy real rights secrets/licences into public MST GitHub.
2. **Authenticated writer:** obtain independent Cloud-only per-scope identity, authorize a *private* protected control-ref target and provider-specific Drive partition. Deny untrusted direct writes, external force updates, deletion and bypasses.
3. **Immutable chunk:** stage an allowed content-addressed object under the correct source/endpoint/ticker/timeframe/date/RAW-vs-ADJUSTED/revision partition; independently check the object bytes/hash/source provenance and canonical version schema. An upload alone must not make it visible to readers.
4. **Control candidate:** construct a Git commit with exactly one parent equal to the last independently observed control head, bind generation, canonical manifest hash, source rights/provenance/floor, and stage only privacy-approved metadata. Use `force=false` and verify protection for the exact ref; `expected_sha` client preflight is not atomic by itself.
5. **Ambiguous commit outcome:** on any 409, 422, 5xx, connector `UNKNOWN`, timeout or lost response, never retry blindly as an assumed success. Read Git ref and independently inspect commit parent/tree/manifest, then reconcile with actual immutable Drive chunk. If not provably consistent, mark **INDETERMINATE/QUARANTINED** for authorized review.
6. **Reader barrier:** require an *authorized* source and publisher, authenticated current ref, exact commit/parent/tree, matching partition+manifest, independently fetched immutable chunk/checksum, valid source time/revision and a durable, independently protected rollback floor. Reject missing/pending chunk, competing ref, parent fork, stale floor or revoked/expired rights. No silent SSI→DNSE/VCBS switch or last-good source downgrade.
7. **Recovery:** orphaned Drive chunks following unsuccessful control promotion remain invisible to readers, are tracked by an authorized lifecycle and eventually cleaned up only in compliance with vendor retention/revocation terms. Rollback publishes a **new generation** referencing last-good contents, not a force-push/head rewind. Deny read if a protected floor or signed lineage cannot be independently checked.
8. **Operational acceptance:** run real authorized Cloud staging negative tests for two or more independent writers/accounts, direct out-of-band Git ref mutations, protected rulesets, actual chunk tampering, post-upload/pre-ref crash, post-ref/pre-response crash, source revocation, quota/rate limits, leaked private metadata and N/N−1 recovery. These remain **NOT PERFORMED**.

### Fault matrix — target behavior

| Fault | Candidate reader/producer behavior | Current verification |
| --- | --- | --- |
| Drive upload succeeds, Git ref update fails | Orphan chunk not readable through current head | Simulated only |
| Git ref advances, chunk missing | Deny read, quarantine | Synthetic test |
| Git ref points at competing/unknown commit | Deny promotion | Synthetic test |
| Commit parent, tree or partition does not match | Deny read | Synthetic test |
| Manifest/generation differs from control proposal | Deny read | Synthetic test |
| Chunk digest or source partition mismatch | Deny read | Synthetic test |
| Reader floor higher or equal with conflicting manifest | Deny replay/downgrade | Synthetic test, floor not signed |
| Opaque GraphQL connector error on competing writer | Read ref/commit rather than claim CAS success | Real GitHub lab + synthetic behavior |
| Forked commit from current head with `force=false` | Non-fast-forward update rejected | Real test-only GitHub ref attempt, error named `UNPROCESSABLE rejecting non-fast forward update` |
| Two independent in-memory witnesses | Conflicting heads can both succeed | Negative synthetic demonstration |
| Vendor data rights expired / externally revoked | Block all real use | No real entitlement proof; default denied |

## Real test-only GitHub ref evidence (follow-up)

Separate **unprotected** lab ref `mst/m4-ref-cas-lab-20261109` is left at `869b64d348b88ceb272408d1a1dabd668ba720d6` (parent `39263a20f9f39cef047968f5f154943aec99c4b6`), with competing old-parent commit `4d089017ffad2a6989e705a7a295ff28ff7b9cc7`. The initial simultaneous BETA attempt returned opaque internal GraphQL error, reason unknown. Follow-up used the **correct current expected head** but tried to set the ref to that BETA fork, `force=false`; GitHub returned `UNPROCESSABLE: rejecting non-fast forward update`. Fresh independent ref readback showed the head unchanged. This supports non-forced fast-forward ancestry on this unprotected test branch **but does not prove cross-service or multi-account production CAS**.

No market payloads were used: the lab commits all point to the exact original source Git tree. No force push, source change, data ingestion, Drive chunk write or merge to `main`.

## Code and tests now staged on Draft PR #8

- `v2_cloud_ref_witness_plan.py`: prior 20 proposal/ref readback tests, always deny actual writes.
- `v2_cloud_publish_verify_lab.py`: new pure metadata observations `FixtureGitCommitObservationV2`, `FixtureDriveObjectObservationV2`, `FixtureReaderFloorV2`, and `audit_fixture_cloud_publish` with states: `REF_NOT_PROMOTED`, `REF_COMPETING_OR_UNKNOWN`, `COMMIT_LINEAGE_MISMATCH`, `COMMIT_TREE_OR_PARTITION_MISMATCH`, `MANIFEST_OR_GENERATION_MISMATCH`, `DRIVE_OBJECT_NOT_READY`, `DRIVE_OBJECT_DIGEST_MISMATCH`, `REPLAY_FLOOR_REJECTED`, `CONSISTENT_CLAIMS_UNATTESTED`.
- `tests/test_m4_v2_cloud_publish_verify_lab.py`: 27 new fake-metadata tests covering all listed states, strict type/UTC/digest inputs, no falsely inferred rights and direct-constructor changes. The GitHub Actions suite is offline and never makes remote API calls.
- The original **63 inherited source Python files**, plus original `pyproject.toml`, remain Git-blob SHA pinned by `tests/test_m2_a03_legacy_blob_parity.py`. Candidate branch now has 71 Python modules (63 originals + 8 opt-in v2). H3 rough static detector may mark the new barrier `IMPROVE/HIGH_BRANCH_SCORE` for manual review; it is not a signed defect report.
- Previous 1,503 tests + 27 new tests = **1,530 unittest cases per Python 3.11/3.12**, plus engineering suite 63, H2/H3 and packaging. Cite the **current exact PR HEAD** CI results before promotion; passing tests provide no production data rights.

## Explicit unresolved gates

`M4_PRIVATE_PROTECTED_CONTROL_REPOSITORY=OPEN`; `M4_WRITER_IDENTITY_SIGNING=OPEN`; `M4_MULTIPARTITION_CAPACITY_AND_PRIVACY=OPEN`; `M4_REAL_DRIVE_CHUNK_INTEGRATION=NOT_IMPLEMENTED`; `M4_DURABLE_INDEPENDENT_FLOOR=OPEN`; `M4_CROSS_SERVICE_ATOMICITY=NOT_PROVEN`; `M3_VENDOR_RIGHTS=UNVERIFIED`; `M4_PRODUCTION_AUTHORIZATION=NO`; `PR8_MERGE=NO`. Main remains the exact immutable source baseline.

**Tracking:** [M4 Issue #10](https://github.com/ngluonghoa/MST/issues/10), [M3 Issue #9](https://github.com/ngluonghoa/MST/issues/9), [A03 Issue #6](https://github.com/ngluonghoa/MST/issues/6), [A02 Issue #4](https://github.com/ngluonghoa/MST/issues/4).
