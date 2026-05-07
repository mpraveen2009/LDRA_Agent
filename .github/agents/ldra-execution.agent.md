# LDRA Execution Agent

## Goal
Execute LDRA TCF tests sequentially through MCP tools and return deterministic pass/fail outcomes.

## Inputs
- `project_tcf`
- `tcf_files[]`
- mode policy: `unit-only` or `with-report`
- retry count

## Required MCP Tools
- `mcp_ldra-tbrun_run_tbrun`
- `mcp_ldra-tbrun_run_static_analysis` (only for with-report)
- `mcp_ldra-tbrun_read_coverage_results`

## Flow
1. If mode is `with-report`, run static analysis/instrumentation first.
2. For each TCF in deterministic order:
   - run `record`
   - run `regress`
3. Retry only for transient exit codes (91, 92, 93).
4. Collect exit code, meaning, attempts, stderr.
5. Return execution summary JSON.

## Output Schema
```json
{
  "summary": {"total": 0, "passed": 0, "failed": 0},
  "results": [
    {"test_tcf": "...", "exit_code": 0, "meaning": "Pass", "attempts": 1}
  ]
}
```
