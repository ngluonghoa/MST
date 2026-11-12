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


## Measured GitHub-hosted A02 dynamic footprint at implementation code HEAD (2026-11-10)

Actual GitHub Draft PR #8 implementation code HEAD `2aaa359f68e72f78e60b6fd78b38ea78709bd015` verified **41/41 GitHub Actions workflow runs SUCCESS**. The amended A02 63-module owner matrix workflow https://github.com/ngluonghoa/MST/actions/runs/42827829755 completed SUCCESS, including original 63 V1 + eight pre-existing V2 upstream/main/PR source byte lock, prior 35 matrix tests, and **24 new dynamic trace validation tests**. All eight B01–B08 original synthetic A02 unittest suites actually ran under the new CPython tracer as eight isolated child processes:

- **330/330 tests PASS** across the eight selected A02 suites.
- **62/63 original V1 modules with function call events**. The remaining original module is the package `src/swing_trading/__init__.py`, previously classified import/version/metadata only; **63/63 original V1 modules appeared in import/line execution events**.
- 63/63 original source files with source line events; no original module entirely unseen by selected A02 suites.
- 8 approved, opt-in V2 sidecars strictly excluded from V1 source classification.
- Metadata receipt SHA256 `24d9bc967ebbb4a64d456130b0345792978dd842766da9a7a83dd68434597992` is a deterministic QA fingerprint, not owner or supplier authority.

**Important interpretation:** call events do not prove distinct tested branches, each individual method, all transitions or all symbol/market/timeframe combinations, error handling completeness, financial results, real source quality, or full V1↔V2 1:1 behavior. Some calls were reached transitively from other tests. CPython instrumentation cannot see all C extension work or external workers. No A02 human owner decision was signed (0/63). This is not a parity certification.

The report-containing QA commit after this note must be checked again at its own exact PR HEAD before labeling the final checkpoint 41/41 PASS.
Permanent QA Google Doc and canonical MST handoff/spec/gap to be linked upon verified documentation completion.
