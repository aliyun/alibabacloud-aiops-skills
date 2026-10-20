"""Explicit diagnostic SDK transport for EIAM's private auxiliary APIs.

This is not an automatic public-API fallback. The caller must provide an
authorized default credential chain; CLI OAuth profiles are not imported.
"""
import argparse
import json
import re
import sys

from skill_ua import user_agent

ACTIONS = ('GetCloudAccountRoleConfig', 'CheckCloudAccountRoleConfig')
ENDPOINT = 'eiam.cn-hangzhou.aliyuncs.com'


def request_parameters(action, instance, account, role):
    if action not in ACTIONS:
        raise ValueError('Unsupported action')
    for value, prefix in ((instance, 'idaas_'), (account, 'ca_'), (role, 'carole_')):
        if not re.fullmatch(re.escape(prefix) + r'[A-Za-z0-9]+', value):
            raise ValueError('Invalid resource ID; refusing cloud calls')
    return {'InstanceId': instance, 'CloudAccountId': account,
            'CloudAccountRoleId': role}


def invoke(action, query, credential=None):
    # Validate attribution before resolving any credentials or making requests.
    ua = user_agent()
    from alibabacloud_credentials.client import Client as Credentials
    from alibabacloud_tea_openapi.client import Client
    from alibabacloud_tea_openapi import models as api
    from alibabacloud_tea_util import models as util
    client = Client(api.Config(credential=credential or Credentials(), endpoint=ENDPOINT,
                              user_agent=ua, connect_timeout=5000,
                              read_timeout=15000))
    params = api.Params(action=action, version='2021-12-01', protocol='HTTPS',
                        method='POST', auth_type='AK', style='RPC', pathname='/',
                        req_body_type='formData', body_type='json')
    result = client.call_api(params, api.OpenApiRequest(query=query),
                            util.RuntimeOptions(autoretry=False, max_attempts=1,
                                                connect_timeout=5000,
                                                read_timeout=15000))
    body = result.get('body')
    if not isinstance(body, dict):
        raise ValueError('Unexpected API response body')
    return body


def verified_credentials(expected_account):
    from alibabacloud_credentials.client import Client as Credentials
    from alibabacloud_tea_openapi.client import Client
    from alibabacloud_tea_openapi import models as api
    from alibabacloud_tea_util import models as util
    credential = Credentials()
    client = Client(api.Config(credential=credential,
        endpoint='sts.cn-hangzhou.aliyuncs.com', user_agent=user_agent(),
        connect_timeout=5000, read_timeout=15000))
    params = api.Params(action='GetCallerIdentity', version='2015-04-01',
        protocol='HTTPS', method='POST', auth_type='AK', style='RPC',
        pathname='/', req_body_type='formData', body_type='json')
    body = client.call_api(params, api.OpenApiRequest(), util.RuntimeOptions(
        autoretry=False, max_attempts=1, connect_timeout=5000, read_timeout=15000))['body']
    if body.get('AccountId') != expected_account:
        raise ValueError('SDK default credential account differs from confirmed EIAM owner')
    return credential


def failure(exc, action):
    # Never print SDK exception messages: these can include request headers.
    data = getattr(exc, 'data', None)
    data = data if isinstance(data, dict) else {}
    code = data.get('Code') or data.get('code') or getattr(exc, 'code', None)
    request_id = data.get('RequestId') or data.get('requestId')
    return {'status': 'blocked', 'failed_action': action,
            'error_type': type(exc).__name__,
            'reason': 'SDK default credential account differs from confirmed EIAM owner'
            if isinstance(exc, ValueError) and str(exc) == 'SDK default credential account differs from confirmed EIAM owner'
            else 'Auxiliary API validation, credentials or request failed; inspect safe error fields',
            'error_code': code if isinstance(code, str) and
            re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', code) else None,
            'RequestId': request_id if isinstance(request_id, str) and
            re.fullmatch(r'[A-Za-z0-9-]{1,100}', request_id) else None,
            'configuration_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=ACTIONS)
    parser.add_argument('--verify-identity', action='store_true')
    parser.add_argument('--expected-account-id', required=True)
    parser.add_argument('--instance-id')
    parser.add_argument('--cloud-account-id')
    parser.add_argument('--cloud-account-role-id')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[0-9]{12,20}', args.expected_account_id):
            raise ValueError('Invalid expected account')
        if args.verify_identity:
            verified_credentials(args.expected_account_id)
            print(json.dumps({'status': 'identity_verified', 'AccountId': args.expected_account_id}))
            return 0
        query = request_parameters(args.action, args.instance_id,
                                   args.cloud_account_id, args.cloud_account_role_id)
        credential = verified_credentials(args.expected_account_id)
        print(json.dumps(invoke(args.action, query, credential)))
        return 0
    except Exception as exc:
        print(json.dumps(failure(exc, args.action)))
        return 2


if __name__ == '__main__':
    sys.exit(main())
