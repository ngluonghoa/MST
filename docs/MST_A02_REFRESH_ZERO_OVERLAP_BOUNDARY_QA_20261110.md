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

## Exact implementation code-head GitHub Actions receipt

Draft PR8 code HEAD `1664fd7814172e53f1fe653c1b0ab08697f730ce`: independently checked all **42/42 GitHub Actions workflows SUCCESS** (new A02 exact-close regression workflow is the 42nd). Dedicated A02 boundary run https://github.com/ngluonghoa/MST/actions/runs/42834701234 SUCCESS; GitHub-hosted job logs show `Ran 19 tests` / OK for pre-existing original planner regressions and `Ran 32 tests` / OK for the additional original-source 22-case boundary experiment. Original upstream Swing/main/PR 63 V1 plus eight opt-in V2 source lock ran SUCCESS before tests; report index b1cf29c62fbd1a251d87234ad3e12f7685285177b8bb924fe85926c3bfc576d1 is synthetic QA metadata, NOT an authenticated signer. Both existing V1 exception and valid neighboring source behavior reproduced.
No original V1 bug fix was applied, no signed 1:1 parity owner disposition, no external vendor source/data rights or actual Drive market cache, no production release/trade.

Permanent native Google Drive QA: https://docs.google.com/document/d/1rNfMWr_etQAFFNjDSpgdU8eqw_UMaRqKln68-GqJG3I/edit .

**This QA append creates a NEW report-containing PR HEAD; full 42/42 CI at that final SHA must be rechecked separately before any final-head PASS statement.**
