# MST M3/M4 — Cloud provider eligibility & Google Drive partition-cache boundary (candidate)

**Status:** DESIGN + SYNTHETIC TESTS ONLY / NOT APPROVED FOR LIVE DATA, CACHE OR RELEASE.
**Source lock:** `MST/main@4048f91beaaa3410116d97e35896c8b688384e19` with Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` matches original Swing Trading source exactly. All code in this candidate stays on Draft PR #8. Do not change original 63 Python source files or inherited `pyproject.toml`.

## 1. M3 external-provider admission architecture

MST may eventually use distinct SSI, DNSE, VCBS and additional provider N adapters. But a ChatGPT-connected MCP, a synthetically working reader, a provider-looking endpoint, or a caller-supplied `verified=True` are **not** licence/retention authorization.

Proposed qualification gates, each with independently checked **provider + specific endpoint + account/workspace + purpose + effective dates**:

1. Independent vendor identity and real endpoint owner.
2. Account-specific licensed entitlement and restrictions.
3. Exact APIs, request frequency, quotas, timeframe range and rate limits.
4. Historical and intraday raw read permissions.
5. Google Drive Cloud retention, copying, offline storage, redistributing and purge/revocation policy.
6. Derived timeframes/indicators and derivative storage rights.
7. Historical backtest, OOS, research and portfolio usage rights.
8. Authenticated **Cloud-only** secret/identity custody, separation between ChatGPT connector session and unattended GitHub Actions runtime; no Mac/MOCHI credentials.
9. Exchange calendar, raw versus adjusted pricing, volume units, closure/first-known time and source-revision semantics independently validated.
10. Revocation, incident handling and documented N/N-1 rollback, including data deletion/retention obligations.

Source `src/swing_trading/v2_provider_readiness.py` maintains a **deny-only, metadata-only** readiness docket for exactly these ten gates. Its only evidence references are bounded opaque `EVID-` tokens; no licences, secrets, PII, real endpoints or market data enter GitHub. Notes are strongly tied to exact provider/fixture endpoint, recorded UTC and optional expiry; future-dated, duplicate, expired, revoked, malformed or cross-provider items are denied. There is **intentionally no verified state** and no path for a complete collection of CLAIMS to become `live_transport_authorized`, `cloud_retention_authorized`, `backtest_authorized` or `trading_authorized`. The output reports missing/unverified/expired conditions, never a grant.

A later real adapter needs separate owner-approved, independently authenticated and reviewed vendor-rights evidence and new trust/custody design. Do not add live source calls into this deny-only module. Record only evidence identifier and immutable reviewer receipt in an authorized Drive audit document after privacy assessment; do not paste real licences/secrets into the public MST repo.

## 2. M4 Google Drive partition identity, not yet a working cache

Source `src/swing_trading/v2_cache_partition_plan.py` proposes a deterministic **TEST_ONLY** partition identity with every one of these fields:

- Project hard namespace MST, candidate schema `mst.cache.partition.v2.test_only`.
- Exact source provider and endpoint, never implicit SSI/DNSE/VCBS fallback.
- Exact normalized ticker, requested M5/M15/M30/H1/H4/D1 timeframe.
- Local trading session date, without treating machine timezone as a certified VN market calendar.
- Explicit RAW vs ADJUSTED price basis; forbid mixing those as one OHLCV series.
- Explicit source-revision namespace (unverified metadata until M3 confirms origin).
- SHA256 hash of canonical sorted JSON over **all** identity fields.

The plan-only path prefix is `MST_V2_TEST_ONLY/` and is **not a Google Drive folder, file ID, grant, cache hit or pre-approved storage location**. No Drive I/O exists in the candidate module. A source name, symbol, date, timeframe, price basis, endpoint or revision namespace change necessarily yields a different hash; tests cover cross-provider head reuse rejection.

Only synthetic metadata heads may be considered in the planner; their generation and SHA are **caller assertions**, not independent source heads. `plan_fixture_refresh` offers hints for empty partition, recent local check under five minutes and provider revalidation due at 5 minutes. Regardless of hint, its permissions to fetch, read licensed cache, write Drive or trade remain **False**, and source freshness remains unverified. This is *not* an operational incremental updater or market polling scheduler.

## 3. Proposed future operational Cloud cache workflow (NOT IMPLEMENTED)

A future separately approved M4 plan would operate exclusively in GitHub/Google Drive Cloud and must gate each state transition:

1. Independent M3 rights/credential/endpoint admission for the specific source and use before any read.
2. Explicit consumer request: provider + source feed + set of tickers + timeframe + price basis + version + session. Changing from 1 to 5 to 20 tickers MUST retain isolated existing valid partitions without automatically refetching all prior history.
3. Read rights-eligible metadata-only pointers; validate schema, SHA digests, approved source lineage, expiry/revocation and immutable prior generation before considering any cached payload. **Do not** trust a string `verified=True` or caller-supplied content hash alone.
4. For unchanged CLOSED candles, prefer already validated immutable historical chunks; for new/revised OPEN candles plan the smallest bounded retrieval supported by the **real provider's documented capability**. If no delta/change cursor exists, never invent one; use the supported window/full-session endpoint and reconcile by provider revision and first-known time.
5. A new chunk would be uploaded **immutable/content addressed** to a provider-specific Drive partition, then checked independently. A separate per-partition manifest would describe source identity, schema, right-to-retain reference, canonical chunk digest, generation, signed head chain/previous digest, temporal validation and revoked-data handling. Historical chunks must never be overwritten in place.
6. **Critical concurrency limitation:** Google Drive file updates and a plain last-writer-wins manifest are **not a general distributed compare-and-swap**. GitHub Actions workflow `concurrency` could serialize one agreed writer key in a single repo, but this alone does not protect against other accounts/workflows or out-of-band Drive writes. Until a separately approved atomic lease/witness/fencing protocol and independent head verifier are implemented and negatively tested, parallel writers and automatic persistent promotion must remain BLOCKED.
7. Publish/activate new manifest only after every gate, checksum, signed anti-rollback and independent writer authorization passes; ensure readers fail closed on missing/stale/divergent manifest rather than silently switching provider. Preserve source quality, adjusted/raw, calendar and time-series lookahead constraints.
8. Demonstrate crash recovery, stale writer, duplicate upload, token revocation, Drive throttle, lost update, anti-rollback, source licence expiry, altered chunk, N/N-1 rollback and complete deletion/revocation tests **before** real customer data is stored.

Do not reinterpret `swing-trading-1-8` v1 Cache identities, signatures, publisher namespaces or provider rights as v2 MST storage entitlements; inherited v1 remains source-locked. Cloud-only means no Mac/MOCHI/local caches or compute, including use of a local helper as a hidden scheduler.

## 4. QA and decisions

- `tests/test_m3_v2_provider_readiness.py`: 17 offline cases including ten purportedly complete unverified claims still yielding no authority, cross-provider/endpoint docket rejection, timestamps, expiry/revocation and secret-shaped reference rejection.
- `tests/test_m4_v2_cache_partition_plan.py`: 21 offline cases including provider/endpoint/instrument/TF/date/price-basis/revision identity separation, 1→5→20 tickers preserving deterministic prior keys, five-minute refresh-hint only, malformed/future heads and zero real data/Drive permissions.
- `tests/test_m2_a03_legacy_blob_parity.py`: still pins all **63** original Python modules and source package metadata; the new two opt-in modules are allowlisted separately. Candidate branch has 68 Python modules (63 original + 5 opt-in), NOT 68 final module acceptance signoffs.
- Current 66-module PR #8 previous verified baseline was 1,416 Python tests on both 3.11 and 3.12; after 17+21 test methods, **expected 1,454 tests**, but only cite the exact latest GitHub CI HEAD as accepted when completed SUCCESS with three required check contexts plus H3-generated matrix/lint/wheel.
- H3 classifies `v2_provider_readiness` as provisional IMPROVE based on rough static branch score; this is a manual-review TODO, **not** a proven code defect. Continue source-wide review and explicit owner acceptance separately.

### Governance / release state

M3 provider actual account licence and authenticated live MCP adapters: **NOT IMPLEMENTED**. M4 Google Drive operational cache/atomic head/rights enforcement: **NOT IMPLEMENTED**. M5 real 16-zone detection and M6 live validated backtest: OPEN. M8 signed release: NOT APPROVED. PR #8 remains **DRAFT/UNMERGED**, prior in-place PR #7 CLOSED UNMERGED. No new credential, market data, real cache, trade order, trading recommendation, automatic monitoring or release is produced by this candidate.

Track:
- https://github.com/ngluonghoa/MST/issues/4 — A02 full 63-module review.
- https://github.com/ngluonghoa/MST/issues/6 — A03 strict v2 contract readiness.
- https://github.com/ngluonghoa/MST/issues/9 — M3 independently authorized real SSI/DNSE/VCBS provider admission.
- M4 separate Google Drive operational Cache issue: https://github.com/ngluonghoa/MST/issues/10 ; no M4 operational delivery claimed here.
- M3/M4 full QA receipt, source blob SHAs, current CI and rollback boundaries: https://docs.google.com/document/d/1DVO7c-eoW8vK5iAxjdLLHr4xpReMtwEXywTEUQFw2kw/edit .
