# MST M3 — Connected provider cross-surface D1 finality boundary (read-only)

**Observed 2026-11-12, Asia/Ho_Chi_Minh. Status: M3 source finality NO-GO; experimental metadata-only safeguard, not a live adapter, trading signal or Cache release.**

## New actual observation — 2026-11-12 FPT, no prices retained in GitHub

Connected SSI/DNSE/VCBS app calls were made read-only; this report intentionally keeps ONLY response shapes, counts and source lifecycle flags. It does not replicate vendor quote arrays, credentials, market prices or a market Cache.

| Connected endpoint | Requested shape | Bounded structural observation | What cannot be inferred |
|---|---|---|---|
| SSI marketdata_list_stock_daily_data | FPT, range 1d, toDate 11/11/2026 | 2 D1 rows for 10–11 Nov; status ok; response has an asOfUtc envelope | Vendor candle-close signature, historical first-known, source retention right |
| SSI marketdata_list_intraday_stock_infor latest | FPT latest | 1 row labeled 12/11/2026, 14:45:00; OHLCV-like reference fields, not whole session | Closed M5, complete session or source clock authenticity |
| DNSE price_get_history | FPT, DAY-only MCP | 248 columnar D1 records: t,o,h,l,c,v all aligned, nextTime=0; last t corresponds to 12 Nov 09:00 +07 | This is a row timestamp, NOT proof that this D1 bar has closed; vendor first-known or licence |
| VCBS vcbs_get_history interval D | FPT, 4 D1 rows, raw basis | Today 12 Nov D1 row explicitly provisional=true; matched volume scope and price_unit VND | Not ready as a fully closed daily bar |
| VCBS vcbs_get_intraday_history | FPT, current session | 226 series entries (time,price), 10 recentTrades (time,price,volume); ohlcSource=price_board_live; ohlcProvisional=false | That flag belongs to the endpoint's *board OHLC*, NOT to vcbs_get_history's D1 row, nor to each per-minute OHLCV candle |

**Important nuance:** The two VCBS flags are not necessarily contradictory: they describe different product scopes. Conservatively, never transfer finality from one endpoint to another, even within the same provider. The DNSE D1 historical t is a time label, not a closed-event receipt. SSI's latest reference is not a complete source-native M5 bar. A late clock, no remaining pagination or a matching date likewise does not certify source finality.

## Reuse and non-duplication

- The original main `src/swing_trading/c2_source_capability_audit.py` and existing Draft PR8's three-source capability/freshness/M5 timestamp tests remain the prior broad source contracts.
- This isolated PR adds one **narrow, distinct cross-surface finality hint** regression, not a new provider transport, generic source router, fake CAS, Drive two-read experiment, first-known issuer, actual provider entitlement or production logic.
- New `scripts/m3_cross_surface_finality_gate.py` and `tests/test_m3_cross_surface_finality_gate.py` operate on typed endpoint names, calendar dates and booleans only. All outcomes keep closed_bar_verified=false, cache_publish_authorized=false and signal_eligible=false. No source snapshots are embedded.

## Verification and acceptance still OPEN

Provider-issued and independently authenticated bar-close/first-known semantics; official VN venue calendar/auction/missing-bar classification; native M5/M15/M30/H1/H4/D1 historical fidelity; source raw/derived storage, retention and backtest rights; independent signed publisher/CAS/nonrollbackable highwater; controlled Drive media-readback; owner module approvals and release/trading.

No source market data, GitHub secrets/variables/rulesets, ACL, protected main, Watchlist, automation or Cloud production resources are changed by this scoped source-finality contract.

Official cross-check: [DNSE historical OHLC REST](https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/), [DNSE OHLC closed WebSocket](https://developers.dnse.com.vn/docs/guide/market-data/connect/), [SSI historical availability](https://developers.ssi.com.vn/docs/faq/market-data).

**Exact-head CI:** to be appended after GitHub Actions verifies this Draft PR; absence of a completed run remains unverified.


## 2026-11-12 follow-up — official DNSE OHLC Closed channel, distinct from connected DAY MCP

Public DNSE documentation (read on 12 Nov 2026) explicitly separates the **in-progress** WebSocket subscription `ohlc.{resolution}.{encoding}` from **closed-candle** `ohlc_closed.{resolution}.{encoding}`. The former updates while trades happen; the latter is described as emitted at candle close. The example message's `time` is the **candle START Unix timestamp**, while `lastUpdated` is a last update timestamp; **neither is the independently authenticated earliest publication/first-known receipt**. A theoretical `time + 300s` for M5 is not an official auction/lunch/calendar close attestation.

Documented channel resolutions are `1,3,5,15,30,1H,1D,1W`: within MST's required six timeframes this directly lists **M5/M15/M30/H1/D1**, but **not H4**. H4 therefore remains a derived-timeframe validation obligation; never advertise native DNSE 4H in this product. These WebSocket products and the separate signed HTTP `GET /price/ohlc` are **NOT present** in the currently connected DNSE MCP `price_get_history` DAY-only interface. No market data or feed connection was retrieved through this public-document research.

Narrow new `scripts/m3_dnse_documented_closed_channel.py` and `tests/test_m3_dnse_documented_closed_channel.py` distinguish formers vs closed channel *envelope labels* (exact resolution and type, start/last-updated ordering, explicit UTC observation, no fictitious fixed D1/W close), reject REST/DAY-MCP impersonation and caller-asserted entitlement or first-known, and always keep `source_native_closed_event_verified=false`, `licensed_cache_retention=false`, `cache_publish_authorized=false`, `signal_eligible=false`. These synthetic tests cannot simulate an authenticated vendor WebSocket connection. Real owner/vendor rights and identity, client-side receipt provenance, reconnect/gap/revision/duplicate behavior, H4 derived semantics and exchange calendar still need a separate approved authorized cloud client.

Official primary sources:
- https://developers.dnse.com.vn/docs/guide/market-data/connect/ — WS channels, candle-start time and lastUpdated examples
- https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/ — signed REST history, independently documented API product

**Engineering interpretation:** DNSE's description of unchanged closed events is vendor documentation, NOT proof that the user's account may subscribe, or that a late arriving/revised historical record can never exist. Never treat `ohlc_closed` string, `lastUpdated` or client receipt time as independently authenticated first-known.


## 2026-11-12 follow-up — DNSE documented reconnect, authenticated-session and gap-recovery limitations

**Primary official documentation verified:**
- https://developers.dnse.com.vn/docs/sdk/build_websocket/ — the documented WebSocket protocol requires a welcome message, HMAC auth with timestamp+fresh nonce within 30 seconds, then explicit subscribe ACK; reconnect creates a NEW session_id and requires fresh timestamp/nonce and all subscriptions repeated.
- The official same page documents a maximum 8-hour connection lifetime, server PING roughly every 3 minutes, PONG within 1 minute, close code 1008 for expiry/heartbeat/policy and 1013 for overloaded slow client; exponential backoff is recommended for retries.
- https://developers.dnse.com.vn/docs/guide/market-data/connect/ — distinguishes forming `ohlc` and published-on-close `ohlc_closed` event families and lists their time/resolution fields.

**Crucial evidence distinction:** These pages prescribe **how to reconnect**, but no verified, per-symbol/per-timeframe monotone delivery sequence, guaranteed replay from cursor, complete REST repair on reconnect, or externally signed issuer first-known / revision origin was established in the reviewed protocol. Therefore even `auth_success`, subscription ACK and adjacent later candle-start labels do NOT prove that messages were not missed while disconnected. Equally, a large gap in candle-start labels might represent auction/lunch/no-trade/holiday/special venue behavior; it is a **potential** delivery/calendar gap until an official market schedule and vendor proof are checked. Distinguish duplicate exact slot vs conflicting payload and out-of-order correction; never silently overwrite earlier accepted state.

**New additive test-only implementation** in the same Draft PR25:
- `scripts/m3_dnse_reconnect_gap_negative_lab.py` — metadata-only SYNTHETIC protocol-phase/epoch state machine; requires welcome, a fresh synthetic auth-ack nonce marker, and exact re-subscription before receiving synthetic `ohlc_closed` slot labels. Detects same-slot duplicate, conflicting claim, out-of-order label, clock skew and potential time jump; bounds stored synthetic slot metadata; quarantines suspected faults. A reconnect always flags **unverified delivery history**, regardless of later chronological adjacency. All vendor identities/rights, first-known, real replay, Cache and signal fields remain permanently FALSE.
- `tests/test_m3_dnse_reconnect_gap_negative_lab.py` — 37 negative/offline unit methods, including reconnect code 1008, pseudo-network loss 1006, repeated nonce, stale epoch, missing subscription, duplicate/conflict, simulated lunch gap, no false calendar completeness, bounded capacity and no quote/secret fields.
- This does **NOT** open a WebSocket, construct a HMAC request, authenticate any provider account, collect market data, write a Google Drive cache, prove raw/derived retention rights, or upgrade the separate current connected DNSE DAY-only MCP. All handshake IDs/nonces/digest tags are **SYN-... fixture markers**, not vendor replies and not market payload hashes.

**External evidence still required before a future live admission:** independently approved DNSE subscription/Cloud credentials and licence, protected Cloud runner and identity, authenticated WS origin and verified instrument+timeframe delivery contract, vendor-provided resume/backfill/cursor or proved alternative recovery, official venue calendar/auction/no-trade, correction/revision and first-known history, H4-derived chain, signed audit and nonrollbackable publisher floor, owner go-live approval. No real market cache or trading until all gates pass.

**CI checkpoint:** verify the final exact PR25 HEAD in GitHub Foundation CI after this commit. The new protocol lab is an intentionally untrusted negative oracle, not a live transport or a production cache safety proof.


## 2026-11-12 §161 — private-source D1/intraday/ATC volume reconciliation

A **new manual, user-authorized, private Google Drive source QA** compared three independent real connected MCP surfaces: SSI minute-level source reported volume (holding the 14:45 auction observation separately), DNSE DAY source reported volume, VCBS D1 board-supplement and VCBS intraday board matched-volume/ATC. The official February 2026 HOSE schedule [HSX PDF](https://staticfile.hsx.vn/Uploads/UploadDocuments/2453338/HTGD_Quy%20dinh%20can%20biet%20khi%20GDCK%20tren%20HOSE_T2.2026.pdf) documents morning/afternoon continuous order matching, lunch interruption, ATO and **ATC 14:30–14:45** as distinct order-matching phases. The observed SSI 14:45 row is not certified as a native minute/M5 closed bar; it must not be silently inserted into continuous-time M5.

The separate private source evidence found: two of three observed symbols had numerically matching session totals across SSI, DNSE and VCBS; **one symbol had an exact nonzero SSI/DNSE-vs-VCBS total volume disagreement that numerically matched its SSI-vs-VCBS ATC component delta.** A second read-only live query repeated the discrepancy. This **does not prove root cause**; provider feed scope, corrections, auction definitions, matched/put-through/odd-lot inclusion and first-known are not independently aligned. **Do not embed the private quote payload or actual symbol values in the public PR.** Source records and exact observations stay in private MST Google Drive and canonical Handoff §161.

Added the small, strictly synthetic **`scripts/m3_cross_source_volume_reconciliation.py`** to existing Draft PR25, plus **`tests/test_m3_cross_source_volume_reconciliation.py`** (31 offline methods). It enforces exact provider surface/symbol/local session and integral unit shares, source isolation, deterministic order and pairwise volume deltas; optionally computes exact ATC arithmetic localization, but the report marks *publisher verification, volume-basis equivalence, source rights, closed-bar finality, trusted first-known, cache publisher, production, signals* all **FALSE** even where sources agree. It rejects self-attested rights, counterfeit publisher origin, cross-day/symbol and malformed/duplicate inputs. The code does not call SSI/DNSE/VCBS, read actual quote files, accept signed source evidence or write market Cache.

**GO/NO-GO:** A numeric mismatch must be quarantined for source QA; numerical agreement remains observational only and does not authorize source-derived signal readiness or native TF finality. The independent actual private 3-symbol reconciliation document is linked from Handoff §161, not stored as market payload in the public repository.


## 2026-11-12 §162 — source-volume requery receipts and a private D1 incremental QA join

After the §161 discrepancy, the owner requested further **actual** source collection. Five connected read-only source surfaces were re-queried for the same HOSE stock/day (SSI minute OHLCV, SSI D1, DNSE D1, VCBS D1 and VCBS intraday board). The previously observed cross-provider **100-share discrepancy and matching ATC-component discrepancy** persisted, with no observed native numeric OHLCV revision in comparable data. SSI D1 had not yet returned a current-session daily row; current-day SSI minute bars and another vendor's board supplement **cannot be silently promoted** to SSI D1. One optional VCBS D1 metadata field changed from an explicit `null` in the prior saved view to omitted in the requery; numeric O/H/L/C/V were unchanged. This illustrates **semantic field-level change vs content revision** and why raw JSON equality alone can create a false OHLCV revision alert.

Private Google Drive contains a **new readback-verified DCM follow-up receipt** linking the earlier source snapshots and the latest observed counts, plus a separate **private, readback-verified D1 incremental QA join index** linking the D1 manifest, earlier delta index, intraday manifest, initial cross-source QA and latest DCM follow-up. One symbol is quarantined for volume conflict; the two observed-agreement symbols are NOT certified as eligible for production signals. Earlier snapshots and source rows are untouched. Private raw price payloads are not included in the public repository.

The same existing Draft PR25 `scripts/m3_cross_source_volume_reconciliation.py` now provides a **pure** `compare_volume_refreshes(previous, current, previous_received_utc, current_received_utc)` preflight that compares exact typed provider/symbol/day share counts and optional ATC counts across two monotone, explicitly UTC-local receipt times. It returns deterministic changed-source lists, separate source conflict vs observed numeric agreement, and only a **candidate** append-receipt or volume-revision/recompute instruction. It does not compare complete raw O/H/L/C/V, cannot certify matching first-known or provider revisions, and does **not** execute the suggested operation, write Drive, grant a live Cache V2 source or trade. No timestamp selfattestation can convert the local receipt clock into a vendor publisher timestamp. New offline methods cover unchanged disagreement, new/corrected mismatch, ATC-only revisions, missing/changed ATC evidence, wrong source sets, local clock regression and timezones, and no false source promotion.

**Next real integration:** keep source-partitioned **complete OHLCV** comparison from the manually stored private Drive snapshots as the actual revision authority for the current owner-driven capture flow; use this preflight as a metadata-only **volume/ATC alert** in front of any future independently authorized writer, never as proof that equal volume means unchanged prices. Exact source session/auction matching, close and first-known for the 6 TF chain remain separate.


### §162 follow-up: source-specific SSI D1 freshness, not provider-wide freshness

An additional live read-only check used **`SSI.marketdata_list_daily_stock_infor`** (detailed daily product), **`SSI.marketdata_list_stock_daily_data`** (compact daily product), and an independent **`VCBS.vcbs_get_stock_price`** board endpoint for the same observed local trading session. The SSI **detailed D1** endpoint returned the current session's native matched-volume field, whereas the SSI **compact D1** endpoint had not returned that day at the prior requery. Therefore the correct data-status key is **`(provider, endpoint_product, symbol, timeframe, local_session)`**, NOT merely provider/symbol/D1. Freshness of one SSI product must never be transferred to the other by name.

The independent SSI detailed matched-volume and VCBS stock-price board lot again showed the same previously observed cross-provider aggregate-volume disagreement; no publisher-corrected root cause or source entitlement was established by these observations. SSI full/raw intraday pagination returned **DOWNSTREAM_UNAVAILABLE** during this check; absence of that product does not invalidate the separately returned SSI minute-source or detailed-D1 records. **Do not embed the source row data in this public repo.** The new private evidence Doc and separately versioned **D1 QA join index V2** supersede the earlier V1's broad D1-availability description **by reference**, preserving both older artifacts and their full audit trail. A correct future refresh must record the endpoint-specific metadata, semantically normalize optional absent-vs-null fields for numeric OHLCV revisions, and keep cross-provider source-basis QA explicit.

No real automatic Cloud writer, source-close attestation, H4 derivation, nonrollbackable manifest commit, publisher first-known or production trading is implied by source endpoint freshness.
