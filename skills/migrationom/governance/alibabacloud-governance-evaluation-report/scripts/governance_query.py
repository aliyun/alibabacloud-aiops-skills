#!/usr/bin/env python3
"""
阿里云治理中心查询工具

支持四种模式:
  overview   - 全局成熟度报告（评分 + 各支柱分布 + 风险分布）
  pillar     - 指定支柱的风险明细
  detail     - 指定检测项的完整详情（含修复建议）
  resources  - 指定检测项的不合规资源列表
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter

CATEGORIES = [
    "Security", "Reliability", "CostOptimization",
    "OperationalExcellence", "Performance",
]
CATEGORY_CN = {
    "Security": "安全",
    "Reliability": "稳定",
    "CostOptimization": "成本",
    "OperationalExcellence": "效率",
    "Performance": "性能",
}
LEVELS = ["Critical", "High", "Medium", "Suggestion"]
LEVEL_CN = {
    "Critical": "严重", "High": "高", "Medium": "中", "Suggestion": "建议",
}
RISKS = ["Error", "Warning", "Suggestion", "None"]
RISK_CN = {
    "Error": "高风险", "Warning": "中风险", "Suggestion": "低风险", "None": "合规",
}

CACHE_DIR = os.path.expanduser("~/.governance_cache")
METADATA_CACHE_TTL = 86400


def call_api(command, timeout=60):
    cmd = ["aliyun", "governance", command, "--user-agent", "AlibabaCloud-Agent-Skills"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"API 调用超时 (>{timeout}s): {' '.join(cmd)}", file=sys.stderr)
        sys.exit(1)
    if proc.returncode != 0:
        print(f"API 调用失败: {proc.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return json.loads(proc.stdout)


def load_metadata(refresh=False):
    """Load metadata with file cache (rarely changes)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, "metadata.json")

    if not refresh and os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < METADATA_CACHE_TTL:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

    data = call_api("list-evaluation-metadata")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def load_data(refresh=False):
    if refresh and os.path.isdir(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, f))

    meta_raw = load_metadata(refresh)
    result_raw = call_api("list-evaluation-results")

    meta_idx = {}
    for em in meta_raw.get("EvaluationMetadata", []):
        for item in em.get("Metadata", []):
            meta_idx[item["Id"]] = item

    result_idx = {}
    for item in result_raw.get("Results", {}).get("MetricResults", []):
        result_idx[item["Id"]] = item

    summary = {
        "TotalScore": result_raw.get("Results", {}).get("TotalScore"),
        "EvaluationTime": result_raw.get("Results", {}).get("EvaluationTime"),
    }
    return meta_idx, result_idx, summary


def merge_item(mid, meta, result):
    risk = result.get("Risk")
    compliance = result.get("Result")
    item = {
        "Id": mid,
        "DisplayName": meta.get("DisplayName"),
        "Description": meta.get("Description"),
        "Category": meta.get("Category"),
        "CategoryCN": CATEGORY_CN.get(meta.get("Category"), ""),
        "RecommendationLevel": meta.get("RecommendationLevel"),
        "RecommendationLevelCN": LEVEL_CN.get(meta.get("RecommendationLevel"), ""),
        "Status": result.get("Status", "Unknown"),
        "Risk": risk,
        "RiskCN": RISK_CN.get(risk, "N/A"),
        "Compliance": compliance,
    }
    summary = result.get("ResourcesSummary")
    if summary and summary.get("NonCompliant"):
        item["NonCompliant"] = summary["NonCompliant"]
    return item


def cmd_overview(meta_idx, result_idx, summary, risk_filter=None):
    risk_filters = {r.strip() for r in risk_filter.split(",")} if risk_filter else None

    output = {
        "TotalScore": summary["TotalScore"],
        "EvaluationTime": summary["EvaluationTime"],
        "TotalMetrics": len(meta_idx),
        "PillarSummary": [],
        "RiskDistribution": {},
        "RiskyItems": [],
    }
    if risk_filters:
        output["RiskFilter"] = sorted(risk_filters, key=lambda r: RISKS.index(r) if r in RISKS else 99)

    risk_order = {r: i for i, r in enumerate(RISKS)}
    level_order = {l: i for i, l in enumerate(LEVELS)}

    pillar_data = {c: {"total": 0, "finished": 0, "risky": 0, "risk_counts": Counter()} for c in CATEGORIES}
    risky_items = []

    for mid, meta in meta_idx.items():
        result = result_idx.get(mid, {})
        cat = meta.get("Category")
        status = result.get("Status", "Unknown")
        risk = result.get("Risk")

        if cat in pillar_data:
            pillar_data[cat]["total"] += 1
            if status == "Finished":
                pillar_data[cat]["finished"] += 1
                if risk and risk != "None":
                    pillar_data[cat]["risky"] += 1
                    pillar_data[cat]["risk_counts"][risk] += 1
                    if not risk_filters or risk in risk_filters:
                        risky_items.append(merge_item(mid, meta, result))

    for cat in CATEGORIES:
        d = pillar_data[cat]
        output["PillarSummary"].append({
            "Category": cat,
            "CategoryCN": CATEGORY_CN[cat],
            "Total": d["total"],
            "Risky": d["risky"],
            "RiskCounts": dict(d["risk_counts"]),
        })

    global_risk = Counter()
    for mid, result in result_idx.items():
        if result.get("Status") == "Finished":
            risk = result.get("Risk")
            if risk and risk != "None":
                global_risk[risk] += 1
    output["RiskDistribution"] = dict(global_risk)

    risky_items.sort(key=lambda x: (
        risk_order.get(x.get("Risk") or "None", 99),
        level_order.get(x.get("RecommendationLevel") or "", 99),
    ))
    output["RiskyItems"] = risky_items
    return output


def cmd_pillar(meta_idx, result_idx, summary, category, level=None, risk=None, risky_only=False):
    risk_order = {r: i for i, r in enumerate(RISKS)}
    level_order = {l: i for i, l in enumerate(LEVELS)}
    levels = [l.strip() for l in level.split(",")] if level else None
    risks = [r.strip() for r in risk.split(",")] if risk else None

    items = []
    for mid, meta in meta_idx.items():
        if meta.get("Category") != category:
            continue
        result = result_idx.get(mid, {})
        status = result.get("Status", "Unknown")
        r = result.get("Risk")

        if risky_only and (status != "Finished" or r in (None, "None")):
            continue
        if levels and meta.get("RecommendationLevel") not in levels:
            continue
        if risks and (r or "None") not in risks:
            continue

        items.append(merge_item(mid, meta, result))

    items.sort(key=lambda x: (
        risk_order.get(x.get("Risk") or "None", 99),
        level_order.get(x.get("RecommendationLevel") or "", 99),
    ))

    return {
        "TotalScore": summary["TotalScore"],
        "EvaluationTime": summary["EvaluationTime"],
        "Category": category,
        "CategoryCN": CATEGORY_CN.get(category, ""),
        "MatchedCount": len(items),
        "Items": items,
    }


def cmd_detail(meta_idx, result_idx, metric_id=None, keyword=None):
    target_meta = None
    target_id = None

    if metric_id:
        target_meta = meta_idx.get(metric_id)
        target_id = metric_id
    elif keyword:
        matches = []
        for mid, meta in meta_idx.items():
            if keyword in (meta.get("DisplayName") or "") or keyword in (meta.get("Description") or ""):
                matches.append((mid, meta))
        if len(matches) == 0:
            return {"error": f"未找到包含关键字 '{keyword}' 的检测项"}
        if len(matches) > 1:
            return {
                "error": f"关键字 '{keyword}' 匹配到 {len(matches)} 条，请更精确",
                "matches": [{"Id": m[0], "DisplayName": m[1].get("DisplayName")} for m in matches[:10]],
            }
        target_id, target_meta = matches[0]

    if not target_meta:
        return {"error": f"未找到 Id={metric_id} 的检测项"}

    result = result_idx.get(target_id, {})

    remediation_list = []
    for r in target_meta.get("RemediationMetadata", {}).get("Remediation", []):
        rem = {"RemediationType": r.get("RemediationType"), "Steps": []}
        for action in r.get("Actions", []):
            step = {}
            if action.get("Classification"):
                step["Classification"] = action["Classification"]
            if action.get("Description"):
                step["Description"] = action["Description"]
            if action.get("Suggestion"):
                step["Suggestion"] = action["Suggestion"]
            if action.get("CostDescription"):
                step["CostDescription"] = action["CostDescription"]
            if action.get("Notice"):
                step["Notice"] = action["Notice"]
            guidance = []
            for g in action.get("Guidance", []):
                entry = {}
                if g.get("Title"):
                    entry["Title"] = g["Title"]
                if g.get("Content"):
                    content = g["Content"].replace("</br>", "\n")
                    entry["Content"] = content
                if g.get("ButtonName"):
                    entry["ButtonName"] = g["ButtonName"]
                if g.get("ButtonRef"):
                    entry["ButtonRef"] = g["ButtonRef"]
                guidance.append(entry)
            if guidance:
                step["Guidance"] = guidance
            rem["Steps"].append(step)
        remediation_list.append(rem)

    resource_props = []
    for p in target_meta.get("ResourceMetadata", {}).get("ResourcePropertyMetadata", []):
        resource_props.append({
            "DisplayName": p.get("DisplayName"),
            "PropertyName": p.get("PropertyName"),
            "PropertyType": p.get("PropertyType"),
        })

    merged = merge_item(target_id, target_meta, result)
    merged["Scope"] = target_meta.get("Scope")
    merged["Stage"] = target_meta.get("Stage")
    merged["TopicCode"] = target_meta.get("TopicCode")
    merged["Remediation"] = remediation_list
    if resource_props:
        merged["ResourceProperties"] = resource_props
    if result.get("PotentialScoreIncrease"):
        merged["PotentialScoreIncrease"] = result["PotentialScoreIncrease"]

    return merged


def cmd_resources(metric_id, max_results=50, timeout=60, max_pages=100):
    """Query non-compliant resources for a specific check item."""
    all_resources = []
    next_token = None
    page_count = 0
    
    while page_count < max_pages:
        page_count += 1
        cmd = [
            "aliyun", "governance", "list-evaluation-metric-details",
            "--id", metric_id,
            "--max-results", str(max_results),
            "--user-agent", "AlibabaCloud-Agent-Skills"
        ]
        if next_token:
            cmd.extend(["--next-token", next_token])
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"error": f"API 调用超时 (>{timeout}s): {' '.join(cmd)}"}
        if proc.returncode != 0:
            return {"error": f"API 调用失败: {proc.stderr.strip()}"}
        
        data = json.loads(proc.stdout)
        resources = data.get("Resources", [])
        all_resources.extend(resources)
        
        next_token = data.get("NextToken")
        if not next_token or not resources:
            break
    
    if page_count >= max_pages and next_token:
        print(f"警告: 已达到最大分页限制 ({max_pages} 页)，可能存在更多资源", file=sys.stderr)
    
    # Format resources for output
    formatted = []
    for res in all_resources:
        item = {
            "ResourceId": res.get("ResourceId"),
            "ResourceName": res.get("ResourceName"),
            "ResourceType": res.get("ResourceType"),
            "RegionId": res.get("RegionId"),
            "ResourceOwnerId": res.get("ResourceOwnerId"),
            "Classification": res.get("ResourceClassification"),
        }
        # Extract properties as key-value pairs
        props = {}
        for p in res.get("ResourceProperties", []):
            props[p.get("PropertyName")] = p.get("PropertyValue")
        if props:
            item["Properties"] = props
        formatted.append(item)
    
    return {
        "MetricId": metric_id,
        "TotalCount": len(formatted),
        "Resources": formatted,
    }


def main():
    parser = argparse.ArgumentParser(description="阿里云治理中心查询工具")
    parser.add_argument("--refresh", action="store_true", help="强制刷新缓存")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_overview = sub.add_parser("overview", help="全局成熟度报告")
    p_overview.add_argument("-r", "--risk", help="实际风险过滤（逗号分隔，如 Error,Warning）")

    p_pillar = sub.add_parser("pillar", help="指定支柱的风险明细")
    p_pillar.add_argument("-c", "--category", required=True, help="支柱名称")
    p_pillar.add_argument("-l", "--level", help="推荐等级过滤（逗号分隔）")
    p_pillar.add_argument("-r", "--risk", help="实际风险过滤（逗号分隔）")
    p_pillar.add_argument("--risky", dest="risky_only", action="store_true", help="只显示有风险的项")

    p_detail = sub.add_parser("detail", help="检测项详情")
    p_detail.add_argument("--id", dest="metric_id", help="检测项 Id")
    p_detail.add_argument("--keyword", help="按名称关键字搜索")

    p_resources = sub.add_parser("resources", help="查询不合规资源列表")
    p_resources.add_argument("--id", dest="metric_id", required=True, help="检测项 Id")
    p_resources.add_argument("--max-results", type=int, default=50, help="每页最大数量")

    args = parser.parse_args()
    meta_idx, result_idx, summary = load_data(args.refresh)

    if args.mode == "overview":
        result = cmd_overview(meta_idx, result_idx, summary, args.risk)
    elif args.mode == "pillar":
        result = cmd_pillar(meta_idx, result_idx, summary,
                            args.category, args.level, args.risk, args.risky_only)
    elif args.mode == "detail":
        if not args.metric_id and not args.keyword:
            parser.error("请指定 --id 或 --keyword")
        result = cmd_detail(meta_idx, result_idx, args.metric_id, args.keyword)
    elif args.mode == "resources":
        result = cmd_resources(args.metric_id, args.max_results)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
