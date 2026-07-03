#!/usr/bin/env python3
"""
report_markdown.py - Generate Markdown executive summary for CSM reporting
Reads scores.json -> renders assets/templates/exec_summary.md.j2
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PRODUCT_LABEL = {
    "waf": "WAF 3.0",
    "sas": "Security Center (SAS)",
    "cfw": "Cloud Firewall (CFW)",
    "ddos": "DDoS Protection",
}
PRODUCT_SHORT = {"waf": "WAF", "sas": "SAS", "cfw": "CFW", "ddos": "DDoS"}
EFFORT_LABEL = {"low": "Low", "medium": "Medium", "high": "High"}
GRADE_BANDS = [
    (90, "A", "Excellent"),
    (75, "B", "Good"),
    (60, "C", "Passing"),
    (0,  "D", "Needs Improvement"),
]

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
EFFORT_RANK = {"low": 3, "medium": 2, "high": 1}


def grade_for(score):
    for cutoff, g, label in GRADE_BANDS:
        if score >= cutoff:
            return g, label
    return "D", "Needs Improvement"


def headline(overall_score, products):
    """Generate a narrative sentence based on overall score and product distribution"""
    weakest = min(products, key=lambda p: p["score"])
    strongest = max(products, key=lambda p: p["score"])

    if overall_score >= 90:
        return f"Overall configuration health is strong. {strongest['name']} performs best ({strongest['score']}/100). Recommend maintaining current posture and scheduling periodic re-scans."
    if overall_score >= 75:
        return f"Overall health is at a good level. The primary gap is in **{weakest['name']}** ({weakest['score']}/100), where most optimization opportunities are concentrated."
    if overall_score >= 60:
        return (
            f"Overall configuration only meets the passing threshold. **{weakest['name']}** is the biggest gap ({weakest['score']}/100). "
            f"Multiple high-risk items remain unactivated. Recommend scheduling focused remediation this quarter."
        )
    return (
        f"Overall configuration has systemic gaps. **{weakest['name']}** carries the highest risk ({weakest['score']}/100). "
        "Multiple core protection capabilities are not enabled. Recommend initiating P0 remediation immediately and re-testing."
    )


def first_step(steps_text: str) -> str:
    """Extract the first sentence of remediation steps as a summary"""
    if not steps_text:
        return "—"
    s = steps_text.strip().split("\n")[0]
    # Remove numbering prefix
    for prefix in ("1.", "1)", "- "):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    return s if len(s) <= 60 else s[:60] + "..."


def build_risk_areas(failed_or_partial):
    """Aggregate by category and produce the top three critical risk areas"""
    by_category = defaultdict(list)
    for r in failed_or_partial:
        by_category[r["category"]].append(r)

    # Category priority (by average risk)
    cat_priority = sorted(
        by_category.items(),
        key=lambda x: -sum(
            SEVERITY_RANK.get(r["severity"], 1) * r["weight"] for r in x[1]
        ),
    )

    area_desc = {
        "coverage":       "Core protection capabilities have incomplete asset coverage, leaving blind spots.",
        "strength":       "Features are enabled but policies are weak; protection may underperform in attack scenarios.",
        "responsiveness": "Alert/response pipeline has latency, impacting incident response speed.",
        "compliance":     "Not aligned with compliance baseline requirements; may be flagged during audits.",
        "best-practice":  "Recommended advanced capabilities are not enabled, affecting overall security posture.",
    }

    areas = []
    for cat, items in cat_priority[:3]:
        sorted_items = sorted(
            items,
            key=lambda r: -(
                SEVERITY_RANK.get(r["severity"], 1) * 5 + r["weight"]
            ),
        )[:4]
        out_items = []
        for it in sorted_items:
            actual = it["actual_value"]
            if isinstance(actual, float):
                actual = f"{actual:.0%}" if 0 <= actual <= 1 else f"{actual:.2f}"
            else:
                actual = str(actual)
            impact = "High risk, prioritize remediation" if it["severity"] == "high" else "Room for improvement"
            out_items.append({
                "product_label": PRODUCT_SHORT.get(it["product"], it["product"]),
                "name": it["name"],
                "actual_value": actual,
                "impact": impact,
            })
        areas.append({
            "title": f"{cat} ({len(items)} items pending remediation)",
            "desc": area_desc.get(cat, ""),
            "entries": out_items,
        })
    return areas


def classify_priority(items):
    """Classify by P0/P1/P2. P0 = high severity + (fail or low effort); P1 = other fail / high severity partial; P2 = remainder"""
    p0, p1, p2 = [], [], []
    for it in items:
        sev = it["severity"]
        verd = it["verdict"]
        eff = it.get("remediation", {}).get("effort", "medium")

        entry = {
            "product_label": PRODUCT_SHORT.get(it["product"], it["product"]),
            "name": it["name"],
            "first_step": first_step(it.get("remediation", {}).get("steps", "")),
            "effort_label": EFFORT_LABEL.get(eff, "Medium"),
        }

        if sev == "high" and verd == "fail":
            p0.append(entry)
        elif sev == "high" and verd == "partial":
            p1.append(entry)
        elif verd == "fail" and eff == "low":
            p1.append(entry)
        else:
            p2.append(entry)
    return p0[:8], p1[:8], p2[:6]


def build_context(scores, customer_name):
    products_out = []
    overall = 0.0
    for pid, p in scores["products"].items():
        checks = [r for r in scores["all_results"] if r["product"] == pid]
        full = sum(1 for r in checks if r["verdict"] == "full")
        part = sum(1 for r in checks if r["verdict"] == "partial")
        fail = sum(1 for r in checks if r["verdict"] == "fail")
        g, label = grade_for(p["score"])
        products_out.append({
            "name": p["name"], "score": p["score"],
            "grade": g, "grade_label": label,
            "full": full, "partial": part, "fail": fail,
        })
        overall += p["score"]
    overall_score = round(overall / max(1, len(scores["products"])), 1)
    og, ol = grade_for(overall_score)

    pending = [r for r in scores["all_results"]
               if r["verdict"] in ("fail", "partial")]
    top_risks = sorted(
        pending,
        key=lambda r: -(SEVERITY_RANK.get(r["severity"], 1) * 5 + r["weight"]),
    )[:12]
    p0, p1, p2 = classify_priority(top_risks)

    return {
        "customer_name": customer_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "product_count": len(scores["products"]),
        "product_list": ", ".join(
            PRODUCT_LABEL.get(pid, scores["products"][pid].get("name", pid))
            for pid in scores["products"].keys()
        ),
        "skipped_products": ", ".join(
            PRODUCT_LABEL[pid] for pid in PRODUCT_LABEL.keys()
            if pid not in scores["products"]
        ),
        "total_checks": len(scores["all_results"]),
        "overall_score": overall_score,
        "overall_grade": og,
        "grade_label": ol,
        "headline_sentence": headline(overall_score, products_out),
        "products": products_out,
        "top_risks": top_risks,
        "risk_areas": build_risk_areas(pending),
        "p0_items": p0,
        "p1_items": p1,
        "p2_items": p2,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate executive summary Markdown")
    parser.add_argument("--scores", default="output/scores.json")
    parser.add_argument("--template", default=str(Path(__file__).resolve().parents[2] / "assets" / "templates" / "exec_summary.md.j2"))
    parser.add_argument("--output", default="output/exec-summary.md")
    parser.add_argument("--customer", default="Example Customer ABC")
    args = parser.parse_args()

    scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    tpl_dir = Path(args.template).parent
    tpl_name = Path(args.template).name

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        trim_blocks=True, lstrip_blocks=True,
    )
    tpl = env.get_template(tpl_name)
    ctx = build_context(scores, args.customer)
    md = tpl.render(**ctx)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"[MD]    Generated: {out_path}")
    print(f"        P0={len(ctx['p0_items'])}  P1={len(ctx['p1_items'])}  P2={len(ctx['p2_items'])}")


if __name__ == "__main__":
    main()
