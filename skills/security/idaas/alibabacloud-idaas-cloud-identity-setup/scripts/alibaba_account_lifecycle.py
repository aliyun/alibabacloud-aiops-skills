#!/usr/bin/env python3
"""Confirmed EIAM onboarding with read-only Alibaba RAM reconciliation.

This helper creates only the EIAM record. Missing or different RAM resources
stop the workflow and require a separate repair plan; it never changes RAM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import cloud_identity_preflight as preflight
from skill_ua import user_agent


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def semantic(value):
    """Compare policy sets, including singleton string/list representations."""
    if isinstance(value, dict):
        return tuple(sorted((k, semantic(v)) for k, v in value.items()))
    if isinstance(value, list):
        values = sorted((semantic(v) for v in value), key=repr)
        return values[0] if len(values) == 1 else tuple(values)
    return value


def document(value):
    return json.loads(value) if isinstance(value, str) else value


class Lifecycle:
    def __init__(self, plan):
        self.plan = plan
        self.evidence = []

    def call(self, product, action, target=False, **parameters):
        if self.plan.get('eiam_auxiliary_transport') == 'sdk' and product == 'eiam' and action in (
                'get-cloud-account-role-config', 'check-cloud-account-role-config'):
            action_name = {'get-cloud-account-role-config': 'GetCloudAccountRoleConfig',
                           'check-cloud-account-role-config': 'CheckCloudAccountRoleConfig'}[action]
            argv = [sys.executable, str(Path(__file__).with_name('eiam_auxiliary_api.py')),
                    '--action', action_name, '--expected-account-id', self.plan['eiam_account_id']]
            for key, value in parameters.items():
                argv.extend(['--' + key, str(value)])
            data = preflight.run_json(argv)
            self.evidence.append({'product': product, 'action': action_name,
                                  'transport': 'sdk', 'RequestId': data.get('RequestId')})
            return data
        profile = self.plan['cloud_profile'] if target else self.plan['eiam_profile']
        argv = [preflight.cli_path('aliyun'), product, action, '--profile', profile]
        for key, value in parameters.items():
            argv.extend(['--' + key, str(value)])
        data = preflight.run_json(argv)
        self.evidence.append({'product': product, 'action': action, 'RequestId': data.get('RequestId')})
        return data

    def matching_accounts(self):
        return [a for a in preflight.list_accounts(self.plan['instance_id'], self.plan['eiam_profile'])
                if preflight.account_match(a, 'alibaba_cloud', self.plan['account_id'])]

    def ensure_account(self):
        accounts = self.matching_accounts()
        if len(accounts) > 1:
            raise ValueError('multiple matching EIAM records; stopped')
        expected = self.plan.get('expected_existing_account_id')
        if expected and (not accounts or accounts[0]['CloudAccountId'] != expected):
            raise ValueError('approved existing EIAM record disappeared or changed; no creation permitted')
        if accounts:
            return accounts[0]['CloudAccountId'], 'reused'
        p = self.plan
        kwargs = dict(InstanceId=p['instance_id'], CloudAccountExternalId=p['account_id'],
                      CloudAccountVendorType='alibaba_cloud', CloudAccountSite=p['site'],
                      CloudAccountProviderName=p['provider_name'],
                      CloudAccountName='alibaba_' + p['account_id'], ClientToken=p['client_token'])
        try:
            result = self.call('eiam', 'CreateCloudAccount', **kwargs)
        except preflight.CommandError as error:
            if 'timed out' not in str(error):
                raise
            # A timeout does not prove failure. Read back before one stable-token retry.
            accounts = self.matching_accounts()
            if len(accounts) == 1:
                return accounts[0]['CloudAccountId'], 'recovered_after_timeout'
            if accounts:
                raise ValueError('ambiguous record state after timeout')
            result = self.call('eiam', 'CreateCloudAccount', **kwargs)
        return result['CloudAccountId'], 'created'

    def inspect(self, account_id):
        common = {'InstanceId': self.plan['instance_id'], 'CloudAccountId': account_id}
        account = self.call('eiam', 'GetCloudAccount', **common)['CloudAccount']
        if (account.get('CloudAccountExternalId') != self.plan['account_id'] or
                account.get('CloudAccountSite') != self.plan['site'] or
                account.get('CloudAccountProviderName') != self.plan['provider_name']):
            raise ValueError('EIAM record differs from the confirmed target')
        roles = self.call('eiam', 'ListCloudAccountRoles', **common)['CloudAccountRoles']
        systems = [r for r in roles if r.get('CloudAccountRoleUsageType') == 'system'
                   and r.get('CloudAccountRoleCreationType') == 'system_init']
        if len(systems) != 1:
            raise ValueError('expected exactly one automatically created system role')
        role_id = systems[0]['CloudAccountRoleId']
        self.previous_check = {
            'account': (account.get('CloudAccountHealthCheckResult') or {}).get('LastCheckTime', 0),
            'role': (systems[0].get('CloudAccountRoleHealthCheckResult') or {}).get('LastCheckTime', 0)}
        lower = {'instance-id': self.plan['instance_id'], 'cloud-account-id': account_id,
                 'cloud-account-role-id': role_id}
        config = self.call('eiam', 'get-cloud-account-role-config', **lower)
        generated = config['CloudAccountRoleConfig']['AlibabaCloudAccountRoleConfig']
        provider = self.call('ims', 'GetOIDCProvider', True,
                             OIDCProviderName=self.plan['provider_name'])['OIDCProvider']
        provider_config = account['CloudAccountProviderConfig']
        if provider['IssuerUrl'] != provider_config['Issuer']:
            raise ValueError('OIDC issuer differs; RAM repair is not approved')
        audiences = provider.get('ClientIds', '')
        audiences = audiences.split(',') if isinstance(audiences, str) else audiences
        if set(audiences) != {provider_config['Audience']}:
            raise ValueError('OIDC audience differs; RAM repair is not approved')
        role = self.call('ram', 'GetRole', True, RoleName=generated['RoleName'])['Role']
        trust = generated['TrustConfig']
        if semantic(document(role['AssumeRolePolicyDocument'])) != semantic(document(trust['AssumeRolePolicyDocument'])):
            raise ValueError('RAM trust differs; repair is not approved')
        if int(role['MaxSessionDuration']) != int(trust['RoleSessionDuration']):
            raise ValueError('RAM session duration differs; repair is not approved')
        policies = self.call('ram', 'ListPoliciesForRole', True,
                             RoleName=generated['RoleName'])['Policies']['Policy']
        actual = []
        for attached in policies:
            info = self.call('ram', 'GetPolicy', True, PolicyName=attached['PolicyName'],
                             PolicyType=attached['PolicyType'])['Policy']
            version = self.call('ram', 'GetPolicyVersion', True, PolicyName=attached['PolicyName'],
                                PolicyType=attached['PolicyType'], VersionId=info['DefaultVersion'])
            actual.append(semantic(document(version['PolicyVersion']['PolicyDocument'])))
        if not all(semantic(document(p['PolicyDocument'])) in actual for p in generated['PolicyConfigs']):
            raise ValueError('required policy is not attached; repair is not approved')
        return common, lower, role_id

    def apply(self):
        for profile, expected in [(self.plan['eiam_profile'], self.plan['eiam_account_id']),
                                  (self.plan['cloud_profile'], self.plan['account_id'])]:
            actual, _ = preflight.caller_identity('alibaba_cloud', profile)
            if actual != expected:
                raise ValueError('profile identity changed; no write is permitted')
        # Re-run complete discovery immediately before the confirmed create.
        for instance in preflight.list_instances(self.plan['eiam_profile']):
            matches = [a for a in preflight.list_accounts(instance['InstanceId'], self.plan['eiam_profile'])
                       if preflight.account_match(a, 'alibaba_cloud', self.plan['account_id'])]
            if matches and instance['InstanceId'] != self.plan['instance_id']:
                raise ValueError('account is managed by another instance; cross-instance transfer is unsupported; no writes permitted')
        account_id, operation = self.ensure_account()
        common, lower, role_id = self.inspect(account_id)
        check = self.call('eiam', 'check-cloud-account-role-config', **lower)
        for attempt in range(3):
            account = self.call('eiam', 'GetCloudAccount', **common)['CloudAccount']
            roles = self.call('eiam', 'ListCloudAccountRoles', **common)['CloudAccountRoles']
            role = next(r for r in roles if r['CloudAccountRoleId'] == role_id)
            account_result = account.get('CloudAccountHealthCheckResult') or {}
            role_result = role.get('CloudAccountRoleHealthCheckResult') or {}
            fresh = (account_result.get('LastCheckTime', 0) > (self.previous_check['account'] or 0)
                     and role_result.get('LastCheckTime', 0) > (self.previous_check['role'] or 0))
            if fresh:
                break
            if attempt < 2:
                time.sleep(1)
        if (not fresh or account.get('CloudAccountHealth') != 'healthy'
                or role.get('CloudAccountRoleHealth') != 'healthy'
                or account_result.get('Result') != 'success' or role_result.get('Result') != 'success'):
            raise ValueError('fresh successful account and system-role health checks were not observed')
        repeated = self.matching_accounts()
        if len(repeated) != 1 or repeated[0]['CloudAccountId'] != account_id:
            raise ValueError('repeat discovery did not find the same unique record')
        return {'status': 'healthy', 'cloud_account_id': account_id, 'system_role_id': role_id,
                'operation': operation, 'ram_operation': 'reused_without_writes',
                'RequestId': check.get('RequestId'), 'account_health': account['CloudAccountHealth'],
                'role_health': role['CloudAccountRoleHealth'],
                'account_check': account_result, 'role_check': role_result, 'evidence': self.evidence}


def require_lifecycle_commands(transport="cli", owner=None):
    """Validate local command capabilities before creating any EIAM record."""
    if transport == 'sdk':
        if not owner:
            raise ValueError('SDK transport requires the confirmed EIAM owner account')
        argv = [sys.executable, str(Path(__file__).with_name('eiam_auxiliary_api.py')),
                '--verify-identity', '--expected-account-id', owner]
        result = preflight.run_json(argv)
        if result.get('status') != 'identity_verified':
            raise ValueError('SDK identity verification did not succeed')
        return
    for action in ('get-cloud-account-role-config', 'check-cloud-account-role-config'):
        argv = [preflight.cli_path('aliyun'), 'eiam', action, '--help']
        env = os.environ.copy()
        env['ALIBABA_CLOUD_USER_AGENT'] = user_agent()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=20,
                                  stdin=subprocess.DEVNULL, env=env)
        except subprocess.TimeoutExpired as exc:
            raise preflight.CommandError(argv, 'Local EIAM command capability check timed out; no onboarding write is permitted', error_type='environment') from exc
        if proc.returncode or action not in proc.stdout or '--cloud-account-role-id' not in proc.stdout:
            raise preflight.CommandError(argv, 'Installed EIAM CLI does not provide the required lifecycle command; use a trusted compatible official distribution', error_type='environment')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'apply'])
    parser.add_argument('--plan-file', required=True)
    parser.add_argument('--instance-id')
    parser.add_argument('--account-id')
    parser.add_argument('--eiam-profile')
    parser.add_argument('--cloud-profile')
    parser.add_argument('--site', choices=['china_mainland', 'global'], default='china_mainland')
    parser.add_argument('--provider-name', default='idaas-eiam-oidc-provider')
    parser.add_argument('--eiam-auxiliary-transport', choices=['cli', 'sdk'], default='cli')
    parser.add_argument('--eiam-account-id')
    requirement = parser.add_mutually_exclusive_group()
    requirement.add_argument('--require-new', action='store_true', help='Reject existing EIAM records during new-onboarding planning')
    requirement.add_argument('--require-existing', action='store_true', help='Bind the plan to an existing EIAM record and prohibit creation')
    parser.add_argument('--approved-plan', help='SHA256 of the exact plan confirmed by the user')
    args = parser.parse_args()
    path = Path(args.plan_file)
    lifecycle = None
    try:
        os.environ.setdefault('SKILL_SESSION_ID', uuid.uuid4().hex)
        user_agent()  # Fail on invalid manifest before cloud calls.
        if args.mode == 'plan':
            if not all([args.instance_id, args.account_id, args.eiam_profile, args.cloud_profile]):
                raise ValueError('plan requires instance, account and both profile names')
            require_lifecycle_commands(args.eiam_auxiliary_transport, args.eiam_account_id)
            argv = [sys.executable, str(Path(__file__).with_name('cloud_identity_preflight.py')),
                    '--vendor', 'alibaba_cloud', '--account-id', args.account_id,
                    '--instance-id', args.instance_id, '--eiam-profile', args.eiam_profile,
                    '--cloud-profile', args.cloud_profile, '--site', args.site]
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
            discovery = json.loads(proc.stdout)
            if proc.returncode or discovery['status'] not in ['ready_new', 'ready_resume']:
                raise ValueError('preflight blocks onboarding: ' + discovery['status'])
            if args.require_new and discovery['status'] != 'ready_new':
                raise ValueError('fixture mismatch: new onboarding requires ready_new; existing EIAM record must not be substituted')
            if args.require_existing and discovery['status'] != 'ready_resume':
                raise ValueError('existing-only workflow requires ready_resume; no creation permitted')
            owner, _ = preflight.caller_identity('alibaba_cloud', args.eiam_profile)
            if args.eiam_auxiliary_transport == 'sdk' and owner != args.eiam_account_id:
                raise ValueError('CLI and SDK EIAM owner identities do not match')
            plan = dict(eiam_auxiliary_transport=args.eiam_auxiliary_transport, instance_id=args.instance_id, account_id=args.account_id,
                        eiam_profile=args.eiam_profile, cloud_profile=args.cloud_profile,
                        eiam_account_id=owner, site=args.site, provider_name=args.provider_name,
                        client_token=uuid.uuid4().hex, preflight_status=discovery['status'],
                        actions=['create_or_reuse_eiam_record', 'inspect_and_reuse_matching_ram',
                                 'check_health', 'repeat_discovery'], ram_writes=False)
            if args.require_existing:
                plan['expected_existing_account_id'] = discovery['target_record']['cloud_account_id']
                if not plan['expected_existing_account_id']:
                    raise ValueError('existing record ID missing; no plan generated')
                plan['actions'][0] = 'reuse_exact_eiam_record_without_creation'
            if not re.fullmatch(r'idaas-eiam-[A-Za-z0-9_.@-]{3,128}', args.provider_name):
                raise ValueError('invalid provider name')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'status': 'awaiting_confirmation', 'plan': plan,
                              'plan_sha256': digest(plan)}, indent=2))
        else:
            plan = json.loads(path.read_text(encoding='utf-8'))
            if args.approved_plan != digest(plan):
                raise ValueError('exact plan has not been confirmed; no cloud calls')
            require_lifecycle_commands(plan.get('eiam_auxiliary_transport', 'cli'), plan['eiam_account_id'])
            lifecycle = Lifecycle(plan)
            print(json.dumps(lifecycle.apply(), indent=2))
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, preflight.CommandError) as error:
        print(json.dumps({'status': 'blocked', 'reason': str(error),
                          **(preflight.error_fields(error) if isinstance(error, preflight.CommandError) else {}),
                          'evidence': lifecycle.evidence if lifecycle else [],
                          'recovery': 'read target state; resume the same approved plan; do not roll back RAM'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
