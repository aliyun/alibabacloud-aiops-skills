# -*- coding: utf-8 -*-
import json
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient

# Timeout configuration (milliseconds)
CONNECT_TIMEOUT_MS = 10000  # Connection timeout 10 seconds
READ_TIMEOUT_MS = 30000     # Read timeout 30 seconds


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
    config.user_agent = 'AlibabaCloud-Agent-Skills'
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


if __name__ == '__main__':
    response = describe_risk_rules()
    status_code = response.get('statusCode')
    body = response.get('body', {})
    
    if status_code == 200:
        total_count = body.get('TotalCount', 0)
        items = body.get('Items', [])
        
        print(f"Found {total_count} unprocessed security risk events")
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
            print("No unprocessed security risk events found")
    else:
        print(f"Query failed: {json.dumps(body, indent=2, ensure_ascii=False)}")
