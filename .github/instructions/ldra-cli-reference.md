# LDRA CLI Reference (Local Capture)

This reference is based on commands executed on the local machine and saved raw under `.github/instructions/`.

## Captured Files
- `.github/instructions/ldra_tbini_help.txt`
- `.github/instructions/ldra_contbrun_help.txt`
- `.github/instructions/ldra_contestbed_help.txt`

## TBini (captured successfully)
Command used:
- `TBini.exe /?`

Observed synopsis:
- `tbini [-Profile='<lang>' || -Section='<section_name>'] KEY[=VALUE]`

Purpose:
- Configure LDRA ini flags and section settings.

## Contbrun and Contestbed
Commands used:
- `Contbrun.exe /?`
- `Contestbed.exe /?`

Observed behavior:
- CLI startup attempted license initialization first.
- On this host, help invocation hit license host validation issues for those tools in the captured runs.

## License Diagnostic Captured
From local output:
- `License Initialisation failure`
- `Invalid host`
- `FLEXlm Code -9`

## Agent Guidance
- Use MCP wrappers for normal execution and status handling.
- Use TBini help output for local configuration reference.
- Treat Contbrun/Contestbed raw help as environment-sensitive due to license checks.
