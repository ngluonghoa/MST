# MST A03 — SSI/DNSE/VCBS capability matrix, six timeframes; VCBS price-point negative QA

Date: 2026-11-10 Asia/Ho_Chi_Minh
State: Draft PR8 additive scripts-only source QA; GitHub Actions exact-HEAD pending.

## Connected VCBS read-only check (NOT retained source data)
A current MCP vcbs_get_intraday_history read for FPT, inspected in memory: data_status=available; 226 price points; each point contains time and price, not row-level open/high/low/close/volume. The session-level open/high/low has ohlcSource=price_board_live, not M5 highs/lows. This test stores NO vendor prices, raw series, source payload/digest, credentials or timestamps. An MCP price-point series cannot prove per-5-minute volume or true intra-minute high/low, even if points look regular.

## Source x timeframe matrix: documentation is not connected entitlement or signal authority

| Provider | M5 | M15 | M30 | H1 | H4 | D1 |
|---|---|---|---|---|---|---|
| SSI | Public SSI Developer Portal SDK native 5m documented; different from connected MCP | SDK native 15m documented, unconnected | SSI REST API v3 documents timeFrame=30m, but not connected/approved in MST MCP | SDK native 1h documented, unconnected | Requires approved session-aware derivation | Connected D1 schema, unqualified |
| DNSE | Public HTTP /price/ohlc resolution 5, unconnected MCP | Public HTTP resolution 15, unconnected MCP | Public HTTP resolution 30, unconnected MCP | Public HTTP resolution 1H, unconnected MCP | Requires approved aggregation | Connected D1 schema, unqualified |
| VCBS | Connected intraday time/price only, NOT OHLCV M5 | Price reference only | Price reference only | Price reference only | Price reference only | Connected vcbs_get_history D, unqualified |

References: SSI Developer Portal https://developers.ssi.com.vn/docs/tutorials/ohlc; SSI FastConnect https://guide.ssi.com.vn/ssi-products/fastconnect-data/api-specs (unverified integer resollution and timestamp label); DNSE OHLC https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/. Existing native original C2 module src/swing_trading/c2_source_capability_audit.py already labels VCBS source DataNeed.MINUTE_PRICE_REFERENCE and blocks MINUTE_OHLCV; we reuse that exact contract instead of inventing native bars. Public SDK endpoints may be distinct from currently connected MCP actions.

## Implementation and 48 tests
The new scripts/m2_a03_three_source_vcbs_capability_lab.py produces an explicit 18-cell 3x6 matrix using existing Provider, ConnectedEndpoint, DataNeed and original in-memory C2 audit; all cells keep signal_eligible=false and no source rights. The VCBS synthetic payload has just 3 invented time/price observations and invented board high/low. Its source shape can be inspected, but never made into OHLCV. Negative tests include spoofed per-row o/h/l/c/volume, repeated timestamps, incomplete points, no_data, invalid prices, bad row count, non-dict, unsupported timeframe, owner/rights bypass and explicit require_signal_eligible_bar denial for 18/18.

The only workflow is read-only GitHub PR8 with remote source-byte lock 63 original V1 and 8 pre-existing V2, 48 new unittest, fabricated JSON only. NO original V1/V2 src modifications, no real vendor data in GitHub or Drive, no Mac/MOCHI/local or other cloud, no ACL/ruleset/main mutation, merge or broker/trading.

## Gate status
Original owner A02 0/63, opt-in V2 0/8, A03 owner choices 0/14; G01–G08/OA01–OA06 OPEN. Licensed true native minute data, SSI/DNSE timestamp/closure, exchange calendars/ATO/ATC, true first-known, revision source, authorized Drive physical cache, independent floor/CAS, production and trades still NO-GO.

Next real evidence: confirm privately licensed native M5 source and timestamp policy per provider. VCBS intraday stays reference/price verification only, unless publisher directly supplies a separately qualified per-bar product.

## Confirmed GitHub-hosted QA at implementation code HEAD

At implementation PR8 HEAD `780d41f99024fb0252d82123c930e65de2162be6`, **47/47 GitHub Actions SUCCESS**. Dedicated three-source/VCBS test workflow https://github.com/ngluonghoa/MST/actions/runs/42857184915 PASS: source-byte lock 63 original V1 + 8 opt-in V2, **48/48 Python unittest methods**, exact 18 provider/timeframe cells, three fabricated VCBS price points and fail-closed minute OHLCV guard. The SHA256 `60ea091f6f5515c6e862392d4e2c4556bc0c847becafba7581cca2afc8db6a68` is a deterministic synthetic QA receipt only (not an issuer/provider signature). No live VCBS quote values or timestamps are included in the committed files or Drive cache.

Native Google Drive QA: https://docs.google.com/document/d/1Zrcsug5mQ50GAULPYdxwMy54MarTNS790jKBc3MJtbs/edit. Existing 63 V1 and 8 V2 source bytes, protected MST main and original Swing pin unchanged, PR8 remains DRAFT/unmerged. A02 0/63, A03 V2 0/8 and A03 0/14 owner signoffs remain pending, all real market/source licensing/production/trading NO-GO.

This documentation append creates a new report-containing HEAD; its 47 GitHub Actions workflows must be checked on that exact SHA separately before declaring the final report checkpoint PASS.


## Connected SSI and DNSE date/clock source-mode observation — 2026-11-10

Actual read-only connected SSI intraday FULL-DAY returned 226 OHLCV-shaped timestamped rows; 223 adjacent gaps were 60 seconds, and two gaps were larger. These are row shapes and apparent one-minute cadence, not a vendor-attested native M1 or M5 contract, exact START/END, bar closure, historical first-known, or lawful retention. A historical request for a day numbered greater than 12 had a single day-first interpretation; a latest-mode date token had both numeric components <=12, so DD/MM versus MM/DD could not be independently resolved with a single universal parser. There is no source-authorized proof that the two modes share a uniform date format. Raw live quotes and timestamps were inspected in memory, NOT saved here, in GitHub, or in Google Drive.

Connected DNSE price_get_history returned 248 daily-shaped OHLCV observations in columns t/o/h/l/c/v across approximately a year, with 1-day and weekend-sized spacing. The connected MCP accepts only symbol; it has NO native resolution=5 query selector. Separate public HTTP documentation for native minute OHLC does not automatically qualify connected DNSE MCP as M5.

The existing A03 scripts-only three-provider lab now adds a candidate-only strict SSI date parser: both DD/MM and MM/DD date interpretations are enumerated, and ambiguous tokens are rejected EVEN if the requested day or current date appears to resolve one. An unambiguous token passes only shape-level validation, not issuer/timeframe rights. Original C2 in-memory shape checks are exercised on manufactured SSI and D1 DNSE payloads. DNSE connected minute OHLCV request remains BLOCKED. The existing dedicated PR8 workflow is expanded from 48 to 64 unit tests; no additional workflow, no source-module change, no real vendor data in test artifacts. Exact GitHub CI pending after this update.


## Verified GitHub-hosted QA: SSI/DNSE connector-mode date risk + previous VCBS and 3x6 matrix

At implementation code HEAD 048bd989884e464ec086949063bdfe012cfbcd94, **47/47 GitHub Actions workflows SUCCESS**. Dedicated original-source-locked QA run https://github.com/ngluonghoa/MST/actions/runs/42860022876 PASS: 64/64 Python unittest methods, existing 18 source-timeframe cells, 3 fabricated VCBS minute price points, and the NEW manufactured SSI intraday/DNSE D1 C2 in-memory shape observations. Full original 63 V1 + eight preexisting opt-in V2 source-byte parity verified against pinned Swing/master/PR on GitHub-hosted runner.

New distinct findings: actual connected SSI day-scoped FPT read returned 226 OHLCV-shaped, timestamped rows (223 adjacent 60-second differences, two longer breaks). It does NOT supply an independently attested native M5 resolution/START-END/closure/source rights. Connected DNSE FPT history returns 248 D1 OHLCV-shaped values over approximately a year with day/weekend gaps and no selectable M5 resolution in its MCP arguments. SSI source-mode date-token ambiguity requires conservative parser denial rather than an unverified assumption that both latest and date-range modes emit identical DD/MM or MM/DD order. Vendor data was inspected transiently in memory; NO raw quotes, values, timestamps or source digests entered committed code, fixtures, GitHub workflow logs or Drive market cache.

Synthetic report checksum c0a53fff79e752778de07bcef6275f7703039bf43e9804f3801ce370bfdb9dd5 proves only deterministic fixture output; NOT an authoritative source issuer, first-known or owner approval. Native Drive QA mirror: https://docs.google.com/document/d/1Zrcsug5mQ50GAULPYdxwMy54MarTNS790jKBc3MJtbs/edit.

IMPORTANT: This append creates a new *report-containing* PR HEAD. Claim 47/47 on that final HEAD only after querying its actual GitHub Actions workflow run conclusions. Original V1/V2, protected main, permissions, release and trading remain unchanged and NO-GO.

## 2026-11-11 — distinct SSI clock freshness + cross-product M5 comparability acceptance test

New additive only scripts/m2_a03_connected_source_freshness_lab.py and tests/test_m2_a03_connected_source_freshness_lab.py add **24 strictly synthetic clock and source-mode tests** without a new workflow (previous 64 source-shape/VCBS tests remain in place; combined 88). The existing PR8 GitHub Actions workflow reruns live GitHub byte-lock original 63 V1 and eight preexisting opt-in V2 and saves only deterministic synthetic metadata. No source prices, raw sample rows, user IDs or credentials are committed.

Important separation: SSI MCP latest=true is a SINGLE QUOTE_REFERENCE, while range=1d is a WHOLE_SESSION minute-OHLCV-shaped response; neither is an issuer-certified M5 bar. Connected DNSE price_get_history is D1 history, and VCBS minute intraday is PRICE_REFERENCE, so these three surfaces cannot be used to claim independently confirmed newest native M5 candles. SSI source meta.asOfUtc is a connector snapshot timestamp; it is NOT independently established as first-known or exchange publisher clock. A syntactic parse can check that an unambiguous historical date/time is not after snapshot-asof, but cannot prove freshness, bar closure, official trading sessions or rights. The new witness explicitly denies ambiguous SSI latest date tokens even if the apparent request date would choose one, and denies future-relative event/observation clocks. A fabricated 900-second lag is not a universal tolerance or service-level assertion: official holiday, halt, auction and feed schedule must be independently verified before setting a signal freshness policy.

All vendor roots, licensed source history/retention, true publisher first-known, current market session/ATO/ATC calendar, M5 source rights, physical Google Drive market cache, independent protected CAS/floor, owner signoffs and trading remain NO-GO. GitHub source/module tree unchanged in src/, only scripts/tests/QA workflow docs on Draft PR8. Exact final Actions SHA and QA counts to be appended after live GitHub observation.


## 2026-11-11 source-clock and inter-provider freshness boundary — verified implementation-head GitHub QA

Distinct additive-only scripts/m2_a03_connected_source_freshness_lab.py and tests/test_m2_a03_connected_source_freshness_lab.py extend the existing three-provider capability workflow, not production source or an additional CI workflow. This adds **24/24** source-clock, SSI latest/day mode, ambiguous date, asOf/observer ordering and cross-source-M5-incomparability tests to the earlier **64/64** VCBS and SSI/DNSE source mode tests (88 tests total). Tests use invented source/clock values; no actual trading data or vendor raw timestamps are persisted.

The original connected C2 contracts distinguish SSI latest QUOTE_REFERENCE/LATEST_SINGLE from SSI full-day MINUTE_OHLCV-shape/WHOLE_SESSION, DNSE connected D1 history and VCBS minute PRICE_REFERENCE. A connector-reported meta.asOfUtc and syntactically parseable event date are NOT independently verified market publisher first-known times, real M5 candle close, official session/calendar freshness or issuer data rights. A plausible 900-second fabricated lag is not a production stale threshold. SSI DD/MM/MM/DD ambiguity is denied even if the request or current date apparently resolves one meaning. It is unsafe to rank or merge these incomparable source products as a consensus freshest M5 signal.

Code HEAD `69013548e4972bf10ad73123e478ccd9fcd93d3e` independently verified **47/47 GitHub Actions SUCCESS**. Dedicated https://github.com/ngluonghoa/MST/actions/runs/42862557445 PASS: 64 + 24 = 88 direct targeted tests, original 63 V1 and 8 V2 live upstream/main/PR source byte lock PASS, synthetic-only artifact PASS. Fabricated source-clock receipt SHA256 `2f2c863e18e8767476505f9295dd65184d4a92e2ea585c0443b5767bbe73b9ff` is only a deterministic test checksum, not external source or owner certification. Permanent QA native Google Drive: https://docs.google.com/document/d/1FHpi2vrgiVCInoRqQUOxrAox85D_0DhyFY-X9G_cqrQ/edit .

The documentation append changes PR8 HEAD; FINAL report-containing SHA requires separate full 47-workflow GitHub readback before claiming the final checkpoint CI success. PR8 remains Draft/unmerged, MST protected main and pinned upstream unchanged, all 63+8 original V1/V2 source files unchanged. A02 owner 0/63, A03 V2 owner 0/8 and A03 choices 0/14, G01-G08/OA01-OA06 OPEN. Licensed M5 market source/first-known/calendar/rights, authorized physical Drive market cache, independent floor/CAS, release/trading remain NO-GO.


## 2026-11-11 public provider API product reconciliation (NOT connected source acceptance)

Two useful distinct official documentation findings were checked against provider-hosted text:
(1) SSI REST API v3 GET /api/v3/data/ohlc explicitly lists timeFrame=30m, 5m, 15m, 1h, 1d; this is a distinct developer API from the current connected SSI MCP and the separate SDK tutorials, which list 1m/3m/5m/15m/1h/1d. We therefore corrected SSI M30 in the existing three-source six-timeframe matrix from undocumented to PUBLIC REST-v3 M30 DOCUMENTED, **unconnected, no credentials or retention grant and no signal authority**. Official reference https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc .
(2) DNSE public Market Data WebSocket documentation https://developers.dnse.com.vn/docs/guide/market-data/connect/ documents two DIFFERENT streams: ohlc.{resolution}.{encoding} carrying a developing candle, and ohlc_closed.{resolution}.{encoding} carrying a closed candle. For both stock payload examples the time field represents candle START, with a separate lastUpdated. Resolution 5 is publicly described. This scope is the native WebSocket product; it DOES NOT establish START/END semantics of DNSE separate HTTP /price/ohlc t field nor the connected DNSE MCP, which is D1 only. The closed-channel wording cannot prove authenticated first-known, vendor correction lineage, historical completeness, connection permission, archival rights or publisher source identity from caller-supplied field strings.

New additive scripts/m2_a03_documented_ohlc_transport_boundary_lab.py and 26 focused synthetic tests enforce a documented-transport classifier. A fabricated ohlc developing event remains non-closed even after its nominal interval passes; a fabricated ohlc_closed event after interval end is a shape candidate only and stays unverified/not signal-eligible, and a purported closed message before interval end is rejected. Malformed timestamps, bool/millisecond epoch, spoofed source attestation, wrong resolution, negative volume, invalid price/geometry and future observation fail closed. It emits NO actual market values and does not open WebSocket. Existing 64+24 source-mode/freshness QA remains, now 114 targeted test cases through the SAME workflow.

Nothing in original V1 (63 modules) or pre-existing V2 (8 modules), provider permissions, protected MST main or running production changed. Real SSI REST-v3 and DNSE WS are NOT currently connected and therefore cannot be treated as approved current MCP market source. Licensed source evidence, time rights and first-known/corrections and physical Drive cache remain NO-GO. Exact code/report GitHub Actions outcomes to be written only after observed CI.


## GitHub-hosted source-transport QA confirmation — 2026-11-11

At **implementation code HEAD** `3a658a39160d6dbe148cd0b6474306c0641e935a`, independently verified **47/47 GitHub Actions SUCCESS**. The existing dedicated source-capability workflow https://github.com/ngluonghoa/MST/actions/runs/42867699575 PASS: remote pinned Swing/main/PR original 63 V1 plus 8 existing V2 source byte lock, **64 prior + 24 source-clock + 26 new documented-transport = 114/114** test cases, read-only fabricated source-transport receipt, no real market-data artifact. Source docs establishing SSI REST v3 timeFrame=30m: https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc ; DNSE forming vs closed WS and time as bar START: https://developers.dnse.com.vn/docs/guide/market-data/connect/ . The printed / returned fake input shapes are NOT authenticated channel origin, rights or current production feed.

Initial test commit `425fac144cd3dddcd92c7d2f1f29782dfe39c3bb` failed foundation and new workflow due solely to a **synthetic observer clock error**: the fabricated developing-candle sample used an update timestamp later than the test's observer. That was corrected at `3a658a39160d6dbe148cd0b6474306c0641e935a` by placing the synthetic observer after BOTH fabricated updates; no original V1/V2 bug or approved real source was inferred. Existing 18 source/timeframe cells still have NO trading authority; the one corrected public documentation fact is SSI REST-v3 M30 availability separate from the connected SSI MCP.

Permanent native Drive QA: https://docs.google.com/document/d/1Yv0a84iO0QylgWWArZsrnRmugbu53PrCi_cIfcpjrcs/edit . The report append creates a NEW report-containing PR HEAD which must be checked separately for all 47 Actions SUCCESS before claiming terminal checkpoint success. Draft PR8 unmerged, protected main / pinned original Swing unchanged, A02 0/63 + V2 0/8 + A03 0/14, G01-G08/OA01-OA06 OPEN; real feed licensing, authenticated delivery/first-known/history, official exchange calendar, physical Drive licensed data cache, protected CAS/floor and production/trading NO-GO.
