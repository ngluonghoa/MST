# MST §252 — Private connected-MCP D1 → original 16-zone engine diagnostic, NO_TRADE

**Date:** 2026-11-23 ICT. **Scope:** atomic isolated extraction from Draft PR #23 pinned at `a3cca901f37f3dedd4d7a3ec49771b553b54c70d` with unchanged source `src/swing_trading/private_cache_source_bridge.py` and matching `tests/test_private_cache_source_bridge.py`. Main foundation at extraction: `6667a3879550b899ee8ff596f162846f83a6175b`.

## Purpose

A legitimate offline **reference-only, provider-partitioned** input bridge for the already merged initial `swing_trading.engine.evaluate_unimplemented_zones`. Earlier §251 added structural phase geometry ingredients but no source-qualified complete B1–B8/S1–S8 detectors. The bridge takes caller-supplied *private research snapshots* matching historical SSI, DNSE and VCBS MCP envelope shapes, checks dates/order/OHLCV/integer volume/bounds/semantic differences, stores **nothing**, and creates typed source-scoped D1 reference diagnostics for SHORT and SWING. The original engine emits 16 `UNVERIFIED` statuses for either strategy and NEVER emits trading signals. Source material/price values are omitted from public receipts.

This is a step towards the locked UI-1.0 A–I **incomplete** report, not an actual licensed Cloud ingestion pipeline, venue-close attestations, complete multi-TF contract, production source, Google Drive Cache write or release. The bridge is not wired to an incoming live GitHub Actions vendor API connection, nor to an operational private signed highwater repository, and must not be confused with `scripts/mst_d1_research_cross_feed_basis248.py` which checks three MCP observations with explicit upstream raw/adjusted unit labeling. Every vendor data path remains subject to separately verified rights and source clock.

## Source-specific boundary and tests

- SSI compact private MCP research rows (price VND) are not aliased to SSI FastConnect V3 directly called on GitHub. Adjustment basis stays `UNKNOWN` unless independently attested. Do not declare confirmed D1 finality.
- DNSE DAY series price numbers in thousands of VND are normalized only within the explicit DNSE provider adapter, without mutating source input.
- VCBS `board_supplement` newer row and separate adjusted/raw fields remain observable/provisional; no automatic close/finality promotion.
- Reject invalid provider/symbol/session, duplicated/out-of-order rows, malformed OHLC, negative/noninteger volume, cross-provider provenance, nonfinite values, and fake authorized/published flags. Independent no-broker/no-write behavior is checked with fabricated fixtures.
- No owner credentials, external provider API calls, OAuth refresh, private Drive write, GitHub branch mutation, real signal, backtest OOS or trade action. All 16 zones remain `UNVERIFIED/NO_TRADE`.

## Still blocked

Owner's real preflight [45041453411](https://github.com/ngluonghoa/MST/actions/runs/45041453411) found both SSI/DNSE read-only `HOLD` because owner declaration and at least one secret-group item is missing. No subsequent manual native data fetch yet as of this extraction; GitHub Cloud provider access and vendor retention permission are independent of connected-MCP research availability. Owner-private highwater signer/CAS, six native/derived TFs + W1, first-known and fully calibrated 64 zone phases remain unverified. Neither the earlier 22 Nov engineering RC target nor trading readiness is satisfied by this step.
