# MST M3/M4 Cache V2.1 P0 — Calendar Policy As-Of Revision and Six-TF Quarantine QA

Date: 2026-11-11 Asia/Ho_Chi_Minh.
SCOPE: GitHub-hosted hypothetical fixtures ONLY. NO official exchange calendar, source entitlements, authenticated revisions, real Google Drive market cache, signed rollback floor, two-writer CAS, real signals, production release or trading.

## Why this checkpoint

Previous P0 proved artificial 16-day V1 EMA20/ATR14 parity, 96 per-date V2 candidate links and bitemporal source-bar first-known history. It did not cover a calendar/source-resolution policy correction becoming known after the fake candles were observed. Retroactive venue-like holidays or halts affect M5 admissibility and all derived TF windows. Reusing indicators from an old calendar-policy namespace without requalification could contaminate historic analysis.

## Synthetic experiment

- New additive script: scripts/m4_v21_calendar_revision_quarantine_lab.py
- 47 negative and positive cases: tests/test_m4_v21_calendar_revision_quarantine_lab.py
- Existing workflow extension: .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml
- New QA checkpoint: docs/MST_M4_V21_CALENDAR_REVISION_QUARANTINE_QA_20261111.md

Reuses the original 16 wholly invented calendar days including weekends; imaginary AM 09:00–11:00 and PM 13:00–15:00 with a fictional gap and 768 synthetic M5 source observations. These times are NOT evidence of an official HOSE/HNX/UPCOM trading calendar.

A separately untrusted local calendar ledger records 16 invented initial calendars and two later invented corrections at distinct first-known times: day ordinal 3 changes to CLOSED; day 8 PM changes to HALTED. Earlier historical as-of queries must not see those future calendar revisions.

Before corrections 768/768 toy M5 rows are structurally aligned. After toy closure 48 rows are quarantined; after additional toy halt 72 rows are quarantined. The unchanged morning of the halted day may remain structurally aligned, but the old full-policy calendar digest must NOT be reused without explicit versioned requalification.

Derived artificial TF windows intersecting any quarantined underlying M5 member are flagged: M5=72, M15=24, M30=12, H1=6, H4=2, D1=2; total 118. This is a dependency preview, not an actual numerical recomputation or officially derived market bar.

Each calendar digest binds the pre-existing exact per-date V1→V2 full source-policy binding plus explicit fictional calendar version, day status and phase kinds. Corrected days must rotate digest; unaffected days do not. Positive checks and fail-closed negatives cover missing source/calendar, phase type, session gap, unqualified AUCTION/AFTER_HOURS/HALTED/UNKNOWN phase, bitemporal first-known, sequence replay, old policy reuse, forged local chain, cross-history mix, and attempted self-attestation of genuine issuer, official closure or licensing.

The local SHA links and hypothetical OPEN/CLOSED/UNKNOWN statuses provide NO real venue authority, endpoint timestamp semantics, license/retention, issuer-signed revisions, protected cloud high-water floor or authenticated distributed writer CAS. Real market source access, Drive quote-cache I/O, production and trading MUST remain false.

## QA acceptance

Previous 472 focused synthetic methods + 47 new = 519 cumulative targeted methods only after exact-head GitHub Actions 47/47 COMPLETED SUCCESS (including Foundation Python 3.11/3.12). This is NOT the full repository test count.

Verify Git diff against preceding green commit 35c3fe0ab1298330c34ee2855b389840baeae286: only new script, new tests, QA document and existing relevant workflow. Original 63 inherited V1, eight existing V2 Python modules and protected main must remain untouched. PR #8 Draft/unmerged.

PR: https://github.com/ngluonghoa/MST/pull/8
M3 rights/calendar: https://github.com/ngluonghoa/MST/issues/9
M4 custody/Drive: https://github.com/ngluonghoa/MST/issues/10

## OPEN external gates

Document genuine source vendor terms and authorized Cloud cache retention, versioned official exchange historical calendars and auction/halt/correction behavior, source-issued first-known history, approved cache ABI, physically authenticated Google Drive workflow, independently protected signer/rollback high-water and two-writer CAS before ANY live quote cache, release or trade. Eight approved Cache V2.1 enhancements cover design and synthetic QA only.
