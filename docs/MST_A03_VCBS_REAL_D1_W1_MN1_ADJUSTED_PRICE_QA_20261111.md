# MST A03 — VCBS connected D1 vs W1/MN1 adjusted corporate-action arithmetic & partial-period QA

Date: 2026-11-11 (Asia/Ho_Chi_Minh). Status: real read-only MCP observation in-memory, **not** real Cloud production ingestion or provider-source qualification. Public repo contains only factual aggregate counts and fully fabricated script/test inputs; no real ticker OHLCV arrays, source requests/tokens or source quote rows.

## Master Handoff precedence / why this is new

Master Handoff §§95–97 (2026-11-10/11) previously established VCBS historical D1 and 226 FPT intraday **time/price points only**, explicitly *not* authentic per-minute OHLCV. SSI/DNSE public vendor OHLC multi-TF and current MCP reachability are separate evidence types (§§94–103). Recent §117 separately retained REAL DCM/HPG and prior FPT three-provider D1 snapshots under private Drive; no W1/MN1 persisted production cache was claimed.

VCBS connected `vcbs_get_history` supports interval `D`, `W`, `M`. Weekly/monthly are **provider connector aggregations of daily session records**, not independently verified native intraday provider candle publication. W1/MN1 are supplemental research; MST's owner-locked six trading/indicator frames **remain M5/M15/M30/H1/H4/D1**, not expanded or silently changed.

## Real connected observations (read-only)

Called the current authenticated ChatGPT VCBS MCP `vcbs_get_history` for FPT, DCM, and HPG independently with `interval` D, W and M; same requested calendar range 2026-09-01 to 2026-11-10 and `price_basis=adjusted`. Data came exclusively from user-connected VCBS MCP. All nine calls succeeded:

| Aggregate | D | W | M |
|---|---:|---:|---:|
| Source observations across 3 symbols | 147 | 33 | 9 |
| Source-reported `partial=true` | — | 3 | 3 |
| Source-reported `partial=false` | — | 30 | 6 |
| D1-derived adjusted OHLCV/value arithmetic comparisons | — | 33/33 match | 9/9 match |

Daily reconstruction: sort D1 by `tradingDate`; scope to each returned `periodStart..periodEnd`. For adjusted periods, reconstruct `open = first_daily.openPrice * first_daily.adjFactor`, `high = max(day.highPrice * day.adjFactor)`, `low = min(day.lowPrice * day.adjFactor)`, `close = last_daily.adjClosePrice`; sum `volume`, `tradingValue`, `ptValue`, `foreignNetValue`; compare `sessions`. All 42 returned weekly/monthly aggregates passed when **each daily row uses its own adjustment factor** (price tolerance 0.10 VND, values tolerance 0.02). No publisher-authoritative external calendar, per-period completeness proof, official adjustment first-known record, or source entitlement follows from an arithmetic match.

### Important real diagnostic that original naive check missed

An earlier comparison using DAILY raw `openPrice/highPrice/lowPrice` directly found mismatch in FPT's three September weekly periods and the September monthly period. In these four periods, daily `adjFactor` differed from 1 (roughly 0.909 in earlier September observations); testing adjusted daily OHLC with each row's factor removed all four differences. DCM/HPG did not present the same issue in this sample.

Consequence: a naive MST Cache source promotion treating VCBS W/M `priceBasis=adjusted` values as equivalent to a `max(raw_highPrice)` / `min(raw_lowPrice)` resample would be **wrong around corporate actions**, even when raw/adjusted close or volume seems stable. Preserve `priceBasis`, `adjFactor`, source-native output and corporate-action lineage separately; quarantine any mismatch, no silent price-unit or basis coercion.

The six reported partial periods are the weeks/months containing 2026-11-10, each marked `partial=true`, `provisional=false`. Excluding an open intraday row is not sufficient to close a **weekly/monthly** period. Crucially, the first September window has W `partial=false` and `periodStart=2026-09-03` due to the returned D1 window; this is **not** proof of official complete venue calendar membership. No W1/MN1 source row is promoted to certified closed until a separate historical official calendar and source-issued period/correction contract are validated.

## Additive Cloud-only code & test gates on Draft PR #8

- `scripts/m2_a03_vcbs_adjusted_wm_crosscheck_lab.py`: independent read-only pure-function observer. Explicit `adjusted`, VND and per-D1 matched-volume requirement; deterministic date-period scope, unique D1 and W/M identities, finite OHLC/adjustment, per-day price-factor-adjusted OHLC aggregation, volume/value reconciliation. Mismatch causes fail-closed `VCBS_D1_W_M_CROSS_SOURCE_ARITHMETIC_DRIFT_DENIED`; `partial=true` is quarantined. Passing arithmetic is always `OBSERVATIONAL_ARITHMETIC_MATCH_NOT_CALENDAR_CERTIFIED`. No live provider authentication, source quote persistence, calendar sign-off, Cloud Cache activation, orders.
- `tests/test_m2_a03_vcbs_adjusted_wm_crosscheck_lab.py`: 50 completely fictional unit tests for adjusted-vs-raw discrepancy, mismatched open/high/low/close, volume/value/sessions, false closed/provisional, invalid dates/periods, duplicate/missing source rows, NaN/non-finite values, wrong currency, source `priceBasis` and scopes, no Cloud/issuer grant.
- Existing unprivileged `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml` adds these 50 fake tests and sanitized synthetic-only NO-GO receipt. No new elevated workflow, token, GitHub Actions provider call or real quote arrays.
- THIS QA report `docs/MST_A03_VCBS_REAL_D1_W1_MN1_ADJUSTED_PRICE_QA_20261111.md`.

## Strict external gates / operational disposition

REAL OBSERVED in user-connected ChatGPT MCP: D1/W1/MN1 connector returns and 42/42 source-internal arithmetic reconciliation. REAL NOT OBSERVED: intraday M5/M15/M30/H1/H4 VCBS authentic OHLCV candles, publisher-signed W/M closure and first-known/correction history, official historical VN session and auction/holiday calendar, provider cross-platform Cloud retention rights, GitHub Actions VCBS entitlement, independent GitHub→Google Cloud WIF metadata identity, production CAS/anti-rollback, approved new ABI, automated Cache or actionable trading.

The previous FPT/DCM/HPG real D1 snapshots (180 individual private three-provider rows) are unchanged. This turn **does not save the 189 VCBS D/W/M observations to a production cache**, does not move or publish user's private source rows into public GitHub, and does not alter the 63 source-locked V1 or eight existing V2 opt-in source modules. The new 42 W/M entries are QA comparisons, not additional licensed retained production candle data.

Owner acceptance M3 Issue #9 and M4 Issue #10 remains OPEN/NO-GO. Previous Draft PR8 exact green HEAD `5e9c794fc86380b2f32d7ac75eab72020ba01e4e`: 47/47 GitHub PR workflows success and 731 focused synthetic test methods. Only credit +50 new methods and 47/47 green on the new exact HEAD after all GitHub jobs complete and source boundaries are rechecked.
