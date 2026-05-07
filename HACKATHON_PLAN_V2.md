# LDRA Agent-Only Hackathon Plan (V2)

## Objective
Build an LDRA-focused, agent-first CI flow where AI agents orchestrate test generation and execution through MCP tools, with minimal custom Python logic.

## Design Principles
- Agent-first orchestration in Markdown specs.
- MCP tools are the execution interface to LDRA CLI.
- No synthetic report generation.
- Use only LDRA-generated artifacts for official reporting.
- Keep server module thin: trigger + status + job routing.

## Agent Topology

1. Trigger Agent
- Receives local trigger calls from self-hosted GitHub Actions.
- Creates job IDs and enqueues execution.
- Exposes `/trigger` and `/status/{job_id}`.

2. Function Discovery Agent
- Reads changed C files.
- Extracts procedures via MCP.
- Outputs testable function list.

3. Test Data Generator Agent
- Produces normal, boundary, and error vectors.
- Defines expected mode: `fixed` or `record-first`.

4. TCF Assembly Agent
- Converts function/test vectors to LDRA-compatible TCF files.
- Stores under `LDRA/CopilotGenerated/TestCases`.

5. LDRA Execution Agent
- Executes TCFs sequentially via MCP.
- Supports `unit-only` and `with-report` modes.
- Applies retry policy for transient exits.

6. LDRA Report Harvester Agent
- Collects LDRA-generated report artifacts only.
- Resolves real report paths and publishes references.
- No handmade HTML/coverage artifacts.

7. Reporting Agent
- Posts summary/status from LDRA outputs.
- Publishes PR comments and job status checks.

## Trigger Flow
1. Source repo push.
2. Self-hosted runner invokes local POST `http://localhost:8000/trigger`.
3. Payload: `source_repo`, `commit_sha`, `branch`.
4. Server returns `{ accepted: true, job_id }`.
5. Workflow polls `/status/{job_id}` until terminal state.

## LDRA Modes

- unit-only
  - Run `record` + `regress` without static analysis.
  - Fast signal for commit-level validation.

- with-report
  - Run static analysis/instrumentation where required.
  - Execute tests and collect LDRA-generated report artifacts.

## Report Policy
- Allowed: LDRA-generated `.dyn.html`, `.exh`, and related outputs.
- Not allowed: custom generated `.dyn.html` or fabricated coverage metrics.
- If report missing: return explicit reason and path scan log.

## Team Split (4 People)

Person 1
- Self-hosted runner + local trigger endpoints.

Person 2
- Function discovery + test data generation agents.

Person 3
- TCF assembly + LDRA execution agent.

Person 4
- Report harvesting + GitHub reporting integration.

## Deliverables
- `.github/agents/ldra-orchestrator.agent.md`
- `.github/agents/function-discovery.agent.md`
- `.github/agents/testdata-generator.agent.md`
- `.github/agents/tcf-assembly.agent.md`
- `.github/agents/tcf-validator.agent.md`
- `.github/agents/reporting.agent.md`
- `.github/agents/ldra-execution.agent.md`
- `.github/agents/ldra-report-harvester.agent.md`
- `.github/instructions/ldra-cli-reference.md`
- `.github/instructions/ldra-web-reference.md`

## Success Criteria
- Commit triggers local LDRA pipeline reliably.
- Agent chain produces valid TCFs for changed files.
- Sequential LDRA execution succeeds with retry policy.
- Reporting uses only LDRA-generated artifacts.
- End-to-end status flows back to GitHub checks/comments.

## Bonus Task: contextLens Hover Integration
- Add LDRA unit-test context to contextLens hover cards.
- Implement `TestReportContext` and `TestReportIndex` in models.
- Add `testReportLoader` that indexes `results.json` and supports file+function lookups.
- Wire loader into hover provider and extension activation.
- Add watcher for `results.json` refresh.
- Add unit tests for parsing, lookup, and malformed/missing file handling.
