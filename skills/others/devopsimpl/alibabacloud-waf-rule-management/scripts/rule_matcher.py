#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WAF 规则条件匹配诊断引擎

核心功能：将规则配置的每个条件与 SLS 日志逐一对比，
找出不匹配项并给出诊断结论。

用法:
  python rule_matcher.py --rule-json '{"config":...}' --log-json '{"real_client_ip":"1.2.3.4",...}'
  python rule_matcher.py --rule-file rule.json --log-file log.json

输入:
  --rule-json / --rule-file : 规则完整配置（rule_fetcher.py 输出中的 rule 字段）
  --log-json  / --log-file  : SLS 日志条目（get_waf_log.py 输出中的单条日志）
  --xff-status              : XFF 配置状态 (0=未开启, 1=xff第一个值, 2=自定义header)
  --defense-scene           : 防护场景覆写（可选，默认从规则中读取）

输出:
  JSON 格式的诊断结果，包含：
  - conclusion: 诊断结论
  - summary: 摘要
  - pre_checks: 前置检查（白名单冲突、防护对象绑定、观察规则）
  - condition_results: 每个条件的匹配/不匹配详情
  - is_cc_rule: 是否为频率规则
  - unrecorded_fields: 无法在日志中验证的字段
  - recommendations: 处置建议
"""

import argparse
import ipaddress
import json
import re
import sys
from urllib.parse import urlparse, parse_qs

# ==============================================================
# 常量映射（从 test1.py 提取并整理）
# ==============================================================

# 规则配置 key -> SLS 日志字段名
KEY_TO_SLS_FIELD = {
    'URL': 'request_uri',
    'IP': 'real_client_ip',
    'Referer': 'http_referer',
    'User-Agent': 'http_user_agent',
    'Query String': 'request_uri',      # 规则底层叫 Params
    'content_length': 'request_length',
    'Http-Method': 'request_method',
    'URLPath': 'request_path',
    'Query-Arg': 'request_uri',          # Query String Parameter
    'Extension': 'request_uri',          # File Extension
    'Filename': 'request_uri',
    'Host': 'host',
    'abroadRegionList': 'remote_country_id',
    'cnRegionList': 'remote_region_id',
}

# 规则 key -> 控制台显示名称
KEY_TO_DISPLAY_NAME = {
    'URL': 'URI',
    'IP': 'IP',
    'Referer': 'Referer',
    'User-Agent': 'User-Agent',
    'Params': 'Query String',
    'Cookie': 'Cookie',
    'Content-Type': 'Content-Type',
    'Content-Length': 'Content-Length',
    'X-Forwarded-For': 'X-Forwarded-For',
    'Post-Body': 'Body',
    'Http-Method': 'Http-Method',
    'Header': 'Header',
    'URLPath': 'URI Path',
    'Query-Arg': 'Query String Parameter',
    'Server-Port': 'Server-Port',
    'Extension': 'File Extension',
    'Filename': 'Filename',
    'Host': 'Host',
    'Cookie-Exact': 'Cookie-Name',
    'Post-Arg': 'Body Parameter',
    'Query String': 'Query String',
}

# 日志中无法查询到的字段
NOT_RECORDED_FIELDS = [
    "Cookie", "Content-Type", "X-Forwarded-For",
    "Post-Body", "Header", "Server-Port", "Cookie-Exact", "Post-Arg"
]

# 操作符描述映射
OP_DESC = {
    "not-contain": "不包含",
    "contain": "包含",
    "none": "不存在",
    "not-exist": "不存在",
    "ne": "不等于",
    "eq": "等于",
    "lt": "小于",
    "gt": "大于",
    "len-lt": "长度小于",
    "len-eq": "长度等于",
    "len-gt": "长度大于",
    "not-match": "不匹配",
    "match-one": "等于多值之一",
    "all-not-match": "都不等于任一值",
    "all-not-contain": "都不包含任一值",
    "contain-one": "包含多值之一",
    "not-regex": "正则不匹配",
    "regex": "正则匹配",
    "all-not-regex": "都不正则匹配",
    "regex-one": "正则匹配其中之一",
    "prefix-match": "前缀匹配",
    "suffix-match": "后缀匹配",
    "empty": "内容为空",
    "exists": "字段存在",
    "inl": "在列表中",
    "equal": "等于",
    "not-equal": "不等于",
}

# 白名单标签 -> 模块描述
WHITELIST_TAGS = {
    'waf': '全部模块',
    'customrule': '自定义规则',
    'blacklist': 'IP 黑名单',
    'antiscan': '扫描防护',
    'regular': '规则防护',
    'regular_rule': '基于特定规则的基础防护规则',
    'regular_type': '基于特定模块的基础防护规则',
    'major_protection': '重保场景防护',
    'cc': 'CC 防护',
    'region_block': '区域封禁',
    'antibot_scene': 'BOT 场景防护',
    'dlp': '信息泄露防护',
    'tamperproof': '网页防篡改',
    'spike_throttle': '洪峰限流防护',
    'regular_field': '指定字段',
    'sema': '语义防护',
    'compliance': '协议合规',
    'deeplearning': '深度学习引擎',
    'account': '账户安全',
    'normalized': '主动防御',
    'bot_intelligence': '爬虫威胁情报',
    'bot_algorithm': '典型爬虫行为识别',
    'bot_wxbb': 'App防护',
    'antifraud': '数据风控',
}

# final_plugin -> 模块描述
FINAL_PLUGIN_DESC = {
    "waf": "Web核心防护规则",
    "acl": "IP黑名单、自定义规则",
    "cc": "CC防护",
    "antiscan": "扫描防护",
    "dlp": "防敏感信息泄露",
    "scene": "场景化配置（APP也包括在内）",
    "intelligence": "爬虫威胁情报",
    "wxbb": "App防护",
    "sema": "语义防护",
    "scc_gdrl": "洪峰限流",
    "major_protection": "重保场景防护",
    "compliance": "协议违背（协议合规）",
}

# 地域代码映射（中国省份 + 国际国家）
REGION_MAPPING = {
    "110000": "北京市", "120000": "天津市", "130000": "河北省",
    "140000": "山西省", "150000": "内蒙古自治区", "210000": "辽宁省",
    "220000": "吉林省", "230000": "黑龙江省", "310000": "上海市",
    "320000": "江苏省", "330000": "浙江省", "340000": "安徽省",
    "350000": "福建省", "360000": "江西省", "370000": "山东省",
    "410000": "河南省", "420000": "湖北省", "430000": "湖南省",
    "440000": "广东省", "450000": "广西壮族自治区", "460000": "海南省",
    "500000": "重庆市", "510000": "四川省", "520000": "贵州省",
    "530000": "云南省", "540000": "西藏自治区", "610000": "陕西省",
    "620000": "甘肃省", "630000": "青海省", "640000": "宁夏回族自治区",
    "650000": "新疆维吾尔自治区",
    "MO_01": "中国澳门", "HK_01": "中国香港", "TW_01": "中国台湾",
    # 国际国家代码
    "AD": "安道尔", "AE": "阿拉伯联合酋长国", "AF": "阿富汗",
    "AG": "安提瓜和巴布达", "AI": "安圭拉", "AL": "阿尔巴尼亚",
    "AM": "亚美尼亚", "AO": "安哥拉", "AP": "亚太地区",
    "AQ": "南极洲", "AR": "阿根廷", "AS": "美属萨摩亚",
    "AT": "奥地利", "AU": "澳大利亚", "AW": "阿鲁巴",
    "AX": "奥兰群岛", "AZ": "阿塞拜疆", "BA": "波黑",
    "BB": "巴巴多斯", "BD": "孟加拉共和国", "BE": "比利时",
    "BF": "布基纳法索", "BG": "保加利亚", "BH": "巴林",
    "BI": "布隆迪共和国", "BJ": "贝宁", "BL": "圣巴泰勒米岛",
    "BM": "百慕大群岛", "BN": "文莱达鲁萨兰国", "BO": "玻利维亚",
    "BQ": "博内尔、圣尤斯蒂休斯和萨巴", "BR": "巴西", "BS": "巴哈马群岛",
    "BT": "不丹", "BW": "博茨瓦纳", "BY": "白俄罗斯",
    "BZ": "伯利兹", "CA": "加拿大", "CD": "刚果民主共和国",
    "CF": "中非共和国", "CG": "刚果", "CH": "瑞士",
    "CI": "科特迪瓦", "CK": "库克群岛", "CL": "智利",
    "CM": "喀麦隆", "CN": "中国", "CO": "哥伦比亚",
    "CR": "哥斯达黎加", "CU": "古巴", "CV": "佛得角",
    "CW": "库拉索", "CX": "澳大利亚圣诞岛", "CY": "塞浦路斯",
    "CZ": "捷克共和国", "DE": "德国", "DJ": "吉布提",
    "DK": "丹麦", "DM": "多米尼克国", "DO": "多米尼加共和国",
    "DZ": "阿尔及利亚", "EC": "厄瓜多尔", "EE": "爱沙尼亚",
    "EG": "埃及", "ER": "厄立特里亚", "ES": "西班牙",
    "ET": "埃塞俄比亚", "FI": "芬兰", "FJ": "斐济",
    "FK": "马尔维纳斯群岛", "FM": "密克罗尼西亚联邦", "FO": "法罗群岛",
    "FR": "法国", "GA": "加蓬", "GB": "英国",
    "GD": "格林纳达", "GE": "格鲁吉亚", "GF": "法属圭亚那",
    "GG": "根西岛", "GH": "加纳", "GI": "直布罗陀",
    "GL": "格陵兰岛", "GM": "冈比亚共和国", "GN": "几内亚",
    "GP": "瓜德罗普", "GQ": "赤道几内亚", "GR": "希腊",
    "GT": "危地马拉", "GU": "关岛", "GW": "几内亚比绍共和国",
    "GY": "圭亚那", "HN": "洪都拉斯", "HR": "克罗地亚",
    "HT": "海地", "HU": "匈牙利", "ID": "印度尼西亚",
    "IE": "爱尔兰", "IL": "以色列", "IM": "马恩岛",
    "IN": "印度", "IO": "英属印度洋领地", "IQ": "伊拉克共和国",
    "IR": "伊朗", "IS": "冰岛", "IT": "意大利",
    "JE": "泽西岛", "JM": "牙买加", "JO": "约旦",
    "JP": "日本", "KE": "肯尼亚", "KG": "吉尔吉斯斯坦",
    "KH": "柬埔寨", "KI": "基里巴斯", "KM": "科摩罗",
    "KN": "圣基茨和尼维斯联邦", "KP": "朝鲜", "KR": "韩国",
    "KW": "科威特", "KY": "开曼群岛", "KZ": "哈萨克斯坦",
    "LA": "老挝", "LB": "黎巴嫩", "LC": "圣卢西亚",
    "LI": "列支敦士登", "LK": "斯里兰卡", "LR": "利比里亚",
    "LS": "莱索托", "LT": "立陶宛", "LU": "卢森堡",
    "LV": "拉脱维亚", "LY": "利比亚", "MA": "摩洛哥",
    "MC": "摩纳哥", "MD": "摩尔多瓦", "ME": "黑山共和国",
    "MF": "圣马丁", "MG": "马达加斯加", "MH": "马绍尔群岛",
    "MK": "马其顿", "ML": "马里", "MM": "缅甸",
    "MN": "蒙古", "MP": "北马里亚纳群岛", "MQ": "马提尼克岛",
    "MR": "毛里塔尼亚", "MS": "蒙塞拉特岛", "MT": "马耳他",
    "MU": "毛里求斯", "MV": "马尔代夫", "MW": "马拉维",
    "MX": "墨西哥", "MY": "马来西亚", "MZ": "莫桑比克",
    "NA": "纳米比亚", "NC": "新喀里多尼亚", "NE": "尼日尔",
    "NF": "诺福克岛", "NG": "尼日利亚", "NI": "尼加拉瓜",
    "NL": "荷兰", "NO": "挪威", "NP": "尼泊尔",
    "NR": "瑙鲁", "NU": "纽埃岛", "NZ": "新西兰",
    "OM": "阿曼", "PA": "巴拿马", "PE": "秘鲁",
    "PF": "法属波利尼西亚", "PG": "巴布亚新几内亚", "PH": "菲律宾",
    "PK": "巴基斯坦", "PL": "波兰", "PM": "圣皮埃尔和密克隆岛",
    "PR": "波多黎各", "PS": "巴勒斯坦", "PT": "葡萄牙",
    "PW": "帕劳", "PY": "巴拉圭", "QA": "卡塔尔",
    "RE": "留尼旺岛", "RO": "罗马尼亚", "RS": "塞尔维亚",
    "RU": "俄罗斯", "RW": "卢旺达", "SA": "沙特阿拉伯",
    "SB": "所罗门群岛", "SC": "塞舌尔", "SD": "苏丹",
    "SE": "瑞典", "SG": "新加坡", "SI": "斯洛文尼亚",
    "SK": "斯洛伐克", "SL": "塞拉利昂", "SM": "圣马力诺",
    "SN": "塞内加尔", "SO": "索马里", "SR": "苏里南",
    "SS": "南苏丹", "ST": "圣多美和普林西比", "SV": "萨尔瓦多",
    "SX": "荷属圣马丁", "SY": "阿拉伯叙利亚共和国", "SZ": "斯威士兰",
    "TC": "特克斯和凯科斯岛", "TD": "乍得", "TG": "多哥",
    "TH": "泰国", "TJ": "塔吉克斯坦", "TK": "托克劳群岛",
    "TL": "东帝汶", "TM": "土库曼斯坦", "TN": "突尼斯",
    "TO": "汤加", "TR": "土耳其", "TT": "特立尼达和多巴哥",
    "TV": "图瓦卢", "TZ": "坦桑尼亚", "UA": "乌克兰",
    "UG": "乌干达", "UM": "美国本土外小岛屿", "US": "美国",
    "UY": "乌拉圭", "UZ": "乌兹别克斯坦", "VA": "梵蒂冈",
    "VC": "圣文森特和格林纳丁斯", "VE": "委内瑞拉", "VG": "英属维尔京群岛",
    "VI": "美属维尔京群岛", "VN": "越南", "VU": "瓦努阿图",
    "WF": "瓦利斯群岛和富图纳群岛", "WS": "萨摩亚群岛",
    "YE": "也门", "YT": "马约特岛", "ZA": "南非",
    "ZM": "赞比亚", "ZW": "津巴布韦",
}


# ==============================================================
# 匹配引擎核心函数
# ==============================================================

def match_condition(config_value, op, log_value):
    """单条件匹配判断

    Args:
        config_value: 规则中配置的值（字符串或列表）
        op: 操作符（如 eq, contain, regex 等）
        log_value: SLS 日志中对应字段的值

    Returns:
        匹配成功返回 True 或匹配到的具体值（match-one/contain-one 场景），
        不匹配返回 False
    """
    log_value = str(log_value) if log_value is not None else ""
    config_value = str(config_value) if config_value is not None else ""

    try:
        if op in ('eq', 'equal'):
            return log_value == config_value
        elif op in ('ne', 'not-equal'):
            return log_value != config_value
        elif op == 'contain':
            return config_value in log_value
        elif op == 'not-contain':
            return config_value not in log_value
        elif op in ('none', 'not-exist'):
            return config_value == '' and log_value == ''
        elif op == 'exists':
            return True  # 走到这里说明字段存在
        elif op == 'empty':
            return log_value.strip() == ""
        elif op == 'lt':
            return float(log_value) < float(config_value)
        elif op == 'gt':
            return float(log_value) > float(config_value)
        elif op == 'len-lt':
            return len(log_value) < int(config_value)
        elif op == 'len-eq':
            return len(log_value) == int(config_value)
        elif op == 'len-gt':
            return len(log_value) > int(config_value)
        elif op == 'regex':
            return re.search(config_value, log_value) is not None
        elif op == 'not-regex':
            return re.search(config_value, log_value) is None
        elif op == 'prefix-match':
            return log_value.startswith(config_value)
        elif op == 'suffix-match':
            return log_value.endswith(config_value)
        elif op == 'match-one':
            for v in config_value.split(','):
                if v.strip() == log_value:
                    return v.strip()
            return False
        elif op == 'all-not-match':
            return log_value not in [v.strip() for v in config_value.split(',')]
        elif op == 'inl':
            return log_value in [v.strip() for v in config_value.split(',')]
        elif op == 'contain-one':
            for v in config_value.split(','):
                if v.strip() in log_value:
                    return v.strip()
            return False
        elif op == 'all-not-contain':
            return all(v.strip() not in log_value for v in config_value.split(','))
        elif op == 'regex-one':
            return any(re.search(v.strip(), log_value) for v in config_value.split(','))
        elif op == 'all-not-regex':
            return all(re.search(v.strip(), log_value) is None for v in config_value.split(','))
        else:
            return False
    except Exception:
        return False


def check_ip_in_list(ip_to_check, ip_list):
    """检查 IP 是否在 IP/CIDR 列表中

    Args:
        ip_to_check: 要检查的 IP 地址字符串
        ip_list: IP 地址或 CIDR 列表（可以是逗号分隔字符串或 list）

    Returns:
        dict: {matched: bool, match_type: "ip"/"cidr"/"", matched_entry: ""}
    """
    if isinstance(ip_list, str):
        ip_list = [s.strip() for s in ip_list.split(',') if s.strip()]
    elif isinstance(ip_list, list):
        # 处理嵌套列表 ["1.1.1.1", "2.2.2.0/24"]
        flat = []
        for item in ip_list:
            if isinstance(item, str):
                flat.extend(s.strip() for s in item.split(',') if s.strip())
            else:
                flat.append(str(item))
        ip_list = flat

    try:
        ip = ipaddress.ip_address(ip_to_check)
    except ValueError:
        return {"matched": False, "match_type": "", "matched_entry": ""}

    for entry in ip_list:
        entry = entry.strip()
        if not entry:
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
            if ip in network:
                mtype = "ip" if network.num_addresses == 1 else "cidr"
                return {"matched": True, "match_type": mtype, "matched_entry": entry}
        except ValueError:
            try:
                if ip == ipaddress.ip_address(entry):
                    return {"matched": True, "match_type": "ip", "matched_entry": entry}
            except ValueError:
                continue

    return {"matched": False, "match_type": "", "matched_entry": ""}


def check_region_match(region_list_str, region_id):
    """区域封禁匹配判断

    Args:
        region_list_str: 逗号分隔的区域代码列表字符串
        region_id: 日志中的区域 ID

    Returns:
        str or None: 匹配的区域代码，未匹配返回 None
    """
    if not region_list_str or not region_id:
        return None
    region_id_str = str(region_id)
    for part in region_list_str.split(','):
        stripped = part.strip()
        if stripped and region_id_str.startswith(stripped):
            return stripped
    return None


# ==============================================================
# 诊断主流程
# ==============================================================

def analyze_conditions(rule_config, log_entry, defense_scene):
    """逐条分析规则条件与日志是否匹配

    Args:
        rule_config: 规则的 config 字典（包含 conditions 等）
        log_entry: SLS 单条日志
        defense_scene: 防护场景

    Returns:
        dict: {
            matched_conditions: [...],   # 已匹配的条件
            mismatched_conditions: [...], # 不匹配的条件
            unrecorded_fields: [...],     # 无法验证的字段
            has_recorded_fields: bool,    # 是否有可验证的已知字段
            is_cc_rule: bool,             # 是否频率规则
            cc_config: dict or None       # 频率配置
        }
    """
    conditions = rule_config.get('conditions', [])
    matched = []
    mismatched = []
    unrecorded = []
    has_recorded = False

    # 判断是否频率规则
    is_cc = rule_config.get('ccStatus') == 1 or defense_scene == 'custom_cc'
    cc_config = rule_config.get('ratelimit') if is_cc else None

    for cond in conditions:
        rule_key = cond.get('key', '')
        rule_op = cond.get('opValue', '')
        rule_value = cond.get('values', cond.get('value', ''))
        sub_key = cond.get('subKey', '')

        # 跳过无法在日志中验证的字段
        if rule_key in NOT_RECORDED_FIELDS:
            unrecorded.append({
                "field": rule_key,
                "display_name": KEY_TO_DISPLAY_NAME.get(rule_key, rule_key),
                "op": rule_op,
                "op_desc": OP_DESC.get(rule_op, rule_op),
                "config_value": rule_value,
                "reason": "该字段未记录在 SLS 日志中，无法验证"
            })
            continue

        has_recorded = True
        sls_field = KEY_TO_SLS_FIELD.get(rule_key, rule_key)
        log_value = log_entry.get(sls_field, '')

        # 特殊处理: Query-Arg 需要解析 URI 参数
        if rule_key == 'Query-Arg' and sub_key:
            try:
                parsed = urlparse(str(log_value))
                query_dict = parse_qs(parsed.query)
                log_value = query_dict.get(sub_key, [''])[0]
            except Exception:
                log_value = ''

        display_name = KEY_TO_DISPLAY_NAME.get(rule_key, rule_key)
        op_desc = OP_DESC.get(rule_op, rule_op)

        # 处理列表值
        config_val_str = rule_value
        if isinstance(rule_value, list):
            config_val_str = ','.join(str(v) for v in rule_value)

        # IP 字段特殊处理（使用 CIDR 匹配）
        if rule_key == 'IP':
            ip_check = check_ip_in_list(str(log_value), rule_value)
            if rule_op == 'contain':
                is_matched = ip_check['matched']
            elif rule_op == 'not-contain':
                is_matched = not ip_check['matched']
            else:
                is_matched = match_condition(config_val_str, rule_op, log_value)

            result_item = {
                "field": rule_key,
                "display_name": display_name,
                "sls_field": sls_field,
                "op": rule_op,
                "op_desc": op_desc,
                "config_value": config_val_str,
                "log_value": str(log_value),
                "is_ip_field": True,
            }
            if is_matched:
                result_item["matched"] = True
                if ip_check['matched']:
                    result_item["matched_entry"] = ip_check['matched_entry']
                matched.append(result_item)
            else:
                result_item["matched"] = False
                mismatched.append(result_item)
            continue

        # 通用匹配逻辑
        match_result = match_condition(config_val_str, rule_op, log_value)
        result_item = {
            "field": rule_key,
            "display_name": display_name,
            "sls_field": sls_field,
            "op": rule_op,
            "op_desc": op_desc,
            "config_value": config_val_str,
            "log_value": str(log_value),
        }
        if sub_key:
            result_item["sub_key"] = sub_key

        if match_result:
            result_item["matched"] = True
            if isinstance(match_result, str):
                result_item["matched_value"] = match_result
            matched.append(result_item)
        else:
            result_item["matched"] = False
            mismatched.append(result_item)

    return {
        "matched_conditions": matched,
        "mismatched_conditions": mismatched,
        "unrecorded_fields": unrecorded,
        "has_recorded_fields": has_recorded,
        "is_cc_rule": is_cc,
        "cc_config": cc_config,
    }


def check_whitelist_conflict(log_entry, defense_scene, bypass_config=None):
    """检查白名单冲突

    如果流量已命中白名单（bypass_matched_ids 非空），且当前诊断的不是白名单规则本身，
    说明白名单导致了规则不生效。

    Args:
        log_entry: SLS 日志条目
        defense_scene: 当前规则的防护场景
        bypass_config: 白名单规则的配置（可选，用于精确判断）

    Returns:
        dict or None: 白名单冲突信息
    """
    bypass_ids = log_entry.get('bypass_matched_ids', '')
    upstream_status = log_entry.get('upstream_status', '')

    if not bypass_ids or bypass_ids == 'null':
        return None

    # 白名单规则自身不存在"被白名单跳过"的问题
    if defense_scene == 'whitelist':
        return None

    # upstream_status 为 '-' 时通常是 WAF 直接返回，非白名单相关
    if upstream_status == '-':
        return None

    result = {
        "has_conflict": True,
        "bypass_matched_ids": bypass_ids,
        "message": f"当前流量已命中白名单（规则ID: {bypass_ids}），导致拦截规则不生效"
    }

    # 如果有白名单详细配置，做精确判断
    if bypass_config:
        tags = bypass_config.get('tags', [])
        custom_rules = bypass_config.get('customRules', [])
        blacklist_rules = bypass_config.get('blacklistRules', [])

        if defense_scene == 'custom_acl':
            if 'customrule' in tags or 'waf' in tags:
                result["reason"] = "白名单跳过了自定义规则模块"
        elif defense_scene == 'ip_blacklist':
            if 'blacklist' in tags or 'waf' in tags:
                result["reason"] = "白名单跳过了IP黑名单模块"
        elif defense_scene in tags:
            result["reason"] = f"白名单跳过了 {WHITELIST_TAGS.get(defense_scene, defense_scene)} 模块"

        result["whitelist_tags"] = tags
        result["whitelist_custom_rules"] = custom_rules
        result["whitelist_blacklist_rules"] = blacklist_rules

    return result


def check_monitor_rules(log_entry):
    """检查是否命中了观察模式的规则

    Args:
        log_entry: SLS 日志条目

    Returns:
        dict or None: 观察规则信息
    """
    matched_rules_detail = log_entry.get('matched_rules_detail', '')
    if not matched_rules_detail or matched_rules_detail == 'null':
        return None

    try:
        detail = json.loads(matched_rules_detail)
    except (json.JSONDecodeError, TypeError):
        return None

    user_id = log_entry.get('user_id', '')
    matched_host = log_entry.get('matched_host', '')
    key = f"{matched_host}@{user_id}"

    rules_list = detail.get(key, [])
    monitor_hits = []
    for rule in rules_list:
        # test=True 表示命中了观察模式的规则
        if rule.get('test') is True:
            plugin = rule.get('plugin', '')
            # 映射 plugin -> 日志字段名
            log_field_map = {
                'compliance': 'waf_test',
                'acl': 'acl_test',
                'cc': 'cc_test',
            }
            monitor_hits.append({
                "rule_id": rule.get('id'),
                "plugin": plugin,
                "log_field": log_field_map.get(plugin, f'{plugin}_test'),
                "action": rule.get('action', 'default'),
            })

    if not monitor_hits:
        return None

    return {
        "has_monitor_hit": True,
        "monitor_rules": monitor_hits,
        "message": f"流量命中了 {len(monitor_hits)} 条观察模式规则"
    }


def diagnose_ip_blacklist(rule_config, log_entry, xff_status):
    """IP 黑名单规则专用诊断

    Args:
        rule_config: 规则的 config
        log_entry: SLS 日志条目
        xff_status: XFF 配置状态

    Returns:
        dict: 诊断结论
    """
    ip_list = rule_config.get('remoteAddr', [])
    real_ip = log_entry.get('real_client_ip', '')
    final_plugin = log_entry.get('final_plugin', '')
    final_rule_id = log_entry.get('final_rule_id', '')

    ip_check = check_ip_in_list(real_ip, ip_list)

    if not ip_check['matched']:
        xff_hint = _get_xff_hint(real_ip, xff_status)
        return {
            "conclusion": "not_matched",
            "summary": f"IP {real_ip} 不在黑名单列表中",
            "detail": f"real_client_ip ({real_ip}) 不在黑名单配置 {ip_list} 中",
            "xff_hint": xff_hint,
        }
    else:
        if final_plugin == 'acl' and str(final_rule_id) != '':
            return {
                "conclusion": "matched_but_other_rule",
                "summary": f"IP {real_ip} 已在黑名单中（匹配 {ip_check['matched_entry']}），但流量被其他 ACL 规则 {final_rule_id} 优先拦截",
                "detail": "当流量同时命中多个 ACL 规则时，最先配置的规则优先生效",
            }
        return {
            "conclusion": "matched_timing",
            "summary": f"IP {real_ip} 已在黑名单中（匹配 {ip_check['matched_entry']}），规则应生效",
            "detail": "推测是规则刚配置，需要约1分钟下发生效",
        }


def diagnose_region_block(rule_config, log_entry):
    """区域封禁规则专用诊断

    Args:
        rule_config: 规则的 config
        log_entry: SLS 日志条目

    Returns:
        dict: 诊断结论
    """
    abroad_list = rule_config.get('abroadRegionList', '')
    cn_list = rule_config.get('cnRegionList', [])
    remote_country = log_entry.get('remote_country_id', '')
    remote_region = log_entry.get('remote_region_id', '')

    # 检查海外区域
    if abroad_list and check_region_match(abroad_list, remote_country):
        region_name = REGION_MAPPING.get(remote_country, remote_country)
        return {
            "conclusion": "matched_timing",
            "summary": f"源IP所在区域({region_name})已匹配区域封禁规则",
            "detail": "推测是规则刚配置，需要约1分钟下发生效",
        }

    # 检查国内区域
    if cn_list:
        cn_list_str = ','.join(str(c) for c in cn_list) if isinstance(cn_list, list) else str(cn_list)
        if check_region_match(cn_list_str, remote_region):
            region_name = REGION_MAPPING.get(remote_region, remote_region)
            return {
                "conclusion": "matched_timing",
                "summary": f"源IP所在区域({region_name})已匹配区域封禁规则",
                "detail": "推测是规则刚配置，需要约1分钟下发生效",
            }
        # 特殊处理: CN 代表所有国内
        if 'CN' in cn_list and remote_country == 'CN':
            region_name = REGION_MAPPING.get(remote_region, remote_region)
            return {
                "conclusion": "matched_timing",
                "summary": f"源IP属于国内区域({region_name})，已匹配区域封禁规则",
                "detail": "推测是规则刚配置，需要约1分钟下发生效",
            }

    # 未匹配
    region_name = REGION_MAPPING.get(remote_region, REGION_MAPPING.get(remote_country, f"{remote_country}/{remote_region}"))
    return {
        "conclusion": "not_matched",
        "summary": f"源IP所在区域({region_name})不在区域封禁配置中",
        "detail": "请检查区域封禁规则的配置是否包含该区域",
    }


def diagnose_whitelist(rule_config, log_entry, rule_id):
    """白名单规则专用诊断

    白名单不生效的场景：
    1. 条件字段不匹配
    2. 源站返回405（非WAF拦截）
    3. 跳过模块不匹配
    4. 未知字段不匹配

    Args:
        rule_config: 规则的 config
        log_entry: SLS 日志条目
        rule_id: 白名单规则 ID

    Returns:
        dict: 诊断结论
    """
    bypass_ids = log_entry.get('bypass_matched_ids', '')
    upstream_status = log_entry.get('upstream_status', '')
    final_plugin = log_entry.get('final_plugin', '')
    final_rule_id = log_entry.get('final_rule_id', '')
    final_rule_type = log_entry.get('final_rule_type', '')

    # 检查白名单是否已经命中
    if str(rule_id) in str(bypass_ids):
        if upstream_status == '405':
            return {
                "conclusion": "already_matched_origin_405",
                "summary": f"白名单规则已命中（bypass_matched_ids 包含 {rule_id}），但当前 405 是源站返回的",
                "detail": "upstream_status=405 说明源站返回了 405，非 WAF 拦截。白名单规则实际已生效。",
            }
        return {
            "conclusion": "already_matched",
            "summary": f"白名单规则已命中（bypass_matched_ids: {bypass_ids}）",
            "detail": "白名单规则已经生效",
        }

    # 获取白名单跳过模块配置
    tags = rule_config.get('tags', [])
    tags_desc = [WHITELIST_TAGS.get(t, t) for t in tags]
    regular_rules = rule_config.get('regularRules', [])
    regular_types = rule_config.get('regularTypes', [])

    # 检查跳过模块是否匹配当前拦截模块
    module_mismatch = None
    if final_plugin:
        plugin_desc = FINAL_PLUGIN_DESC.get(final_plugin, final_plugin)

        if final_plugin == 'waf':
            if not any(t in tags for t in ['regular', 'regular_rule', 'regular_type', 'waf']):
                module_mismatch = {
                    "type": "module_not_covered",
                    "detail": f"流量被 {plugin_desc} 拦截，但白名单跳过模块为 {tags_desc}，未包含 Web 核心防护规则"
                }
            elif 'regular_rule' in tags and str(final_rule_id) not in [str(r) for r in regular_rules]:
                module_mismatch = {
                    "type": "specific_rule_not_covered",
                    "detail": f"白名单配置了跳过特定规则 {regular_rules}，但流量命中的规则是 {final_rule_id}"
                }
            elif 'regular_type' in tags and final_rule_type not in regular_types:
                module_mismatch = {
                    "type": "specific_type_not_covered",
                    "detail": f"白名单配置了跳过特定类型 {regular_types}，但流量命中的类型是 {final_rule_type}"
                }

        elif final_plugin == 'acl':
            acl_rule_type = log_entry.get('acl_rule_type', '')
            tag_name = 'customrule' if acl_rule_type == 'custom' else acl_rule_type
            custom_rules = rule_config.get('customRules', [])
            if tag_name not in tags and 'waf' not in tags:
                if str(final_rule_id) not in [str(r) for r in custom_rules]:
                    module_mismatch = {
                        "type": "module_not_covered",
                        "detail": f"流量被 {plugin_desc}({acl_rule_type}) 拦截，但白名单跳过模块为 {tags_desc}"
                    }

        else:
            if final_plugin not in tags and 'waf' not in tags:
                module_mismatch = {
                    "type": "module_not_covered",
                    "detail": f"流量被 {plugin_desc} 拦截，但白名单跳过模块为 {tags_desc}，未包含该模块"
                }

    if module_mismatch:
        return {
            "conclusion": "module_mismatch",
            "summary": module_mismatch["detail"],
            "detail": module_mismatch["detail"],
            "module_info": {
                "final_plugin": final_plugin,
                "whitelist_tags": tags,
                "whitelist_tags_desc": tags_desc,
            }
        }

    return None  # 返回 None 表示模块匹配正常，需要继续检查条件


def _get_xff_hint(real_ip, xff_status):
    """根据 XFF 配置状态生成 IP 相关的提示信息"""
    if xff_status == 0:
        return (
            f"如果 {real_ip} 不是真实出口 IP，需要在 WAF 控制台的接入配置中"
            f"开启「WAF前是否有七层代理（高防/CDN等）」配置项"
        )
    elif xff_status == 1:
        return (
            f"已开启 XFF 取值。如果 {real_ip} 不是真实出口 IP，"
            f"说明可能存在 XFF 伪造，可尝试通过自定义 header 获取真实 IP"
        )
    elif xff_status == 2:
        return (
            f"已开启自定义 header 取值。如果 {real_ip} 不是真实出口 IP，"
            f"说明当前 header 中未记录真实 IP，请检查 header 配置"
        )
    return ""


def build_mismatch_detail(item, xff_status):
    """为不匹配的条件构建详细描述"""
    field = item['field']
    display = item['display_name']
    op_desc = item['op_desc']
    config_val = item['config_value']
    log_val = item['log_value']

    detail = f"规则要求 {display} {op_desc}: {config_val}，但流量中实际值为: {log_val}"

    if field == 'IP':
        xff_hint = _get_xff_hint(log_val, xff_status)
        if xff_hint:
            detail += f"。{xff_hint}"

    return detail


def diagnose(rule_json, log_json, defense_scene=None, xff_status=0, bypass_config=None, full_check=False):
    """完整诊断入口

    Args:
        rule_json: 规则完整信息（rule_fetcher.py 输出的 rule 字段）
        log_json: SLS 单条日志（get_waf_log.py 输出的日志条目）
        defense_scene: 防护场景（可选，默认从规则中读取）
        xff_status: XFF 配置状态 (0/1/2)
        bypass_config: 命中的白名单规则配置（可选）
        full_check: 全量检查模式（默认False=快速返回，True=检查所有可能原因）

    Returns:
        dict: 完整诊断结果
    """
    rule_config = rule_json.get('config', {})
    if not defense_scene:
        defense_scene = rule_json.get('defense_scene', '')
    rule_id = rule_json.get('rule_id', '')

    result = {
        "success": True,
        "rule_id": rule_id,
        "defense_scene": defense_scene,
        "pre_checks": {},
        "condition_results": {},
        "recommendations": [],
        "all_issues": [],  # 全量检查模式：收集所有问题
    }

    # === 前置检查 1: 白名单冲突 ===
    whitelist_conflict = check_whitelist_conflict(log_json, defense_scene, bypass_config)
    if whitelist_conflict and whitelist_conflict.get('has_conflict'):
        result["pre_checks"]["whitelist_conflict"] = whitelist_conflict
        result["all_issues"].append({
            "issue_type": "whitelist_bypass",
            "severity": "critical",
            "summary": whitelist_conflict["message"],
            "recommendation": "检查并调整白名单规则，确保其不跳过当前需要拦截的模块"
        })
        result["recommendations"].append(
            "检查并调整白名单规则，确保其不跳过当前需要拦截的模块"
        )
        # 快速模式直接返回，全量模式继续检查
        if not full_check:
            result["conclusion"] = "whitelist_bypass"
            result["summary"] = whitelist_conflict["message"]
            return result

    # === 前置检查 2: 观察规则 ===
    monitor_info = check_monitor_rules(log_json)
    if monitor_info:
        result["pre_checks"]["monitor_rules"] = monitor_info
        result["all_issues"].append({
            "issue_type": "monitor_mode_hit",
            "severity": "warning",
            "summary": monitor_info["message"],
            "recommendation": "观察模式规则仅记录不拦截，如需拦截请修改规则动作为拦截"
        })

    # === 场景分支处理 ===

    # IP 黑名单
    if defense_scene in ('ip_blacklist', 'blacklist'):
        diag = diagnose_ip_blacklist(rule_config, log_json, xff_status)
        result["condition_results"] = diag
        result["all_issues"].append({
            "issue_type": diag["conclusion"],
            "severity": "critical" if diag["conclusion"] == "not_matched" else "info",
            "summary": diag["summary"],
            "detail": diag.get("detail", "")
        })
        if diag.get("xff_hint"):
            result["all_issues"].append({
                "issue_type": "xff_configuration",
                "severity": "warning",
                "summary": diag["xff_hint"]
            })
            result["recommendations"].append(diag["xff_hint"])
        
        if not full_check:
            result["conclusion"] = diag["conclusion"]
            result["summary"] = diag["summary"]
            return result
        # 全量模式：设置主要结论但继续检查
        result["conclusion"] = diag["conclusion"]
        result["summary"] = diag["summary"]
        # IP黑名单场景无后续检查，直接返回
        return result

    # 区域封禁
    if defense_scene == 'region_block':
        diag = diagnose_region_block(rule_config, log_json)
        result["condition_results"] = diag
        result["all_issues"].append({
            "issue_type": diag["conclusion"],
            "severity": "critical" if diag["conclusion"] == "not_matched" else "info",
            "summary": diag["summary"],
            "detail": diag.get("detail", "")
        })
        
        if not full_check:
            result["conclusion"] = diag["conclusion"]
            result["summary"] = diag["summary"]
            return result
        # 全量模式：设置主要结论但继续检查
        result["conclusion"] = diag["conclusion"]
        result["summary"] = diag["summary"]
        # 区域封禁场景无后续检查，直接返回
        return result

    # 白名单规则自身不生效
    if defense_scene == 'whitelist':
        whitelist_diag = diagnose_whitelist(rule_config, log_json, rule_id)
        if whitelist_diag:
            result["condition_results"] = whitelist_diag
            result["all_issues"].append({
                "issue_type": whitelist_diag["conclusion"],
                "severity": "critical",
                "summary": whitelist_diag["summary"],
                "detail": whitelist_diag.get("detail", "")
            })
            
            if not full_check:
                result["conclusion"] = whitelist_diag["conclusion"]
                result["summary"] = whitelist_diag["summary"]
                return result
            # 全量模式：设置主要结论但继续检查
            result["conclusion"] = whitelist_diag["conclusion"]
            result["summary"] = whitelist_diag["summary"]

    # === 通用条件分析（自定义规则、CC规则、白名单条件检查等）===
    analysis = analyze_conditions(rule_config, log_json, defense_scene)
    result["condition_results"] = {
        "matched": analysis["matched_conditions"],
        "mismatched": analysis["mismatched_conditions"],
    }
    result["unrecorded_fields"] = analysis["unrecorded_fields"]
    result["is_cc_rule"] = analysis["is_cc_rule"]
    if analysis["cc_config"]:
        result["cc_config"] = analysis["cc_config"]

    has_mismatch = len(analysis["mismatched_conditions"]) > 0
    has_unrecorded = len(analysis["unrecorded_fields"]) > 0
    has_recorded = analysis["has_recorded_fields"]
    is_cc = analysis["is_cc_rule"]

    # 生成诊断结论
    if has_mismatch:
        # 有不匹配的条件
        mismatch_details = []
        for item in analysis["mismatched_conditions"]:
            detail = build_mismatch_detail(item, xff_status)
            mismatch_details.append(detail)
    
        result["conclusion"] = "condition_mismatch"
        result["summary"] = "规则中各个匹配条件之间是「与」的关系。未命中规则的原因：" + "；".join(mismatch_details)
        result["mismatch_details"] = mismatch_details
            
        # 全量检查：添加到问题列表
        result["all_issues"].append({
            "issue_type": "condition_mismatch",
            "severity": "critical",
            "summary": "规则条件与流量不匹配",
            "details": mismatch_details,
            "recommendation": "检查规则配置的条件字段是否与请求特征一致"
        })

    elif not has_recorded and has_unrecorded:
        # 所有条件都是无法验证的字段
        unrecorded_names = [f['field'] for f in analysis['unrecorded_fields']]
        if monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "all_unrecorded_with_monitor"
            result["summary"] = (
                f"流量已命中观察规则 {monitor_rule['rule_id']}，"
                f"可在 WAF 控制台日志字段 {monitor_rule['log_field']} 中查看。"
                f"当前规则的所有条件字段 {unrecorded_names} 均未在日志中记录，无法完全验证。"
            )
        else:
            result["conclusion"] = "all_unrecorded"
            result["summary"] = (
                f"当前规则的所有条件字段 {unrecorded_names} 均未在日志中记录（如 body、cookie 等），"
                "无法通过日志验证匹配情况。"
            )
        result["recommendations"].append(
            f"建议在 WAF 控制台——日志服务——日志设置中勾选 {unrecorded_names} 字段，"
            "然后触发新流量并观察新的日志"
        )
        
        # 全量检查：添加到问题列表
        result["all_issues"].append({
            "issue_type": result["conclusion"],
            "severity": "warning",
            "summary": f"无法验证的字段：{unrecorded_names}",
            "recommendation": f"在日志设置中勾选 {unrecorded_names} 字段后重新测试"
        })

    elif has_recorded and not has_mismatch and has_unrecorded:
        # 已知字段全部匹配，但存在无法验证的字段
        unrecorded_names = [f['field'] for f in analysis['unrecorded_fields']]
        if is_cc:
            result["conclusion"] = "partial_match_cc_unrecorded"
            result["summary"] = (
                "日志中可验证的字段均匹配规则条件，但存在无法验证的字段和频率条件。"
                f"未记录字段: {unrecorded_names}。"
                "推测可能原因: 1) 未记录字段不匹配 2) 频率未达阈值 "
                "3) WAF 使用滚动窗口检测，非滑动窗口"
            )
        elif monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "partial_match_with_monitor"
            result["summary"] = (
                f"流量已命中观察规则 {monitor_rule['rule_id']}。"
                "日志中可验证的字段均匹配规则条件，"
                f"但 {unrecorded_names} 未在日志中记录，可能是这些字段不匹配导致规则不生效。"
            )
        else:
            result["conclusion"] = "partial_match_unrecorded"
            result["summary"] = (
                "日志中可验证的字段均匹配规则条件，"
                f"但 {unrecorded_names} 未在日志中记录，可能是这些字段不匹配导致规则不生效。"
            )
        result["recommendations"].append(
            f"建议在 WAF 控制台——日志服务——日志设置中勾选 {unrecorded_names} 字段，"
            "然后触发新流量并观察新的日志"
        )
        
        # 全量检查：添加到问题列表
        result["all_issues"].append({
            "issue_type": result["conclusion"],
            "severity": "warning",
            "summary": f"已知字段匹配，但未记录字段：{unrecorded_names}",
            "recommendation": f"在日志设置中勾选 {unrecorded_names} 字段后重新测试"
        })

    elif has_recorded and not has_mismatch and not has_unrecorded:
        # 所有条件全部匹配
        if is_cc:
            result["conclusion"] = "all_match_cc"
            result["summary"] = (
                "所有匹配条件均满足规则要求，但这是一条频率规则，"
                "可能是访问频率未达阈值或因滚动窗口检测机制导致未触发。"
                "WAF 使用滚动窗口（非滑动窗口），统计窗口以第一个请求到达时间为起点。"
            )
        elif monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "all_match_with_monitor"
            result["summary"] = (
                f"所有条件均匹配。流量已命中观察规则 {monitor_rule['rule_id']}（动作为观察）。"
                f"可在 WAF 控制台勾选日志字段 {monitor_rule['log_field']} 查看命中情况。"
            )
        else:
            final_plugin = log_json.get('final_plugin', '')
            final_rule_id_log = log_json.get('final_rule_id', '')
            if final_plugin == 'acl' and final_rule_id_log and str(final_rule_id_log) != str(rule_id):
                result["conclusion"] = "all_match_other_rule_priority"
                result["summary"] = (
                    f"所有条件均匹配。但流量已被另一条 ACL 规则 {final_rule_id_log} 优先拦截。"
                    "当多条 ACL 规则同时满足时，最先配置的规则优先生效。"
                )
            else:
                result["conclusion"] = "all_match_timing"
                result["summary"] = (
                    "所有条件均匹配规则要求。推测是规则配置时间不足，"
                    "规则配置/变更后底层需要约1分钟才能生效。"
                )
        
        # 全量检查：添加到问题列表
        if is_cc:
            result["all_issues"].append({
                "issue_type": "cc_frequency_not_reached",
                "severity": "warning",
                "summary": "频率未达阈值或滚动窗口机制",
                "recommendation": "检查CC防护频率配置，确认访问频率是否达到阈值"
            })
        elif monitor_info:
            result["all_issues"].append({
                "issue_type": "monitor_mode_action",
                "severity": "info",
                "summary": "规则已命中但动作为观察模式",
                "recommendation": "如需拦截请将规则动作修改为拦截"
            })
        else:
            final_plugin = log_json.get('final_plugin', '')
            final_rule_id_log = log_json.get('final_rule_id', '')
            if final_plugin == 'acl' and final_rule_id_log and str(final_rule_id_log) != str(rule_id):
                result["all_issues"].append({
                    "issue_type": "rule_priority_conflict",
                    "severity": "warning",
                    "summary": f"被其他ACL规则{final_rule_id_log}优先拦截",
                    "recommendation": "调整规则顺序，将当前规则移到更靠前的位置"
                })
            else:
                result["all_issues"].append({
                    "issue_type": "timing_delay",
                    "severity": "info",
                    "summary": "规则配置不足1分钟，可能尚未生效",
                    "recommendation": "等待约1分钟后重试"
                })
    else:
        result["conclusion"] = "unknown"
        result["summary"] = "无法确定规则不生效的原因，建议人工排查"

    # 白名单场景的额外模块匹配检查
    if defense_scene == 'whitelist' and not has_mismatch:
        whitelist_module_check = diagnose_whitelist(rule_config, log_json, rule_id)
        if whitelist_module_check:
            result["whitelist_module_check"] = whitelist_module_check
            result["conclusion"] = whitelist_module_check["conclusion"]
            result["summary"] = whitelist_module_check["summary"]

    return result


# ==============================================================
# CLI 入口
# ==============================================================

def main():
    parser = argparse.ArgumentParser(description='WAF 规则条件匹配诊断引擎')
    parser.add_argument('--rule-json', type=str, default=None,
                        help='规则 JSON 字符串')
    parser.add_argument('--log-json', type=str, default=None,
                        help='日志 JSON 字符串')
    parser.add_argument('--rule-file', type=str, default=None,
                        help='规则 JSON 文件路径')
    parser.add_argument('--log-file', type=str, default=None,
                        help='日志 JSON 文件路径')
    parser.add_argument('--xff-status', type=int, default=0,
                        help='XFF 配置状态 (0=未开启, 1=xff第一个值, 2=自定义header)')
    parser.add_argument('--defense-scene', type=str, default=None,
                        help='防护场景覆写（默认从规则中读取）')
    parser.add_argument('--bypass-config', type=str, default=None,
                        help='白名单规则配置 JSON 字符串（可选）')
    parser.add_argument('--full-check', action='store_true', default=False,
                        help='全量检查模式：检查所有可能原因并一次性输出（默认快速模式，发现主要问题即返回）')
    args = parser.parse_args()

    # 读取规则数据
    rule_data = None
    if args.rule_json:
        rule_data = json.loads(args.rule_json)
    elif args.rule_file:
        with open(args.rule_file, 'r', encoding='utf-8') as f:
            rule_data = json.load(f)
    else:
        parser.error("必须指定 --rule-json 或 --rule-file")

    # 读取日志数据
    log_data = None
    if args.log_json:
        log_data = json.loads(args.log_json)
    elif args.log_file:
        with open(args.log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    else:
        parser.error("必须指定 --log-json 或 --log-file")

    # 读取白名单配置
    bypass_cfg = None
    if args.bypass_config:
        bypass_cfg = json.loads(args.bypass_config)

    try:
        result = diagnose(
            rule_json=rule_data,
            log_json=log_data,
            defense_scene=args.defense_scene,
            xff_status=args.xff_status,
            bypass_config=bypass_cfg,
            full_check=args.full_check,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"诊断失败: {str(e)}"
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
