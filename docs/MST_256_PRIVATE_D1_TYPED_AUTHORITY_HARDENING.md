# MST §256 — Harden direct D1 typed-object authority and source provenance gates

Date: 2026-11-24 ICT. Baseline protected main: `43b848a80d7e0fd9203b8f74e2283db96fc9ead4`. Status: source-boundary correctness/security fix, no new algorithm or data source.

## Real defect

The existing private MCP D1 snapshot adapter validates source-specific historical rows, dates, bounded VND price values and source isolation, but its output dataclasses are public Python constructors. Before §256:

- `QuarantinedD1Bar` only checked provider/symbol superficially, OHLC relative ordering and volume negativity. A direct caller could pass NaN/Infinity, price `0`, negative/beyond-range or Python bool/string/huge integer volume, invalid type of session day, invalid basis/provisional tag, or a price beyond configured max. These objects were called quarantined but did not enforce the raw parser's same constraints.
- `PrivateD1Reference` only checked SHA256 text form and that its tuple of bars matched a count. Direct construction could mix different providers, symbols, future-session bars, unsorted/duplicated historical sessions or lie about `has_provisional_source`. Worse, it accepted `venue_close_attested=True`, `issuer_first_known_attested=True`, `source_is_appowned_publisher=True` and `eligible_for_signals=True` for private non-authoritative research.
- `PrivateD1Diagnostic` checked only timezone and strategy; a direct caller could set `eligible_for_signals=True` or `trading_or_broker_calls>0`. The existing locked report binding eventually rejected these flags but that is too late for any other consumer inspecting typed objects.

This is an **internal API invariant / spoofing risk**, not proof an attacker exploited MST or that a trading system had been running. These objects only support bounded diagnostic research, and all public authorization flags must remain FALSE.

## Correction

In `src/swing_trading/private_cache_source_bridge.py` validate in each `__post_init__`, including when constructed through `dataclasses.replace`:

1. Bar exact provider/symbol/session/price-basis/provisional types; finite positive `Decimal` OHLCV price fields within the VND source bound; original OHLC ordering; exact non-boolean integer shares 0..2^63-1.
2. Reference exact provider/symbol/day/digest/count/tuple types and 1..2048 rows; every element is a typed `QuarantinedD1Bar` of matching provider and symbol, no future sessions, strictly unique ascending trading dates, exact provisional flag; all publication/close/first-known/signal/backtest flags are literal False. The adapter already sorted rows; that normal behavior is preserved.
3. Diagnostic typed source and strategy, capture day cannot be future to as-of, and exact False eligibility and zero broker calls. Existing locked report remains the final 16-zone decision-content gate so unrelated mutation tests continue to test that boundary. No `UNVERIFIED`→`NO_SIGNAL` promotion.

New `tests/test_private_d1_authority_hardening256.py` uses invented historical fixtures for all SSI/DNSE/VCBS envelope shapes, direct constructors and `replace` to exercise forged flags, cross-provider injection, timestamp/session duplicates, out-of-order source, NaN/Infinity/nonnumeric/oversized price, malformed volume, provisional tampering, future-as-of and fixed redacted errors. Also verifies two original engine strategies still each produce exactly 16 `UNVERIFIED` rows.

## Governance and remaining blockers

This is an actual invariant hardening of the existing integration, not another fabricated trading demo. No new market prices, licensed data ingestion, broker operations, Google Drive writes, official first-known, calibrated zone formulas, signed highwater/CAS or production release is introduced. Existing protected-main manual source owner preflight `45041453411` still leaves provider credential/read-rights HOLD; 0 verified zone rules; all 16 zones `UNVERIFIED/NO_TRADE`. The approved Cloud-only, atomic scoped PR, CI green 3/3 and squash merge policy remains binding. Update H3 matrix only from the GitHub runner's regenerated whole-module audit, do not disable or weaken the contract check.
