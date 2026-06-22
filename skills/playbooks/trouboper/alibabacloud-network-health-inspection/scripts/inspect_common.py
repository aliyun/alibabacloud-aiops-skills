"""
inspect_common.py - 阿里云网络产品巡检公共工具库

提供 aliyun CLI 封装、凭证检测、云监控查询、风险评估等公共功能。
所有 API 调用均为只读查询操作，不涉及任何写操作。

用法:
    python3 inspect_common.py check-env
"""

import sys
if sys.version_info < (3, 7):
    import json as _json
    _msg = {"error": "需要 Python >= 3.7", "current": f"{sys.version_info.major}.{sys.version_info.minor}"}
    print(_json.dumps(_msg, ensure_ascii=False))
    sys.exit(1)

import json
import os
import shlex
import shutil
import subprocess
import time
from typing import Optional


# ─── 中国大陆 Region 列表 ──────────────────────────────────────────

CN_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
    "cn-chengdu", "cn-zhangjiakou", "cn-huhehaote", "cn-wulanchabu",
    "cn-guangzhou", "cn-nanjing", "cn-fuzhou", "cn-heyuan",
]

# CMS 是全局服务，统一使用 cn-hangzhou 作为 endpoint（数据归属由 instanceId 决定）
CMS_ENDPOINT_REGION = "cn-hangzhou"

HAS_CLI = shutil.which("aliyun") is not None


# ─── aliyun CLI 封装 ──────────────────────────────────────────────

def _get_cli_profile() -> str:
    return os.environ.get("ALIYUN_CLI_PROFILE", "")


def run_cli(product: str, api: str, params: dict = None,
            region: str = None, timeout: int = 30) -> dict:
    """
    调用 aliyun CLI（只读操作）并返回 JSON 结果。
    """
    if not HAS_CLI:
        return {"error": "aliyun CLI 不可用，请安装: brew install aliyun-cli"}

    cmd = ["aliyun", product, api]
    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd.extend(["--region", effective_region])

    if params:
        for key, value in params.items():
            if value is not None:
                cmd.extend([f"--{key}", str(value)])

    profile = _get_cli_profile()
    if profile:
        cmd.extend(["--profile", profile])

    shell_cmd = " ".join(shlex.quote(c) for c in cmd)
    try:
        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"API 调用超时: {product} {api}"}
    except FileNotFoundError:
        return {"error": "aliyun CLI 不可用"}

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        try:
            err_json = json.loads(error_msg)
            code = err_json.get("Code", "")
            message = err_json.get("Message", error_msg)
            return {"error": f"{code}: {message}"}
        except json.JSONDecodeError:
            return {"error": error_msg[:300]}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"无法解析 API 响应: {result.stdout[:200]}"}


def _is_transient_error(error_msg: str) -> bool:
    patterns = ["bad file descriptor", "connection reset", "connection refused",
                "dial tcp", "i/o timeout", "Throttling", "timeout", "EOF", "broken pipe"]
    error_lower = error_msg.lower()
    return any(p.lower() in error_lower for p in patterns)


def call_with_retry(product: str, api: str, params: dict = None,
                    region: str = None, max_retries: int = 3) -> dict:
    """带重试的 API 调用（只读操作）。"""
    result = {}
    for attempt in range(max_retries):
        result = run_cli(product, api, params, region)
        error = result.get("error", "")
        if error and _is_transient_error(error):
            wait = 2 ** attempt
            print(f"[重试] {product} {api} region={region} 第{attempt+1}次 等待{wait}秒 错误={error[:80]}",
                  file=sys.stderr)
            time.sleep(wait)
            continue
        return result
    return result


# ─── 云监控查询（只读操作）──────────────────────────────────────────

def query_metric(namespace: str, metric_name: str, instance_id: str,
                 start_time: int, end_time: int, period: int = 60,
                 dim_key: str = "instanceId") -> dict:
    """查询单个云监控指标（只读操作），自动分页拉取全部数据点。

    当聚合粒度小（如60s）且时间跨度长（如7天）时，单次 API 可能无法
    返回全部数据点（上限约1000条）。本函数通过 NextToken 自动分页，
    确保获取完整的监控数据，不丢失任何数据点。
    """
    dimensions = json.dumps([{dim_key: instance_id}])
    all_datapoints = []
    next_token = None

    while True:
        params = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "Dimensions": dimensions,
            "Period": str(period),
            "StartTime": str(start_time),
            "EndTime": str(end_time),
        }
        if next_token:
            params["NextToken"] = next_token

        result = call_with_retry("cms", "DescribeMetricList", params, CMS_ENDPOINT_REGION)
        if "error" in result:
            return {"metric": metric_name, "datapoints": all_datapoints or [],
                    "summary": None, "error": result["error"]}

        dp_str = result.get("Datapoints", "[]")
        try:
            datapoints = json.loads(dp_str) if isinstance(dp_str, str) else dp_str
        except json.JSONDecodeError:
            datapoints = []

        all_datapoints.extend(datapoints)

        next_token = result.get("NextToken", "")
        if not next_token:
            break

    if not all_datapoints:
        return {"metric": metric_name, "datapoints": [], "summary": None}

    values = []
    for dp in all_datapoints:
        v = dp.get("Average") or dp.get("Value") or dp.get("Maximum")
        if v is not None:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass

    summary = None
    if values:
        sorted_vals = sorted(values)
        p95_idx = min(int(len(sorted_vals) * 0.95), len(sorted_vals) - 1)
        p99_idx = min(int(len(sorted_vals) * 0.99), len(sorted_vals) - 1)
        summary = {
            "avg": round(sum(values) / len(values), 2),
            "max": round(max(values), 2),
            "min": round(min(values), 2),
            "p95": round(sorted_vals[p95_idx], 2),
            "p99": round(sorted_vals[p99_idx], 2),
            "count": len(values),
        }

    return {"metric": metric_name, "datapoints": all_datapoints, "summary": summary}


def query_metrics_batch(namespace: str, metric_names: list, instance_id: str,
                        days: int, period: int, dim_key: str = "instanceId") -> dict:
    """批量查询多个云监控指标（只读操作）。

    Args:
        period: 数据聚合粒度（秒），由调用方显式传入，不再内部自动计算。
    """
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000

    metrics = {}
    for metric_name in metric_names:
        result = query_metric(namespace, metric_name, instance_id,
                              start_time, end_time, period, dim_key)
        metrics[metric_name] = result

    return {
        "instance_id": instance_id,
        "time_range": {
            "start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time / 1000)),
            "end": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time / 1000)),
            "days": days,
            "period": period,
        },
        "metrics": metrics,
    }


# ─── 工具函数 ──────────────────────────────────────────────────────

def assess_risk(peak_pct: float, has_drops: bool = False) -> str:
    """根据利用率峰值和丢包情况判定风险等级。"""
    if has_drops or peak_pct >= 90:
        return "critical"
    elif peak_pct >= 70:
        return "warning"
    return "ok"


def bits_to_mbps(bits_per_sec: float) -> float:
    """bits/s 转换为 Mbps。"""
    return round(bits_per_sec / 1_000_000, 2)


def risk_label(level: str) -> str:
    return {"critical": "严重", "warning": "告警", "ok": "正常", "error": "异常"}.get(level, "未知")


def risk_emoji(level: str) -> str:
    return {"critical": "[!!!]", "warning": "[!]", "ok": "[OK]", "error": "[ERR]"}.get(level, "[-]")


def format_standard_output(resource_type: str, resource_type_cn: str, days: int,
                           regions: list, inspected: list, errors: list) -> dict:
    """生成标准化的巡检输出 JSON。"""
    summary = {
        "total": len(inspected),
        "ok": sum(1 for i in inspected if i.get("risk_level") == "ok"),
        "warning": sum(1 for i in inspected if i.get("risk_level") == "warning"),
        "critical": sum(1 for i in inspected if i.get("risk_level") == "critical"),
        "error": sum(1 for i in inspected if i.get("risk_level") == "error"),
    }
    return {
        "resource_type": resource_type,
        "resource_type_cn": resource_type_cn,
        "inspect_days": days,
        "regions": regions,
        "summary": summary,
        "instances": inspected,
        "errors": errors,
    }


# ─── 环境检查 ──────────────────────────────────────────────────────

def check_env():
    """Check runtime environment and credential readiness."""
    has_cli_profile = False
    if HAS_CLI:
        try:
            result = subprocess.run("aliyun configure list", shell=True,
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                has_cli_profile = True
        except Exception:
            pass

    credentials_ready = has_cli_profile
    result = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "aliyun_cli_installed": HAS_CLI,
        "credentials_ready": credentials_ready,
        "credential_source": ("cli_profile" if has_cli_profile else "none"),
        "cn_regions": CN_REGIONS,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check-env":
        check_env()
    else:
        print("用法: python3 inspect_common.py check-env")
