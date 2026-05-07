# Test Data Generator Agent

## Goal
Generate robust normal, boundary, and error test vectors for each discovered function.

## Inputs
- Function target list from Function Discovery Agent
- Optional domain constraints (ranges, nullability, safety conditions)

## Output Contract
```json
{
  "cases": [
    {
      "procedure": "u8Crc8",
      "id": "TC100",
      "category": "boundary",
      "inputs": {
        "u8Array": "&TestBuff",
        "u32Bytes": "0u",
        "globals": {"TestBuff[0]": "0u"}
      },
      "expected": {
        "mode": "fixed",
        "return": "0u"
      }
    }
  ]
}
```

## Rules
- Minimum per procedure: 1 normal + 1 boundary + 1 error-oriented case when feasible.
- Mark expected policy explicitly:
  - `fixed`: deterministic expected value is known
  - `record-first`: expected value captured from initial run
- Keep values LDRA-compatible (`0u`, `1u`, enums, pointer aliases).

## Model Guidance
- Use the strongest available reasoning model for this stage.
- Preferred model: `GPT-5.3-Codex (copilot)`.
- Prioritize semantic correctness of boundary/error vectors over case volume.
