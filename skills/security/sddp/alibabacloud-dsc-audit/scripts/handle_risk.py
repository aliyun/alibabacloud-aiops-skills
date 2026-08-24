# -*- coding: utf-8 -*-
import json
import os
import re
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient

# Constants
RISK_ID_MIN = 1
RISK_ID_MAX = 2 ** 63 - 1  # Alibaba Cloud IDs are typically 64-bit integers
HANDLE_DETAIL_MAX_LENGTH = 500
# Allowed characters: Chinese, English, numbers, common punctuation
HANDLE_DETAIL_PATTERN = re.compile(r'^[\u4e00-\u9fa5a-zA-Z0-9\s，。、；：""''！？（）\-_,.;:!?()\[\]]+$')
UNSAFE_HANDLE_DETAIL_PATTERNS = [
    re.compile(r'\brm\s+-rf\b', re.IGNORECASE),
    re.compile(r'\b(drop|truncate|alter)\s+(table|database|schema)\b', re.IGNORECASE),
    re.compile(r'\bdelete\s+from\b', re.IGNORECASE),
    re.compile(r'\binsert\s+into\b', re.IGNORECASE),
    re.compile(r'\bupdate\s+\w+\s+set\b', re.IGNORECASE),
    re.compile(r'(--|/\*|\*/|\$\(|`|\||&&|\|\||[<>])'),
    re.compile(r';\s*(rm|sh|bash|curl|wget|nc|python|perl|drop|delete|insert|update|alter|truncate)\b', re.IGNORECASE),
]

# Timeout configuration (milliseconds)
CONNECT_TIMEOUT_MS = 10000  # Connection timeout 10 seconds
READ_TIMEOUT_MS = 30000     # Read timeout 30 seconds
SKILL_NAME = 'alibabacloud-dsc-audit'
SESSION_ID_PATTERN = re.compile(r'^[0-9a-f]{32}$')


def build_user_agent():
    """Build the session-scoped SDK user agent from SKILL_SESSION_ID."""
    session_id = os.environ.get('SKILL_SESSION_ID', '')
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise RuntimeError(
            "SKILL_SESSION_ID must be a 32-character lowercase hexadecimal value"
        )
    return f'AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id}'


def create_runtime_options():
    """Create RuntimeOptions with timeout configuration"""
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = CONNECT_TIMEOUT_MS
    runtime.read_timeout = READ_TIMEOUT_MS
    return runtime


def validate_risk_id(risk_id_str):
    """
    Validate risk_id parameter
    - Must be a valid positive integer format
    - Must be within valid range
    Returns: (is_valid, risk_id_int_or_error_msg)
    """
    # Format validation: must be numeric only
    if not risk_id_str or not risk_id_str.strip().isdigit():
        return False, "risk_id must be a positive integer"
    
    try:
        risk_id = int(risk_id_str.strip())
    except ValueError:
        return False, "risk_id conversion failed, please enter a valid integer"
    
    # Range validation
    if risk_id < RISK_ID_MIN or risk_id > RISK_ID_MAX:
        return False, f"risk_id is out of valid range ({RISK_ID_MIN} - {RISK_ID_MAX})"
    
    return True, risk_id


def validate_handle_detail(handle_detail):
    """
    Validate handle_detail parameter
    - Length limit
    - Special character filtering (prevent command injection)
    Returns: (is_valid, sanitized_detail_or_error_msg)
    """
    if not handle_detail or not handle_detail.strip():
        return False, "handle_detail cannot be empty"
    
    detail = handle_detail.strip()
    
    # Length validation
    if len(detail) > HANDLE_DETAIL_MAX_LENGTH:
        return False, f"handle_detail length cannot exceed {HANDLE_DETAIL_MAX_LENGTH} characters"
    
    # Reject obvious shell or SQL injection indicators before character filtering.
    for pattern in UNSAFE_HANDLE_DETAIL_PATTERNS:
        if pattern.search(detail):
            return False, "handle_detail contains unsafe command or SQL injection indicators"

    # Special character validation (prevent command injection)
    if not HANDLE_DETAIL_PATTERN.match(detail):
        return False, "handle_detail contains invalid characters, only Chinese, English, numbers and common punctuation are allowed"
    
    return True, detail


def create_client():
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = 'sddp.cn-zhangjiakou.aliyuncs.com'
    config.user_agent = build_user_agent()
    return OpenApiClient(config)


def describe_risk_rules(current_page=1, page_size=20):
    """Query unprocessed security risk events"""
    client = create_client()
    params = open_api_models.Params(
        action='DescribeRiskRules',
        version='2019-01-03',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='json',
        body_type='json'
    )
    queries = {
        'CurrentPage': current_page,
        'PageSize': page_size,
        'HandleStatus': 'UNPROCESSED'
    }
    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = create_runtime_options()
    return client.call_api(params, request, runtime)


def find_risk_in_unprocessed(risk_id):
    """Find specified RiskId in unprocessed risk events list, supports pagination"""
    current_page = 1
    page_size = 50
    
    while True:
        response = describe_risk_rules(current_page, page_size)
        status_code = response.get('statusCode')
        body = response.get('body', {})
        
        if status_code != 200:
            return False
        
        items = body.get('Items', [])
        total_count = body.get('TotalCount', 0)
        
        # Search for target RiskId in current page
        for item in items:
            if item.get('RiskId') == risk_id:
                return True
        
        # Check if there are more pages
        if current_page * page_size >= total_count:
            break
        current_page += 1
    
    return False


def collect_unprocessed_risk_summaries(page_size=50):
    """Collect current unprocessed risk events for user selection."""
    current_page = 1
    summaries = []

    while True:
        response = describe_risk_rules(current_page, page_size)
        status_code = response.get('statusCode')
        body = response.get('body', {})

        if status_code != 200:
            return summaries

        items = body.get('Items', [])
        total_count = body.get('TotalCount', 0)
        for item in items:
            summaries.append({
                'RiskId': item.get('RiskId'),
                'RuleName': item.get('RuleName'),
                'WarnLevelName': item.get('WarnLevelName'),
                'ProductCode': item.get('ProductCode'),
                'AlarmCount': item.get('AlarmCount'),
                'InstanceCount': item.get('InstanceCount'),
            })

        if current_page * page_size >= total_count:
            break
        current_page += 1

    return summaries


def format_unprocessed_risk_options(risk_summaries):
    """Format current unprocessed risks so the user can choose another RiskId."""
    if not risk_summaries:
        return "No current unprocessed risk events are available for selection."

    lines = [
        "Current unprocessed risk events available for selection:",
        "=" * 80,
    ]
    for item in risk_summaries:
        lines.append(f"Risk ID: {item.get('RiskId')}")
        if item.get('RuleName'):
            lines.append(f"Rule Name: {item.get('RuleName')}")
        if item.get('WarnLevelName'):
            lines.append(f"Risk Level: {item.get('WarnLevelName')}")
        if item.get('ProductCode'):
            lines.append(f"Product Type: {item.get('ProductCode')}")
        if item.get('AlarmCount') is not None:
            lines.append(f"Alert Count: {item.get('AlarmCount')}")
        if item.get('InstanceCount') is not None:
            lines.append(f"Asset Count: {item.get('InstanceCount')}")
        lines.append("-" * 80)
    lines.append("Please choose one RiskId from the current unprocessed list and retry handling.")
    return "\n".join(lines)


def handle_audit_risk(risk_id, handle_detail):
    """Handle security risk event"""
    client = create_client()
    
    params = open_api_models.Params(
        action='PreHandleAuditRisk',
        version='2019-01-03',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='json',
        body_type='json'
    )
    
    # Use flat mode for complex objects
    queries = {
        'RiskId': risk_id,
        'HandleInfoList.1.HandleType': 'Manual',
        'HandleInfoList.1.HandleContent': json.dumps({
            'HandleMethod': 0,
            'HandleDetail': handle_detail
        })
    }
    
    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = create_runtime_options()
    return client.call_api(params, request, runtime)


def main(args):
    """Run the handling workflow and return a process exit code."""
    dry_run = "--dry-run" in args
    positional_args = [arg for arg in args if arg != "--dry-run"]

    if len(positional_args) != 2:
        print("Usage: python3 handle_risk.py [--dry-run] <RiskID> <HandleDetail>")
        print("Example: python3 handle_risk.py --dry-run 66718695 'Confirmed as false positive, closing alert'")
        return 1
    
    # Input validation
    is_valid, result = validate_risk_id(positional_args[0])
    if not is_valid:
        print(f"❌ Parameter error: {result}")
        return 1
    risk_id = result
    
    is_valid, result = validate_handle_detail(positional_args[1])
    if not is_valid:
        print(f"❌ Parameter error: {result}")
        return 1
    handle_detail = result
    
    # Pre-handling validation: check if risk event exists in unprocessed list
    print(f"Validating risk event...")
    if not find_risk_in_unprocessed(risk_id):
        print(f"❌ No handleable risk event found: RiskId={risk_id}")
        print(format_unprocessed_risk_options(collect_unprocessed_risk_summaries()))
        return 0
    
    print(f"✓ Risk event confirmed to exist in unprocessed list")
    print(f"Handling risk event...")
    print(f"Risk ID: {risk_id}")
    print(f"Handle Detail: {handle_detail}")
    print("-" * 50)

    if dry_run:
        print("DRY-RUN validation completed.")
        print("PreHandleAuditRisk was not called (planned only).")
        print(f"No risk state was changed; rehearsal target RiskId={risk_id}.")
        return 0
    
    response = handle_audit_risk(risk_id, handle_detail)
    status_code = response.get('statusCode')
    body = response.get('body', {})
    
    if status_code == 200:
        print("✅ Handling successful!")
        print(f"RequestId: {body.get('RequestId')}")
    else:
        print(f"❌ Handling failed: {json.dumps(body, indent=2, ensure_ascii=False)}")

    return 0


if __name__ == '__main__':
    import sys

    sys.exit(main(sys.argv[1:]))
