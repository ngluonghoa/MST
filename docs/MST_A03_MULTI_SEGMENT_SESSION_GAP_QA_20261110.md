# MST A03 — Multi-segment M5 trading-day gap/market-phase test candidate

Date: 2026-11-10 Asia/Ho_Chi_Minh
QA ID: MST-A03-MULTI-SEGMENT-GAP-PHASE-20261110
Status: Draft PR8 ONLY, synthetic negative QA, not a real trading calendar. GitHub exact-head CI pending.

## Evidence motivating this distinct next test
The previous A03 candidate UntrustedSessionSlot correctly required four contiguous M5 candles in ONE synthetic interval, but a single contiguous grid is insufficient to express a full trading day that includes a break. Verified public educational context: HOSE published English "Trading hours" PDF https://staticfile.hsx.vn/Uploads/UploadDocuments/2372209/2.Trading%20hours.pdf specifies 09:00-09:15 opening auction, 09:15-11:30 continuous morning, 11:30-13:00 lunch, 13:00-14:30 afternoon continuous, and 14:30-14:45 closing call auction. HNX official FAQ https://cbinfo.hnx.vn/vi-vn/hoi-dap.html describes a similar lunch break and distinct HNX/UPCoM matching rules. These are *public background sources*, NOT provider-licensed M5 OHLCV, signed notice validity, instrument/holiday/suspension proof, clock custody or eligibility for a particular issuer/feed. No exchange snapshot or Google Drive licensed bar was fetched.

## Implemented scope: scripts/tests ONLY
scripts/m2_a03_multi_segment_session_gap_lab.py composes existing test-only A03 UntrustedSessionSlot and screen() with original SessionType enum, V1↔V2 identity mapping, and retained r1/r2 first-known candidate logic. It models two small M5 CONTINUOUS segments on a fabricated HOSE-like day: 11:20–11:30 and 13:00–13:10 Asia/Ho_Chi_Minh, separated by 90 minutes. Each segment has strictly contiguous permitted M5 starts; the daily candidate allows a disjoint, sorted, nonoverlapping union without silently filling lunch. Each candle must match an EXPLICIT claimed segment, matching exchange and full V2/V1 partition binding.

Conservative negative policy: noon break candle, boundary-crossing candle, wrong segment, wrong venue, duplicate labels, overlap/reverse, wrong local date, caller self-verified calendar and unknown segment are rejected. Synthetic AUCTION/AFTER_HOURS segments cannot automatically be interpreted as CONTINUOUS M5 bars: source-specific auction/aggregation semantics require independent owner approval. A historic morning-bar correction first published the following day remains in morning event-time segment but is only selected as revision r2 at exact first-known; just before, r1 is used. All metadata is invented; SHA256 indexes are local consistency, not authority.

31 additional unittest methods plus 16 direct integration assertions run in GitHub-hosted Python 3.12, original 63 inherited V1 and eight opt-in V2 unchanged with upstream/main/PR byte-lock. No calendar provider integration, official holiday/closure inventory, market source entitlement, real Google Drive cache, Mac/MOCHI/local, third cloud or broker.

## Owner decisions / limitations
The 2x10-minute CONTINUOUS example does NOT assert an official full-session minute-bar inventory, when auction trades form 5-minute candles, whether a particular provider timestamps bar START or END, or any completed first-known ledger. Production calendar issuer, approved exchange/venue phase mapping, instrument suspensions, historical calendar version/notice custody, licensed data-retention and physical Drive cache permissions must be independently verified. A02 owner 0/63, A03 V2 0/8 and A03 owner choices 0/14; G01–G08/OA01–OA06 remain OPEN. No V1 fix, new production V2 module, main/ruleset/ACL change, merge, release or trading.

## QA evidence
PENDING exact report-containing GitHub Actions readback.
