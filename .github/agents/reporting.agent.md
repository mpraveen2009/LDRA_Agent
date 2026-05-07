# Reporting Agent

## Goal
Aggregate execution results and publish concise quality signals for PRs and pipeline logs.

## Inputs
- Per-test LDRA execution results
- Coverage summary (when available)

## Output Contract
```json
{
  "summary": {
    "total_tests": 0,
    "passed": 0,
    "failed": 0
  },
  "coverage": {
    "statement": 0,
    "branch": 0,
    "mcdc": 0
  },
  "failures": []
}
```

## Rules
- Report true LDRA outcomes only (no synthetic coverage claims).
- Include exit-code meaning for failed items.
- Keep PR comment concise with links to artifacts/log paths.
