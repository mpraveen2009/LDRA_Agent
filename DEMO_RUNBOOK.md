# Demo Runbook (LDRA + Mock Trigger)

## What is Ready
- Real LDRA execution path remains available through MCP tools in server.py.
- Mock HTTP trigger API is available in the same file for fallback demo mode.
- Endpoints:
  - POST http://127.0.0.1:8000/trigger
  - GET http://127.0.0.1:8000/status/{job_id}

## Start Mock Trigger API (Fallback Demo)
Run:

python server.py --run-mock-trigger-api

Expected startup output:
- Mock trigger API listening on http://127.0.0.1:8000
- Endpoints: POST /trigger, GET /status/<job_id>

## Mock Demo Request
PowerShell example:

$payload = @{ source_repo='iex_msc'; commit_sha='demo-sha'; branch='feature/demo' } | ConvertTo-Json
$trigger = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/trigger' -Method Post -Body $payload -ContentType 'application/json'
$job = $trigger.job_id
Invoke-RestMethod -Uri ("http://127.0.0.1:8000/status/" + $job) -Method Get

Note:
- Status transitions based on elapsed time: queued -> running -> completed.

## Real LDRA Demo (Tomorrow)
1. Ensure LDRA license and tools are active.
2. Start MCP mode (standard):

python server.py

3. Use existing agent chain:
- function-discovery -> testdata-generator -> tcf-assembly -> tcf-validator -> ldra-execution -> ldra-report-harvester

4. Execute record/regress against your project and TCFs.
5. Show native LDRA artifacts only for reporting.

## Quick Presentation Flow
1. Show trigger/status API with mock mode first (fast and deterministic).
2. Switch to real LDRA execution flow.
3. Show validator gate before execution.
4. Show final status + LDRA artifact references.
