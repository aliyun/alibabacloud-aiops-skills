#!/usr/bin/env python3
"""
create_probes.py — 批量创建云监控一次性拨测任务（C1 多地 DNS 解析 + C4 内地/海外访问健康）

与 alibabacloud-ddos-origin-exposure-detector 的关键差别：
  - 那边探的是「源站 IP:端口 是否可直连」，这边探的是「域名本身」——
    C1 用 DNS 任务看域名解析到哪、C4 用 HTTP 任务看用户实际访问是否健康。
  - 本技能不探测源站，源站暴露检测请走 origin-exposure-detector。

固化的已验证规则（踩坑记录）：
  1. TaskType 只支持 HTTP/PING/TCP/UDP/DNS；探 HTTPS 必须 --task-type HTTP + address 用 https:// 前缀
     （写 HTTPS 会报 TaskType does not exists）
  2. TaskId 在 CreateResultList[0].TaskId，不是 Data.TaskId
  3. --task-name 长度 4~100，需先做字符白名单清洗
  4. --isp-cities 一旦设置，--random-isp-city 失效；两者互斥
  5. 相邻任务间隔 1.5s；限流类错误 2s/4s/8s 退避，最多重试 3 次，重试耗尽后记为 failed 而不是跳过
  6. [MUST] 海外探测点只能运行时从 describe-site-monitor-isp-city-list 按 Country 字段筛，
     官方文档没有公布海外 city/isp 编码示例，硬编码任何编码都是猜 —— 筛不到就把 C4-海外记 NOT_DETECTED，
     绝不能因为「没探」而报「海外健康」

用法：
  SKILL_SESSION_ID=<sid> SKILL_VERSION=<ver> python3 create_probes.py --config access-config.json --out taskids.json
  python3 create_probes.py --config access-config.json --dry-run          # 只看计划与费用面，不创建
  python3 create_probes.py --config access-config.json --checks c1 --overseas-count 3 --out taskids.json

会创建一次性拨测任务（按量计费，费用极小），不修改任何高防/DNS/证书配置，不创建持久监控。
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

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

INTERVAL = 1.5
BACKOFF = [2, 4, 8]
# 内地真实用户视角优先三大运营商：电信 132 / 联通 232 / 移动 5
# （阿里云自身节点 isp=465 不代表用户访问，C4 要的是真实用户视角）
PREFERRED_DOMESTIC_ISPS = ["132", "232", "5"]
THROTTLE_HINTS = ["Throttling", "QuotaExceeded", "RequestLimitExceeded", "ServiceUnavailable"]
NOT_ACTIVATED_HINTS = ["not activated", "service not opened", "not opened", "Forbidden.NotActivated"]
PLUGIN_PARSE_HINTS = ["invalid character", "looking for beginning of value"]
INTERNAL_HINTS = ["InternalError", "SDK.ServerError", "HttpCode 500", "HttpCode 502", "HttpCode 503"]


def log(msg):
    print(msg, file=sys.stderr)


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout after %ss" % timeout
    except OSError as e:
        return -1, "", "exec-failed: %s" % e


def classify_error(blob):
    """按 SKILL.md 的 Cloud Probe Error Handling Decision Tree 归类。"""
    b = blob or ""
    if any(h in b for h in NOT_ACTIVATED_HINTS):
        return "A_SERVICE_NOT_ACTIVATED", "云监控拨测服务未开通 → 自动回退本地探测，C4 内地/海外对比记 NOT_DETECTED"
    if any(h in b for h in PLUGIN_PARSE_HINTS):
        return "B_PLUGIN_PARSE", ("aliyun-cli-cms 插件解析 bug（非 JSON 语法错）→ 走 "
                                  "references/acceptance-criteria.md 的补救梯度：升级插件 → 泛化 RPC(PascalCase) → 临时文件")
    if any(h in b for h in THROTTLE_HINTS):
        return "C_THROTTLING", "限流 → 已退避重试；重试耗尽则记为 failed 并列入未检测清单，不得跳过后续项"
    if any(h in b for h in INTERNAL_HINTS):
        return "D_INTERNAL_ERROR", "服务端内部错误 → 重试一次后回退本地探测该单项"
    return "UNKNOWN", "未归类错误，原文已记录；不得当作 PASS"


def sanitize_task_name(name):
    """--task-name 限制 4~100 字符，且实践中只接受字母数字与连字符。"""
    s = re.sub(r"[^a-z0-9-]+", "-", str(name).lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if len(s) > 88:
        s = s[:88].rstrip("-")
    while len(s) < 4:
        s = (s + "-chk")[:100]
    return s


def flat_field(item, base, subs):
    """
    [MUST] DescribeSiteMonitorISPCityList 返回的是**扁平点号键**：
      "Country.en": "China", "Country.zh_CN": "中国", "Country": "629",
      "CityName.en": "Hangzhou", "CityName.zh_CN": "杭州市", "IspName.en": "China-Mobile"
    不是嵌套对象。旧实现用 item.get("Country") 读到的是国家**编码** "629"，
    拿它去比 "china" 永远不成立 → 253 个探测点全被判成海外、内地池为空。
    两种形态都要能读，且优先读带后缀的扁平键。
    """
    if not isinstance(item, dict):
        return ""
    for sub in subs:
        v = item.get("%s.%s" % (base, sub))
        if v not in (None, ""):
            return str(v).strip()
    v = item.get(base)
    if isinstance(v, dict):
        for sub in subs:
            if v.get(sub) not in (None, ""):
                return str(v[sub]).strip()
    return ""


def country_of(item):
    en = flat_field(item, "Country", ("en", "EN"))
    zh = flat_field(item, "Country", ("zh_CN", "zh-CN"))
    return en, zh


def is_mainland(item):
    """只认国家名（en/zh），不认国家编码——编码写死就是猜。"""
    en, zh = country_of(item)
    return en.lower() in ("china", "mainland china") or zh in ("中国", "中国大陆")


def pick_vantage(domestic_count, overseas_count):
    """
    运行时探测点选择。返回 (isp_cities_json|None, info_dict)。
    海外点按 Country 字段筛，不硬编码任何 city/isp 编码。
    """
    info = {"source": "random-isp-city", "domestic": [], "overseas": [],
            "overseas_available": False, "note": ""}
    rc, out, err = run(["aliyun", "cms", "describe-site-monitor-isp-city-list",
                        "--ipv4", "true", "--view-all", "true", "--user-agent", UA])
    if rc != 0:
        info["note"] = "describe-site-monitor-isp-city-list 失败（%s），回退 --random-isp-city %s；" \
                       "此时无法保证海外视角" % ((err or "")[:150], max(domestic_count, 3))
        return None, info
    try:
        d = json.loads(out)
    except Exception as e:
        info["note"] = "解析探测点列表失败（%s），回退 random-isp-city" % e
        return None, info
    items = (d.get("IspCityList") or {}).get("IspCity") or []
    if not items:
        info["note"] = "探测点列表为空，回退 random-isp-city"
        return None, info

    def probe_count(it):
        try:
            return int(it.get("IPV4ProbeCount") or 0)
        except (TypeError, ValueError):
            return 0

    usable = [it for it in items if probe_count(it) > 0]
    domestic_pool = [it for it in usable if is_mainland(it)]
    overseas_pool = [it for it in usable if not is_mainland(it)]

    chosen_dom = []
    for isp in PREFERRED_DOMESTIC_ISPS:
        cand = sorted([it for it in domestic_pool if str(it.get("Isp")) == isp],
                      key=probe_count, reverse=True)
        if cand:
            chosen_dom.append(cand[0])
        if len(chosen_dom) >= domestic_count:
            break
    if len(chosen_dom) < domestic_count:
        rest = sorted([it for it in domestic_pool if it not in chosen_dom], key=probe_count, reverse=True)
        chosen_dom.extend(rest[: domestic_count - len(chosen_dom)])

    # 海外：按国家分散，每国取探针最多的一个点
    by_country = {}
    for it in overseas_pool:
        en, zh = country_of(it)
        key = en or zh or "unknown"
        cur = by_country.get(key)
        if cur is None or probe_count(it) > probe_count(cur):
            by_country[key] = it
    chosen_ovs = sorted(by_country.values(), key=probe_count, reverse=True)[:overseas_count] if overseas_count else []

    chosen = chosen_dom + chosen_ovs
    if not chosen:
        info["note"] = "未选到任何可用探测点（IPV4ProbeCount>0），回退 random-isp-city"
        return None, info

    def label(it):
        en, zh = country_of(it)
        cname = flat_field(it, "CityName", ("zh_CN", "en")) or str(it.get("City") or "")
        iname = flat_field(it, "IspName", ("zh_CN", "en")) or str(it.get("Isp") or "")
        return {"city": str(it.get("City")), "isp": str(it.get("Isp")),
                "country": en or zh, "country_en": en, "country_zh": zh,
                "city_name": cname, "isp_name": iname,
                "region": flat_field(it, "Region", ("zh_CN", "en")),
                "area": flat_field(it, "Area", ("zh_CN", "en")),
                "ipv4_probe_count": probe_count(it)}

    info["domestic"] = [label(x) for x in chosen_dom]
    info["overseas"] = [label(x) for x in chosen_ovs]
    info["overseas_available"] = bool(chosen_ovs)
    info["source"] = "isp-cities"
    notes = []
    if domestic_count and not chosen_dom:
        notes.append("[E] 没选到内地探测点（Country.en/zh_CN == China 且 IPV4ProbeCount>0）→ "
                     "C4-内地 必须记 NOT_DETECTED，禁止报「内地健康」")
    if overseas_count and not chosen_ovs:
        notes.append("[E] 没选到海外探测点（Country != China 且 IPV4ProbeCount>0）→ "
                     "C4-海外 必须记 NOT_DETECTED，禁止报「海外健康」")
    if notes:
        notes.append("C4 的目的是全球访问健康，两组点缺一不可；只要有一组为空，"
                     "「内地 vs 海外」对比就不成立，报告必须明说哪一半未检测")
    info["note"] = " ".join(notes)
    payload = [{"city": str(x.get("City")), "isp": str(x.get("Isp"))} for x in chosen]
    return json.dumps(payload, ensure_ascii=False), info


def vantage_args(isp_cities, fallback_n):
    if isp_cities:
        return ["--isp-cities", isp_cities]
    return ["--random-isp-city", str(fallback_n)]


def create_task(cmd, name):
    """带退避重试的创建。返回 (ok, task_id|None, err, error_class, action)。"""
    attempt = 0
    while True:
        rc, out, err = run(cmd)
        blob = (out or "") + (err or "")
        if rc == 0:
            try:
                tid = (json.loads(out).get("CreateResultList") or [{}])[0].get("TaskId", "")
            except Exception as e:
                return False, None, "created but TaskId 解析失败: %s" % e, "UNKNOWN", ""
            if tid:
                return True, tid, None, None, None
            return False, None, "created but no TaskId: %s" % out[:150], "UNKNOWN", ""
        ecls, action = classify_error(blob)
        if ecls == "C_THROTTLING" and attempt < len(BACKOFF):
            wait = BACKOFF[attempt]
            log("  [THROTTLE] %s 退避 %ss（第 %s 次重试）" % (name, wait, attempt + 1))
            time.sleep(wait)
            attempt += 1
            continue
        return False, None, blob.strip()[:300], ecls, action


def build_tasks(cfg, domains_filter, checks, wildcard_samples, max_endpoints,
                extra_domains="", extra_region=""):
    """从 config 构造探测任务清单。泛域名不能直接探，需 --wildcard-samples 展开。

    --extra-domains 追加**没有七层规则**的域名：合成一条空规则后走同一套构造逻辑，
    endpoints 为空时下面本来就会回退到默认 https:443，因此不需要另开一条分支。
    """
    web_rules = cfg.get("web_rules") or []
    exp = cfg.get("expected_cnames") or {}
    antiddos_ips = cfg.get("antiddos_ips") or []
    # 与 check_local.py 同一算法：按 region 数实例。config 里没有现成的计数字段。
    region_inst_count = {}
    for i in (cfg.get("instances") or []):
        region_inst_count[i.get("region")] = region_inst_count.get(i.get("region"), 0) + 1
    only = set(d.strip() for d in domains_filter.split(",") if d.strip()) if domains_filter else set()
    samples = [s.strip() for s in wildcard_samples.split(",") if s.strip()]

    extra = [d.strip() for d in (extra_domains or "").split(",") if d.strip()]
    if extra:
        known = set(w.get("domain") or "" for w in web_rules)
        region = extra_region
        if not region:
            for w in web_rules:
                if w.get("region"):
                    region = w.get("region")
                    break
        if not region:
            for i in (cfg.get("instances") or []):
                if i.get("region"):
                    region = i.get("region")
                    break
        web_rules = list(web_rules) + [{
            "domain": d, "cname": "", "endpoints": [],
            "origin_ips_v4": [], "origin_ips_v6": [],
            "region": region, "cert_name": "", "user_cert_name": "", "baseline_free": True,
        } for d in extra if d not in known]
    tasks, skipped = [], []

    for w in web_rules:
        dom = w.get("domain") or ""
        # --extra-domains 是用户显式点名的目标，不受 --domains 过滤器约束
        if only and dom not in only and not w.get("baseline_free"):
            continue
        if dom.startswith("*."):
            parent = dom[2:]
            if not samples:
                skipped.append({"domain": dom, "reason": "泛域名不能直接做 DNS/HTTP 探测，需用户提供子域名清单"
                                                          "或用 --wildcard-samples 抽样，或明确跳过"})
                continue
            targets = ["%s.%s" % (s, parent) for s in samples]
        else:
            targets = [dom]

        origin_ips = (w.get("origin_ips_v4") or []) + (w.get("origin_ips_v6") or [])
        base_meta = {
            "configured_domain": dom,
            "expected_web_cname": w.get("cname") or "",
            "expected_cnames_all": exp.get("all") or [],
            "scheduler_cnames": exp.get("scheduler_cnames") or [],
            "origin_ips": origin_ips,
            "antiddos_ips": antiddos_ips,
            "region": w.get("region"),
            "is_wildcard_sample": dom.startswith("*."),
            # judge_c1 第3类分支要用它说明「该 region 实例数为 0，规则无实例承载，
            # 这正是 Cname 为空的原因」；缺了这句，不适用结论会被误读成「改 DNS 就能修」。
            "region_instance_count": region_inst_count.get(w.get("region"), 0),
            # True = 该域名在本账号没有七层规则，是降级/无基线观测对象。
            # 报告与判定都要据此标注：C1 只能是 NOT_APPLICABLE_NO_WEB_RULE，
            # 任何结论都不得呈现为接入验收结论。
            "baseline_free": bool(w.get("baseline_free")),
        }

        for t in targets:
            slug = sanitize_task_name("ddoscoo-acc-" + t.replace(".", "-"))
            # [MUST] 一个 DNS 任务同时服务 C1 和 C3：云拨测 DNS 的 DNSRaw 字段回的是**整段有序应答**
            # （形如 "域名 CNAME 高防CNAME TTL 600|高防CNAME A 1.2.3.4 TTL 10|"），
            # 因此首跳 CNAME、整条链的层级、最终 IP 都能从云端多点拿到。
            # C1 判首跳是否等于高防 CNAME，C3 判高防在第几层——同一份证据，不要为 C3 再建一个任务。
            if "c1" in checks or "c3" in checks:
                tasks.append({"group": "dns_chain", "name": sanitize_task_name(slug + "-dns"),
                              "cmd_kind": "dns",
                              "serves": sorted(x for x in ("c1", "c3") if x in checks),
                              "meta": dict(base_meta, domain=t)})
            if "c4" in checks:
                eps = w.get("endpoints") or []
                # TLS 类 proxy_type 集合须与 fetch_config.py / check_local.py 保持一致：
                # websockets(wss) 走 TLS，漏掉它会让该端点既不进 https 也不进 http，
                # 最终回退到默认的 https:443，探错端口
                https_eps = [e for e in eps
                             if e.get("proxy_type") in ("https", "websockets", "wss") or e.get("port") == 443]
                http_eps = [e for e in eps if e.get("proxy_type") in ("http", "websocket", "ws")]
                picked = (https_eps or http_eps or [{"proxy_type": "https", "port": 443}])[:max_endpoints]
                seen_ports = set()
                for ep in picked:
                    port = ep.get("port")
                    if port in seen_ports:
                        continue
                    seen_ports.add(port)
                    ptype = str(ep.get("proxy_type") or "").lower()
                    # websocket/ws 与 http 共用 TCP 端口与 HTTP 握手，用 HTTP 任务即可覆盖
                    scheme = "http" if ptype in ("http", "websocket", "ws") else "https"
                    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
                    address = "%s://%s%s/" % (scheme, t, "" if default_port else ":%s" % port)
                    tasks.append({"group": "c4_http", "name": sanitize_task_name("%s-%s-%s" % (slug, scheme, port)),
                                  "cmd_kind": "http", "address": address,
                                  "meta": dict(base_meta, domain=t, scheme=scheme, port=port,
                                               proxy_type=ptype)})
    return tasks, skipped


def build_cmd(task, vantage, agent_group):
    if task["cmd_kind"] == "dns":
        return (["aliyun", "cms", "create-instant-site-monitor",
                 "--address", task["meta"]["domain"], "--task-type", "DNS",
                 "--task-name", task["name"], "--agent-group", agent_group] + vantage +
                ["--user-agent", UA])
    # HTTP/HTTPS 都用 --task-type HTTP；HTTPS 靠 address 的 https:// 前缀触发 TLS 握手
    return (["aliyun", "cms", "create-instant-site-monitor",
             "--address", task["address"], "--task-type", "HTTP",
             "--task-name", task["name"], "--agent-group", agent_group] + vantage +
            ["--options-json", json.dumps({"time_out": 5000}), "--user-agent", UA])


def main():
    ap = argparse.ArgumentParser(description="批量创建云监控一次性拨测任务（C1 DNS / C4 HTTP）")
    ap.add_argument("--config", required=True, help="fetch_config.py 产出的 access-config.json")
    ap.add_argument("--out", default="taskids.json")
    ap.add_argument("--checks", default="c1,c3,c4",
                    help="逗号分隔，可选 c1 / c3 / c4。c1 与 c3 共用同一个云拨测 DNS 任务"
                         "（DNSRaw 同时给出首跳 CNAME 与整条链），不会重复计费；"
                         "c2 只看绑定证书到期、数据源是 cas，从不探测")
    ap.add_argument("--domains", default="", help="可选，只探这些域名")
    ap.add_argument("--domestic-count", type=int, default=3,
                    help="内地探测点数；未明确指定时默认 3 个就够（与海外 3 个对称）")
    ap.add_argument("--overseas-count", type=int, default=3,
                    help="C4 要看的是全球访问健康，默认海外 3 个点（与内地 3 个对称）")
    ap.add_argument("--max-endpoints", type=int, default=2, help="每域名最多探几个端口，控制费用")
    ap.add_argument("--agent-group", default="PC", choices=["PC", "MOBILE"])
    ap.add_argument("--interval", type=float, default=INTERVAL)
    ap.add_argument("--wildcard-samples", default="", help="泛域名展开用的子域前缀，逗号分隔")
    ap.add_argument("--extra-domains", default="",
                    help="无七层转发规则也要探的域名，逗号分隔。这是**追加**而不是过滤："
                         "--domains 只在 web_rules 里筛选，目标域名没有规则时筛不出任何探测对象。"
                         "用于经用户显式同意的降级/无基线公网观测——没有规则可推导端点，"
                         "按默认 https:443 探；C1 判 NOT_APPLICABLE_NO_WEB_RULE，"
                         "C4 拿到真实的公网可达性结论")
    ap.add_argument("--extra-region", default="",
                    help="--extra-domains 的归属地域；留空则从 config 的 web_rules/instances 推断")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不创建任务（用于向用户确认范围与费用面）")
    args = ap.parse_args()

    checks = set(c.strip().lower() for c in args.checks.split(",") if c.strip())
    if not checks <= {"c1", "c3", "c4"}:
        log("[ERROR] --checks 只支持 c1,c3,c4")
        sys.exit(2)
    with open(args.config) as f:
        cfg = json.load(f)

    tasks, skipped = build_tasks(cfg, args.domains, checks, args.wildcard_samples, args.max_endpoints,
                                extra_domains=args.extra_domains, extra_region=args.extra_region)
    if not tasks:
        log("[ERROR] 没有可探测对象（web_rules 为空，或全部是未展开的泛域名）。")
        log("        web_rules 里没有目标域名时，--domains 只是过滤器、筛不出东西；"
            "泛域名要用 --wildcard-samples 展开。")
        log("        若目标域名在本账号根本没有七层规则，而用户已显式同意降级/无基线公网观测，"
            "用 --extra-domains a.example.com,b.example.com 追加（默认按 https:443 探）。")
        for s in skipped:
            log("  - 跳过 %s: %s" % (s["domain"], s["reason"]))
        sys.exit(2)

    interval = args.interval
    result = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "probe_mode": "cloud", "checks": sorted(checks), "dry_run": args.dry_run,
        "agent_group": args.agent_group, "planned": len(tasks),
        "skipped": skipped, "created": [], "failed": [],
    }

    if args.dry_run:
        result["vantage"] = {"source": "not-selected(dry-run)", "domestic": [], "overseas": [],
                             "overseas_available": None,
                             "note": "dry-run 未查询探测点，也未创建任务"}
        result["plan"] = [{"group": t["group"], "name": t["name"],
                           "address": t.get("address") or t["meta"]["domain"],
                           "task_type": "DNS" if t["cmd_kind"] == "dns" else "HTTP",
                           "domain": t["meta"]["domain"]} for t in tasks]
        with open(args.out, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log("[DRY-RUN] 计划创建 %s 个一次性拨测任务（按量计费）：" % len(tasks))
        for p in result["plan"]:
            log("  %s %s -> %s" % (p["task_type"], p["address"], p["name"]))
        if skipped:
            log("[SKIPPED]")
            for s in skipped:
                log("  - %s: %s" % (s["domain"], s["reason"]))
        log("写入 %s（未调用任何创建接口）" % args.out)
        return

    if not shutil.which("aliyun"):
        log("[ERROR] 未找到 aliyun CLI，无法创建云拨测任务。")
        log("        请安装 CLI（见 references/cli-installation-guide.md），或改用 ProbeMode=local：")
        log("        本地路径用 scripts/check_local.py --with-health（C4 只有单出口视角，")
        log("        内地 vs 海外对比必须记 NOT_DETECTED，不能报「海外健康」）。")
        sys.exit(2)
    isp_cities, vinfo = pick_vantage(args.domestic_count, args.overseas_count)
    log("[VANTAGE] source=%s 内地=%s 海外=%s" % (vinfo["source"], len(vinfo["domestic"]), len(vinfo["overseas"])))
    for x in vinfo["domestic"]:
        log("  内地: %s %s/%s (city=%s isp=%s probes=%s)" % (x["country"], x["city_name"], x["isp_name"],
                                                             x["city"], x["isp"], x["ipv4_probe_count"]))
    for x in vinfo["overseas"]:
        log("  海外: %s %s/%s (city=%s isp=%s probes=%s)" % (x["country"], x["city_name"], x["isp_name"],
                                                             x["city"], x["isp"], x["ipv4_probe_count"]))
    if vinfo.get("note"):
        log("[VANTAGE NOTE] %s" % vinfo["note"])

    # [MUST] 选点自检：内地组里不得出现非中国点，海外组里不得出现中国点。
    # 曾因为把扁平键 Country.en 读成国家编码 Country，导致 253 个点全判海外、
    # 杭州移动被归入海外组。分组错了 C4 的全部价值就没了，所以这里硬停，不浪费探测费用。
    bad_dom = [x for x in vinfo["domestic"] if not (str(x.get("country_en") or "").lower()
                                                    in ("china", "mainland china")
                                                    or x.get("country_zh") in ("中国", "中国大陆"))]
    bad_ovs = [x for x in vinfo["overseas"] if (str(x.get("country_en") or "").lower()
                                                in ("china", "mainland china")
                                                or x.get("country_zh") in ("中国", "中国大陆"))]
    if bad_dom or bad_ovs:
        log("[FATAL] 探测点分组自检不通过，已停止（不创建任何探测任务）：")
        for x in bad_dom:
            log("        内地组里的非中国点: %s" % json.dumps(x, ensure_ascii=False))
        for x in bad_ovs:
            log("        海外组里的中国点: %s" % json.dumps(x, ensure_ascii=False))
        log("        原因通常是 DescribeSiteMonitorISPCityList 的字段形态变了"
            "（扁平点号键 vs 嵌套对象），请先修 flat_field/country_of 再跑")
        result["vantage"] = vinfo
        result["fatal"] = "VANTAGE_GROUPING_SELFCHECK_FAILED"
        with open(args.out, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        raise SystemExit(3)
    if args.domestic_count and not vinfo["domestic"]:
        log("[MUST] 内地组为空：C4-内地 记 NOT_DETECTED，「内地 vs 海外」对比不成立")
    if args.overseas_count and not vinfo["overseas"]:
        log("[MUST] 海外组为空：C4-海外 记 NOT_DETECTED，「内地 vs 海外」对比不成立")
    result["vantage"] = vinfo
    vantage = vantage_args(isp_cities, max(args.domestic_count, 3))

    for i, t in enumerate(tasks):
        cmd = build_cmd(t, vantage, args.agent_group)
        ok, tid, err, ecls, action = create_task(cmd, t["name"])
        if ok:
            result["created"].append({"group": t["group"], "name": t["name"], "task_id": tid,
                                      "address": t.get("address") or t["meta"]["domain"],
                                      "task_type": "DNS" if t["cmd_kind"] == "dns" else "HTTP",
                                      "meta": t["meta"]})
            log("  [OK] %s %s -> %s" % (t["group"], t["name"], tid))
        else:
            result["failed"].append({"group": t["group"], "name": t["name"], "error": err,
                                     "error_class": ecls, "action": action, "meta": t["meta"]})
            log("  [FAIL] %s %s: %s" % (t["group"], t["name"], ecls))
            log("         %s" % (err or "")[:200])
            if action:
                log("         处置: %s" % action)
            if ecls == "A_SERVICE_NOT_ACTIVATED":
                # 服务未开通：后续全部不再尝试，交回 agent 走本地探测（决策树 Type A）
                log("[STOP] 云拨测服务未开通，剩余 %s 个任务不再尝试创建。" % (len(tasks) - i - 1))
                result["aborted_remaining"] = [x["name"] for x in tasks[i + 1:]]
                result["fallback_local"] = True
                break
            if ecls == "C_THROTTLING":
                interval = min(interval * 2, 12)
                log("[SLOW] 触发限流，后续调用间隔提升到 %.1fs" % interval)
        time.sleep(interval)

    with open(args.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log("")
    log("[DONE] 写入 %s：成功 %s，失败 %s，计划 %s" % (args.out, len(result["created"]),
                                                      len(result["failed"]), len(tasks)))
    if result.get("fallback_local"):
        log("[MUST] 已回退本地探测；报告需注明「云拨测服务未开通，C4 降级为本地单出口，内地/海外对比 NOT_DETECTED」")
    if result["failed"]:
        log("[MUST] 失败项必须逐条列入报告的未检测清单（Not-Detected List），不得当作 PASS 或健康")


if __name__ == "__main__":
    main()
