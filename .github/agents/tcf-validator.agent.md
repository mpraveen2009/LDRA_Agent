# TCF Validator Agent

## Goal
Validate generated LDRA `.tcf` files against the reference TCF structure and ensure every test case has complete variable coverage before running TBrun.

## Inputs
- `reference_tcf_path` (human-authored reference for comparison)
- `generated_tcf_files[]`
- `variable_universe` (from Function Discovery Agent)
- optional `expected_source_file`

## Current Reference (from user-provided sample)
- `reference_tcf_path`: `C:\Users\k64126431\OneDrive - KONE Corporation\Work_dir\IEX_Repos\iex_msc\LDRA\Unit Testing\Application\brakeLiftMonitoring.tcf`
- `expected_source_file`: `C:\Users\k64126431\OneDrive - KONE Corporation\Work_dir\IEX_Repos\iex_msc\SourceFiles\Application\NonSecure\SafetyFunctions\BrakeLiftMonitor\brakeLiftMonitoring.c`

## Required MCP Tools
- `mcp_ldra-tbrun_read_tcf_file`

## Validation Checks

### 1. Header compatibility
- Accept optional `$ Begin Test Regression Automation Information` block.
- Require `# Begin Testbed Set` and `# End Testbed Set`.

### 2. Source mapping
- Require `RelativeFile = .\<source>.c`.
- Require absolute `File = <...>\<source>.c` entry.
- Verify generated file references the intended source file.

### 3. Structural sections
- Require at least one:
  - `# Begin Attributes`
  - `# Begin Test Case`
  - `# Begin Variable`
- Ensure each opened section is properly closed (`# End ...`).

### 4. Variable completeness (CRITICAL)
For EACH test case:
- **Count active variables** (`# Begin Variable` / `# End Variable` with Value) — MUST be >= 1.
- **Count removed variables** (`# Begin Removed Variable` / `# End Removed Variable` without Value) — MUST be >= 0.
- **Total variable count** (active + removed) must equal the function's variable universe size. If it doesn't, the TCF is INCOMPLETE.
- Every active variable MUST have: `Name`, `Decl_type`, `Usage`, `Value`.
- Every removed variable MUST have: `Name`, `Decl_type`, `Usage` — and MUST NOT have `Value`.
- Struct member variables (e.g., `sMscFaultsList[54].u8FaultReturnStatus`) must include `Packed = T`.

### 5. Usage code validation
- `Usage = G` — global/static input (valid for active and removed)
- `Usage = H` — helper/expected output (valid for active and removed)
- `Usage = I` / `Usage = Z` — parameter input
- `Usage = O` — return value
- Non-void functions MUST have at least one `Usage = O` or `Usage = H` variable per test case.

### 6. Procedure coverage
- Verify generated TCF includes test cases for ALL discovered procedures from the target source file.
- Flag any procedure with zero test cases.

### 7. Branch coverage estimation
- Count test cases per procedure.
- Compare against expected minimum (number of decision branches from source analysis).
- Warn if a procedure has fewer test cases than decision branches.

### 8. Read-back safety
- Re-read each TCF post-write via `mcp_ldra-tbrun_read_tcf_file`.
- Verify no encoding issues or truncation.

## Output Contract
```json
{
  "valid": true,
  "results": [
    {
      "tcf": "path/to/generated.tcf",
      "valid": true,
      "total_test_cases": 45,
      "total_active_variables": 312,
      "total_removed_variables": 1890,
      "procedures_covered": 8,
      "issues": [],
      "warnings": ["vHandleBrakeMonitoring has 4 test cases but 6 decision branches"]
    }
  ]
}
```

## Failure Policy
- **BLOCK execution** if any test case has ZERO variable blocks — this is the #1 quality failure.
- **BLOCK execution** if any test case is missing removed variables (incomplete universe).
- If any file is invalid, return actionable fixes specifying which variables are missing.
- Never auto-invent expected values; mark as `record-first` when deterministic expected values are unknown.
