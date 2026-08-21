#!/usr/bin/env python3
"""
分析 boce-tool HTTP/DNS 拨测结果（JSON 格式）。
输出状态码分布、目的 IP 分布、中国节点详情、异常节点筛选等统计信息。

用法:
    python3 ./scripts/analyze_boce_http.py <boce_result.json>
    python3 ./scripts/analyze_boce_http.py <boce_result.json> --china-only
    python3 ./scripts/analyze_boce_http.py <boce_result.json> --abnormal-only
    python3 ./scripts/analyze_boce_http.py <boce_result.json> --report-md <output.md>

--report-md 模式：仅输出异常节点统计为 Markdown，正常节点全部舍弃，
适合作为运营商报障邮件的附件提交（替代不可用的 boce Web 分享链接）。
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime


def collect_abnormal(data):
    """从 boce 结果中筛选异常节点，返回 (abnormal_list, total, ip_counter, status_counter)。

    异常判定：
    - errorCode 非 0 / 非空，或
    - HTTPResponseCode 非 200（HTTP 拨测），或
    - 解析 IP 落在非法/私有保留段（0.0.0.0、127.x.x.x）—— 仅当 ipGeoMap 中存在该 IP 时
    """
    private_or_invalid = ("0.0.0.0", "127.")
    abnormal = []
    status_counter = Counter()
    ip_counter = Counter()
    for item in data:
        ec = item.get("errorCode")
        hc = item.get("HTTPResponseCode")
        target_ip = item.get("targetIp", "") or ""
        # 解析 ipGeoMap 取所有解析 IP（DNS 拨测无 targetIp 字段时使用）
        try:
            geo = json.loads(item.get("ipGeoMap", "{}") or "{}")
        except Exception:
            geo = {}
        resolved_ips = list(geo.keys()) if geo else ([target_ip] if target_ip else [])
        for ip in resolved_ips:
            ip_counter[ip] += 1
        if not resolved_ips:
            ip_counter["<empty>"] += 1

        is_abnormal = False
        reason = []
        if ec is not None and ec != "" and float(ec) != 0.0:
            is_abnormal = True
            reason.append(f"errorCode={int(float(ec))}")
        if hc is not None and hc != "" and float(hc) != 200.0 and float(hc) != 301.0 and float(hc) != 302.0:
            # 4XX/5XX/0 都视为异常；3XX 重定向不算异常
            if float(hc) != 0.0 or "errorCode" not in " ".join(reason):
                is_abnormal = True
                reason.append(f"HTTP={int(float(hc))}")
        # DNS 解析到 0.0.0.0 / 127.x.x.x 即使 errorCode=0 也判异常
        for ip in resolved_ips:
            if ip.startswith(private_or_invalid):
                is_abnormal = True
                reason.append(f"resolved={ip}")
                break

        status = extract_status(item)
        status_counter[status] += 1

        if is_abnormal:
            abnormal.append({
                "country": item.get("countryCN", "") or item.get("areaCN", ""),
                "province": item.get("provinceCN", "") or item.get("areaCN", ""),
                "city": item.get("cityCN", "") or item.get("city", ""),
                "isp": item.get("ispCN", ""),
                "errorCode": int(float(ec)) if ec not in (None, "") else 0,
                "httpCode": int(float(hc)) if hc not in (None, "") else None,
                "targetIp": target_ip,
                "resolvedIps": resolved_ips,
                "reason": "; ".join(reason),
                "message": item.get("message", "") or item.get("expection", ""),
            })
    return abnormal, len(data), ip_counter, status_counter


def write_report_md(json_path, output_md, data):
    """生成「仅含异常节点」的 Markdown 统计报告（运营商报障邮件附件用）。"""
    abnormal, total, ip_counter, status_counter = collect_abnormal(data)
    src_name = os.path.basename(json_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"# boce 拨测异常节点统计 — {src_name}")
    lines.append("")
    lines.append(f"- 生成时间：{now}")
    lines.append(f"- 数据源 JSON：`{json_path}`")
    lines.append(f"- 总节点数：{total}")
    lines.append(f"- 异常节点数：{len(abnormal)}")
    lines.append(f"- 异常占比：{(len(abnormal) / total * 100):.1f}%" if total else "- 异常占比：N/A")
    lines.append("")
    lines.append("> 本附件仅列出异常节点，正常节点全部舍弃，便于运营商定位拦截规则。完整原始数据请参见同附件提交的 JSON 文件。")
    lines.append("")

    if not abnormal:
        lines.append("## 异常节点")
        lines.append("")
        lines.append("无异常节点。")
        lines.append("")
    else:
        # 错误原因分布
        lines.append("## 异常类型分布")
        lines.append("")
        reason_counter = Counter()
        for n in abnormal:
            reason_counter[n["reason"]] += 1
        lines.append("| 异常原因 | 节点数 |")
        lines.append("|----------|--------|")
        for r, c in reason_counter.most_common():
            lines.append(f"| `{r}` | {c} |")
        lines.append("")

        # 受影响运营商/地域
        lines.append("## 受影响运营商 / 地域")
        lines.append("")
        op_counter = Counter()
        for n in abnormal:
            key = f"{n['province']} {n['isp']}".strip()
            op_counter[key] += 1
        lines.append("| 省份/运营商 | 节点数 |")
        lines.append("|-------------|--------|")
        for k, c in op_counter.most_common():
            lines.append(f"| {k} | {c} |")
        lines.append("")

        # 异常节点明细
        lines.append("## 异常节点明细")
        lines.append("")
        lines.append("| 国家 | 省份 | 城市 | 运营商 | errorCode | HTTP | 解析 IP | 异常原因 | message |")
        lines.append("|------|------|------|--------|-----------|------|---------|----------|---------|")
        for n in abnormal:
            ips = ",".join(n["resolvedIps"]) if n["resolvedIps"] else (n["targetIp"] or "-")
            msg = (n["message"] or "").replace("|", "\\|").replace("\n", " ")[:80]
            http = n["httpCode"] if n["httpCode"] is not None else "-"
            lines.append(
                f"| {n['country']} | {n['province']} | {n['city']} | {n['isp']} | "
                f"{n['errorCode']} | {http} | {ips} | {n['reason']} | {msg} |"
            )
        lines.append("")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[INFO] 异常节点统计报告已生成: {output_md}")
    print(f"[INFO] 总节点 {total}，异常 {len(abnormal)}（{(len(abnormal)/total*100 if total else 0):.1f}%）")



def load_results(path):
    """加载 boce-tool 输出的 JSON，兼容 stdout 前缀行（如 urllib3 警告）。"""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找到 JSON 数组起始位置
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            start = i
            break

    return json.loads("".join(lines[start:]))


def extract_status(item):
    """提取节点最终状态：优先用 errorCode，其次 HTTPResponseCode。"""
    ec = item.get("errorCode")
    if ec is not None and ec != 0 and ec != "":
        return str(int(ec)) if isinstance(ec, float) else str(ec)
    hc = item.get("HTTPResponseCode")
    if hc is not None and hc != "":
        return str(int(hc)) if isinstance(hc, float) else str(hc)
    return "unknown"


def derive_verdict(total, abnormal_nodes):
    """按异常节点数据推导机器可读结论与一句话总体判定。
    返回 (verdict, verdict_text)。verdict 取值:
    normal / regional_failure / global_failure / http_error / mixed
    """
    abn = len(abnormal_nodes)
    if total == 0 or abn == 0:
        return "normal", f"全部节点 HTTP 200，服务全网可用（共 {total} 个节点）"
    if abn == total:
        return "global_failure", f"全部 {total} 个节点异常，服务全网不可达"
    # 部分异常：区分连接级错误（errorCode）与 HTTP 状态码错误
    conn_err = sum(1 for n in abnormal_nodes if n.get("kind") == "conn")
    http_err = abn - conn_err
    if conn_err and http_err:
        return "mixed", f"{abn} 个节点异常（连接失败 {conn_err}，HTTP 错误 {http_err}），多种异常并存"
    if http_err:
        return "http_error", f"{abn} 个节点返回非 200 状态码，疑似服务端错误"
    return "regional_failure", f"{abn} 个节点异常（共 {total} 个），疑似地域性故障"


def analyze(data, china_only=False, abnormal_only=False):
    if not isinstance(data, list):
        print("错误：JSON 根节点应为数组（boce-tool 输出格式）")
        sys.exit(1)

    total = len(data)

    # 状态码分布
    status_counter = Counter()
    ip_counter = Counter()
    china_nodes = []
    overseas_nodes = []
    abnormal_nodes = []

    for item in data:
        status = extract_status(item)
        status_counter[status] += 1

        ip = item.get("targetIp", "unknown")
        ip_counter[ip] += 1

        is_china = item.get("countryCN") == "中国"
        node_info = {
            "country": item.get("countryCN", ""),
            "province": item.get("provinceCN", ""),
            "city": item.get("cityCN", ""),
            "isp": item.get("ispCN", ""),
            "status": status,
            "ip": ip,
            "msg": item.get("message", ""),
            "dns_success": item.get("dnsSuccess", ""),
        }

        if is_china:
            china_nodes.append(node_info)
        else:
            overseas_nodes.append(node_info)

        # 异常判定：errorCode 非 0 且非空，或 HTTPResponseCode 非 200
        ec = item.get("errorCode")
        hc = item.get("HTTPResponseCode")
        is_abnormal = False
        if ec is not None and ec != "" and ec != 0.0:
            is_abnormal = True
        elif hc is not None and hc != "" and hc != 200.0:
            is_abnormal = True

        if is_abnormal:
            info = dict(node_info)
            info["kind"] = "conn" if (ec is not None and ec != "" and ec != 0.0) else "http"
            abnormal_nodes.append(info)

    # 统计摘要（总分结构：先总后分，置顶展示）
    verdict, verdict_text = derive_verdict(total, abnormal_nodes)
    abnormal_china = [n for n in abnormal_nodes if n["country"] == "中国"]
    abnormal_overseas = [n for n in abnormal_nodes if n["country"] != "中国"]
    print("=" * 50)
    print("摘要")
    print("=" * 50)
    print(f"  总节点: {total}")
    print(f"  中国节点: {len(china_nodes)}")
    print(f"  海外节点: {len(overseas_nodes)}")
    print(f"  异常节点: {len(abnormal_nodes)} (境内 {len(abnormal_china)}, 境外 {len(abnormal_overseas)})")
    if abnormal_nodes:
        codes = Counter(n["status"] for n in abnormal_nodes)
        print(f"  异常状态码: {dict(codes)}")
    print(f"  总体判定: {verdict_text}")
    print()
    print(f"总探测节点数: {total}\n")

    # 输出状态码分布
    print("=" * 50)
    print("状态码分布")
    print("=" * 50)
    for code, count in status_counter.most_common():
        pct = count / total * 100
        print(f"  {code:>10s}: {count:>3d}  ({pct:5.1f}%)")
    print()

    # 输出目的 IP 分布
    print("=" * 50)
    print("目的 IP 分布")
    print("=" * 50)
    for ip, count in ip_counter.most_common():
        pct = count / total * 100
        print(f"  {ip:>20s}: {count:>3d}  ({pct:5.1f}%)")
    print()

    # 中国节点详情
    if china_nodes:
        target_nodes = china_nodes
        label = f"中国节点 ({len(china_nodes)} 个)"
    else:
        target_nodes = []
        label = "中国节点 (0 个)"

    if not abnormal_only:
        print("=" * 50)
        print(label)
        print("=" * 50)
        for n in china_nodes:
            flag = "⚠️" if n["status"] not in ("0", "200") else "  "
            print(f"  {flag} {n['province']:>8s} {n['city']:>10s} {n['isp']:>10s} -> {n['status']:>6s} ({n['ip']}) {n['msg']}")
        print()

        # 海外节点明细（为 0 时省略；--china-only 时不展示）
        if overseas_nodes and not china_only:
            print("=" * 50)
            print(f"海外节点 ({len(overseas_nodes)} 个)")
            print("=" * 50)
            for n in overseas_nodes:
                flag = "⚠️" if n["status"] not in ("0", "200") else "  "
                print(f"  {flag} {n['country']:>8s} {n['city']:>10s} {n['isp']:>10s} -> {n['status']:>6s} ({n['ip']}) {n['msg']}")
            print()

    # 异常节点
    if abnormal_nodes:
        print("=" * 50)
        print(f"异常节点 ({len(abnormal_nodes)} 个)")
        print("=" * 50)
        for n in abnormal_nodes:
            print(f"  {n['country']:>6s} {n['province']:>10s} {n['city']:>10s} {n['isp']:>10s} -> {n['status']:>6s} ({n['ip']}) {n['msg']}")
        print()
    else:
        print("=" * 50)
        print("异常节点: 无")
        print("=" * 50)
        print()

    # 机器可读结论行
    print(f"verdict: {verdict}")


def print_ip_geo_summary(data):
    """从 boce 结果 JSON 的 ipGeoMap 字段提取每个 targetIp 的归属地摘要（零开销）。"""
    from collections import defaultdict
    ip_geo_map = {}
    for item in data:
        target_ip = item.get("targetIp", "")
        if not target_ip or target_ip in ip_geo_map:
            continue
        try:
            geo = json.loads(item.get("ipGeoMap", "{}") or "{}")
        except Exception:
            geo = {}
        info = geo.get(target_ip, {})
        if info:
            ip_geo_map[target_ip] = {
                "country": info.get("country", ""),
                "province": info.get("province", ""),
                "city": info.get("city", ""),
                "isp": info.get("isp", ""),
            }
    if not ip_geo_map:
        print("[INFO] 未在 ipGeoMap 中找到 IP 归属地信息")
        return
    print("\n=== IP 归属地摘要 (from ipGeoMap, 零开销) ===")
    for ip, info in ip_geo_map.items():
        parts = [p for p in [info["country"], info["province"], info["city"], info["isp"]] if p]
        print(f"  {ip}: {' / '.join(parts)}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    china_only = "--china-only" in sys.argv
    abnormal_only = "--abnormal-only" in sys.argv

    data = load_results(path)

    # --report-md 模式：仅输出异常节点 Markdown 报告
    if "--report-md" in sys.argv:
        idx = sys.argv.index("--report-md")
        if idx + 1 >= len(sys.argv):
            print("[ERROR] --report-md 需要指定输出文件路径")
            sys.exit(1)
        output_md = sys.argv[idx + 1]
        write_report_md(path, output_md, data)
        return

    # --ip-geo-summary 模式：零开销提取 IP 归属地
    if "--ip-geo-summary" in sys.argv:
        print_ip_geo_summary(data)
        return

    analyze(data, china_only=china_only, abnormal_only=abnormal_only)


if __name__ == "__main__":
    main()
