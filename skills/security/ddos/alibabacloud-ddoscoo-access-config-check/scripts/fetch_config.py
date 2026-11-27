#!/usr/bin/env python3
"""
fetch_config.py — 拉取代理高防接入配置（config truth），供 C1~C4 判定使用

只做确定性取数 + 结构化，不做任何 PASS/FAIL 判定。

  1. 按 region 全量分页拉取 DescribeInstances / DescribeWebRules / DescribeSchedulerRules
  2. [MUST] describe-web-rules 严禁用 --instance-ids 过滤（实测漏采 80%）；本脚本不提供该开关
  3. [MUST] 每个列表接口做 TotalCount 完整性校验，取回数 != TotalCount 时告警
  4. ProxyTypes[] 展开成 (协议, 端口) 全组合，避免只取第一个端口导致漏检
  5. 源站归一化：RsType=1(域名) 用本地 dig +short 解析；RealServer 可能逗号分隔多个 IP
     源站 IP 仅用于 C1/C3 的「解析结果是否落在源站」比对，本技能不探测源站
  6. 泛域名(*.) 只标记，展开策略交给调用方（需用户确认）
  7. 调度器规则结构化 + RuleType/ValueType/Status 语义翻译，并算出「是否存在生效的高防线路」
  8. 输出 expected_cnames：C1 的比对基准 = web-rule CNAME ∪ scheduler CNAME
  9. 查数字证书管理服务(cas) 拿「高防上绑定的那张证书」的到期时间——这是 C2 的唯一数据源。
     先 ListUserCertificateOrder 列证书；被高防绑定但列表里没带 EndDate 的，再按 CertId 调
     GetUserCertificateDetail 补 EndDate/Expired。解析不到只告警，绝不编造。默认开启，--no-cas 可跳过
     （跳过后 C2 全部记 NOT_DETECTED）。DescribeWebRules[].CertExpireTime 官方标注「暂不使用」，永不读取。

用法：
  SKILL_SESSION_ID=<sid> SKILL_VERSION=<ver> python3 fetch_config.py --regions cn-hangzhou --out access-config.json
  SKILL_SESSION_ID=<sid> SKILL_VERSION=<ver> python3 fetch_config.py --regions cn-hangzhou,ap-southeast-1 --out access-config.json
  SKILL_SESSION_ID=<sid> SKILL_VERSION=<ver> python3 fetch_config.py --regions cn-hangzhou --no-cas --out access-config.json

本脚本只读、无副作用（不创建任何云资源）。
"""
import argparse
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys

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

PAGE_SIZE = 10            # describe-web-rules / describe-scheduler-rules 上限 10
INSTANCE_PAGE_SIZE = 50   # describe-instances 上限 50

RULE_TYPE_LABELS = {
    "2": "阶梯防护(tiered protection)",
    "3": "海外加速(overseas acceleration)",
    "5": "CDN联动(CDN interaction)",
    "6": "云产品联动(cloud product interaction)",
    "8": "安全加速(secure acceleration)",
}
VALUE_TYPE_LABELS = {
    "1": "高防IP(Anti-DDoS IP)",
    "2": "云资源(cloud resource)",
    "3": "加速线路(acceleration line)",
    "5": "CDN域名(CDN domain)",
    "6": "云产品(cloud product)",
    "8": "安全加速(secure acceleration)",
}
STATUS_LABELS = {"0": "未生效(inactive)", "1": "生效(active)"}


def die(msg, code=2):
    print("[ERROR] %s" % msg, file=sys.stderr)
    sys.exit(code)


def run_json(cmd, timeout=60):
    """执行 aliyun 命令并解析 JSON，返回 (dict|None, err|None)。不抛异常。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout after %ss" % timeout
    except OSError as e:
        return None, "exec-failed: %s" % e
    if r.returncode != 0:
        return None, (r.stderr or r.stdout or "nonzero-exit").strip()[:300]
    try:
        return json.loads(r.stdout), None
    except Exception as e:
        return None, "json-parse-failed: %s; stdout=%s" % (e, r.stdout[:200])


def dig_short(domain):
    """本地 dig +short 归一化域名为 IP 列表（只保留 A/AAAA，丢弃 CNAME 行）。"""
    if not shutil.which("dig"):
        return []
    try:
        r = subprocess.run(["dig", "+short", domain], capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    out = []
    for line in r.stdout.strip().splitlines():
        line = line.strip().rstrip(".")
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", line):
            out.append(line)
        elif ":" in line and re.match(r"^[0-9a-fA-F:]+$", line):
            out.append(line)
    return out


def is_ipv6(ip):
    return ":" in str(ip)


def split_multi(val):
    """RealServer 可能是逗号分隔的多个地址。"""
    return [x.strip() for x in str(val or "").split(",") if x.strip()]


def fetch_instances(region):
    action = ["aliyun", "ddoscoo", "describe-instances"]
    base = action + ["--region", region, "--page-size", str(INSTANCE_PAGE_SIZE), "--user-agent", UA]
    d, err = run_json(base + ["--page-number", "1"])
    if d is None:
        print("[ERROR] describe-instances %s: %s" % (region, err), file=sys.stderr)
        return [], err
    tc = int(d.get("TotalCount", 0) or 0)
    insts = d.get("Instances", []) or []
    for p in range(2, int(math.ceil(tc / float(INSTANCE_PAGE_SIZE))) + 1):
        dd, _ = run_json(base + ["--page-number", str(p)])
        if dd:
            insts.extend(dd.get("Instances", []) or [])
    if len(insts) != tc:
        print("[WARN] describe-instances %s: TotalCount=%s 但取回=%s" % (region, tc, len(insts)), file=sys.stderr)
    for i in insts:
        i["_region"] = region
    return insts, None


def fetch_paged(product_action, region, extra_args, list_key):
    """
    通用全量分页 + TotalCount 完整性校验。
    [MUST] extra_args 不得含 --instance-ids（web-rules 会漏采）。
    返回 (list, warning|None)
    """
    base = ["aliyun"] + product_action + ["--region", region] + extra_args + ["--user-agent", UA]
    first, err = run_json(base + ["--page-number", "1", "--page-size", str(PAGE_SIZE)])
    if first is None:
        return [], "first-page-error: %s" % err
    tc = int(first.get("TotalCount", 0) or 0)
    items = first.get(list_key, []) or []
    for p in range(2, int(math.ceil(tc / float(PAGE_SIZE))) + 1):
        d, _ = run_json(base + ["--page-number", str(p), "--page-size", str(PAGE_SIZE)])
        if d:
            items.extend(d.get(list_key, []) or [])
    warn = None
    tag = " ".join(product_action)
    if len(items) != tc:
        warn = "TotalCount=%s but fetched=%s (差 %s)，请人工确认服务端快照是否抖动" % (tc, len(items), tc - len(items))
        print("[WARN] %s %s: %s" % (tag, region, warn), file=sys.stderr)
    else:
        print("[OK] %s %s: 取数完整 %s/%s" % (tag, region, len(items), tc), file=sys.stderr)
    return items, warn


def expand_proxy_types(rule):
    """把 ProxyTypes[] 展开成 (proxy_type, port) 全组合。一个域名可同时有 http:80 + https:443 + 自定义端口。"""
    endpoints = []
    for pt in rule.get("ProxyTypes", []) or []:
        ptype = str(pt.get("ProxyType", "") or "").lower()
        for port in pt.get("ProxyPorts", []) or []:
            try:
                p = int(port)
            except (TypeError, ValueError):
                continue
            endpoints.append({"proxy_type": ptype, "port": p})
    return endpoints


def normalize_web_rule(rule, region):
    domain = rule.get("Domain", "") or ""
    real_servers = rule.get("RealServers", []) or []
    origin_ips_v4, origin_ips_v6, origin_domains, dig_failed = [], [], [], []
    for rs in real_servers:
        rs_val = rs.get("RealServer", "") or ""
        if rs.get("RsType") == 1:
            origin_domains.append(rs_val)
            ips = dig_short(rs_val)
            if not ips:
                dig_failed.append(rs_val)
            for ip in ips:
                (origin_ips_v6 if is_ipv6(ip) else origin_ips_v4).append(ip)
        else:
            for ip in split_multi(rs_val):
                (origin_ips_v6 if is_ipv6(ip) else origin_ips_v4).append(ip)

    endpoints = expand_proxy_types(rule)
    has_https = any(e["proxy_type"] in ("https", "websockets", "wss") or e["port"] == 443 for e in endpoints)
    return {
        "domain": domain,
        "region": region,
        "cname": rule.get("Cname", "") or "",
        # CertExpireTime 官方文档标注「暂不使用」，故意不读取，避免把无效字段当到期时间上报
        "cert_name": rule.get("CertName", "") or "",
        "user_cert_name": rule.get("UserCertName", "") or "",
        "cert_region": rule.get("CertRegion", "") or "",
        "endpoints": endpoints,
        "has_https": has_https,
        "proxy_types_raw": rule.get("ProxyTypes", []) or [],
        "origin_raw": [rs.get("RealServer", "") for rs in real_servers],
        "origin_rs_types": [rs.get("RsType") for rs in real_servers],
        "origin_domains": origin_domains,
        "origin_ips_v4": sorted(set(origin_ips_v4)),
        "origin_ips_v6": sorted(set(origin_ips_v6)),
        "origin_dig_failed": dig_failed,
        "is_wildcard": domain.startswith("*."),
    }


def normalize_scheduler_rule(rule, region):
    lines = []
    for r in rule.get("Rules", []) or []:
        vt = str(r.get("ValueType", "") or "")
        st = str(r.get("Status", "") or "")
        lines.append({
            "type": r.get("Type", ""),
            "value": r.get("Value", ""),
            "value_type": vt,
            "value_type_label": VALUE_TYPE_LABELS.get(vt, "未知ValueType=%s" % vt),
            "priority": r.get("Priority"),
            "status": st,
            "status_label": STATUS_LABELS.get(st, "未知Status=%s" % st),
            "restore_delay": r.get("RestoreDelay"),
            "line": r.get("Line", ""),
            "line_region_id": r.get("RegionId", ""),
        })
    effective_ddos = [x for x in lines if x["value_type"] == "1" and x["status"] == "1"]
    rt = str(rule.get("RuleType", "") or "")
    return {
        "region": region,
        "rule_name": rule.get("RuleName", "") or "",
        "rule_type": rt,
        "rule_type_label": RULE_TYPE_LABELS.get(rt, "未知RuleType=%s" % rt),
        "cname": rule.get("Cname", "") or "",
        "lines": lines,
        "has_effective_ddos_line": bool(effective_ddos),
        "effective_ddos_lines": effective_ddos,
        "param": rule.get("Param") or {},
        # 调度器规则不含 Domain 字段，与域名的绑定关系只能靠 DNS 实测（域名 CNAME 链是否命中本 Cname）
        "domain_agnostic": True,
    }


def fetch_cas_certs(bound_names=None):
    """
    查数字证书管理服务(cas) 的证书到期时间，返回 ({cert_name: {...}}, warns)。
    这是 C2 的唯一数据源：C2 只看「高防上绑定的那张证书」何时到期。

    两级取数：
      1) ListUserCertificateOrder 列出账号下的证书（字段名各版本略有差异，做多键名兜底）
      2) bound_names 里被高防绑定、但列表记录没带 EndDate 的，按 CertId 调
         GetUserCertificateDetail 补 EndDate/Expired/StartDate（官方确认的到期字段在这个接口上）
    解析不到只告警，绝不编造日期。
    """
    out, warns = {}, []
    for page in range(1, 11):
        d, err = run_json(["aliyun", "cas", "list-user-certificate-order",
                           "--current-page", str(page), "--show-size", "50",
                           "--user-agent", UA])
        if d is None:
            warns.append("cas list-user-certificate-order 第%s页失败: %s" % (page, err))
            break
        batch = None
        for key in ("CertificateOrderList", "certificateOrderList", "Data", "CertList"):
            if isinstance(d.get(key), list):
                batch = d[key]
                break
        if batch is None:
            warns.append("cas 响应中未找到证书列表字段（返回键: %s）；cas 是 C2 的唯一数据源，"
                         "本次所有域名的 C2 只能记 NOT_DETECTED（不是「证书没问题」）"
                         % ",".join(list(d.keys())[:12]))
            break
        if not batch:
            break
        for c in batch:
            name = c.get("Name") or c.get("name") or c.get("CommonName") or ""
            if not name:
                continue
            out[str(name)] = {
                "cert_id": c.get("CertificateId") or c.get("CertId") or c.get("InstanceId") or "",
                "domain": c.get("Domain") or c.get("domain") or "",
                "end_date": c.get("EndDate") or c.get("endDate") or "",
                "start_date": c.get("StartDate") or c.get("startDate") or "",
                "expired": c.get("Expired") if c.get("Expired") is not None else c.get("expired"),
                "status": c.get("Status") or c.get("status") or "",
            }
        if len(batch) < 50:
            break

    # 被高防绑定、但列表记录里没带 EndDate 的，按 CertId 补查详情
    # （官方确认到期字段 EndDate/Expired 在 GetUserCertificateDetail 上）
    for nm in sorted(set(bound_names or [])):
        rec = out.get(nm)
        if not rec or rec.get("end_date") or not rec.get("cert_id"):
            continue
        d, err = run_json(["aliyun", "cas", "get-user-certificate-detail",
                           "--cert-id", str(rec["cert_id"]), "--user-agent", UA])
        if d is None:
            warns.append("cas get-user-certificate-detail(CertId=%s，绑定证书 %s) 失败: %s"
                         % (rec["cert_id"], nm, err))
            continue
        if d.get("EndDate"):
            rec["end_date"] = d.get("EndDate")
        if d.get("StartDate"):
            rec["start_date"] = d.get("StartDate")
        if d.get("Expired") is not None:
            rec["expired"] = d.get("Expired")
        if not rec.get("domain") and (d.get("CommonName") or d.get("Sans")):
            rec["domain"] = d.get("CommonName") or d.get("Sans")
        rec["detail_source"] = "GetUserCertificateDetail"
        if not rec.get("end_date"):
            warns.append("证书 %s(CertId=%s) 在 cas 详情接口里也没有返回 EndDate，"
                         "该条 C2 记 NOT_DETECTED，不编造日期" % (nm, rec["cert_id"]))

    if not out and not warns:
        warns.append("cas 未返回任何证书（账号下无上传证书，或权限不足）")
    return (out or None), warns


def registrable_domain(name):
    """粗略取可注册域（最后两段），仅用于给「近似命中」提示，不作权威判定。"""
    parts = [p for p in str(name).strip().lower().rstrip(".").split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else (parts[0] if parts else "")


def dig_cname_chain(domain, max_hops=8):
    """本地走 CNAME 链（不调云 API），用于判断域名是否指向本账号的调度器 CNAME。"""
    if not shutil.which("dig"):
        return []
    chain, cur = [], str(domain).strip().lower().rstrip(".")
    for _ in range(max_hops):
        try:
            r = subprocess.run(["dig", "+short", cur, "CNAME"], capture_output=True, text=True, timeout=10)
        except Exception:
            break
        nxt = None
        for line in r.stdout.splitlines():
            n = line.strip().lower().rstrip(".")
            if n and n != cur and "." in n:
                nxt = n
                break
        if not nxt or nxt in chain:
            break
        chain.append(nxt)
        cur = nxt
    return chain


def resolve_scope(expect_list, web_rules, instances, sched_rules, regions_searched):
    """
    归属门槛：判定用户给的域名/实例是否属于本账号。只做确定性归属判定，不下 C1~C4 结论。

    [MUST] 必须跨所有已查 region 判定 —— 只查一个 region 就下「不在账号下」的结论是假阴性
    （同一账号常常 cn-hangzhou 与 ap-southeast-1 都有实例）。
    匹配顺序：InstanceId -> 精确域名 -> 泛域名父级覆盖 -> 调度器 CNAME（本地 dig 实测）。
    """
    wr_by_domain = {}
    for w in web_rules:
        wr_by_domain.setdefault(w["domain"].strip().lower().rstrip("."), []).append(w)
    wildcards = [w for w in web_rules if w["is_wildcard"]]
    inst_ids = dict((str(i.get("InstanceId") or "").strip().lower(), i) for i in instances)
    sched_cnames = set(s["cname"].strip().lower().rstrip(".") for s in sched_rules if s.get("cname"))
    resolved, unresolved = [], []

    for raw_item in expect_list:
        it = str(raw_item).strip().lower().rstrip(".")
        if not it:
            continue

        if it in inst_ids:
            i = inst_ids[it]
            resolved.append({"input": raw_item, "kind": "instance", "status": "FOUND_INSTANCE",
                             "region": i.get("_region") or i.get("region"),
                             "instance_id": i.get("InstanceId"),
                             "ip": i.get("Ip"), "remark": i.get("Remark", "")})
            continue

        if it in wr_by_domain:
            hits = wr_by_domain[it]
            resolved.append({"input": raw_item, "kind": "domain", "status": "FOUND_EXACT",
                             "regions": sorted(set(h["region"] for h in hits)),
                             "cnames": sorted(set(h["cname"] for h in hits if h["cname"]))})
            continue

        # 泛域名覆盖：*.parent 覆盖 it 且 it 只比 parent 多一层标签（泛证书/泛规则都只覆盖一层）
        cover = []
        for w in wildcards:
            parent = w["domain"][2:].strip().lower().rstrip(".")
            if it.endswith("." + parent) and "." not in it[:-(len(parent) + 1)]:
                cover.append({"wildcard_rule": w["domain"], "region": w["region"], "cname": w["cname"]})
        if cover:
            no_cname = [c["wildcard_rule"] for c in cover if not c.get("cname")]
            note = ("字面上不在 DescribeWebRules 中，但被泛域名规则覆盖，属合法接入；"
                    "C1/C2/C4 需用该具体子域名探测，报告须标注为泛域名覆盖")
            if no_cname:
                note += ("。注意：覆盖它的泛域名规则 %s 的 Cname 为空（未关联高防 IP），"
                         "因此该子域名的 C1 将落入第3类 NOT_APPLICABLE_NO_CNAME_ASSIGNED，"
                         "而不是判定 DNS 是否一致" % ",".join(no_cname))
            resolved.append({"input": raw_item, "kind": "domain", "status": "FOUND_WILDCARD",
                             "covered_by": cover, "covering_rules_without_cname": no_cname,
                             "note": note})
            continue

        # 调度器接入：规则是 domain-agnostic 的，域名可能根本没有自己的 web rule，
        # 但客户把它 CNAME 到了本账号的调度器 CNAME —— 这种也属于本账号，不能判为「不在账号下」
        chain = dig_cname_chain(it)
        sched_hit = [c for c in chain if c in sched_cnames]
        if sched_hit:
            matched = [s for s in sched_rules
                       if s.get("cname", "").strip().lower().rstrip(".") in sched_hit]
            # 第2类：没有七层转发规则，但 DNS 指向本账号的调度器 CNAME。
            # 此时 C1 不适用（没有 web-rule CNAME 可比对），但必须提示用户确认业务是否需要七层转发。
            resolved.append({"input": raw_item, "kind": "domain", "status": "FOUND_VIA_SCHEDULER",
                             "cname_chain": chain, "matched_scheduler_cname": sched_hit,
                             "matched_rules": [{"rule_name": m.get("rule_name"),
                                                "rule_type": m.get("rule_type"),
                                                "rule_type_label": m.get("rule_type_label"),
                                                "region": m.get("region"),
                                                "has_effective_ddos_line": m.get("has_effective_ddos_line")}
                                               for m in matched],
                             "c1_verdict": "NOT_APPLICABLE_SCHEDULER_ONLY",
                             "c1_prompt": "该域名在本账号没有七层转发规则，但 DNS 已指向流量调度器 CNAME "
                                          "%s（规则 %s）。C1 不适用——没有 web-rule CNAME 可比对。"
                                          "请确认：该域名的请求是否需要经过高防做七层转发？"
                                          "若需要，除了调度器规则外还必须补配七层转发规则；"
                                          "若只做四层/调度分流则无需配置。C2/C3/C4 仍照常检查。"
                                          % (",".join(sched_hit),
                                             ",".join(m.get("rule_name") or "-" for m in matched)),
                             "note": "调度器规则是 domain-agnostic 的，本条归属靠 DNS 实测命中调度器 CNAME 确认"})
            continue

        rd = registrable_domain(it)
        # 第1类：本账号下没有该域名的七层转发规则，且 DNS 也没指向任何调度器 CNAME。
        # C1 不适用（无基线），处置是补配转发规则，而不是判 DNS 配错。
        unresolved.append({
            "input": raw_item,
            "kind": "domain" if "." in it else "unknown",
            "status": "NOT_FOUND_IN_ACCOUNT",
            "searched_regions": regions_searched,
            "cname_chain_observed": chain,
            "near_miss_same_registrable_domain": sorted(
                set(w["domain"] for w in web_rules if registrable_domain(w["domain"]) == rd))[:10],
            "wildcard_rules_in_account": sorted(set(w["domain"] for w in wildcards))[:10],
            "c1_verdict": "NOT_APPLICABLE_NO_WEB_RULE",
            "c1_prompt": "该域名在本账号（已查 region: %s）没有任何七层转发规则，DNS 也未指向本账号的调度器 CNAME。"
                         "C1 不适用——没有可比对的基线。处置：若该域名需要代理高防防护，"
                         "请先在高防上添加七层转发规则（域名、协议端口、源站），关联高防 IP 生成 CNAME 后再切 DNS。"
                         "在补配之前不要把它报成「DNS 配错」或「检查通过」" % ",".join(regions_searched),
        })

    return {"gate": "PASS" if not unresolved else "FAIL_UNRESOLVED",
            "requested": list(expect_list), "searched_regions": regions_searched,
            "resolved": resolved, "unresolved": unresolved}


def main():
    ap = argparse.ArgumentParser(description="拉取代理高防接入配置（只读）")
    ap.add_argument("--regions", default="cn-hangzhou", help="逗号分隔，cn-hangzhou=新BGP高防 / ap-southeast-1=国际版")
    ap.add_argument("--domain", default="", help="可选，逗号分隔的域名白名单；为空则取该 region 全部七层域名")
    ap.add_argument("--expect-domains", default="",
                    help="用户指定要检查的域名/实例ID，逗号分隔。触发归属门槛校验：不在本账号则 gate=FAIL_UNRESOLVED")
    ap.add_argument("--no-cas", action="store_true",
                    help="跳过数字证书管理服务(cas)查询。C2 只看绑定证书的到期时间、唯一数据源就是 cas，"
                         "跳过后所有域名的 C2 都只能记 NOT_DETECTED")
    ap.add_argument("--out", default="access-config.json")
    args = ap.parse_args()

    if not shutil.which("aliyun"):
        die("未找到 aliyun CLI。请先安装（见 references/cli-installation-guide.md）。"
            "配置只能从云 API 取，本地探测路径（dig/curl）替代不了本脚本。")
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    whitelist = set(d.strip().lower() for d in args.domain.split(",") if d.strip())
    warnings, instances, web_rules, sched_rules = [], [], [], []

    for region in regions:
        insts, err = fetch_instances(region)
        if err and not insts:
            warnings.append("[%s] describe-instances 失败: %s" % (region, err))
            continue
        instances.extend(insts)

        # [MUST] 始终按 region 全量拉取。既不用 --instance-ids（实测漏采 80%），也不用 --domain 逐条查：
        # 后者拿不到泛域名规则，会让归属门槛把「被 *.parent 覆盖的子域名」误判成不属于本账号。
        # 域名收窄在本地做（见 resolve_scope / whitelist 过滤），不靠 API 过滤。
        raw, warn = fetch_paged(["ddoscoo", "describe-web-rules"], region, [], "WebRules")
        if warn:
            warnings.append("[%s] web-rules: %s" % (region, warn))
        web_rules.extend(normalize_web_rule(r, region) for r in raw)

        sraw, swarn = fetch_paged(["ddoscoo", "describe-scheduler-rules"], region, [], "SchedulerRules")
        if swarn:
            warnings.append("[%s] scheduler-rules: %s" % (region, swarn))
        sched_rules.extend(normalize_scheduler_rule(r, region) for r in sraw)

    # 去重在全量集合上做，保证归属门槛看到的是完整账号视图（而不是被白名单裁剪后的视图）
    seen, deduped = set(), []
    for w in web_rules:
        key = (w["domain"], w["region"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(w)
    all_web_rules = deduped

    expect = [x.strip() for x in args.expect_domains.split(",") if x.strip()]
    scope_gate = resolve_scope(expect, all_web_rules, instances, sched_rules, regions) if expect else None

    if whitelist:
        keep = set(d.strip().lower().rstrip(".") for d in args.domain.split(",") if d.strip())
        # 白名单命中泛域名时必须保留覆盖它的泛域名规则，否则后续检查会失去配置基线
        covered = set()
        for w in all_web_rules:
            if not w["is_wildcard"]:
                continue
            parent = w["domain"][2:].strip().lower().rstrip(".")
            for k in keep:
                if k.endswith("." + parent) and "." not in k[:-(len(parent) + 1)]:
                    covered.add(w["domain"].strip().lower())
        before = len(all_web_rules)
        web_rules = [w for w in all_web_rules
                     if w["domain"].strip().lower().rstrip(".") in keep
                     or w["domain"].strip().lower() in covered]
        print("[INFO] 域名白名单过滤: %s -> %s（其中泛域名覆盖规则 %s 条）"
              % (before, len(web_rules), len(covered)), file=sys.stderr)

    web_cnames = sorted(set(w["cname"] for w in web_rules if w["cname"]))
    sched_cnames = sorted(set(s["cname"] for s in sched_rules if s["cname"]))
    wildcards = [w["domain"] for w in web_rules if w["is_wildcard"]]
    dig_failed = sorted(set(x for w in web_rules for x in w["origin_dig_failed"]))
    if dig_failed:
        warnings.append("以下域名型源站本地 dig 未解析出 IP（C1/C3 的源站比对会不完整）: %s" % ",".join(dig_failed))

    # C2 只看「高防上绑定的那张证书」的到期时间，cas 是唯一数据源，所以默认就查
    cas_certs = None
    cas_enabled = not args.no_cas
    bound_names = sorted(set(x for w in web_rules
                             for x in (w["cert_name"], w["user_cert_name"]) if x))
    if cas_enabled:
        cas_certs, cas_warns = fetch_cas_certs(bound_names)
        warnings.extend(cas_warns)
        if cas_certs:
            matched = [w["domain"] for w in web_rules
                       if w["cert_name"] in cas_certs or w["user_cert_name"] in cas_certs]
            with_date = [w["domain"] for w in web_rules
                         if (cas_certs.get(w["cert_name"]) or cas_certs.get(w["user_cert_name"]) or {}).get("end_date")]
            print("[OK] cas 证书 %s 张；高防绑定的证书名 %s 个，匹配上 %s 个域名，其中拿到到期时间 %s 个"
                  % (len(cas_certs), len(bound_names), len(matched), len(with_date)), file=sys.stderr)
            unmatched = [w["domain"] for w in web_rules
                         if (w["cert_name"] or w["user_cert_name"])
                         and w["cert_name"] not in cas_certs and w["user_cert_name"] not in cas_certs]
            if unmatched:
                warnings.append("以下域名在高防上绑定了证书名，但在 cas 列表中匹配不到（可能是非本账号上传或名称不一致），"
                                "C2 记 NOT_DETECTED: %s" % ",".join(unmatched))
            if len(matched) != len(with_date):
                warnings.append("有 %s 个域名匹配到了 cas 证书记录但没拿到 EndDate，C2 记 NOT_DETECTED"
                                % (len(matched) - len(with_date)))
        if not cas_certs:
            warnings.append("cas 没有可用证书数据，而 cas 是 C2 的唯一数据源 —— 本次全部域名的 C2 都只能记 "
                            "NOT_DETECTED（不是「证书没问题」）。若需要 C2 结论，请确认当前身份有 "
                            "yundun-cert 读权限后重跑")
    else:
        warnings.append("已用 --no-cas 跳过证书服务查询：C2 唯一数据源缺失，全部域名的 C2 记 NOT_DETECTED")

    out = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "regions": regions,
        "domain_filter": sorted(whitelist) if whitelist else [],
        "scope_gate": scope_gate,
        "account_web_domains_total": len(all_web_rules),
        "instances": [{"InstanceId": i.get("InstanceId"), "Ip": i.get("Ip"),
                       "IpVersion": i.get("IpVersion"), "Remark": i.get("Remark", ""),
                       "region": i.get("_region")} for i in instances],
        "antiddos_ips": sorted(set(str(i.get("Ip")) for i in instances if i.get("Ip"))),
        "web_rules": web_rules,
        "scheduler_rules": sched_rules,
        "scheduler_in_use": bool(sched_rules),
        "expected_cnames": {
            "web_rule_cnames": web_cnames,
            "scheduler_cnames": sched_cnames,
            "all": sorted(set(web_cnames) | set(sched_cnames)),
        },
        "wildcard_domains": wildcards,
        "cas_certs": cas_certs,
        "with_cas": cas_enabled,
        "warnings": warnings,
        "summary": {
            "instances": len(instances),
            "web_domains": len(web_rules),
            "https_domains": sum(1 for w in web_rules if w["has_https"]),
            "wildcard_domains": len(wildcards),
            "scheduler_rules": len(sched_rules),
            "scheduler_rules_without_effective_ddos_line": sum(1 for s in sched_rules if not s["has_effective_ddos_line"]),
            "endpoints_total": sum(len(w["endpoints"]) for w in web_rules),
            "cas_certs": len(cas_certs) if cas_certs else 0,
        },
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("", file=sys.stderr)
    print("[DONE] 写入 %s" % args.out, file=sys.stderr)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2), file=sys.stderr)
    # 三种「查不到」语义完全不同，不能共用一句话，否则会把「你指定的域名不在本账号」
    # 误报成「账号没有任何七层配置」，让 agent 得出错误结论
    # [MUST] 「零实例」不是停止条件，除非七层规则也为空。
    # 零实例 + 有规则是真实可达状态：实例已退款/释放而转发规则仍在，或该 region 实例数为 0。
    # 旧实现在 not instances 时无条件打 [STOP]，Agent 据此停在 Step 1，于是 check_local.py /
    # create_probes.py / parse_probe_log.py 全都不执行，C1~C4 一个结论都没有 ——
    # 而 judge_c1 的第3类分支恰恰就是为这个状态写的：它返回 NOT_APPLICABLE_NO_CNAME_ASSIGNED，
    # 并在 _region_instance_count==0 时说明「规则无实例承载，这正是 Cname 为空的原因，改 DNS 解决不了」。
    # 停下来等于把这个结论连同 C2/C3/C4 一起丢掉。
    if not instances and not all_web_rules:
        print("\n[STOP] 未找到高防实例，且账号下没有任何七层网站接入配置：请确认 RegionId"
              "（内地 cn-hangzhou / 非内地 ap-southeast-1）或该账号是否开通代理高防。"
              "不要输出「检查通过」。", file=sys.stderr)
    elif not instances:
        print("\n[CONTINUE] 未找到高防实例，但账号下有 %s 个七层域名 —— **这不是停止条件，"
              "必须继续跑完整条流水线**（check_local.py -> create_probes.py -> parse_probe_log.py）。\n"
              "         实例缺失本身是一项发现，写进报告第 2 节；C1 会走第3类分支给出\n"
              "         NOT_APPLICABLE_NO_CNAME_ASSIGNED 并说明「规则无实例承载，改 DNS 解决不了」，\n"
              "         C2/C3/C4 照常判定。停在这里会让四项检查全部没有结论。\n"
              "         同时仍要提示客户确认 RegionId 或代理高防是否已开通 —— 但不要因此中止。"
              % len(all_web_rules), file=sys.stderr)
    elif not all_web_rules:
        print("\n[STOP] 有高防实例但账号下没有任何七层网站接入配置，无接入配置可检查。"
              "四层端口接入不在本技能范围内。", file=sys.stderr)
    elif not web_rules:
        print("\n[STOP] 账号下共有 %s 个七层域名，但你指定的范围一个都没匹配上。"
              "不要报「无接入配置可检查」——见下方 scope_gate 的归属判定与近似命中提示。"
              % len(all_web_rules), file=sys.stderr)

    if scope_gate:
        print("\n[SCOPE GATE] %s（已跨 region 判定: %s）"
              % (scope_gate["gate"], ",".join(scope_gate["searched_regions"])), file=sys.stderr)
        for r in scope_gate["resolved"]:
            extra = ""
            if r["status"] == "FOUND_WILDCARD":
                extra = " ← 被泛域名 %s 覆盖" % ",".join(c["wildcard_rule"] for c in r["covered_by"])
            elif r["status"] == "FOUND_VIA_SCHEDULER":
                extra = " ← DNS 指向调度器 CNAME %s（无独立七层规则）" % ",".join(r["matched_scheduler_cname"])
            elif r["status"] == "FOUND_INSTANCE":
                extra = " ← region=%s ip=%s" % (r.get("region"), r.get("ip"))
            print("  [OK]   %s -> %s%s" % (r["input"], r["status"], extra), file=sys.stderr)
            if r.get("c1_verdict"):
                print("         C1 = %s" % r["c1_verdict"], file=sys.stderr)
                print("         [C1 提示] %s" % r["c1_prompt"], file=sys.stderr)
        for u in scope_gate["unresolved"]:
            print("  [FAIL] %s -> NOT_FOUND_IN_ACCOUNT" % u["input"], file=sys.stderr)
            print("         已查 region: %s" % ",".join(u["searched_regions"]), file=sys.stderr)
            print("         实测 CNAME 链: %s" % (" -> ".join(u["cname_chain_observed"]) or "(无 CNAME)"),
                  file=sys.stderr)
            if u["near_miss_same_registrable_domain"]:
                print("         同主域下的已有配置: %s" % ",".join(u["near_miss_same_registrable_domain"]),
                      file=sys.stderr)
            if u["wildcard_rules_in_account"]:
                print("         账号下的泛域名规则: %s" % ",".join(u["wildcard_rules_in_account"]),
                      file=sys.stderr)
            if u.get("c1_verdict"):
                print("         C1 = %s" % u["c1_verdict"], file=sys.stderr)
                print("         [C1 提示] %s" % u["c1_prompt"], file=sys.stderr)
        if scope_gate["gate"] == "FAIL_UNRESOLVED":
            print("\n  [MUST] 归属门槛未通过：按 SKILL.md Step 1.5 停下并提示用户，不要继续 C1~C4 判定流程。"
                  "\n         可选降级：经用户显式同意后，只做与配置无关的公网观测"
                  "（C2 证书 + C4 本地单出口健康 + 描述性 CNAME 链），"
                  "C1 必须记 NOT_APPLICABLE_NO_WEB_RULE（第1类）、C3 必须记 "
                  "NOT_APPLICABLE_NO_CONFIG_BASELINE，且报告须写明该域名不属于本账号。",
                  file=sys.stderr)
    if out["scheduler_in_use"]:
        no_ddos = [s["rule_name"] for s in sched_rules if not s["has_effective_ddos_line"]]
        print("\n[调度器] 检测到 %s 条流量调度器规则；C1/C3 的期望首跳 CNAME 需改用调度器 CNAME。"
              % len(sched_rules), file=sys.stderr)
        print("  调度器 CNAME: %s" % ",".join(sched_cnames), file=sys.stderr)
        print("  [MUST] 判定前先读 references/check-criteria.md 的 Traffic scheduler 章节"
              "（RuleType 决定高防是否本就只在大流量时切入）", file=sys.stderr)
        if no_ddos:
            print("  [!!] 以下调度器规则没有生效的高防线路(ValueType=1 且 Status=1)，"
                  "高防可能实际不在链路中: %s" % ",".join(no_ddos), file=sys.stderr)
    if wildcards:
        print("\n[泛域名] 需按 SKILL.md Step 2 让用户选择处理方式（提供子域名/常见前缀抽样/跳过）: %s"
              % ",".join(wildcards), file=sys.stderr)
    if warnings:
        print("\n[WARNINGS]（需人工确认，勿忽略）:", file=sys.stderr)
        for w in warnings:
            print("  - %s" % w, file=sys.stderr)


if __name__ == "__main__":
    main()
