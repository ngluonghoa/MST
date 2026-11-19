# MST §234 — DNSE official OpenAPI signed OHLC read-only cloud probe (P0-B)

**Status:** isolated provider adapter and manual workflow, **NOT a real provider PASS**. Only fictional unit tests and GitHub CI can execute without owner-scoped DNSE credentials. NO_TRADE / UNVERIFIED.

## Why this exists

MST's §231 SSI FastConnect cloud probe is provider-specific. DNSE has a different official authenticated REST contract. Connected ChatGPT research access is NOT a GH Actions API credential or a right to store/redistribute provider data. This change introduces exactly one protected-main, manually dispatched market-data GET capability; it does not authorize unattended acquisition or any Drive writing.

Official provider references checked 2026-11-20:

- [DNSE authentication — HMAC-SHA256 signature, Date, unique nonce](https://developers.dnse.com.vn/docs/guide/intro/authentication/)
- [DNSE historical OHLC — GET /price/ohlc](https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/)
- [DNSE dated API versions](https://developers.dnse.com.vn/docs/guide/versioning/api/)

The request signs request-target for GET /price/ohlc, Date, and a fresh UUID4 hex nonce using the documented HMAC-SHA256/Base64/percent-encoding method. It sends a pinned version header (2026-07-23), restricted to https://openapi.dnse.com.vn/price/ohlc only, type=STOCK; no order/account endpoints.

## Owner preconditions, only when independently satisfied

Set GitHub repository Actions Secrets MST_DNSE_API_KEY and MST_DNSE_API_SECRET after DNSE has granted valid scoped OpenAPI access; never paste credentials in issues, pull requests, ChatGPT output or logs.

Set GitHub repository Actions Variables MST_DNSE_READONLY_OWNER_ACCEPTED and MST_DNSE_SOURCE_RIGHTS_CONFIRMED to literal true ONLY after confirming source-access terms. Setting either variable is not by itself independent rights attestation. Leave unset otherwise; workflow fails closed.

Run [MST DNSE signed native OHLC read-only - MANUAL OWNER GATED](https://github.com/ngluonghoa/MST/actions/workflows/mst-dnse-native-readonly-manual.yml), on branch main, manually select confirm=READ_DNSE_ONLY, one symbol FPT/HPG/DCM, one native timeframe D1/H1/M30/M15/M5, and YYYY-MM-DD dates within conservative caps (D1 95 calendar days, H1 35, M30 20, M15 10, M5 5). Inputs are inclusive calendar dates in Asia/Ho_Chi_Minh, converted to half-open Unix seconds. Empty, duplicate, unsorted, malformed, oversized or OHLC-inconsistent source responses fail closed. One request only; a nextTime hint is reported but NOT followed or treated as full coverage.

## Output/authorization boundaries

A successful run prints only a fixed-schema aggregate receipt: source ID, direct TF, observed row count, whether DNSE exposed a continuation hint, and local OHLCV checks. It prints NO API keys, signatures, prices, timestamp series, provider error response, broker data or Traceback. Failing requests produce fixed codes without server error content. Logs never represent source rights, candle close, historical first-known, adjusted/raw price basis, complete pagination, provider cross-parity, or official venue calendar as verified.

No Google Drive writes, Cache CHUNKS/MANIFESTS promotion, highwater CAS, cron, strategy detectors, signal approval or trading. H4 is NOT a DNSE native OHLC TF in MST's five-resolution contract; W1 derivation remains separately gated. No live call was made while introducing this PR. If an official DNSE API response differs from documented schema or version, treat this as a gate failure requiring review, NOT a reason to relax the validator or log raw rows.

## Next P0-B/P0-C

After owner-authorized real-source read-only PASS, record only the non-sensitive count/shape receipt in QA, then separately qualify native clock labels, first-known, session close, adjustment basis, volume scope, partial/corporate-action revisions and usage rights. Only after those and independent source-owned signing/CAS may a separate guarded PR implement immutable app-owned market CHUNKS/MANIFESTS. Do not conflate this read-only probe with a production-ready Cache or 16-zone verifier.
