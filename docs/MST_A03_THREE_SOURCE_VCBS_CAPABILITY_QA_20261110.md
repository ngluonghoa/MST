# MST A03 — SSI/DNSE/VCBS capability matrix, six timeframes; VCBS price-point negative QA

Date: 2026-11-10 Asia/Ho_Chi_Minh
State: Draft PR8 additive scripts-only source QA; GitHub Actions exact-HEAD pending.

## Connected VCBS read-only check (NOT retained source data)
A current MCP vcbs_get_intraday_history read for FPT, inspected in memory: data_status=available; 226 price points; each point contains time and price, not row-level open/high/low/close/volume. The session-level open/high/low has ohlcSource=price_board_live, not M5 highs/lows. This test stores NO vendor prices, raw series, source payload/digest, credentials or timestamps. An MCP price-point series cannot prove per-5-minute volume or true intra-minute high/low, even if points look regular.

## Source x timeframe matrix: documentation is not connected entitlement or signal authority

| Provider | M5 | M15 | M30 | H1 | H4 | D1 |
|---|---|---|---|---|---|---|
| SSI | Public SSI Developer Portal SDK native 5m documented; different from connected MCP | SDK native 15m documented, unconnected | Not proven for current connected API | SDK native 1h documented, unconnected | Requires approved session-aware derivation | Connected D1 schema, unqualified |
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
