#!/usr/bin/env python3
"""
parse_probe_log.py — 解析云拨测日志，输出逐探测点原始证据（判定分层）

设计原则（关键）：
  - TCP/UDP：出确定性判定（判据已验证可靠）
  - HTTP：只输出原始证据 + 风险信号，标 verdict="NEED_AGENT_REVIEW"，不自行下 HIT/MISS
    原因：HTTP 暴露判定尚未定型，存在「泛应答服务器」「阿里云 IP 拦截页」等干扰，需 agent 结合
    响应头/Location/探测点分布研判，不能只看状态码 2xx/3xx（会误报）。

固化的解析要点（已踩坑）：
  1. 一次只查一个 task-id（逗号分隔多 ID 会报 invalid character）
  2. DescribeSiteMonitorLog 的 Data 是 JSON 字符串，需二次 json.loads
  3. DNS 的 ips 字段可能带尾逗号，split 后 strip 过滤空串
  4. TCP 判定：errorCode 为空 且 tcpConnectTime 有真实值 → OPEN；errorCode 非空(常见 611)/含
     i/o timeout|connection refused|no suitable address found → CLOSED
     [MUST] 严禁用 TotalTime>=0 或 status!="error" 判 OPEN（失败时 TotalTime 仍被填超时时长、
     TCP 的 status 恒空，会导致 100% 误判 OPEN）
  5. 轮询：拨测有时延，Data 为空重试（默认每 5s、最多 6 次）

HTTP 风险信号（供 agent 研判，本脚本只标不判）：
  - aliyun_block_page: Location 含 wanwang.aliyun.com / ipvisit_stop（阿里云禁止 IP 直接访问拦截页 → 大概率未暴露）
  - probe_isp_all_alibaba: 探测点 ISP 全是 465（阿里云内网视角，对阿里云 ECS 源站可能失真）
  - http_code: 逐点状态码（agent 判 2xx/3xx 时需排除上面两种干扰，并结合是否泛应答）

用法：
  SKILL_SESSION_ID=<sid> python3 parse_probe_log.py --taskids taskids.json --out probe-evidence.json
"""
import argparse
import json
import os
import subprocess
import sys
import time

SESSION_ID = os.environ.get("SKILL_SESSION_ID", "")
UA = f"AlibabaCloud-Agent-Skills/ddos-origin-exposure-detector/{SESSION_ID}"

POLL_INTERVAL = 5
POLL_MAX = 6
TCP_FAIL_HINTS = ["i/o timeout", "connection refused", "no suitable address found", "connection reset"]
BLOCK_HINTS = ["wanwang.aliyun.com", "ipvisit_stop"]


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def query_log(task_id):
    """查一个 task 的 ProbeLog，返回逐探测点 list（已二次解析 Data）；Data 空返回 None。"""
    rc, out, err = run(["aliyun", "cms", "describe-site-monitor-log",
                        "--task-ids", task_id, "--metric-name", "ProbeLog",
                        "--user-agent", UA])
    if rc != 0:
        return None, f"query-error: {err[:150]}"
    try:
        d = json.loads(out)
    except Exception as e:
        return None, f"outer-json-error: {e}"
    data = d.get("Data") or ""
    if not data:
        return None, "empty"
    try:
        points = json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        return None, f"data-json-error: {e}"
    return points, None


def poll_log(task_id):
    """带重试轮询。"""
    for _ in range(POLL_MAX):
        pts, status = query_log(task_id)
        if pts is not None:
            return pts, None
        if status != "empty":
            return None, status
        time.sleep(POLL_INTERVAL)
    return None, "pending-after-max-poll"


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def judge_tcp_point(p):
    """TCP/UDP 单点确定性判定。返回 'OPEN'|'CLOSED'。"""
    err = str(p.get("errorCode") or "").strip()
    msg = str(p.get("message") or "").lower()
    tct = _num(p.get("tcpConnectTime"))
    if err and err not in ("0", "0.0", ""):
        return "CLOSED"
    if any(h in msg for h in TCP_FAIL_HINTS):
        return "CLOSED"
    if tct is not None and tct > 0:
        return "OPEN"
    return "CLOSED"


def parse_dns_point(p):
    raw = p.get("ips") or p.get("ip") or ""
    if isinstance(raw, str):
        ips = [x.strip() for x in raw.split(",") if x.strip()]
    else:
        ips = [str(x).strip() for x in raw if str(x).strip()]
    return ips


def http_signals(points):
    """汇总 HTTP 任务的风险信号（供 agent 研判）。"""
    isps = [str(p.get("isp") or p.get("ispName") or "") for p in points]
    all_alibaba = bool(isps) and all(i == "465" for i in isps)
    block = False
    codes = []
    for p in points:
        code = _num(p.get("HTTPResponseCode"))
        codes.append(int(code) if code is not None else None)
        loc = str(p.get("redirectUrl") or p.get("location") or p.get("Location") or "")
        errmsg = str(p.get("errorMessage") or p.get("message") or "")
        if any(h in loc for h in BLOCK_HINTS) or any(h in errmsg for h in BLOCK_HINTS):
            block = True
    return {
        "http_codes": codes,
        "probe_isps": isps,
        "signal_aliyun_block_page": block,
        "signal_probe_isp_all_alibaba": all_alibaba,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taskids", default="taskids.json")
    ap.add_argument("--out", default="probe-evidence.json")
    args = ap.parse_args()

    with open(args.taskids) as f:
        created = json.load(f).get("created", [])

    out = {"dns": [], "http": [], "l4": [], "errors": []}

    for item in created:
        group = item["group"]
        name = item["name"]
        tid = item["task_id"]
        meta = item.get("meta", {})
        pts, err = poll_log(tid)
        if pts is None:
            out["errors"].append({"name": name, "group": group, "task_id": tid, "error": err})
            continue

        if group == "s1_dns":
            per_point = []
            hit_any = False
            origins = set(meta.get("origins", []))
            for p in pts:
                ips = parse_dns_point(p)
                inter = sorted(set(ips) & origins)
                if inter:
                    hit_any = True
                per_point.append({"isp": p.get("isp"), "city": p.get("city"),
                                  "resolved_ips": ips, "hit_origin": inter})
            out["dns"].append({
                "name": name, "domain": meta.get("domain"),
                "origins": sorted(origins),
                "verdict": "HIT" if hit_any else "MISS",  # DNS 判定确定：解析 IP ∩ 源站 IP
                "evidence": per_point,
            })

        elif group == "s2_http":
            sig = http_signals(pts)
            out["http"].append({
                "name": name, "domain": meta.get("domain"),
                "origin_ip": meta.get("origin_ip"), "port": meta.get("port"),
                "scheme": meta.get("scheme"),
                "verdict": "NEED_AGENT_REVIEW",  # HTTP 不自行下结论
                "review_hint": ("按 SKILL 规则研判：命中需满足 http_code∈2xx/3xx 且 "
                                "非阿里云拦截页(signal_aliyun_block_page=false) 且 "
                                "非泛应答(需换随机 Host 复验) 且 探测点非全阿里云"),
                "signals": sig,
                "raw_points": pts,
            })

        elif group == "s2_l4":
            per_point = [{"isp": p.get("isp"), "city": p.get("city"),
                          "verdict": judge_tcp_point(p),
                          "errorCode": p.get("errorCode"),
                          "tcpConnectTime": p.get("tcpConnectTime"),
                          "message": str(p.get("message") or "")[:120]} for p in pts]
            open_any = any(x["verdict"] == "OPEN" for x in per_point)
            out["l4"].append({
                "name": name, "origin_ip": meta.get("origin_ip"),
                "backend_port": meta.get("backend_port"),
                "protocol": meta.get("protocol", "tcp"),
                "verdict": "HIT" if open_any else "MISS",  # TCP/UDP 判定确定
                "evidence": per_point,
            })

    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    dns_hit = sum(1 for x in out["dns"] if x["verdict"] == "HIT")
    l4_hit = sum(1 for x in out["l4"] if x["verdict"] == "HIT")
    print(f"[DONE] 写入 {args.out}", file=sys.stderr)
    print(f"  DNS: {len(out['dns'])} 项, HIT {dns_hit}", file=sys.stderr)
    print(f"  HTTP: {len(out['http'])} 项 (全部 NEED_AGENT_REVIEW，见 signals 研判)", file=sys.stderr)
    print(f"  L4(TCP/UDP): {len(out['l4'])} 项, HIT {l4_hit}", file=sys.stderr)
    if out["errors"]:
        print(f"  取日志失败: {len(out['errors'])} 项", file=sys.stderr)


if __name__ == "__main__":
    main()
