# MST M4 Cache V2.1 — P0 Daily Partition Chain and V1 Indicator Carry

Date: 2026-11-11 (Asia/Ho_Chi_Minh)
Status: SYNTHETIC DESIGN / QA ONLY; licensed market data, real Cloud cache, production release and trading NO-GO.

## Purpose

The previous 16-day inherited V1-only oracle reached exact numeric EMA20/Wilder ATR14 parity across six TFs and 1,248 fictional windows, but an entire 16-day composite cannot be passed to existing single-date V1->V2 FixtureV2ConsumerScope. Its V1_V2_SESSION_MAP_NOT_EXPLICITLY_LOCKED guard is correct and must remain enforced.

## Additive implementation

- scripts/m4_v21_daily_partition_checkpoint_chain_lab.py creates one typed FixturePartitionV2 + FixtureV2ConsumerScope for EACH fabricated date, timeframe and full inherited source policy identity.
- tests/test_m4_v21_daily_partition_checkpoint_chain_lab.py adds 35 dedicated positive/negative synthetic cases for causal EMA/ATR carry, revisions, integrity and fail-closed controls.
- .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml runs the new module and validates no-go JSON, archived to GitHub Actions ephemeral 14-day artifact only.
- 16 consecutive fabricated calendar days (including weekends), six TFs: 96 independent dated candidate V2 partitions; same fictional two 2-hour segments per day with artificial lunch gap. H4 and D1 grouping is fake, not official provider/venue bars.
- Every checkpoint link SHA includes preceding link digest, daily V2 partition digest, all legacy policy dimensions via the one-day binding, V1 synthetic daily scope, content and separately versioned first-known lineage digests, incoming and outgoing EMA20/Wilder ATR14 states.
- Late fictional PRICE correction: recalculate only affected suffix within day13, then carry recomputation across later dates. Expected M5/M15/M30/H1/H4/D1 positions 124+42+21+11+3+3=204; numerical checkpoints must match original V1 full_recompute and an independent Decimal oracle. Pre-dirty links unchanged.
- Metadata-only correction: content and inherited numeric carry unchanged, indicator recomputation 0, but day14 and downstream lineage parent hashes must be relinked.
- Explicit denial for cross-provider, cross-policy, cross-TF, missing days, missing predecessor, altered prefix, forged source lineage/link SHA, future-known data and backdated as-of.

## Trust and release boundaries

Local deterministic SHA linkage is NOT an independently signed issuer receipt, protected external monotonic anti-rollback floor, authenticated multiwriter CAS or real Google Drive persisted manifest. The typed acceptance of one synthetic date is NOT an approval of real OHLCV storage, exchange session calendar, source retention, first-known authenticity or production ABI. M3 source-rights Issue #9 and M4 Drive/rollback Issue #10 remain OPEN. Draft PR #8 stays UNMERGED, source-locked 63 V1 plus eight existing V2 modules untouched, protected main unchanged.

No actual SSI/DNSE/VCBS Cloud credentials or vendor calls, no official HOSE/HNX/UPCOM sessions, no physical Drive quote cache read/write, no live signals, release or trades. User approval for eight Cache V2.1 improvements is design/synthetic engineering permission only.

## Required verification

Proposed new 35 focused tests would increase the prior 390 to 425 focused synthetic methods ONLY AFTER GitHub CI PASS; this is not the all-repository test total. Independently inspect exact report-containing commit SHA and all 47 expected PR-triggered workflow outcomes, including Foundation Python 3.11/3.12, and the dedicated 35-test receipt. Inspect branch diff and preserve byte-identical original modules and main. If CI is pending or red, do not claim acceptance.

GitHub PR: https://github.com/ngluonghoa/MST/pull/8
Source rights: https://github.com/ngluonghoa/MST/issues/9
Cache custody: https://github.com/ngluonghoa/MST/issues/10

Next P0: issuer-approved real VN calendar and aggregation/first-known policy, physical per-day checkpoint carry schema with owner-reviewed ABI, licensed Drive storage, independent signer and protected rollback/CAS proof. Continue synthetic-only until those gates close.
