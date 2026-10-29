"""Bounded read-only EIAM role inspection and initial-discovery diagnosis.

No target-cloud calls, mutations, health checks or plan approval are implemented.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

from alibaba_role_lifecycle import Executor, OperationError, verify_identity, checked_read_command
from role_tools import load, validate


def inspect_system(executor, expected_owner, name):
    verify_identity(executor, 'sts_eiam', expected_owner, 'EiamOwnerMismatch')
    matches = [r for r in executor.roles() if r.get('CloudAccountRoleName') == name]
    if len(matches) != 1:
        raise OperationError('ListCloudAccountRoles', 'MissingOrAmbiguousRole')
    role_id = matches[0].get('CloudAccountRoleId')
    if not isinstance(role_id, str) or not re.fullmatch(r'carole_[A-Za-z0-9]+', role_id):
        raise OperationError('ListCloudAccountRoles', 'InvalidRoleId')
    role = executor.eiam('get-cloud-account-role', **{'cloud-account-role-id': role_id})['CloudAccountRole']
    if (role.get('CloudAccountRoleId') != role_id or
            role.get('CloudAccountRoleName') != name or
            role.get('InstanceId') != executor.plan['instance_id'] or
            role.get('CloudAccountId') != executor.plan['cloud_account_id'] or
            role.get('CloudAccountRoleUsageType') != 'system'):
        raise OperationError('GetCloudAccountRole', 'NotTheRequestedSystemRole')
    result = {'status': 'system_role_inspected', 'cloud_account_role_id': role_id,
              'role_name': name, 'usage': 'system',
              'creation_type': role.get('CloudAccountRoleCreationType'),
              'description': role.get('Description'), 'mutations_performed': False,
              'target_cloud_calls_performed': False,
              'summary': ('Protected system role; usage: system. Purpose: connected-account '
                          'federation and management. Read-only inspection complete. '
                          'No target-cloud calls, health checks, plans or changes performed.')}
    executor.save('system-role-inspection', result)
    return result


def diagnose(executor, expected_owner, operation):
    if operation not in ('get-instance', 'get-cloud-account'):
        raise ValueError('Unsupported diagnostic read')
    verify_identity(executor, 'sts_eiam', expected_owner, 'EiamOwnerMismatch')
    params = {'instance-id': executor.plan['instance_id']}
    if operation == 'get-cloud-account':
        params['cloud-account-id'] = executor.plan['cloud_account_id']
    executor.call('eiam', operation, params)
    return {'status': 'diagnostic_read_succeeded', 'mutations_performed': False,
            'summary': 'Initial diagnostic read succeeded; diagnosis ended without provisioning.'}


def validate_request_file(path, instance, owner):
    request = validate(load(path))
    if request['instance_id'] != instance or request['vendor'] != 'alibaba_cloud':
        raise ValueError('Request target differs from diagnostic target')
    # Owner here is the target cloud account, not the EIAM instance owner.
    if request['account_id'] != owner:
        raise ValueError('Request account differs from diagnostic target')
    argv = [sys.executable, str(Path(__file__).with_name('role_tools.py')),
            'validate', '--input', str(Path(path).resolve())]
    completed = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, shell=False, timeout=15)
    print(json.dumps({'command': shlex.join(argv), 'exit_code': completed.returncode,
                      'stdout': completed.stdout, 'stderr': completed.stderr}), flush=True)
    if completed.returncode:
        raise ValueError('Local request validation failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inspect-system', 'diagnose'))
    parser.add_argument('--instance-id', required=True)
    parser.add_argument('--cloud-account-id', required=True)
    parser.add_argument('--eiam-profile', required=True)
    parser.add_argument('--eiam-owner-id', required=True)
    parser.add_argument('--role-name')
    parser.add_argument('--operation', choices=('get-instance', 'get-cloud-account'))
    parser.add_argument('--request-file')
    parser.add_argument('--target-owner-id')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--audit-file')
    parser.add_argument('--repair-environment',action='store_true',help='Repair official CLI packages before the first API call; no credential changes')
    parser.add_argument('--read-command', nargs=argparse.REMAINDER,
        help='Optional exact official diagnostic read argv; no additional read is performed')
    args = parser.parse_args()
    try:
        if (not re.fullmatch(r'idaas_[A-Za-z0-9]+', args.instance_id) or
                not re.fullmatch(r'ca_[A-Za-z0-9]+', args.cloud_account_id) or
                not re.fullmatch(r'[0-9]{12,20}', args.eiam_owner_id)):
            raise ValueError('Invalid exact diagnostic target')
        if args.mode == 'inspect-system':
            if not args.role_name or args.operation or args.request_file or args.read_command:
                raise ValueError('System inspection requires only the exact role name')
        else:
            if not args.operation or not args.request_file or not args.target_owner_id:
                raise ValueError('Diagnosis requires the complete user request and target owner')
            validate_request_file(args.request_file, args.instance_id, args.target_owner_id)
        plan = {'instance_id': args.instance_id, 'cloud_account_id': args.cloud_account_id,
                'eiam_profile': args.eiam_profile}
        explicit = checked_read_command(plan, args.read_command)
        if explicit and explicit[2] != args.operation:
            raise ValueError('Explicit read differs from the requested diagnosis')
        from role_environment import inspect, repair
        environment = (repair('alibaba_cloud', args.mode) if args.repair_environment
                       else inspect('alibaba_cloud', scope=args.mode))
        if environment['status'] != 'cli_capabilities_available':
            print(json.dumps(environment)); return 2
        executor = Executor(plan, args.evidence_dir, args.session_id, args.audit_file, read_command=explicit)
        if args.mode == 'inspect-system':
            result = inspect_system(executor, args.eiam_owner_id, args.role_name)
        else:
            result = diagnose(executor, args.eiam_owner_id, args.operation)
        print(json.dumps(result)); return 0
    except OperationError as exc:
        print(json.dumps({'status': 'blocked', 'failed_action': exc.action,
                          'error_code': exc.code, 'RequestId': exc.request_id,
                          'summary': 'Workflow terminated at the failed read; no downstream calls.'}))
        return 2
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired):
        print(json.dumps({'status': 'invalid_input_or_response', 'mutations_performed': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
