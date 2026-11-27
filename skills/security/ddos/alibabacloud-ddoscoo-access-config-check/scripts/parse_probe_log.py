#!/usr/bin/env python3
"""
parse_probe_log.py — 解析云监控拨测日志，输出 C1/C4 的逐探测点证据

固化的解析要点（均为官方文档字段 + 已踩坑验证）：
  1. [MUST] 一次只查一个 --task-ids（逗号分隔多 ID 会报 invalid character）
  2. [MUST] DescribeSiteMonitorLog 的 Data 是 JSON 字符串，需二次 json.loads；不是 Datapoints
  3. DNS 的 ips 字段可能带尾逗号（"1.2.3.4,"），split 后要 strip 并过滤空串
  4. [MUST] 判定成功只看 errorCode + HTTPResponseCode：
     官方文档里 errorCode 是整数，且**没有 errorMessage 字段**，所以不能靠错误文本判失败原因；
     更严禁用 TotalTime>=0 或 status!="error" 判成功 —— 失败时 TotalTime 仍会被填成超时时长，
     用那两个条件会把所有失败点误判为成功
  5. 拨测有时延：Data 为空要轮询（默认每 5s、最多 6 次）
  6. 文档确认的可用字段：HTTPResponseCode / TotalTime / tcpConnectTime / HTTPConnectTime /
     HTTPDNSTime / SSLConnectTime / errorCode / ips / isp / ispCN / ispEN / city / cityCN / cityEN /
     countryCN / countryEN / provinceCN / provinceEN / localDns / suorceIp(官方拼写如此) / timestamp

能力边界（重要）：云拨测 DNS 任务返回的是**最终解析 IP**，不返回完整 CNAME 链。
所以 C1 的「首跳 CNAME 是否等于高防 CNAME」必须由 check_local.py 的 dig 链路 + config 比对给出；
本脚本的 C1 只补充多地视角：有没有哪个地区把域名解析到了源站 IP（= 该地区绕过了高防）。

用法：
  SKILL_SESSION_ID=<sid> SKILL_VERSION=<ver> python3 parse_probe_log.py --taskids taskids.json --config access-config.json --out probe-evidence.json
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

# [MUST] C1/C3 的判定逻辑只有一份实现，在 check_local.py 里。云拨测只是**另一个观测源**：
# 把 DNSRaw 还原成与 resolve_chain() 同构的 chain 结构后直接喂给同一批判定函数。
# 绝不在这里重写一套 C1/C3 判定 —— 两套逻辑迟早会给出互相矛盾的结论。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_local import (judge_c1, judge_c3, classify_ips, find_scheduler_rule, norm_name)

SKILL_NAME = "alibabacloud-ddoscoo-access-config-check"
SESSION_ID = os.environ.get("SKILL_SESSION_ID", "").strip()


def _skill_version():
    """版本只认两个来源：SKILL_VERSION 环境变量，或本技能 references/manifest.json 的顶层 version。"""
    env = os.environ.get("SKILL_VERSION", "").strip()
    if env:
        return env
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "references", "manifest.json")
    try:
        with open(path) as f:
            v = json.load(f).get("version")
    except Exception:
        return ""
    return v.strip() if isinstance(v, str) else ""


SKILL_VERSION = _skill_version()
if not SESSION_ID or not SKILL_VERSION:
    # UA 规范要求取值缺失时停止，不得臆造或借用其他技能的版本/会话 ID
    sys.stderr.write(
        "[ERROR] UA 必需取值缺失，已停止（不会臆造）：\n"
        "        SKILL_SESSION_ID = %s（需本次会话新生成的 32 位小写十六进制）\n"
        "        skill-version    = %s（需来自本技能 references/manifest.json 顶层非空 version）\n"
        % (SESSION_ID or "<empty>", SKILL_VERSION or "<empty>"))
    raise SystemExit(2)

# UA 含空格，传给 CLI 时必须整体加双引号
UA = 'AlibabaCloud-Agent-Skills/%s/%s skill-version/%s' % (SKILL_NAME, SESSION_ID, SKILL_VERSION)

POLL_INTERVAL = 5
POLL_MAX = 6
SLOW_MS_DEFAULT = 2000
DNS_SLOW_MS = 500


def log(msg):
    print(msg, file=sys.stderr)


def run(cmd, timeout=45):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout after %ss" % timeout
    except OSError as e:
        return -1, "", "exec-failed: %s" % e


def query_log(task_id, start_time="", end_time=""):
    """查一个 task 的 ProbeLog；返回 (points|None, status)。status='empty' 表示还没出结果，需继续轮询。

    [MUST] 必须显式传 --start-time/--end-time。不传时服务端只按它自己的默认近窗返回，
    探测任务是几十分钟前建的就一律拿到空 Data —— 现象是「任务建成、日志为空、
    全部记 NOT_DETECTED」，很容易被误读成「域名解析不出来」。时间格式 "%Y-%m-%d %H:%M:%S"。
    """
    cmd = ["aliyun", "cms", "describe-site-monitor-log",
           "--task-ids", task_id, "--metric-name", "ProbeLog", "--user-agent", UA]
    if start_time:
        cmd += ["--start-time", start_time]
    if end_time:
        cmd += ["--end-time", end_time]
    rc, out, err = run(cmd)
    if rc != 0:
        return None, "query-error: %s" % (err or out)[:200]
    try:
        d = json.loads(out)
    except Exception as e:
        return None, "outer-json-error: %s" % e
    data = d.get("Data")
    if not data:
        return None, "empty"
    try:
        points = json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        return None, "data-json-error: %s" % e
    if isinstance(points, dict):
        points = [points]
    if not isinstance(points, list):
        return None, "unexpected-data-shape: %s" % type(points).__name__
    return points, None


def poll_log(task_id, start_time="", end_time=""):
    for _ in range(POLL_MAX):
        pts, status = query_log(task_id, start_time, end_time)
        if pts is not None:
            return pts, None
        if status != "empty":
            return None, status
        time.sleep(POLL_INTERVAL)
    return None, "pending-after-max-poll(%sx%ss)" % (POLL_MAX, POLL_INTERVAL)


def num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def first_present(d, keys, default=""):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def point_location(p):
    """逐点地理/运营商信息。字段名取官方文档确认过的拼写（含 suorceIp 这个官方拼写错误）。"""
    return {
        "country": first_present(p, ["countryEN", "countryCN", "country"]),
        "province": first_present(p, ["provinceEN", "provinceCN", "province"]),
        "city": first_present(p, ["cityEN", "cityCN", "city"]),
        "isp": first_present(p, ["ispEN", "ispCN", "ispName", "isp"]),
        "local_dns": first_present(p, ["localDns", "localDNS"]),
        "source_ip": first_present(p, ["suorceIp", "sourceIp", "suorceIP"]),
        "city_code": str(first_present(p, ["city"], "")),
        "isp_code": str(first_present(p, ["isp"], "")),
    }


def parse_dns_ips(p):
    raw = p.get("ips")
    if raw is None:
        raw = p.get("ip")
    if isinstance(raw, list):
        vals = [str(x) for x in raw]
    else:
        vals = str(raw or "").split(",")
    return sorted(set(x.strip().rstrip(",") for x in vals if x and x.strip()))


def chain_from_dnsraw(p, domain):
    """
    把云拨测 DNS 的 DNSRaw 还原成与 check_local.resolve_chain() **同构**的 chain。

    [MUST] DNSRaw 是整段有序应答，管道分隔，形如：
        "a.com CNAME b.aliyunddos0018.com TTL 600|b.aliyunddos0018.com A 1.2.3.4 TTL 10|any: type 41 string (...)|"
    所以云拨测**能**证明首跳 CNAME 和整条链的层级 —— 早前脚本里写的
    「云拨测 DNS 只返回最终 IP，不返回 CNAME 链」是错的，那句话曾把 C1/C3 不必要地
    推回本地 dig（单出口、且本机在企业代理后有失真风险）。

    OPT 伪段（"any: type 41 string ..."）不是答案记录，必须跳过。
    """
    raw = str(p.get("DNSRaw") or "")
    cur = norm_name(domain)
    cnames, ips_v4, ips_v6, loop, recs = [], [], [], False, []
    for part in raw.split("|"):
        t = part.strip()
        if not t or t.lower().startswith("any:") or "OPT PSEUDOSECTION" in t or "EDNS" in t:
            continue
        tk = t.split()
        if len(tk) < 3:
            continue
        owner, rtype, target = norm_name(tk[0]), tk[1].upper(), tk[2]
        recs.append({"owner": owner, "type": rtype, "target": target})
        if rtype == "CNAME":
            n = norm_name(target)
            if n and n != owner and n not in cnames:
                cnames.append(n)
            elif n in cnames:
                loop = True
        elif rtype == "A":
            ips_v4.append(target)
        elif rtype == "AAAA":
            ips_v6.append(target)

    # 与独立的 cnames 字段交叉校验：DNSRaw 缺失/被截断时用它兜住首跳
    field_cnames = [norm_name(x) for x in str(p.get("cnames") or "").split(",") if x.strip()]
    field_cnames = [c for c in field_cnames if c]
    crosscheck = None
    if field_cnames and cnames and field_cnames[0] != cnames[0]:
        crosscheck = {"dnsraw_first_hop": cnames[0], "cnames_field_first_hop": field_cnames[0]}
    if not cnames and field_cnames:
        cnames = field_cnames
    if not ips_v4 and not ips_v6:
        ips_v4 = parse_dns_ips(p)

    # [MUST] 必须区分两种「拿不到链」，它们的结论完全相反：
    #   (a) 探测点自身失败（errorCode 非 0，或压根没返回 DNSRaw）→ 观测没做成 → NOT_DETECTED
    #   (b) 探测**成功**（errorCode 0）但应答段里只有 OPT 伪段、没有任何 CNAME/A/AAAA
    #       → 观测做成了，答案就是「公网无解析记录」→ 必须让 judge 走 FAIL_NO_RECORD
    # 曾把 (b) 也设成 error，结果 youyitestwaf.qq.com 这种「域名根本没解析」的真发现
    # 被降级成 NOT_DETECTED（未检测），本地兜底侧反而判对了 FAIL_NO_RECORD。
    ec = error_code_of(p)
    raw_present = bool(str(p.get("DNSRaw") or "").strip())
    answer_empty = raw_present and not cnames and not ips_v4 and not ips_v6 and not field_cnames
    if ec is not None:
        chain_error = "云拨测该点探测失败（errorCode=%s）" % ec
    elif not raw_present and not parse_dns_ips(p):
        chain_error = "云拨测未返回 DNSRaw，且无 ips 字段，无法判定该点解析情况"
    else:
        chain_error = None

    return {
        "resolver": str(p.get("dnsServer") or "") or "cloud-probe-default",
        "answer_empty": answer_empty,
        "probe_error_code": ec,
        "cnames": cnames,
        "first_hop": cnames[0] if cnames else None,
        "terminal_name": cnames[-1] if cnames else cur,
        "ips_v4": sorted(set(ips_v4)),
        "ips_v6": sorted(set(ips_v6)),
        "loop_detected": loop,
        "truncated": False,
        "error": chain_error,
        "records": recs,
        "cname_field_crosscheck": crosscheck,
        "perspective": "CLOUD_MULTI_VANTAGE",
    }


def error_code_of(p):
    """errorCode 官方定义为整数；空/0/None 视为无错误。绝不读不存在的 errorMessage 来判成败。"""
    ec = p.get("errorCode")
    if ec in (None, "", 0, "0"):
        return None
    try:
        return int(ec)
    except (TypeError, ValueError):
        return str(ec)


def is_mainland_point(loc, vantage_map):
    """
    分组依据优先级：**探测日志自己的 country 字段优先**，选点时的归组作为兑底。

    为什么反过来：日志里的 countryCN/countryEN 是该探测点**实际跑在哪**的事实，
    而 vantage_map 是我们事前的分组意图。曾因为选点侧把扁平键 Country.en 读成国家编码，
    杭州移动的点被归入海外组；那时日志里明明写着 country=China。
    两者不一致时以日志为准，并把不一致记下来供人工复核。
    """
    c = str(loc.get("country") or "").strip()
    from_log = None
    if c.lower() in ("china", "mainland china") or c in ("中国", "中国大陆"):
        from_log = True
    elif c:
        from_log = False
    key = (loc.get("city_code") or "", loc.get("isp_code") or "")
    from_map = vantage_map.get(key)
    if from_log is not None:
        if from_map is not None and from_map != from_log:
            loc["grouping_disagreement"] = {"probe_log_country": c, "vantage_group_mainland": from_map}
        return from_log
    return from_map


def judge_c1_point(ips, origin_ips, antiddos_ips, expected_cnames):
    """单点 DNS 结论：只看「最终解析 IP 落在哪」。"""
    hit_origin = sorted(set(ips) & set(origin_ips))
    hit_ddos = sorted(set(ips) & set(antiddos_ips))
    others = sorted(set(ips) - set(origin_ips) - set(antiddos_ips))
    if not ips:
        return "FAIL_NO_RECORD", "该探测点未解析到任何 IP", {"hit_origin": [], "hit_antiddos_ip": [], "others": []}
    if hit_origin:
        return "FAIL_A_RECORD_TO_ORIGIN", ("该探测点解析到源站 IP %s，该地区流量绕过高防直达源站"
                                           % ",".join(hit_origin)), \
               {"hit_origin": hit_origin, "hit_antiddos_ip": hit_ddos, "others": others}
    if hit_ddos:
        return "PASS_TO_ANTIDDOS_IP", "解析到高防 IP %s" % ",".join(hit_ddos), \
               {"hit_origin": [], "hit_antiddos_ip": hit_ddos, "others": others}
    return "NEED_AGENT_REVIEW", ("解析到 %s，既不是配置的源站 IP 也不是本机已知的高防实例 IP；"
                                 "可能是高防集群 IP/调度器/CDN/WAF。这只是「最终 IP 落点」的桶归类，"
                                 "落点桶只有 源站/高防IP/其他 三个，分不出服务商；"
                                 "首跳 CNAME 是否等于高防 CNAME(%s) 由 DNSRaw 还原的链路定论，见 chain 字段"
                                 % (",".join(others), ",".join(expected_cnames[:3]) or "-")), \
           {"hit_origin": [], "hit_antiddos_ip": [], "others": others}


def judge_c4_points(points, slow_ms):
    """一组（内地或海外）HTTP 探测点的健康判定。"""
    ok, bad, slow = [], [], []
    for p in points:
        code = num(p.get("HTTPResponseCode"))
        code = int(code) if code is not None else None
        ec = error_code_of(p)
        total = num(p.get("TotalTime"))
        loc = point_location(p)
        rec = {"location": loc, "http_code": code, "error_code": ec,
               "total_time_ms": total,
               "dns_time_ms": num(p.get("HTTPDNSTime")),
               "ssl_time_ms": num(p.get("SSLConnectTime")),
               "tcp_connect_time_ms": num(p.get("tcpConnectTime")),
               "http_connect_time_ms": num(p.get("HTTPConnectTime")),
               "redirect_count": p.get("redirectCount")}
        # 成功判据：状态码 2xx/3xx 且无 errorCode。不看 TotalTime、不看 status
        if code is not None and 200 <= code < 400 and ec is None:
            ok.append(rec)
            if total is not None and total > slow_ms:
                slow.append(rec)
        else:
            bad.append(rec)
    n = len(points)
    if n == 0:
        verdict, detail = "NOT_DETECTED", "该分组没有拿到任何探测点结果"
    elif not bad:
        verdict = "HEALTHY"
        detail = "%s/%s 个探测点访问正常（2xx/3xx 且无 errorCode）" % (len(ok), n)
        if slow:
            verdict = "WARN_SLOW"
            detail += "；其中 %s 个点 TotalTime > %sms（最慢 %sms）" % (
                len(slow), slow_ms, max(x["total_time_ms"] for x in slow))
    elif not ok:
        verdict, detail = "UNAVAILABLE", "%s/%s 个探测点全部失败" % (len(bad), n)
    else:
        verdict, detail = "PARTIAL", "%s/%s 个探测点失败，%s 个正常" % (len(bad), n, len(ok))
    return {"verdict": verdict, "detail": detail, "total_points": n,
            "ok": ok, "failed": bad, "slow": slow}


def divergence_signals(dom, ovs):
    """跨地域差异才是诊断价值所在：只报两半各自的健康度是没用的。"""
    sigs = []
    dv, ov = dom.get("verdict"), ovs.get("verdict")
    dom_bad_codes = [x["http_code"] for x in dom.get("failed", []) if x["http_code"]]
    ovs_bad_codes = [x["http_code"] for x in ovs.get("failed", []) if x["http_code"]]
    dom_ok = dv in ("HEALTHY", "WARN_SLOW")
    ovs_ok = ov in ("HEALTHY", "WARN_SLOW")
    if ov == "NOT_DETECTED":
        sigs.append({"signal": "OVERSEAS_NOT_DETECTED",
                     "hint": "海外没有探测点或探测失败，海外健康度未知；禁止在报告里写成「海外正常」"})
    elif not ovs_ok and dom_ok:
        sigs.append({"signal": "OVERSEAS_FAIL_MAINLAND_OK",
                     "hint": "内地正常、海外异常。优先排查：证书链不完整(海外校验更严)、"
                             "调度器海外加速线路未生效、实例 region 与业务地域不匹配"
                             "(国际版实例配在 ap-southeast-1 但解析指向内地高防)、海外回源超时"})
    elif not dom_ok and ovs_ok:
        sigs.append({"signal": "MAINLAND_FAIL_OVERSEAS_OK",
                     "hint": "海外正常、内地异常。优先排查：ICP 备案未完成导致内地拦截、"
                             "内地线路解析异常(C1 的 WARN_POINT_INCONSISTENT)、"
                             "业务面向内地但用的是国际版实例"})
    elif not dom_ok and not ovs_ok:
        if any(c and c >= 500 for c in dom_bad_codes + ovs_bad_codes):
            sigs.append({"signal": "BOTH_FAIL_5XX",
                         "hint": "全球均返回 5xx，指向回源失败：常见于源站 ACL 未放通高防回源网段、"
                                 "源站端口/协议配错、源站已宕。源站 ACL 处置见 "
                                 "alibabacloud-ddos-origin-exposure-detector 的建议"})
        else:
            sigs.append({"signal": "BOTH_FAIL",
                         "hint": "全球均不可达：站点宕机、高防转发规则未生效、或域名解析整体异常(见 C1)"})
    elif dom.get("verdict") == "PARTIAL" or ovs.get("verdict") == "PARTIAL":
        sigs.append({"signal": "PARTIAL_BY_POINT",
                     "hint": "部分探测点失败：多为区域性运营商链路问题或探测点自身抖动，"
                             "建议对失败点单独复测后再定性"})
    return sigs


def overall_c4(dom, ovs):
    """内地/海外两半合成一个 C4 结论：任一半不可用即 FAIL，任一半未知即 NOT_DETECTED。"""
    order = {"UNAVAILABLE": 4, "PARTIAL": 3, "NOT_DETECTED": 2, "WARN_SLOW": 1, "HEALTHY": 0}
    dv, ov = dom.get("verdict", "NOT_DETECTED"), ovs.get("verdict", "NOT_DETECTED")
    if order.get(dv, 2) >= 3 or order.get(ov, 2) >= 3:
        return "FAIL"
    if order.get(dv, 2) == 2 or order.get(ov, 2) == 2:
        return "NOT_DETECTED"
    if order.get(dv, 2) == 1 or order.get(ov, 2) == 1:
        return "WARN"
    return "PASS"


def main():
    ap = argparse.ArgumentParser(description="解析云拨测日志，输出 C1/C4 证据")
    ap.add_argument("--taskids", required=True, help="create_probes.py 产出的 taskids.json")
    ap.add_argument("--config", default="", help="access-config.json（可选，用于补充高防 IP/源站 IP）")
    ap.add_argument("--out", default="probe-evidence.json")
    ap.add_argument("--local-evidence", default="",
                    help="check_local.py 产出的 local-evidence.json。C2 的结论只存在于该文件里，"
                         "缺省时自动在 --taskids 同目录下找 local-evidence.json")
    ap.add_argument("--slow-ms", type=float, default=SLOW_MS_DEFAULT, help="TotalTime 超过此值标记为慢")
    ap.add_argument("--start-time", default="", help='日志查询起始时间，格式 "YYYY-MM-DD HH:MM:SS"。'
                                                     '缺省则按 taskids.json 的 generated_at 前推 15 分钟')
    ap.add_argument("--end-time", default="", help='日志查询结束时间，格式同上。缺省为当前时间')
    ap.add_argument("--window-pad-min", type=int, default=15,
                    help="自动时间窗在 generated_at 之前额外前推的分钟数（默认 15）")
    args = ap.parse_args()

    with open(args.taskids) as f:
        tj = json.load(f)
    created = tj.get("created") or []
    vantage = tj.get("vantage") or {}
    cfg = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            cfg = json.load(f)
    global_ddos_ips = set(cfg.get("antiddos_ips") or [])

    # 选点时我们自己知道每个 city/isp 属于内地还是海外，比事后猜 country 字段可靠
    vantage_map = {}
    for x in vantage.get("domestic") or []:
        vantage_map[(str(x.get("city")), str(x.get("isp")))] = True
    for x in vantage.get("overseas") or []:
        vantage_map[(str(x.get("city")), str(x.get("isp")))] = False

    # ---------- 时间窗：必须覆盖任务创建时刻，否则一律拿到空 Data ----------
    now = datetime.datetime.now()
    start_time, end_time = args.start_time, args.end_time
    if not start_time:
        gen = str(tj.get("generated_at") or "").strip()
        base = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                base = datetime.datetime.strptime(gen, fmt)
                break
            except ValueError:
                continue
        if base is None:
            base = now - datetime.timedelta(hours=2)
            log("  [WARN] taskids.json 没有可解析的 generated_at，时间窗回退为「近 2 小时」；"
                "若任务更早创建，请显式传 --start-time，否则日志会全空并被误记 NOT_DETECTED")
        start_time = (base - datetime.timedelta(minutes=args.window_pad_min)).strftime("%Y-%m-%d %H:%M:%S")
    if not end_time:
        end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    log("  日志时间窗: %s ~ %s" % (start_time, end_time))

    out = {"generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
           "log_window": {"start_time": start_time, "end_time": end_time},
           "probe_mode": tj.get("probe_mode") or "cloud",
           "vantage": vantage, "c1": [], "c3_cloud": [], "c4": [], "errors": []}

    for item in created:
        group, name, tid = item.get("group"), item.get("name"), item.get("task_id")
        meta = item.get("meta") or {}
        pts, err = poll_log(tid, start_time, end_time)
        if pts is None:
            out["errors"].append({"group": group, "name": name, "task_id": tid, "error": err})
            log("  [ERR] %s %s: %s" % (group, name, err))
            continue

        if group in ("dns_chain", "c1_dns"):
            # [MUST] 云拨测是 C1/C3 的**首选**观测源：多点（国内+海外）、各点自带 dnsServer 留证，
            # 不受本机单出口与企业代理的失真影响。本地 dig 只在云拨测不可用时兜底。
            origin_ips = set(meta.get("origin_ips") or [])
            ddos_ips = set(meta.get("antiddos_ips") or []) | global_ddos_ips
            expected = meta.get("expected_cnames_all") or []
            # judge_c1/judge_c3 要的 cfg 形状，全部由 meta + config 拼出，与 check_local 同构
            web_cnames = set((cfg.get("expected_cnames") or {}).get("web_rules") or []) or set(expected)
            sched_cnames = set(meta.get("scheduler_cnames") or []) | \
                set((cfg.get("expected_cnames") or {}).get("scheduler_cnames") or [])
            judge_cfg = {
                "domain": meta.get("domain"),
                "cname": (meta.get("expected_web_cname") or "").strip(),
                # 无七层规则的降级/无基线对象（create_probes.py --extra-domains 合成）。
                # 不带这个标记，cname 为空会让 judge_c1 落到第3类「规则存在但未关联高防 IP」，
                # 而正确结论是第1类「本账号根本没有这条规则」——两者的处置动作完全不同。
                "baseline_free": bool(meta.get("baseline_free")),
                "region": meta.get("region"),
                "_web_cnames": web_cnames,
                "_sched_cnames": sched_cnames,
                "_antiddos_ips": sorted(ddos_ips),
                "_region_instance_count": meta.get("region_instance_count")
                    if meta.get("region_instance_count") is not None
                    else (cfg.get("region_instance_count") or {}).get(meta.get("region"), 0),
            }
            sched_rules = cfg.get("scheduler_rules") or []
            # [MUST] 两套结论必须分开存：ip_verdicts 来自「最终 IP 落在哪个桶」，
            # chain_verdicts 来自 judge_c1 的首跳 CNAME 比对。曾复用同一个 verdicts 变量，
            # 结果 observed_ip_landing 被打成 C1 的链上结论（逐点明明是 NEED_AGENT_REVIEW，
            # 聚合却写 NOT_APPLICABLE_NO_CNAME_ASSIGNED），两列互相污染。
            per_point, ip_verdicts, chain_verdicts, c3_points, c3_verdicts = [], [], [], [], []
            for p in pts:
                dom = meta.get("domain") or ""
                chain = chain_from_dnsraw(p, dom)
                ips = chain["ips_v4"] + chain["ips_v6"] or parse_dns_ips(p)
                ip_cls = classify_ips(ips, origin_ips, ddos_ips)
                sched_rule, _hit = find_scheduler_rule(chain["cnames"], sched_rules)
                # C1：与本地路径同一套判定函数，比对首跳 CNAME
                v, d = judge_c1(judge_cfg, chain, ip_cls, sched_rule)
                ip_v = judge_c1_point(ips, origin_ips, ddos_ips, expected)[0]
                # C3：同一份链，判高防在第几层
                v3, d3, hops3 = judge_c3(judge_cfg, chain, ip_cls, sched_rule)
                loc = point_location(p)
                mainland = is_mainland_point(loc, vantage_map)
                chain_verdicts.append(v)
                ip_verdicts.append(ip_v)
                c3_verdicts.append(v3)
                per_point.append({"location": loc, "resolved_ips": ips,
                                  "chain": chain["cnames"], "first_hop": chain["first_hop"],
                                  "dns_server": chain["resolver"],
                                  # 透出「探测成功但应答为空」这一区分，否则报告无法说明
                                  # FAIL_NO_RECORD 与 NOT_DETECTED 的差别从何而来
                                  "probe_succeeded_answer_empty": chain["answer_empty"],
                                  "probe_error_code": chain["probe_error_code"],
                                  "cname_field_crosscheck": chain["cname_field_crosscheck"],
                                  "error_code": error_code_of(p),
                                  "verdict": v, "detail": d,
                                  "ip_landing": ip_v,
                                  "classification": ip_cls,
                                  "perspective": "CLOUD_MULTI_VANTAGE",
                                  "is_mainland": mainland})
                c3_points.append({"location": loc, "verdict": v3, "detail": d3, "hops": hops3,
                                  "chain": chain["cnames"], "dns_server": chain["resolver"],
                                  "perspective": "CLOUD_MULTI_VANTAGE", "is_mainland": mainland})
            bypass = [x for x in per_point if x["ip_landing"] == "FAIL_A_RECORD_TO_ORIGIN"]
            if bypass:
                agg = "FAIL_A_RECORD_TO_ORIGIN"
                agg_detail = "%s/%s 个探测点把域名解析到了源站 IP，这些地区绕过高防：%s" % (
                    len(bypass), len(per_point),
                    "; ".join("%s %s -> %s" % (x["location"].get("country") or "-",
                                               x["location"].get("isp") or "-",
                                               ",".join(x["classification"]["hit_origin"])) for x in bypass))
            elif ip_verdicts and all(v == "PASS_TO_ANTIDDOS_IP" for v in ip_verdicts):
                agg, agg_detail = "PASS_TO_ANTIDDOS_IP", "%s 个探测点均解析到高防 IP" % len(ip_verdicts)
            elif "FAIL_NO_RECORD" in ip_verdicts:
                n = ip_verdicts.count("FAIL_NO_RECORD")
                agg = "FAIL_NO_RECORD" if n == len(ip_verdicts) else "WARN_POINT_INCONSISTENT"
                agg_detail = "%s/%s 个探测点未解析到记录" % (n, len(ip_verdicts))
            elif len(set(ip_verdicts)) > 1:
                agg = "WARN_POINT_INCONSISTENT"
                agg_detail = "各探测点 IP 落点结论不一致(%s)，需按地区分别定性，不能取多数派" % ",".join(sorted(set(ip_verdicts)))
            else:
                agg = ip_verdicts[0] if ip_verdicts else "NOT_DETECTED"
                agg_detail = ("全部探测点 IP 落点一致(%s)。落点桶只有 源站/高防IP/其他 三个，"
                              "NEED_AGENT_REVIEW 表示落在「其他」；首跳 CNAME 已由云拨测 DNSRaw 定论，"
                              "见 verdict 字段，不必再退回本地 dig" % agg)

            # C1 聚合改成基于**首跳 CNAME 链**（云拨测 DNSRaw 已给出整条链）。
            # 上面的 IP 落点聚合保留为 observed_ip_landing，作为辅证而非判据。
            if not chain_verdicts:
                c1_agg, c1_detail = "NOT_DETECTED", "云拨测 DNS 任务没有返回任何探测点数据"
            elif len(set(chain_verdicts)) == 1:
                c1_agg = chain_verdicts[0]
                c1_detail = "%s/%s 个探测点结论一致：%s" % (len(chain_verdicts), len(chain_verdicts),
                                                          per_point[0]["detail"])
            else:
                c1_agg = "WARN_POINT_INCONSISTENT"
                c1_detail = ("各探测点首跳链结论不一致(%s)，须按地区分别定性，**不得取多数派**：%s"
                             % (",".join(sorted(set(chain_verdicts))),
                                "; ".join("%s %s -> %s(%s)" % (
                                    x["location"].get("country") or "-", x["location"].get("isp") or "-",
                                    x["first_hop"] or "无CNAME", x["verdict"]) for x in per_point)))

            if not c3_verdicts:
                c3_agg, c3_detail = "NOT_DETECTED", "云拨测 DNS 任务没有返回任何探测点数据"
            elif len(set(c3_verdicts)) == 1:
                c3_agg = c3_verdicts[0]
                c3_detail = "%s/%s 个探测点结论一致：%s" % (len(c3_verdicts), len(c3_verdicts),
                                                           c3_points[0]["detail"])
            else:
                c3_agg = "WARN_POINT_INCONSISTENT"
                c3_detail = ("各探测点的层级结论不一致(%s)——这通常正是分区域解析/绕行造成的，"
                             "须按地区分别定性，**不得取多数派**：%s"
                             % (",".join(sorted(set(c3_verdicts))),
                                "; ".join("%s %s -> %s" % (
                                    x["location"].get("country") or "-", x["location"].get("isp") or "-",
                                    x["verdict"]) for x in c3_points)))

            # ---------- C1 前置条件（第3类）：无 CNAME 基线时 C1 不适用 ----------
            configured_cname = (meta.get("expected_web_cname") or "").strip().lower().rstrip(".")
            observed_landing = agg
            observed_landing_detail = agg_detail
            if not configured_cname:
                # 云拨测的 IP 落点仍是有效证据，但只能交给 C3 定性：
                # 没有基线时把它报成 C1 FAIL，等于把「还没配好」说成「配错了」
                handoff = ""
                if bypass:
                    handoff = ("。[重要] 解析落到源站说明流量绕过高防直达源站——"
                               "该结论应记入 C3(FAIL_DIRECT_TO_ORIGIN)，而不是 C1")
                c1_agg = "NOT_APPLICABLE_NO_CNAME_ASSIGNED"
                c1_detail = ("该域名的转发规则未关联高防 IP，DescribeWebRules.Cname 为空，"
                             "C1 没有可比对的基线，故 C1 不适用。处置：先关联高防 IP 生成 CNAME，再切 DNS。"
                             "云拨测观测到的 IP 落点结论：%s%s" % (observed_landing_detail, handoff))
            out["c1"].append({"name": name, "task_id": tid, "domain": meta.get("domain"),
                              "configured_domain": meta.get("configured_domain"),
                              "expected_web_cname": meta.get("expected_web_cname"),
                              "c1_applicable": bool(configured_cname),
                              "observed_ip_landing": observed_landing,
                              "observed_ip_landing_detail": observed_landing_detail,
                              "verdict": c1_agg, "detail": c1_detail,
                              "perspective": "CLOUD_MULTI_VANTAGE",
                              "note": "云拨测 DNS 的 DNSRaw 回的是整段有序应答，首跳 CNAME 与整条链均可证；"
                                      "本地 dig 仅在云拨测不可用时兜底（单出口、且本机在企业代理后有失真风险）",
                              "evidence": per_point})
            out.setdefault("c3_cloud", []).append(
                {"name": name, "task_id": tid, "domain": meta.get("domain"),
                 "configured_domain": meta.get("configured_domain"),
                 "verdict": c3_agg, "detail": c3_detail,
                 "perspective": "CLOUD_MULTI_VANTAGE",
                 "note": "C3 层级判定与 C1 共用同一个云拨测 DNS 任务，不额外计费；"
                         "判定函数与 check_local.py 完全同一份实现",
                 "evidence": c3_points})
            log("  [C1] %s -> %s%s" % (meta.get("domain"), c1_agg,
                                        "" if configured_cname else "（IP 落点观测: %s）" % observed_landing))
            log("  [C3] %s -> %s（云拨测）" % (meta.get("domain"), c3_agg))

        elif group == "c4_http":
            dom_pts, ovs_pts, unk_pts = [], [], []
            for p in pts:
                loc = point_location(p)
                m = is_mainland_point(loc, vantage_map)
                (dom_pts if m is True else ovs_pts if m is False else unk_pts).append(p)
            dom = judge_c4_points(dom_pts, args.slow_ms)
            ovs = judge_c4_points(ovs_pts, args.slow_ms)
            unk = judge_c4_points(unk_pts, args.slow_ms)
            if not vantage.get("overseas_available", True):
                ovs = {"verdict": "NOT_DETECTED",
                       "detail": "本次没有可用的海外探测点（见 vantage.note），海外健康度未知",
                       "total_points": 0, "ok": [], "failed": [], "slow": []}
            sigs = divergence_signals(dom, ovs)
            out["c4"].append({"name": name, "task_id": tid, "domain": meta.get("domain"),
                              "address": item.get("address"), "scheme": meta.get("scheme"),
                              "port": meta.get("port"), "proxy_type": meta.get("proxy_type"),
                              "domestic": dom, "overseas": ovs,
                              "unattributed": unk if unk_pts else None,
                              "divergence_signals": sigs,
                              "verdict": overall_c4(dom, ovs)})
            log("  [C4] %s 内地=%s 海外=%s" % (meta.get("domain"), dom["verdict"], ovs["verdict"]))
            for s in sigs:
                log("       信号 %s: %s" % (s["signal"], s["hint"][:80]))

    # ---------- C2：本脚本不判定 C2，结论只在 check_local.py 的输出里 ----------
    # [MUST] 四项检查的结论原先分散在两个文件，Agent 在云拨测模式下很容易只读 probe-evidence.json，
    # 于是 C2 整项静默消失 —— 那比 NOT_DETECTED 更糟，因为报告看起来是完整的。
    # 这里把 C2 合并进来；合并不到就明确报错，绝不假装 C2 通过。
    le_path = args.local_evidence
    if not le_path:
        guess = os.path.join(os.path.dirname(os.path.abspath(args.taskids)), "local-evidence.json")
        if os.path.exists(guess):
            le_path = guess
    # [MUST] C2 必须按**本次探测范围**过滤。check_local.py 不带 --domains 时会判定全账号域名，
    # 而 C1/C3/C4 只覆盖被探测的那些；直接全量合并会让同一份证据里出现「C2: 43 项」
    # 挨着「C1: 1 项」，读者无法判断覆盖率分母到底是哪个。
    probed_domains = set()
    for key in ("c1", "c3_cloud", "c4"):
        for row in (out.get(key) or []):
            for dk in ("domain", "configured_domain"):
                if row.get(dk):
                    probed_domains.add(str(row[dk]))
    c2_rows = []
    c2_out_of_scope = 0
    if le_path and os.path.exists(le_path):
        try:
            with open(le_path, encoding="utf-8") as f:
                le = json.load(f)
            for dom in (le.get("domains") or []):
                c2 = dom.get("c2") or {}
                if not c2:
                    continue
                dnames = {str(x) for x in (dom.get("domain"), dom.get("configured_domain")) if x}
                if probed_domains and not (dnames & probed_domains):
                    c2_out_of_scope += 1
                    continue
                c2_rows.append({"domain": dom.get("domain"),
                                "configured_domain": dom.get("configured_domain"),
                                "verdict": c2.get("verdict"),
                                "bound_cert_name": c2.get("bound_cert_name"),
                                "end_date": c2.get("end_date"),
                                "days_left": c2.get("days_left"),
                                "expired_flag": c2.get("expired_flag"),
                                "detail": c2.get("detail"),
                                "source": "check_local.py"})
            out["c2"] = c2_rows
            out["c2_source"] = le_path
            out["c2_out_of_scope"] = c2_out_of_scope
        except Exception as e:
            out["c2"] = []
            out["c2_error"] = "读取 %s 失败: %s" % (le_path, e)
    else:
        out["c2"] = []
        out["c2_error"] = ("未提供 --local-evidence，且在 --taskids 同目录下没找到 local-evidence.json")


    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    c1_fail = sum(1 for x in out["c1"] if x["verdict"].startswith("FAIL"))
    c1_warn = sum(1 for x in out["c1"] if x["verdict"].startswith("WARN"))
    c1_review = sum(1 for x in out["c1"] if x["verdict"] == "NEED_AGENT_REVIEW")
    c1_na = sum(1 for x in out["c1"] if x["verdict"].startswith("NOT_APPLICABLE"))
    # [MUST] overall_c4() 返回的是 FAIL/WARN/PASS/NOT_DETECTED，而分组级才是
    # UNAVAILABLE/PARTIAL/WARN_SLOW/NOT_DETECTED。旧实现只比后一套词表，
    # 导致 C4 整体 FAIL 时汇总打印「非 HEALTHY 0」，把问题全吞了。
    c4_bad = sum(1 for x in out["c4"] if x["verdict"] in ("FAIL", "WARN", "NOT_DETECTED"))
    c4_group_bad = sum(1 for x in out["c4"] for g in ("domestic", "overseas")
                       if (x.get(g) or {}).get("verdict") in ("UNAVAILABLE", "PARTIAL", "WARN_SLOW", "NOT_DETECTED"))
    c4_split_void = sum(1 for x in out["c4"]
                        if (x.get("domestic") or {}).get("total_points", 0) == 0
                        or (x.get("overseas") or {}).get("total_points", 0) == 0)
    log("")
    if out.get("c2"):
        c2_na = sum(1 for x in out["c2"] if str(x.get("verdict", "")).startswith("NOT_APPLICABLE"))
        c2_nd = sum(1 for x in out["c2"] if x.get("verdict") == "NOT_DETECTED")
        c2_bad = sum(1 for x in out["c2"] if str(x.get("verdict", "")).startswith("FAIL"))
        c2_warn = sum(1 for x in out["c2"] if str(x.get("verdict", "")).startswith("WARN"))
        log("  C2: %s 项（来自 check_local.py，本脚本不判定 C2）FAIL %s / WARN %s / 不适用 %s / 未检测 %s"
            % (len(out["c2"]), c2_bad, c2_warn, c2_na, c2_nd))
        if c2_out_of_scope:
            log("       已按本次探测范围过滤掉 %s 个未被探测域名的 C2 结论，"
                "以免与 C1/C3/C4 的覆盖率分母不一致（全量结果见 %s）"
                % (c2_out_of_scope, le_path))
    else:
        log("  [MUST] C2 没有任何结论：%s。"
            "\n         check_local.py 是 C2 的**唯一**判定入口（本脚本与 create_probes.py 都不判 C2），"
            "\n         且在 ProbeMode=cloud 下也必须运行。请先跑 "
            "\n         `python3 scripts/check_local.py --config <access-config.json> "
            "--out <local-evidence.json>`，"
            "\n         再用 --local-evidence 指向它重跑本脚本。"
            "\n         **绝不**把缺失的 C2 写成「证书正常」或直接省略该章节。"
            % out.get("c2_error"))
    log("[DONE] 写入 %s" % args.out)
    log("  C1: %s 项（适用 %s / FAIL %s / WARN %s / 需研判 %s / 前置条件不满足不适用 %s）"
        % (len(out["c1"]), len(out["c1"]) - c1_na, c1_fail, c1_warn, c1_review, c1_na))
    if c1_na:
        log("  [MUST] 上述 %s 项 C1 不适用（无 CNAME 基线），报告中必须带上处置提示，"
            "既不能记 FAIL 也不能记 PASS；其 IP 落点观测交给 C3 定性" % c1_na)
    c3c = out.get("c3_cloud") or []
    c3_bad = sum(1 for x in c3c if str(x.get("verdict", "")).startswith(("FAIL", "WARN")))
    c3_na = sum(1 for x in c3c if str(x.get("verdict", "")).startswith("NOT_APPLICABLE"))
    c3_nd = sum(1 for x in c3c if x.get("verdict") == "NOT_DETECTED")
    c3_split = sum(1 for x in c3c
                   if not any(e.get("is_mainland") is True for e in (x.get("evidence") or []))
                   or not any(e.get("is_mainland") is False for e in (x.get("evidence") or [])))
    log("  C3(云拨测): %s 项（FAIL/WARN %s / 不适用 %s / 未检测 %s）"
        % (len(c3c), c3_bad, c3_na, c3_nd))
    if c3_nd:
        log("  [MUST] 有 %s 项 C3 云拨测未取到探测点数据。先排查时间窗（--start-time/--end-time）"
            "是否覆盖任务创建时刻，再考虑降级本地 dig；**不得**把未检测写成「高防在第一层」" % c3_nd)
    if c3_split:
        log("  [MUST] 有 %s 项 C3 的探测点缺国内或缺海外一侧 —— 分区域解析差异正是 C3 要抓的，"
            "单侧证据不足以下「第一层」结论，报告须写明缺哪一侧" % c3_split)
    log("  C4: %s 项（整体结论 FAIL/WARN/NOT_DETECTED 共 %s；分组级异常 %s 个）"
        % (len(out["c4"]), c4_bad, c4_group_bad))
    if c4_split_void:
        log("  [MUST] 有 %s 项的内地或海外组一个探测点都没有 —— C4 的目的是全球访问健康，"
            "两组点缺一不可；这些项的「内地 vs 海外」对比不成立，"
            "报告必须明说哪一半未检测，绝不能写成「另一半正常」" % c4_split_void)
    if out["errors"]:
        log("  [MUST] 取日志失败 %s 项，必须逐条列入报告未检测清单，不得当作 PASS：%s"
            % (len(out["errors"]), ",".join(x["name"] for x in out["errors"])))
    failed_tasks = tj.get("failed") or []
    if failed_tasks:
        log("  [MUST] 创建阶段失败 %s 项（见 taskids.json），同样列入未检测清单" % len(failed_tasks))


if __name__ == "__main__":
    main()
