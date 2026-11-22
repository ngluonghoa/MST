# MST §254 — actual offline private D1 → 16-zone engine → locked UI-1.0 HTML integration

Date 2026-11-23 ICT; isolated from pinned Draft PR23 SHA `a3cca901f37f3dedd4d7a3ec49771b553b54c70d`, unchanged source modules and synthetic test. PR52 brought in private connected-MCP D1 source→original engine, PR53 the locked UI A–I viewmodel/HTML, PR51 the structural evidence-only layer. **This increment connects them through an executable Python function** in `src/swing_trading/private_cache_signal_ui_preview.py`, and adds `private_multitf_readiness.py` for the strict six-TF coverage visibility.

## What runs

`render_private_d1_cache_signal_ui_preview(private_d1_snapshot, as_of_utc, run_id, exchange)` accepts one caller-provided strictly validated private SSI/DNSE/VCBS D1 research snapshot, runs BOTH SHORT and SWING through the already merged original `engine.evaluate_unimplemented_zones` via the §252 bridge, asserts that all 16 zone results are `UNVERIFIED`, constructs locked UI-1.0 A–I metadata viewmodel and renders a non-interactive escaped HTML `INCOMPLETE_REPORT`. Returns a typed preview, HTML SHA-256 and a redacted safe summary, no market price rows. Does not use any token, cloud API or I/O; no Trade or Cache publish path exists in the module.

`private_multitf_readiness.py` separately checks caller-provided candidate canonical candles across M5/M15/M30/H1/H4/D1 with bounded data and identity integrity. H4 is DERIVED-ONLY, W1 is **not** automatically claimed present or authoritative. Six displayed rows do **not** constitute qualified source provenance, close first-known, adjustment, venue calendar, authorized 16-rule parity or release, even when all fictional local consistency checks pass. For the D1-only integration, five other TFs remain `MISSING`, D1 remains `D1_REFERENCE_ONLY`.

## Regression evidence

`tests/test_mst_private_multitf_cache_signal_ui.py` tests fake data through the entire D1→Signal→HTML path and independent six-TF contract. Fails closed against symbol/provider/date drift, stale/provisional source, mutation of mutable viewmodel/summary, misreported higher-TF readiness, and counterfeit `trade_eligible`, `FULL_ANALYSIS` or Step08. The HTML remains the locked existing A–I sections with 16 B/S rows and negative evidence; no simulated precision price/SL/TP escapes into public GitHub logs. All test fixtures synthetic.

## Production and release status

**ENGINEERING INTEGRATION PREVIEW ONLY**: This is not a network/web deployment or certified browser E2E screenshot, cannot consume actual signed provider source from GitHub Actions or retain real market data until owner API keys/read rights and independent external SaaS retention rights are proven, and cannot declare the source finality, six TF context/W1, 64 full original zone predicates, independently signed atomic highwater CAS, Step08 published report, OOS performance or real trading readiness. Owner's last verified actual manual source preflight run [45041453411](https://github.com/ngluonghoa/MST/actions/runs/45041453411) had SSI/DNSE in `HOLD` for missing declarations/secret groups. All 16 zones `UNVERIFIED/NO_TRADE`. The expired 22 Nov deadline is NOT an accepted production release.

H3 static full-package inventory must regenerate with any newly added module; the pinned matrix audit in CI is mandatory. This branch leaves original B/S predicates and no-trade engine unchanged; broad Draft PR23 remains unmerged.
