# -*- coding: utf-8 -*-
"""List Alibaba Cloud products by keyword filter.

Usage:
    python3 scripts/lsit_products.py <filter_keyword>

Example:
    python3 scripts/lsit_products.py '云网络'
    python3 scripts/lsit_products.py 'ECS'
"""
import sys
import json

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient


def validate_input(value, name, max_length=2000):
    """Validate input value for length and non-empty."""
    if not value or len(value) > max_length:
        print(f"Error: {name} exceeds {max_length} chars or is empty", file=sys.stderr)
        sys.exit(1)


def sanitize_response(obj):
    """Recursively sanitize sensitive fields in response object."""
    sensitive_keys = {'accesskeyid', 'accesskeysecret', 'securitytoken', 'password', 'secret', 'accountid', 'credential'}
    
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = sanitize_response(value)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_response(item) for item in obj]
    else:
        return obj


def create_client() -> OpenApiClient:
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = 'openapi-mcp.cn-hangzhou.aliyuncs.com'
    config.user_agent = 'AlibabaCloud-Agent-Skills'
    return OpenApiClient(config)


def list_products(filter_keyword: str) -> dict:
    client = create_client()
    params = open_api_models.Params(
        action='ListProducts',
        version='2024-11-30',
        protocol='HTTPS',
        method='GET',
        auth_type='AK',
        style='ROA',
        pathname='/listProducts',
        req_body_type='json',
        body_type='json'
    )
    queries = {}
    if filter_keyword:
        queries['filter'] = filter_keyword
    runtime = util_models.RuntimeOptions(read_timeout=30000)
    request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(queries)
    )
    return client.call_api(params, request, runtime)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/lsit_products.py <filter_keyword>", file=sys.stderr)
        sys.exit(1)
    filter_keyword = sys.argv[1]
    
    validate_input(filter_keyword, 'filter_keyword', max_length=200)
    
    result = list_products(filter_keyword)
    sanitized = sanitize_response(result)
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
