# MST §243 — Optional SSI private source CHUNK + UNPUBLISHED MANIFESTS manual stage

2026-11-20 ICT. Change limited to the existing protected-main manual GitHub Actions SSI source-to-Drive workflow, its Python entrypoint, new synthetic tests and this document. **NO automatic hourly data capture, no production cache publisher, no CAS/head and NO_TRADE.**

## Modes

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/mst-private-source-chunks-manual.yml

1. **CHUNK_ONLY** (default). Exact existing §241 guarded SSL/TLS SSI FastConnect marketdata read and private app-owned OAuth drive.file CHUNK upload and SHA256/MD5 readback only. MANIFESTS is not queried or touched.
2. **UNPUBLISHED_MANIFEST** (new, explicit). Requires all existing SSI source-retention/write gates AND an extra repository variable `MST_PRIVATE_MANIFEST_WRITE_ACCEPTED=true`. Fails before any vendor query on missing approval, invalid stage mode or failed app-owned MANIFESTS preflight. Runs the original private CHUNK upload, then §242 re-verifies it directly from Google Drive and creates a private **UNPUBLISHED** manifest with two SHA256/MD5 readbacks. A manifest failure can leave a private orphan CHUNK; no delete, overwrite, blind retry or rollback.

Only a human manually selecting input `manifest_mode=UNPUBLISHED_MANIFEST` and having the separate true variable can activate the new stage. Setting `MST_PRIVATE_MANIFEST_WRITE_ACCEPTED=true` alone does not change the safe `CHUNK_ONLY` default.

## GitHub owner credentials/rights

No secrets were viewed or configured in this PR. The owner needs valid scoped `MST_SSI_API_KEY`/`MST_SSI_API_SECRET`, Google OAuth `MST_GDRIVE_OAUTH_CLIENT_ID`, `MST_GDRIVE_OAUTH_CLIENT_SECRET`, `MST_GDRIVE_OAUTH_REFRESH_TOKEN`, and confirmed lawful permission to retain native SSI OHLCV. The existing literal true variables `MST_PRIVATE_CHUNKS_WRITE_ACCEPTED`, `MST_SOURCE_RETENTION_RIGHTS_CONFIRMED`, `MST_SSI_READONLY_OWNER_ACCEPTED`, and `MST_SSI_SOURCE_RIGHTS_CONFIRMED` remain necessary. Do not set rights to true without a real source-license determination.

Explicitly deny source H4/W1 native capture; select one FPT/HPG/DCM, D1/H1/M30/M15/M5, bounded inclusive dates. Main-only, first-attempt, one non-cancelling GitHub Actions concurrency group; no PR, fork, push or scheduled run. Old folder bootstrap write must remain disabled.

## Proven vs not proven

The §243 offline synthetic tests check manual mode/default, separate gate, exact root/CHUNKS/MANIFESTS siblings, source-to-Drive call flow, no private ID/price in public receipt, and fail-closed semantics. §242 already tests individual source rereads and MANIFESTS double readback with synthetic transport. **No actual live SSI OAuth workflow has been dispatched by this change.**

A GitHub Actions CI PASS or an unpublished MANIFESTS upload is NOT legal source rights, first-known bar clock, venue open/close, raw/adjusted basis, duplicate-free long-term Drive storage, atomic single-writer publication, independent signed monotone highwater, complete original Swing Trading 1.8 zone equations or trading eligibility. A future separately approved publisher design must bind receipts into independently signed monotone CAS and reject rollback/races before any market Cache head.

Until those external proofs, all 16 B/S regions remain UNVERIFIED/NO_TRADE. Target 2026-11-22 is conditional engineering RC only.
