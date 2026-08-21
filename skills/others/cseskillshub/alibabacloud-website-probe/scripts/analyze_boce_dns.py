#!/usr/bin/env python3
"""
分析 boce-tool DNS 拨测结果（JSON 格式）。
专为 DNS 拨测（taskType=5）输出设计，按节点直接展示 provinceCN/ispCN/ips/ipGeoMap 摘要，
避免在主诊断流程中临时探字段（节省约 50s ad-hoc 调试时间）。

用法:
    python3 ./scripts/analyze_boce_dns.py <boce_dns_result.json>
    python3 ./scripts/analyze_boce_dns.py <boce_dns_result.json> --pollution-only
    python3 ./scripts/analyze_boce_dns.py <boce_dns_result.json> --expected 8.148.151.67
    python3 ./scripts/analyze_boce_dns.py <boce_dns_result.json> --report-md <output.md>
    python3 ./scripts/analyze_boce_dns.py <boce_dns_result.json> --json

字段约定（boce DNS 节点）：
    - ips:           节点解析到的 A 记录（逗号分隔）
    - resolution:    某些版本返回结果字段（已知部分版本恒为空，禁止依赖）
    - ipGeoMap:      JSON 字符串，key=IP, value={cnty,city,prov,isp,...}
    - errorCode:     0 表示成功
    - provinceCN/ispCN: 节点所在省份与运营商（用于污染分布定位）
    - probeType:     idc / wifi / mobile （--isp 过滤后多为 idc，但 dnsServer 已切到三大运营商递归）
    - dnsServer:     节点实际使用的递归 DNS（带 --isp 后为运营商真实递归地址）
"""

import json
import os
import sys
from collections import Counter, defaultdict


PRIVATE_OR_INVALID = ("0.0.0.0", "127.")


def parse_geo(item):
    raw = item.get("ipGeoMap") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) or {}
    except Exception:
        return {}


def extract_ips(item):
    """提取节点解析到的 IP 列表。优先 ips 字段，回退 resolution，再回退 ipGeoMap key。"""
    raw = item.get("ips") or item.get("resolution") or ""
    ips = [x.strip() for x in raw.split(",") if x.strip()]
    if not ips:
        geo = parse_geo(item)
        ips = list(geo.keys())
    return ips


def classify_node(item, expected_ips):
    """对单个节点判定状态。返回 (status, ips, geo)。
    status 取值: ok / pollution_overseas / pollution_invalid / empty / partial / mismatch
    mismatch: 给定 expected 且解析结果全部不命中期望 IP（与期望不符）。
    """
    ips = extract_ips(item)
    geo = parse_geo(item)
    if not ips:
        return "empty", ips, geo

    has_invalid = any(ip.startswith(PRIVATE_OR_INVALID) for ip in ips)
    if has_invalid:
        return "pollution_invalid", ips, geo

    if expected_ips:
        if all(ip in expected_ips for ip in ips):
            return "ok", ips, geo
        if any(ip in expected_ips for ip in ips):
            return "partial", ips, geo
        # 给定 expected 且全部不命中：明确判为与期望不符，不再 fall-through 到归属地判定
        return "mismatch", ips, geo

    # 无 expected 时，靠归属地判定境外污染
    overseas = []
    for ip in ips:
        info = geo.get(ip, {})
        cnty = info.get("cnty", "")
        if cnty and cnty != "中国":
            overseas.append(ip)
    if overseas and len(overseas) == len(ips):
        return "pollution_overseas", ips, geo

    return "ok", ips, geo


def summarize(data, expected=None):
    expected_set = set(expected) if expected else set()
    rows = []
    status_counter = Counter()
    ip_counter = Counter()
    overseas_isp_dist = defaultdict(int)
    pollution_geo_dist = Counter()

    for item in data:
        if not isinstance(item, dict):
            continue
        status, ips, geo = classify_node(item, expected_set)
        status_counter[status] += 1
        for ip in ips:
            ip_counter[ip] += 1
            if status in ("pollution_overseas", "pollution_invalid"):
                info = geo.get(ip, {})
                key = f"{info.get('cnty','?')}/{info.get('city') or '-'}/{info.get('isp','?')}"
                pollution_geo_dist[key] += 1
        if status in ("pollution_overseas", "pollution_invalid"):
            overseas_isp_dist[item.get("ispCN", "?")] += 1

        rows.append({
            "areaCN": item.get("areaCN", ""),
            "provinceCN": item.get("provinceCN", ""),
            "cityCN": item.get("cityCN", ""),
            "ispCN": item.get("ispCN", ""),
            "probeType": item.get("probeType", ""),
            "dnsServer": item.get("dnsServer", ""),
            "errorCode": item.get("errorCode"),
            "status": status,
            "ips": ips,
            "geo": {ip: geo.get(ip, {}) for ip in ips},
        })

    total = len(rows)
    return {
        "total": total,
        "status_counter": dict(status_counter),
        "ip_counter": dict(ip_counter.most_common()),
        "pollution_geo_dist": dict(pollution_geo_dist.most_common()),
        "overseas_isp_dist": dict(overseas_isp_dist),
        "rows": rows,
    }


def compute_verdict(status_counter):
    """按状态计数推导机器可读结论: normal / dns_pollution / mismatch / mixed。"""
    pollution = status_counter.get("pollution_overseas", 0) + status_counter.get("pollution_invalid", 0)
    mismatch = status_counter.get("mismatch", 0)
    kinds = []
    if pollution:
        kinds.append("dns_pollution")
    if mismatch:
        kinds.append("mismatch")
    if not kinds:
        return "normal"
    if len(kinds) > 1:
        return "mixed"
    return kinds[0]


def render_text(summary, expected, pollution_only=False):
    out = []
    total = summary["total"]
    sc = summary["status_counter"]
    ok = sc.get("ok", 0)
    pov = sc.get("pollution_overseas", 0)
    piv = sc.get("pollution_invalid", 0)
    em = sc.get("empty", 0)
    pa = sc.get("partial", 0)
    mm = sc.get("mismatch", 0)
    pollution = pov + piv

    out.append("=" * 60)
    out.append(f"DNS 拨测节点摘要（共 {total} 节点）")
    out.append("=" * 60)
    if expected:
        out.append(f"权威 DNS 期望解析: {', '.join(expected)}")
    out.append(
        f"  正常: {ok} | 污染(境外): {pov} | 污染(0/127): {piv} | 期望不符: {mm} | 部分命中: {pa} | 空解析: {em}"
    )
    if expected and mm:
        out.append(f"  ⚠️ {mm} 个节点解析结果与权威期望不符，疑似劫持/配置错误")
    if total:
        out.append(
            f"  污染占比: {pollution}/{total} = {pollution*100/total:.1f}%"
        )
    out.append("")

    out.append("=== 解析 IP 分布 (TOP 30) ===")
    for ip, c in list(summary["ip_counter"].items())[:30]:
        out.append(f"  {c:3d}  {ip}")
    out.append("")

    if summary["pollution_geo_dist"]:
        out.append("=== 污染 IP 归属分布 ===")
        for k, c in summary["pollution_geo_dist"].items():
            out.append(f"  {c:3d}  {k}")
        out.append("")

    if summary["overseas_isp_dist"]:
        out.append("=== 受污染节点的运营商分布 ===")
        for k, c in summary["overseas_isp_dist"].items():
            out.append(f"  {c:3d}  {k}")
        out.append("")

    out.append("=== 节点详情 ===")
    for r in summary["rows"]:
        if pollution_only and r["status"] not in ("pollution_overseas", "pollution_invalid"):
            continue
        ip_brief = []
        for ip in r["ips"]:
            g = r["geo"].get(ip, {})
            ip_brief.append(
                f"{ip}({g.get('cnty','?')}/{g.get('isp','?')})"
            )
        out.append(
            f"  [{r['status']:20s}] {r['provinceCN']:8s} {r['ispCN']:6s} dns={r['dnsServer']:18s} -> {', '.join(ip_brief) or '<empty>'}"
        )
    out.append("")
    out.append(f"verdict: {compute_verdict(sc)}")
    return "\n".join(out)


def render_markdown(summary, expected):
    out = []
    total = summary["total"]
    sc = summary["status_counter"]
    pov = sc.get("pollution_overseas", 0)
    piv = sc.get("pollution_invalid", 0)
    pollution = pov + piv

    out.append("# DNS 拨测分析报告")
    out.append("")
    out.append(f"- 节点总数：{total}")
    if expected:
        out.append(f"- 权威 DNS 期望 IP：`{', '.join(expected)}`")
    out.append(f"- 正常节点：{sc.get('ok',0)}")
    out.append(f"- 污染节点（解析到境外 IP）：{pov}")
    out.append(f"- 污染节点（解析到 0.0.0.0/127.x）：{piv}")
    out.append(f"- 与期望不符节点（全部不命中期望 IP）：{sc.get('mismatch',0)}")
    out.append(f"- 空解析：{sc.get('empty',0)}")
    if expected and sc.get("mismatch", 0):
        out.append(f"- ⚠️ {sc.get('mismatch',0)} 个节点解析结果与权威期望不符，疑似劫持/配置错误")
    if total:
        out.append(f"- **污染占比：{pollution}/{total} = {pollution*100/total:.1f}%**")
    out.append("")

    if summary["pollution_geo_dist"]:
        out.append("## 污染 IP 归属分布")
        out.append("")
        out.append("| 数量 | 国家 / 城市 / 网段 |")
        out.append("|---:|---|")
        for k, c in summary["pollution_geo_dist"].items():
            out.append(f"| {c} | {k} |")
        out.append("")

    out.append("## 异常节点明细")
    out.append("")
    out.append("| 省份 | 运营商 | dnsServer | 状态 | 解析 IP（归属/网段） |")
    out.append("|---|---|---|---|---|")
    for r in summary["rows"]:
        if r["status"] not in ("pollution_overseas", "pollution_invalid", "empty", "mismatch"):
            continue
        ip_brief = []
        for ip in r["ips"]:
            g = r["geo"].get(ip, {})
            ip_brief.append(f"`{ip}`({g.get('cnty','?')}/{g.get('isp','?')})")
        out.append(
            f"| {r['provinceCN']} | {r['ispCN']} | `{r['dnsServer']}` | {r['status']} | {', '.join(ip_brief) or '<empty>'} |"
        )
    out.append("")
    out.append(f"verdict: {compute_verdict(sc)}")
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    src = args[0]
    pollution_only = "--pollution-only" in args
    json_out = "--json" in args
    expected = []
    if "--expected" in args:
        i = args.index("--expected")
        if i + 1 < len(args):
            expected = [x.strip() for x in args[i + 1].split(",") if x.strip()]
    md_path = None
    if "--report-md" in args:
        i = args.index("--report-md")
        if i + 1 < len(args):
            md_path = args[i + 1]

    if not os.path.exists(src):
        print(f"[ERR] 文件不存在: {src}", file=sys.stderr)
        sys.exit(2)
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 兼容包装层
    if isinstance(data, dict):
        for key in ("results", "data", "result", "nodes", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break

    if not isinstance(data, list):
        print("[ERR] 期望 list 顶层；实际为 " + type(data).__name__, file=sys.stderr)
        sys.exit(3)

    summary = summarize(data, expected=expected)

    if json_out:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(render_text(summary, expected, pollution_only=pollution_only))

    if md_path:
        md = render_markdown(summary, expected)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n[OK] Markdown 报告已写入: {md_path}")


if __name__ == "__main__":
    main()
