# §438 full H1-base B8 strict integration (fictional only)

Completes the explicit base-timeframe matrix begun in §436–437. Reuse a single resolved strict BASE or selected TOD input and replace its base history with the explicit H1 fixture; when RF is also H1, maintain the exact 21-row RF window and rebuild raw volume witness bindings for the changed history. D1 ATR, independent aligned adjusted D1 RS, raw price grids, same-size hypothetical execution, settlement and portfolio remain bound to their existing explicit scopes. H1 floor 8, target 22, total hypothetical risk 140 instead of D1 floor 7, target 23, total risk 150. Synthetic only.

Six regression methods cover all 8 H1-base × H1/D1 RF × SHORT/SWING × BASE/TOD combinations, missing H1 without D1 fallback, late right-pivot bar, H1-floor-specific net RR rejection, illegal frame, and deterministic redacted nonactionable replay. Combined §436–438 covers all 16 positive combinations.

## Acceptance boundary against locked Master Spec §24.4

- R0: explicit D1/H1 causal base and resistance, D1 ATR, aligned independent adjusted D1 benchmark RS, raw M15 price grid.
- RC: explicit same-resistance near/approach with matched R0.
- RE: closed same-resistance M15 cross; explicit selected TOD raw M1 prefix and matched prior20 slots, no implicit alternative.
- RF: later closed H1/D1 cross, raw matched prior20 RVOL with explicit threshold, advanced aligned RS, extension, measured-base net RR and max-entry, raw price grid, hypothetical settlement/liquidity/portfolio checks.
- Missing, unknown and nonmatch remain fail-closed; exact phase selection and no action/verification authority preserved.

This is candidate arithmetic and fictional integration, NOT the locked rule's final approval. Outstanding: approved exact feature/parameter and strategy risk policies; licensed historical RAW/ADJUSTED/benchmark and matched-share/unit/venue calendar/aggregation attestations; official band/tick/settlement semantics; actual order capacity, execution and slippage; immutable event IDs/expiry and source-backed OOS calibration plus independent QA. No inferred thresholds, live trading, source promotion, cache, or automation. Rollback: revert squash commit.
