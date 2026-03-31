# -*- coding: utf-8 -*-
"""Search Alibaba Cloud documents by keyword.

Usage:
    python3 scripts/search_documents.py <query> [limit]

Example:
    python3 scripts/search_documents.py 'ECS实例规格'
    python3 scripts/search_documents.py 'VPC网络配置' 5
"""
import sys
import json

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models


def validate_input(value, name, max_length=2000):
    """Validate input value for length and non-empty."""
    if not value or len(value) > max_length:
        print(f"Error: {name} exceeds {max_length} chars or is empty", file=sys.stderr)
        sys.exit(1)


def validate_int_range(value, name, min_val, max_val):
    """Validate integer is within range."""
    if value < min_val or value > max_val:
        print(f"Error: {name} must be between {min_val} and {max_val}", file=sys.stderr)
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


def search_documents(query: str, limit: int = 5) -> dict:
    client = create_client()
    params = open_api_models.Params(
        action='SearchDocuments',
        version='2024-11-30',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/searchDocuments',
        req_body_type='json',
        body_type='json'
    )
    body = {'query': query, 'limit': limit}
    runtime = util_models.RuntimeOptions(read_timeout=60000)
    request = open_api_models.OpenApiRequest(body=body)
    return client.call_api(params, request, runtime)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/search_documents.py <query> [limit]", file=sys.stderr)
        sys.exit(1)
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    validate_input(query, 'query', max_length=2000)
    validate_int_range(limit, 'limit', 1, 100)
    
    result = search_documents(query, limit)
    sanitized = sanitize_response(result)
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
