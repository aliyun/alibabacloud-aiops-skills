"""Discover an absent Alibaba user role and prepare an unsealed plan; no writes.

This adapter reuses one explicitly selected existing Custom policy unchanged.
It never creates a role, seals a plan, checks health, or establishes approval.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import time

from alibaba_role_lifecycle import Executor, OperationError, document, verify_identity
from role_tools import load, validate, validate_plan


def prepare(request, policy_name, output, session):
    validate(request)
    if request['vendor'] != 'alibaba_cloud':
        raise ValueError('This planner supports Alibaba Cloud only')
    for field in ('eiam_profile', 'cloud_profile', 'eiam_owner_id', 'cloud_account_id'):
        if not isinstance(request.get(field), str) or not request[field].strip():
            raise ValueError('Missing ' + field)
    if not re.fullmatch(r'\d{12,20}', request['eiam_owner_id'], flags=re.ASCII):
        raise ValueError('Invalid EIAM owner')
    if not re.fullmatch(r'ca_[A-Za-z0-9]+', request['cloud_account_id']):
        raise ValueError('Invalid connected account ID')
    duration = request.get('max_session_duration', 3600)
    if type(duration) is not int or not 3600 <= duration <= 43200:
        raise ValueError('Invalid session duration')
    if not re.fullmatch(r'[A-Za-z0-9.-]{1,128}', policy_name):
        raise ValueError('Invalid existing policy name')
    planning_started_ms = int(time.time() * 1000)
    ex = Executor(request, output, session)
    for domain, owner in [('sts_eiam', request['eiam_owner_id']), ('sts_cloud', request['account_id'])]:
        verify_identity(ex, domain, owner)
    instance = ex.call('eiam', 'GetInstance', {'InstanceId': request['instance_id']}).get('Instance', {})
    if instance.get('InstanceId') != request['instance_id']:
        raise OperationError('GetInstance', 'InstanceMismatch')
    account = ex.eiam('get-cloud-account').get('CloudAccount', {})
    if (account.get('CloudAccountId') != request['cloud_account_id']
            or account.get('CloudAccountExternalId') != request['account_id']
            or account.get('CloudAccountSite') != 'china_mainland'
            or account.get('CloudAccountVendorType') != 'alibaba_cloud'
            or account.get('CloudAccountHealth') != 'healthy'):
        raise OperationError('GetCloudAccount', 'AccountMismatchOrUnhealthy')
    config = account.get('CloudAccountProviderConfig', {})
    provider_name = account.get('CloudAccountProviderName')
    if not provider_name or not config.get('Issuer') or not config.get('Audience'):
        raise OperationError('GetCloudAccount', 'ProviderConfigurationMissing')
    provider = ex.call('ims', 'GetOIDCProvider', {'OIDCProviderName': provider_name,
        'endpoint': 'ims.aliyuncs.com', 'region': 'cn-hangzhou'}).get('OIDCProvider', {})
    clients = provider.get('ClientIds', [])
    if isinstance(clients, dict):
        clients = clients.get('ClientId', [])
    if isinstance(clients, str):
        clients = [v.strip() for v in clients.split(',')]
    expected_arn = 'acs:ram::' + request['account_id'] + ':oidc-provider/' + provider_name
    if (provider.get('Arn') != expected_arn or provider.get('IssuerUrl') != config['Issuer']
            or not isinstance(clients, list) or config['Audience'] not in clients):
        raise OperationError('GetOIDCProvider', 'ProviderMismatch')
    roles = ex.roles()
    systems = [r for r in roles if r.get('CloudAccountRoleUsageType') == 'system']
    if not systems or any(r.get('CloudAccountRoleHealth') != 'healthy' for r in systems):
        raise OperationError('ListCloudAccountRoles', 'SystemRoleUnhealthy')
    if any(r.get('CloudAccountRoleName') == request['role_name'] for r in roles):
        raise OperationError('ListCloudAccountRoles', 'RoleAlreadyExists')
    if ex.call('ram', 'GetRole', {'RoleName': request['role_name']}, absent='EntityNotExist.Role') is not None:
        raise OperationError('GetRole', 'RoleAlreadyExists')
    policy = ex.call('ram', 'GetPolicy', {'PolicyName': policy_name, 'PolicyType': 'Custom'}).get('Policy', {})
    version = policy.get('DefaultVersion')
    if policy.get('PolicyName') != policy_name or not isinstance(version, str) or not version:
        raise OperationError('GetPolicy', 'PolicyMetadataMismatch')
    detail = ex.call('ram', 'GetPolicyVersion', {'PolicyName': policy_name, 'PolicyType': 'Custom',
        'VersionId': version}).get('PolicyVersion', {})
    if detail.get('VersionId') != version:
        raise OperationError('GetPolicyVersion', 'PolicyVersionMismatch')
    plan = {key: request[key] for key in ('instance_id', 'vendor', 'account_id', 'cloud_account_id',
        'role_name', 'permission_intent', 'eiam_profile', 'cloud_profile', 'eiam_owner_id')}
    plan.update(planning_started_ms=planning_started_ms, site='china_mainland', project_selection='server_default', mode='create',
        discovery_evidence=[str(ex.audit_file.resolve())],
        business_policies=[{'kind': 'custom', 'name': policy_name, 'version': version,
            'document': document(detail.get('PolicyDocument'))}],
        trust_constraints={'provider_id': expected_arn, 'issuer': config['Issuer'],
            'audience': config['Audience'], 'max_session_duration': duration},
        changes=['Create only the absent named EIAM user role and RAM role',
            'Bind the selected existing Custom policy unchanged; no assignment'])
    validate_plan(plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-file', required=True)
    parser.add_argument('--policy-name', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--output-plan', required=True)
    args = parser.parse_args()
    try:
        target = Path(args.output_plan)
        if target.exists():
            raise ValueError('Refusing to replace an existing plan')
        plan = prepare(load(args.request_file), args.policy_name, args.evidence_dir, args.session_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as handle:
            json.dump(plan, handle, indent=2)
        print(json.dumps({'status': 'unsealed_plan_prepared', 'plan_path': str(target.resolve()),
            'plan': plan, 'user_approval_established': False, 'mutations_performed': False,
            'fresh_health_checked': False}))
        return 0
    except (ValueError, KeyError, OSError, OperationError) as exc:
        result = {'status': 'planning_blocked', 'error': str(exc), 'mutations_performed': False}
        if isinstance(exc, OperationError):
            result.update(error_code=exc.code, RequestId=exc.request_id)
        print(json.dumps(result)); return 2


if __name__ == '__main__':
    sys.exit(main())
