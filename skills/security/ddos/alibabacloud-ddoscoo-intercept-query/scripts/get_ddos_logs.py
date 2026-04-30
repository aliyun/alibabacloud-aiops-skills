#!/usr/bin/env python3
"""
DDoS Pro (ddoscoo) SLS Full Log Query Script
Generates timestamps and calls aliyun sls get-logs to query DDoS Pro intercept/block logs
"""

import subprocess
import sys
import json
import time
import argparse
import re

# Note: User-Agent is managed globally via AI-Mode (aliyun configure ai-mode set-user-agent).
# No per-command --header is needed.

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


def query_sls_logs(project, logstore, request_id, region, ttl=90, profile=None):
    """
    Query SLS logs with automatic time range expansion
    
    Args:
        project: SLS Project name
        logstore: SLS Logstore name
        request_id: Request ID to query
        region: SLS region
        ttl: Log retention period (days), default 90
        profile: Aliyun CLI profile name (optional)
    
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
        
        # Build aliyun sls command (plugin-mode: kebab-case get-logs per SA-2.11)
        cmd = [
            "aliyun", "sls", "get-logs",
            "--project", project,
            "--logstore", logstore,
            "--from", str(from_ts),
            "--to", str(to_time),
            "--query", request_id,
            "--reverse", "true",
            "--lines", "100",
            "--region", region,
        ]
        if profile:
            cmd.extend(["--profile", profile])
        
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
        'traceid': 'Request ID',
        'request_traceid': 'Request ID',
        'final_rule_id': 'Rule ID',
        'final_plugin': 'Block Plugin',
        'final_action': 'Action',
        'cc_action': 'CC Action',
        'cc_rule_id': 'CC Rule ID',
        'cc_phase': 'CC Phase',
        'cc_blocks': 'CC Blocks',
        'last_owner': 'Last Owner',
        'status': 'HTTP Status',
        'upstream_status': 'Upstream Status',
        'real_client_ip': 'Client IP',
        'matched_host': 'Matched Host',
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


def determine_block_type(log):
    """Determine the block type from DDoS Pro log fields.
    
    Returns a tuple of (block_type_label, phase_key) where phase_key
    is one of: 'cc', 'gfacl', 'ai', 'global', 'blacklist', 'region', or 'unknown'.
    """
    cc_phase = log.get('cc_phase', '')
    cc_action = log.get('cc_action', '')
    final_plugin = log.get('final_plugin', '')
    
    # cc_phase mapping — actual DDoS Pro values all have 'gf' prefix
    _PHASE_MAP = {
        # CC protection (频率控制)
        'cc':          ('CC Protection (频率控制自定义规则)', 'cc'),
        'gfcc':        ('CC Protection (频率控制自定义规则)', 'cc'),
        # Precise Access Control (精确访问控制 / ACL)
        'gfacl':       ('Precise Access Control (精确访问控制)', 'gfacl'),
        'acl':         ('Precise Access Control (精确访问控制)', 'gfacl'),
        # AI Smart Protection (AI智能防护)
        'ai':          ('AI Smart Protection (AI智能防护)', 'ai'),
        'gfai':        ('AI Smart Protection (AI智能防护)', 'ai'),
        # Global Defense Policy (全局防护策略)
        'global':      ('Global Defense Policy (全局防护策略)', 'global'),
        'gfglobal':    ('Global Defense Policy (全局防护策略)', 'global'),
        'gf_rule':     ('Global Defense Policy (全局防护策略)', 'global'),
        # IP Blacklist (IP黑名单)
        'blacklist':   ('IP Blacklist (IP黑名单)', 'blacklist'),
        'gfbwip':      ('IP Blacklist (IP黑名单)', 'blacklist'),
        # Region Blocking (区域封禁)
        'region':      ('Region Blocking (区域封禁)', 'region'),
        'geo':         ('Region Blocking (区域封禁)', 'region'),
        'gfareaban':   ('Region Blocking (区域封禁)', 'region'),
    }
    
    # Primary: exact match on cc_phase
    if cc_phase in _PHASE_MAP:
        return _PHASE_MAP[cc_phase]
    
    # Fallback: match on cc_action / final_plugin
    if cc_action in ('block', 'captcha') or log.get('cc_rule_id'):
        return ('CC Protection (频率控制)', 'cc')
    if 'precise' in final_plugin or 'acl' in final_plugin:
        return ('Precise Access Control (精确访问控制)', 'gfacl')
    if 'region' in final_plugin or 'geo' in final_plugin:
        return ('Region Blocking (区域封禁)', 'region')
    if 'blacklist' in final_plugin or 'ip' in final_plugin:
        return ('IP Blacklist (IP黑名单)', 'blacklist')
    if 'ai' in final_plugin:
        return ('AI Smart Protection (AI智能防护)', 'ai')
    if final_plugin:
        return (f'Other ({final_plugin})', 'unknown')
    return ('Unknown', 'unknown')


def _get_rule_query_commands(log, phase_key, region='cn-hangzhou'):
    """Generate CLI commands for querying ALL policy types for the domain.
    
    The matched policy type (based on phase_key) is marked with [MATCHED].
    Returns a list of (description, command, is_matched) tuples.
    """
    domain = log.get('matched_host') or log.get('host', '<domain>')
    last_owner = log.get('last_owner', '')
    rule_name = last_owner.split('|')[0] if '|' in last_owner else last_owner
    owner = 'manual'
    if '|' in last_owner:
        owner = last_owner.split('|')[1]
    
    # All policy query commands: (phase_key, description, command)
    all_policies = [
        ('_switch',
         "All protection switch status (策略预检)",
         f"aliyun ddoscoo describe-web-cc-protect-switch --domains.1 '{domain}' --region {region}"),
        ('cc',
         f"CC protection rules (频率控制) [Owner={owner}]",
         f"aliyun ddoscoo describe-web-cc-rules-v2 --domain '{domain}' --offset 0 --page-size 30 --owner {owner} --region {region}"),
        ('gfacl',
         "Precise Access Control rules (精确访问控制/ACL)",
         f"aliyun ddoscoo describe-web-precise-access-rule --domains.1 '{domain}' --region {region}"),
        ('ai',
         "AI Smart Protection status (AI智能防护)",
         f"aliyun ddoscoo describe-web-cc-protect-switch --domains.1 '{domain}' --region {region}"),
        ('global',
         "Global Defense Policy rules (全局防护策略)",
         f"aliyun ddoscoo describe-l7-global-rule --domain '{domain}' --region {region}"),
        ('blacklist',
         "IP Blacklist/Whitelist (IP黑白名单)",
         f"aliyun ddoscoo describe-web-rules --domain '{domain}' --region {region}"),
        ('region',
         "Region Blocking config (区域封禁)",
         f"aliyun ddoscoo describe-web-area-block-configs --domains.1 '{domain}' --region {region}"),
    ]
    
    commands = []
    for policy_key, desc, cmd in all_policies:
        is_matched = (policy_key == phase_key)
        if is_matched and rule_name:
            desc = f"{desc} → rule '{rule_name}'"
        commands.append((desc, cmd, is_matched))
    
    return commands


def print_log_analysis(logs, region='cn-hangzhou'):
    """Print log analysis results for DDoS Pro intercept events"""
    if not logs:
        return
    
    print("\n" + "="*60)
    print("DDoS Pro Intercept Analysis Report")
    print("="*60)
    
    for idx, log in enumerate(logs, 1):
        parsed = parse_log_entry(log)
        
        print(f"\n[Log Record {idx}]")
        print("-"*60)
        
        # Request information
        print("\nRequest Information:")
        for key in ['Request ID', 'Time', 'Client IP', 'Request Method',
                     'Domain', 'Matched Host', 'Request URI', 'User-Agent']:
            if key in parsed:
                print(f"  {key}: {parsed[key]}")
        
        # Block details
        print("\nBlock Details:")
        block_type_label, phase_key = determine_block_type(log)
        print(f"  Block Type: {block_type_label}")
        
        # Parse last_owner for rule name and source
        last_owner = log.get('last_owner', '')
        if last_owner and '|' in last_owner:
            rule_name, rule_source = last_owner.split('|', 1)
            source_label = 'User-created' if rule_source == 'manual' else 'Auto-generated'
            print(f"  Matched Rule Name: {rule_name} ({source_label})")
        
        for key in ['Rule ID', 'CC Rule ID', 'Block Plugin', 'Action',
                     'CC Action', 'CC Phase', 'HTTP Status', 'Upstream Status']:
            if key in parsed:
                print(f"  {key}: {parsed[key]}")
        
        # Raw log (optional, for single record)
        if len(logs) == 1:
            # Exclude already-displayed fields
            _displayed = {
                'request_traceid', 'final_rule_id', 'final_plugin', 'final_action',
                'cc_action', 'cc_rule_id', 'cc_phase',
                'status', 'upstream_status', 'real_client_ip', 'matched_host',
                'host', 'request_uri', 'request_method',
                'http_user_agent', 'time',
                '__source__', '__time__', '__topic__',
            }
            print("\nFull Log Fields:")
            for key, value in sorted(log.items()):
                if key not in _displayed:
                    if _is_sensitive_field(key):
                        display_value = _mask_field_value(key, value)
                    else:
                        display_value = value if len(str(value)) < 50 else str(value)[:50] + "..."
                    print(f"  {key}: {display_value}")
    
    # Recommended rule query commands (based on first log record)
    first_log = logs[0]
    _, first_phase_key = determine_block_type(first_log)
    rule_commands = _get_rule_query_commands(first_log, first_phase_key, region=region)
    if rule_commands:
        print("\nAll Policy Query Commands:")
        print("-"*60)
        for desc, cmd, is_matched in rule_commands:
            marker = " [MATCHED]" if is_matched else ""
            print(f"\n  # {desc}{marker}")
            print(f"  {cmd}")
    
    print("\n" + "="*60)


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

# Pattern: DDoS Pro instance ID (e.g. ddoscoo-cn-xxx)
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
    """Validate DDoS Pro instance ID format."""
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
    parser = argparse.ArgumentParser(description='Query DDoS Pro SLS full logs for intercept/block events')
    parser.add_argument('--project', required=True,
                        type=lambda v: _validate_sls_name(v, 'project'),
                        help='SLS Project name')
    parser.add_argument('--logstore', required=True,
                        type=lambda v: _validate_sls_name(v, 'logstore'),
                        help='SLS Logstore name')
    parser.add_argument('--request-id', required=True,
                        type=_validate_request_id,
                        help='Request ID (traceid) to query')
    parser.add_argument('--region', default='cn-hangzhou',
                        type=_validate_region,
                        help='SLS region (default: cn-hangzhou)')
    parser.add_argument('--ttl', type=_validate_ttl, default=90,
                        help='Log retention period in days (default: 90, max: 3650)')
    parser.add_argument('--json', action='store_true', help='Output raw logs in JSON format')
    parser.add_argument('--instance-id',
                        type=_validate_instance_id,
                        help='DDoS Pro instance ID (for reference)')
    parser.add_argument('--profile',
                        help='Aliyun CLI profile name (e.g. default, china, intl)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("DDoS Pro SLS Full Log Query")
    print("="*60)
    print(f"Project: {args.project}")
    print(f"Logstore: {args.logstore}")
    print(f"Request ID: {args.request_id}")
    print(f"Region: {args.region}")
    print(f"Current timestamp: {get_current_timestamp()} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(get_current_timestamp()))})")
    
    # Query logs
    if args.profile:
        print(f"Profile: {args.profile}")
    
    # Query logs
    logs = query_sls_logs(args.project, args.logstore, args.request_id, args.region, args.ttl, profile=args.profile)
    
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
            # Analysis format output
            print_log_analysis(logs, region=args.region)
        return 0
    else:
        print("\nSuggestions:")
        print("  1. Verify the Request ID is correct")
        print("  2. Confirm that full log is enabled for the domain")
        print("  3. Wait 3-5 minutes and retry (log sync delay)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
