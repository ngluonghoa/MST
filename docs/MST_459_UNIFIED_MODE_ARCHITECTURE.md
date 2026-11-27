# DEC-MST-UNIFIED-001 — shared core, three execution modes
Owner decision 2026-11-27: adapt the MFX30 proposal in MST only. Do not modify MFX.
Baseline §458 exact main 893aa71eb43d5ffa08eb67e7eaa77a642a6828b3; 2589 tests on each Python.
MST already has one baseline dispatcher and causal feature ingredients. Keep frozen
Swing Trading 1.8 source, zone/phase/variant semantics, SHORT/SWING (not short sale),
UI 1.0, eight-step audit, cache consent and cadence, source/settlement/release gates.
No wholesale rewrite or imported Forex rules. No background automation.
## Incremental implementation
- §459: explicit versioned private candidate profile and common Research/Validation
  dispatcher, deterministic typed configuration identity. Production denied before
  evaluation. Code SHA is a claim, not attestation. No public profile or raw data.
- §460: extract shared D1 feature boundary from existing §383 engine, preserve exact
  function and output compatibility; use same feature path from both modes.
- §461 onward: bind chronological validation inputs and pinned candidate profile,
  preserve independent source, causal/OOS, settlement, costs and release evidence.
  Continue existing §459-planned S3 TP event (renumbered after architecture work),
  RF, holdings and strict integration, then remaining zones. No lost scope.
Research can evaluate synthetic or separately eligible data; Validation is not
synthetic QA certification. Production stays blocked until independent approval
and qualified version, source, parameters and operational evidence; no orders.
No provider, cache, schedule or UI change in §459. Roll back via reviewed atomic
revert only. MST-CEP-001 and exact independent main CI remain mandatory.
