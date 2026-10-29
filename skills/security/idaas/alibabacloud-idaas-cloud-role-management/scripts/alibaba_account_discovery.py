"""Resolve an exact connected Alibaba cloud account name using real scoped reads."""
import argparse
import json
import re
import sys
from alibaba_role_lifecycle import Executor, OperationError, verify_identity
from role_environment import inspect, repair


def resolve(executor, expected_owner, account_name, target_owner):
    verify_identity(executor, 'sts_eiam', expected_owner, 'EiamOwnerMismatch')
    accounts, seen, request_ids = [], set(), []
    token = None
    for _ in range(1000):
        params = {'instance-id': executor.plan['instance_id'], 'max-results': 100}
        if token:
            params['next-token'] = token
        page = executor.call('eiam', 'list-cloud-accounts', params)
        rows = page.get('CloudAccounts')
        if (not isinstance(rows, list) or not all(isinstance(row,dict) for row in rows)
                or not isinstance(page.get('RequestId'), str) or not page['RequestId']):
            raise OperationError('ListCloudAccounts', 'InvalidResponse')
        accounts.extend(rows)
        request_ids.append(page['RequestId'])
        token = page.get('NextToken') or None
        if token is not None and not isinstance(token,str):
            raise OperationError('ListCloudAccounts', 'InvalidPaginationToken')
        if not token:
            if page.get('TotalCount', len(accounts)) > len(accounts):
                raise OperationError('ListCloudAccounts', 'PaginationIncomplete')
            break
        if token in seen:
            raise OperationError('ListCloudAccounts', 'RepeatedPaginationToken')
        seen.add(token)
    else:
        raise OperationError('ListCloudAccounts', 'PaginationIncomplete')
    matches = [row for row in accounts if row.get('CloudAccountName') == account_name]
    if len(matches) != 1:
        raise OperationError('ListCloudAccounts', 'MissingOrAmbiguousAccountName')
    account = matches[0]
    account_id = account.get('CloudAccountId')
    if (not isinstance(account_id, str) or not re.fullmatch(r'ca_[A-Za-z0-9]+', account_id)
            or account.get('CloudAccountExternalId') != target_owner
            or account.get('CloudAccountVendorType') != 'alibaba_cloud'
            or account.get('InstanceId', executor.plan['instance_id']) != executor.plan['instance_id']):
        raise OperationError('ListCloudAccounts', 'AccountScopeMismatch')
    result = {'event': 'account_name_resolved', 'status': 'account_resolved',
              'instance_id': executor.plan['instance_id'], 'cloud_account_id': account_id,
              'account_name': account_name, 'account_id': target_owner,
              'eiam_profile': executor.plan['eiam_profile'], 'RequestIds': request_ids,
              'pages': len(request_ids), 'pagination_exhausted': True,
              'mutations_performed': False}
    executor.save('resolved-account', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('instance-id', 'account-name', 'target-owner-id', 'eiam-profile',
                 'eiam-owner-id', 'session-id', 'evidence-dir'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--audit-file')
    parser.add_argument('--repair-environment', action='store_true')
    args = parser.parse_args()
    try:
        if (not re.fullmatch(r'idaas_[A-Za-z0-9]+', args.instance_id)
                or not re.fullmatch(r'[0-9]{12,20}', args.eiam_owner_id)
                or not re.fullmatch(r'[0-9]{12,20}', args.target_owner_id)
                or not args.account_name.strip() or len(args.account_name) > 128):
            raise ValueError('Invalid exact account target')
        env = (repair('alibaba_cloud', 'resolve-account') if args.repair_environment
               else inspect('alibaba_cloud', scope='resolve-account'))
        if env['status'] != 'cli_capabilities_available':
            print(json.dumps(env)); return 2
        executor = Executor({'instance_id': args.instance_id, 'eiam_profile': args.eiam_profile},
                            args.evidence_dir, args.session_id, args.audit_file)
        print(json.dumps(resolve(executor, args.eiam_owner_id, args.account_name, args.target_owner_id)))
        return 0
    except OperationError as exc:
        print(json.dumps({'status': 'blocked', 'failed_action': exc.action,
                          'error_code': exc.code, 'RequestId': exc.request_id,
                          'mutations_performed': False})); return 2
    except (ValueError, KeyError, TypeError, OSError):
        print(json.dumps({'status': 'invalid_input_or_response', 'mutations_performed': False})); return 2


if __name__ == '__main__':
    sys.exit(main())
