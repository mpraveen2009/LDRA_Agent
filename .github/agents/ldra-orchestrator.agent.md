# LDRA Orchestrator Agent

## Goal
Run an end-to-end LDRA unit-test workflow from commit changes without creating a separate Python orchestration app.

## Generator Agent Chain
- `function-discovery.agent.md`
- `testdata-generator.agent.md`
- `tcf-assembly.agent.md`
- `tcf-validator.agent.md`
- `ldra-execution.agent.md`
- `ldra-report-harvester.agent.md`

## Agent Contract
- Input: changed files from commit/webhook, project root, LDRA project context.
- Output: generated TCF files, test execution status, and summary for PR comments.
- Transport: MCP tool calls only.

## Model Selection Policy
- For test-case generation quality, use the best available reasoning model for the `testdata-generator` stage.
- Preferred model: `GPT-5.3-Codex (copilot)`.
- Keep model choice explicit in orchestration metadata for reproducibility.

## Required MCP Tools
- `mcp_ldra-tbrun_read_c_file`
- `mcp_ldra-tbrun_list_procedures`
- `mcp_ldra-tbrun_write_tcf_file`
- `mcp_ldra-tbrun_read_tcf_file`
- `mcp_ldra-tbrun_run_tbrun`
- `mcp_ldra-tbrun_run_static_analysis` (only when report/instrumentation is required)
- `mcp_ldra-tbrun_read_coverage_results`

## Workflow
1. Accept changed file list and keep only `.c/.h/.cpp/.hpp` files.
2. Run **Function Discovery Agent** to produce testable procedures.
3. Run **Test Data Generator Agent** to produce normal/boundary/error case data for all discovered procedures.
4. Run **TCF Assembly Agent** in exhaustive mode to generate `.tcf` files under `LDRA/CopilotGenerated/TestCases` covering all discovered functions and file-scope variables.
5. Run **TCF Validator Agent** to validate generated files against sample format + structure rules.
6. Run **LDRA Execution Agent** to execute tests one-by-one using `run_tbrun`:
   - `record` first (optional)
   - then `regress`
7. On failure, retry only for transient exit codes (`91`, `92`, `93`) up to policy limit.
8. Run **LDRA Report Harvester Agent** to collect LDRA-generated artifacts.
9. Read coverage with `read_coverage_results` when project workarea is available.
10. Return a machine-readable summary:
   - total tests
   - passed/failed
   - per-file outcome
   - exit-code meaning

## Execution Policies
- `unit-only`: skip `run_static_analysis`; run `record/regress` only.
- `with-report`: run static analysis/instrumentation before dynamic run.
- `strict`: fail pipeline if any test fails or required coverage threshold is not met.

## Report Policy
- Never generate synthetic `.dyn.html` or custom coverage artifacts.
- Publish only LDRA-generated report files and LDRA-origin coverage data.

## Naming Convention
- TCF file: `<source_stem>_<function_name>_custom.tcf`
- Sequence name: `<function_name>_Seq`
- Test descriptions: `TC100`, `TC200`, `TC300` ...

## Retry Policy
- Retryable exit codes: `91` (build), `92` (execution), `93` (timeout)
- Max retries default: `1`
- Never retry deterministic failures like regression mismatch (`90`) more than policy allows.

## Output Schema
```json
{
  "changed_files": ["path/to/file.c"],
  "tcf_files": ["path/to/generated.tcf"],
  "summary": {
    "total_tests": 0,
    "passed": 0,
    "failed": 0
  },
  "results": [
    {
      "test_tcf": "...",
      "exit_code": 0,
      "meaning": "Pass"
    }
  ]
}
```
