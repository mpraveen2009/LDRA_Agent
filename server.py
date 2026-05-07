"""
LDRA TBrun MCP Server
Exposes tools for reading C source files, writing .tcf test cases,
running TBrun, and reading coverage results.
"""

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ── Configuration ────────────────────────────────────────────────────────────
LDRA_INSTALL = Path(r"C:\LDRA_Toolsuite_C_CPP_10.3.0")
LDRA_WORKAREA = Path(r"C:\LDRA_Workarea_C_CPP_10.3.0")
CONTBRUN = LDRA_INSTALL / "Contbrun.exe"
CONTESTBED = LDRA_INSTALL / "Contestbed.exe"
TBINI = LDRA_INSTALL / "TBini.exe"

mcp = FastMCP("ldra-tbrun")

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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
