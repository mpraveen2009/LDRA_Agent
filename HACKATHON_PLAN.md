# LDRA TBrun Automated Testing Hackathon Plan

## Project Goal
Develop an **end-to-end CI/CD workflow** that automatically scans GitHub commits for C/C++ file changes and runs LDRA TBrun unit tests sequentially. When new files are detected or existing files are modified, the system analyzes the code and generates comprehensive test cases.

---

## Team Structure: 4 People, 1 Team

### Person 1: GitHub Integration & Commit Detection
**Responsibility**: Connect GitHub → detect changes → feed to pipeline

**Approach**: GitHub Actions (no webhook server required)

**Tasks**:
- [ ] Write `.github/workflows/trigger.yml` with `on: push` trigger filtered to `**.c` and `**.h` paths
- [ ] Write `commit_detector.py` that reads `GITHUB_EVENT_PATH` env var (Actions-injected event JSON) and extracts added/modified `.c`/`.h` files
- [ ] Output filtered file list + commit hash for Person 2 (via step output or artifact)
- [ ] Log detected changes in workflow output

**Key inputs** (all auto-injected by GitHub Actions — no setup needed):
- `GITHUB_EVENT_PATH` — path to the push event JSON with `commits[].added`, `commits[].modified`
- `GITHUB_SHA` — current commit hash

**Sample `commit_detector.py` entry point**:
```python
import json, os
event = json.load(open(os.environ["GITHUB_EVENT_PATH"]))
changed = [f for c in event["commits"] for f in c["added"] + c["modified"] if f.endswith((".c", ".h"))]
```

**Deliverables**:
- `commit_detector.py` - Event parser & file extractor
- `.github/workflows/trigger.yml` - GitHub Actions workflow (push trigger)

**Tech Stack**: Python stdlib (json, os, pathlib), GitHub Actions YAML

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
│                     GitHub Push Event                        │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 1: Commit Detection     │
        │  ├─ Parse diff                  │
        │  ├─ Identify new/modified .c    │
        │  └─ Queue files                 │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  Person 2: Test Generation      │
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
LDRA_Agent/
├── .github/
│   └── workflows/
│       ├── trigger.yml               # Person 1: Main workflow trigger
│       └── ldra-tests.yml            # Person 4: Full testing workflow
├── src/
│   ├── commit_detector.py            # Person 1: Webhook & parser
│   ├── test_case_generator.py        # Person 2: C analyzer & TCF generator
│   ├── test_executor.py              # Person 3: LDRA runner
│   ├── coverage_analyzer.py          # Person 3: Coverage parser
│   ├── report_generator.py           # Person 4: Report creation
│   └── github_reporter.py            # Person 4: GitHub integration
├── server.py                         # LDRA MCP server (existing)
├── TestCases/                        # Auto-generated .tcf files
├── results.json                      # Test results
├── test_report.html                  # Generated report
└── HACKATHON_PLAN.md                # This file
```

---

## Integration Points

### Person 1 → Person 2
**Output**: List of file paths to analyze
```json
{
  "files": [
    "/path/to/file1.c",
    "/path/to/file2.c"
  ],
  "commit": "abc123def456"
}
```

### Person 2 → Person 3
**Output**: List of TCF file paths
```json
{
  "tcf_files": [
    "/TestCases/file1_test.tcf",
    "/TestCases/file2_test.tcf"
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

- ✅ Detects new/modified C files on GitHub push
- ✅ Auto-generates and runs LDRA tests
- ✅ Reports coverage metrics
- ✅ Posts results to PR comments
- ✅ Sets PR status (pass/fail)
- ✅ Handles errors gracefully
- ✅ End-to-end workflow runs without manual intervention

---

## Dependencies

- Python 3.8+
- GitHub Actions
- LDRA Toolsuite (existing)
- PyGithub
- FastAPI/Flask (for webhook)
- requests library

---

## Getting Started

1. Clone the repo
2. Assign tasks to each person
3. Create feature branches: `feature/person1-commit-detection`, etc.
4. Use existing `server.py` (LDRA MCP server) as foundation
5. Meet daily to sync on integration points
6. Test on sample C files first before full pipeline

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
