# MST M3 — DNSE OHLC REST repair feasibility, access/rights decision, Cloud-only runtime boundary

**Date:** 2026-11-12 (Asia/Ho_Chi_Minh). **Status:** READ-ONLY PUBLIC DOCUMENT RESEARCH / NO ACCOUNT ENTITLEMENT / NO LIVE ADAPTER / NO CACHE LICENSE / NO PRODUCTION.  
**Owner context:** MST Handoff §157; existing Draft PR #25 source-finality and reconnect negative checks. This document records new external facts and decisions, not another fake data/replay test.

## Decision in one paragraph

A *possible* future recovery method exists: after an authenticated DNSE `ohlc_closed` WebSocket interruption, perform authenticated **historical OHLC REST** `GET /price/ohlc` for overlapping explicit `from` and `to` windows, reconcile each (provider, symbol, resolution, start-label, price basis, session, history version) against the previously observed closed-event candidate, then **quarantine** unknown, conflicting, missing or unqualified records. This is only a **candidate design**, not an authorized or proven REST replay/resume guarantee. REST history cannot reconstruct the original publisher-first-known time of an unseen message. Neither REST access nor a source quote returned by the currently connected ChatGPT DNSE MCP is permission to persist raw/derived data on Google Drive or use it in out-of-sample backtesting.

## Official vendor product facts verified

1. **WebSocket transport:** DNSE [protocol guide](https://developers.dnse.com.vn/docs/sdk/build_websocket/) specifies session welcome, HMAC authentication with timestamp/new nonce, subscription, up to eight-hour connection life, ping/pong and full resubscribe on reconnect. It does **not** state a verified replay cursor or an account-proven server guarantee of missing `ohlc_closed` events on reconnect.
2. **WebSocket products:** DNSE [market-data connection guide](https://developers.dnse.com.vn/docs/guide/market-data/connect/) distinguishes `ohlc.{resolution}.{encoding}` (forming) and `ohlc_closed.{resolution}.{encoding}` (closed). Source field `time` is a candle START label; `lastUpdated` represents last source update, **not independently verified earliest publication**.
3. **REST historical OHLC:** DNSE [endpoint guide](https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/) documents `GET https://openapi.dnse.com.vn/price/ohlc` with required `symbol`, `resolution`, `from`, `to`, `type=STOCK` for stocks, and `X-API-Key`, `X-Aux-Date`, `X-Signature`. Documented resolutions: `1,3,5,15,30,1H,1D,1W`; target MST **M5/M15/M30/H1/D1** appear, **H4 does not**. An H4 aggregate needs independent exchange-session/calendar, first-known and aggregation policy qualification.
4. **API versioning:** [DNSE version policy](https://developers.dnse.com.vn/docs/guide/versioning/api/) documents explicit date-based `version: YYYY-MM-DD` header and recommends pinning a version; default mapping can preserve an earlier API rather than surface latest behavior. Before any real request, select, test and record the vendor-supported exact version and schema; never interchange WS and REST auth methods.
5. **API request limits:** [DNSE published rate limits](https://developers.dnse.com.vn/docs/guide/ratelimits/) list an OHLC rate/quota budget (at review 50,000 requests/hour and 100,000/day), 429 throttling, and a recommendation to reduce unnecessary fetches. These are public *product* figures, not account-level authorization, stable SLA, guaranteed throughput, or blanket data-storage permission.
6. **Licensed-use restrictions:** DNSE [Lightspeed API terms](https://hdsd.dnse.com.vn/die-u-khoa-n-di-ch-vu-dnse/dieu-khoan-san-pham-dich-vu/dieu-khoan-san-pham-lightspeed-api) describe use of received market data for the customer's own securities trading, and restrict providing **raw or processed** data to third parties; third-party distribution requires written notice/approval and potentially exchange/authority requirements. An API registration or public recommendation to cache does **not** by itself establish MST's right to store historical raw candles, derived multi-TF OHLC, indicator histories, portfolios, training/backtesting artefacts or backups in a third-party Cloud. Need account-specific authorization/competent review before implementation.
7. **Current connector is not this product:** connected `mcp__MCP_DNSE__price_get_history(symbol)` exposes a **DAY-only snapshot**, no per-timeframe `resolution`, `from/to` or closed WS subscription. A successful call on ChatGPT proves only that connected *MCP surface*, not owner entitlement to standalone DNSE REST/WS from GitHub Actions or another Cloud runner.

## REST-reconcile candidate: explicit sequence, NO-GO until independently proven

1. **Do not start** unless independent source use/retention grants, account scope, private secure Cloud identity and owner-designated publisher/witness exist. Never accept a caller-provided `authorized=true`.
2. Choose **exact version, provider product, symbol, resolution, source session and price basis**. Record the requested window and how it was chosen. Do not use the DAY-only ChatGPT connector to impersonate the signed REST endpoint.
3. On WS gap/reconnect, mark all affected `(symbol, resolution, local trading session)` partitions **QUARANTINED**, not complete or latest; record a metadata-only gap diagnostic. Missing time labels can legitimately reflect no trade, auction or lunch — do not invent zero-volume OHLC.
4. If separately authorized, request REST history for **bounded overlapping windows** covering the unverified interval and a documented correction lookback, subject to per-account limits. No assumed server `resume` / `changed_since` cursor. Preserve response `version`, errors and rate-limit metadata in secure restricted logs (never secrets or public quote arrays).
5. Check server response shape, range clipping, page/row completeness, timezone/start/end label convention, vendor adjustment/basis and symbol identity. Match native historical data to the previously closed-event observation for each slot. A missing row cannot be called either "lost" or "no-trade" without authoritative venue calendar and provider exception coverage.
6. Distinguish **matching history**, **price revision**, **metadata-only revision**, **conflicting duplicate**, **out-of-order** and **unresolved missing**. Reconstructed later REST price bars have a **later first-seen-by-MST receipt time**; they cannot be backdated to the instant a WS event might have been published. Do not call this authoritative issuer first-known.
7. Only a separately verified source publisher + signed nonrollbackable historical receipt / approved rights + complete official session coverage could ever promote an untrusted candidate into a qualified closed source. **No method in PR25 currently does this**; no production Cache writer or trading flag may become true.

## Runtime feasibility: do not mistake a CI runner for a market feed daemon

| Cloud option | What is technically conceivable | Current verdict |
|---|---|---|
| Manual ChatGPT connected DNSE MCP | Read-only research of D1 source response | Not native M5+ WS/REST and not licensed persistence |
| Short-lived GitHub Actions + signed REST queries | Periodic overlap/reconciliation after account & legal approval | No current service account/secret/right; schedule can delay or skip; not an exact five-minute SLA |
| Continuous WebSocket daemon on GitHub-hosted Actions | Session streaming within individual jobs, interrupted on runner end | **Not suitable as an uninterrupted daemon**; GitHub-hosted job execution is limited to six hours |
| Independently provisioned PRIVATE Cloud service | Durable WS client + account-approved REST repair + secure credentials and receipts | Requires **new owner approval** of provider access, cost/privacy/IAM, network compliance, signer and storage; not provisioned |

Sources: [GitHub Actions runner limits](https://docs.github.com/en/actions/reference/limits) and [scheduled workflow delay/drop caveat](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows). This design must remain Cloud-only (GitHub/Google Drive and any separately owner-approved Cloud service), never Mac/MOCHI/local.

## External response required from DNSE and authorized owner/reviewer

For the specific account/product and MST Cloud-only private implementation, obtain written, scope-specific answers and independently review them **outside the public GitHub repository**:

1. Is the account entitled to *both* historical REST `/price/ohlc` and `ohlc_closed` WS? Which exact API versions, markets, symbols, intraday resolutions and history ranges?
2. Are raw history reads permitted for research and the owner's own trading only, and can raw D1/M5/etc be retained in **private Google Drive**, with precise retention, encryption, deletion and revocation rules?
3. Can MST retain **derived H4, indicator caches, audit digests and backtest/OOS artefacts**, and use price history for automated research vs only personal live trading?
4. Does hosting on GitHub Actions/Google Drive or another Cloud provider involve a **third-party disclosure or redistribution** under the account contract? What written consent, DPA, exchange terms or restriction is required?
5. Does WS support a **signed cursor/resume, per-symbol per-resolution sequence, guaranteed missed event replay,** and does `ohlc_closed` always include no-trade bars?
6. Is REST historical data complete after outages; how are retroactive corrections, ex-right adjustment, matched vs negotiated volume, holiday/session calendars and out-of-order events represented?
7. Is any provider-signed/origin-authenticated **first-known publication timestamp** or immutable correction history available, distinct from `time`, `lastUpdated` and client ingestion clock?
8. Which per-account request/per-channel limits and infrastructure constraints apply (source IP allowlist, static IP/VPN, retention, historical windows, price basis)? Do they allow Cloud runners?
9. Can the signed data be used by one unattended account-specific Cloud worker (and which key type, secret custodian and access permissions are required)? Do not supply credentials during this evidence review.
10. How should revocation, account termination and historical backup erasure be performed and audited?

**Current answer:** no signed account-specific approvals or real vendor proof received for any of these ten questions; nothing in this document should be mistaken for such a grant.

## Non-overlap, governance, acceptance

- PR #8 already covers generic provider admission/rights docket, synthetic source freshness and native M5 REST time ambiguity. PR #25's earlier files own cross-endpoint WS finality and synthetic reconnection negatives. PR #22/#23 cover offline/later Drive readback ideas; PR #24 covers real GET-only GitHub authority preflight. **No duplicate implementation** is created by this decision document.
- New source-contract findings support **M3 owner issue #9** and **M4 writer issue #10**. Source exact upstream Swing 1.8 and MST locked parity still govern.
- Accepted now: **public-source design and risk register only**. NOT accepted: live authenticated REST/WS transport, permission to keep raw/derived price data, complete native six-TF bars, guaranteed replay, provider first-known, real GDrive Cache, independent CAS, backtests or production trading.
- Do not modify original 63 V1/eight V2 modules, production permissions, watched symbols, source credentials, scheduler or main to satisfy this milestone.
