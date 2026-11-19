# MST §233 — SSI FastConnect V3 cloud-native read-only source probe

**Scope:** A narrow GitHub Actions manual, protected-main-only probe for SSI
native OHLCV. It is NOT the first market Cache writer and it does not attest
price basis, official session closure, source revision or provider retention
rights. The existing app-owned Google Drive synthetic canary already verified
Google Drive write/readback; that test did **not** verify SSI API access.

## Prerequisites (owner must verify on GitHub)

Repository Actions secrets (values must never be committed or pasted in logs):

- \`MST_SSI_API_KEY\` and \`MST_SSI_API_SECRET\`: SSI FastConnect V3 **market
  data** API credentials authorized for this use. Do not use brokerage trading
  session, OTP or a ChatGPT MCP token in GitHub Actions.
- Repository Actions variables \`MST_SSI_READONLY_OWNER_ACCEPTED=true\` and
  \`MST_SSI_SOURCE_RIGHTS_CONFIRMED=true\` only after genuinely verifying
  SSI account/market-data API usage terms. Setting a variable is an execution
  gate, **not independent vendor attestation or license evidence**.

The scripts never create or update secrets, variables or API grants. Do not
assume the above values currently exist. If they are missing, the probe must
fail closed with only a fixed diagnostic code.

## After reviewed squash-only merge into protected main

1. Open GitHub Actions:
   \`https://github.com/ngluonghoa/MST/actions/workflows/mst-ssi-native-readonly-manual.yml\`.
2. Choose branch \`main\`, \`confirm=READ_SSI_ONLY\`, a stock symbol
   \`FPT/HPG/DCM\`, a supported timeframe \`M5/M15/M30/H1/D1\`, and a bounded
   ISO date range \`YYYY-MM-DD\`. Select only a time range for which the
   credentials and legal use of source data have been verified. H4/W1 are
   deliberately not source-native here.
3. Run once. A successful count-only receipt has status
   \`MST_233_SSI_CLOUD_NATIVE_READONLY_PROBE_PASS\`, rows/pages and explicit
   false authority/trade/cache flags. Logs do **not** include price series,
   token, credentials, raw response, file IDs or request headers.
4. A failure or an empty response is **not** a price record or market Cache
   signal. Keep \`NO_TRADE/UNVERIFIED\`.

## Bounded behavior

- Manual dispatch only; exact GitHub repository ID, owner ID, protected main
  branch, workflow file identity, first run attempt and explicit confirmation.
- SSI FastConnect V3 token endpoint for scoped OHLC **read** only, no OTP,
  order endpoint, broker trades, service-account fallback, Drive upload or
  provider credential persistence.
- Five SSI-native resolutions mapped by §231. Strict bounded date window,
  up to five provider pages and 500 rows, duplicate/invalid OHLC rejection.
  Actual venue close, revision sequence, source first-known, price adjustment
  and complete historical window coverage remain unverified.
- The source adapter keeps vendor-native rows inside the ephemeral process
  and returns a safe aggregate receipt only. Future licensed private staged
  Cache writer must be proposed/tested separately.

**Status at authoring:** Source adapter §232 merged; workflow §233 is still a
code proposal until its CI passes and a squash-only merge occurs. No live
GitHub SSI probe has been performed simply by creating this file.
