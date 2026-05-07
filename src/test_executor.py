import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent

if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from coverage_analyzer import extract_coverage_metrics
from server import read_coverage_results, run_static_analysis, run_tbrun


RETRYABLE_EXIT_CODES = {91, 92, 93}
PROC_RE = re.compile(r"^\s*Procedure\s*=\s*(\w+)\s*$", re.MULTILINE)


def discover_tcf_files(test_dir: Path) -> List[Path]:
    return sorted(test_dir.rglob("*.tcf"))


def _should_retry(exit_code: int) -> bool:
    return exit_code in RETRYABLE_EXIT_CODES


def run_single_test(project_tcf: str, test_tcf: str, retries: int = 1) -> Dict:
    attempts = 0
    last = None
    while attempts <= retries:
        attempts += 1
        last = run_tbrun(project_tcf=project_tcf, test_tcf=test_tcf, mode="regress")
        exit_code = last.get("exit_code")
        if exit_code == 0:
            break
        if attempts > retries:
            break
        if not _should_retry(exit_code):
            break
    last["attempts"] = attempts
    last["retryable"] = _should_retry(last.get("exit_code"))
    last["test_tcf"] = test_tcf
    return last


def _extract_procedures_from_tcf(test_tcf: str) -> List[str]:
    path = Path(test_tcf)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    seen = []
    for match in PROC_RE.finditer(text):
        proc = match.group(1)
        if proc not in seen:
            seen.append(proc)
    return seen


def _build_function_contexts(regress_results: List[Dict], coverage: Dict[str, float]) -> List[Dict]:
    function_stats: Dict[str, Dict[str, int]] = {}
    for result in regress_results:
        procedures = _extract_procedures_from_tcf(result.get("test_tcf", ""))
        if not procedures:
            continue
        failed = result.get("exit_code") != 0
        for proc in procedures:
            bucket = function_stats.setdefault(proc, {"pass": 0, "fail": 0})
            if failed:
                bucket["fail"] += 1
            else:
                bucket["pass"] += 1

    contexts = []
    for function_name, stats in sorted(function_stats.items()):
        contexts.append(
            {
                "functionName": function_name,
                "passCount": stats["pass"],
                "failCount": stats["fail"],
                "statementCoverage": coverage.get("statement", 0.0),
                "branchCoverage": coverage.get("branch", 0.0),
                "mcdcCoverage": coverage.get("mcdc"),
            }
        )
    return contexts


def run_pipeline(
    project_tcf: str,
    test_dir: str,
    project_name: str,
    do_record: bool,
    retries: int,
    single_tcf: str | None,
    unit_only: bool,
) -> Dict:
    if single_tcf:
        tcf_path = Path(single_tcf)
        if not tcf_path.exists():
            raise FileNotFoundError(f"Single TCF file not found: {single_tcf}")
        tcf_paths = [tcf_path]
    else:
        tcf_paths = discover_tcf_files(Path(test_dir))
        if not tcf_paths:
            raise FileNotFoundError(f"No .tcf files found under: {test_dir}")

    static_result = {
        "skipped": unit_only,
        "reason": "Unit-test-only mode" if unit_only else None,
    }
    if not unit_only:
        static_result = run_static_analysis(project_tcf)
        static_ok = static_result.get("exit_code") == 0

        if not static_ok:
            return {
                "project_tcf": project_tcf,
                "test_dir": test_dir,
                "project_name": project_name,
                "static_analysis": static_result,
                "record_results": [],
                "regress_results": [],
                "summary": {
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": True,
                    "reason": "Static analysis/instrumentation failed; regress stage skipped.",
                },
                "coverage": {},
                "coverage_raw_excerpt": "",
            }

    record_results = []
    if do_record:
        for tcf in tcf_paths:
            rec = run_tbrun(project_tcf=project_tcf, test_tcf=str(tcf), mode="record")
            rec["test_tcf"] = str(tcf)
            record_results.append(rec)

    regress_results = [run_single_test(project_tcf, str(tcf), retries=retries) for tcf in tcf_paths]

    passed = sum(1 for r in regress_results if r.get("exit_code") == 0)
    failed = len(regress_results) - passed

    coverage_raw = read_coverage_results(project_name)
    coverage = extract_coverage_metrics(coverage_raw)
    function_contexts = _build_function_contexts(regress_results, coverage)

    return {
        "project_tcf": project_tcf,
        "test_dir": test_dir,
        "project_name": project_name,
        "static_analysis": static_result,
        "record_results": record_results,
        "regress_results": regress_results,
        "summary": {
            "total_tests": len(regress_results),
            "passed": passed,
            "failed": failed,
        },
        "coverage": coverage,
        "function_contexts": function_contexts,
        "coverage_raw_excerpt": "\n".join(coverage_raw.splitlines()[:80]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LDRA TBrun tests sequentially for all TCF files.")
    parser.add_argument("--project-tcf", required=True, help="Absolute path to project .tcf")
    parser.add_argument("--test-dir", required=True, help="Directory containing unit test .tcf files")
    parser.add_argument("--project-name", required=True, help="LDRA project name for coverage lookup")
    parser.add_argument("--record-first", action="store_true", help="Run record mode before regress mode")
    parser.add_argument("--unit-only", action="store_true", help="Skip static analysis and run unit tests only")
    parser.add_argument("--retries", type=int, default=1, help="Retries per regress test on failure")
    parser.add_argument("--single-tcf", help="Run only one .tcf file (smoke/debug mode)")
    parser.add_argument("--output", default="results.json", help="Output JSON file path")
    args = parser.parse_args()

    results = run_pipeline(
        project_tcf=args.project_tcf,
        test_dir=args.test_dir,
        project_name=args.project_name,
        do_record=args.record_first,
        retries=max(args.retries, 0),
        single_tcf=args.single_tcf,
        unit_only=args.unit_only,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote results to {out}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
