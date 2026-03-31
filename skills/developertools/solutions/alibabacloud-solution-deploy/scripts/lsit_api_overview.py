# -*- coding: utf-8 -*-
"""List API overviews for a given Alibaba Cloud product.

Usage:
    python3 scripts/lsit_api_overview.py <product> <version> [filter]

Example:
    python3 scripts/lsit_api_overview.py Ecs 2014-05-26
    python3 scripts/lsit_api_overview.py Ecs 2014-05-26 '云助手'
"""
import sys
import json
import re

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient


def validate_product(product):
    """Validate product matches ^[a-zA-Z][a-zA-Z0-9-]{0,49}$."""
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9-]{0,49}$', product):
        print(f"Error: product must start with letter and contain only alphanumeric or hyphen, max 50 chars", file=sys.stderr)
        sys.exit(1)


def validate_version(version):
    r"""Validate version matches ^\d{4}-\d{2}-\d{2}$."""
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', version):
        print(f"Error: version must be in YYYY-MM-DD format", file=sys.stderr)
        sys.exit(1)


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


def list_api_overviews(product: str, version: str, filter_keyword: str = '') -> dict:
    client = create_client()
    params = open_api_models.Params(
        action='ListApiOverviews',
        version='2024-11-30',
        protocol='HTTPS',
        method='GET',
        auth_type='AK',
        style='ROA',
        pathname='/listApiOverviews',
        req_body_type='json',
        body_type='json'
    )
    queries = {'product': product, 'version': version}
    if filter_keyword:
        queries['filter'] = filter_keyword
    runtime = util_models.RuntimeOptions(read_timeout=30000)
    request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(queries)
    )
    return client.call_api(params, request, runtime)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/lsit_api_overview.py <product> <version> [filter]", file=sys.stderr)
        sys.exit(1)
    product = sys.argv[1]
    version = sys.argv[2]
    filter_kw = sys.argv[3] if len(sys.argv) > 3 else ''
    
    validate_product(product)
    validate_version(version)
    if filter_kw:
        validate_input(filter_kw, 'filter', max_length=200)
    
    result = list_api_overviews(product, version, filter_kw)
    sanitized = sanitize_response(result)
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
