# MST M4 — Cross-GitHub-Actions-run test artifact recovery: explicitly untrusted probe

Date: 2026-11-09. Branch: `mst/m2-a03-opt-in-v2-sidecar-20261109`; [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8) (NEVER merged without owner approval). This file is an intentional **strict second-run test marker**: the opt-in workflow fails closed unless it restores a previous-run synthetic cache record.

## Boundaries and provenance

- Original Swing Trading 1.8 source commit `cd90c1babae8912db31490ad614fc2ad2f868042`, MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, legacy tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`; all **63 unmodified original Python modules** remain source-locked. No v1 or existing opt-in v2 source edits, no changes to `pyproject.toml`.
- New isolated test-only [`.github/workflows/m4-cross-run-fixture.yml`](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/.github/workflows/m4-cross-run-fixture.yml) on the Draft PR, separate from `Foundation CI`. Uses **two GitHub-hosted Ubuntu jobs**:
  1. `recover-prior-run`: `actions/cache/restore@v4` on PR-number-scoped, run-ID-suffixed key, restore-key prefix from earlier PR runs; Python `scripts/m4_cross_run_fixture.py recover` verifies checksum, schema, exact synthetic partition, previous run ID strictly older than current, and same PR number.
  2. `stage-next-run`: only after recovery job, a **different hosted runner** emits synthetic bytes (SHA256 claim, no key/signature) with current run ID, and `actions/cache/save@v4` uploads to GitHub's disposable Actions cache.
- A committed **report marker** causes future `recover` jobs to use `--require-prior` instead of silent bootstrap: a cache miss produces `NO_CROSS_RUN_CACHE_FOUND` and fails rather than faking continuity.
- `scripts/m4_cross_run_fixture.py` has **NO network code, service credentials, Google Drive objects, licensed OHLCV data, independent keys, real publisher operation, or protected rollback floor**. CI's cache/restore action is the only hosted cross-run storage mechanism. It is not a compliance-approved market-data store, anti-rollback or CAS service.
- New `tests/test_m4_cross_run_fixture.py` adds **10 synthetic parser contract tests**: bootstrap status, prior-run reading, corruption, same/future run, wrong PR, self-rehashed forged authorization, cross-partition digest, noncanonical extra fields, deterministic unsigned hash, and invalid IDs/JSON.

## First independent run — verified

At PR candidate commit `b7584794196cc28101fec9c2a578782213631aaf`:
- [Separate cross-run workflow #42586778775](https://github.com/ngluonghoa/MST/actions/runs/42586778775): **SUCCESS 2/2**, `recover-prior-run` reports `BOOTSTRAP_NO_PRIOR_CACHE` for current run ID `42586778775`, and `stage-next-run` successfully uploads a synthetic cache with an explicitly separate future-recoverable key.
- [Foundation CI #42586778685](https://github.com/ngluonghoa/MST/actions/runs/42586778685): **SUCCESS 3/3**, Python 3.11 `1609/1609`, Python 3.12 `1609/1609`, engineering `63/63` and H2/H3/lint/wheel passing.

**The second independent run is the acceptance event**: it must report `CROSS_RUN_CACHE_BYTES_VERIFIED_UNATTESTED` with `prior_run_id=42586778775` and a different new `current_run_id`, including seven false authorization flags. If GitHub has evicted the cache or scoped it differently, the run must FAIL and this remains a blocker; do not claim cross-run verification from the first run.

## Security model and absence of production authority

Even if two separate GitHub Actions runs exchange and validate synthetic bytes, a **publicly computed SHA256 is not an authenticated vendor signature**; an Actions cache is a replayable/evictable, PR-scoped test artifact, not independent durable floor, legal Drive retention, account-bound writer key, physical Google Drive payload, server-side distributed CAS, or a protected authoritative GitHub ref. The test can demonstrate *actual cross-run continuity of a disposable GitHub-hosted test artifact*, not real data freshness, author/writer identity, source-clock monotonicity or production write authorization. All output fields `real_google_drive_readback`, `independent_witness`, `durable_rollback_floor`, `distributed_cas`, `vendor_entitlement`, `market_data_authorized`, and `trading_authorized` MUST remain `false`.

## M4 acceptance delta: a future protected writer must separately prove

- **M4-INTER-RUN-G01:** independently protected, signed per-partition+rights-policy monotonic head/floor persisted across Actions **run IDs** and across different authorized writer accounts, plus original source-clock witness and retention authorization.
- **M4-INTER-RUN-G02:** two separate authorized runners race the same immutable parent ref and produce exactly one server-verified winning child; losers cannot falsely declare committed.
- **M4-INTER-RUN-G03:** after crashes at each publication cutpoint, a newly dispatched Actions run recovers an authenticated journal, checks physical Google Drive chunk bytes and independent Git ref parent/tree/readback, and deterministically converges or quarantines.
- **M4-INTER-RUN-G04:** a new account, missing/evicted cache, a replaced runner, stale signer key or revoked provider rights must cause **fail-closed**, not floor reset or restored rights.
- **M4-INTER-RUN-G05:** machine-readable proof distinguishes `SYNTHETIC_CACHE_RESTORED_UNATTESTED` from `PROTECTED_CLOUD_WRITER_VERIFIED`; the latter can only be recorded after the former's missing production requirements have genuinely passed.

## Open milestones

A02 manual 63/63 owner disposition remains OPEN, A03 v2 ABI [Issue #6](https://github.com/ngluonghoa/MST/issues/6) OPEN. M3 vendor entitlement/source clock/Google Drive retention unverified. M4 [Issues #10](https://github.com/ngluonghoa/MST/issues/10), [#13](https://github.com/ngluonghoa/MST/issues/13), [#14](https://github.com/ngluonghoa/MST/issues/14) real independently protected cloud publisher/CAS/fencing/Drive chunk custody NOT IMPLEMENTED; M5/M8 live release BLOCKED. No Mac/MOCHI/user-local environment, real market payload or production trade. All updates in Draft PR #8 only.
