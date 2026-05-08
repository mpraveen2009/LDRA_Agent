# Test Data Generator Agent

## Goal
Generate exhaustive test vectors for each function that cover ALL code paths and include EVERY variable from the function's variable universe. Each test case must specify which variables are active (with concrete values) and which are removed (present but unused in that path).

## Inputs
- Function target list with full variable inventory from Function Discovery Agent
- Source code (via `mcp_ldra-tbrun_read_c_file`)
- Optional domain constraints (ranges, nullability, safety conditions)

## Workflow

### Step 1 — Analyse each function's control flow
Read the source code and trace every `if/else`, `switch/case`, `for/while` branch. Identify:
- Every unique execution path through the function
- The precondition (global/static variable values) needed to reach each path
- The postcondition (expected changes to globals/statics/struct members) after each path

### Step 2 — Build test cases per path
For each unique path, create a test case that:
1. **Sets up preconditions** — Active variables with `Usage = G` and concrete `Value` for every global/static that must hold a specific value to enter that path.
2. **Defines expected outputs** — Active variables with `Usage = H` and concrete `Value` for every global/static/struct member modified by that path.
3. **Lists all unused variables as removed** — Every variable from the function's variable universe that is NOT active in this test case must still appear as a "removed" entry (no Value).

### Step 3 — Ensure branch coverage
- Minimum per procedure: **one test case per decision branch** (not just 1 normal + 1 boundary).
- For `if (A && B && C)` conditions, create test cases where each sub-condition is independently FALSE.
- For `switch` statements, create one test case per `case` label plus one for `default`/fallthrough.
- For fault counters (e.g., `u8BrakeLift1Motor1FaultCount`), test boundary at threshold values (e.g., count < max, count == max, count > max).

### Step 4 — Mark expected value policy
- `fixed`: use when the expected output is deterministic and known from code analysis
- `record-first`: use when the expected value requires runtime recording (complex calculations, hardware-dependent values)

## Output Contract
```json
{
  "cases": [
    {
      "procedure": "vCheckBrakeLiftFaultRunning",
      "procedure_number": 5,
      "id": "TC100",
      "category": "branch-path-1",
      "description": "Brake1Motor1 feedback ASSERTED, fault count at threshold",
      "active_variables": [
        {"name": "u8Brake1Motor1Feedback", "decl_type": "uint8", "usage": "G", "value": "ASSERTED"},
        {"name": "u8BrakeLift1Motor1Fault", "decl_type": "uint8", "usage": "G", "value": "INACTIVE"},
        {"name": "u8BrakeLift1Motor1FaultCount", "decl_type": "uint8", "usage": "G", "value": "20u"},
        {"name": "sMscFaultsList[54].u8FaultReturnStatus", "decl_type": "uint8", "usage": "H", "value": "FAULTY_STATE", "packed": true},
        {"name": "u8BrakeLift1Motor1Fault", "decl_type": "uint8", "usage": "H", "value": "ACTIVE"},
        {"name": "u8BrakeLift1Motor1FaultCount", "decl_type": "uint8", "usage": "H", "value": "21u"}
      ],
      "removed_variables": [
        {"name": "u8BrakeLift1Motor2FaultCount", "decl_type": "uint8", "usage": "H"},
        {"name": "u8BrakeLift2Motor2FaultCount", "decl_type": "uint8", "usage": "H"},
        {"name": "sMscFaultsList[180].u8FaultReturnStatus", "decl_type": "uint8", "usage": "H", "packed": true}
      ],
      "expected_policy": "fixed"
    }
  ]
}
```

## Variable Usage Codes
| Code | Meaning | When to use |
|------|---------|-------------|
| `G`  | Global input | Set a global/static/extern variable BEFORE the function runs |
| `H`  | Helper/expected output | Check a global/static/struct member value AFTER the function runs |
| `I`  | Input parameter | Value passed as a function parameter |
| `O`  | Output/return value | Expected return value of the function |
| `Z`  | Parameter (alternative) | Function parameter in some TCF styles |
| `P`  | Pointer input | Pointer parameter (paired with H helper) |

## Rules
- **EVERY variable from the function's variable universe MUST appear in EVERY test case** — either as active (with Value) or as removed (without Value).
- A variable may appear TWICE in one test case: once as `Usage = G` (input) and once as `Usage = H` (expected output) when the function both reads and modifies it.
- For struct arrays like `sMscFaultsList[N].u8FaultReturnStatus`, use the exact array index from the source code and set `packed = true`.
- Keep values LDRA-compatible: `0u`, `1u`, `ACTIVE`, `INACTIVE`, `ASSERTED`, `DEASSERTED`, enum names, etc.
- **Do NOT generate empty test cases** — every test case must have at least one active variable.
- Target coverage: all decision branches for Statement + Branch coverage; MC/DC for safety-critical code.

## Model Guidance
- Use the strongest available reasoning model for this stage.
- Prioritize completeness (all variables, all branches) over brevity.
