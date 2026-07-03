#!/usr/bin/env python3
"""
report_html.py - Generate dark-themed HTML health check report
Reads scores.json -> renders assets/templates/report.html.j2 -> outputs single-file HTML
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# ---- Label/color mapping ----
VERDICT_LABEL = {
    "full": "Passed",
    "partial": "Partial",
    "fail": "Failed",
    "error": "Undetermined",
}
EFFORT_LABEL = {"low": "Low", "medium": "Medium", "high": "High"}
PRODUCT_LABEL = {
    "waf": "WAF",
    "sas": "SAS",
    "cfw": "CFW",
    "ddos": "DDoS",
}
GRADE_BANDS = [
    (90, "A", "Excellent", "#34d399"),
    (75, "B", "Good", "#5b8def"),
    (60, "C", "Passing", "#f59e0b"),
    (0,  "D", "Needs Improvement", "#ef4444"),
]

# Top10 sorting: high severity > high weight > low effort
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
EFFORT_RANK   = {"low": 3, "medium": 2, "high": 1}


def grade_for(score: float):
    for cutoff, g, label, color in GRADE_BANDS:
        if score >= cutoff:
            return g, label, color
    return "D", "Needs Improvement", "#ef4444"


def format_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def build_context(scores: dict, customer_name: str) -> dict:
    products_out = []
    radar_labels, radar_scores = [], []
    overall = 0.0
    p_count = 0

    for pid, p in scores["products"].items():
        # All check items for this product
        checks = [
            r for r in scores["all_results"] if r["product"] == pid
        ]
        full    = sum(1 for r in checks if r["verdict"] == "full")
        partial = sum(1 for r in checks if r["verdict"] == "partial")
        fail    = sum(1 for r in checks if r["verdict"] == "fail")

        g, label, color = grade_for(p["score"])
        radar_labels.append(p["name"])
        radar_scores.append(p["score"])
        overall += p["score"]
        p_count += 1

        check_rows = []
        for r in checks:
            check_rows.append({
                "name": r["name"],
                "category": r["category"],
                "weight": r["weight"],
                "actual_value": format_value(r["actual_value"]),
                "verdict": r["verdict"],
                "verdict_label": VERDICT_LABEL[r["verdict"]],
                "effort_label": EFFORT_LABEL.get(
                    r.get("remediation", {}).get("effort", "medium"), "Medium"
                ),
                "doc": r.get("remediation", {}).get("doc", "#"),
            })

        products_out.append({
            "id": pid,
            "name": p["name"],
            "score": p["score"],
            "grade": g,
            "grade_label": label,
            "grade_color": color,
            "full": full, "partial": partial, "fail": fail,
            "checks": check_rows,
        })

    overall_score = round(overall / p_count, 1) if p_count else 0
    og, ol, oc = grade_for(overall_score)

    # Top10 remediation: only partial + fail, sorted by risk x effort
    candidates = [r for r in scores["all_results"]
                  if r["verdict"] in ("partial", "fail")]

    def rank_key(r):
        sev   = SEVERITY_RANK.get(r["severity"], 1)
        verd  = 2 if r["verdict"] == "fail" else 1
        eff   = EFFORT_RANK.get(
            r.get("remediation", {}).get("effort", "medium"), 2
        )
        # Composite score: severity level x ease of remediation x weight
        return -(sev * 2 + verd * 3 + eff + r["weight"] * 0.3)

    top10 = sorted(candidates, key=rank_key)[:10]
    top10_out = []
    for item in top10:
        eff = item.get("remediation", {}).get("effort", "medium")
        top10_out.append({
            "name": item["name"],
            "category": item["category"],
            "weight": item["weight"],
            "actual_value": format_value(item["actual_value"]),
            "product_label": PRODUCT_LABEL.get(item["product"], item["product"]),
            "effort": eff,
            "effort_label": EFFORT_LABEL.get(eff, "Medium"),
            "verdict": item["verdict"],
            "verdict_label": VERDICT_LABEL[item["verdict"]],
        })

    return {
        "customer_name": customer_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overall_score": overall_score,
        "overall_grade": og,
        "grade_label": ol,
        "grade_color": oc,
        "products": products_out,
        "total_checks": len(scores["all_results"]),
        "top10": top10_out,
        "radar_data": {
            "labels": radar_labels,
            "scores": radar_scores,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate HTML health check report")
    parser.add_argument("--scores", default="output/scores.json")
    parser.add_argument("--template", default=str(Path(__file__).resolve().parents[2] / "assets" / "templates" / "report.html.j2"))
    parser.add_argument("--output", default="output/health-report.html")
    parser.add_argument("--customer", default="Example Customer ABC")
    args = parser.parse_args()

    scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    tpl_dir = Path(args.template).parent
    tpl_name = Path(args.template).name

    env = Environment(loader=FileSystemLoader(str(tpl_dir)))
    tpl = env.get_template(tpl_name)
    ctx = build_context(scores, args.customer)
    html = tpl.render(**ctx)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[HTML] Generated: {out_path}")
    print(f"       Customer={args.customer}  Score={ctx['overall_score']} ({ctx['overall_grade']})")


if __name__ == "__main__":
    main()
