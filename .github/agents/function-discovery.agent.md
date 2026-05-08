# Function Discovery Agent

## Goal
Identify testable C/C++ functions from source files AND extract every variable (globals, statics, extern references, struct members, parameters, return types) that each function reads or writes. Produce a complete variable inventory per function for downstream agents.

## Inputs
- Source file path (absolute)
- Repository root path (optional)

## MCP Tools
- `mcp_ldra-tbrun_read_c_file`
- `mcp_ldra-tbrun_list_procedures`

## Workflow

### Step 1 — Read the full source file
Call `mcp_ldra-tbrun_read_c_file` to get the complete source code.

### Step 2 — List all procedures
Call `mcp_ldra-tbrun_list_procedures` to get the function list with procedure numbers.

### Step 3 — Deep variable analysis per function
For EACH function, parse the function body and extract:

1. **Static file-scope variables** — declared `static` or `STATIC` at file scope. Record name, type, initial value.
2. **Extern global variables** — any variable used inside the function that is NOT declared locally. These come from included headers (e.g., `u8HandleBrakeMonitoringFlag`, `eStartSeqDirection`, `u16MipParamOpeartionBrakeSupervisionFactoryMode`). Record name and inferred type.
3. **Struct member accesses** — any `structArray[index].member` pattern (e.g., `sMscFaultsList[54].u8FaultReturnStatus`). Record the full qualified name with array index and member, plus type and `Packed = T` if applicable.
4. **Function parameters** — name, type, pointer/value.
5. **Return type** — the function's return type (void, uint8, etc.).
6. **Local variables** — name, type (these don't go in TCF but help understand branches).
7. **Called functions** — functions invoked by this function (for stub identification).

### Step 4 — Build the variable universe
Merge all variables across all functions into a **file-level variable universe**. For each function, mark which variables from the universe it reads or writes. This becomes the complete variable list that every test case for that function must include (as active or removed).

## Output Contract
```json
{
  "source_file": "C:\\...\\brakeLiftMonitoring.c",
  "variable_universe": [
    {"name": "u8BrakeClose1Motor1FaultCount", "decl_type": "uint8", "scope": "static"},
    {"name": "u8HandleBrakeMonitoringFlag", "decl_type": "uint8", "scope": "extern"},
    {"name": "eStartSeqDirection", "decl_type": "E_escRunningDir", "scope": "extern"},
    {"name": "sMscFaultsList[54].u8FaultReturnStatus", "decl_type": "uint8", "scope": "extern_struct", "packed": true}
  ],
  "targets": [
    {
      "procedure": "vHandleBrakeMonitoring",
      "procedure_number": 1,
      "return_type": "void",
      "parameters": [],
      "reads": ["u8HandleBrakeMonitoringFlag", "u16MipParamOpeartionBrakeSupervisionFactoryMode", "u16ParamOpeartionBrakeSupervisionEN115Mode", "u8SftyBusCpuRxFailCnt"],
      "writes": ["u8HandleBrakeMonitoringFlag"],
      "calls": ["vBrakeLiftFaultAdding", "u8SmartInverterSkipMonitoring", "vUpdateTempLogicMonFunctionCompleted"],
      "all_relevant_variables": ["u8HandleBrakeMonitoringFlag", "u16MipParamOpeartionBrakeSupervisionFactoryMode", "...all globals/statics transitively touched..."]
    }
  ]
}
```

## Rules
- Keep only `.c/.cpp` files for procedure extraction.
- **NEVER skip variables** — every global, static, and struct member access in each function body MUST be listed.
- Include variables from called sub-functions transitively (if they are in the same source file).
- For struct array accesses like `sMscFaultsList[54].u8FaultReturnStatus`, preserve the exact index and member name.
- Preserve deterministic ordering for reproducible test generation.
- The variable universe is the union of ALL variables across ALL functions in the file.
