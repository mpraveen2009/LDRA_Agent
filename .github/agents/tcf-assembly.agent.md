# TCF Assembly Agent

## Goal
Convert test data from the Test Data Generator into valid, exhaustive LDRA `.tcf` files that match the quality and structure of human-authored LDRA TCF files. Every test case must list ALL variables from the function's variable universe.

## Inputs
- Function target inventory (with full variable universe from Function Discovery)
- Test data cases (with active + removed variables from Test Data Generator)
- Source path and output folder

## MCP Tools
- `mcp_ldra-tbrun_write_tcf_file`
- `mcp_ldra-tbrun_read_tcf_file`

## TCF Structure (must follow this exact layout)

### 1. Testbed Set Header
```
 # Begin Testbed Set

 SINGLE_FILE = TRUE
 GENERATED_BY = LDRA MCP Agent

    # Begin Source Files

    RelativeFile = .\<source_filename>.c
    File = <absolute_path_to_source>.c

    # End Source Files

 # End Testbed Set
```

### 2. Attributes Block
```
    # Begin Attributes

      Sequence Name = <source_stem>_Seq
      Language Code = 2

    # End Attributes
```

### 3. Test Case Blocks (one per test vector)
Each test case MUST contain:
```
    # Begin Test Case

      File = <absolute_path_to_source>.c
      Procedure = <function_name>
      Procedure Number = <N>
      Creation Date = <Mon DD YYYY HH:MM:SS>

        # Begin Variable

          Name = <variable_name>
          Decl_type = <C_type>
          Usage = G
          Value = <concrete_value>

        # End Variable

        ... more active variables ...

        # Begin Removed Variable

          Name = <variable_name>
          Decl_type = <C_type>
          Usage = G

        # End Removed Variable

        ... more removed variables ...

    # End Test Case
```

## Variable Block Rules

### Active Variables (`# Begin Variable` / `# End Variable`)
- MUST have `Name`, `Decl_type`, `Usage`, and `Value` fields
- These are the variables that drive this specific test case
- A variable can appear twice: once as `Usage = G` (input setup) and once as `Usage = H` (expected output check)

### Removed Variables (`# Begin Removed Variable` / `# End Removed Variable`)
- MUST have `Name`, `Decl_type`, and `Usage` fields
- MUST NOT have a `Value` field
- These are variables from the function's universe that are NOT active in this test case
- They MUST still be listed to show the complete variable inventory
- Both G and H variants of a variable should be listed as removed if not active

### Struct Member Variables
- Use exact qualified name with array index: `sMscFaultsList[54].u8FaultReturnStatus`
- Add `Packed = T` on a separate line within the variable block when applicable

### Usage Codes
| Code | Meaning |
|------|---------|
| `G`  | Global/static variable input — set before function call |
| `H`  | Helper/expected output — checked after function call |
| `I`  | Input parameter passed to function |
| `O`  | Output/return value expected from function |
| `Z`  | Parameter (alternative style) |
| `P`  | Pointer input (paired with H helper) |

## Assembly Rules

1. **File naming**: `<source_stem>_all_functions_custom.tcf` for exhaustive file, or `<source_stem>_<function_name>_custom.tcf` for single-function.

2. **ALL functions must be covered** — generate test cases for every discovered procedure in the source file.

3. **ALL variables must appear in EVERY test case** — either as active (with Value) or as removed (without Value). This is the critical quality requirement.

4. **Multiple test cases per function** — one per execution path / branch combination. Minimum: enough test cases to achieve full branch coverage.

5. **Ordering within a test case**:
   - Active `Usage = G` variables first (inputs)
   - Active `Usage = H` variables next (expected outputs)
   - Active `Usage = O` variables (return values)
   - Removed `Usage = G` variables
   - Removed `Usage = H` variables

6. **Concrete values only** — never use placeholders like `TODO`, `???`, or empty values. Use `record-first` mode (omit Value and let LDRA record it) only when explicitly flagged by the test data generator.

7. **Validate after write** — call `mcp_ldra-tbrun_read_tcf_file` to read back and verify the file parses correctly.

8. **Do not ship limited TCFs** — reject any TCF that has test cases without variable blocks.

## Output Contract
```json
{
  "tcf_files": [
    ".../LDRA/CopilotGenerated/TestCases/brakeLiftMonitoring_all_functions_custom.tcf"
  ],
  "stats": {
    "total_test_cases": 45,
    "total_active_variables": 312,
    "total_removed_variables": 1890,
    "procedures_covered": 8
  }
}
```
