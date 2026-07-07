#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WAF Rule Condition Matching Diagnosis Engine

Core function: Compare each condition in the rule configuration with the SLS log entry by entry,
find mismatches and produce a diagnosis conclusion.

Usage:
  python rule_matcher.py --rule-json '{"config":...}' --log-json '{"real_client_ip":"1.2.3.4",...}'
  python rule_matcher.py --rule-file rule.json --log-file log.json

Inputs:
  --rule-json / --rule-file : Full rule configuration (the rule field from rule_fetcher.py output)
  --log-json  / --log-file  : SLS log entry (a single log entry from get_waf_log.py output)
  --xff-status              : XFF configuration status (0=disabled, 1=first xff value, 2=custom header)
  --defense-scene           : Defense scene override (optional, read from rule by default)

Output:
  JSON-formatted diagnosis result, containing:
  - conclusion: diagnosis conclusion
  - summary: summary
  - pre_checks: pre-checks (whitelist conflict, protection object binding, observe rules)
  - condition_results: match/mismatch details for each condition
  - is_cc_rule: whether it is a frequency rule
  - unrecorded_fields: fields that cannot be verified in the log
  - recommendations: handling suggestions
"""

import argparse
import ipaddress
import json
import re
import sys
from urllib.parse import urlparse, parse_qs

# ==============================================================
# Constant mappings (extracted and organized from test1.py)
# ==============================================================

# Rule config key -> SLS log field name
KEY_TO_SLS_FIELD = {
    'URL': 'request_uri',
    'IP': 'real_client_ip',
    'Referer': 'http_referer',
    'User-Agent': 'http_user_agent',
    'Query String': 'request_uri',      # Rule internally called Params
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

# Rule key -> console display name
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

# Fields not recorded in logs
NOT_RECORDED_FIELDS = [
    "Cookie", "Content-Type", "X-Forwarded-For",
    "Post-Body", "Header", "Server-Port", "Cookie-Exact", "Post-Arg"
]

# Operator description mapping
OP_DESC = {
    "not-contain": "does not contain",
    "contain": "contains",
    "none": "does not exist",
    "not-exist": "does not exist",
    "ne": "not equal",
    "eq": "equal",
    "lt": "less than",
    "gt": "greater than",
    "len-lt": "length less than",
    "len-eq": "length equal",
    "len-gt": "length greater than",
    "not-match": "does not match",
    "match-one": "equals one of multiple values",
    "all-not-match": "not equal to any value",
    "all-not-contain": "does not contain any value",
    "contain-one": "contains one of multiple values",
    "not-regex": "regex does not match",
    "regex": "regex match",
    "all-not-regex": "none regex match",
    "regex-one": "regex match one of",
    "prefix-match": "prefix match",
    "suffix-match": "suffix match",
    "empty": "content is empty",
    "exists": "field exists",
    "inl": "in list",
    "equal": "equal",
    "not-equal": "not equal",
}

# Whitelist tag -> module description
WHITELIST_TAGS = {
    'waf': 'All Modules',
    'customrule': 'Custom Rules',
    'blacklist': 'IP Blacklist',
    'antiscan': 'Anti-Scan',
    'regular': 'Rule Protection',
    'regular_rule': 'Rule-based Basic Protection',
    'regular_type': 'Module-based Basic Protection',
    'major_protection': 'Major Event Protection',
    'cc': 'CC Protection',
    'region_block': 'Region Block',
    'antibot_scene': 'BOT Scene Protection',
    'dlp': 'Data Loss Prevention',
    'tamperproof': 'Web Tamper Protection',
    'spike_throttle': 'Spike Throttle Protection',
    'regular_field': 'Specified Field',
    'sema': 'Semantic Protection',
    'compliance': 'Protocol Compliance',
    'deeplearning': 'Deep Learning Engine',
    'account': 'Account Security',
    'normalized': 'Active Defense',
    'bot_intelligence': 'Bot Threat Intelligence',
    'bot_algorithm': 'Bot Behavior Recognition',
    'bot_wxbb': 'App Protection',
    'antifraud': 'Anti-Fraud',
}

# final_plugin -> module description
FINAL_PLUGIN_DESC = {
    "waf": "Web Core Protection Rules",
    "acl": "IP Blacklist, Custom Rules",
    "cc": "CC Protection",
    "antiscan": "Anti-Scan",
    "dlp": "Data Loss Prevention",
    "scene": "Scene-based Configuration (including App)",
    "intelligence": "Bot Threat Intelligence",
    "wxbb": "App Protection",
    "sema": "Semantic Protection",
    "scc_gdrl": "Spike Throttle",
    "major_protection": "Major Event Protection",
    "compliance": "Protocol Violation (Compliance)",
}

# Region code mapping (Chinese provinces + international countries)
REGION_MAPPING = {
    "110000": "Beijing", "120000": "Tianjin", "130000": "Hebei",
    "140000": "Shanxi", "150000": "Inner Mongolia", "210000": "Liaoning",
    "220000": "Jilin", "230000": "Heilongjiang", "310000": "Shanghai",
    "320000": "Jiangsu", "330000": "Zhejiang", "340000": "Anhui",
    "350000": "Fujian", "360000": "Jiangxi", "370000": "Shandong",
    "410000": "Henan", "420000": "Hubei", "430000": "Hunan",
    "440000": "Guangdong", "450000": "Guangxi", "460000": "Hainan",
    "500000": "Chongqing", "510000": "Sichuan", "520000": "Guizhou",
    "530000": "Yunnan", "540000": "Tibet", "610000": "Shaanxi",
    "620000": "Gansu", "630000": "Qinghai", "640000": "Ningxia",
    "650000": "Xinjiang",
    "MO_01": "Macau", "HK_01": "Hong Kong", "TW_01": "Taiwan",
    # International country codes
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
    "AG": "Antigua and Barbuda", "AI": "Anguilla", "AL": "Albania",
    "AM": "Armenia", "AO": "Angola", "AP": "Asia-Pacific",
    "AQ": "Antarctica", "AR": "Argentina", "AS": "American Samoa",
    "AT": "Austria", "AU": "Australia", "AW": "Aruba",
    "AX": "Aland Islands", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina",
    "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium",
    "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BL": "Saint Barthelemy",
    "BM": "Bermuda", "BN": "Brunei", "BO": "Bolivia",
    "BQ": "Bonaire, Sint Eustatius and Saba", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus",
    "BZ": "Belize", "CA": "Canada", "CD": "DR Congo",
    "CF": "Central African Republic", "CG": "Congo", "CH": "Switzerland",
    "CI": "Ivory Coast", "CK": "Cook Islands", "CL": "Chile",
    "CM": "Cameroon", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "CV": "Cape Verde",
    "CW": "Curacao", "CX": "Christmas Island", "CY": "Cyprus",
    "CZ": "Czech Republic", "DE": "Germany", "DJ": "Djibouti",
    "DK": "Denmark", "DM": "Dominica", "DO": "Dominican Republic",
    "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia",
    "EG": "Egypt", "ER": "Eritrea", "ES": "Spain",
    "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji",
    "FK": "Falkland Islands", "FM": "Micronesia", "FO": "Faroe Islands",
    "FR": "France", "GA": "Gabon", "GB": "United Kingdom",
    "GD": "Grenada", "GE": "Georgia", "GF": "French Guiana",
    "GG": "Guernsey", "GH": "Ghana", "GI": "Gibraltar",
    "GL": "Greenland", "GM": "Gambia", "GN": "Guinea",
    "GP": "Guadeloupe", "GQ": "Equatorial Guinea", "GR": "Greece",
    "GT": "Guatemala", "GU": "Guam", "GW": "Guinea-Bissau",
    "GY": "Guyana", "HN": "Honduras", "HR": "Croatia",
    "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia",
    "IE": "Ireland", "IL": "Israel", "IM": "Isle of Man",
    "IN": "India", "IO": "British Indian Ocean Territory", "IQ": "Iraq",
    "IR": "Iran", "IS": "Iceland", "IT": "Italy",
    "JE": "Jersey", "JM": "Jamaica", "JO": "Jordan",
    "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan",
    "KH": "Cambodia", "KI": "Kiribati", "KM": "Comoros",
    "KN": "Saint Kitts and Nevis", "KP": "North Korea", "KR": "South Korea",
    "KW": "Kuwait", "KY": "Cayman Islands", "KZ": "Kazakhstan",
    "LA": "Laos", "LB": "Lebanon", "LC": "Saint Lucia",
    "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia",
    "LS": "Lesotho", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "LY": "Libya", "MA": "Morocco",
    "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro",
    "MF": "Saint Martin", "MG": "Madagascar", "MH": "Marshall Islands",
    "MK": "Macedonia", "ML": "Mali", "MM": "Myanmar",
    "MN": "Mongolia", "MP": "Northern Mariana Islands", "MQ": "Martinique",
    "MR": "Mauritania", "MS": "Montserrat", "MT": "Malta",
    "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi",
    "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique",
    "NA": "Namibia", "NC": "New Caledonia", "NE": "Niger",
    "NF": "Norfolk Island", "NG": "Nigeria", "NI": "Nicaragua",
    "NL": "Netherlands", "NO": "Norway", "NP": "Nepal",
    "NR": "Nauru", "NU": "Niue", "NZ": "New Zealand",
    "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PF": "French Polynesia", "PG": "Papua New Guinea", "PH": "Philippines",
    "PK": "Pakistan", "PL": "Poland", "PM": "Saint Pierre and Miquelon",
    "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal",
    "PW": "Palau", "PY": "Paraguay", "QA": "Qatar",
    "RE": "Reunion", "RO": "Romania", "RS": "Serbia",
    "RU": "Russia", "RW": "Rwanda", "SA": "Saudi Arabia",
    "SB": "Solomon Islands", "SC": "Seychelles", "SD": "Sudan",
    "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia",
    "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somalia", "SR": "Suriname",
    "SS": "South Sudan", "ST": "Sao Tome and Principe", "SV": "El Salvador",
    "SX": "Sint Maarten", "SY": "Syria", "SZ": "Eswatini",
    "TC": "Turks and Caicos Islands", "TD": "Chad", "TG": "Togo",
    "TH": "Thailand", "TJ": "Tajikistan", "TK": "Tokelau",
    "TL": "Timor-Leste", "TM": "Turkmenistan", "TN": "Tunisia",
    "TO": "Tonga", "TR": "Turkey", "TT": "Trinidad and Tobago",
    "TV": "Tuvalu", "TZ": "Tanzania", "UA": "Ukraine",
    "UG": "Uganda", "UM": "US Minor Outlying Islands", "US": "United States",
    "UY": "Uruguay", "UZ": "Uzbekistan", "VA": "Vatican",
    "VC": "Saint Vincent and the Grenadines", "VE": "Venezuela", "VG": "British Virgin Islands",
    "VI": "US Virgin Islands", "VN": "Vietnam", "VU": "Vanuatu",
    "WF": "Wallis and Futuna", "WS": "Samoa",
    "YE": "Yemen", "YT": "Mayotte", "ZA": "South Africa",
    "ZM": "Zambia", "ZW": "Zimbabwe",
}


# ==============================================================
# Matching engine core functions
# ==============================================================

def match_condition(config_value, op, log_value):
    """Single condition matching.

    Args:
        config_value: Configured value in the rule (string or list)
        op: Operator (e.g., eq, contain, regex, etc.)
        log_value: Corresponding field value from SLS log

    Returns:
        True or the matched value (for match-one/contain-one) on success,
        False on no match.
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
            return True  # Reaching here means the field exists
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
    """Check if an IP is in an IP/CIDR list.

    Args:
        ip_to_check: IP address string to check
        ip_list: IP address or CIDR list (comma-separated string or list)

    Returns:
        dict: {matched: bool, match_type: "ip"/"cidr"/"", matched_entry: ""}
    """
    if isinstance(ip_list, str):
        ip_list = [s.strip() for s in ip_list.split(',') if s.strip()]
    elif isinstance(ip_list, list):
        # Handle nested lists ["1.1.1.1", "2.2.2.0/24"]
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
    """Region block matching.

    Args:
        region_list_str: Comma-separated region code list string
        region_id: Region ID from the log

    Returns:
        str or None: Matched region code, or None if no match.
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
# Diagnosis main flow
# ==============================================================

def analyze_conditions(rule_config, log_entry, defense_scene):
    """Analyze rule conditions against log entry.

    Args:
        rule_config: Rule config dict (contains conditions, etc.)
        log_entry: Single SLS log entry
        defense_scene: Defense scene

    Returns:
        dict: {
            matched_conditions: [...],   # Matched conditions
            mismatched_conditions: [...], # Mismatched conditions
            unrecorded_fields: [...],     # Fields that cannot be verified
            has_recorded_fields: bool,    # Whether there are verifiable known fields
            is_cc_rule: bool,             # Whether it is a frequency rule
            cc_config: dict or None       # Frequency config
        }
    """
    conditions = rule_config.get('conditions', [])
    matched = []
    mismatched = []
    unrecorded = []
    has_recorded = False

    # Check if it is a frequency rule
    is_cc = rule_config.get('ccStatus') == 1 or defense_scene == 'custom_cc'
    cc_config = rule_config.get('ratelimit') if is_cc else None

    for cond in conditions:
        rule_key = cond.get('key', '')
        rule_op = cond.get('opValue', '')
        rule_value = cond.get('values', cond.get('value', ''))
        sub_key = cond.get('subKey', '')

        # Skip fields that cannot be verified in logs
        if rule_key in NOT_RECORDED_FIELDS:
            unrecorded.append({
                "field": rule_key,
                "display_name": KEY_TO_DISPLAY_NAME.get(rule_key, rule_key),
                "op": rule_op,
                "op_desc": OP_DESC.get(rule_op, rule_op),
                "config_value": rule_value,
                "reason": "This field is not recorded in SLS logs, cannot verify"
            })
            continue

        has_recorded = True
        sls_field = KEY_TO_SLS_FIELD.get(rule_key, rule_key)
        log_value = log_entry.get(sls_field, '')

        # Special handling: Query-Arg needs URI parameter parsing
        if rule_key == 'Query-Arg' and sub_key:
            try:
                parsed = urlparse(str(log_value))
                query_dict = parse_qs(parsed.query)
                log_value = query_dict.get(sub_key, [''])[0]
            except Exception:
                log_value = ''

        display_name = KEY_TO_DISPLAY_NAME.get(rule_key, rule_key)
        op_desc = OP_DESC.get(rule_op, rule_op)

        # Handle list values
        config_val_str = rule_value
        if isinstance(rule_value, list):
            config_val_str = ','.join(str(v) for v in rule_value)

        # IP field special handling (CIDR matching)
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

        # Generic matching logic
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
    """Check whitelist conflict.

    If traffic has already matched a whitelist (bypass_matched_ids is non-empty),
    and the current diagnosis is not for the whitelist rule itself,
    the whitelist caused the rule to not take effect.

    Args:
        log_entry: SLS log entry
        defense_scene: Defense scene of the current rule
        bypass_config: Whitelist rule config (optional, for precise judgment)

    Returns:
        dict or None: Whitelist conflict info
    """
    bypass_ids = log_entry.get('bypass_matched_ids', '')
    upstream_status = log_entry.get('upstream_status', '')

    if not bypass_ids or bypass_ids == 'null':
        return None

    # Whitelist rule itself does not have the "skipped by whitelist" problem
    if defense_scene == 'whitelist':
        return None

    # upstream_status of '-' usually means WAF direct response, not whitelist related
    if upstream_status == '-':
        return None

    result = {
        "has_conflict": True,
        "bypass_matched_ids": bypass_ids,
        "message": f"Current traffic matched a whitelist (rule ID: {bypass_ids}), causing the block rule to not take effect"
    }

    # If detailed whitelist config is available, do precise judgment
    if bypass_config:
        tags = bypass_config.get('tags', [])
        custom_rules = bypass_config.get('customRules', [])
        blacklist_rules = bypass_config.get('blacklistRules', [])

        if defense_scene == 'custom_acl':
            if 'customrule' in tags or 'waf' in tags:
                result["reason"] = "Whitelist skipped the custom rule module"
        elif defense_scene == 'ip_blacklist':
            if 'blacklist' in tags or 'waf' in tags:
                result["reason"] = "Whitelist skipped the IP blacklist module"
        elif defense_scene in tags:
            result["reason"] = f"Whitelist skipped the {WHITELIST_TAGS.get(defense_scene, defense_scene)} module"

        result["whitelist_tags"] = tags
        result["whitelist_custom_rules"] = custom_rules
        result["whitelist_blacklist_rules"] = blacklist_rules

    return result


def check_monitor_rules(log_entry):
    """Check if monitor-mode rules were hit.

    Args:
        log_entry: SLS log entry

    Returns:
        dict or None: Monitor rule info
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
        # test=True means a monitor-mode rule was hit
        if rule.get('test') is True:
            plugin = rule.get('plugin', '')
            # Map plugin -> log field name
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
        "message": f"Traffic hit {len(monitor_hits)} monitor-mode rule(s)"
    }


def diagnose_ip_blacklist(rule_config, log_entry, xff_status):
    """IP blacklist rule diagnosis.

    Args:
        rule_config: Rule config
        log_entry: SLS log entry
        xff_status: XFF configuration status

    Returns:
        dict: Diagnosis conclusion
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
            "summary": f"IP {real_ip} is not in the blacklist",
            "detail": f"real_client_ip ({real_ip}) is not in the blacklist config {ip_list}",
            "xff_hint": xff_hint,
        }
    else:
        if final_plugin == 'acl' and str(final_rule_id) != '':
            return {
                "conclusion": "matched_but_other_rule",
                "summary": f"IP {real_ip} is in the blacklist (matched {ip_check['matched_entry']}), but traffic was intercepted by another ACL rule {final_rule_id} first",
                "detail": "When traffic matches multiple ACL rules, the first configured rule takes effect",
            }
        return {
            "conclusion": "matched_timing",
            "summary": f"IP {real_ip} is in the blacklist (matched {ip_check['matched_entry']}), rule should take effect",
            "detail": "Likely the rule was just configured, needs about 1 minute to take effect",
        }


def diagnose_region_block(rule_config, log_entry):
    """Region block rule diagnosis.

    Args:
        rule_config: Rule config
        log_entry: SLS log entry

    Returns:
        dict: Diagnosis conclusion
    """
    abroad_list = rule_config.get('abroadRegionList', '')
    cn_list = rule_config.get('cnRegionList', [])
    remote_country = log_entry.get('remote_country_id', '')
    remote_region = log_entry.get('remote_region_id', '')

    # Check international regions
    if abroad_list and check_region_match(abroad_list, remote_country):
        region_name = REGION_MAPPING.get(remote_country, remote_country)
        return {
            "conclusion": "matched_timing",
            "summary": f"Source IP region ({region_name}) matched the region block rule",
            "detail": "Likely the rule was just configured, needs about 1 minute to take effect",
        }

    # Check domestic regions
    if cn_list:
        cn_list_str = ','.join(str(c) for c in cn_list) if isinstance(cn_list, list) else str(cn_list)
        if check_region_match(cn_list_str, remote_region):
            region_name = REGION_MAPPING.get(remote_region, remote_region)
            return {
                "conclusion": "matched_timing",
                "summary": f"Source IP region ({region_name}) matched the region block rule",
                "detail": "Likely the rule was just configured, needs about 1 minute to take effect",
            }
        # Special handling: CN represents all domestic regions
        if 'CN' in cn_list and remote_country == 'CN':
            region_name = REGION_MAPPING.get(remote_region, remote_region)
            return {
                "conclusion": "matched_timing",
                "summary": f"Source IP belongs to a domestic region ({region_name}), matched the region block rule",
                "detail": "Likely the rule was just configured, needs about 1 minute to take effect",
            }

    # No match
    region_name = REGION_MAPPING.get(remote_region, REGION_MAPPING.get(remote_country, f"{remote_country}/{remote_region}"))
    return {
        "conclusion": "not_matched",
        "summary": f"Source IP region ({region_name}) is not in the region block config",
        "detail": "Please check if the region block rule config includes this region",
    }


def diagnose_whitelist(rule_config, log_entry, rule_id):
    """Whitelist rule diagnosis.

    Scenarios where whitelist does not take effect:
    1. Condition field mismatch
    2. Origin returned 405 (not WAF block)
    3. Skip module mismatch
    4. Unknown field mismatch

    Args:
        rule_config: Rule config
        log_entry: SLS log entry
        rule_id: Whitelist rule ID

    Returns:
        dict: Diagnosis conclusion
    """
    bypass_ids = log_entry.get('bypass_matched_ids', '')
    upstream_status = log_entry.get('upstream_status', '')
    final_plugin = log_entry.get('final_plugin', '')
    final_rule_id = log_entry.get('final_rule_id', '')
    final_rule_type = log_entry.get('final_rule_type', '')

    # Check if whitelist already matched
    if str(rule_id) in str(bypass_ids):
        if upstream_status == '405':
            return {
                "conclusion": "already_matched_origin_405",
                "summary": f"Whitelist rule already matched (bypass_matched_ids contains {rule_id}), but the 405 was returned by the origin",
                "detail": "upstream_status=405 means the origin returned 405, not a WAF block. The whitelist rule is actually effective.",
            }
        return {
            "conclusion": "already_matched",
            "summary": f"Whitelist rule already matched (bypass_matched_ids: {bypass_ids})",
            "detail": "Whitelist rule is effective",
        }

    # Get whitelist skip module config
    tags = rule_config.get('tags', [])
    tags_desc = [WHITELIST_TAGS.get(t, t) for t in tags]
    regular_rules = rule_config.get('regularRules', [])
    regular_types = rule_config.get('regularTypes', [])

    # Check if skip module matches the current interception module
    module_mismatch = None
    if final_plugin:
        plugin_desc = FINAL_PLUGIN_DESC.get(final_plugin, final_plugin)

        if final_plugin == 'waf':
            if not any(t in tags for t in ['regular', 'regular_rule', 'regular_type', 'waf']):
                module_mismatch = {
                    "type": "module_not_covered",
                    "detail": f"Traffic was intercepted by {plugin_desc}, but whitelist skip modules are {tags_desc}, which do not include Web Core Protection Rules"
                }
            elif 'regular_rule' in tags and str(final_rule_id) not in [str(r) for r in regular_rules]:
                module_mismatch = {
                    "type": "specific_rule_not_covered",
                    "detail": f"Whitelist is configured to skip specific rules {regular_rules}, but the traffic matched rule is {final_rule_id}"
                }
            elif 'regular_type' in tags and final_rule_type not in regular_types:
                module_mismatch = {
                    "type": "specific_type_not_covered",
                    "detail": f"Whitelist is configured to skip specific types {regular_types}, but the traffic matched type is {final_rule_type}"
                }

        elif final_plugin == 'acl':
            acl_rule_type = log_entry.get('acl_rule_type', '')
            tag_name = 'customrule' if acl_rule_type == 'custom' else acl_rule_type
            custom_rules = rule_config.get('customRules', [])
            if tag_name not in tags and 'waf' not in tags:
                if str(final_rule_id) not in [str(r) for r in custom_rules]:
                    module_mismatch = {
                        "type": "module_not_covered",
                        "detail": f"Traffic was intercepted by {plugin_desc}({acl_rule_type}), but whitelist skip modules are {tags_desc}"
                    }

        else:
            if final_plugin not in tags and 'waf' not in tags:
                module_mismatch = {
                    "type": "module_not_covered",
                    "detail": f"Traffic was intercepted by {plugin_desc}, but whitelist skip modules are {tags_desc}, which do not include this module"
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

    return None  # Returns None means module match is normal, need to continue checking conditions


def _get_xff_hint(real_ip, xff_status):
    """Generate IP-related hints based on XFF configuration status."""
    if xff_status == 0:
        return (
            f"If {real_ip} is not the real egress IP, enable the "
            f"'Is there a Layer 7 proxy before WAF (Anti-DDoS/CDN, etc.)' option in the WAF console access config"
        )
    elif xff_status == 1:
        return (
            f"XFF value extraction is enabled. If {real_ip} is not the real egress IP, "
            f"XFF spoofing may exist. Try obtaining the real IP via a custom header"
        )
    elif xff_status == 2:
        return (
            f"Custom header value extraction is enabled. If {real_ip} is not the real egress IP, "
            f"the current header does not contain the real IP. Please check the header config"
        )
    return ""


def build_mismatch_detail(item, xff_status):
    """Build detailed description for mismatched conditions."""
    field = item['field']
    display = item['display_name']
    op_desc = item['op_desc']
    config_val = item['config_value']
    log_val = item['log_value']

    detail = f"Rule requires {display} {op_desc}: {config_val}, but actual traffic value is: {log_val}"

    if field == 'IP':
        xff_hint = _get_xff_hint(log_val, xff_status)
        if xff_hint:
            detail += f". {xff_hint}"

    return detail


def diagnose(rule_json, log_json, defense_scene=None, xff_status=0, bypass_config=None, full_check=False):
    """Complete diagnosis entry point.

    Args:
        rule_json: Complete rule info (rule field from rule_fetcher.py output)
        log_json: Single SLS log entry (from get_waf_log.py output)
        defense_scene: Defense scene (optional, read from rule by default)
        xff_status: XFF configuration status (0/1/2)
        bypass_config: Matched whitelist rule config (optional)
        full_check: Full check mode (default False=fast return, True=check all possible causes)

    Returns:
        dict: Complete diagnosis result
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
        "all_issues": [],  # Full check mode: collect all issues
    }

    # === Pre-check 1: Whitelist conflict ===
    whitelist_conflict = check_whitelist_conflict(log_json, defense_scene, bypass_config)
    if whitelist_conflict and whitelist_conflict.get('has_conflict'):
        result["pre_checks"]["whitelist_conflict"] = whitelist_conflict
        result["all_issues"].append({
            "issue_type": "whitelist_bypass",
            "severity": "critical",
            "summary": whitelist_conflict["message"],
            "recommendation": "Check and adjust the whitelist rule to ensure it does not skip the module that needs to intercept"
        })
        result["recommendations"].append(
            "Check and adjust the whitelist rule to ensure it does not skip the module that needs to intercept"
        )
        # Fast mode returns immediately, full mode continues checking
        if not full_check:
            result["conclusion"] = "whitelist_bypass"
            result["summary"] = whitelist_conflict["message"]
            return result

    # === Pre-check 2: Monitor rules ===
    monitor_info = check_monitor_rules(log_json)
    if monitor_info:
        result["pre_checks"]["monitor_rules"] = monitor_info
        result["all_issues"].append({
            "issue_type": "monitor_mode_hit",
            "severity": "warning",
            "summary": monitor_info["message"],
            "recommendation": "Monitor mode rules only log, not block. To block, change the rule action to block"
        })

    # === Scene branch processing ===

    # IP blacklist
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
        # Full mode: set main conclusion but continue checking
        result["conclusion"] = diag["conclusion"]
        result["summary"] = diag["summary"]
        # IP blacklist scene has no further checks, return directly
        return result

    # Region block
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
        # Full mode: set main conclusion but continue checking
        result["conclusion"] = diag["conclusion"]
        result["summary"] = diag["summary"]
        # Region block scene has no further checks, return directly
        return result

    # Whitelist rule itself not effective
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
            # Full mode: set main conclusion but continue checking
            result["conclusion"] = whitelist_diag["conclusion"]
            result["summary"] = whitelist_diag["summary"]

    # === General condition analysis (custom rules, CC rules, whitelist condition checks, etc.) ===
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

    # Generate diagnosis conclusion
    if has_mismatch:
        # Has mismatched conditions
        mismatch_details = []
        for item in analysis["mismatched_conditions"]:
            detail = build_mismatch_detail(item, xff_status)
            mismatch_details.append(detail)
    
        result["conclusion"] = "condition_mismatch"
        result["summary"] = "Rule conditions are combined with AND logic. Reason for not matching: " + "; ".join(mismatch_details)
        result["mismatch_details"] = mismatch_details
            
        # Full check: add to issues list
        result["all_issues"].append({
            "issue_type": "condition_mismatch",
            "severity": "critical",
            "summary": "Rule conditions do not match the traffic",
            "details": mismatch_details,
            "recommendation": "Check if the rule condition fields match the request characteristics"
        })

    elif not has_recorded and has_unrecorded:
        # All conditions are fields that cannot be verified
        unrecorded_names = [f['field'] for f in analysis['unrecorded_fields']]
        if monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "all_unrecorded_with_monitor"
            result["summary"] = (
                f"Traffic has hit monitor rule {monitor_rule['rule_id']}, "
                f"viewable in WAF console log field {monitor_rule['log_field']}. "
                f"All condition fields {unrecorded_names} of the current rule are not recorded in logs, cannot fully verify."
            )
        else:
            result["conclusion"] = "all_unrecorded"
            result["summary"] = (
                f"All condition fields {unrecorded_names} of the current rule are not recorded in logs (e.g., body, cookie, etc.), "
                "cannot verify matching through logs."
            )
        result["recommendations"].append(
            f"It is recommended to select the {unrecorded_names} fields in WAF console - Log Service - Log Settings, "
            "then trigger new traffic and observe the new logs"
        )
        
        # Full check: add to issues list
        result["all_issues"].append({
            "issue_type": result["conclusion"],
            "severity": "warning",
            "summary": f"Cannot verify fields: {unrecorded_names}",
            "recommendation": f"Select the {unrecorded_names} fields in Log Settings and retest"
        })

    elif has_recorded and not has_mismatch and has_unrecorded:
        # Known fields all match, but there are unverifiable fields
        unrecorded_names = [f['field'] for f in analysis['unrecorded_fields']]
        if is_cc:
            result["conclusion"] = "partial_match_cc_unrecorded"
            result["summary"] = (
                "Verifiable fields in the log all match rule conditions, but there are unverifiable fields and frequency conditions. "
                f"Unrecorded fields: {unrecorded_names}. "
                "Possible causes: 1) Unrecorded fields do not match 2) Frequency threshold not reached "
                "3) WAF uses tumbling window detection, not sliding window"
            )
        elif monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "partial_match_with_monitor"
            result["summary"] = (
                f"Traffic has hit monitor rule {monitor_rule['rule_id']}. "
                "Verifiable fields in the log all match rule conditions, "
                f"but {unrecorded_names} are not recorded in logs, possibly these fields do not match causing the rule to not take effect."
            )
        else:
            result["conclusion"] = "partial_match_unrecorded"
            result["summary"] = (
                "Verifiable fields in the log all match rule conditions, "
                f"but {unrecorded_names} are not recorded in logs, possibly these fields do not match causing the rule to not take effect."
            )
        result["recommendations"].append(
            f"It is recommended to select the {unrecorded_names} fields in WAF console - Log Service - Log Settings, "
            "then trigger new traffic and observe the new logs"
        )
        
        # Full check: add to issues list
        result["all_issues"].append({
            "issue_type": result["conclusion"],
            "severity": "warning",
            "summary": f"Known fields match, but unrecorded fields: {unrecorded_names}",
            "recommendation": f"Select the {unrecorded_names} fields in Log Settings and retest"
        })

    elif has_recorded and not has_mismatch and not has_unrecorded:
        # All conditions match
        if is_cc:
            result["conclusion"] = "all_match_cc"
            result["summary"] = (
                "All matching conditions satisfy the rule requirements, but this is a frequency rule. "
                "The access frequency may not have reached the threshold, or the tumbling window detection mechanism caused it not to trigger. "
                "WAF uses tumbling windows (not sliding windows), the counting window starts from the first request arrival time."
            )
        elif monitor_info:
            monitor_rule = monitor_info['monitor_rules'][0]
            result["conclusion"] = "all_match_with_monitor"
            result["summary"] = (
                f"All conditions match. Traffic has hit monitor rule {monitor_rule['rule_id']} (action is monitor). "
                f"You can select the log field {monitor_rule['log_field']} in the WAF console to view hit details."
            )
        else:
            final_plugin = log_json.get('final_plugin', '')
            final_rule_id_log = log_json.get('final_rule_id', '')
            if final_plugin == 'acl' and final_rule_id_log and str(final_rule_id_log) != str(rule_id):
                result["conclusion"] = "all_match_other_rule_priority"
                result["summary"] = (
                    f"All conditions match. But traffic was intercepted by another ACL rule {final_rule_id_log} first. "
                    "When multiple ACL rules are satisfied simultaneously, the first configured rule takes effect."
                )
            else:
                result["conclusion"] = "all_match_timing"
                result["summary"] = (
                    "All conditions match the rule requirements. Likely the rule was configured too recently, "
                    "the rule needs about 1 minute after configuration/change to take effect."
                )
        
        # Full check: add to issues list
        if is_cc:
            result["all_issues"].append({
                "issue_type": "cc_frequency_not_reached",
                "severity": "warning",
                "summary": "Frequency threshold not reached or tumbling window mechanism",
                "recommendation": "Check CC protection frequency config, confirm if access frequency reaches the threshold"
            })
        elif monitor_info:
            result["all_issues"].append({
                "issue_type": "monitor_mode_action",
                "severity": "info",
                "summary": "Rule was hit but action is monitor mode",
                "recommendation": "To block, change the rule action to block"
            })
        else:
            final_plugin = log_json.get('final_plugin', '')
            final_rule_id_log = log_json.get('final_rule_id', '')
            if final_plugin == 'acl' and final_rule_id_log and str(final_rule_id_log) != str(rule_id):
                result["all_issues"].append({
                    "issue_type": "rule_priority_conflict",
                    "severity": "warning",
                    "summary": f"Intercepted by other ACL rule {final_rule_id_log} first",
                    "recommendation": "Adjust rule order, move the current rule to an earlier position"
                })
            else:
                result["all_issues"].append({
                    "issue_type": "timing_delay",
                    "severity": "info",
                    "summary": "Rule configured less than 1 minute ago, may not have taken effect yet",
                    "recommendation": "Wait about 1 minute and retry"
                })
    else:
        result["conclusion"] = "unknown"
        result["summary"] = "Unable to determine the reason why the rule is not effective, manual investigation recommended"

    # Additional module match check for whitelist scenario
    if defense_scene == 'whitelist' and not has_mismatch:
        whitelist_module_check = diagnose_whitelist(rule_config, log_json, rule_id)
        if whitelist_module_check:
            result["whitelist_module_check"] = whitelist_module_check
            result["conclusion"] = whitelist_module_check["conclusion"]
            result["summary"] = whitelist_module_check["summary"]

    return result


# ==============================================================
# CLI entry
# ==============================================================

def main():
    parser = argparse.ArgumentParser(description='WAF rule condition matching diagnosis engine')
    parser.add_argument('--rule-json', type=str, default=None,
                        help='Rule JSON string')
    parser.add_argument('--log-json', type=str, default=None,
                        help='Log JSON string')
    parser.add_argument('--rule-file', type=str, default=None,
                        help='Rule JSON file path')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Log JSON file path')
    parser.add_argument('--xff-status', type=int, default=0,
                        help='XFF configuration status (0=disabled, 1=first xff value, 2=custom header)')
    parser.add_argument('--defense-scene', type=str, default=None,
                        help='Defense scene override (read from rule by default)')
    parser.add_argument('--bypass-config', type=str, default=None,
                        help='Whitelist rule config JSON string (optional)')
    parser.add_argument('--full-check', action='store_true', default=False,
                        help='Full check mode: check all possible causes and output at once (default fast mode, returns on first major issue)')
    args = parser.parse_args()

    # Read rule data
    rule_data = None
    if args.rule_json:
        rule_data = json.loads(args.rule_json)
    elif args.rule_file:
        with open(args.rule_file, 'r', encoding='utf-8') as f:
            rule_data = json.load(f)
    else:
        parser.error("Must specify --rule-json or --rule-file")

    # Read log data
    log_data = None
    if args.log_json:
        log_data = json.loads(args.log_json)
    elif args.log_file:
        with open(args.log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    else:
        parser.error("Must specify --log-json or --log-file")

    # Read whitelist config
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
            "error": f"Diagnosis failed: {str(e)}"
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
