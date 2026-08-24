# -*- coding: utf-8 -*-
import json
import os
import re
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient

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


def create_client():
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = 'sddp.cn-zhangjiakou.aliyuncs.com'
    config.user_agent = build_user_agent()
    return OpenApiClient(config)


def describe_risk_rules(current_page=1, page_size=20, handle_status='UNPROCESSED'):
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
        'HandleStatus': handle_status
    }
    request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
    runtime = create_runtime_options()
    return client.call_api(params, request, runtime)


def parse_query_arguments(args):
    """Parse optional CurrentPage, PageSize, and HandleStatus CLI arguments."""
    current_page = 1
    page_size = 20
    handle_status = 'UNPROCESSED'

    if len(args) >= 1:
        if not args[0].isdigit() or int(args[0]) < 1:
            raise ValueError("CurrentPage must be a positive integer")
        current_page = int(args[0])
    if len(args) >= 2:
        if not args[1].isdigit() or int(args[1]) < 1:
            raise ValueError("PageSize must be a positive integer")
        page_size = int(args[1])
    if len(args) >= 3:
        if args[2] not in ('UNPROCESSED', 'PROCESSED'):
            raise ValueError("HandleStatus must be UNPROCESSED or PROCESSED")
        handle_status = args[2]
    if len(args) > 3:
        raise ValueError("Usage: query_risk.py [CurrentPage] [PageSize] [HandleStatus]")

    return current_page, page_size, handle_status


def main(args):
    try:
        current_page, page_size, handle_status = parse_query_arguments(args)
    except ValueError as error:
        print(f"❌ Parameter error: {error}")
        return 1

    response = describe_risk_rules(current_page, page_size, handle_status)
    status_code = response.get('statusCode')
    body = response.get('body', {})
    
    if status_code == 200:
        total_count = body.get('TotalCount', 0)
        items = body.get('Items', [])
        
        status_label = handle_status.lower()
        print(f"Found {total_count} {status_label} security risk events")
        print(
            f"Current page: {current_page}, page size: {page_size}, "
            f"HandleStatus: {handle_status}, returned: {len(items)}"
        )
        print("=" * 80)
        
        if items:
            for item in items:
                print(f"Risk ID: {item.get('RiskId')}")
                print(f"Rule Name: {item.get('RuleName')}")
                print(f"Risk Level: {item.get('WarnLevelName')}")
                print(f"Product Type: {item.get('ProductCode')}")
                print(f"Alert Count: {item.get('AlarmCount')}")
                print(f"Asset Count: {item.get('InstanceCount')}")
                print(f"Rule Category: {item.get('RuleCategoryName')}")
                print("-" * 80)
        else:
            print(f"No {status_label} security risk events found")
    else:
        print(f"Query failed: {json.dumps(body, indent=2, ensure_ascii=False)}")
        return 1

    return 0


if __name__ == '__main__':
    import sys

    sys.exit(main(sys.argv[1:]))
