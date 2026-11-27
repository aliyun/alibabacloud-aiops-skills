#!/usr/bin/env python3
"""
check_local.py — 本地取证（**兜底**）：CNAME 全链路(C1/C3) + 绑定证书到期(C2) + 单出口健康(C4)

[MUST] C1/C3 的 DNS 观测**首选云拨测**，本脚本的 dig 链路只是兜底：
  - 云拨测 DNS 的 DNSRaw 字段回的是整段有序应答（"域名 CNAME 高防CNAME TTL|高防CNAME A IP TTL|"），
    首跳 CNAME、整条链的层级、最终 IP 都能从云端多点拿到，还自带各点实际使用的 dnsServer。
    早前本文件写的「云拨测只给最终解析结果、逐跳链必须本地 dig」是**错的**，已纠正。
  - 本地 dig 的两个失真风险：① 单出口，代表不了国内/海外各地用户的真实解析；
    ② 本机可能处于企业代理/内网 resolver 之后，解析结果与公网不一致（HTTP/TLS 更会被中间人改写）。
  - 因此：有云拨测数据时以云拨测为准；只有在云拨测未开通、任务失败、或 DNSRaw 为空时才用本脚本兜底，
    并且报告里必须标注 perspective=LOCAL_SINGLE_EGRESS，不得把单出口结论写成「全球解析一致」。
  - 判定逻辑不在本脚本与 parse_probe_log.py 之间复制：parse_probe_log.py 直接 import 本文件的
    judge_c1/judge_c3/classify_ips/find_scheduler_rule，两个观测源共用同一份判定实现。

本地仍有一项云拨测替代不了的价值：多解析器对比（系统 resolver + 公共 DNS）能暴露分线路解析/
解析不一致，这是任何单点观测看不出来的——但它只作补充证据，不作 C1/C3 的主判据。

C2 不在本地取证范围内：C2 只看「高防上绑定的那张证书」的到期时间，唯一数据源是 cas
（DescribeWebRules[].CertName/UserCertName -> cas 的 EndDate/Expired），由 fetch_config.py 取回后
写进 --config，本脚本只做判定、不再发起任何证书探测。本脚本不读实际下发的证书（openssl），
也不判域名匹配与证书链完整性——那些不属于 C2。

判定分层：C1/C3/C2 能确定性判定的直接出 verdict；无法归类的跳数标 UNKNOWN_HOP + NEED_AGENT_REVIEW，
交 agent 按 references/check-criteria.md 研判，脚本绝不猜。

用法：
  python3 check_local.py --config access-config.json --out local-evidence.json
  python3 check_local.py --config access-config.json --with-health --resolvers 223.5.5.5,8.8.8.8 --out local-evidence.json
  python3 check_local.py --config access-config.json --wildcard-samples www,api --out local-evidence.json

只读、无副作用；本脚本不调用任何云 API（C2 依赖的 cas 数据来自 --config）。
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

MAX_HOPS = 8
DEFAULT_RESOLVERS = "223.5.5.5,8.8.8.8"

# CNAME 特征后缀 —— 仅作辅助证据（auxiliary）。权威判据是与 config 里的 expected_cnames 精确比对。
# 列表不完备；匹配不到就标 UNKNOWN_HOP 交 agent 研判，绝不硬塞进某一类。
CNAME_SIGNATURES = [
    ("antiddos", ".aliyunddos"),          # 高防 CNAME：aliyunddos1020.com / aliyunddos0001.com / aliyunddos1001.com ...
    ("alicloud_waf", ".aliyunwaf.com"),
    ("alicloud_waf", ".yundunwaf.com"),
    ("alicloud_cdn", ".kunlun"),          # kunlunaq.com / alikunlun.com ...
    ("alicloud_cdn", ".tbcache.com"),
    ("alicloud_cdn", ".cdngslb.com"),
    ("alicloud_dcdn", ".danuoyi."),
    ("alicloud_ga", ".aliyunga"),
    ("cloudflare", ".cdn.cloudflare.net"),
    ("akamai", ".akamaized.net"),
    ("akamai", ".akamaiedge.net"),
    ("aws_cloudfront", ".cloudfront.net"),
    ("azure_cdn", ".azureedge.net"),
    ("tencent_cdn", ".cdn.dnsv1.com"),
    ("tencent_cdn", ".cdntip.com"),
]
HOP_LABELS = {
    "antiddos_config": "Anti-DDoS 高防（与配置 CNAME 精确一致）",
    "scheduler_config": "流量调度器（与配置 CNAME 精确一致）",
    "antiddos": "Anti-DDoS 高防",
    "alicloud_waf": "阿里云 WAF",
    "alicloud_cdn": "阿里云 CDN",
    "alicloud_dcdn": "阿里云 DCDN 全站加速",
    "alicloud_ga": "阿里云全球加速 GA",
    "cloudflare": "Cloudflare",
    "akamai": "Akamai",
    "aws_cloudfront": "AWS CloudFront",
    "azure_cdn": "Azure CDN",
    "tencent_cdn": "腾讯云 CDN",
}
# 这些 RuleType 下，高防按设计就是「大流量时才切入」，平时流量不经高防属预期行为，判 INFO 而非 FAIL
ON_DEMAND_RULE_TYPES = ("2", "3", "8")


def warn(msg):
    print("[WARN] %s" % msg, file=sys.stderr)


def run(cmd, stdin_data=None, timeout=15):
    try:
        r = subprocess.run(cmd, input=stdin_data, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout after %ss" % timeout
    except OSError as e:
        return -1, "", "exec-failed: %s" % e


def norm_name(s):
    """CNAME/域名归一化：小写 + 去尾点。比对必须用归一化后的值。"""
    return str(s or "").strip().lower().rstrip(".")


IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")


def classify_line(line):
    line = line.strip().rstrip(".")
    if IPV4_RE.match(line):
        return "ip", line
    if ":" in line and IPV6_RE.match(line):
        return "ip", line
    if "." in line and not line.startswith('"'):
        return "cname", norm_name(line)
    return "other", line


def dig_lines(name, rtype=None, resolver=None):
    cmd = ["dig", "+short"]
    if resolver:
        cmd.append("@%s" % resolver)
    cmd.append(name)
    if rtype:
        cmd.append(rtype)
    rc, out, err = run(cmd, timeout=12)
    if rc != 0:
        return None, (err or "dig-failed").strip()[:150]
    return [l.strip() for l in out.splitlines() if l.strip()], None


def resolve_chain(domain, resolver=None):
    """逐跳走 CNAME 链（最多 MAX_HOPS 跳，带环检测），返回链路 + 最终 IP。"""
    cnames, cur, loop = [], norm_name(domain), False
    for _ in range(MAX_HOPS):
        cs, err = dig_lines(cur, "CNAME", resolver)
        if cs is None:
            return {"error": err, "cnames": cnames, "ips_v4": [], "ips_v6": [], "truncated": False}
        nxt = None
        for c in cs:
            n = norm_name(c)
            if n and n != cur:
                nxt = n
                break
        if not nxt:
            break
        if nxt in cnames:
            loop = True
            break
        cnames.append(nxt)
        cur = nxt
    truncated = len(cnames) >= MAX_HOPS

    def ips_of(rtype):
        lines, _ = dig_lines(cur, rtype, resolver)
        out = []
        for l in lines or []:
            kind, val = classify_line(l)
            if kind == "ip":
                out.append(val)
        return sorted(set(out))

    return {
        "resolver": resolver or "system",
        # [MUST] 本地 dig 是单出口观测，每条链路都要带这个标记，报告须原样透出
        "perspective": "LOCAL_SINGLE_EGRESS",
        "cnames": cnames,
        "first_hop": cnames[0] if cnames else None,
        "terminal_name": cur,
        "ips_v4": ips_of("A"),
        "ips_v6": ips_of("AAAA"),
        "loop_detected": loop,
        "truncated": truncated,
        "error": None,
    }


def classify_hop(name, expected_web_cnames, expected_sched_cnames, antiddos_sig_only=False):
    """辅助归类：先精确匹配 config CNAME，再退回特征后缀。"""
    n = norm_name(name)
    if n in expected_web_cnames:
        return "antiddos_config", "与 DescribeWebRules.Cname 精确一致"
    if n in expected_sched_cnames:
        return "scheduler_config", "与 DescribeSchedulerRules.Cname 精确一致"
    for label, sig in CNAME_SIGNATURES:
        if sig in n:
            return label, "特征后缀 %s（辅助证据，非 config 精确匹配）" % sig
    return "unknown", "无法归类，需 agent 研判"


def classify_ips(ips, origin_ips, antiddos_ips):
    hit_origin = sorted(set(ips) & set(origin_ips))
    hit_ddos = sorted(set(ips) & set(antiddos_ips))
    others = sorted(set(ips) - set(origin_ips) - set(antiddos_ips))
    return {"hit_origin": hit_origin, "hit_antiddos_ip": hit_ddos, "others": others}


def find_scheduler_rule(cnames, sched_rules):
    """调度器规则不含 Domain 字段：只能靠域名 CNAME 链是否命中某条规则的 Cname 来绑定。"""
    for hop in cnames:
        for s in sched_rules:
            if s.get("cname") and norm_name(s["cname"]) == hop:
                return s, hop
    return None, None


def judge_c1(cfg, chain, ip_cls, sched_rule):
    """
    C1：域名解析与高防 CNAME 是否一致。

    [MUST] 先判前置条件（有没有可比对的基线），再判一致性。基线缺失时判「不适用」并给出处置提示，
    绝不降级成 FAIL —— 那会把「还没配好」误报成「配错了」，两者的处置动作完全不同。

    本函数只负责第 3、4 类：
      第3类  有七层规则但 Cname 为空（未关联高防 IP）-> NOT_APPLICABLE_NO_CNAME_ASSIGNED
      第4类  有七层规则且有 Cname -> C1 适用；DNS 既未用该 CNAME、也未用调度器 CNAME -> 不通过
    第1类（无七层规则）与第2类（无规则但 DNS 指向调度器 CNAME）由 fetch_config.py 的归属门槛产出：
    那两种情况下压根没有 web rule，本函数不会被调用。
    """
    # ---------- 第1类：本账号没有该域名的七层规则 ----------
    # 只可能由 --extra-domains 合成进来（经用户显式同意的降级/无基线公网观测）。
    # 第2类（无规则但 DNS 指向本账号调度器 CNAME）已由 fetch_config.py 的归属门槛排除：
    # 能通过门槛就不会走到这里，因此此处不重复判定，避免与门槛给出互相矛盾的结论。
    if cfg.get("baseline_free"):
        return "NOT_APPLICABLE_NO_WEB_RULE", (
            "该域名在本账号没有任何七层转发规则（DescribeWebRules 里没有它），因此没有可比对的 "
            "CNAME 基线，C1 不适用。本次是经用户显式同意的降级/无基线公网观测，下面的解析与"
            "可达性结果只描述公网现状，不构成接入验收结论。处置：先在高防为该域名添加七层转发规则"
            "并关联高防 IP 生成 CNAME，再把域名 DNS 切到该 CNAME，然后重跑本检查")

    expected = norm_name(cfg.get("cname"))

    # ---------- 第3类：无 CNAME 基线，C1 不适用 ----------
    if not expected:
        detail = ("该域名在高防上有七层转发规则，但 DescribeWebRules 返回的 Cname 为空——"
                  "未关联高防 IP，因此没有可供比对的 CNAME 基线，C1 不适用。"
                  "处置：先在高防上为该转发规则关联高防 IP 生成 CNAME，再把域名 DNS 切到该 CNAME")
        if cfg.get("_region_instance_count") == 0:
            detail += ("。另注：该 region(%s) 当前实例数为 0，规则处于无实例承载状态，"
                       "这通常正是 CNAME 为空的原因" % cfg.get("region"))
        return "NOT_APPLICABLE_NO_CNAME_ASSIGNED", detail

    # ---------- 第4类：C1 适用 ----------
    if chain.get("error"):
        # 文案必须与观测源无关：云拨测与本地 dig 共用本函数
        return "NOT_DETECTED", "解析观测未做成（来源 %s）: %s" % (
            chain.get("perspective") or "local-dig", chain["error"])
    cnames = chain.get("cnames") or []
    all_ips = (chain.get("ips_v4") or []) + (chain.get("ips_v6") or [])
    sched_cnames = cfg.get("_sched_cnames") or set()
    other_web_cnames = (cfg.get("_web_cnames") or set()) - set([expected])

    if not cnames and not all_ips:
        return "FAIL_NO_RECORD", ("公网无任何解析记录（无 CNAME、无 A/AAAA）。本域名配置的高防 CNAME 是 %s，"
                                  "但没有任何 DNS 记录指向它——DNS 未切换或记录被删除" % expected)

    if cnames:
        first = chain["first_hop"]
        if first == expected:
            v, d = "PASS_CONSISTENT", "首跳 CNAME %s 与本域名配置的高防 CNAME 一致" % first
        elif first in sched_cnames:
            rn = sched_rule.get("rule_name") if sched_rule else "-"
            v, d = "PASS_CONSISTENT_VIA_SCHEDULER", ("首跳 CNAME %s 命中流量调度器规则 %s；"
                                                     "按判定规则，使用调度器 CNAME 同样算通过，"
                                                     "不能因为不等于本域名的 web-rule CNAME 就判不通过" % (first, rn))
        elif first in other_web_cnames:
            v, d = "FAIL_CNAME_MISMATCH", ("首跳 CNAME %s 是本账号下**其他域名**的高防 CNAME，"
                                           "不是本域名配置的 %s；疑似配置串用" % (first, expected))
        else:
            kind, _ = classify_hop(first, set(), sched_cnames)
            hint = ""
            if kind == "antiddos":
                hint = "（带高防 CNAME 特征后缀，可能是实例迁移或配置重建后的旧值）"
            elif kind != "unknown":
                hint = "（归类为 %s）" % HOP_LABELS.get(kind, kind)
            v, d = "FAIL_CNAME_MISMATCH", ("首跳 CNAME %s%s 既不是本域名配置的高防 CNAME %s，"
                                           "也不是任何调度器 CNAME；DNS 未切到高防或切到了别处"
                                           % (first, hint, expected))
        # 链路末端落到源站 IP 是最严重的情形，覆盖上面的结论
        if ip_cls["hit_origin"]:
            return "FAIL_A_RECORD_TO_ORIGIN", ("链路末端解析到源站 IP %s，流量绕过高防直达源站；%s"
                                               % (",".join(ip_cls["hit_origin"]), d))
        return v, d

    # 无 CNAME，纯 A 记录接入
    if ip_cls["hit_origin"]:
        return "FAIL_A_RECORD_TO_ORIGIN", ("域名直接 A 记录指向源站 IP %s，完全绕过高防；"
                                           "应改为 CNAME 指向 %s" % (",".join(ip_cls["hit_origin"]), expected))
    if ip_cls["hit_antiddos_ip"]:
        # 按判定规则：未使用分配的 CNAME 即不通过。流量确实经过高防，但接入方式脆弱，
        # 故保留独立子标签以便报告给出准确处置（改 CNAME），而不是当成「绕过高防」处理
        return "FAIL_A_RECORD_TO_ANTIDDOS_IP", ("域名用 A 记录直接指向高防 IP %s，未使用分配的 CNAME %s。"
                                                "流量当前确实经过高防，但实例迁移/扩容换 IP 后会立刻断，"
                                                "应改为 CNAME 接入" % (",".join(ip_cls["hit_antiddos_ip"]), expected))
    return "FAIL_A_RECORD_UNKNOWN_TARGET", ("域名 A 记录指向 %s，既不是已知高防 IP 也不是源站 IP，"
                                            "且未使用分配的 CNAME %s；疑似残留旧记录或指向第三方。"
                                            "注意：若该 region 实例已释放，高防 IP 比对集合会不完整，"
                                            "此结论需人工确认该 IP 归属"
                                            % (",".join(ip_cls["others"] or all_ips), expected))


def judge_c3(cfg, chain, ip_cls, sched_rule):
    """C3：高防是否在互联网链路第一层。判的是「顺序」，不是「有没有」。"""
    # 无基线（--extra-domains 合成）时 C3 一律不适用：既没有期望 CNAME、也没有源站 IP 集合，
    # 「顺序」无从判起。此时若照常分类链路，会把无依据的推断报成 FAIL_DIRECT_TO_ORIGIN ——
    # 那正是本技能反复禁止的「把未知当结论」。解析链仍会作为描述性证据记录在 domains[].chain。
    if cfg.get("baseline_free"):
        return "NOT_APPLICABLE_NO_CONFIG_BASELINE", (
            "该域名在本账号没有七层转发规则，缺少判定「高防是否在第一层」所需的配置基线"
            "（期望 CNAME 与源站 IP 集合），C3 不适用。本次为降级/无基线公网观测，"
            "解析链仅作描述性记录，不构成接入验收结论"), []
    if chain.get("error"):
        return "NOT_DETECTED", "解析观测未做成（来源 %s）: %s" % (
            chain.get("perspective") or "local-dig", chain["error"]), []
    cnames = chain.get("cnames") or []
    classified = []
    for hop in cnames:
        kind, why = classify_hop(hop, cfg["_web_cnames"], cfg["_sched_cnames"])
        classified.append({"hop": hop, "class": kind, "label": HOP_LABELS.get(kind, kind), "why": why})

    if not cnames:
        all_ips = ip_cls["hit_origin"] + ip_cls["hit_antiddos_ip"] + ip_cls["others"]
        if not all_ips:
            # 无解析时链路层级无从判定，不能报「直达源站」——那是把未知当成结论
            detail = "域名在公网无任何解析记录，无法判定链路层级（见 C1 的 FAIL_NO_RECORD）"
            return "NOT_DETECTED", detail, classified
        if ip_cls["hit_origin"]:
            return "FAIL_DIRECT_TO_ORIGIN", "解析直达源站，链路中完全没有高防", classified
        if ip_cls["hit_antiddos_ip"]:
            detail = "高防在第一层，但用 A 记录而非 CNAME 接入，IP 变更即失效"
            return "WARN_FIRST_LAYER_VIA_A_RECORD", detail, classified
        # 落点既不命中源站、也不命中账号已知高防 IP：本账号的信息不足以评判这个 IP 归谁，
        # 因此 C3 不适用——不能报 FAIL。DescribeInstances[].Ip 实测就不是完整集
        # （某账号 2 个实例 IP，而 6 个可解析的高防 CNAME 里 4 个落在集合外），
        # 所以「落点不在集合里」推不出「高防不在链路里」，正如它也推不出「直达源站」。
        # 该域名的接入问题不会因此丢失：C1 仍按「本域名自己的 CNAME」判（那个依据账号给得全）。
        detail = ("解析落到 %s，既不命中本域名配置的源站 IP，也不命中账号已知的高防实例 IP"
                  "（该 region 实例数=%s，全账号已知高防 IP=%s）。本账号的信息不足以判定该 IP 归属，"
                  "C3 不适用——既不能说「高防不在链路里」，也不能说「直达源站」。"
                  "要定性需人工确认该 IP 归属（旧服务商 / CDN / 已释放的高防实例 / 客户自己的 ECS）"
                  % (",".join(ip_cls["others"]), cfg.get("_region_instance_count"),
                     ",".join(cfg.get("_antiddos_ips") or []) or "无"))
        return "NOT_APPLICABLE_NO_IP_BASIS", detail, classified

    first = classified[0]
    own_cname = norm_name(cfg.get("cname"))
    first_hop = norm_name(first["hop"])
    if first["class"] in ("antiddos_config", "antiddos") and first_hop == own_cname and own_cname:
        return "PASS_FIRST_LAYER", "首跳即本域名的高防 CNAME %s，攻击流量先经高防清洗" % own_cname, classified
    if first["class"] == "antiddos_config":
        # 首跳是本账号内某条规则的高防 CNAME，但不是本域名自己的。
        # 层级结论仍成立（流量确实先到高防），但绝不能说成「本域名的 CNAME」——那是假陈述。
        detail = ("首跳 %s 是本账号内的高防 CNAME，攻击流量先经高防清洗，所以高防在第一层。"
                  "但它**不是本域名自己的** CNAME（本域名 Cname=%s），绑定归属需人工确认："
                  "请核对该 CNAME 属于哪条转发规则，其协议端口与回源是否与本域名一致"
                  % (first_hop, own_cname or "空"))
        return "PASS_FIRST_LAYER", detail, classified
    if first["class"] == "antiddos":
        # 只有特征后缀、本账号无精确匹配：形态上是高防，但不是本账号签发的
        detail = ("首跳 %s 带高防 CNAME 特征（*.aliyunddos*.com），形态上高防在第一层；"
                  "但它不是本账号任何一条 DescribeWebRules 的 Cname（本域名 Cname=%s）。"
                  "可能是旧实例、别的账号或残留记录，归属需人工确认，脚本不下结论"
                  % (first_hop, own_cname or "空"))
        return "PASS_FIRST_LAYER", detail, classified

    if first["class"] == "scheduler_config" and sched_rule:
        rule_name = sched_rule.get("rule_name")
        if not sched_rule.get("has_effective_ddos_line"):
            detail = ("首跳是调度器 %s，但其规则中没有生效的高防线路(ValueType=1 且 Status=1)，"
                      "高防实际不在链路中" % rule_name)
            return "FAIL_SCHEDULER_NO_DDOS_LINE", detail, classified
        rt = str(sched_rule.get("rule_type") or "")
        ddos_line = next((l for l in sched_rule.get("lines") or []
                          if str(l.get("value_type")) == "1" and str(l.get("status")) == "1"), {})
        if rt in ON_DEMAND_RULE_TYPES:
            detail = ("调度器 %s 类型为 %s：平时流量走加速/云资源线路，仅在大流量攻击时切入高防"
                      "（RestoreDelay=%s）。这是调度器的预期设计，不是接入缺陷，但客户需知道"
                      "「平时流量不经高防清洗」"
                      % (rule_name, sched_rule.get("rule_type_label"), ddos_line.get("restore_delay", "-")))
            return "INFO_SCHEDULER_ON_DEMAND", detail, classified
        detail = ("首跳是调度器 %s（%s），其生效线路包含高防，高防在链路中"
                  % (rule_name, sched_rule.get("rule_type_label")))
        return "PASS_VIA_SCHEDULER", detail, classified

    if first["class"] == "scheduler_config":
        detail = "首跳命中某个调度器 CNAME 但未能定位到具体规则，需人工确认"
        return "WARN_SCHEDULER_UNMATCHED", detail, classified

    # 首跳是 CDN/WAF/GA/第三方：先看是否有调度器规则能解释这个架构（如 CDN 联动）
    if sched_rule:
        vals = [norm_name(str(l.get("value") or "")) for l in sched_rule.get("lines", [])]
        if any(first["hop"] in v or v in first["hop"] for v in vals if v):
            detail = ("首跳 %s(%s) 是调度器 %s 的一条线路（RuleType=%s），属联动架构的预期形态"
                      % (first["hop"], first["label"], sched_rule.get("rule_name"),
                         sched_rule.get("rule_type_label")))
            return "PASS_VIA_SCHEDULER", detail, classified

    ddos_depth = next((i for i, c in enumerate(classified)
                       if c["class"] in ("antiddos_config", "antiddos")), None)
    if ddos_depth == 0:
        # 首跳就是高防，不可能再说「前面还有 X」——上面三个分支已覆盖，
        # 这里是防御性守卫，避免日后新增 class 时又把自己当成自己前面那一层
        return "PASS_FIRST_LAYER", ("首跳 %s 归类为 %s，高防在第一层；具体归属见上方分支"
                                    % (first_hop, first["class"])), classified
    if ddos_depth is None:
        # 子情形(c)：链里完全没有高防跳。能确定的是「高防不是第一层」；
        # 不能确定的是「高防是否存在于该前置层之后」——前置层（CDN/WAF/GA）的回源配置
        # 不在公网 DNS 里，链在它的节点 IP 处就断了。绝不能把「高防被挡在它后面」当事实陈述。
        detail = ("首跳是 %s(%s)，整条 CNAME 链中未发现高防。可确定：高防不在链路第一层，"
                  "攻击流量先打到这一层且未经高防清洗。不可确定：高防是否存在于该层之后——"
                  "前置层的回源配置不在公网 DNS 里，链路到它的节点 IP 就终止了，DNS 无法再往下判断。"
                  "要确认请读该前置层自己的回源配置（属另一产品的控制台/API，不在本技能范围）"
                  % (first["label"], first["hop"]))
        return "FAIL_NOT_FIRST_LAYER", detail, classified
    # 子情形(b)：高防确实出现在第 2 跳及以后——只有前置层通过 CNAME 继续向下委派时才看得到
    detail = ("高防在链路第 %s 跳，前面还有 %s(%s)；攻击流量先打到前置层且未经清洗，高防不是第一层。"
              "本条属可证情形：前置层通过 CNAME 继续向下委派，所以能看到高防在其后"
              % (ddos_depth + 1, first["label"], first["hop"]))
    return "FAIL_NOT_FIRST_LAYER", detail, classified


def parse_cas_date(raw):
    """cas 的 EndDate 各接口格式不一，逐个试；解析不出来返回 None，绝不猜。"""
    s = str(raw or "").strip()
    if not s:
        return None
    if s.isdigit():
        try:
            return datetime.datetime.fromtimestamp(int(s) / 1000.0)
        except (ValueError, OSError, OverflowError):
            return None
    s = s.replace("T", " ").replace("Z", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def check_bound_cert(cert_name, user_cert_name, cas_certs, cas_enabled):
    """
    C2（收窄后）：只查高防上**绑定的那张证书**的到期情况。

    [MUST] 范围边界——以下都不属于 C2，一律不判、不输出：
      · 实际下发给访问者的证书（openssl s_client）：有效性 / CN·SAN 域名匹配 / 证书链完整性
      · 「配了 https 端口却没绑证书」「绑了证书却没配 https 端口」这类配置一致性问题
      · 绑定证书与下发证书的到期时间比对
    C2 的数据源只有一个：DescribeWebRules[].CertName / UserCertName -> cas 的 EndDate / Expired。
    DescribeWebRules[].CertExpireTime 官方标注「暂不使用」，永远不读。
    """
    bound = (cert_name or "").strip() or (user_cert_name or "").strip()
    res = {"verdict": "NOT_DETECTED", "days_left": None, "bound_cert_name": bound,
           "end_date": None, "expired_flag": None, "source": None, "detail": ""}

    if not bound:
        res["verdict"] = "NOT_APPLICABLE_NO_CERT_BOUND"
        res["detail"] = ("该域名的转发规则没有绑定证书（CertName 与 UserCertName 均为空），"
                         "没有「绑定证书」可查到期时间，C2 不适用")
        return res

    if not cas_enabled:
        res["detail"] = ("绑定了证书 %s，但取数阶段没有查 cas，拿不到绑定证书的到期时间。"
                         "cas 是 C2 唯一的数据源，请补跑 fetch_config.py"
                         "（默认带 cas，除非显式传 --no-cas）" % bound)
        return res

    rec, matched_by = None, None
    for key in (cert_name, user_cert_name):
        key = (key or "").strip()
        if key and cas_certs and key in cas_certs:
            rec, matched_by = cas_certs[key], key
            break
    if rec is None:
        res["verdict"] = "NOT_APPLICABLE_NO_CAS_DATA"
        res["detail"] = ("绑定了证书 %s，但本账号的 cas 里找不到对应记录"
                         "（证书可能不在本账号、已删除，或当前身份无 cas 读权限）。"
                         "账号侧给不出评判所需的信息，C2 不适用——不是「证书没问题」，也不编造日期" % bound)
        return res

    res["matched_by"] = matched_by
    res["source"] = "cas"
    res["cert_id"] = rec.get("cert_id") or None
    res["cert_domain"] = rec.get("domain") or None
    res["expired_flag"] = rec.get("expired")
    end_raw = rec.get("end_date")
    res["end_date"] = str(end_raw) if end_raw else None

    if not end_raw:
        filled = ",".join(sorted(k for k in rec if rec.get(k) not in (None, ""))) or "-"
        res["verdict"] = "NOT_APPLICABLE_NO_CAS_DATA"
        res["detail"] = ("cas 里找到了证书 %s，但该记录没有到期时间（EndDate 为空；有值的字段: %s）。"
                         "账号侧给不出评判所需的信息，C2 不适用，不编造日期" % (bound, filled))
        return res

    dt = parse_cas_date(end_raw)
    if dt is None:
        res["detail"] = "cas 返回的到期时间 %r 无法解析成日期，不编造" % (end_raw,)
        return res

    days = (dt.date() - datetime.date.today()).days
    res["days_left"] = days
    res["end_date_iso"] = dt.strftime("%Y-%m-%d")
    flag = rec.get("expired")
    if flag is True or str(flag).lower() == "true":
        res["verdict"] = "FAIL_EXPIRED"
        res["detail"] = "绑定证书 %s 已过期（cas Expired=true，EndDate=%s）" % (bound, res["end_date_iso"])
    elif days < 0:
        res["verdict"] = "FAIL_EXPIRED"
        res["detail"] = "绑定证书 %s 已于 %s 过期（%d 天）" % (bound, res["end_date_iso"], -days)
    elif days <= 7:
        res["verdict"] = "FAIL_CRITICAL"
        res["detail"] = "绑定证书 %s 将在 %s 到期，仅剩 %d 天，需立即续签" % (bound, res["end_date_iso"], days)
    elif days <= 30:
        res["verdict"] = "WARN_EXPIRING"
        res["detail"] = "绑定证书 %s 将在 %s 到期，剩 %d 天，建议排期续签" % (bound, res["end_date_iso"], days)
    else:
        res["verdict"] = "PASS"
        res["detail"] = "绑定证书 %s 到期时间 %s，剩 %d 天" % (bound, res["end_date_iso"], days)
    return res


def check_health_local(domain, endpoints):
    """C4 本地兜底：单出口 curl。必须标注为单出口，且内地/海外对比记 NOT_DETECTED。"""
    if not shutil.which("curl"):
        return None
    if not endpoints:
        endpoints = [{"proxy_type": "https", "port": 443}]
    results = []
    for ep in endpoints[:4]:
        scheme = "http" if ep.get("proxy_type") in ("http", "websocket", "ws") else "https"
        port = ep.get("port")
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        url = "%s://%s%s/" % (scheme, domain, "" if default_port else ":%s" % port)
        fmt = "%{http_code}|%{time_namelookup}|%{time_connect}|%{time_appconnect}|%{time_starttransfer}|%{time_total}"
        rc, out, err = run(["curl", "-sS", "-k", "-o", "/dev/null", "-w", fmt,
                            "--connect-timeout", "6", "--max-time", "12", url], timeout=20)
        parts = out.strip().split("|") if out.strip() else []
        code = None
        if parts:
            try:
                code = int(parts[0])
            except ValueError:
                code = None
        ok = code is not None and 200 <= code < 400
        results.append({
            "url": url, "http_code": code,
            "time_namelookup": parts[1] if len(parts) > 1 else "",
            "time_connect": parts[2] if len(parts) > 2 else "",
            "time_appconnect": parts[3] if len(parts) > 3 else "",
            "time_starttransfer": parts[4] if len(parts) > 4 else "",
            "time_total": parts[5] if len(parts) > 5 else "",
            "verdict": "HEALTHY" if ok else "FAIL",
            "error": "" if rc == 0 else (err or "").strip()[:150],
            "perspective": "LOCAL_SINGLE_EGRESS",
        })
    return results


def expand_wildcards(domain, samples):
    if not domain.startswith("*."):
        return [domain], False
    parent = domain[2:]
    if not samples:
        return [], True
    return ["%s.%s" % (s.strip(), parent) for s in samples if s.strip()], True


def main():
    ap = argparse.ArgumentParser(description="本地取证：CNAME 链路 + 证书 + 单出口健康")
    ap.add_argument("--config", required=True, help="fetch_config.py 产出的 access-config.json")
    ap.add_argument("--out", default="local-evidence.json")
    ap.add_argument("--domains", default="", help="可选，逗号分隔，只检查这些域名")
    ap.add_argument("--resolvers", default=DEFAULT_RESOLVERS,
                    help="对比用的公共 DNS，逗号分隔；传空串则只用系统 resolver")
    ap.add_argument("--with-health", action="store_true", help="额外跑本地 curl 单出口健康检查(C4 兜底)")
    ap.add_argument("--wildcard-samples", default="",
                    help="泛域名展开用的子域前缀，逗号分隔，如 www,api；不传则泛域名记 NOT_DETECTED")
    ap.add_argument("--extra-domains", default="",
                    help="无七层转发规则也要检查的域名，逗号分隔（**追加**，不是过滤）。"
                         "用于经用户显式同意的降级/无基线公网观测：合成一条空规则后走同一套判定，"
                         "cname 为空 -> C1 判 NOT_APPLICABLE_NO_WEB_RULE，不会伪造基线")
    ap.add_argument("--extra-region", default="",
                    help="--extra-domains 的归属地域；留空则从 config 的 web_rules/instances 推断")
    args = ap.parse_args()

    if not shutil.which("dig"):
        print("[ERROR] 本机无 dig，C1/C3 无法取证。请安装 bind-utils/dnsutils 后重试。", file=sys.stderr)
        sys.exit(2)
    with open(args.config) as f:
        cfg_all = json.load(f)

    web_rules = cfg_all.get("web_rules") or []
    sched_rules = cfg_all.get("scheduler_rules") or []
    antiddos_ips = set(cfg_all.get("antiddos_ips") or [])
    # 各 region 的实例数：实例为 0 而规则还在时，高防 IP 比对集合必然不完整，
    # C1 的 IP 落点结论要在报告里标注需人工确认
    region_inst_count = {}
    for i in cfg_all.get("instances") or []:
        region_inst_count[i.get("region")] = region_inst_count.get(i.get("region"), 0) + 1
    cas_certs = cfg_all.get("cas_certs") or {}
    exp = cfg_all.get("expected_cnames") or {}
    web_cnames = set(norm_name(c) for c in exp.get("web_rule_cnames") or [])
    sched_cnames = set(norm_name(c) for c in exp.get("scheduler_cnames") or [])
    extra = [d.strip() for d in (args.extra_domains or "").split(",") if d.strip()]
    if not web_rules and not extra:
        print("[ERROR] config 里没有七层域名（web_rules 为空），且未用 --extra-domains 指定目标，"
              "无可检查对象。", file=sys.stderr)
        sys.exit(2)
    if extra:
        known = set(w.get("domain") or "" for w in web_rules)
        region = args.extra_region
        if not region:
            for w in web_rules:
                if w.get("region"):
                    region = w.get("region")
                    break
        if not region:
            for i in (cfg_all.get("instances") or []):
                if i.get("region"):
                    region = i.get("region")
                    break
        web_rules = list(web_rules) + [{
            "domain": d, "cname": "", "endpoints": [],
            "origin_ips_v4": [], "origin_ips_v6": [],
            "region": region, "cert_name": "", "user_cert_name": "", "baseline_free": True,
        } for d in extra if d not in known]

    only = set(d.strip() for d in args.domains.split(",") if d.strip())
    resolvers = [r.strip() for r in args.resolvers.split(",") if r.strip()]
    samples = [s.strip() for s in args.wildcard_samples.split(",") if s.strip()]

    domains_out, warnings, not_detected = [], [], []
    for w in web_rules:
        # --extra-domains 是用户显式点名的目标，不受 --domains 过滤器约束
        if only and w["domain"] not in only and not w.get("baseline_free"):
            continue
        targets, was_wildcard = expand_wildcards(w["domain"], samples)
        if was_wildcard and not targets:
            not_detected.append({"domain": w["domain"], "check": "C1/C2/C3/C4",
                                 "reason": "泛域名无法直接解析/做 SNI/HTTP 探测；需用户提供子域名清单、"
                                           "或用 --wildcard-samples 抽样、或明确跳过"})
            warnings.append("泛域名 %s 未检查（需用户选择处理方式）" % w["domain"])
            continue

        cfg = dict(w)
        cfg["_web_cnames"] = web_cnames
        cfg["_sched_cnames"] = sched_cnames
        cfg["_region_instance_count"] = region_inst_count.get(w.get("region"), 0)
        cfg["_antiddos_ips"] = sorted(antiddos_ips)
        origin_ips = set(w.get("origin_ips_v4") or []) | set(w.get("origin_ips_v6") or [])

        for target in targets:
            entry = {
                "domain": target,
                "configured_domain": w["domain"],
                "is_wildcard_sample": was_wildcard,
                "region": w.get("region"),
                "config": {
                    "cname": w.get("cname"), "cert_name": w.get("cert_name"),
                    "user_cert_name": w.get("user_cert_name"), "has_https": w.get("has_https"),
                    "endpoints": w.get("endpoints"), "origin_ips_v4": w.get("origin_ips_v4"),
                    "origin_rs_types": w.get("origin_rs_types"),
                },
                "resolutions": {},
            }

            # 多解析器取证：系统 resolver + 公共 DNS，用于暴露分线路/解析不一致
            base = resolve_chain(target)
            entry["resolutions"]["system"] = base
            for rs in resolvers:
                r = resolve_chain(target, resolver=rs)
                if r.get("error") and not r.get("cnames") and not r.get("ips_v4"):
                    warnings.append("解析器 %s 对 %s 查询失败（%s），已跳过该解析器视角" % (rs, target, r["error"]))
                    continue
                entry["resolutions"][rs] = r

            chain = base
            ip_cls = classify_ips((chain.get("ips_v4") or []) + (chain.get("ips_v6") or []),
                                  origin_ips, antiddos_ips)
            sched_rule, sched_hop = find_scheduler_rule(chain.get("cnames") or [], sched_rules)
            entry["ip_classification"] = ip_cls
            entry["matched_scheduler_rule"] = ({"rule_name": sched_rule.get("rule_name"),
                                                "rule_type": sched_rule.get("rule_type"),
                                                "rule_type_label": sched_rule.get("rule_type_label"),
                                                "cname": sched_hop,
                                                "has_effective_ddos_line": sched_rule.get("has_effective_ddos_line")}
                                               if sched_rule else None)

            v, d = judge_c1(cfg, chain, ip_cls, sched_rule)
            entry["c1"] = {"verdict": v, "detail": d, "first_hop": chain.get("first_hop"),
                           "cnames": chain.get("cnames"),
                           "final_ips_v4": chain.get("ips_v4"), "final_ips_v6": chain.get("ips_v6")}

            # 各解析器视角是否互相矛盾 —— 分线路解析/DNS 污染/TTL 切换中的信号，不能被多数派平均掉。
            # [MUST] 比对「首跳 CNAME + IP 落点归类」，绝不比对最终 IP 列表本身：
            # CDN/GSLB 域名在不同解析器下天然返回不同 IP，比 IP 列表会对所有 CDN 域名误报「解析不一致」。
            sigs = []
            for rs, r in entry["resolutions"].items():
                if r.get("error"):
                    continue
                rcls = classify_ips((r.get("ips_v4") or []) + (r.get("ips_v6") or []),
                                    origin_ips, antiddos_ips)
                sig = json.dumps({"first_hop": r.get("first_hop"),
                                  "hop_count": len(r.get("cnames") or []),
                                  "hit_origin": rcls["hit_origin"],
                                  "hit_antiddos_ip": rcls["hit_antiddos_ip"]},
                                 sort_keys=True, ensure_ascii=False)
                sigs.append((rs, sig))
            distinct = set(s for _, s in sigs)
            if len(distinct) > 1:
                entry["c1"]["point_inconsistent"] = [{"resolver": rs, "signature": json.loads(s)}
                                                     for rs, s in sigs]
                if v.startswith("PASS"):
                    entry["c1"]["verdict"] = "WARN_POINT_INCONSISTENT"
                    entry["c1"]["detail"] = ("不同解析器的首跳 CNAME 或 IP 落点归类不一致（%s）；"
                                             "可能存在分线路解析、TTL 切换中或 DNS 污染，不能判一致"
                                             % "; ".join("%s=%s" % (rs, s) for rs, s in sigs))
                else:
                    entry["c1"]["detail"] += "；且不同解析器视角不一致，详见 point_inconsistent"
            elif sigs:
                # 按实测描述，不套用「最终 IP 因 GSLB 不同属正常」这类未经验证的说法。
                # 实测（本账号 7 个高防 CNAME × 4 个 resolver）显示高防 CNAME 返回的 IP 往往完全相同；
                # 不比最终 IP 的真正理由是：配置侧无法枚举高防 CNAME 背后的完整 IP 集合
                # （DescribeInstances[].Ip 实测只有 2 个，而 6 个能解析的高防 CNAME 里有 4 个落在集合外），
                # 且这些 A 记录由高防侧控制、会随节点调度/迁移变化。
                ipsets = sorted(set(tuple(sorted((r.get("ips_v4") or []) + (r.get("ips_v6") or [])))
                                    for r in entry["resolutions"].values() if not r.get("error")))
                if len(ipsets) <= 1:
                    entry["c1"]["resolver_agreement"] = (
                        "%s 个解析器的首跳、落点归类与最终 IP 全部一致（%s）"
                        % (len(sigs), ",".join(ipsets[0]) if ipsets and ipsets[0] else "无 A/AAAA"))
                else:
                    entry["c1"]["resolver_agreement"] = (
                        "%s 个解析器的首跳与落点归类一致，但最终 IP 不同：%s。首跳一致即判一致——"
                        "配置侧无法枚举高防 CNAME 背后的完整 IP 集合，且这些 A 记录由高防侧控制、"
                        "会随节点调度/迁移变化。[注意] 落点归类只有 源站/高防IP/其他 三个桶，"
                        "若这些 IP 分属不同服务商，本脚本看不出差别，需人工确认"
                        % (len(sigs), " | ".join(",".join(t) or "无" for t in ipsets)))

            v3, d3, hops = judge_c3(cfg, chain, ip_cls, sched_rule)
            # 只有「首跳」无法归类才真正阻塞 C3 定论；链路后段的 GSLB 中间域名不影响第一层判定
            first_unknown = bool(hops) and hops[0]["class"] == "unknown"
            entry["c3"] = {"verdict": v3, "detail": d3, "chain_classified": hops,
                           "needs_agent_review": first_unknown,
                           "unknown_hops": [h["hop"] for h in hops if h["class"] == "unknown"]}

            # C2（收窄后）：只查「高防上绑定的那张证书」的到期时间，数据源只有 cas。
            # 不读实际下发的证书、不判域名匹配与证书链完整性、也不判「配了 https 却没绑证书」
            # 这类配置一致性问题——那些都不在 C2 范围内（见 references/check-criteria.md §C2）。
            entry["c2"] = check_bound_cert(w.get("cert_name"), w.get("user_cert_name"),
                                           cas_certs, bool(cfg_all.get("with_cas")))

            if args.with_health:
                entry["c4_local"] = check_health_local(target, w.get("endpoints") or [])
            else:
                entry["c4_local"] = None
            entry["c4_note"] = ("本地 curl 只是单出口视角，内地/海外对比必须由云拨测提供；"
                                "ProbeMode=local 时 C4 的内地vs海外对比记 NOT_DETECTED")
            domains_out.append(entry)

    verdicts = {}
    for e in domains_out:
        for k in ("c1", "c3", "c2"):
            v = (e.get(k) or {}).get("verdict", "NOT_DETECTED")
            verdicts.setdefault(k, {}).setdefault(v, 0)
            verdicts[k][v] += 1

    out = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resolvers_used": ["system"] + resolvers,
        "config_source": os.path.abspath(args.config),
        "domains": domains_out,
        "not_detected": not_detected,
        "verdict_counts": verdicts,
        "warnings": warnings,
        "summary": {
            "domains_checked": len(domains_out),
            "c1_applicable": sum(v for k, v in verdicts.get("c1", {}).items()
                                 if not k.startswith("NOT_APPLICABLE")),
            "c1_not_applicable": sum(v for k, v in verdicts.get("c1", {}).items()
                                     if k.startswith("NOT_APPLICABLE")),
            "c1_fail": sum(v for k, v in verdicts.get("c1", {}).items() if k.startswith("FAIL")),
            "c1_warn": sum(v for k, v in verdicts.get("c1", {}).items() if k.startswith("WARN")),
            "c2_fail": sum(v for k, v in verdicts.get("c2", {}).items() if k.startswith("FAIL")),
            "c2_warn": sum(v for k, v in verdicts.get("c2", {}).items() if k.startswith("WARN")),
            "c2_not_applicable": sum(v for k, v in verdicts.get("c2", {}).items()
                                     if k.startswith("NOT_APPLICABLE")),
            "c3_not_applicable": sum(v for k, v in verdicts.get("c3", {}).items()
                                     if k.startswith("NOT_APPLICABLE")),
            "c3_fail": sum(v for k, v in verdicts.get("c3", {}).items() if k.startswith("FAIL")),
            "c3_warn": sum(v for k, v in verdicts.get("c3", {}).items() if k.startswith("WARN")),
            "c3_info": sum(v for k, v in verdicts.get("c3", {}).items() if k.startswith("INFO")),
            "not_detected": len(not_detected),
            "needs_agent_review": sum(1 for e in domains_out if (e.get("c3") or {}).get("needs_agent_review")),
        },
    }
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("", file=sys.stderr)
    print("[DONE] 写入 %s" % args.out, file=sys.stderr)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2), file=sys.stderr)
    for e in domains_out:
        print("  %s | C1=%s | C2=%s(%s天) | C3=%s" % (
            e["domain"],
            (e.get("c1") or {}).get("verdict"),
            (e.get("c2") or {}).get("verdict"),
            (e.get("c2") or {}).get("days_left"),
            (e.get("c3") or {}).get("verdict")), file=sys.stderr)
    if out["summary"]["needs_agent_review"]:
        print("\n[MUST] 有 %s 个域名的 CNAME 链存在 UNKNOWN_HOP，脚本不下结论，"
              "请按 references/check-criteria.md 研判后再写报告" % out["summary"]["needs_agent_review"], file=sys.stderr)
    for cid, key, why in (
            ("C2", "c2_not_applicable", "\u8d26\u53f7\u4fa7\u7ed9\u4e0d\u51fa\u8bc1\u4e66\u5230\u671f\u4fe1\u606f\uff08\u672a\u7ed1\u8bc1\u4e66\uff0c\u6216 cas \u91cc\u627e\u4e0d\u5230/\u65e0 EndDate\uff09"),
            ("C3", "c3_not_applicable", "\u843d\u70b9\u65e2\u4e0d\u547d\u4e2d\u6e90\u7ad9\u4e5f\u4e0d\u547d\u4e2d\u8d26\u53f7\u5df2\u77e5\u9ad8\u9632 IP\uff0c\u8d26\u53f7\u4fa7\u4fe1\u606f\u4e0d\u8db3\u4ee5\u5224\u5b9a\u5f52\u5c5e")):
        cnt = out["summary"].get(key, 0)
        if cnt:
            doms = [e["domain"] for e in domains_out
                    if str((e.get(cid.lower()) or {}).get("verdict", "")).startswith("NOT_APPLICABLE")]
            print("\n[MUST] \u6709 %s \u4e2a\u57df\u540d\u7684 %s \u4e0d\u9002\u7528\uff1a%s\u3002"
                  "\n      \u4e0d\u9002\u7528 \u2260 \u672a\u68c0\u6d4b \u2260 \u901a\u8fc7\uff1a\u524d\u8005\u662f\u672c\u8d26\u53f7\u7ed9\u4e0d\u51fa\u8bc4\u5224\u4f9d\u636e\uff0c"
                  "\u540e\u8005\u662f\u4f9d\u636e\u5728\u4f46\u89c2\u6d4b\u6ca1\u505a\u6210\u3002\u62a5\u544a\u91cc\u4e09\u8005\u5fc5\u987b\u5206\u5f00\u5217\uff0c"
                  "\u4e14\u4e0d\u9002\u7528\u9879\u4e0d\u8fdb\u8be5\u9879\u8986\u76d6\u7387\u7684\u5206\u6bcd\u3002"
                  "\n      \u6d89\u53ca\u57df\u540d: %s"
                  % (cnt, cid, why, ",".join(doms[:20]) + ("..." if len(doms) > 20 else "")), file=sys.stderr)
    if out["summary"]["c1_not_applicable"]:
        na = [e["domain"] for e in domains_out
              if str((e.get("c1") or {}).get("verdict", "")).startswith("NOT_APPLICABLE")]
        print("\n[MUST] 有 %s 个域名 C1 前置条件不满足（转发规则未关联高防 IP，DescribeWebRules.Cname 为空），"
              "C1 记 NOT_APPLICABLE_NO_CNAME_ASSIGNED —— 既不是 FAIL 也不是 PASS。"
              "\n      报告必须逐条带上处置提示「先关联高防 IP 生成 CNAME，再切 DNS」，C2/C3/C4 照常检查。"
              "\n      C1 覆盖率的分母只算适用的 %s 个域名，这 %s 个要在报告里单独列出分支分布，不能静默丢弃。"
              "\n      涉及域名: %s"
              % (len(na), out["summary"]["c1_applicable"], len(na), ",".join(na[:20]) + ("..." if len(na) > 20 else "")),
              file=sys.stderr)
    if warnings:
        print("\n[WARNINGS]:", file=sys.stderr)
        for x in warnings[:20]:
            print("  - %s" % x, file=sys.stderr)


if __name__ == "__main__":
    main()
