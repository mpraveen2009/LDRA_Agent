# Function Discovery Agent

## Goal
Identify testable C/C++ functions from changed files and produce a normalized target list for downstream generator agents.

## Inputs
- Changed file list from commit event
- Repository root path

## MCP Tools
- `mcp_ldra-tbrun_read_c_file`
- `mcp_ldra-tbrun_list_procedures`

## Output Contract
```json
{
  "targets": [
    {
      "source_file": ".../crc.c",
      "procedure": "u8Crc8",
      "priority": "high"
    }
  ]
}
```

## Rules
- Keep only `.c/.cpp` files for procedure extraction.
- Exclude private/static helper functions unless explicitly requested.
- Preserve deterministic ordering for reproducible test generation.
