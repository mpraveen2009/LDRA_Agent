"""Generate LDRA TBrun .tcf test cases from C source files.

Person 2 deliverable:
- Analyze C files
- Extract procedures
- Build normal/boundary/error cases
- Write one .tcf file per C source under TestCases/
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Allow running this file directly while importing server.py from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server import get_tcf_template, list_procedures, read_c_file, write_tcf_file


@dataclass
class Parameter:
    name: str
    decl_type: str
    is_pointer: bool


def parse_procedure_names(file_path: Path) -> list[str]:
    """Use MCP list_procedures and normalize output."""
    raw = list_procedures(str(file_path))
    if raw.startswith("ERROR") or raw.strip() == "No functions found.":
        return []
    return [name.strip() for name in raw.splitlines() if name.strip()]


def parse_signature(source: str, procedure_name: str) -> tuple[str, list[Parameter]]:
    """Return (return_type, parameters) for a procedure if found."""
    pattern = re.compile(
        rf"(?P<ret>[\w\s\*]+?)\b{re.escape(procedure_name)}\s*\((?P<params>.*?)\)\s*\{{",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        return "int", []

    ret_type = " ".join(match.group("ret").split())
    params = match.group("params").strip()
    if not params or params == "void":
        return ret_type, []

    parsed: list[Parameter] = []
    for part in params.split(","):
        token = " ".join(part.strip().split())
        if not token:
            continue
        m = re.match(r"(?P<type>[\w\s]+?)(?P<ptr>\*+)?\s*(?P<name>\w+)$", token)
        if not m:
            continue
        base_type = " ".join(m.group("type").split())
        ptr = m.group("ptr") or ""
        decl = f"{base_type} {ptr}".strip()
        parsed.append(Parameter(name=m.group("name"), decl_type=decl, is_pointer=bool(ptr)))

    return ret_type, parsed


def sample_value(param: Parameter, profile: str) -> str:
    """Generate simple sample values by parameter type and case profile."""
    low_type = param.decl_type.lower()

    if "float" in low_type or "double" in low_type:
        if profile == "boundary":
            return "0.0"
        if profile == "error":
            return "-1.0"
        return "1.5"

    if any(x in low_type for x in ("int", "short", "long", "size_t", "uint")):
        if profile == "boundary":
            return "2147483647"
        if profile == "error":
            return "-1"
        return "1"

    if "char" in low_type and param.is_pointer:
        if profile == "boundary":
            return '""'
        if profile == "error":
            return "NULL"
        return '"abc"'

    if param.is_pointer:
        return "NULL" if profile == "error" else "1"

    return "0"


def variable_block(name: str, decl_type: str, usage: str, value: str) -> str:
    return (
        "        # Begin Variable\n"
        f"          Name = {name}\n"
        f"          Decl_type = {decl_type}\n"
        f"          Usage = {usage}\n"
        f"          Value = {value}\n"
        "        # End Variable\n"
    )


def build_test_case(
    source_file: Path,
    procedure_name: str,
    procedure_number: int,
    return_type: str,
    parameters: list[Parameter],
    profile: str,
) -> str:
    now = datetime.now().strftime("%b %d %Y %H:%M:%S")
    lines = [
        "    # Begin Test Case",
        "",
        f"      File = {source_file}",
        f"      Procedure = {procedure_name}",
        f"      Procedure Number = {procedure_number}",
        f"      Creation Date = {now}",
        "",
    ]

    for p in parameters:
        value = sample_value(p, profile)
        if p.is_pointer and value != "NULL":
            helper_name = f"{p.name}_map"
            lines.append(variable_block(helper_name, p.decl_type.replace("*", "").strip() or "int", "H", value))
            lines.append(variable_block(p.name, p.decl_type, "P", helper_name))
            continue
        if p.is_pointer and value == "NULL":
            lines.append(variable_block(p.name, p.decl_type, "P", "NULL"))
            continue
        lines.append(variable_block(p.name, p.decl_type, "I", value))

    if return_type.strip() != "void":
        expected = "-1" if profile == "error" else "0"
        lines.append(variable_block("expected_return", return_type, "O", expected))

    lines.append("    # End Test Case")
    return "\n".join(lines)


def build_tcf_header(source_file: Path, procedure_name: str) -> str:
    """Extract the shared TCF header using a valid procedure template."""
    template = get_tcf_template(str(source_file), procedure_name)
    marker = "    # Begin Test Case"
    header = template.split(marker)[0] if marker in template else template

    return header.rstrip()


def build_procedure_cases(
    source_file: Path,
    procedure_name: str,
    procedure_number: int,
    return_type: str,
    parameters: list[Parameter],
) -> str:
    """Build normal, boundary, and error cases for one procedure."""

    profiles = ["normal", "boundary", "error"]
    cases = [
        build_test_case(
            source_file=source_file,
            procedure_name=procedure_name,
            procedure_number=procedure_number,
            return_type=return_type,
            parameters=parameters,
            profile=profile,
        )
        for profile in profiles
    ]
    return "\n\n".join(cases)


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "unnamed"


def _find_repo_root(path: Path) -> Path:
    """Walk up from path until a .git directory is found; fall back to path's root."""
    candidate = path.resolve()
    while True:
        if (candidate / ".git").exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            # filesystem root — no .git found, return the original directory
            return path.resolve().parent
        candidate = parent


def _resolve_output_path(source_file: Path) -> Path:
    """Compute <repo_root>/LDRA/Unit Testing/<stem>_test.tcf."""
    source_file = source_file.resolve()
    repo_root = _find_repo_root(source_file)
    out_dir = repo_root / "LDRA" / "Unit Testing"
    return out_dir / f"{source_file.stem}_test.tcf"


def generate_for_file(source_file: Path) -> list[Path]:
    """Generate one TCF per C source file and return its path."""
    raw_source = read_c_file(str(source_file))
    if raw_source.startswith("ERROR"):
        raise RuntimeError(raw_source)

    procedures = parse_procedure_names(source_file)
    if not procedures:
        return []

    header = build_tcf_header(source_file, procedures[0])
    body_cases: list[str] = []

    for i, procedure in enumerate(procedures, start=1):
        return_type, params = parse_signature(raw_source, procedure)
        body_cases.append(
            build_procedure_cases(
                source_file=source_file,
                procedure_name=procedure,
                procedure_number=i,
                return_type=return_type,
                parameters=params,
            )
        )

    content = header + "\n\n" + "\n\n".join(body_cases) + "\n"
    out_path = _resolve_output_path(source_file)
    result = write_tcf_file(str(out_path), content)
    if result.startswith("ERROR"):
        raise RuntimeError(result)
    return [out_path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate LDRA .tcf test files from C source files.\n"
            "Output is written to <source_repo_root>/LDRA/Unit Testing/<stem>_test.tcf"
        )
    )
    parser.add_argument("files", nargs="+", help="C source files to analyze")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    generated: list[Path] = []
    for file_arg in args.files:
        source = Path(file_arg).resolve()
        if not source.exists():
            print(f"SKIP: file not found: {source}")
            continue
        if source.suffix.lower() != ".c":
            print(f"SKIP: not a .c source file: {source}")
            continue
        try:
            generated.extend(generate_for_file(source))
        except RuntimeError as exc:
            print(f"ERROR: {source}: {exc}")

    print("Generated TCF files:")
    for path in generated:
        print(f"- {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
