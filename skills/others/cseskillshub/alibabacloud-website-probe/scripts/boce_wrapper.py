#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alibabacloud-website-probe skill：boce-tool 拨测封装

对 boce-tool 拨测能力做一层简化封装，作为本 skill 的统一调用入口。
所有拨测结果默认直接落盘为 JSON，避免 stdout 截断问题。
http / dns 的结果解读由 analyze_boce_http.py / analyze_boce_dns.py 承担；
ping / mtr / traceroute 没有专用分析脚本，本封装在落盘后直接打印逐节点明细表
（ping 为各节点 RTT/丢包率，mtr/traceroute 为逐跳 TTL/丢包/时延），
避免调用方临时手工探测结果 JSON 字段。

设备视角（PC vs 移动端）:
    所有拨测命令均支持 `--mobile` 开关：
      - 默认（不加 --mobile）: 使用 IDC 探针（probeType=idc），代表运营商骨干网视角；
      - --mobile: 使用移动端探针（probeType=mobile），代表 4G/5G/家庭宽带 last_mile 视角，
        AgentGroup=2 提交给 boce 后端调度。
    用户报告"手机端访问异常"等终端类故障时，必须加 --mobile 复现现场，IDC 视角作为旁证。

用法:
    # HTTP 广域拨测（默认所有节点 / IDC 视角）
    python3 ./scripts/boce_wrapper.py http --target https://www.example.com --output result.json

    # HTTP 移动端视角拨测
    python3 ./scripts/boce_wrapper.py http --target https://www.example.com --mobile --output result_mobile.json

    # HTTP 境外节点拨测
    python3 ./scripts/boce_wrapper.py http --target https://www.example.com --regions 境外 --output result.json

    # HTTP 境内指定区域拨测
    python3 ./scripts/boce_wrapper.py http --target https://www.example.com --regions 华东,华南 --output result.json

    # DNS 拨测（移动端 + 北京电信）
    python3 ./scripts/boce_wrapper.py dns --target www.example.com --regions 华北 --isp 电信 --mobile --output dns_mobile.json

    # Ping 拨测
    python3 ./scripts/boce_wrapper.py ping --target 8.8.8.8 --output ping_result.json

    # MTR 路由追踪（移动端视角）
    python3 ./scripts/boce_wrapper.py mtr --target 8.8.8.8 --mobile --output mtr_result.json

    # Traceroute 路由追踪
    python3 ./scripts/boce_wrapper.py traceroute --target 8.8.8.8 --output tr_result.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 引入 boce_tool 脚本（与本文件同目录）
BOCE_TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BOCE_TOOL_DIR))

try:
    from boce_tool import (
        build_session,
        detect_http,
        detect_dns,
        detect_ping,
        detect_mtr,
        detect_traceroute,
        get_probe_nodes,
        filter_nodes,
        format_ping_results,
        format_mtr_results,
        format_traceroute_results,
        MOBILE_INVALID_COMBOS,
    )
except ImportError as e:
    print(f"[ERROR] 无法加载 boce_tool 模块: {e}")
    print(f"[INFO] 请确认 boce_tool.py 与本文件在同一目录: {BOCE_TOOL_DIR}")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="alibabacloud-website-probe 拨测封装工具（boce-tool 统一调用入口）")
    subparsers = parser.add_subparsers(dest="command", help="拨测类型")

    def add_common_args(p):
        """所有拨测子命令共享的参数。"""
        p.add_argument("--target", "-t", required=True, help="目标域名/URL/IP")
        p.add_argument("--output", "-o", required=True, help="结果 JSON 输出路径")
        p.add_argument("--regions", "-r", help="区域过滤，逗号分隔（华东,华南,华北,华中,东北,西南,西北,境外）")
        p.add_argument("--isp", "-i", help="运营商过滤，逗号分隔（电信,联通,移动）")
        p.add_argument("--max-nodes", "-m", type=int, default=50, help="最大探测节点数")
        p.add_argument("--mobile", action="store_true",
                       help="使用移动端探针（probeType=mobile, AgentGroup=2），代表手机/家庭宽带 last_mile 视角；不加则为 IDC 骨干视角")

    # HTTP
    http_p = subparsers.add_parser("http", help="HTTP(S) 拨测")
    add_common_args(http_p)
    http_p.add_argument("--method", choices=["get", "post", "head"], default="get")

    # DNS
    dns_p = subparsers.add_parser("dns", help="DNS 拨测")
    add_common_args(dns_p)
    dns_p.add_argument("--dns-type", default="A", help="记录类型: A/AAAA/MX/NS/CNAME/TXT/ANY")
    dns_p.add_argument("--dns-server", default="", help="自定义 DNS 服务器")

    # Ping
    ping_p = subparsers.add_parser("ping", help="Ping 拨测")
    add_common_args(ping_p)

    # MTR
    mtr_p = subparsers.add_parser("mtr", help="MTR 路由追踪")
    add_common_args(mtr_p)

    # Traceroute
    tr_p = subparsers.add_parser("traceroute", help="Traceroute 路由追踪")
    add_common_args(tr_p)

    return parser.parse_args()


def main():
    args = parse_args()
    if not args.command:
        print("[ERROR] 请指定拨测类型: http, dns, ping, mtr, traceroute")
        sys.exit(1)

    session = build_session()

    # 获取节点
    task_type_map = {
        "http": "1",
        "dns": "5",
        "ping": "2",
        "mtr": "12",
        "traceroute": "9",
    }
    print(f"[INFO] 获取探测节点 (task_type={task_type_map[args.command]})...")
    all_nodes = get_probe_nodes(session, task_type=task_type_map[args.command])
    # 复用 boce_tool.filter_nodes（含“境外”特殊语义与确定性分层采样）
    regions = [r.strip() for r in args.regions.split(",")] if args.regions else None
    isps = [i.strip() for i in args.isp.split(",")] if args.isp else None
    nodes = filter_nodes(all_nodes, regions=regions, isps=isps, max_nodes=args.max_nodes)

    # Mobile 探针预过滤：排除已知不支持的 city+isp 组合，减少后端 Code=655 试错等待
    agent_group = "2" if getattr(args, "mobile", False) else "1"
    mobile_blacklist_emptied = False
    if agent_group == "2":
        # 复用 boce_tool 内置黑名单（模块级常量，不再读取外部 JSON 文件）
        invalid_set = MOBILE_INVALID_COMBOS
        before = len(nodes)
        filtered_nodes = []
        removed_samples = []
        for n in nodes:
            city = n.get("CityName.zh_CN", "")
            isp = n.get("IspName.zh_CN", "")
            if (city, isp) in invalid_set:
                removed_samples.append((city, isp))
            else:
                filtered_nodes.append(n)
        nodes = filtered_nodes
        after = len(nodes)
        if before > 0 and after == 0:
            mobile_blacklist_emptied = True
        if before > after:
            print(f"[INFO] Mobile预过滤: 排除 {before - after} 个已知无效组合节点，剩余 {after} 个")
            unique_removed = list(dict.fromkeys(removed_samples))
            if unique_removed:
                print(f"[INFO] 预过滤组合: {unique_removed[:5]}{' ...' if len(unique_removed) > 5 else ''}")

    print(f"[INFO] 总节点: {len(all_nodes)} | 筛选后: {len(nodes)}")

    if not nodes:
        if mobile_blacklist_emptied:
            print("[ERROR] 所有节点均命中 mobile 无效组合内置黑名单，无可执行的移动端探测节点。可去掉 --mobile 改用 IDC 视角，或更换 --regions / --isp 范围")
        else:
            print("[ERROR] 没有匹配的探测节点，请检查 --regions / --isp 参数")
        sys.exit(1)

    # 执行拨测
    mode_label = "Mobile (probeType=mobile, AgentGroup=2)" if agent_group == "2" else "PC/IDC (probeType=idc, AgentGroup=1)"
    print(f"[INFO] 设备视角: {mode_label}")
    print(f"[INFO] 开始 {args.command.upper()} 拨测: {args.target}")
    start = time.time()

    if args.command == "http":
        results = detect_http(session, args.target, method=args.method, nodes=nodes, agent_group=agent_group)
    elif args.command == "dns":
        results = detect_dns(
            session, args.target, dns_type=args.dns_type,
            dns_server=args.dns_server if args.dns_server else "",
            nodes=nodes, agent_group=agent_group,
        )
    elif args.command == "ping":
        results = detect_ping(session, args.target, nodes=nodes, agent_group=agent_group)
    elif args.command == "mtr":
        results = detect_mtr(session, args.target, nodes=nodes, agent_group=agent_group)
    elif args.command == "traceroute":
        results = detect_traceroute(session, args.target, nodes=nodes, agent_group=agent_group)
    else:
        print(f"[ERROR] 不支持的拨测类型: {args.command}")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"[INFO] 拨测完成，耗时 {elapsed:.1f}s，结果数: {len(results)}")

    # 提取 API 内部 taskId（注意：这不是 Web 端可访问的分享链接）
    # boce.aliyun.com 的 Web 分享链接是 32 位 hex 短码，由 Web UI 点击「分享」按钮
    # 单独生成；API 直接执行的拨测不会注册到分享存储中。
    # 因此本脚本不再输出误导性的「分享链接」，仅记录 taskId 供本地数据溯源使用。
    task_id = results[0].get("taskId", "") if results else ""
    if task_id:
        print(f"[INFO] API taskId: {task_id}（仅本地溯源用，不可作为可分享 URL）")

    # 保存结果
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 结果已保存: {output_path}")

    # 快速统计
    total = len(results)
    ok = sum(1 for r in results if r.get("errorCode") == 0)
    error = total - ok
    # 按 probeType 分布统计，验证 --mobile 是否生效
    probe_types = {}
    for r in results:
        pt = r.get("probeType", "unknown")
        probe_types[pt] = probe_types.get(pt, 0) + 1
    print(f"\n{'='*50}")
    print(f"拨测汇总: 总计 {total} | 成功 {ok} | 失败 {error}")
    print(f"探针类型分布: {probe_types}")
    print(f"{'='*50}")

    # ping / mtr / traceroute 无专用分析脚本：直接打印逐节点明细表，
    # 供调用方据此判读，无需再手工探测结果 JSON 字段。
    formatter = {
        "ping": format_ping_results,
        "mtr": format_mtr_results,
        "traceroute": format_traceroute_results,
    }.get(args.command)
    if formatter and results:
        print(f"\n【{args.command.upper()} 逐节点明细】")
        print(formatter(results))

    if error > 0:
        print("\n异常节点:")
        for r in results:
            if r.get("errorCode", 0) != 0:
                area = r.get("areaCN", "?")
                prov = r.get("provinceCN", "?")
                isp = r.get("ispCN", "?")
                msg = r.get("message", "")
                print(f"  {area} {prov} {isp} | errorCode={r.get('errorCode')} | {msg}")


if __name__ == "__main__":
    main()
