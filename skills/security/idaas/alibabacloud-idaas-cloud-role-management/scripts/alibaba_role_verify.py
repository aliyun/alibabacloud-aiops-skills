"""Independent read-only verification of an approved Alibaba USER role.

Does not create, attach, update, check-health, assign, or delete resources.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from role_tools import load, canonical, check
from alibaba_role_lifecycle import Executor, OperationError, document, trust_matches


def load_original_fixture(path):
    index = Path(path)
    roots = [Path(value) for key in ('EVAL_SETUP_RESOURCE_DIR','EVAL_RESOURCE_DIR')
             if (value := os.environ.get(key))]
    if not index.is_file():
        if index.name != 'role-eval-fixture.json':
            raise FileNotFoundError('Original fixture index unavailable')
        matches = [root/index.name for root in roots if (root/index.name).is_file()]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous original fixture index')
        index = matches[0]
    fixture = load(index)
    current_case = os.environ.get('EVAL_TESTCASE_UUID')
    if current_case and fixture.get('platform_testcase_uuid') not in (None,current_case):
        raise ValueError('Fixture belongs to another testcase')
    original = Path(fixture['plan_path'])
    if not original.is_file():
        relative = Path(fixture.get('plan_relative_path',''))
        if not relative.parts or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Original plan unavailable; unsafe or missing relative location')
        root = index.resolve().parent
        original = (root/relative).resolve()
        original.relative_to(root)
        if not original.is_file():
            raise FileNotFoundError('Original sealed bytes unavailable')
    artifact = load(original)
    check(artifact, fixture['plan_sha256'])
    if artifact['client_token'] != fixture['client_token']:
        raise ValueError('Original fixture token changed')
    return fixture, artifact


def verify(artifact, role_id, started_ms, output, session=None):
    artifact = check(artifact, artifact['sha256'])
    p = artifact['plan']
    ex = Executor(p, output, session)
    for domain, owner in [('sts_eiam', p['eiam_owner_id']), ('sts_cloud', p['account_id'])]:
        if ex.call(domain, 'GetCallerIdentity')['AccountId'] != owner:
            raise OperationError('GetCallerIdentity', 'WrongAccount')
    record = ex.eiam('GetCloudAccountRole', **{'CloudAccountRoleId': role_id})['CloudAccountRole']
    if any(record.get(k) != v for k, v in {
        'InstanceId': p['instance_id'], 'CloudAccountId': p['cloud_account_id'],
        'CloudAccountRoleId': role_id, 'CloudAccountRoleName': p['role_name'],
        'CloudAccountRoleUsageType': 'user'}.items()):
        raise OperationError('GetCloudAccountRole', 'RoleOwnershipMismatch')
    health = record.get('CloudAccountRoleHealthCheckResult', {})
    if (record.get('CloudAccountRoleHealth') != 'healthy' or health.get('Result') != 'success'
            or health.get('LastCheckTime', 0) < started_ms):
        raise OperationError('GetCloudAccountRole', 'FreshHealthNotEstablished')
    config = ex.eiam('GetCloudAccountRoleConfig', **{'CloudAccountRoleId': role_id})['CloudAccountRoleConfig']['AlibabaCloudAccountRoleConfig']
    tc = p['trust_constraints']
    if (config.get('RoleName') != p['role_name'] or not trust_matches(
            config['TrustConfig']['AssumeRolePolicyDocument'], tc)):
        raise OperationError('GetCloudAccountRoleConfig', 'DynamicTrustMismatch')
    role = ex.call('ram', 'GetRole', {'RoleName': p['role_name']})
    ex.check_cloud_role(role, tc)
    if role['Role']['Arn'] != 'acs:ram::' + p['account_id'] + ':role/' + p['role_name'].lower():
        raise OperationError('GetRole', 'WrongRoleArn')
    policies = p['business_policies']
    expected = sorted((x['name'], 'Custom') for x in policies)
    actual = ex.policies()
    if sorted((x['PolicyName'], x['PolicyType']) for x in actual) != expected:
        raise OperationError('ListPoliciesForRole', 'UnexpectedFinalPermissions')
    versions = []
    for policy in policies:
        metadata = ex.call('ram', 'GetPolicy', {'PolicyName': policy['name'], 'PolicyType': 'Custom'})
        ex.check_policy(metadata, policy)
        versions.append({'name': policy['name'], 'version': metadata['Policy']['DefaultVersion'],
                         'sha256': hashlib.sha256(canonical(policy['document'])).hexdigest()})
    result = {'verified': True, 'role_id': role_id, 'role_name': p['role_name'],
              'role_arn': role['Role']['Arn'], 'fresh_after_ms': started_ms,
              'health': health, 'policies': versions, 'plan_sha256': artifact['sha256'],
              'assigned_to_users': False, 'effective_user_access_tested': False,
              'cloud_calls_read_only': True}
    ex.save('independent-verification', result)
    return result


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--plan')
    a.add_argument('--fixture')
    a.add_argument('--role-id')
    a.add_argument('--started-ms', type=int)
    a.add_argument('--output', required=True)
    args = a.parse_args()
    try:
        if args.fixture:
            fixture, artifact = load_original_fixture(args.fixture)
            scope = load(Path(__file__).resolve().parents[1]/'evals/verification/approved-scope.json')
            plan = artifact['plan']
            if any(plan.get(k) != scope[k] for k in ('instance_id','cloud_account_id','account_id','eiam_owner_id','trust_constraints')):
                raise ValueError('Fixture scope differs from the approved evaluation baseline')
            policies = plan['business_policies']
            if (len(policies) != 1 or policies[0]['name'] != scope['policy_name'] or
                    hashlib.sha256(canonical(policies[0]['document'])).hexdigest() != scope['policy_sha256']):
                raise ValueError('Fixture policy differs from approved complete business document')
            if fixture['kind'] != 'none' and not plan['role_name'].startswith('idaas-role-eval-'):
                raise ValueError('Role outside approved test prefix')
            if artifact['client_token'] != fixture['client_token'] or artifact['plan']['role_name'] != fixture['role_name']:
                raise ValueError('Original fixture plan or token changed')
            ex = Executor(artifact['plan'], Path(args.output)/'discovery', None)
            if ex.call('sts_eiam', 'GetCallerIdentity').get('AccountId') != plan['eiam_owner_id']:
                raise OperationError('GetCallerIdentity', 'WrongAccount')
            found = [r for r in ex.roles() if r.get('CloudAccountRoleName') == fixture['role_name']]
            if len(found) != 1 or (fixture['role_id'] and found[0]['CloudAccountRoleId'] != fixture['role_id']):
                raise ValueError('Original EIAM record not preserved')
            result = verify(artifact, found[0]['CloudAccountRoleId'], fixture['created_at_ms'], Path(args.output)/'readback')
            if result['policies'][0]['version'] != fixture['policy_version']:
                raise ValueError('Existing policy default version changed')
            print(json.dumps(result))
        else:
            if not args.plan or not args.role_id:
                raise ValueError('Plan and role ID required')
            artifact = load(args.plan)
            check(artifact, artifact['sha256'])
            started_ms = args.started_ms
            if started_ms is None:
                started_ms = artifact['plan'].get('planning_started_ms')
            if type(started_ms) is not int or started_ms <= 0:
                raise ValueError('Fresh check start required in args or original sealed plan')
            print(json.dumps(verify(artifact, args.role_id, started_ms, args.output)))
    except (OperationError, ValueError, KeyError, OSError) as err:
        print(json.dumps({'verified': False, 'error_code': getattr(err, 'code', type(err).__name__),
                          'RequestId': getattr(err, 'request_id', None)}))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
