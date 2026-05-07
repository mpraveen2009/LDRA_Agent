# TCF Validator Agent

## Goal
Validate generated LDRA `.tcf` files against the sample format and LDRA execution constraints before running TBrun.

## Inputs
- `sample_tcf_path`
- `generated_tcf_files[]`
- optional `expected_source_file`

## Current Reference (from user-provided sample)
- `sample_tcf_path`: `C:\Users\k64126431\OneDrive - KONE Corporation\Work_dir\IEX_Repos\iex_msc\LDRA\Unit Testing\Application\brakeLiftMonitoring.tcf`
- `expected_source_file`: `C:\Users\k64126431\OneDrive - KONE Corporation\Work_dir\IEX_Repos\iex_msc\SourceFiles\Application\NonSecure\SafetyFunctions\BrakeLiftMonitor\brakeLiftMonitoring.c`

## Required MCP Tools
- `mcp_ldra-tbrun_read_tcf_file`

## Validation Checks
1. Header compatibility
- Accept optional `$ Begin Test Regression Automation Information` block.
- Require `# Begin Testbed Set` and `# End Testbed Set`.

2. Source mapping
- Require `RelativeFile = .\<source>.c`.
- Require absolute `File = <...>\<source>.c` entry.
- Verify generated file references the intended source file.

3. Structural sections
- Require at least one:
  - `# Begin Attributes`
  - `# Begin Test Case`
  - `# Begin Variable`
- Ensure each opened section is properly closed.

4. Test-case content quality
- Reject test cases with missing variable blocks.
- Reject empty/placeholder-only values for required inputs/expected outputs.
- Require explicit `Usage` codes per variable (`I`, `O`, `P`, `H`, `Z`, `G` as applicable).

5. Exhaustiveness checks
- Verify generated TCF includes test cases for all discovered procedures from the target source file.
- Verify each non-`void` procedure includes at least one `Usage = O` return expectation.
- Verify file-scope static variables from the target source are represented via `Usage = G` entries in generated test cases.

6. Read-back safety
- Re-read each TCF post-write and verify parser-safe plain text shape.

## Output Contract
```json
{
  "valid": true,
  "sample_tcf_path": "...",
  "results": [
    {
      "tcf": "...",
      "valid": true,
      "issues": []
    }
  ]
}
```

## Failure Policy
- If any file is invalid, block execution and return actionable fixes.
- Never auto-invent expected values; mark as `record-first` when deterministic expected values are unknown.
