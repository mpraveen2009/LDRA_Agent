# LDRA TBrun Automated Testing Hackathon Plan

## Project Goal
Develop an end-to-end CI/CD workflow that automatically scans GitHub commits for C/C++ file changes and runs LDRA TBrun unit tests sequentially. When new files are detected or existing files are modified, the system analyzes the code and generates comprehensive test cases.

---

## Team Structure: 4 People, 1 Team

## Agent-First Architecture (Required)

### Primary Agent: IEX Test Orchestrator Agent
Purpose: One central AI agent coordinates the full pipeline from commit detection to LDRA reporting.

Agent responsibilities:
- Watch incoming commit events and identify changed C/C++ files
- Trigger function extraction and test case generation jobs
- Schedule unit test runs one-by-one in deterministic order
- Enforce execution policy (unit-only mode for CI, report mode for release)
- Collect run status, exit codes, and retry failed jobs by policy
- Produce machine-readable results and handoff to reporting

Implementation:
- Runtime: AI agent instructions in Markdown
- Trigger: GitHub Actions + webhook payload
- Execution backends: specialized generator agents + LDRA MCP tool calls + reporting agent

### Specialized Generator Agents (Different by Design)
To avoid one monolithic generator, generation is split across independent agents:

1. function-discovery.agent.md
- Reads changed source files
- Extracts procedures and candidate test targets
- Emits normalized function inventory

2. testdata-generator.agent.md
- Produces normal/boundary/error test data per function
- Defines expected outcomes policy (fixed vs record-first)

3. tcf-assembly.agent.md
- Converts function inventory + test data into LDRA-compatible .tcf
- Enforces naming and directory conventions
- Validates required variable usage blocks before handoff

---

### Person 1: GitHub Integration and Commit Detection
Responsibility: Connect GitHub and trigger LDRA pipeline on local machine.

Approach:
- Self-hosted GitHub runner on local machine
- Local trigger agent endpoint
- No cross-repo dispatch and no external API requirement

Tasks:
- [ ] Install self-hosted GitHub runner on local machine where LDRA is installed
- [ ] Register runner with source repo (Settings -> Actions -> Runners)
- [ ] Start runner in background as service or persistent process
- [ ] Add source repo workflow at .github/workflows/trigger.yml to run on self-hosted runner
- [ ] Workflow sends HTTP POST to http://localhost:8000/trigger with source_repo, commit_sha, branch
- [ ] Add /trigger and /status/{job_id} endpoints in always-running local LDRA server
- [ ] /trigger must enqueue background work and return accepted + job_id
- [ ] /status/{job_id} must return queued/running/success/failed and summary
- [ ] Workflow can poll /status/{job_id} and fail/pass pipeline by status
- [ ] Log trigger requests and job status changes for debugging

Sample trigger request:

POST http://localhost:8000/trigger

{
  "source_repo": "ananthdosskone/sampleCRepo",
  "commit_sha": "abc123def456",
  "branch": "main"
}

Sample response:

{
  "accepted": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}

Deliverables:
- Self-hosted GitHub runner installed and registered
- Source repo workflow .github/workflows/trigger.yml
- /trigger endpoint in local LDRA server
- /status/{job_id} endpoint in local LDRA server

Tech stack: GitHub Actions self-hosted runner, FastAPI or Flask, Python stdlib, Windows service/persistent process

---

### Person 2: C Code Analysis and Test Generation
Responsibility: Analyze C files, extract functions, generate test cases.

Tasks:
- [ ] Use read_c_file() to load source files
- [ ] Use list_procedures() to extract function signatures
- [ ] Analyze input parameters, return values, boundary conditions, and error scenarios
- [ ] Use get_tcf_template() to generate templates
- [ ] Auto-populate TCF files with normal, boundary, and error cases
- [ ] Use write_tcf_file() to save TCF files
- [ ] Pass generated TCF paths to Person 3

Deliverables:
- .github/agents/function-discovery.agent.md
- .github/agents/testdata-generator.agent.md
- .github/agents/tcf-assembly.agent.md
- Generated .tcf test files in TestCases/ directory

Tech stack: AI agents + LDRA MCP tools

---

### Person 3: LDRA Test Execution and Coverage Analysis
Responsibility: Run tests, collect results, and compute coverage.

Tasks:
- [ ] Receive TCF files from Person 2
- [ ] Execute run_static_analysis() when report mode is requested
- [ ] Run tests in record mode: run_tbrun(mode='record')
- [ ] Run tests in regress mode: run_tbrun(mode='regress')
- [ ] Call read_coverage_results() when workarea data is available
- [ ] Parse statement, branch, and MC/DC metrics
- [ ] Implement retry policy for timeout/build/runtime errors
- [ ] Aggregate pass/fail and coverage outputs
- [ ] Generate JSON result payloads

Deliverables:
- src/test_executor.py
- src/coverage_analyzer.py
- results.json

Tech stack: Python subprocess and JSON handling

---

### Person 4: CI/CD Pipeline and Reporting
Responsibility: Orchestrate full flow and publish results to GitHub.

Tasks:
- [ ] Create .github/workflows/ldra-tests.yml
- [ ] Trigger on push and drive Person 1 -> Person 2 -> Person 3 -> Person 4 flow
- [ ] Generate Markdown summary report
- [ ] Post PR comment with pass/fail and coverage
- [ ] Set status checks
- [ ] Upload logs/results as artifacts
- [ ] Optionally add coverage badge and threshold gate

Deliverables:
- .github/workflows/ldra-tests.yml
- .github/agents/reporting.agent.md

Tech stack: GitHub Actions + GitHub API

---

## Data Flow Architecture

┌─────────────────────────────────────────────────────────────┐
│              Source Repo GitHub Push Event                 │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  GitHub Actions on self-hosted │
        │  ├─ Detect push                │
        │  ├─ Extract repo + commit SHA  │
        │  └─ HTTP POST to localhost     │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 1: Trigger Agent       │
        │  ├─ POST /trigger endpoint     │
        │  ├─ Create job_id              │
        │  ├─ Enqueue background work    │
        │  └─ Return {accepted, job_id}  │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 2: Test Generation     │
        │  ├─ Pull source repo commit    │
        │  ├─ Analyze C functions        │
        │  ├─ Generate TCF templates     │
        │  ├─ Populate test cases        │
        │  └─ Write .tcf files           │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 3: Test Execution      │
        │  ├─ Run LDRA static analysis   │
        │  ├─ Execute tests (record)     │
        │  ├─ Execute tests (regress)    │
        │  ├─ Collect coverage           │
        │  └─ Generate results.json      │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 4: Reporting           │
        │  ├─ Generate report            │
        │  ├─ Post PR comment            │
        │  ├─ Set PR status              │
        │  └─ Upload artifacts           │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  GitHub: Display Results       │
        │  ├─ PR comments                │
        │  ├─ Status checks              │
        │  └─ Artifacts/logs             │
        └─────────────────────────────────┘

---

## File Structure

Source repo (example: sampleCRepo):
- .github/workflows/trigger.yml

LDRA_Agent (always-running local repo):
- server.py (local server with /trigger and /status)
- src/test_executor.py
- src/coverage_analyzer.py
- .github/agents/ldra-orchestrator.agent.md
- .github/agents/function-discovery.agent.md
- .github/agents/testdata-generator.agent.md
- .github/agents/tcf-assembly.agent.md
- .github/agents/reporting.agent.md
- TestCases/
- HACKATHON_PLAN.md

---

## Integration Points

GitHub workflow to local trigger:

POST http://localhost:8000/trigger

{
  "source_repo": "ananthdosskone/sampleCRepo",
  "commit_sha": "abc123def456",
  "branch": "main"
}

Response:

{
  "accepted": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}

Person 1 to Person 2 queued payload:

{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_repo": "ananthdosskone/sampleCRepo",
  "commit_sha": "abc123def456",
  "branch": "main",
  "status": "queued"
}

Person 2 to Person 3 payload:

{
  "tcf_files": [
    "TestCases/file1_test.tcf",
    "TestCases/file2_test.tcf"
  ],
  "project_tcf": "C:\\LDRA_Workarea\\project.tcf"
}

Person 3 to Person 4 payload:

{
  "total_tests": 24,
  "passed": 22,
  "failed": 2,
  "coverage": {
    "statement": 92.5,
    "branch": 87.3,
    "mcdc": 78.2
  },
  "failures": [
    {"file": "file1.c", "function": "func_x", "reason": "..."}
  ]
}

---

## Development Timeline

Phase 1 (Days 1-2):
- Person 1 trigger setup
- Person 2 generator agents
- Person 3 executor smoke runs
- Person 4 report skeleton

Phase 2 (Days 2-3):
- Integrate complete chain
- Validate with sample repos

Phase 3 (Day 3):
- Hardening and retries
- Final workflow polish
- Demo prep and documentation

---

## Success Criteria

- Detects new commits from source repos
- Auto-generates and runs LDRA tests
- Reports coverage metrics
- Posts results to PR comments
- Sets PR status (pass/fail)
- Handles errors gracefully
- End-to-end workflow runs without manual intervention

---

## Dependencies

- Python 3.8+
- GitHub Actions with self-hosted runner
- LDRA Toolsuite installed locally
- FastAPI or Flask for local trigger endpoints
- Git for pulling source commits in local pipeline

---

## Getting Started

1. Clone this repo
2. Assign task ownership for Persons 1-4
3. Create branches: feature/person1-commit-detection, etc.
4. Add source workflow .github/workflows/trigger.yml in each source repo
5. Start local LDRA server and runner
6. Test with sample C changes first, then full repo flows

---

## Bonus Task: contextLens Unit Test Report Hover Integration

Goal:
- Extend contextLens VS Code extension to show LDRA unit test context in hover cards.

What contextLens currently does:
- GitBlameProvider: runs git blame --porcelain and caches per-line blame metadata
- InlineDecorationProvider: renders end-of-line italic annotations for active cursor line
- ContextLensHoverProvider: assembles markdown card with Git Blame and optional Why Context from .why files
- WhyContextLoader: indexes .why JSON files into in-memory map by commit hash and file path
- WhyFileWatcher: watches .why directory and triggers index rebuild
- models.ts currently defines BlameInfo, WhyFile, FileChange, WhyContext, WhyContextIndex

Tasks:
- [ ] Define TestReportContext model in models.ts
  - Add interface:
    TestReportContext {
      functionName: string;
      passCount: number;
      failCount: number;
      statementCoverage: number;
      branchCoverage: number;
      mcdcCoverage?: number;
      lastRunDate: string;
    }
  - Add type TestReportIndex = Map<string, TestReportContext> keyed by normalized file path + function name

- [ ] Build TestReportLoader in src/testReportLoader.ts
  - Watch results.json generated by LDRA pipeline
  - Parse JSON into TestReportIndex in memory
  - Expose getContext(filePath: string, functionName: string): TestReportContext | null
  - Rebuild index on file changes (same pattern as WhyContextLoader)

- [ ] Extend hover rendering in src/hoverProvider.ts
  - Accept TestReportLoader as constructor dependency
  - In provideHover, detect enclosing function for hovered line
  - Append section:
    ### Test Results
    Function: <name>
    Pass/Fail: <p>/<f>
    Coverage: SC=<x> DC=<y> MC/DC=<z>
    Last run: <date>

- [ ] Wire in src/extension.ts
  - Instantiate TestReportLoader with existing providers
  - Pass loader to ContextLensHoverProvider
  - Register FileSystemWatcher for results.json and call buildIndex on changes

- [ ] Add unit tests in test/unit/testReportLoader.test.ts
  - Parse sample results.json
  - Validate getContext for matching and non-matching keys
  - Validate graceful handling of missing/malformed results.json

Deliverables:
- src/testReportLoader.ts
- src/models.ts updates (TestReportContext and TestReportIndex)
- src/hoverProvider.ts updates (Test Results section)
- src/extension.ts updates (loader wiring and watcher)
- test/unit/testReportLoader.test.ts

Data contract (results.json produced by pipeline):

{
  "total_tests": 24,
  "passed": 22,
  "failed": 2,
  "coverage": {
    "statement": 92.5,
    "branch": 87.3,
    "mcdc": 78.2
  },
  "failures": [
    {"file": "file1.c", "function": "func_x", "reason": "..."}
  ]
}

---

## Questions and Support

- Ask in team channel
- Reference LDRA MCP tools in server.py
- Check .github/copilot-instructions.md for testing patterns
