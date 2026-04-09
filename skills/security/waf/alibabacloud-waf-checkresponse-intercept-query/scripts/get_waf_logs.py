#!/usr/bin/env python3
"""
WAF SLS Log Query Script
Generates timestamps and calls aliyun sls get-logs to query WAF block logs
"""

import subprocess
import sys
import json
import time
import argparse
import re

# User-Agent header for all Alibaba Cloud API calls
ALIYUN_USER_AGENT = "AlibabaCloud-Agent-Skills"

# ---------------------------------------------------------------------------
# Sensitive data masking helpers
# ---------------------------------------------------------------------------

# Fields that require masking in log output
_SENSITIVE_LOG_FIELDS = {
    'real_client_ip', 'remote_addr', 'client_ip', 'src_ip',
    'http_user_agent', 'user_agent',
    'cookie', 'http_cookie', 'set_cookie',
    'authorization', 'token', 'secret',
}


def _mask_ip(ip_str):
    """Mask an IP address, preserving only the first octet (IPv4) or prefix (IPv6).
    
    Examples:
        '192.168.1.100'  -> '192.***.***.***'
        '2001:db8::1'    -> '2001:****:****:****'
    """
    if not ip_str or not isinstance(ip_str, str):
        return ip_str
    ip_str = ip_str.strip()
    if ':' in ip_str and '.' not in ip_str:  # IPv6
        parts = ip_str.split(':')
        if len(parts) >= 2:
            return parts[0] + ':****:****:****'
        return ip_str
    # IPv4 (may also contain port like 1.2.3.4:8080)
    host = ip_str.split(':')[0] if ':' in ip_str else ip_str
    octets = host.split('.')
    if len(octets) == 4:
        return f"{octets[0]}.***.***.***"
    return ip_str


def _mask_uri(uri_str):
    """Mask query parameters in a URI while preserving the path.
    
    Examples:
        '/api/v1/user?token=abc123&name=test'  -> '/api/v1/user?token=***&name=***'
        '/static/page'                         -> '/static/page'
    """
    if not uri_str or not isinstance(uri_str, str):
        return uri_str
    if '?' not in uri_str:
        return uri_str
    path, query = uri_str.split('?', 1)
    masked_params = []
    for param in query.split('&'):
        if '=' in param:
            key, _ = param.split('=', 1)
            masked_params.append(f"{key}=***")
        else:
            masked_params.append(param)
    return f"{path}?{'&'.join(masked_params)}"


def _mask_user_agent(ua_str):
    """Truncate User-Agent to first 32 chars to reduce PII exposure."""
    if not ua_str or not isinstance(ua_str, str):
        return ua_str
    if len(ua_str) <= 32:
        return ua_str
    return ua_str[:32] + '...'


def _mask_field_value(field_key, value):
    """Apply appropriate masking based on the field key."""
    field_lower = field_key.lower()
    if field_lower in ('real_client_ip', 'remote_addr', 'client_ip', 'src_ip'):
        return _mask_ip(str(value))
    if field_lower in ('request_uri', 'uri', 'querystring', 'query_string'):
        return _mask_uri(str(value))
    if field_lower in ('http_user_agent', 'user_agent'):
        return _mask_user_agent(str(value))
    if field_lower in ('cookie', 'http_cookie', 'set_cookie',
                        'authorization', 'token', 'secret'):
        return '******'
    return value


def _is_sensitive_field(field_key):
    """Check if a field contains potentially sensitive data."""
    fl = field_key.lower()
    return (fl in _SENSITIVE_LOG_FIELDS or
            'cookie' in fl or 'token' in fl or 'secret' in fl or
            'password' in fl or 'auth' in fl or 'credential' in fl)


def get_current_timestamp():
    """Get current Unix timestamp (seconds)"""
    return int(time.time())


def query_sls_logs(project, logstore, request_id, region, ttl=90):
    """
    Query SLS logs with automatic time range expansion
    
    Args:
        project: SLS Project name
        logstore: SLS Logstore name
        request_id: Request ID to query
        region: SLS region
        ttl: Log retention period (days), default 90
    
    Returns:
        Query results (list of dicts)
    """
    to_time = get_current_timestamp()
    max_from_time = to_time - ttl * 86400  # Maximum lookback time
    
    # Initial time range: last 24 hours
    from_time = to_time - 86400
    
    # Progressively expand time range
    time_ranges = [
        (to_time - 86400, "last 24 hours"),
        (to_time - 86400 * 3, "last 3 days"),
        (to_time - 86400 * 7, "last 7 days"),
        (to_time - 86400 * 30, "last 30 days"),
        (max_from_time, f"last {ttl} days (maximum range)"),
    ]
    
    for from_ts, range_desc in time_ranges:
        # Ensure not exceeding maximum lookback time
        if from_ts < max_from_time:
            from_ts = max_from_time
            range_desc = f"last {ttl} days (maximum range)"
        
        print(f"\nQuerying logs for {range_desc}...")
        print(f"Time range: {from_ts} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(from_ts))}) -> {to_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(to_time))})")
        
        # Build aliyun sls command
        cmd = [
            "aliyun", "sls", "get-logs",
            "--project", project,
            "--logstore", logstore,
            "--from", str(from_ts),
            "--to", str(to_time),
            "--query", request_id,
            "--reverse", "true",
            "--region", region,
            "--header", f"User-Agent={ALIYUN_USER_AGENT}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                try:
                    logs = json.loads(result.stdout)
                    if logs and len(logs) > 0:
                        print(f"Found {len(logs)} log record(s)")
                        return logs
                    else:
                        print(f"No logs found in this time range")
                except json.JSONDecodeError:
                    print(f"Failed to parse response")
                    print(f"Raw output: {result.stdout[:200]}")
            else:
                print(f"Query failed: {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            print(f"Query timed out")
        except Exception as e:
            print(f"Query error: {e}")
        
        # Stop querying if maximum range is reached
        if from_ts <= max_from_time:
            break
    
    print(f"\nRequest ID not found in any time range: {request_id}")
    return []


def parse_log_entry(log):
    """Parse a single log entry and extract key information (with masking)"""
    key_fields = {
        'request_traceid': 'Request ID',
        'final_rule_id': 'Rule ID',
        'final_plugin': 'Block Plugin',
        'final_action': 'Action',
        'status': 'HTTP Status',
        'real_client_ip': 'Client IP',
        'host': 'Domain',
        'request_uri': 'Request URI',
        'request_method': 'Request Method',
        'http_user_agent': 'User-Agent',
        'time': 'Time',
    }
    
    parsed = {}
    for key, label in key_fields.items():
        if key in log:
            parsed[label] = _mask_field_value(key, log[key])
    
    return parsed


def query_rule_detail(instance_id, rule_id, region):
    """
    Query rule details using the DescribeDefenseRule API
    
    Args:
        instance_id: WAF instance ID
        rule_id: Rule ID
        region: WAF region
    
    Returns:
        Rule detail dict, or None on failure
    """
    cmd = [
        "aliyun", "waf-openapi", "DescribeDefenseRule",
        "--region", region,
        "--InstanceId", instance_id,
        "--RuleId", str(rule_id),
        "--RegionId", region,
        "--header", f"User-Agent={ALIYUN_USER_AGENT}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data.get('Rule', {})
            except json.JSONDecodeError:
                return None
        else:
            return None
    except Exception:
        return None


def parse_rule_config(rule):
    """
    Parse rule configuration content
    
    Reference: https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-createdefenserule
    
    Important notes:
    - ccStatus: 1 means custom rate limiting rule (CC rule), 0 means custom access control rule (ACL rule)
    - effect: Only valid when ccStatus=1, indicates the scope of effect after blacklisting
        - service: Entire protection object (matched_host)
        - rule: Only within this rule's scope (must satisfy matching conditions)
    """
    if not rule:
        return None
    
    config = {}
    
    # Basic information
    config['rule_id'] = rule.get('RuleId')
    config['rule_name'] = rule.get('RuleName')
    config['status'] = 'Enabled' if rule.get('Status') == 1 else 'Disabled'
    config['defense_origin'] = rule.get('DefenseOrigin', 'N/A')
    config['defense_scene'] = rule.get('DefenseScene', 'N/A')
    config['gmt_modified'] = rule.get('GmtModified')
    
    # Parse Config field (JSON string)
    try:
        rule_config = json.loads(rule.get('Config', '{}'))
        
        # Action configuration
        config['action'] = rule_config.get('action', 'N/A')
        config['name'] = rule_config.get('name', 'N/A')
        
        # CC protection configuration
        cc_status = rule_config.get('ccStatus', 0)
        config['cc_status'] = cc_status
        config['is_cc_rule'] = (cc_status == 1)
        
        # Rule type description
        if cc_status == 1:
            config['rule_type'] = 'Custom Rate Limiting Rule (CC Rule)'
            # effect parameter is only valid for CC rules
            effect = rule_config.get('effect', 'N/A')
            config['effect'] = effect
            if effect == 'service':
                config['effect_desc'] = 'After blacklisting, takes effect on the entire protection object'
            elif effect == 'rule':
                config['effect_desc'] = 'After blacklisting, takes effect only within the rule scope'
            else:
                config['effect_desc'] = 'Unknown'
        else:
            config['rule_type'] = 'Custom Access Control Rule (ACL Rule)'
            # effect parameter is meaningless for ACL rules
            config['effect'] = None
            config['effect_desc'] = 'N/A (only valid for CC rules)'
        
        # Matching conditions
        conditions = []
        for cond in rule_config.get('conditions', []):
            conditions.append({
                'key': cond.get('key', 'N/A'),
                'op_code': cond.get('opCode', 'N/A'),
                'op_value': cond.get('opValue', 'N/A'),
                'values': cond.get('values', 'N/A')
            })
        config['conditions'] = conditions
        
        # Rate limiting configuration (CC rules)
        if 'ratelimit' in rule_config:
            config['rate_limit'] = rule_config['ratelimit']
        
        # Time configuration
        if 'timeConfig' in rule_config:
            config['time_config'] = rule_config['timeConfig']
        
        # Canary configuration
        if 'grayStatus' in rule_config:
            config['gray_status'] = rule_config['grayStatus']
        if 'grayConfig' in rule_config:
            config['gray_config'] = rule_config['grayConfig']
            
    except json.JSONDecodeError:
        config['config_raw'] = rule.get('Config', 'N/A')
    
    return config


def print_log_analysis(logs, instance_id=None, region=None):
    """Print log analysis results including rule details"""
    if not logs:
        return
    
    print("\n" + "="*60)
    print("WAF Block Analysis Report")
    print("="*60)
    
    for idx, log in enumerate(logs, 1):
        parsed = parse_log_entry(log)
        
        print(f"\n[Log Record {idx}]")
        print("-"*60)
        
        # Request information
        print("\nRequest Information:")
        for key in ['Request ID', 'Time', 'Client IP', 'Request Method', 'Domain', 'Request URI', 'User-Agent']:
            if key in parsed:
                print(f"  {key}: {parsed[key]}")
        
        # Block details
        print("\nBlock Details:")
        for key in ['Rule ID', 'Block Plugin', 'Action', 'HTTP Status']:
            if key in parsed:
                print(f"  {key}: {parsed[key]}")
        
        # Query and display rule details
        rule_id = log.get('final_rule_id')
        if rule_id and instance_id and region:
            print("\nRule Details:")
            rule = query_rule_detail(instance_id, rule_id, region)
            if rule:
                config = parse_rule_config(rule)
                if config:
                    print(f"  Rule Name: {config.get('rule_name', 'N/A')}")
                    print(f"  Rule Status: {config.get('status', 'N/A')}")
                    print(f"  Defense Origin: {config.get('defense_origin', 'N/A')}")
                    print(f"  Defense Scene: {config.get('defense_scene', 'N/A')}")
                    print(f"  Rule Type: {config.get('rule_type', 'N/A')}")
                    
                    # CC rule specific information
                    if config.get('is_cc_rule'):
                        print(f"  Effect Scope: {config.get('effect', 'N/A')}")
                        print(f"  Effect Description: {config.get('effect_desc', 'N/A')}")
                        # Display rate limiting configuration
                        if 'rate_limit' in config:
                            print(f"  Rate Limit Config: {config['rate_limit']}")
                    
                    # Display matching conditions
                    conditions = config.get('conditions', [])
                    if conditions:
                        print(f"\n  Matching Conditions:")
                        for i, cond in enumerate(conditions, 1):
                            print(f"    Condition {i}:")
                            print(f"      Field: {cond.get('key', 'N/A')}")
                            print(f"      Operator: {cond.get('op_value', cond.get('op_code', 'N/A'))}")
                            print(f"      Value: {cond.get('values', 'N/A')}")
                else:
                    print(f"  Failed to parse rule configuration")
            else:
                print(f"  Unable to retrieve rule details (may require permissions)")
        
        # Raw log (optional)
        if len(logs) == 1:
            print("\nFull Log Fields:")
            for key, value in sorted(log.items()):
                if key not in ['request_traceid', 'final_rule_id', 'final_plugin', 'final_action', 
                               'status', 'real_client_ip', 'host', 'request_uri', 'request_method', 
                               'http_user_agent', 'time', '__source__', '__time__', '__topic__']:
                    # Mask sensitive fields in raw log output
                    if _is_sensitive_field(key):
                        display_value = _mask_field_value(key, value)
                    else:
                        display_value = value if len(str(value)) < 50 else str(value)[:50] + "..."
                    print(f"  {key}: {display_value}")
    
    print("\n" + "="*60)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

# Allowed Alibaba Cloud region IDs (non-exhaustive but covers all public regions)
_VALID_REGIONS = {
    # China mainland
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen', 'cn-zhangjiakou',
    'cn-huhehaote', 'cn-wulanchabu', 'cn-chengdu', 'cn-qingdao', 'cn-guangzhou',
    'cn-nanjing', 'cn-fuzhou', 'cn-heyuan',
    # International
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-5',
    'ap-southeast-6', 'ap-southeast-7', 'ap-south-1', 'ap-northeast-1',
    'ap-northeast-2', 'us-east-1', 'us-west-1', 'eu-west-1', 'eu-central-1',
    'me-east-1', 'me-central-1',
    # China Finance / Gov
    'cn-hangzhou-finance', 'cn-shanghai-finance-1', 'cn-shenzhen-finance-1',
    'cn-beijing-finance-1', 'cn-north-2-gov-1',
}

# Pattern: alphanumeric, hyphens, underscores (SLS project / logstore names)
_SLS_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$')

# Pattern: request trace ID — hex, alphanumeric, hyphens (e.g. UUIDs, trace IDs)
_REQUEST_ID_RE = re.compile(r'^[a-zA-Z0-9-]{1,128}$')

# Pattern: WAF instance ID (e.g. waf_v3cdnrecognition-cn-xxx, waf-cn-xxx)
_INSTANCE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')


def _validate_sls_name(value, label):
    """Validate SLS project / logstore name format."""
    if not _SLS_NAME_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid {label}: '{value}'. "
            f"Must start with alphanumeric and contain only [a-zA-Z0-9_-], max 128 chars."
        )
    return value


def _validate_request_id(value):
    """Validate request ID format (alphanumeric + hyphens)."""
    if not _REQUEST_ID_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid request ID: '{value}'. "
            f"Must contain only [a-zA-Z0-9-], max 128 chars."
        )
    return value


def _validate_region(value):
    """Validate region is a known Alibaba Cloud region ID."""
    if value not in _VALID_REGIONS:
        raise argparse.ArgumentTypeError(
            f"Invalid region: '{value}'. "
            f"Must be a valid Alibaba Cloud region ID (e.g. cn-hangzhou, ap-southeast-1)."
        )
    return value


def _validate_instance_id(value):
    """Validate WAF instance ID format."""
    if not _INSTANCE_ID_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid instance ID: '{value}'. "
            f"Must contain only [a-zA-Z0-9_-], max 128 chars."
        )
    return value


def _validate_ttl(value):
    """Validate TTL is a positive integer within a reasonable range."""
    try:
        ivalue = int(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"Invalid TTL: '{value}'. Must be a positive integer.")
    if ivalue < 1 or ivalue > 3650:
        raise argparse.ArgumentTypeError(
            f"TTL out of range: {ivalue}. Must be between 1 and 3650 days."
        )
    return ivalue


def main():
    parser = argparse.ArgumentParser(description='Query WAF SLS block logs')
    parser.add_argument('--project', required=True,
                        type=lambda v: _validate_sls_name(v, 'project'),
                        help='SLS Project name')
    parser.add_argument('--logstore', required=True,
                        type=lambda v: _validate_sls_name(v, 'logstore'),
                        help='SLS Logstore name')
    parser.add_argument('--request-id', required=True,
                        type=_validate_request_id,
                        help='Request ID to query')
    parser.add_argument('--region', default='ap-southeast-5',
                        type=_validate_region,
                        help='SLS region (default: ap-southeast-5)')
    parser.add_argument('--ttl', type=_validate_ttl, default=90,
                        help='Log retention period in days (default: 90, max: 3650)')
    parser.add_argument('--json', action='store_true', help='Output raw logs in JSON format')
    parser.add_argument('--instance-id',
                        type=_validate_instance_id,
                        help='WAF instance ID (for querying rule details)')
    parser.add_argument('--waf-region',
                        type=_validate_region,
                        help='WAF region (for querying rule details, defaults to --region)')
    
    args = parser.parse_args()
    
    # WAF region defaults to SLS region
    waf_region = args.waf_region if args.waf_region else args.region
    
    print("="*60)
    print("WAF SLS Log Query")
    print("="*60)
    print(f"Project: {args.project}")
    print(f"Logstore: {args.logstore}")
    print(f"Request ID: {args.request_id}")
    print(f"Region: {args.region}")
    print(f"Current timestamp: {get_current_timestamp()} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(get_current_timestamp()))})")
    
    # Query logs
    logs = query_sls_logs(args.project, args.logstore, args.request_id, args.region, args.ttl)
    
    if logs:
        if args.json:
            # JSON format output — mask sensitive fields before emitting
            sanitized_logs = []
            for log in logs:
                sanitized = {}
                for k, v in log.items():
                    if _is_sensitive_field(k):
                        sanitized[k] = _mask_field_value(k, v)
                    elif k.lower() in ('request_uri', 'uri', 'querystring', 'query_string'):
                        sanitized[k] = _mask_uri(str(v))
                    else:
                        sanitized[k] = v
                sanitized_logs.append(sanitized)
            print("\n" + json.dumps(sanitized_logs, indent=2, ensure_ascii=False))
        else:
            # Analysis format output (with rule details)
            print_log_analysis(logs, args.instance_id, waf_region)
        return 0
    else:
        print("\nSuggestions:")
        print("  1. Verify the Request ID is correct")
        print("  2. Confirm that the log service is enabled")
        print("  3. Wait 3-5 minutes and retry (log sync delay)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
