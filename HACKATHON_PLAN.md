# LDRA TBrun Automated Testing Hackathon Plan

## Project Goal
Develop an **end-to-end CI/CD workflow** that automatically scans GitHub commits for C/C++ file changes and runs LDRA TBrun unit tests sequentially. When new files are detected or existing files are modified, the system analyzes the code and generates comprehensive test cases.

---

## Team Structure: 4 People, 1 Team

### Person 1: GitHub Integration & Commit Detection
**Responsibility**: Connect GitHub → trigger LDRA pipeline on local machine

**Approach**: Self-hosted GitHub runner on local machine → local trigger agent endpoint (no cross-repo dispatch, no external API)

**Tasks**:
- [ ] Install self-hosted GitHub runner on local machine where LDRA is installed
- [ ] Register runner with source repo (get config token from repo Settings → Actions → Runners)
- [ ] Start runner in background as Windows service or persistent process
- [ ] In source repo, add `.github/workflows/trigger.yml` workflow that runs on `self-hosted` runner
- [ ] Workflow makes HTTP POST to `http://localhost:8000/trigger` with source_repo, commit_sha, branch
- [ ] Add `/trigger` and `/status/{job_id}` endpoints to always-running LDRA server
- [ ] `/trigger` accepts request, creates job_id, enqueues background work, returns `{accepted: true, job_id}`
- [ ] `/status/{job_id}` returns current status (queued/running/success/failed) with summary
- [ ] Workflow optionally polls `/status/{job_id}` to wait for completion before marking step as pass/fail
- [ ] Log all trigger requests and job status in server logs for debugging

**Key inputs**:
- GitHub Actions workflow context:
  - `github.repository` — source repo name/owner
  - `github.sha` — current commit hash
  - `github.ref_name` — branch name

**Sample trigger request**:
```json
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
```

**Deliverables**:
- Self-hosted GitHub runner installed and registered on local machine
- `.github/workflows/trigger.yml` in source repo — workflow that calls local trigger endpoint
- `/trigger` endpoint in always-running LDRA server
- `/status/{job_id}` endpoint in always-running LDRA server

**Tech Stack**: GitHub Actions (self-hosted runner), FastAPI/Flask, Python stdlib (json, uuid, pathlib), Windows Service or background process

---

### Person 2: C Code Analysis & Test Generation
**Responsibility**: Analyze C files → extract functions → generate test cases

**Tasks**:
- [ ] Use `read_c_file()` to load source files
- [ ] Use `list_procedures()` to extract all function signatures
- [ ] Analyze each function for:
  - Input parameters & types
  - Return values
  - Boundary conditions (min/max, NULL, empty)
  - Error scenarios
- [ ] Use `get_tcf_template()` to generate templates
- [ ] Auto-populate TCF files with test cases:
  - **Normal cases**: typical valid inputs
  - **Boundary cases**: edge values, empty inputs, zero, NULL
  - **Error cases**: invalid inputs, boundary violations
- [ ] Use `write_tcf_file()` to save TCF files
- [ ] Pass TCF paths to Person 3

**Deliverables**:
- `test_case_generator.py` - Core analyzer & TCF generator
- Generated `.tcf` test files in `TestCases/` directory

**Tech Stack**: Python regex/AST parsing, pathlib

---

### Person 3: LDRA Test Execution & Coverage Analysis
**Responsibility**: Run tests → collect results → measure coverage

**Tasks**:
- [ ] Receive TCF files from Person 2
- [ ] Execute `run_static_analysis()` for code instrumentation
- [ ] Run tests in **record mode**: `run_tbrun(mode='record')`
  - Establishes baseline expected values
- [ ] Run tests in **regress mode**: `run_tbrun(mode='regress')`
  - Validates against expected values (catch failures)
- [ ] Call `read_coverage_results()` for each test
- [ ] Parse coverage metrics (Statement, Branch, MC/DC %)
- [ ] Implement error handling & retry logic
  - Handle timeouts (exit code 93)
  - Handle build failures (exit code 84)
  - Handle licensing errors (exit code 103)
- [ ] Aggregate results (pass/fail counts, coverage %)
- [ ] Generate JSON report with results

**Deliverables**:
- `test_executor.py` - LDRA orchestrator & runner
- `coverage_analyzer.py` - Parse & aggregate coverage data
- `results.json` - Test results + coverage report

**Tech Stack**: Python subprocess, JSON handling, error handling

---

### Person 4: CI/CD Pipeline & Reporting
**Responsibility**: Orchestrate full flow → deliver results to GitHub

**Tasks**:
- [ ] Create GitHub Actions workflow (`.github/workflows/ldra-tests.yml`)
  - Trigger on push events
  - Orchestrate: Person 1 → Person 2 → Person 3 → Person 4
- [ ] Generate HTML/Markdown test report
- [ ] Post results as GitHub PR comment with:
  - Test pass/fail summary
  - Coverage percentages
  - Failed test details
- [ ] Set PR status checks (✓ pass / ✗ fail)
- [ ] Upload test logs & reports as GitHub artifacts
- [ ] Create coverage badge (optional)
- [ ] Set thresholds (fail PR if coverage < X%)

**Deliverables**:
- `.github/workflows/ldra-tests.yml` - Main workflow
- `report_generator.py` - Create HTML/JSON reports
- `github_reporter.py` - Post comments & set status

**Tech Stack**: GitHub Actions YAML, Markdown, GitHub API

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Source Repo GitHub Push Event                   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  GitHub Actions on self-hosted  │
        │  ├─ Detect push                 │
        │  ├─ Extract repo + commit SHA   │
        │  └─ HTTP POST to localhost      │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 1: Trigger Agent        │
        │  ├─ POST /trigger endpoint      │
        │  ├─ Create job_id               │
        │  ├─ Enqueue background work     │
        │  └─ Return {accepted, job_id}   │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 2: Test Generation      │
        │  ├─ Pull source repo commit     │
        │  ├─ Analyze C functions         │
        │  ├─ Generate TCF templates      │
        │  ├─ Populate test cases         │
        │  └─ Write .tcf files            │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 3: Test Execution       │
        │  ├─ Run LDRA static analysis    │
        │  ├─ Execute tests (record)      │
        │  ├─ Execute tests (regress)     │
        │  ├─ Collect coverage            │
        │  └─ Generate results.json       │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 4: Reporting            │
        │  ├─ Generate HTML report        │
        │  ├─ Post PR comment             │
        │  ├─ Set PR status               │
        │  └─ Upload artifacts            │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  GitHub: Display Results        │
        │  ├─ PR Comments                 │
        │  ├─ Status Checks (✓/✗)        │
        │  └─ Artifacts/Logs              │
        └─────────────────────────────────┘
```

---

## File Structure

```
Source Repo (e.g., sampleCRepo):
├── .github/
│   └── workflows/
│       └── trigger.yml               # Person 1: Workflow that calls localhost trigger

LDRA_Agent (always running locally):
├── server.py                         # Person 1-4: FastAPI server with /trigger and /status endpoints
├── src/
│   ├── test_case_generator.py        # Person 2: C analyzer & TCF generator
│   ├── test_executor.py              # Person 3: LDRA runner
│   ├── coverage_analyzer.py          # Person 3: Coverage parser
│   ├── report_generator.py           # Person 4: Report creation
│   └── github_reporter.py            # Person 4: GitHub integration
├── server.py                         # LDRA MCP server (existing)
├── TestCases/                        # Auto-generated .tcf files
└── HACKATHON_PLAN.md                # This file
```

---

## Integration Points

### GitHub Workflow → Person 1 Trigger Agent
**Input**: Push event context
```json
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
```

### Person 1 → Person 2
**Enqueued job payload**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_repo": "ananthdosskone/sampleCRepo",
  "commit_sha": "abc123def456",
  "branch": "main",
  "status": "queued"
}
```

### Person 2 → Person 3
**Output**: List of TCF file paths
```json
{
  "tcf_files": [
    "TestCases/file1_test.tcf",
    "TestCases/file2_test.tcf"
  ],
  "project_tcf": "C:\\LDRA_Workarea\\project.tcf"
}
```

### Person 3 → Person 4
**Output**: Test results JSON
```json
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
```

### Person 4 → GitHub
**Output**: PR Comment + Status Check
```
✅ **LDRA Test Report**
- Tests: 22/24 passed
- Coverage: SC=92.5%, DC=87.3%, MC/DC=78.2%
- Failed: file1.c::func_x
```

---

## Development Timeline

**Phase 1: Individual Components (Days 1-2)**
- Person 1: Commit detector working
- Person 2: Test generator for sample .c file
- Person 3: Test executor running on sample TCF
- Person 4: Basic report generation

**Phase 2: Integration (Days 2-3)**
- Hook components together
- Test end-to-end flow manually

**Phase 3: Polish & Deploy (Day 3)**
- Error handling & edge cases
- Performance optimization
- Final GitHub Actions setup
- Documentation

---

## Success Criteria

- ✅ Detects new commits from source repos
- ✅ Auto-generates and runs LDRA tests
- ✅ Reports coverage metrics
- ✅ Posts results to PR comments
- ✅ Sets PR status (pass/fail)
- ✅ Handles errors gracefully
- ✅ End-to-end workflow runs without manual intervention

---

## Dependencies

- Python 3.8+
- GitHub Actions (self-hosted runner)
- LDRA Toolsuite (installed locally)
- FastAPI or Flask for HTTP endpoints
- Git (for cloning source repos in Person 2)

---

## Getting Started

1. Clone the repo
2. Assign tasks to each person
3. Create feature branches: `feature/person1-commit-detection`, etc.
4. In each source repo, add sender workflow `.github/workflows/notify-ldra-agent.yml` (push on any change)
5. Create source-repo secret `LDRA_AGENT_DISPATCH_TOKEN` with rights to dispatch to LDRA_Agent
6. In LDRA_Agent, keep receiver workflow `.github/workflows/trigger.yml` + root `commit_detector.py`
7. Use existing `server.py` (LDRA MCP server) as foundation
8. Meet daily to sync on integration points
9. Test on sample C files first before full pipeline

---

---

## Bonus Task: contextLens — Unit Test Report Hover Integration

**Goal**: Rewrite the `contextLens` VS Code extension to surface unit test context directly in the editor. Instead of (or alongside) `.why/` git-blame reasoning, hover cards will display test coverage and pass/fail results from LDRA TBrun reports, keyed to the source lines being viewed.

### What contextLens currently does
- `GitBlameProvider` — runs `git blame --porcelain` and caches per-line blame metadata
- `InlineDecorationProvider` — renders end-of-line italic annotations (author, age, summary) for the active cursor line
- `ContextLensHoverProvider` — on hover, assembles a markdown card with **Git Blame** and an optional **Why Context** section sourced from `.why/<hash>.json` files
- `WhyContextLoader` — indexes `.why/` JSON files into a `Map<commitHash, Map<filePath, WhyContext>>`
- `WhyFileWatcher` — watches the `.why/` directory and triggers index rebuilds on change
- `models.ts` defines `BlameInfo`, `WhyFile`, `FileChange`, `WhyContext`, `WhyContextIndex`

### Tasks

- [ ] **Define `TestReportContext` model** (`models.ts`)
  - Add interface `TestReportContext { functionName: string; passCount: number; failCount: number; statementCoverage: number; branchCoverage: number; mcdcCoverage?: number; lastRunDate: string; }`
  - Add type `TestReportIndex = Map<string, TestReportContext>` keyed by normalized file path + function name

- [ ] **Build `TestReportLoader`** (`src/testReportLoader.ts`)
  - Watch for `results.json` (generated by Person 3/4 of the LDRA pipeline) in the workspace
  - Parse the JSON into `TestReportIndex` in-memory
  - Expose `getContext(filePath: string, functionName: string): TestReportContext | null`
  - Rebuild index when file changes (mirror `WhyContextLoader` pattern)

- [ ] **Extend hover card rendering** (`hoverProvider.ts`)
  - Accept `TestReportLoader` as an additional constructor dependency
  - In `provideHover`, determine the function name enclosing `position.line` (use VS Code symbol provider or simple regex scan)
  - Append a **Test Results** section to the markdown card:
    ```
    ### 🧪 Test Results
    **Function:** my_func
    **Pass/Fail:** 5 / 1
    **Coverage:** SC=92.5%  DC=87.3%  MC/DC=78.2%
    **Last run:** 2026-05-07
    ```

- [ ] **Wire up in `extension.ts`**
  - Instantiate `TestReportLoader` alongside existing providers
  - Pass it to `ContextLensHoverProvider`
  - Register a `FileSystemWatcher` for `results.json` that calls `testReportLoader.buildIndex()`

- [ ] **Update `models.ts`** — add `TestReportContext` and `TestReportIndex` types

- [ ] **Add unit tests** (`test/unit/testReportLoader.test.ts`)
  - Test parsing of a sample `results.json`
  - Test `getContext` with matching and non-matching keys
  - Test graceful handling of missing or malformed `results.json`

**Deliverables**:
- `src/testReportLoader.ts` — Report parser & index
- Updated `src/models.ts` — New types
- Updated `src/hoverProvider.ts` — Test results section in hover card
- Updated `src/extension.ts` — Wired up loader and watcher
- `test/unit/testReportLoader.test.ts` — Unit tests

**Data contract** (`results.json` produced by pipeline):
```json
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
```

---

## Questions & Support

- Ask in team Slack/chat
- Reference LDRA MCP tools in `server.py`
- Check `.github/copilot-instructions.md` for testing patterns
