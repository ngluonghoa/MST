# MST A02 — Original V1 zero-overlap exact-closed-bar request gap

QA-ID: MST-A02-ORIGINAL-V1-REFRESH-ZERO-OVERLAP-EDGE-20261110
Date: 2026-11-10 Asia/Ho_Chi_Minh
Status: Synthetic original-behavior gap characterization, exact-head GitHub CI pending.

## Concrete inherited source gap
Real original Swing Trading 1.8 module src/swing_trading/cache_fetch_planner.py (unchanged) accepts overlap_bars=0. Given a valid WINDOWED cursor at the newest closed synthetic five-minute candle, now equal to that candle's end and a due refresh or provisional preview, internal requested start = cursor.closed+5min = now=end. RefreshPlan.__post_init__ raises ValueError("Empty request"). This is a genuine original pure-function edge, not a known live SSI/DNSE/VCBS exception, real request, provider correction or financial loss.

## Characterization
New isolated original-call lab constructs exactly 22 explicit UTC synthetic edge cases; four reproduce the valid-input exception and eighteen neighboring choices correctly produce nonempty window/full session/reuse/blocked. Tests include cap unknown, full-session fallback, correction reconciliation, no cursor, sessions, source clock backstep, overlap=1/24, close+1-minute, no new bar, finality claims and open preview. Original default overlap=1 avoids the gap in standard scenario; source correction and first-known semantics still require independent official data. 32 new direct unittest methods check the original code without changes and owner/production NO-GO flags. Existing original planner regression tests also run.

GitHub-hosted same-repository Draft PR #8 ONLY; remote source-lock originals 63 V1 + eight V2 and read-only workflow, synthetic-only 14-day metadata artifact. No V1 patch, new V2 policy, real data/Drive storage, Mac/MOCHI/local, third cloud, GitHub permissions/ref/main or broker/trade.

## Owner compatibility decision OPEN
Owner must separately decide to preserve the original valid-input exception for strict inherited V1 parity versus approve opt-in V2 failure handling for empty refresh scope. Neither may be silently treated as accepted 1:1. Formal A02 0/63, V2 A03 0/8, owner choices 0/14; external source rights/calendar, real Drive market cache, independent protected floor/CAS, releases and all trading NO-GO.

## CI / evidence
PENDING exact report-containing commit CI and Drive readback. A green *negative reproduction* indicates a known source behavior gap, not defect remediation or signed owner approval.
