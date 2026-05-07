import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _load_results(results_path: Path) -> dict:
    if not results_path.exists():
        raise FileNotFoundError(f"results file not found: {results_path}")
    data = json.loads(results_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("results.json must contain a JSON object")
    return data


def _coverage_value(results: dict, key: str) -> float:
    coverage = results.get("coverage", {})
    value = coverage.get(key, 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_markdown(results: dict) -> str:
    total_tests = int(results.get("total_tests", 0) or 0)
    passed = int(results.get("passed", 0) or 0)
    failed = int(results.get("failed", 0) or 0)
    statement = _coverage_value(results, "statement")
    branch = _coverage_value(results, "branch")
    mcdc = _coverage_value(results, "mcdc")
    failures = results.get("failures", [])

    status_icon = "✅" if failed == 0 else "❌"
    lines = [
        f"{status_icon} **LDRA Test Report**",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Tests: {passed}/{total_tests} passed",
        f"- Failed: {failed}",
        f"- Coverage: SC={statement:.1f}% | DC={branch:.1f}% | MC/DC={mcdc:.1f}%",
        "",
    ]

    if failures:
        lines.append("### Failed Test Details")
        for item in failures:
            file_name = item.get("file", "unknown")
            function = item.get("function", "unknown")
            reason = item.get("reason", "no reason provided")
            lines.append(f"- {file_name}::{function} - {reason}")
        lines.append("")
    else:
        lines.append("No failures were reported.")

    return "\n".join(lines) + "\n"


def _build_html(results: dict) -> str:
    total_tests = int(results.get("total_tests", 0) or 0)
    passed = int(results.get("passed", 0) or 0)
    failed = int(results.get("failed", 0) or 0)
    statement = _coverage_value(results, "statement")
    branch = _coverage_value(results, "branch")
    mcdc = _coverage_value(results, "mcdc")
    failures = results.get("failures", [])

    rows = []
    for item in failures:
        rows.append(
            "<tr>"
            f"<td>{item.get('file', 'unknown')}</td>"
            f"<td>{item.get('function', 'unknown')}</td>"
            f"<td>{item.get('reason', 'no reason provided')}</td>"
            "</tr>"
        )

    failure_table = "\n".join(rows) if rows else "<tr><td colspan='3'>No failures</td></tr>"
    status_text = "PASS" if failed == 0 else "FAIL"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>LDRA Test Report</title>
  <style>
    body {{ font-family: Segoe UI, Tahoma, sans-serif; margin: 2rem; color: #222; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .status {{ font-size: 1.1rem; font-weight: 700; color: {'#0a7d27' if failed == 0 else '#b22222'}; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
    th {{ background: #f4f4f4; }}
  </style>
</head>
<body>
  <h1>LDRA Test Report</h1>
  <div class=\"status\">Status: {status_text}</div>
  <p>Generated: {datetime.now(timezone.utc).isoformat()}</p>
  <ul>
    <li>Tests: {passed}/{total_tests} passed</li>
    <li>Failed: {failed}</li>
    <li>Coverage: SC={statement:.1f}% | DC={branch:.1f}% | MC/DC={mcdc:.1f}%</li>
  </ul>
  <h2>Failed Test Details</h2>
  <table>
    <thead>
      <tr><th>File</th><th>Function</th><th>Reason</th></tr>
    </thead>
    <tbody>
      {failure_table}
    </tbody>
  </table>
</body>
</html>
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LDRA markdown/html reports from results.json")
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    results = _load_results(args.results)
    markdown = _build_markdown(results)
    html = _build_html(results)

    _write(args.markdown, markdown)
    _write(args.html, html)
    _write(args.summary, json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
