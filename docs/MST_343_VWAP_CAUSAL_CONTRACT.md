# §343 — Causal exact-turnover VWAP candidate

Trace: frozen Master Spec §24/P14 and Smart Cache L2. Prior generic
matched_value is optional and not a turnover semantics attestation.
This opt-in M1 continuous-only implementation requires exact declared
matched VND turnover, source event/revision and verification time, RAW
price basis, qualified resolved bar, explicit verified calendar and a
complete minute prefix across continuous segments. No lunch or auction
bars, gap filling, proxy value or mixed lineage. Session VWAP resets at
the first continuous segment; same-day anchored VWAP requires an explicit
aligned event/revision known by the calculation cutoff. Anchor selection
and multi-day/auction policy remain unapproved. Numeric results are
non-actionable, not source certification; no runtime integration.
Fictional regression only, no provider data. Rollback by reverting PR.
