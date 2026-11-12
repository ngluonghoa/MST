# MST A03 — SSI live historical intraday/D1 shape parity, date-contract contradiction and unavailable raw-price stream

Date: **2026-11-11 Asia/Ho_Chi_Minh**. Current branch: MST Draft PR #8 (additive, no merge). Source of the new findings: genuine READ-ONLY user-connected ChatGPT **MCP SSI** responses, not GitHub runner or signed vendor issuer custody. No raw vendor candles/values/timestamps/API token persisted in the public repository.

## Baseline reused before work

Read latest **MST Master Handoff §119**, relevant prior §§94–103/§118, current 01 Master Spec, 03 Gap Register, and existing `m2_a03_three_source_vcbs_capability_lab.py` and `m2_a03_connected_source_freshness_lab.py`. Those previous guards already differentiated VCBS price-only, DNSE connected D1-only, SSI whole-session candidate OHLCV and authenticated native M5 closure UNKNOWN. We must NOT duplicate or supersede their owner-locked six TFs **M5/M15/M30/H1/H4/D1**.

The new examination targets **an additional connected SSI endpoint** and **observed D1 vs intraday numeric conservation**, with a newly evidenced **contradiction between date-token documentation and unambiguous raw returned date token**.

## Real connected SSI endpoint checks

The connected actions expose TWO different intraday APIs:

- `marketdata_list_intraday_stock_infor`: source OHLCV-shaped rows `open/high/low/close/volume/trading_date`; `latest=true` yields one observation, `range=1d,toDate` yields session rows. It offers no issuer-authenticated native M1/M5 start/end or `ohlc_closed` channel.
- `marketdata_list_stock_infor`: separately described by SSI MCP schema as more complete intraday with `open_raw/high_raw/low_raw/close_raw` and `sys_token` continuous pagination. **Three real read-only attempts** (FPT 10/11, FPT 14/10, DCM 10/11) each failed `DOWNSTREAM_UNAVAILABLE`. No successful raw-price data, page or actual pagination receipt was returned. **Do not call this a verified working transport** or infer cause from a generic downstream service error. No `sysToken` replay was possible without a source-issued token.
- `marketdata_list_stock_daily_data`: source D1 OHLCV for range `1d` and `toDate`. Observed a 2-row inclusive window for these samples (requested `toDate` plus preceding session); **select exact source symbol + literal date** when comparing. Do not erroneously equate the first two sessions to two source intraday date partitions or infer provider-published M5 closure.

Three paired independent true-source read-only observations, with no raw values retained:

| Symbol and explicitly requested historical session | Connected lightweight SSI intraday rows | Source D1 exact-date rows | Derived Open/High/Low/Close/SUM(Volume) matching D1 |
|---|---:|---:|---|
| FPT **2026-10-14** | 226 | 1 | **5/5 exact** |
| FPT **2026-11-10** | 226 | 1 | **5/5 exact** |
| DCM **2026-11-10** | 224 | 1 | **5/5 exact** |
| **Total** | **676** | **3 exact target-date rows** | **15/15 field comparisons exact** |

Aggregation is merely **source-internal numeric reconciliation**: order SSI intraday source `trading_date` by printed HH:MM:SS within exact source date token; take first `open`, maximum `high`, minimum `low`, last `close`, sum all `volume`. It proves those 676 observed OHLCV-shaped observations agree with each selected D1 source row under this arithmetic. It does not prove the intraday producer emits genuine issuer-closed M1 or M5 bars; an issuer-specific minute-label contract, origin-time, correction-first-known, market session completeness and license remain unknown. All samples contained `price_changed=false`, which does not verify unaffected historical corporate-action revisions across symbols and dates.

### Critical newly observed contradiction: SSI date labels

The current SSI connected tool `marketdata_list_intraday_stock_infor` (also `marketdata_list_stock_infor`) is described as returning `trading_date` **MM/dd/yyyy HH:mm:ss**, with example **09/04/2026** interpreted as 4 September. However the real successful FPT **2026-10-14** request returned source token **14/10/2026**. This is incompatible with MM/dd, since month 14 does not exist. The successful SSI D1 matched the literal same token. In contrast 10/11/2026 may be interpreted both DD/MM and MM/dd without independent issuer format proof.

Therefore:
- **DO NOT silently parse all connected SSI dates as MM/dd** from the connector description; observed token with day first >12 disproves that universal assumption.
- **DO NOT silently hard-code DD/MM as an authoritative vendor data policy** based only on one unambiguous observation; source issuer format/version/corrections remain unverified and could differ by endpoint or adapter.
- The new QA keeps literal strings, validates both possible real-calendar shapes, labels conflicting/ambiguous evidence, and refuses to grant an authenticated date policy, M5 closure, Cache or trading authorization. The explicit query date cannot serve as an independent proof of producer date semantics.
- Never fabricate missing minute candles for time gaps or use an unverified `price_changed` adjustment flag to replace original source lineage.

## New source-safe Python gate & GitHub QA

Only additive scripts/test/docs and the existing unprivileged PR-only workflow:
- `scripts/m2_a03_ssi_intraday_d1_observational_lab.py` validates one literal symbol/source-day, two potential locale date encodings, source-internal D1 identity, original five OHLCV fields, bounded unique clock rows, strict numerical conservation, provisional/source rights NO-GO. Reports **counts/flags only**.
- `tests/test_m2_a03_ssi_intraday_d1_observational_lab.py`: **50 entirely fictional cases**, including all five numeric drift fields, malformed symbols/tokens/dates, duplicate/missing dates, imputed gaps, false native-minute trust, wrong/negative/nonfinite prices, open/high/low envelopes, and no publisher first-known or trading/cache grants.
- `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml`: add 50 fake tests plus a synthetic-only NO-GO artifact. No GitHub Actions SSI account calls, new secrets, production Cache activation, local compute, Mac or MOCHI.

**Do not mark these 50 tests PASS until the complete exact new HEAD GitHub Actions conclusion is verified.** Prior green checkpoint at `6e216fd06ce760b2742ce9d1fef40f9665ec1a66` was 47/47 workflows SUCCESS and 831 focused fake test methods. Protected MST main remains `4048f91beaaa3410116d97e35896c8b688384e19` before this checkpoint. The 63 inherited Swing V1 and eight existing V2 module bytes must remain unchanged. Draft PR #8 must remain unmerged.

## Important disposition / next meaningful experiment

The real SSI lightweight endpoint DOES support retrieving OHLCV-shaped rows for historical date **2026-10-14** and 2026-11-10, and source D1 arithmetic matched on three concrete dates. This is useful further source qualification evidence but **does not fulfill native closed M5 nor signed first-known**. A real source-issued minute-close declaration plus valid historical exchange calendar would permit separately testing session aggregation policy. The separately described richer SSI `sysToken`/raw endpoint is currently **unavailable** on three independent tries and must not be assumed usable for pagination/corporate-action custody.

The connected DNSE price history is D1-only for this ChatGPT account action; DNSE official separate HTTP M5/WS native endpoints were studied previously but actual vendor authorized account/runner not authenticated. VCBS time/price intraday remains price-reference-only even if it aligns with SSI on timestamps. Vendor licenses, trusted issuer corrective first-known, external signer/CAS/high-water, GCP WIF and GitHub Actions→Google Drive production persistence, live signal and trading remain **OPEN/NO-GO**.

Existing private Drive FPT/DCM/HPG × SSI/DNSE/VCBS **180 real D1 source rows remain unchanged**. Public GitHub files contain no raw SSI/VCBS/DNSE price arrays or credentials.
