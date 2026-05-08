import argparse
import json
import os
from pathlib import Path

import requests


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _coverage(results: dict, key: str) -> float:
    value = results.get("coverage", {}).get(key, 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_state(results: dict, threshold: float) -> tuple[str, str, bool]:
    failed = int(results.get("failed", 0) or 0)
    statement = _coverage(results, "statement")
    success = failed == 0 and statement >= threshold
    if success:
        desc = f"All tests passed and SC {statement:.1f}% >= {threshold:.1f}%"
        return "success", desc, True
    desc = f"Failures={failed}, SC={statement:.1f}% (threshold {threshold:.1f}%)"
    return "failure", desc, False


def _api_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _post_pr_comment(token: str, repository: str, pr_number: int, body: str) -> None:
    url = f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments"
    response = requests.post(url, headers=_api_headers(token), json={"body": body}, timeout=30)
    response.raise_for_status()


def _set_commit_status(token: str, repository: str, sha: str, state: str, description: str, run_url: str) -> None:
    url = f"https://api.github.com/repos/{repository}/statuses/{sha}"
    payload = {
        "state": state,
        "context": "LDRA/Tests",
        "description": description[:140],
        "target_url": run_url,
    }
    response = requests.post(url, headers=_api_headers(token), json=payload, timeout=30)
    response.raise_for_status()


def _read_pr_number_from_event() -> int | None:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    data = _load_json(Path(event_path))
    pull_request = data.get("pull_request")
    if not pull_request:
        return None
    number = pull_request.get("number")
    return int(number) if number is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Post LDRA report and set GitHub status")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--coverage-threshold", required=True, type=float)
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    sha = os.getenv("GITHUB_SHA", "")
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.getenv("GITHUB_RUN_ID", "")

    if not token or not repository or not sha:
        raise RuntimeError("Missing required GitHub environment values")

    results = _load_json(args.results)
    report_body = args.report.read_text(encoding="utf-8")

    state, description, success = _build_state(results, args.coverage_threshold)
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id else f"{server_url}/{repository}"

    _set_commit_status(token, repository, sha, state, description, run_url)

    pr_number = _read_pr_number_from_event()
    if pr_number is not None:
        _post_pr_comment(token, repository, pr_number, report_body)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
