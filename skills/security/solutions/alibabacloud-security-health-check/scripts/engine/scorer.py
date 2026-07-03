#!/usr/bin/env python3
"""
Alibaba Cloud Security Configuration Health Scoring Engine

Input:
  --input <dir>       Directory containing customer-provided JSON files
                      Expects: waf-collected.json / sas-collected.json /
                               cfw-collected.json / ddos-collected.json
  --checks <dir>      Check items YAML directory (default ../../references/checks)
  --output <dir>      Output directory (default ./output)

Output:
  output/health-report.html    Customer-facing visual report
  output/remediation.xlsx      Ops remediation checklist
  output/exec-summary.md       CSM executive summary

Dependencies: pip install pyyaml jsonpath-ng jinja2 openpyxl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonpath_ng import parse as jsonpath_parse
except ImportError as e:
    sys.exit(f"Missing dependency: {e.name}. Please run: pip install pyyaml jsonpath-ng jinja2 openpyxl")


PRODUCT_ALIASES = {
    "waf": "WAF 3.0",
    "sas": "Security Center (SAS)",
    "cfw": "Cloud Firewall (CFW)",
    "ddos": "DDoS Protection",
}


@dataclass
class CheckResult:
    product: str
    check_id: str
    name: str
    category: str
    severity: str
    weight: int
    verdict: str            # full | partial | fail | error
    score: float            # actual score
    actual_value: Any = None
    remediation: dict = field(default_factory=dict)


# ---------------------------------------------------------------- Rule evaluation

def _match_threshold(expr: str, value: float) -> bool:
    """Parse threshold expressions like ">= 0.95" / "60..80" / "< 40 or > 90" """
    expr = expr.strip()
    if " or " in expr:
        return any(_match_threshold(p, value) for p in expr.split(" or "))
    if ".." in expr:
        lo, hi = map(float, expr.split(".."))
        return lo <= value <= hi
    m = re.match(r"^(>=|<=|>|<|==|!=)\s*(-?\d+\.?\d*)$", expr)
    if not m:
        raise ValueError(f"Cannot parse threshold expression: {expr}")
    op, num = m.group(1), float(m.group(2))
    return {
        ">=": value >= num,
        "<=": value <= num,
        ">": value > num,
        "<": value < num,
        "==": value == num,
        "!=": value != num,
    }[op]


def _eval_jsonpath(path: str, data: dict) -> Any:
    matches = [m.value for m in jsonpath_parse(path).find(data)]
    return matches[0] if matches else None


def evaluate_rule(rule: dict, data: dict) -> tuple[str, Any]:
    rtype = rule["type"]

    if rtype == "ratio":
        num = _eval_jsonpath(rule["numerator"], data)
        den = _eval_jsonpath(rule["denominator"], data)
        if num is None or den is None or den == 0:
            return "error", None
        ratio = float(num) / float(den)
        thr = rule["thresholds"]
        for verdict_key in ("full", "partial", "fail"):
            if _match_threshold(thr[verdict_key], ratio):
                return verdict_key, round(ratio, 3)
        return "fail", round(ratio, 3)

    if rtype == "range":
        v = _eval_jsonpath(rule["path"], data)
        if v is None:
            return "error", None
        thr = rule["thresholds"]
        for verdict_key in ("full", "partial", "fail"):
            if _match_threshold(thr[verdict_key], float(v)):
                return verdict_key, v
        return "fail", v

    if rtype == "exists":
        v = _eval_jsonpath(rule["path"], data)
        return ("full", v) if v == rule["expect"] else ("fail", v)

    if rtype == "enum":
        v = _eval_jsonpath(rule["path"], data)
        if v == rule["expect"]:
            return "full", v
        if v in rule.get("partial_values", []):
            return "partial", v
        if v in rule.get("fail_values", []):
            return "fail", v
        return "error", v

    raise ValueError(f"Unknown rule.type: {rtype}")


# ---------------------------------------------------------------- Scoring main flow

def score_product(product: str, checks_yaml: dict, data: dict) -> tuple[float, list[CheckResult]]:
    """
    Returns a normalized 0-100 product score.
    Normalization: actual_score / total_weight_sum * 100
    This ensures scores are comparable regardless of whether YAML has 3 or 30 checks.
    """
    results = []
    total_score = 0.0
    weight_sum = 0
    for check in checks_yaml["checks"]:
        weight_sum += check["weight"]
        try:
            verdict, actual = evaluate_rule(check["rule"], data)
        except Exception as e:
            verdict, actual = "error", f"Evaluation error: {e}"
        score_pct = {"full": 1.0, "partial": 0.5, "fail": 0.0, "error": 0.0}[verdict]
        score = check["weight"] * score_pct
        total_score += score
        results.append(CheckResult(
            product=product,
            check_id=check["id"],
            name=check["name"],
            category=check["category"],
            severity=check["severity"],
            weight=check["weight"],
            verdict=verdict,
            score=score,
            actual_value=actual,
            remediation=check.get("remediation", {}),
        ))
    normalized = (total_score / weight_sum * 100) if weight_sum else 0
    return normalized, results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Directory containing customer JSON files")
    parser.add_argument("--checks", default=str(Path(__file__).resolve().parents[2] / "references" / "checks"))
    parser.add_argument("--output", default="./output")
    args = parser.parse_args()

    in_dir = Path(args.input)
    check_dir = Path(args.checks)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    overall = {"products": {}, "all_results": []}

    for short, full_name in PRODUCT_ALIASES.items():
        json_file = in_dir / f"{short}-collected.json"
        yaml_file = check_dir / f"{short}.yaml"
        if not json_file.exists():
            print(f"[skip] {full_name}: {json_file.name} not provided")
            continue
        if not yaml_file.exists():
            print(f"[skip] {full_name}: check config {yaml_file.name} not found")
            continue

        data = json.loads(json_file.read_text())
        cy = yaml.safe_load(yaml_file.read_text())
        score, results = score_product(short, cy, data)

        overall["products"][short] = {"name": full_name, "score": score, "max": 100}
        overall["all_results"].extend(results)
        print(f"[{full_name}] Score: {score:.1f}/100")

    # Total = average of all products (MVP: simple average; phase 2: weighted by customer purchases)
    if overall["products"]:
        overall["total"] = sum(p["score"] for p in overall["products"].values()) / len(overall["products"])
    else:
        overall["total"] = 0
    print(f"\nOverall score: {overall['total']:.1f}/100")

    # Output intermediate JSON results (for subsequent HTML/Excel rendering)
    intermediate = out_dir / "scores.json"
    intermediate.write_text(json.dumps(
        {
            **overall,
            "all_results": [r.__dict__ for r in overall["all_results"]],
        },
        indent=2, ensure_ascii=False,
    ))
    print(f"Intermediate results: {intermediate}")
    print("Next step: run report_html.py / report_excel.py to render final reports")


if __name__ == "__main__":
    main()
