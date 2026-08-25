#!/usr/bin/env python3
"""
create_probes.py — 批量创建云拨测任务（根治构造类错误）

固化以下已踩坑并验证的确定性规则：
  1. HTTPS 探测：TaskType 用 HTTP，Address 用 https:// 前缀（TaskType 不支持 HTTPS，会报 TaskType does not exists）
  2. TCP/UDP：--address 只填 IP（不带端口），端口放 --options-json 的 port 字段（带端口报 illegal port）
  3. HTTP Host 头：走 --options-json 的 header 字段 "Host: <域名>"（无 host 键）
  4. [MUST] 探测点强制选非阿里云运营商（电信/联通/移动），避免 isp=465 阿里云内网节点对阿里云 ECS 源站系统性漏报
  5. 相邻任务间隔 1.5s；限流类错误 2s/4s/8s 指数退避，最多重试 3 次
  6. TaskId 取自 CreateResultList[0].TaskId
  7. IPv6 源站不在此创建（云拨测不支持），由本地探测处理

探测点来源：调 describe-site-monitor-isp-city-list，挑选电信(132)/联通(232)/移动(5)各一个 IPV4ProbeCount>0 的城市，
构造 --isp-cities。若查询失败则回退到 --random-isp-city 3 并在输出中告警（可能落到 isp=465）。

用法：
  SKILL_SESSION_ID=<sid> python3 create_probes.py --tasks tasks.json --out taskids.json

tasks.json 结构（由调用方或 build 步骤准备）：
  {"s1_dns":[{"name","domain"}...],
   "s2_http":[{"name","domain","origin_ip","port","scheme"}...],
   "s2_l4":[{"name","origin_ip","backend_port","protocol"}...]}   # protocol=tcp|udp, 仅 IPv4

本脚本会创建一次性拨测任务（有极小费用），不修改任何高防配置。
"""
import argparse
import json
import os
import subprocess
import sys
import time

SESSION_ID = os.environ.get("SKILL_SESSION_ID", "")
UA = f"AlibabaCloud-Agent-Skills/ddos-origin-exposure-detector/{SESSION_ID}"

INTERVAL = 1.5
BACKOFF = [2, 4, 8]
THROTTLE_HINTS = ["Throttling", "QuotaExceeded", "RequestLimitExceeded", "ServiceUnavailable"]

# 目标运营商 ISP 编码（非阿里云）：电信 132 / 联通 232 / 移动 5
PREFERRED_ISPS = ["132", "232", "5"]


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def pick_isp_cities():
    """
    查 describe-site-monitor-isp-city-list，为电信/联通/移动各挑 1 个 IPV4ProbeCount>0 的城市。
    返回 (isp_cities_json_str_or_None, note)
    """
    rc, out, err = run(["aliyun", "cms", "describe-site-monitor-isp-city-list",
                        "--ipv4", "true", "--view-all", "true", "--user-agent", UA])
    if rc != 0:
        return None, f"describe-site-monitor-isp-city-list 失败，回退 random-isp-city: {err[:150]}"
    try:
        items = json.loads(out).get("IspCityList", {}).get("IspCity", [])
    except Exception as e:
        return None, f"解析探测点列表失败，回退 random-isp-city: {e}"

    chosen = []
    for isp in PREFERRED_ISPS:
        cand = [it for it in items
                if str(it.get("Isp")) == isp and int(it.get("IPV4ProbeCount", 0) or 0) > 0]
        if cand:
            # 选 IPv4 探针最多的城市
            cand.sort(key=lambda x: int(x.get("IPV4ProbeCount", 0) or 0), reverse=True)
            chosen.append({"city": str(cand[0]["City"]), "isp": isp})
    if len(chosen) < 2:
        return None, f"非阿里云运营商探测点不足（仅 {len(chosen)} 个），回退 random-isp-city"
    return json.dumps(chosen, ensure_ascii=False), f"已选非阿里云探测点: {chosen}"


def vantage_args(isp_cities):
    """返回探测点相关的命令参数列表。"""
    if isp_cities:
        return ["--isp-cities", isp_cities]
    return ["--random-isp-city", "3"]


def create_task(cmd_args, name):
    """执行创建，带限流退避重试。返回 (ok, task_id_or_None, err)。"""
    attempt = 0
    while True:
        rc, out, err = run(cmd_args)
        blob = out + err
        if rc == 0:
            try:
                tid = json.loads(out).get("CreateResultList", [{}])[0].get("TaskId", "")
            except Exception:
                tid = ""
            if tid:
                return True, tid, None
            return False, None, f"created but no TaskId: {out[:150]}"
        # 限流退避
        if any(h in blob for h in THROTTLE_HINTS) and attempt < len(BACKOFF):
            wait = BACKOFF[attempt]
            print(f"  [THROTTLE] {name} 退避 {wait}s（第 {attempt+1} 次重试）", file=sys.stderr)
            time.sleep(wait)
            attempt += 1
            continue
        return False, None, blob.strip()[:200]


def build_dns_cmd(t, vantage):
    return (["aliyun", "cms", "create-instant-site-monitor",
             "--address", t["domain"], "--task-type", "DNS",
             "--task-name", t["name"][:100]] + vantage + ["--user-agent", UA])


def build_http_cmd(t, vantage):
    # HTTPS 用 HTTP + https:// 前缀
    address = f'{t["scheme"]}://{t["origin_ip"]}:{t["port"]}'
    opts = json.dumps({"header": f'Host: {t["domain"]}', "time_out": 5000}, ensure_ascii=False)
    return (["aliyun", "cms", "create-instant-site-monitor",
             "--address", address, "--task-type", "HTTP",
             "--task-name", t["name"][:100]] + vantage +
            ["--options-json", opts, "--user-agent", UA])


def build_l4_cmd(t, vantage):
    ttype = "UDP" if str(t.get("protocol", "tcp")).lower() == "udp" else "TCP"
    opts = json.dumps({"port": t["backend_port"], "time_out": 5000})
    return (["aliyun", "cms", "create-instant-site-monitor",
             "--address", t["origin_ip"], "--task-type", ttype,
             "--task-name", t["name"][:100]] + vantage +
            ["--options-json", opts, "--user-agent", UA])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks.json")
    ap.add_argument("--out", default="taskids.json")
    args = ap.parse_args()

    if not SESSION_ID:
        print("[WARN] SKILL_SESSION_ID 为空", file=sys.stderr)

    with open(args.tasks) as f:
        tasks = json.load(f)

    isp_cities, note = pick_isp_cities()
    print(f"[VANTAGE] {note}", file=sys.stderr)
    vantage = vantage_args(isp_cities)
    vantage_desc = "isp-cities(非阿里云)" if isp_cities else "random-isp-city-3(可能含阿里云节点,已告警)"

    results = {"vantage": vantage_desc, "vantage_note": note, "created": [], "failed": []}

    def emit(group, t, builder):
        cmd = builder(t, vantage)
        ok, tid, err = create_task(cmd, t["name"])
        if ok:
            results["created"].append({"group": group, "name": t["name"], "task_id": tid, "meta": t})
            print(f"  [OK] {group} {t['name']} -> {tid}", file=sys.stderr)
        else:
            results["failed"].append({"group": group, "name": t["name"], "error": err, "meta": t})
            print(f"  [FAIL] {group} {t['name']}: {err}", file=sys.stderr)
        time.sleep(INTERVAL)

    for t in tasks.get("s1_dns", []):
        emit("s1_dns", t, build_dns_cmd)
    for t in tasks.get("s2_http", []):
        emit("s2_http", t, build_http_cmd)
    for t in tasks.get("s2_l4", []):
        emit("s2_l4", t, build_l4_cmd)

    with open(args.out, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 写入 {args.out}: 成功 {len(results['created'])}, 失败 {len(results['failed'])}", file=sys.stderr)
    if results["failed"]:
        print("[FAILED 明细]", file=sys.stderr)
        for x in results["failed"]:
            print(f"  - {x['name']}: {x['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
