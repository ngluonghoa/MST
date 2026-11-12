# MST A02 — Eight High-Impact Inherited V1 Runtime Behavior Matrix (Real Legacy Calls)

QA ID: MST-A02-V1-EIGHT-EXECUTED-BOUNDARIES-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: **PASS** for eight inherited original V1 module fixture/runtime boundaries, **48/48 tests**, **192/192 UNVERIFIED decisions**. Two unsafe/permissive inherited behaviors explicitly documented. This is NOT complete Swing Trading 1:1 trading behavior parity, owner A02/ABI signoff, G01-G08 trust-root approval or trading release.
PR: https://github.com/ngluonghoa/MST/pull/8 (DRAFT/UNMERGED).
Architecture: GitHub + Google Drive ONLY (Option A). Hosted GitHub Actions execution with disposable synthetic fixtures; no Mac/MOCHI/local, third-party cloud service, real vendor quotes, real Drive cache or broker/trading.

## 1. Immutable baseline and direct real-call scope

- Original Swing Trading 1.8 upstream commit cd90c1babae8912db31490ad614fc2ad2f868042; protected MST main 4048f91beaaa3410116d97e35896c8b688384e19; original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e.
- Exact remote GitHub upstream/main/candidate source-byte lock independently fetched in the same CI job. Original 63 V1 modules untouched, eight already existing opt-in V2 source modules untouched and separated. All new files only in existing Draft PR#8.
- Eight actual inherited modules executed: contracts, engine, replay, market_data, source_quality, incremental_cache, cache_fetch_planner, vn_backtest_execution_fixture. This uses actual original Python code, NOT mocks of these eight modules or static AST alone. Reuses previously tested independently implemented EMA/ATR reference and original SQLite cold/warm correction transaction execution.

## 2. Executed cross-module as-of and signal boundary

Six manufactured intraday instants 14,15,20,24,25,30 minutes after 2026-11-06T02:00 UTC. Two original strategies SHORT and SWING; 16 zone identities B1-B8/S1-S8 at each instant. All **6×2×16=192 decisions** produced by original engine are UNVERIFIED with empty evidence — original zone detector remains unimplemented, never infer NOT_DETECTED or DETECTED.

| As-of minute | Original V1 necessary candle quality | V1.2 rich source prerequisites | Original engine for 16 zones × 2 strategies |
|---:|:---:|:---:|---|
|14|false|false|UNVERIFIED|
|15|true|false|UNVERIFIED|
|20|true|false|UNVERIFIED|
|24|true|false|UNVERIFIED|
|25|true|true|UNVERIFIED|
|30|true|true|UNVERIFIED|

Source revision visibility at time known is NOT final source quality or trade authority; V1 necessary candle boolean is not equivalent to the V1.2 richer prerequisite. Even a caller-supplied entitlement verified=true in synthetic fixtures does NOT independently prove provider data licenses, cutoff or source quality. V1 source positive with zero known volume is valid; missing volume None, open bar, unverified quality fail. V1.2 missing entitlement claim, nonempty quality flag or unverified quality fail. No look-ahead.

## 3. Inherited compatibility gaps — do not quietly change legacy

- The original ReplayClock.advance_to method rejects decreasing timestamps, but direct assignment to ReplayClock.as_of_utc can bypass the monotonic method guard. This is a **confirmed original V1 permissive public attribute behavior**, not a declaration that production anti-rollback works.
- The original Evidence dataclass accepts a truthy non-boolean verified field. A synthetic string is accepted; it is **not authenticated evidence**, and cannot be used to authorize DETECTED or a trade.
- The original SignalDecision rejects unknown zone identifiers, non-UNVERIFIED decision without evidence, and replay/evidence date-time constructors reject non-UTC as tested.
- These legacy behavior gaps are deliberately NOT patched in the protected/source-locked V1 code. A future strict V2 behavior requires separate explicit ABI and migration decisions; never silently claim strict V2 and permissive V1 are drop-in equivalent.

## 4. Cache and Vietnamese equity fixture boundaries

- The real V1 read-only five-minute cache planner REUSE_CLOSED before cadence, REQUEST_WINDOW at cadence, REQUEST_FULL_SESSION when historic correction reconciliation is due, BLOCKED when provider capability is UNKNOWN. A synthetic claimed final immutable head may alter a reuse hint but NEVER certifies provider freshness or authorizes data/trade.
- The real inherited synthetic-only SQLite cache executes ten changes: cold initialization of 36 closed fabricated M5 candles, reopen/warm reuse with zero recalculation, lineage-only revision, append one, correct old candle and recompute exactly 32 affected checkpoints, incomplete page never deletes absent bars, complete bounded scope delete/backfill, open preview ignored, stale-known update fully rolls back all SQLite state.
- Persisted EMA20/ATR14 checkpoints are cross-checked both against V1 cold recompute and a separate independent reference implementation. ATR14 first valid bar index 14 and closure of the temporary database are explicit. This is not licensed Google Drive cache parity.
- VN synthetic calculation yields Decimal net P&L string 196.600 solely on fabricated fills, venue fee/tax values and externally provided settlement session index. A bar touching stop AND target is AMBIGUOUS_BOTH, never a proven fill. require_vn_backtest_release explicitly raises PermissionError.
- Original V1 positive booleans and synthetic P&L DO NOT mean live signal, performance, licensed market entitlement, Vietnamese exchange calendar, broker fills or production release.

## 5. Code, tests and exact Cloud CI evidence

Additive files in Draft PR#8:
1. scripts/m2_a02_eight_inherited_runtime_boundary_lab.py — actual 8-module V1 execution and joined no-go receipt.
2. tests/test_m2_a02_eight_inherited_runtime_boundary_lab.py — 48 unit tests, including negative permission/temporal/quality/cache and VN OHLC cases, deterministic repeat receipt.
3. .github/workflows/m2-a02-eight-inherited-runtime-boundaries.yml — same-repo PR8 only, permissions contents:read, hosted Python3.12. Independent real GitHub upstream/main/PR source-tree readback then actual V1 48 tests and 8-module receipt. No privileged calls, secret, real Drive bytes, vendor or trade.
4. docs/MST_A02_EIGHT_INHERITED_BEHAVIOR_QA_20261110.md — technical QA report (this file) and a mirrored Google Drive QA document.

Code/workflow HEAD f8f75256fb746313f0549c55078432590abf0734:
- Dedicated eight-module runtime workflow https://github.com/ngluonghoa/MST/actions/runs/42763246302: **SUCCESS, 48/48 tests**; status EIGHT_V1_RUNTIME_BOUNDARIES_EXECUTED_SYNTHETIC_GAPS_EXPLICIT_NO_GO; 192 UNVERIFIED, zero owner approvals; remote original tree source lock PASS. Deterministic synthetic receipt SHA256 2c2932f08060dce7c0d127b564d0c2ac04c99e9d27ec34664bbb2ad47689cfe9 (not cryptographic market source attestation).
- Foundation https://github.com/ngluonghoa/MST/actions/runs/42763246261: **SUCCESS** 3/3 jobs, Python3.11 2543/2543, Python3.12 2543/2543, original engineering module source boundary 63/63 plus H2/H3/lint/wheel.
- **24/24 workflows SUCCESS at exact code/workflow HEAD**. The final QA-report-containing HEAD after this Markdown commit requires separately checked CI confirmation.

## 6. Owner-review and production constraints

A02 63 human owner module dispositions remain 0/63; this checkpoint provides executed evidence for eight prioritized modules but does not sign off even those eight. Remaining 55 V1 modules require deeper runtime behavioral review too. A03 V2 ABI/full behavior acceptance remains OPEN, as do G01-G08 actual external signer/durable floor/two-writer CAS/vendor/Drive/revocation/trade gates, OA01–OA06 independent owner decisions and M3/M4/M5/M8 production readiness.

Next independent engineering work can expand executed behavioral coverage to the remaining 55 V1 modules with meaningful domain-specific fixtures; preserve existing protected V1 source and all fail-closed production fences. No automatic OWNER_SIGNOFF, PR merge, ACL/ref/ruleset change or trading.
