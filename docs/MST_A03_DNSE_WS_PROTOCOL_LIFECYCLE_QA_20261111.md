# MST A03 — DNSE WebSocket Client Lifecycle Documented Protocol (synthetic NO-GO)
Date: 2026-11-11 Asia/Ho_Chi_Minh
Status: DRAFT PR #8 additive-only documented protocol + synthetic test. No authenticated live WebSocket call.

## Evidence basis
DNSE official documentation: https://developers.dnse.com.vn/docs/sdk/build_websocket/
- Endpoint `wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json`. This endpoint was NOT called.
- New welcome/session_id; authenticate within 30 seconds; HMAC-SHA256 uses api_key, API secret, timestamp and unique nonce. Timestamp allowed within ±300 seconds of server, nonce reuse is forbidden within 10 minutes by provider.
- Subscribe only after auth_success, await subscribed acknowledgment; MST's hypothetical M5 study subscribes to both `ohlc.5.json` and `ohlc_closed.5.json`.
- DNSE sends PING about every 3 minutes; PONG must follow within 1 minute. Each connection lasts max 8 hours.
- On disconnect, new welcome/session_id, fresh auth timestamp/nonce and all subscriptions again. Documented closure cases include codes 1000/1008/1013 and network intermediaries 1001/1006/1011/1012; guidance suggests backoff for retries.
- The public guide specifies reconnection handshake. It does NOT supply an authenticated event sequence, historical exactly-once delivery, source-issued correction chain, mandatory closed-candle continuity, guaranteed backfill contract or data licensing.

## Additive test-only artifacts
- `scripts/m2_a03_dnse_ws_protocol_lifecycle_lab.py`
- `tests/test_m2_a03_dnse_ws_protocol_lifecycle_lab.py`
- Existing `.github/workflows/m2-a03-three-source-vcbs-capability.yml` extended, not a new workflow.
- 28 new fake lifecycle tests: handshake ordering, a fresh session, fake nonce reuse rejection, auth deadline/clock skew, dual M5 subscription policy, subscribed ACK before hypothetical data, PING/PONG identity/deadline, eight-hour expiry, reconnect authorization flow, immutable receipt and no real source authority.
- Only invented control timestamps, session labels and nonce labels appear in tests. Never use actual api_key/api_secret, real DNSE OHLCV, source timestamp sequences or issuer credentials.

## Gate / policy
A synthetic `auth_success` is NOT independent DNSE issuer authentication. A synthetic `subscribed` ACK is NOT entitlement, right to retain/re-publish historical OHLCV, or proof of bar completeness. A new session_id is NOT a publisher replay token. A heartbeat/PONG is NOT a history backfill. Always keep market cache, production and trading NO-GO. Original Swing 63 V1 and eight opt-in V2 must remain byte-identical, protected MST main untouched, Draft PR #8 unmerged.

A real owner-authorized experiment requires external issuer/license evidence, approved secure cloud secrets, a legitimate authenticated stream session, vendor-approved correction/replay/backfill, official HOSE/HNX/UPCOM market calendar, and validated first-known/source clock. Do not create secrets or connect automatically.

GitHub exact SHA / CI evidence: PENDING until independently observed after writing this doc.

## Verified GitHub cloud implementation checkpoint — 2026-11-11
Initial exact implementation HEAD `4b6af5d6bd98761b39d29a79bd070d519976fa03`: independently read back 47/47 GitHub Actions SUCCESS, including Foundation CI Python 3.11/3.12 and dedicated read-only three-provider/source-lock QA run https://github.com/ngluonghoa/MST/actions/runs/42876484957 . Dedicated job succeeded on new 28/28 documented lifecycle negative methods alongside previous 146/146 targeted tests (174 total). Remote-original source lock on 63 inherited V1 and eight pre-existing V2 still SUCCESS, protected main `4048f91beaaa3410116d97e35896c8b688384e19` and pinned source Swing `cd90c1babae8912db31490ad614fc2ad2f868042` unchanged, Draft PR8 unmerged. This evidence is only deterministic fabricated client-control traces, not a live vendor WebSocket result, HMAC issuer trust, real bar retention license or release permission.

This report-containing document revision should itself be checked at exact GitHub PR HEAD after commit; do not infer CI from the earlier implementation SHA. All original owner gates A02 0/63, V2 0/8, A03 choices 0/14, G01-G08 and OA01-OA06 OPEN. Provider authenticated reconnect/backfill/first-known/calendar, physical market Drive cache, independent CAS/floor, production and trading remain NO-GO.
