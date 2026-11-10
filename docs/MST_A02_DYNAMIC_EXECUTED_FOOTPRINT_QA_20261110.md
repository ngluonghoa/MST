# MST A02 — Dynamic execution footprint: eight original V1 test suites, 63 modules

Date: 2026-11-10 (Asia/Ho_Chi_Minh)
QA ID: MST-A02-ORIGINAL-63-DYNAMIC-PYTHON-CALL-FOOTPRINT
Status: New GitHub-hosted execution evidence PENDING at implementation HEAD; no owner signoff.

## Why this is new and needed
The existing H3+AST 63-row evidence matrix links all 63 legacy modules to eight scripted A02 tranche QA packets and 62 scoped-domain/one __init__ import check. It is a STATIC test-to-path association and cannot demonstrate which original V1 functions actually executed under each suite. This new audit **measures real Python function call and executed-line events** inside the original package while the eight existing A02 unittest suites run separately in GitHub Actions. It distinguishes FUNCTION_CALLED_IN_SELECTED_EIGHT_SUITES vs IMPORT_OR_MODULE_LEVEL_ONLY vs NOT_OBSERVED_IN_SELECTED_SUITES, with package __init__ explicitly classified as METADATA only.

The tracer runs 8 exact original A02 unittest test files (B01–B08) under eight isolated GitHub-hosted Python child processes using standard-library sys.settrace, with outbound socket connect denied. It records source-file paths, integer call counts, number of called function-name identifiers and line counts (and total tests passed), no OHLCV or market data. The original 63 file paths are identified from the inherited src/swing_trading package and independently exclude exactly the eight already-approved opt-in V2 files. Existing live remote upstream/main/PR source bytes are locked before this audit. Final output is a schema-bound 63-row JSON, plus batch-level counts, archived for 14 days. No real licensed provider endpoint, Google Drive cache, privileged GitHub action, broker or local machine.

The 24 new negative tests check missing eighth suite, altered batch order, wrong original modules, V2 path disguised as V1, duplicate source, zero or boolean coverage counts, unauthorized owner flags, code executed without line proof, and never converting a traced invocation into full 1:1 behavioral acceptance. Original source is read-only.

## Interpretation
- Calls and executed source lines are **observed on these particular synthetic fixtures**, not branch/path/requirements coverage for every input, nor authenticated benchmark/calculation correctness.
- A module may be executed transitively from another suite; this is not a proof of assigned module's own unit coverage.
- Class body/import metadata execution does not mean that a production function was tested.
- No source-level requirements, live price feed, genuine remote cache or fully signed owner approvals exist; A02 owners 0/63, A03 V2 0/8 and A03 choices 0/14 remain unapproved.

The concrete new dynamic count must be taken from a completed GitHub-hosted receipt, not guessed. No production/trading authorization from this test.

## Next step
Review measured NOT_OBSERVED and IMPORT_ONLY paths. Prefer closing an actual under-exercised original behavior on synthetic fixtures with a targeted test, not claiming 63/63 full behavior parity or adding more unreviewed owner forms. Keep PR8 Draft; protect main; no production.
