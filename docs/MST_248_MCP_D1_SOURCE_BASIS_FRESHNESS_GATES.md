# MST §248 — Real-source-driven D1 basis, unit and freshness gates (research only)

Date: 2026-11-20 ICT. Separate **read-only connected MCP** research sources from the independent SSI FastConnect V3 GitHub Actions credential and ingestion path. The former was exercised directly by an authorized ChatGPT research connector; the latter has still not been dispatched live.

## What surfaced from actual connected-provider observations

A bounded live read-only FPT D1 comparison on 2026-11-20 used the SSI research connector, DNSE one-year DAY history and VCBS D1 history. SSI and VCBS expose prices in VND whereas the DNSE DAY series exposes numeric prices in **thousands of VND**. Values must never be compared without explicit scale, and the SSI compact MCP source is described as **adjusted** while VCBS exposes separate raw and adjusted fields.

VCBS's newest returned 2026-11-20 daily row was tagged `source=board_supplement` rather than independently confirmed post-session historical D1. Matching same-day close/volume figures from three providers is therefore **not proof of provider first-known time or venue session finality**. Its row should be kept observational/provisional until a subsequent historical provider read and immutable source-clock evidence establish closure. This is a real observed category problem, not a randomly invented scenario.

## PR scope

- `scripts/mst_d1_research_cross_feed_basis248.py`: pure offline, zero-I/O, **non-trading** comparison of *caller-supplied, explicit* SSI/DNSE/VCBS MCP D1 observations for a narrow FPT/DCM/HPG research pilot. Must provide exact provider source, session date, price unit, adjustment basis, volume scope and record provenance. No implicit 'normalize by plausible prices', no silent rounding and no synthetic promotion into official FastConnect V3 identity.
- Price units: SSI MCP compact D1 and VCBS MCP D1 are VND; DNSE MCP DAY series is `THOUSAND_VND` and must be explicitly labelled as such before being multiplied by 1000. If the upstream feed changes its unit contract, this check fails closed until updated.
- Price adjustment basis `raw`, `adjusted` or `unknown` must align explicitly; mixed/unknown means price comparison is NOT CERTIFIED even if numbers happen to match. Volume comparison requires explicit identical `matched` or `all_trades` scope; unknown scope cannot be compared.
- Record origin `historical`, `board_supplement`, `provisional` or `unknown`: any non-historical label triggers a block; even historical-labelled data is **not** an independently signed venue finality claim.
- Redacted output carries only source count, scope/date, boolean match/unknown and fixed reason codes; no raw OHLCV prices or vendor HTTP response. **All downstream production/rights/first-known/CAS/trading flags remain false** for every possible input.
- `tests/test_mst_d1_research_cross_feed_basis248.py` uses **fictional numbers** only. Includes tests for a normal K-VND conversion, absence of implicit price basis, supplemental rows, missing/duplicate provider, wrong date, unequal price/volume, nonfinite/fractional values, and redaction.

## Important rights boundary

SSI's official FastConnect API terms (https://developers.ssi.com.vn/en/term-condition) restrict disclosure of API information to third parties and bind use to the client's securities trading purposes. A user permitting private Cache storage does **not by itself** establish the vendor's permission to put FastConnect market data in an external Google Drive backend. Owner must check their actual subscribed terms/storage rights or obtain explicit permission before enabling `MST_SOURCE_RETENTION_RIGHTS_CONFIRMED`. **This PR does not collect or store market OHLCV, nor change existing GitHub Actions rights gates.**

MCP research connectors and FastConnect V3 issued market-data API keys are separate authentication paths: successful SSI MCP research is not proof that GitHub Actions has an API key or cloud source storage entitlement. This code must not be mistaken for original Swing Trading 1.8 provider normalization, complete M5–D1+H4/W1 coverage, backtest parity, source clock, signed highwater/CAS or trade-ready Cache.

Reference SSI official documentation:
- https://developers.ssi.com.vn/docs/getting-started/overview
- https://developers.ssi.com.vn/en/term-condition

## Current NO-GO

GitHub Actions SSI/DNSE live source fetch unconfirmed, app-owned Drive CHUNKS/MANIFESTS/AUDIT last audited empty; highwater owner-private signer/CAS unproven. All B1–B8/S1–S8 regions remain `UNVERIFIED/NO_TRADE`. The 2026-11-22 target is at most a conditional engineering RC.

Separate next steps: owner-side Cloud API credential and provider storage-rights verification; live read-only GitHub Actions source probe; source clock/basis normalization; post-session historical requery; and independently witnessed atomic CAS in a protected highwater backend.
