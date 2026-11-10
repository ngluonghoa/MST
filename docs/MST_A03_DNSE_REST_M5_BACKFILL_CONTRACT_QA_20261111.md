# MST — A03 DNSE REST M5 historical OHLC nextTime and WS closed-bar reconciliation (NO-GO)

Date: 2026-11-11 Asia/Ho_Chi_Minh
Status: Draft PR #8, new additive scripts-only contract QA; no authenticated provider calls.

## 1. Newly verified official public documentation
DNSE REST OHLC history: https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/
GET https://openapi.dnse.com.vn/price/ohlc
Required query: symbol, resolution, from, to; resolution includes "5" and other documented options.
Required headers: X-API-Key, X-Aux-Date and X-Signature; an API version header is shown separately.
Response: parallel OHLCV arrays t/o/h/l/c/v and nextTime. t uses Unix seconds. nextTime=0 is documented as no further data; positive nextTime identifies a subsequent candle when a request's history is incomplete.
WebSocket OHLC Closed: https://developers.dnse.com.vn/docs/guide/market-data/connect/ documents ohlc_closed.5.json closed events; separate forming stream is ohlc.5.json.

These are public API products; the currently connected DNSE MCP price_get_history is symbol-only DAY history, not the REST M5 interface nor WebSocket. Public documentation does not establish account entitlement, licensed retention, revision history, source publication timestamps, provider event sequencing, mandatory backfill completeness or official exchange calendar. nextTime is a history pagination marker, NOT a changed-since indicator or an authenticated correction ledger.

## 2. Explicit test-only implementation
- scripts/m2_a03_dnse_rest_m5_backfill_contract_lab.py
- tests/test_m2_a03_dnse_rest_m5_backfill_contract_lab.py
- Existing .github/workflows/m2-a03-three-source-vcbs-capability.yml extended; no new workflows.
- Original 63 Swing V1 and eight pre-existing opt-in V2 source bytes locked, not edited.

23 new focused unit test methods exercise parallel response arrays, time ordering, OHLC geometry, negative/boolean volume, malformed timestamps, invalid nextTime, stuck cursor, extra pages after nextTime=0, out-of-window candidate, synthetic numeric overlap/conflict with fake WS closed, and persistent NO-GO for source authority/trading. Test data consist ONLY of invented FPT-like numeric candles, no real quotes, source timestamps, API key, secret, signature or access token.
Pagination is an explicit hypothetical request sequence, never an actual REST client. The loop makes no network calls and never enables data storage. Numeric agreement between fake WS and fake REST events does not certify identical provider candle identity because REST time START/END semantics and first-known remain unverified.

## 3. Owner-gated evidence needed before integration
A. Authorized DNSE Market Data REST M5 and WS OHLC Closed entitlements (including symbols/venues, rate and connection limits), with issuer-backed evidence and retention terms permitting private Google Drive caching and revisions.
B. REST nextTime contract for inclusive/exclusive from/to, no-trade intervals, rate limiting, partial responses, and whether gaps can actually be backfilled.
C. How historical bar corrections and late/out-of-order WS events are published, first-known proof, timestamp label semantics, exchange sessions/ATO/ATC/holidays/halts.
D. Real source clock, official unit and price basis, corporate-action adjustment, and permitted request/data storage security.
E. Re-test on licensed Cloud-only credentials after distinct owner approval; never persist secrets, market rows or signed quote digests in GitHub/Docs.

No automatically enabled live M5 source, authorized Drive cache, actionable signals, production release or trading. Original A02 0/63, A03 V2 0/8 and owner choices 0/14; G01-G08/OA01-OA06 OPEN.

## 4. GitHub CI receipt
PENDING: exact commit, 23/23 new focused tests and full 47-workflow remote CI must be read back before marking PASS.
