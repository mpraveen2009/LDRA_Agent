"""
LDRA TBrun MCP Server
Exposes tools for reading C source files, writing .tcf test cases,
running TBrun, and reading coverage results.
"""

import os
import re
import json
import uuid
import time
import subprocess
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    FastMCP = None

# ── Configuration ────────────────────────────────────────────────────────────
LDRA_INSTALL = Path(r"C:\LDRA_Toolsuite_C_CPP_10.3.0")
LDRA_WORKAREA = Path(r"C:\LDRA_Workarea_C_CPP_10.3.0")
CONTBRUN = LDRA_INSTALL / "Contbrun.exe"
CONTESTBED = LDRA_INSTALL / "Contestbed.exe"
TBINI = LDRA_INSTALL / "TBini.exe"
MOCK_DB = Path(__file__).with_name(".mock_trigger_jobs.json")

if FastMCP is not None:
    mcp = FastMCP("ldra-tbrun")
else:
    class _NoopMCP:
        @staticmethod
        def tool():
            def _decorator(func):
                return func
            return _decorator

        @staticmethod
        def run(transport: str = "stdio"):
            raise RuntimeError("mcp package is not installed; MCP transport is unavailable")

    mcp = _NoopMCP()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_ldra(args: list[str], timeout: int = 120) -> tuple[int, str]:
    """Run an LDRA console tool via cmd /c start /wait /min and return (exit_code, stderr)."""
    cmd = ["cmd", "/c", "start", "/wait", "/min"] + args
    result = subprocess.run(
        cmd,
        cwd=str(LDRA_WORKAREA),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stderr


def _exit_code_meaning(code: int) -> str:
    meanings = {
        0:  "Pass",
        64: "Invalid command line",
        65: "Input data incorrect",
        70: "Internal software limitation",
        73: "Cannot create output file or directory",
        80: "Main static analysis phase incomplete",
        81: "Instrumentation failed",
        82: "Dynamic coverage failed",
        83: "Other analysis failed",
        84: "Build failed",
        85: "Execution of instrumented program failed",
        90: "Regression failure",
        91: "Build failure",
        92: "Failed to execute",
        93: "Execution timed out",
        103: "Licensing error",
    }
    return meanings.get(code, f"Unknown exit code {code}")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_mock_jobs() -> dict[str, dict]:
    if not MOCK_DB.exists():
        return {}
    try:
        return json.loads(MOCK_DB.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_mock_jobs(jobs: dict[str, dict]) -> None:
    MOCK_DB.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def _create_mock_job(source_repo: str, commit_sha: str, branch: str) -> dict:
    jobs = _load_mock_jobs()
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "accepted": True,
        "mode": "mock",
        "source_repo": source_repo,
        "commit_sha": commit_sha,
        "branch": branch,
        "status": "queued",
        "created_at": _utc_now_iso(),
        "created_at_epoch": time.time(),
        "updated_at": _utc_now_iso(),
        "summary": None,
    }
    jobs[job_id] = job
    _save_mock_jobs(jobs)
    return job


def _get_mock_job(job_id: str) -> dict | None:
    return _load_mock_jobs().get(job_id)


def _refresh_mock_job(job_id: str) -> dict | None:
    jobs = _load_mock_jobs()
    job = jobs.get(job_id)
    if not job:
        return None

    if job.get("status") == "completed":
        return job

    age = time.time() - float(job.get("created_at_epoch", time.time()))
    if age >= 2.0:
        job["status"] = "completed"
        job["summary"] = {
            "total_tests": 3,
            "passed": 3,
            "failed": 0,
            "note": "Mock pipeline result for demo without active LDRA runtime",
        }
    elif age >= 1.0:
        job["status"] = "running"

    job["updated_at"] = _utc_now_iso()
    jobs[job_id] = job
    _save_mock_jobs(jobs)
    return job


def _make_mock_handler():
    class MockTriggerHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/trigger":
                self._send_json(404, {"error": "not_found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid_json"})
                return

            source_repo = str(data.get("source_repo", "unknown"))
            commit_sha = str(data.get("commit_sha", "unknown"))
            branch = str(data.get("branch", "unknown"))

            job = _create_mock_job(source_repo, commit_sha, branch)
            self._send_json(202, {"accepted": True, "job_id": job["job_id"], "status": "queued"})

        def do_GET(self):
            if not self.path.startswith("/status/"):
                self._send_json(404, {"error": "not_found"})
                return

            job_id = self.path.rsplit("/", 1)[-1]
            job = _refresh_mock_job(job_id)
            if not job:
                self._send_json(404, {"error": "job_not_found", "job_id": job_id})
                return

            self._send_json(200, job)

        def log_message(self, _format, *_args):
            return

    return MockTriggerHandler


def run_mock_trigger_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), _make_mock_handler())
    print(f"Mock trigger API listening on http://{host}:{port}")
    print("Endpoints: POST /trigger, GET /status/<job_id>")
    server.serve_forever()


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def read_c_file(file_path: str) -> str:
    """Read the contents of a C or C++ source file.

    Args:
        file_path: Absolute path to the .c / .cpp / .h file.
    Returns:
        File content as a string.
    """
    path = Path(file_path)
    if not path.exists():
        return f"ERROR: File not found: {file_path}"
    if path.suffix.lower() not in (".c", ".cpp", ".h", ".hpp"):
        return f"ERROR: Not a C/C++ file: {file_path}"
    return path.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def list_procedures(file_path: str) -> str:
    """List all function/procedure names found in a C source file.

    Uses a simple regex — good enough for finding top-level functions.
    Args:
        file_path: Absolute path to the .c / .h file.
    Returns:
        Newline-separated list of procedure names.
    """
    path = Path(file_path)
    if not path.exists():
        return f"ERROR: File not found: {file_path}"
    src = path.read_text(encoding="utf-8", errors="replace")
    # Match C function definitions: return_type name(
    pattern = re.compile(
        r"^[\w\s\*]+\b(\w+)\s*\([^;]*\)\s*\{",
        re.MULTILINE,
    )
    names = [m.group(1) for m in pattern.finditer(src)
             if m.group(1) not in ("if", "while", "for", "switch")]
    return "\n".join(names) if names else "No functions found."


@mcp.tool()
def read_tcf_file(tcf_path: str) -> str:
    """Read an existing TBrun .tcf test case file.

    Args:
        tcf_path: Absolute path to the .tcf file.
    Returns:
        File content as a string.
    """
    path = Path(tcf_path)
    if not path.exists():
        return f"ERROR: File not found: {tcf_path}"
    return path.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def write_tcf_file(tcf_path: str, content: str) -> str:
    """Write (create or overwrite) a TBrun .tcf test case file.

    Args:
        tcf_path: Absolute path where the .tcf should be written.
        content:  Full .tcf file content.
    Returns:
        Confirmation message or error.
    """
    path = Path(tcf_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written: {tcf_path}"
    except OSError as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def get_tcf_template(
    source_file: str,
    procedure_name: str,
    sequence_name: str = "",
) -> str:
    """Generate a minimal TBrun .tcf template for a given procedure.

    The template contains one empty test case skeleton.  The agent should
    fill in the Variable sections with actual input/expected values.

    Args:
        source_file:    Absolute path to the C source file.
        procedure_name: Name of the C function to test.
        sequence_name:  Optional sequence name (defaults to <procedure>_Seq).
    Returns:
        TCF template as a string ready to be edited and saved.
    """
    seq = sequence_name or f"{procedure_name}_Seq"
    rel = Path(source_file).name
    from datetime import datetime
    now = datetime.now().strftime("%b %d %Y %H:%M:%S")

    return f"""\
 # Begin Testbed Set

 SINGLE_FILE = TRUE
 GENERATED_BY = LDRA MCP Agent

    # Begin Source Files

    RelativeFile = .\\{rel}

    # End Source Files

 # End Testbed Set

    # Begin Attributes

      Sequence Name = {seq}
      Language Code = 2

    # End Attributes

    # Begin Test Case

      File = {source_file}
      Procedure = {procedure_name}
      Procedure Number = 1
      Creation Date = {now}

        # Begin Variable
          Name = <param_name>
          Decl_type = <type>
          Usage = I
          Value = <value>
        # End Variable

        # Begin Variable
          Name = <return_var>
          Decl_type = <return_type>
          Usage = O
          Value = <expected_value>
        # End Variable

    # End Test Case
"""


@mcp.tool()
def run_tbrun(project_tcf: str, test_tcf: str, mode: str = "regress") -> dict:
    """Run TBrun with a test case file and return the result.

    Args:
        project_tcf: Absolute path to the project .tcf file (the set file).
        test_tcf:    Absolute path to the unit test .tcf file.
        mode:        'regress' to compare against expected values (default),
                     'record'  to record new expected values.
    Returns:
        dict with keys: exit_code, status, meaning.
    """
    tcf_mode = "retain" if mode == "regress" else "update"
    args = [
        str(CONTBRUN),
        project_tcf,
        f"-tcf={test_tcf}",
        f"-tcf_mode={tcf_mode}",
        "-regress" if mode == "regress" else "-record",
        "-quit",
    ]
    try:
        code, stderr = _run_ldra(args, timeout=180)
    except subprocess.TimeoutExpired:
        return {"exit_code": 93, "status": "timeout", "meaning": "Execution timed out"}

    return {
        "exit_code": code,
        "status": "pass" if code == 0 else "fail",
        "meaning": _exit_code_meaning(code),
        "stderr": stderr.strip() if stderr.strip() else None,
    }


@mcp.tool()
def run_static_analysis(project_tcf: str) -> dict:
    """Run LDRA static analysis and instrumentation on a project.

    Args:
        project_tcf: Absolute path to the project .tcf file.
    Returns:
        dict with keys: exit_code, status, meaning.
    """
    # /112 = static analysis, /0212 = instrumentation, /q = quit
    args = [str(CONTESTBED), project_tcf, "/1120212", "/q"]
    try:
        code, stderr = _run_ldra(args, timeout=300)
    except subprocess.TimeoutExpired:
        return {"exit_code": 93, "status": "timeout", "meaning": "Timed out"}

    return {
        "exit_code": code,
        "status": "pass" if code == 0 else "fail",
        "meaning": _exit_code_meaning(code),
    }


@mcp.tool()
def read_coverage_results(project_name: str) -> str:
    """Read the latest dynamic coverage summary for a project from the workarea.

    Looks for .exh (execution history) files in the workarea and parses coverage %.
    Args:
        project_name: Name used by LDRA for the project set (e.g. 'Cashregister').
    Returns:
        Coverage summary as text, or a message if no results found.
    """
    tbwrk = LDRA_WORKAREA / f"{project_name}_tbwrkfls"
    if not tbwrk.exists():
        return f"No workarea found for project '{project_name}' at {tbwrk}"

    # Look for .exh files (execution history)
    exh_files = list(tbwrk.rglob("*.exh"))
    if not exh_files:
        return f"No coverage results (.exh) found in {tbwrk}"

    lines = []
    for exh in exh_files[:20]:  # cap at 20 files
        lines.append(f"--- {exh.name} ---")
        try:
            content = exh.read_text(encoding="utf-8", errors="replace")
            # Show first 40 lines of each file
            lines.extend(content.splitlines()[:40])
        except OSError as exc:
            lines.append(f"  (could not read: {exc})")
    return "\n".join(lines)


@mcp.tool()
def list_tcf_files(directory: str) -> str:
    """List all .tcf files in a directory.

    Args:
        directory: Absolute path to search for .tcf files.
    Returns:
        Newline-separated list of absolute paths.
    """
    d = Path(directory)
    if not d.exists():
        return f"ERROR: Directory not found: {directory}"
    files = sorted(d.rglob("*.tcf"))
    if not files:
        return "No .tcf files found."
    return "\n".join(str(f) for f in files)


@mcp.tool()
def set_tbini(key: str, value: str, section: str = "") -> str:
    """Set a TBini configuration value (testbed.ini flag).

    Args:
        key:     The ini flag name (e.g. COMPILER_SELECTED).
        value:   The value to set.
        section: Optional section prefix (e.g. 'C/C++ MinGW200 GCC C/C++ v3.2 LDRA Testbed').
    Returns:
        Confirmation or error message.
    """
    if section:
        args = [str(TBINI), f'/Section="{section}"', f'{key}="{value}"']
    else:
        args = [str(TBINI), f'{key}="{value}"']

    try:
        code, stderr = _run_ldra(args, timeout=30)
        if code == 0:
            return f"Set {key}={value}"
        return f"ERROR (exit {code}): {stderr}"
    except subprocess.TimeoutExpired:
        return "ERROR: TBini timed out"


@mcp.tool()
def mock_trigger(source_repo: str, commit_sha: str, branch: str) -> dict:
    """Create a mock trigger job for demo flows without active LDRA runtime."""
    job = _create_mock_job(source_repo, commit_sha, branch)
    return {"accepted": True, "job_id": job["job_id"], "status": "queued"}


@mcp.tool()
def mock_status(job_id: str) -> dict:
    """Get status for a mock trigger job."""
    job = _refresh_mock_job(job_id)
    if not job:
        return {"error": "job_not_found", "job_id": job_id}
    return job


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LDRA TBrun MCP Server")
    parser.add_argument("--run-mock-trigger-api", action="store_true", help="Run demo HTTP trigger API")
    parser.add_argument("--host", default="127.0.0.1", help="Host for mock trigger API")
    parser.add_argument("--port", type=int, default=8000, help="Port for mock trigger API")
    args = parser.parse_args()

    if args.run_mock_trigger_api:
        run_mock_trigger_api(host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
