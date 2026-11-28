# H3 — Provisional whole-module review matrix

This is static prioritization, NOT a human code quality verdict.
KEEP means no threshold breached, NOT error-free. IMPROVE means inspect
before any behavioral refactor. REPLACE and REMOVE are never automatic;
these require separate consumer, migration and rollback evidence.

| Module | Group | LOC | Max branch | Longest function | Consumers | Proposed | Flags |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| __init__ | domain_and_reference | 3 | 0 | 0 | 0 | KEEP | none |
| adaptive_source_router | source_adapter_and_quality | 289 | 27 | 75 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| b1_decline499 | domain_and_reference | 111 | 11 | 19 | 1 | KEEP | none |
| b2s2_swing_evidence215 | domain_and_reference | 379 | 33 | 98 | 1 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| b5_calibration_draft | domain_and_reference | 169 | 16 | 33 | 0 | KEEP | none |
| b5_feature_pack | domain_and_reference | 149 | 28 | 64 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| b5_formula_geometry | domain_and_reference | 624 | 24 | 76 | 2 | IMPROVE | FILE_500_PLUS, HIGH_BRANCH_SCORE |
| b5_phase_contract | domain_and_reference | 261 | 46 | 117 | 3 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| b5_temporal_split_audit | domain_and_reference | 235 | 35 | 91 | 0 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| b6_baseline_preview387 | domain_and_reference | 473 | 18 | 49 | 2 | KEEP | none |
| b6_rf_volume405 | domain_and_reference | 82 | 10 | 19 | 3 | KEEP | none |
| b7_support_preview409 | domain_and_reference | 469 | 16 | 38 | 1 | KEEP | none |
| b8_base_preview415 | domain_and_reference | 497 | 12 | 44 | 1 | KEEP | none |
| b8_execution_preview430 | domain_and_reference | 122 | 9 | 20 | 1 | KEEP | none |
| b8_liquidity428 | domain_and_reference | 95 | 10 | 15 | 2 | KEEP | none |
| b8_mandatory435 | domain_and_reference | 59 | 9 | 14 | 1 | KEEP | none |
| b8_portfolio429 | domain_and_reference | 97 | 11 | 11 | 2 | KEEP | none |
| b8_price_band426 | domain_and_reference | 82 | 8 | 18 | 2 | KEEP | none |
| b8_risk_geometry424 | domain_and_reference | 105 | 8 | 17 | 2 | KEEP | none |
| b8_rs_stock434 | domain_and_reference | 64 | 7 | 11 | 1 | KEEP | none |
| b8_settlement427 | domain_and_reference | 75 | 9 | 13 | 2 | KEEP | none |
| b8_tod_preview432 | domain_and_reference | 67 | 18 | 25 | 1 | KEEP | none |
| backtest | domain_and_reference | 71 | 4 | 23 | 0 | KEEP | none |
| baseline_ui10_runtime379 | domain_and_reference | 159 | 7 | 20 | 1 | KEEP | none |
| c2_fair_source_benchmark | source_adapter_and_quality | 292 | 28 | 41 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| c2_session_probe_readiness | source_adapter_and_quality | 285 | 40 | 56 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| c2_source_capability_audit | source_adapter_and_quality | 371 | 47 | 76 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| cache_fetch_planner | cache_and_persistence | 150 | 30 | 77 | 3 | IMPROVE | HIGH_BRANCH_SCORE |
| cache_snapshot_bundle | cache_and_persistence | 357 | 24 | 61 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| cache_swap_preview | domain_and_reference | 133 | 16 | 47 | 0 | KEEP | none |
| causal | domain_and_reference | 22 | 4 | 7 | 1 | KEEP | none |
| causal_compression_approach403 | domain_and_reference | 110 | 10 | 19 | 2 | KEEP | none |
| causal_compression_breakout404 | domain_and_reference | 136 | 8 | 29 | 1 | KEEP | none |
| causal_compression_candidate395 | domain_and_reference | 86 | 7 | 27 | 3 | KEEP | none |
| causal_compression_pivot402 | domain_and_reference | 76 | 11 | 30 | 2 | KEEP | none |
| causal_contraction_candidate386 | domain_and_reference | 140 | 10 | 25 | 1 | KEEP | none |
| causal_cross_tf_candidate392 | domain_and_reference | 97 | 10 | 33 | 2 | KEEP | none |
| causal_exhaustion492 | domain_and_reference | 113 | 15 | 24 | 2 | KEEP | none |
| causal_indicators | domain_and_reference | 404 | 18 | 58 | 29 | KEEP | HIGH_FAN_IN |
| causal_range_candidate384 | domain_and_reference | 129 | 8 | 37 | 1 | KEEP | none |
| causal_range_percentile397 | domain_and_reference | 75 | 7 | 27 | 3 | KEEP | none |
| causal_structure_geometry | domain_and_reference | 334 | 32 | 89 | 44 | IMPROVE | HIGH_BRANCH_SCORE, HIGH_FAN_IN |
| causal_trend_candidate382 | domain_and_reference | 88 | 11 | 19 | 4 | KEEP | none |
| causal_volume_dryup399 | domain_and_reference | 109 | 9 | 27 | 1 | KEEP | none |
| contracts | domain_and_reference | 70 | 5 | 7 | 39 | KEEP | HIGH_FAN_IN |
| d1_atr_reconciliation | domain_and_reference | 288 | 27 | 113 | 2 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| d1_mcp_transport_bridge | source_adapter_and_quality | 292 | 11 | 44 | 2 | KEEP | none |
| d1_three_source_observation_audit | domain_and_reference | 336 | 45 | 117 | 0 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| dnse_d1_reference_fallback | source_adapter_and_quality | 368 | 30 | 69 | 5 | IMPROVE | HIGH_BRANCH_SCORE |
| durable_evidence | evidence_and_rights | 184 | 12 | 35 | 3 | IMPROVE | DUPLICATE_AST |
| engine | domain_and_reference | 537 | 56 | 111 | 3 | IMPROVE | FILE_500_PLUS, FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| engineering_contracts | engineering_governance | 175 | 10 | 27 | 5 | KEEP | none |
| engineering_release | engineering_governance | 102 | 19 | 20 | 0 | KEEP | none |
| evidence_checkpoint | evidence_and_rights | 184 | 12 | 36 | 1 | KEEP | none |
| evidence_recovery | evidence_and_rights | 81 | 4 | 23 | 1 | KEEP | none |
| feature_engine460 | domain_and_reference | 50 | 9 | 18 | 13 | KEEP | HIGH_FAN_IN |
| fixture_scan | cache_and_persistence | 88 | 8 | 44 | 0 | KEEP | none |
| hose_session_geometry210 | domain_and_reference | 494 | 28 | 91 | 0 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| incremental_cache | cache_and_persistence | 441 | 23 | 83 | 9 | IMPROVE | HIGH_BRANCH_SCORE |
| legacy_migration | domain_and_reference | 205 | 24 | 98 | 1 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| locked_ui10_binding | domain_and_reference | 413 | 87 | 131 | 3 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| locked_ui10_renderer | domain_and_reference | 352 | 10 | 129 | 1 | IMPROVE | FUNCTION_90_PLUS |
| market_data | domain_and_reference | 162 | 23 | 29 | 76 | IMPROVE | HIGH_BRANCH_SCORE, HIGH_FAN_IN |
| migration_archive | domain_and_reference | 126 | 24 | 69 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| native_minute_bar_source_plan | source_adapter_and_quality | 252 | 15 | 61 | 3 | KEEP | none |
| partition_chunk_cache | cache_and_persistence | 483 | 26 | 49 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| phase_input_routing369 | domain_and_reference | 241 | 16 | 36 | 22 | KEEP | HIGH_FAN_IN |
| private_cache_signal_ui_preview | domain_and_reference | 164 | 34 | 60 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| private_cache_source_bridge | domain_and_reference | 357 | 27 | 64 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| private_multitf_readiness | domain_and_reference | 308 | 35 | 91 | 19 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE, HIGH_FAN_IN |
| provider_custody_host_plan | evidence_and_rights | 393 | 25 | 47 | 0 | IMPROVE | HIGH_BRANCH_SCORE |
| provider_head_custody | evidence_and_rights | 432 | 40 | 84 | 1 | IMPROVE | HIGH_BRANCH_SCORE |
| provider_review_packet | evidence_and_rights | 264 | 37 | 104 | 0 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| provider_rights_review | evidence_and_rights | 197 | 17 | 58 | 2 | KEEP | none |
| provider_signed_event_chain | evidence_and_rights | 306 | 26 | 81 | 1 | IMPROVE | HIGH_BRANCH_SCORE |
| quality_audit | domain_and_reference | 181 | 14 | 27 | 1 | KEEP | none |
| range_baseline_preview385 | domain_and_reference | 158 | 10 | 17 | 3 | KEEP | none |
| reference_checkpoint_mac | evidence_and_rights | 168 | 11 | 22 | 0 | KEEP | none |
| reference_checkpoint_signature | evidence_and_rights | 176 | 15 | 35 | 1 | KEEP | none |
| reference_host_dryrun | evidence_and_rights | 154 | 8 | 29 | 0 | KEEP | none |
| reference_journal | evidence_and_rights | 353 | 31 | 56 | 5 | IMPROVE | HIGH_BRANCH_SCORE, DUPLICATE_AST |
| reference_journal_recovery | evidence_and_rights | 298 | 12 | 66 | 3 | KEEP | none |
| reference_offline_verified_archive | evidence_and_rights | 159 | 15 | 96 | 0 | IMPROVE | FUNCTION_90_PLUS |
| reference_pinned_fd | evidence_and_rights | 163 | 23 | 78 | 1 | IMPROVE | HIGH_BRANCH_SCORE, SILENT_EXCEPT |
| reference_storage_preflight | evidence_and_rights | 143 | 22 | 82 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| relative_strength421 | domain_and_reference | 155 | 11 | 14 | 2 | KEEP | none |
| replay | domain_and_reference | 26 | 3 | 5 | 71 | KEEP | HIGH_FAN_IN |
| replay_batch | domain_and_reference | 139 | 13 | 47 | 1 | KEEP | none |
| rvol_tod_contract | domain_and_reference | 357 | 21 | 75 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| s1_choch442 | domain_and_reference | 119 | 11 | 23 | 7 | KEEP | none |
| s1_confirm443 | domain_and_reference | 75 | 9 | 23 | 1 | KEEP | none |
| s1_context_preview439 | domain_and_reference | 199 | 9 | 37 | 14 | KEEP | HIGH_FAN_IN |
| s1_distribution440 | domain_and_reference | 96 | 11 | 21 | 2 | KEEP | none |
| s1_failed_break441 | domain_and_reference | 81 | 11 | 17 | 10 | KEEP | HIGH_FAN_IN |
| s1_holdings445 | domain_and_reference | 64 | 11 | 15 | 10 | KEEP | HIGH_FAN_IN |
| s1_major446 | domain_and_reference | 118 | 10 | 24 | 1 | KEEP | none |
| s1_rf_volume444 | domain_and_reference | 59 | 7 | 18 | 1 | KEEP | none |
| s1_strict447 | domain_and_reference | 54 | 12 | 17 | 1 | KEEP | none |
| s2_context448 | domain_and_reference | 457 | 12 | 30 | 1 | KEEP | none |
| s2_strict453 | domain_and_reference | 71 | 10 | 19 | 1 | KEEP | none |
| s3_context454 | domain_and_reference | 491 | 15 | 31 | 4 | KEEP | none |
| s3_holdings465 | domain_and_reference | 166 | 10 | 18 | 1 | KEEP | none |
| s3_tp458 | domain_and_reference | 153 | 11 | 20 | 2 | KEEP | none |
| s3_tp_event463 | domain_and_reference | 207 | 11 | 23 | 2 | KEEP | none |
| s4_holdings471 | domain_and_reference | 142 | 10 | 18 | 1 | KEEP | none |
| s4_rejection467 | domain_and_reference | 364 | 12 | 19 | 2 | KEEP | none |
| s5_holdings477 | domain_and_reference | 142 | 10 | 18 | 1 | KEEP | none |
| s5_transition473 | domain_and_reference | 445 | 15 | 15 | 5 | KEEP | none |
| s6_breakout479 | domain_and_reference | 431 | 15 | 18 | 3 | IMPROVE | DUPLICATE_AST |
| s6_holdings484 | domain_and_reference | 152 | 14 | 22 | 1 | KEEP | none |
| s6_rf_volume483 | domain_and_reference | 87 | 14 | 17 | 2 | KEEP | none |
| s7_breakdown486 | domain_and_reference | 444 | 15 | 18 | 2 | IMPROVE | DUPLICATE_AST |
| s7_holdings490 | domain_and_reference | 148 | 11 | 19 | 1 | KEEP | none |
| s7_retest_evidence | domain_and_reference | 572 | 21 | 75 | 2 | IMPROVE | FILE_500_PLUS, HIGH_BRANCH_SCORE |
| s8_context492 | domain_and_reference | 390 | 21 | 24 | 3 | IMPROVE | HIGH_BRANCH_SCORE |
| s8_holdings497 | domain_and_reference | 154 | 14 | 22 | 1 | KEEP | none |
| s8_rf_volume496 | domain_and_reference | 87 | 14 | 17 | 2 | KEEP | none |
| segmented_cache | cache_and_persistence | 295 | 27 | 58 | 1 | IMPROVE | HIGH_BRANCH_SCORE |
| session_calendar | domain_and_reference | 128 | 14 | 21 | 3 | KEEP | none |
| source_capability_evidence | domain_and_reference | 231 | 32 | 76 | 1 | IMPROVE | HIGH_BRANCH_SCORE |
| source_quality | domain_and_reference | 296 | 39 | 58 | 21 | IMPROVE | HIGH_BRANCH_SCORE, HIGH_FAN_IN |
| ssi_historical_availability | source_adapter_and_quality | 95 | 12 | 45 | 0 | KEEP | none |
| ssi_intraday_label_diagnostics | source_adapter_and_quality | 181 | 17 | 87 | 0 | KEEP | none |
| ssi_intraday_session_probe209 | domain_and_reference | 202 | 38 | 104 | 1 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| ssi_multivenue_review | source_adapter_and_quality | 129 | 11 | 59 | 0 | KEEP | none |
| ssi_source_qualification | source_adapter_and_quality | 345 | 16 | 64 | 2 | KEEP | none |
| ssi_volume_parity | source_adapter_and_quality | 229 | 20 | 63 | 2 | IMPROVE | HIGH_BRANCH_SCORE |
| structural_phase_evidence | domain_and_reference | 611 | 34 | 110 | 6 | IMPROVE | FILE_500_PLUS, FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| unified_mode459 | domain_and_reference | 121 | 13 | 26 | 1 | KEEP | none |
| validation_replay461 | domain_and_reference | 134 | 12 | 19 | 0 | KEEP | none |
| vcbs_source_contract | source_adapter_and_quality | 175 | 19 | 41 | 0 | KEEP | none |
| vn_2026_closure_anchors | domain_and_reference | 102 | 8 | 30 | 0 | KEEP | none |
| vn_backtest_execution_fixture | domain_and_reference | 184 | 18 | 38 | 0 | KEEP | none |
| vn_release_rollback | engineering_governance | 345 | 35 | 97 | 0 | IMPROVE | FUNCTION_90_PLUS, HIGH_BRANCH_SCORE |
| vwap_contract343 | domain_and_reference | 224 | 33 | 72 | 1 | IMPROVE | HIGH_BRANCH_SCORE |
| zone_manifest_v03 | domain_and_reference | 269 | 18 | 31 | 7 | KEEP | none |

## Review gates
Any proposed change must freeze current fixture behavior, assess direct
and transitive consumers, test corrupt/stale/source-boundary paths,
and demonstrate a scoped rollback. An unchanged module can be kept.
No market provider rights, live cache, release or OOS are certified.
