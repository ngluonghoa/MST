# MST §253 — locked UI-1.0 A–I INCOMPLETE diagnostic (source→engine→report)

2026-11-23 ICT. Atomic extraction from pinned Draft PR #23 `a3cca901f37f3dedd4d7a3ec49771b553b54c70d` of original locked UI diagnostic `src/swing_trading/locked_ui10_binding.py`, static HTML `locked_ui10_renderer.py`, their separate tests and exact `tests/golden/ui10_incomplete_semantics.json`. This follows §251 source-traced but non-signal structural phase evidence and §252 provider-partitioned *private MCP D1 reference*→original engine diagnostics. Baseline Swing Trading 1.8 design frozen to UI-1.0 and original master spec.

## Implemented engineering behavior

The A–I UI sections retain fixed order, 16 B1–B8/S1–S8 zone labels, 8 pipeline stages, 8 per-signal audit topics, independent SHORT and SWING branches, explicit no-position context, missing source/TF/finality warnings, and the decision `NO_TRADE` for each incomplete synthetic candidate. The viewmodel requires the existing engine to report all 16 zones `UNVERIFIED` and prevents `NO_SIGNAL`, fabricated entry, SL/TP, score, risk/reward, completed Step08 or a false paper/live market report. Source observations in the UI are metadata only: no original provider bars, prices, tokens, secrets, Google Drive private IDs or account identifiers.

The HTML renderer is server-independent static HTML, escapes untrusted text, includes a restrictive CSP and no executable script or external asset, provides mobile/print styles and basic screenreader table structure, and rechecks the reference fingerprint after potential caller mutation. All underlying reference data are synthetic in regression tests. Tests assert 9 section order, 16 zone rows, 8 pipeline/audit rows, exact golden legend and method status, provider separation, no-price or credential leak, mutation resistance and safe no-signal wording.

## Explicit limitations

This is a **working pure-Python HTML rendering function** but no hosted web application, live browser deploy, end-to-end Step08 atomic signed publish, golden browser screenshot, actual licensed provider ingestion, 6 TF+W1 certification, actual original 16 detector formulas, OOS backtest or production trading. The correct rendered result for currently unqualified data is `INCOMPLETE_REPORT/NO_TRADE`. §253 does not silently change UI design or claim full UI acceptance. Any browser screenshot/hosting and full source-to-market report needs separate evidence and approval.

Owner-side data credential/rights blockers persist after authenticated no-HTTP manual preflight 45041453411: SSI and DNSE Cloud native read-only paths HOLD (owner declarations and at least one secret group missing). No SSI/DNSE native workflow_dispatch since then at this extraction. App-owned production market CHUNKS/MANIFESTS are empty and independent highwater signer/atomic CAS remains unproven. All B1–B8/S1–S8 stay UNVERIFIED/NO_TRADE.

This PR changes no jobs, provider rights variables, OAuth controls or broker controls. The H3 whole-source static inventory requires regeneration when adding these two modules; any change to matrix is mechanical and verified against Cloud CI's generated report. Merge only on 3/3 Foundation CI, atomic scope, squash-only, protected-main postmerge checks.
