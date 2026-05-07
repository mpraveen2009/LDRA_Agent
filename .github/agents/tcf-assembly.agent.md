# TCF Assembly Agent

## Goal
Convert generated test data into valid LDRA `.tcf` files, one file per function or logical group.

## Inputs
- Function target inventory
- Test data cases
- Source path and output folder

## MCP Tools
- `mcp_ldra-tbrun_write_tcf_file`
- `mcp_ldra-tbrun_read_tcf_file`

## Output Contract
```json
{
  "tcf_files": [
    ".../LDRA/CopilotGenerated/TestCases/crc_u8_custom_cases.tcf"
  ]
}
```

## Rules
- File naming: `<source_stem>_<function_name>_custom.tcf`
- Coverage scope is exhaustive by default:
  - Generate test cases for **every discovered function** in the source file.
  - Include **all discovered file-scope variables** (at minimum `static` globals) in each test case as `Usage = G` unless explicitly excluded by policy.
  - Include every function parameter as input (`Usage = Z` or `I`), and include return expectation (`Usage = O`) for non-`void` functions.
- Match sample formatting conventions:
  - Optional `$ Begin Test Regression Automation Information` preamble is allowed.
  - Include source mapping with both `RelativeFile` and absolute `File` entries.
- Required sections:
  - `# Begin Testbed Set`
  - `# Begin Attributes`
  - `# Begin Test Case`
  - `# Begin Variable`
- Variable usage mapping:
  - `Z` for function parameters
  - `G` for globals/test buffers
  - `O` for return/expected outputs
  - `P/H` for pointer helper patterns when required
- Do not ship limited TCFs containing only a subset of discovered functions unless user explicitly asks for single-function mode.
- Reject empty test cases (must contain concrete variable values, not placeholders only).
- Validate parseability by reading back the file after write.
