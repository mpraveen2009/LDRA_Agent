import re
from typing import Dict, List


PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")


def extract_coverage_metrics(raw_text: str) -> Dict[str, float]:
    """Extract coarse coverage metrics from LDRA coverage text output.

    This parser is intentionally tolerant because .exh content can vary across
    LDRA versions and project configurations.
    """
    lower = raw_text.lower()
    metrics = {
        "statement": _find_named_metric(lower, raw_text, ["statement", "sc"]),
        "branch": _find_named_metric(lower, raw_text, ["branch", "dc"]),
        "mcdc": _find_named_metric(lower, raw_text, ["mcdc", "mc/dc"]),
    }
    return {k: v for k, v in metrics.items() if v is not None}


def _find_named_metric(lower_text: str, original_text: str, keys: List[str]):
    for key in keys:
        idx = lower_text.find(key)
        if idx == -1:
            continue
        window = original_text[idx : idx + 180]
        match = PERCENT_RE.search(window)
        if match:
            return float(match.group(1))
    return None
