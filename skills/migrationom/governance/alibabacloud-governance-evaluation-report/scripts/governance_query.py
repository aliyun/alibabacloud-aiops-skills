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
import re
import shutil
import subprocess
import sys
import time
import uuid
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
SKILL_NAME = "alibabacloud-governance-evaluation-report"
USER_AGENT_PREFIX = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
SESSION_ID_ENV_VAR = "ALIBABA_CLOUD_AGENT_SESSION_ID"
SESSION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_SESSION_ID = None
READ_ONLY_API_COMMANDS = frozenset({
    "list-evaluation-metadata",
    "list-evaluation-results",
    "list-evaluation-metric-details",
})
METRIC_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
MAX_API_TIMEOUT = 300
MAX_RESULTS_PER_PAGE = 100
MAX_NEXT_TOKEN_LENGTH = 4096


class ApiCallError(RuntimeError):
    """Raised when a validated Aliyun CLI API call fails."""


def _validate_session_id(session_id):
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(
        session_id
    ):
        raise ValueError(
            f"{SESSION_ID_ENV_VAR} must be a 32-char hex UUID v4"
        )
    try:
        parsed = uuid.UUID(hex=session_id)
    except ValueError as exc:
        raise ValueError(
            f"{SESSION_ID_ENV_VAR} must be a 32-char hex UUID v4"
        ) from exc
    if parsed.version != 4:
        raise ValueError(
            f"{SESSION_ID_ENV_VAR} must be a 32-char hex UUID v4"
        )
    return parsed.hex


def get_session_id():
    """Return one 32-char hex UUID v4 shared by all calls in this process."""
    global _SESSION_ID
    if _SESSION_ID is None:
        configured = os.environ.get(SESSION_ID_ENV_VAR)
        _SESSION_ID = (
            _validate_session_id(configured)
            if configured
            else uuid.uuid4().hex
        )
    return _SESSION_ID


def get_user_agent():
    """Build the required observable User-Agent for this skill invocation."""
    return f"{USER_AGENT_PREFIX}/{get_session_id()}"


def _validate_positive_int(name, value, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} 必须是整数")
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} 必须在 1 到 {maximum} 之间")


def _validate_metric_id(metric_id):
    if not isinstance(metric_id, str) or not METRIC_ID_PATTERN.fullmatch(metric_id):
        raise ValueError(
            "检测项 Id 格式无效，仅允许 1-128 位字母、数字、下划线和连字符"
        )


def _validate_next_token(next_token):
    if not isinstance(next_token, str):
        raise ValueError("分页令牌必须是字符串")
    if not next_token or len(next_token) > MAX_NEXT_TOKEN_LENGTH:
        raise ValueError(f"分页令牌长度必须在 1 到 {MAX_NEXT_TOKEN_LENGTH} 之间")
    if any(ord(char) < 32 or ord(char) == 127 for char in next_token):
        raise ValueError("分页令牌不能包含控制字符")


def _resolve_aliyun_cli():
    executable = shutil.which("aliyun")
    if not executable:
        raise ApiCallError("未找到 aliyun CLI，请先按安装指南完成安装")

    executable = os.path.realpath(executable)
    if not os.path.isabs(executable):
        raise ApiCallError("aliyun CLI 必须解析为绝对路径")
    if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
        raise ApiCallError(f"aliyun CLI 不存在或不可执行: {executable}")
    return executable


def _build_api_command(command, metric_id=None, max_results=None, next_token=None):
    if command not in READ_ONLY_API_COMMANDS:
        raise ValueError(f"不允许调用治理 API: {command!r}")

    detail_args_supplied = any(
        value is not None for value in (metric_id, max_results, next_token)
    )
    if command != "list-evaluation-metric-details" and detail_args_supplied:
        raise ValueError(f"{command} 不接受资源明细参数")

    detail_args = []
    if command == "list-evaluation-metric-details":
        _validate_metric_id(metric_id)
        _validate_positive_int(
            "max_results",
            max_results,
            MAX_RESULTS_PER_PAGE,
        )
        detail_args.extend(["--id", metric_id, "--max-results", str(max_results)])
        if next_token is not None:
            _validate_next_token(next_token)
            detail_args.extend(["--next-token", next_token])

    cmd = [_resolve_aliyun_cli(), "governance", command]
    cmd.extend(detail_args)
    cmd.extend(["--user-agent", get_user_agent()])
    return cmd


def _run_api(command, timeout=60, metric_id=None, max_results=None, next_token=None):
    _validate_positive_int("timeout", timeout, MAX_API_TIMEOUT)
    cmd = _build_api_command(command, metric_id, max_results, next_token)
    print(
        "[安全提示] 即将通过本机 Aliyun CLI 调用阿里云治理中心只读 API "
        f"`governance {command}`。该请求会使用当前 CLI 凭证访问阿里云；"
        f"可执行文件: {cmd[0]}",
        file=sys.stderr,
    )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ApiCallError(f"API 调用超时 (>{timeout}s): governance {command}")
    if proc.returncode != 0:
        raise ApiCallError(f"API 调用失败: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ApiCallError(f"API 返回了无效 JSON: {exc.msg}") from exc


def call_api(command, timeout=60):
    try:
        return _run_api(command, timeout=timeout)
    except (ApiCallError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


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
    try:
        _validate_metric_id(metric_id)
        _validate_positive_int(
            "max_results",
            max_results,
            MAX_RESULTS_PER_PAGE,
        )
        _validate_positive_int("timeout", timeout, MAX_API_TIMEOUT)
        _validate_positive_int("max_pages", max_pages, 1000)
    except ValueError as exc:
        return {"error": str(exc)}

    all_resources = []
    next_token = None
    page_count = 0
    
    while page_count < max_pages:
        page_count += 1
        try:
            data = _run_api(
                "list-evaluation-metric-details",
                timeout=timeout,
                metric_id=metric_id,
                max_results=max_results,
                next_token=next_token,
            )
        except (ApiCallError, ValueError) as exc:
            return {"error": str(exc)}

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

    if args.mode == "resources":
        # Resource queries do not need the metadata/result prefetch. Validate their
        # user-controlled arguments before any external process is launched.
        result = cmd_resources(args.metric_id, args.max_results)
    else:
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

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
