#!/usr/bin/env python3
"""
fetch_config.py — 全量拉取高防转发配置（根治漏采）

职责（只做确定性的取数 + 结构化，不做任何暴露判定）：
  1. 按 region 全量分页拉取 DescribeInstances / DescribeWebRules / DescribeNetworkRules
  2. [MUST] 严禁用 --instance-ids 过滤 web-rules（实测会漏采 80%）；按 region 直接查
  3. [MUST] 每个列表接口都做 TotalCount 完整性校验，取回数 != TotalCount 时告警
  4. 七层源站归一化：RsType=1(域名) 用本地 dig +short 解析为 IP；RsType=0(IP) 直接用（可能逗号分隔）
  5. 四层规则按 IsAutoCreate 拆分：=true 剔除（高防转发集群 IP，非用户源站）、=false 为待探手动规则
  6. 泛域名（*.）标记出来，展开策略交给调用方（本脚本只标记，不自动展开）
  7. 识别 IPv6 源站（含 ':'），单独标记（云拨测不支持 IPv6 目标，需本地 nc -6）

用法：
  SKILL_SESSION_ID=<sid> python3 fetch_config.py --regions cn-hangzhou,ap-southeast-1 --out raw-config.json

本脚本只读、无副作用。
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

SESSION_ID = os.environ.get("SKILL_SESSION_ID", "")
UA = f"AlibabaCloud-Agent-Skills/ddos-origin-exposure-detector/{SESSION_ID}"

PAGE_SIZE = 10          # web-rules/network-rules 上限 10
INSTANCE_PAGE_SIZE = 50 # describe-instances 上限 50


def run_json(cmd):
    """执行 aliyun 命令并解析 JSON，失败返回 (None, error_str)。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if r.returncode != 0:
        return None, (r.stderr or r.stdout or "nonzero-exit").strip()[:300]
    try:
        return json.loads(r.stdout), None
    except Exception as e:
        return None, f"json-parse-failed: {e}; stdout={r.stdout[:200]}"


def dig_short(domain):
    """本地 dig +short 归一化域名为 IP 列表（过滤 CNAME 行）。"""
    try:
        r = subprocess.run(["dig", "+short", domain], capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    valid = []
    for line in r.stdout.strip().splitlines():
        line = line.strip()
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', line):
            valid.append(line)
        elif ':' in line and re.match(r'^[0-9a-fA-F:]+$', line):
            valid.append(line)
    return valid


def is_ipv6(ip):
    return ":" in ip


def split_real_server(val):
    """RealServer 可能是逗号分隔的多个 IP。"""
    return [x.strip() for x in str(val).split(",") if x.strip()]


def fetch_instances(region):
    d, err = run_json(["aliyun", "ddoscoo", "describe-instances", "--region", region,
                       "--page-number", "1", "--page-size", str(INSTANCE_PAGE_SIZE),
                       "--user-agent", UA])
    if d is None:
        print(f"[ERROR] describe-instances {region}: {err}", file=sys.stderr)
        return [], err
    tc = d.get("TotalCount", 0)
    insts = d.get("Instances", [])
    if tc > INSTANCE_PAGE_SIZE:
        pages = math.ceil(tc / INSTANCE_PAGE_SIZE)
        for p in range(2, pages + 1):
            dd, _ = run_json(["aliyun", "ddoscoo", "describe-instances", "--region", region,
                              "--page-number", str(p), "--page-size", str(INSTANCE_PAGE_SIZE),
                              "--user-agent", UA])
            if dd:
                insts.extend(dd.get("Instances", []))
    for i in insts:
        i["_region"] = region
    return insts, None


def fetch_paged(product_action, region, extra_args, list_key):
    """
    通用全量分页 + TotalCount 校验。
    [MUST] web-rules 的 extra_args 不得含 --instance-ids（会漏采）。
    返回 (rules_list, warning_or_None)
    """
    base = ["aliyun"] + product_action + ["--region", region] + extra_args
    first, err = run_json(base + ["--page-number", "1", "--page-size", str(PAGE_SIZE), "--user-agent", UA])
    if first is None:
        return [], f"first-page-error: {err}"
    tc = first.get("TotalCount", 0)
    rules = first.get(list_key, [])
    pages = math.ceil(tc / PAGE_SIZE) if tc else 1
    for p in range(2, pages + 1):
        d, _ = run_json(base + ["--page-number", str(p), "--page-size", str(PAGE_SIZE), "--user-agent", UA])
        if d:
            rules.extend(d.get(list_key, []))
    warn = None
    if len(rules) != tc:
        warn = f"TotalCount={tc} but fetched={len(rules)} (差 {tc - len(rules)})，请人工确认是否服务端快照抖动"
        print(f"[WARN] {' '.join(product_action)} {region}: {warn}", file=sys.stderr)
    else:
        print(f"[OK] {' '.join(product_action)} {region}: 取数完整 {len(rules)}/{tc}", file=sys.stderr)
    return rules, warn


def normalize_web_rule(rule, region):
    """归一化单条七层规则：解析源站 IP、标记域名型源站、标记泛域名。"""
    domain = rule.get("Domain", "")
    real_servers = rule.get("RealServers", [])
    origin_ips, domain_origins, ipv6_origins = [], [], []
    for rs in real_servers:
        rs_type = rs.get("RsType")
        rs_val = rs.get("RealServer", "")
        if rs_type == 1:
            domain_origins.append(rs_val)
            for ip in dig_short(rs_val):
                (ipv6_origins if is_ipv6(ip) else origin_ips).append(ip)
        else:
            for ip in split_real_server(rs_val):
                (ipv6_origins if is_ipv6(ip) else origin_ips).append(ip)
    return {
        "domain": domain,
        "region": region,
        "cname": rule.get("Cname", ""),
        "origin_ips_v4": sorted(set(origin_ips)),
        "origin_ips_v6": sorted(set(ipv6_origins)),
        "origin_raw": [rs.get("RealServer", "") for rs in real_servers],
        "origin_rs_types": [rs.get("RsType") for rs in real_servers],
        "domain_type_origins": domain_origins,
        "proxy_types": rule.get("ProxyTypes", []),
        "is_wildcard": domain.startswith("*."),
    }


def process_network_rules(inst_id, region, rules):
    """拆分四层规则：auto-create 剔除项 / 手动待探项（再分 IPv4、IPv6）。"""
    excluded, manual_v4, manual_v6 = [], [], []
    for r in rules:
        common = {
            "instance": inst_id, "region": region,
            "frontend_port": r.get("FrontendPort"),
            "backend_port": r.get("BackendPort"),
            "protocol": r.get("Protocol"),
        }
        if r.get("IsAutoCreate", False):
            excluded.append({**common, "real_servers_count": len(r.get("RealServers", [])),
                             "reason": "IsAutoCreate=true 网站接入自动生成，源站为高防转发集群 IP，非用户源站"})
        else:
            for ip in r.get("RealServers", []):
                item = {**common, "origin_ip": ip}
                (manual_v6 if is_ipv6(ip) else manual_v4).append(item)
    return excluded, manual_v4, manual_v6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="cn-hangzhou,ap-southeast-1",
                    help="逗号分隔的 region 列表")
    ap.add_argument("--out", default="raw-config.json")
    args = ap.parse_args()

    if not SESSION_ID:
        print("[WARN] SKILL_SESSION_ID 环境变量为空，--user-agent 将缺少 session-id", file=sys.stderr)

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    warnings = []
    all_instances, web_rules = [], []
    net_excluded, net_manual_v4, net_manual_v6 = [], [], []

    for region in regions:
        insts, err = fetch_instances(region)
        if err and not insts:
            warnings.append(f"[{region}] describe-instances 失败: {err}")
            continue
        all_instances.extend(insts)

        web_raw, warn = fetch_paged(["ddoscoo", "describe-web-rules"], region, [], "WebRules")
        if warn:
            warnings.append(f"[{region}] web-rules: {warn}")
        for rule in web_raw:
            web_rules.append(normalize_web_rule(rule, region))

        for inst in insts:
            iid = inst["InstanceId"]
            net_raw, warn = fetch_paged(["ddoscoo", "describe-network-rules"], region,
                                        ["--instance-id", iid], "NetworkRules")
            if warn:
                warnings.append(f"[{region}/{iid}] network-rules: {warn}")
            exc, mv4, mv6 = process_network_rules(iid, region, net_raw)
            net_excluded.extend(exc)
            net_manual_v4.extend(mv4)
            net_manual_v6.extend(mv6)

    wildcard_domains = [w["domain"] for w in web_rules if w["is_wildcard"]]

    out = {
        "regions": regions,
        "instances": [{"InstanceId": i["InstanceId"], "Ip": i.get("Ip"),
                       "IpVersion": i.get("IpVersion"), "region": i["_region"],
                       "Remark": i.get("Remark", "")} for i in all_instances],
        "web_rules": web_rules,
        "network_excluded_auto_create": net_excluded,
        "network_manual_ipv4": net_manual_v4,
        "network_manual_ipv6": net_manual_v6,
        "wildcard_domains": wildcard_domains,
        "warnings": warnings,
        "summary": {
            "instances": len(all_instances),
            "web_domains": len(web_rules),
            "wildcard_domains": len(wildcard_domains),
            "l4_excluded_auto_create": len(net_excluded),
            "l4_manual_ipv4": len(net_manual_v4),
            "l4_manual_ipv6": len(net_manual_v6),
        },
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 写入 {args.out}", file=sys.stderr)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2), file=sys.stderr)
    if warnings:
        print("\n[WARNINGS]（需人工确认，勿忽略）:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    if wildcard_domains:
        print(f"\n[泛域名]需按 SKILL 规范让用户选择处理方式（子域名清单/常见前缀/跳过）: {wildcard_domains}", file=sys.stderr)


if __name__ == "__main__":
    main()
