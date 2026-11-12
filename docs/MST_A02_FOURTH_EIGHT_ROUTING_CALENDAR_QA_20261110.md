# MST A02 — Fourth Eight Original V1: Routing / Session Calendar / Source History (QA 2026-11-10)

**QA ID:** MST-A02-V1-FOURTH-EIGHT-ROUTE-CALENDAR-001
**Verdict:** 40/40 newly added tests PASS; 27/27 workflows SUCCESS on code/workflow HEAD; actual original V1 source byte lock PASS; all external production/owner gates NO-GO.
**Draft PR:** https://github.com/ngluonghoa/MST/pull/8 (DRAFT/UNMERGED).

## 1. Scope and immutable baseline

Original upstream Swing Trading commit cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main commit 4048f91beaaa3410116d97e35896c8b688384e19; original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. Dedicated GitHub-hosted CI separately reads REAL upstream/main/PR remote Git trees to verify all 63 inherited original V1 Python paths and eight already-existing opt-in V2 sidecars unchanged.

Eight NEW original V1 modules with selected actual-runtime synthetic fixtures: adaptive_source_router, c2_source_capability_audit, c2_session_probe_readiness, d1_atr_reconciliation, native_minute_bar_source_plan, session_calendar, ssi_historical_availability, vn_2026_closure_anchors. These are distinct from the prior 24 V1 modules. Four grouped tranches now cover 32 DISTINCT original V1 modules under scoped real-call QA, with 31 remaining. Prior AST/H3 inspection 63/63 is STATIC, not equivalent to executed behavior certification. Owner module dispositions remain 0/63.

## 2. Original V1 runtime results — nine linked safety assertions

1. **Reference routing:** synthetic D1 priority DNSE, synthetic M1 only SSI; without SSI, no native minute candidate even when DNSE/VCBS claim intraday. Wrong RAW/ADJUSTED price basis and bad quality cannot be rescued by low reported latency. RouteDecision remains reference-only, no provider entitlement/trade.
2. **Transient SSI/DNSE/VCBS metadata:** original C2 audit returns SHAPE_RETURNED for fabricated correctly formed D1 response shapes, SCHEMA_REJECTED for malformed SSI OHLC, EMPTY_UNVERIFIED for empty SSI intraday. require_authorized_c2_source raises PermissionError. Actual SSI intraday MCP offers whole-session refetch, not five-minute source revision delta; a changed_since requirement is BLOCKED.
3. **Synthetic probe measurements:** five fabricated response durations yield median 120ms/P95 900ms, but not network-wire measured data, provider SLA, authorized router, or independent freshness. Four successful samples cannot establish percentile. A single weekday missing auction/multiple sessions has open coverage gates; real session metric authorization denied.
4. **D1 expected session completeness:** 20 fabricated D1 snapshots matched 20 caller-supplied D1 sessions return MATCH_UNCERTIFIED, not verified calendar. Missing one expected session returns BLOCKED and missing ID. Future-known manifest denied. No official exchange historical completeness claim.
5. **Native minute catalog != connected MCP:** four M5 product candidates remain nonexecutable. Connected SSI intraday ticks cannot be promoted to M5 OHLC; undocumented SSI FastConnect M15 integer mapping denied. DNSE OpenAPI M5 query sketch is inert, unsent, with no credential, source rights or retention.
6. **Intraday calendar and gaps:** synthetic verified continuous session structurally contains an M15 candle; unverified session, auction, gap and cross-session candle fail to resolve. Fabricated verified flag is not official exchange attestation.
7. **SSI empty intraday with positive D1 volume:** NONEMPTY_MATCHED_UNCERTIFIED remains unlicensed history; positive D1 matched volume plus empty intraday is INTRADAY_EMPTY_DAILY_TRADES_UNCERTIFIED (availability gap), not "no trades". Both empty/D1 zero block rather than proving official closure.
8. **Selected 2026 HOSE/HNX closures:** known published exchange closure 2026-01-02 blocks both synthetic expected sessions; a date not in selected anchors remains NO_KNOWN_COLLISION_UNCERTIFIED, NOT proof of a fully valid trading calendar.
9. **Joined denial authority:** all tested runtime paths preserve false source-licensing, real provider-call, official calendar, actual physical Drive market-cache, independent security root, owner signoff and production/trading rights.

The nine assertions summarize eight distinct inherited domain modules. Existing test fixture helpers ONLY fabricate input metadata; actual source module implementation is executed without mocks replacing it.

## 3. Additive changes on Draft PR8

- scripts/m2_a02_fourth_eight_routing_calendar_runtime_lab.py: actual original V1 router, C2 shape/latency, D1 source and session calendar, native-product blueprint, SSI availability and HOSE/HNX closure integration, synthetic-only aggregate NO-GO report.
- tests/test_m2_a02_fourth_eight_routing_calendar_runtime_lab.py: 40 positive/negative cases, read-only, no credentials, quotes or physical Drive cache.
- .github/workflows/m2-a02-fourth-eight-routing-calendar-runtime.yml: GitHub-hosted PR8-only contents:read, actual upstream/main/PR Git source tree equality BEFORE new tests, all 40 tests + nine linked receipt assertions, 14-day untrusted review artifact.
- docs/MST_A02_FOURTH_EIGHT_ROUTING_CALENDAR_QA_20261110.md: this report, mirrored to Google Drive MST QA.

No inherited src/swing_trading V1 or existing V2 source modules edited; no ACL/ref/ruleset/witness, merge, release or broker action. Option A strictly GitHub+Google Drive, no Mac/MOCHI/local or third Cloud.

## 4. Exact GitHub Actions evidence

Code/workflow HEAD f2fdaf597d3cb50605e7f4b4e06cb9456f23500c:
- Dedicated fourth-tranche real-module CI: https://github.com/ngluonghoa/MST/actions/runs/42772094833 SUCCESS 40/40, nine cross-module checks PASS, REAL source-locked upstream/main/PR Git tree proof PASS.
- Foundation CI: https://github.com/ngluonghoa/MST/actions/runs/42772094802 SUCCESS, Python3.11 2665/2665, Python3.12 2665/2665, original 63 engineering source-boundary + H2/H3/lint/wheel.
- 27/27 workflow runs SUCCESS at exact code/workflow HEAD. After committing this report verify the report-containing HEAD separately; NEVER apply green status to a newer unverified commit.

## 5. Remaining owner/security gates and next safe engineering work

A02 formal human owner module dispositions: 0/63; 32 V1 modules have LIMITED executed synthetic QA, 31 do not yet have this grouped execution coverage. A03 full V2 ABI and behavior acceptance still OPEN. All OA01–OA06 owner decisions, G01–G08 security gates and M3/M4/M5/M8 production/trading BLOCKED. No independent real vendor source licence, fully authenticated calendar, antirollback floor, separate two-writer server CAS, physical Google Drive licensed market cache or authority to publish/trade has been demonstrated. CI PASS certifies only the stated bounded fixture regression and original bytes 1:1.

Next safe A02 scope: execute meaningful inherited behavior cases among remaining 31 originals (SSI/DNSE/VCBS source qualification, replay event recovery and migration), with no privileged apply and human owner signoff only outside public CI.
