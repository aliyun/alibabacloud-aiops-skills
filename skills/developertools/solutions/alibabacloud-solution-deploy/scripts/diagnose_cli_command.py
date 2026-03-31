# -*- coding: utf-8 -*-
"""Diagnose an Alibaba Cloud CLI command error.

Usage:
    python3 scripts/diagnose_cli_command.py <command> <error>

Example:
    python3 scripts/diagnose_cli_command.py 'aliyun ecs DescribeInstances' 'InvalidAccessKeyId.NotFound'
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


def diagnose_cli(command: str, error: str) -> dict:
    client = create_client()
    params = open_api_models.Params(
        action='DiagnoseCLI',
        version='2024-11-30',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/diagnoseCLI',
        req_body_type='json',
        body_type='json'
    )
    body = {'command': command, 'error': error}
    runtime = util_models.RuntimeOptions(read_timeout=60000)
    request = open_api_models.OpenApiRequest(body=body)
    return client.call_api(params, request, runtime)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/diagnose_cli_command.py <command> <error>", file=sys.stderr)
        sys.exit(1)
    command = sys.argv[1]
    error = sys.argv[2]
    
    validate_input(command, 'command', max_length=2000)
    validate_input(error, 'error', max_length=4000)
    
    result = diagnose_cli(command, error)
    sanitized = sanitize_response(result)
    print(json.dumps(sanitized, ensure_ascii=False, indent=2))
