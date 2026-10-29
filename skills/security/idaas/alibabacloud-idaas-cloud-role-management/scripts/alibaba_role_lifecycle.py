"""Approved Alibaba USER role creation/reuse and readback. Never deletes resources.

CLI authentication is resolved by official named profiles. No credential parsing.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote

from role_tools import load, check, canonical
from skill_ua import user_agent
from eiam_transport import AUXILIARY, auxiliary_command


class OperationError(Exception):
    def __init__(self, action, code, request_id=None):
        self.action, self.code, self.request_id = action, code, request_id
        super().__init__(code)


def cli_error(stderr, stdout=''):
    """Structured fields outrank human messages; conflicting errors fail closed."""
    structured = []
    saw_json = False
    for stream in (stderr, stdout):
        try:
            body = json.loads(stream)
        except (ValueError, TypeError):
            continue
        saw_json = True
        if not isinstance(body, dict):
            continue
        codes = {body[key] for key in ('error_code', 'Code', 'ErrorCode')
                 if isinstance(body.get(key), str) and body[key]}
        ids = {body[key] for key in ('request_id', 'RequestId', 'RequestID')
               if isinstance(body.get(key), str) and body[key]}
        if len(codes) != 1 or len(ids) > 1:
            return 'CLIError', None
        code = next(iter(codes))
        request_id = next(iter(ids), None)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', code):
            return 'CLIError', None
        structured.append((code, request_id))
    if saw_json:
        return structured[0] if len(set(structured)) == 1 else ('CLIError', None)
    text = '\n'.join(filter(None, (stderr, stdout)))
    codes = set(re.findall(r'^\s*(?:ErrorCode|Code)\s*:\s*([A-Za-z0-9_.-]+)(?=\s|:|$)',
                           text, re.I | re.M))
    request = re.search(r'(?:RequestId:|request id:)\s*([A-Za-z0-9_-]+)', text, re.I)
    return (next(iter(codes)) if len(codes) == 1 else 'CLIError',
            request.group(1) if request else None)

def document(value):
    if isinstance(value, str):
        value = json.loads(unquote(value) if value.lstrip().startswith('%') else value)
    if not isinstance(value, dict):
        raise ValueError('Missing policy document')
    return value


def trust_matches(trust, constraints):
    trust = document(trust)
    statements = trust.get('Statement')
    if not isinstance(statements, list) or len(statements) != 1:
        return False
    statement = statements[0]
    def values(v):
        return v if isinstance(v, list) else [v]
    conditions = statement.get('Condition', {}).get('StringEquals', {})
    return (trust.get('Version') == '1' and set(trust) == {'Version','Statement'}
        and statement.get('Effect') == 'Allow'
        and values(statement.get('Action')) == ['sts:AssumeRole']
        and set(statement.get('Principal',{})) == {'Federated'}
        and values(statement['Principal']['Federated']) == [constraints['provider_id']]
        and set(statement.get('Condition',{})) == {'StringEquals'}
        and set(conditions) == {'oidc:iss','oidc:aud'}
        and values(conditions['oidc:iss']) == [constraints['issuer']]
        and values(conditions['oidc:aud']) == [constraints['audience']]
        and set(statement) == {'Effect','Action','Principal','Condition'})


def audience_repair(trust, constraints, approved_before):
    """Return the exact audience-only repair, refusing all other drift."""
    trust = document(trust)
    if canonical(trust) != canonical(document(approved_before)):
        raise OperationError('GetRole', 'RepairPlanDrift')
    fixed = json.loads(json.dumps(trust))
    try:
        equals = fixed['Statement'][0]['Condition']['StringEquals']
        old = equals['oidc:aud']
        equals['oidc:aud'] = ([constraints['audience']] if isinstance(old, list)
                              else constraints['audience'])
    except (KeyError, IndexError, TypeError):
        raise OperationError('GetRole', 'UnsupportedTrustRepair') from None
    if not trust_matches(fixed, constraints):
        raise OperationError('GetRole', 'UnsupportedTrustRepair')
    return fixed


def verify_identity(executor, domain, expected_owner, error_code='WrongAccount'):
    """Emit verified identity evidence only after the actual STS response matches."""
    body = executor.call(domain, 'GetCallerIdentity')
    if body.get('AccountId') != expected_owner:
        raise OperationError('GetCallerIdentity', error_code, body.get('RequestId'))
    profile_key = 'eiam_profile' if domain == 'sts_eiam' else 'cloud_profile'
    event = {'event': 'identity_verified', 'profile': executor.plan.get(profile_key),
        'AccountId': body['AccountId'], 'RequestId': body.get('RequestId')}
    if hasattr(executor, 'audit'):
        event['command_index'] = len(executor.audit['commands'])
        executor.audit.setdefault('identity_checks', []).append(event)
        executor.flush_audit()
    print(json.dumps(event), flush=True)
    return body


def checked_read_command(plan, argv):
    """Allow an explicit official read argv only when it matches the exact scope.

    This keeps an audited subprocess visible at a calling tool boundary without
    an extra probe or replay. It is not an arbitrary command execution interface.
    """
    if argv is None:
        return None
    if not isinstance(argv, list) or len(argv) < 3 or argv[0] != 'aliyun':
        raise ValueError('Explicit read must use the official CLI')
    if argv[1:3] == ['ram', 'get-role']:
        expected = ['aliyun', 'ram', 'get-role', '--role-name', plan['role_name'],
                    '--profile', plan['cloud_profile']]
        if argv != expected:
            raise ValueError('Explicit role read differs from the checked target/profile')
        return list(argv)
    if argv[1] != 'eiam':
        raise ValueError('Unsupported read service')
    operation = argv[2]
    if operation not in ('get-instance', 'get-cloud-account'):
        raise ValueError('Only initial read operations are supported')
    expected = ['aliyun', 'eiam', operation, '--instance-id', plan['instance_id']]
    if operation == 'get-cloud-account':
        expected += ['--cloud-account-id', plan['cloud_account_id']]
    expected += ['--profile', plan['eiam_profile']]
    if argv != expected:
        raise ValueError('Explicit read command differs from the checked target/profile')
    return list(argv)


def write_completion(result, output):
    """Persist the actual verified result and derive its UTC timestamp once."""
    if result.get('status') != 'configuration_verified' or result.get('assigned_to_users') is not False:
        raise ValueError('Only an explicitly verified, unassigned result can be completed')
    timestamp = result['health']['LastCheckTime']
    if type(timestamp) is not int or timestamp <= 0:
        raise ValueError('Actual health timestamp required')
    result = dict(result)
    result['health_timestamp_utc'] = datetime.fromtimestamp(
        timestamp / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    target = Path(output).resolve() / 'verified-result.json'
    result['completion_summary'] = (
        'Configuration verified.\n'
        f'EIAM role: {result["cloud_account_role_id"]}; RAM role ARN: {result["role_arn"]}\n'
        f'Policy: {result["policy_name"]}; policy version: {result["policy_version"]}\n'
        f'Fresh health timestamp (epoch ms): {timestamp}; UTC: {result["health_timestamp_utc"]}\n'
        'Assigned to users/groups: false (this workflow performs no assignment).\n'
        'Effective user access was not tested.\n'
        f'Evidence: {target}')
    with target.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    return result


class Executor:
    def __init__(self, plan, output, session, audit_file=None, page_size=100, read_command=None):
        self.plan, self.output = plan, Path(output)
        self.read_command = checked_read_command(plan, read_command)
        self.output.mkdir(parents=True, exist_ok=True)
        self.cli = shutil.which('aliyun')
        if not self.cli:
            raise ValueError('Alibaba CLI missing')
        self.env = dict(os.environ)
        self.env['ALIBABA_CLOUD_USER_AGENT'] = user_agent(session)
        self.sequence = 0
        self.deadline = time.monotonic() + 600
        if not 1 <= page_size <= 100:
            raise ValueError('Page size outside API bounds')
        self.page_size = page_size
        self.audit_file = Path(audit_file) if audit_file else self.output / 'role-command-audit.json'
        self.audit = {'commands': [], 'session_id': session}
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_file.open('x', encoding='utf-8') as handle:
            json.dump(self.audit, handle)

    def call(self, domain, action, params=None, absent=None):
        # Only an explicit transient failure of a read can be retried. Writes,
        # malformed replies, timeouts and authorization/parameter errors stop.
        read = (re.match(r'^(get|list)(?:-|[A-Z])', action, re.I) is not None
                and not hasattr(self, 'operation_deadline'))
        for attempt in range(3):
            try:
                return self.call_once(domain, action, params, absent)
            except OperationError as exc:
                transient = exc.code in ('Throttling', 'Throttling.User', 'Throttling.Api',
                    'InternalError', 'InternalFailure', 'ServiceUnavailable')
                if not read or not transient or attempt == 2:
                    raise
                remaining = min(self.deadline, getattr(self, 'operation_deadline', self.deadline)) - time.monotonic()
                if remaining <= 0:
                    raise
                delay = min(2 ** attempt, remaining)
                event = {'event': 'read_retry_scheduled', 'action_after_error': 'retry',
                    'service': domain, 'operation': action, 'params': dict(params or {}),
                    'profile': self.plan['eiam_profile' if domain in ('eiam', 'sts_eiam') else 'cloud_profile'],
                    'error_code': exc.code, 'RequestId': exc.request_id,
                    'failed_attempt': attempt + 1, 'next_attempt': attempt + 2,
                    'max_attempts': 3, 'backoff_seconds': delay,
                    'monotonic': time.monotonic()}
                if hasattr(self, 'audit'):
                    self.audit.setdefault('recovery_events', []).append(event)
                    self.flush_audit()
                print(json.dumps(event), flush=True)
                time.sleep(delay)

    def call_once(self, domain, action, params=None, absent=None):
        deadline = min(self.deadline, getattr(self, 'operation_deadline', self.deadline))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OperationError(action, 'WorkflowDeadlineExceeded')
        profile = self.plan['eiam_profile' if domain in ('eiam','sts_eiam') else 'cloud_profile']
        product = 'sts' if domain.startswith('sts_') else domain
        def plugin_name(value):
            value = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', value)
            return re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', value).lower()
        argv = [self.cli, product, plugin_name(action)]
        for key,value in (params or {}).items():
            argv += ['--'+plugin_name(key), str(value)]
        argv += ['--profile', profile]
        explicit = getattr(self, 'read_command', None)
        if explicit and product == explicit[1] and argv[2] == explicit[2]:
            requested = [self.cli] + explicit[1:]
            if argv != requested:
                raise OperationError(action, 'ExplicitReadScopeDrift')
            argv = requested
        if product == 'eiam' and action in AUXILIARY:
            argv = auxiliary_command(self.cli, action, params or {}, profile)
        started = time.monotonic()
        try:
            response = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, encoding='utf-8', errors='replace', shell=False,
                timeout=min(45, remaining), env=self.env)
        except subprocess.TimeoutExpired:
            self.record_command(argv, started, -1, '', 'TimeoutStateUnknown', None)
            raise OperationError(action, 'TimeoutStateUnknown') from None
        if response.returncode:
            code, request_id = cli_error(response.stderr, response.stdout)
            self.record_command(argv, started, response.returncode, response.stdout, code, request_id,
                                stderr=response.stderr)
            error = OperationError(action, code, request_id)
            self.save(action, {'exit_code':response.returncode,'error_code':error.code,'RequestId':error.request_id})
            if absent and error.code == absent:
                return None
            raise error
        try:
            body = json.loads(response.stdout)
        except ValueError:
            self.record_command(argv, started, 0, response.stdout, 'InvalidJSONResponse', None)
            raise OperationError(action, 'InvalidJSONResponse') from None
        if not isinstance(body, dict):
            self.record_command(argv, started, 0, response.stdout, 'InvalidResponseShape', None)
            raise OperationError(action, 'InvalidResponseShape')
        self.record_command(argv, started, 0, response.stdout, None, body.get('RequestId'),
                            stderr=response.stderr)
        self.save(action, body)
        return body

    def record_command(self, argv, started, exit_code, stdout, code, request_id, stderr=''):
        if not hasattr(self, 'audit'):
            return  # Pure unit-test executors may replace all persistence.
        ended = time.monotonic()
        index = len(self.audit['commands']) + 1
        raw = self.output / f'command-{index:03}.json'
        with raw.open('x', encoding='utf-8') as handle:
            handle.write(stdout)
        raw_stderr = self.output / f'command-{index:03}.stderr.txt'
        with raw_stderr.open('x', encoding='utf-8') as handle:
            handle.write(stderr)
        self.audit['commands'].append({'argv': list(argv), 'start_monotonic': started,
            'end_monotonic': ended, 'exit_code': exit_code, 'error_code': code,
            'request_id': request_id, 'stdout_file': str(raw.resolve()),
            'stderr_file': str(raw_stderr.resolve())})
        self.flush_audit()
        # Observable real call/result, so an orchestrator need not infer API
        # execution from Python source or trust a final success assertion.
        event = {'command': shlex.join(argv), 'exit_code': exit_code,
                 'error_code': code, 'RequestId': request_id,
                 'stdout_file': str(raw.resolve()), 'stderr_file': str(raw_stderr.resolve()),
                 'stderr': stderr}
        if len(stdout) > 8192:
            # A role inventory can otherwise drown out earlier identity/provider
            # evidence in an orchestrator's bounded tool output. The complete
            # original response remains in stdout_file; a preview is never
            # represented as a complete API response.
            event.update(stdout_truncated=True, stdout_preview=stdout[:1024])
        else:
            event['stdout'] = stdout
        print(json.dumps(event), flush=True)

    def flush_audit(self):
        if hasattr(self, 'audit'):
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.audit_file.with_name(self.audit_file.name + '.tmp')
            temporary.write_text(json.dumps(self.audit, indent=2), encoding='utf-8')
            temporary.replace(self.audit_file)

    def save(self, label, response):
        self.sequence += 1
        file = self.output / f'{time.time_ns()}-{self.sequence:03}-{label}.json'
        with file.open('x',encoding='utf-8') as handle:
            json.dump(response,handle,ensure_ascii=False,indent=2)

    def eiam(self, action, **params):
        return self.call('eiam',action,{'instance-id':self.plan['instance_id'],
            'cloud-account-id':self.plan['cloud_account_id'],**params})

    def policies(self):
        # The RAM operation returns the complete attachment list and accepts
        # RoleName only. Do not send pagination flags belonging to other APIs.
        body=self.call('ram','ListPoliciesForRole',{'RoleName':self.plan['role_name']})
        if body.get('IsTruncated') or body.get('NextToken') or body.get('Marker'):
            raise OperationError('ListPoliciesForRole','UnsupportedPagination')
        return body.get('Policies',{}).get('Policy',[])

    def roles(self):
        roles=[]; token=None; seen=set()
        # The per-call and overall workflow deadlines still bound all work.
        # Explicit one-item pagination must not silently stop at 100 roles.
        for _ in range(1000):
            params={'max-results':getattr(self, 'page_size', 100)}
            if token:params['next-token']=token
            body=self.eiam('list-cloud-account-roles',**params)
            roles += body.get('CloudAccountRoles',[])
            token=body.get('NextToken')
            if not token:
                if body.get('TotalCount',len(roles)) > len(roles):
                    raise OperationError('ListCloudAccountRoles','PaginationIncomplete')
                if hasattr(self, 'audit'):
                    self.audit['pagination'] = {'exhausted': True, 'pages': len(seen) + 1,
                        'tokens_unique': True}
                    self.flush_audit()
                return roles
            if token in seen:break
            seen.add(token)
        raise OperationError('ListCloudAccountRoles','PaginationIncomplete')

    def run(self, artifact, verify_only=False, discover_only=False):
        p=self.plan
        self.original_artifact = artifact
        if p['vendor']!='alibaba_cloud' or p['mode'] not in ('create','reuse','register','repair'):
            raise ValueError('This helper supports approved Alibaba USER role operations only')
        if len(p['business_policies'])!=1 or p['business_policies'][0]['kind']!='custom':
            raise ValueError('One dedicated custom policy is required by this helper')
        policy=p['business_policies'][0]; name=p['role_name']; constraints=p['trust_constraints']
        for domain, expected in [('sts_eiam',p['eiam_owner_id']),('sts_cloud',p['account_id'])]:
            verify_identity(self, domain, expected)
        instance = self.call('eiam', 'GetInstance', {'InstanceId': p['instance_id']}).get('Instance', {})
        if instance.get('InstanceId') != p['instance_id']:
            raise OperationError('GetInstance', 'InstanceMismatch')
        account=self.eiam('get-cloud-account').get('CloudAccount',{})
        if (account.get('CloudAccountExternalId')!=p['account_id']
            or account.get('CloudAccountVendorType')!='alibaba_cloud'
            or account.get('CloudAccountHealth')!='healthy'):
            raise OperationError('GetCloudAccount','AccountMismatchOrUnhealthy')
        provider = self.call('ims', 'GetOIDCProvider', {
            'OIDCProviderName': constraints['provider_id'].split('/')[-1],
            'endpoint': 'ims.aliyuncs.com', 'region': 'cn-hangzhou'}).get('OIDCProvider', {})
        clients = provider.get('ClientIds', [])
        if isinstance(clients, dict):
            clients = clients.get('ClientId', [])
        if isinstance(clients, str):
            clients = [value.strip() for value in clients.split(',')]
        if (provider.get('Arn') != constraints['provider_id']
            or provider.get('IssuerUrl') != constraints['issuer']
            or not isinstance(clients, list) or constraints['audience'] not in clients):
            raise OperationError('GetOIDCProvider', 'ProviderMismatch')
        roles=self.roles()
        systems=[r for r in roles if r.get('CloudAccountRoleUsageType')=='system']
        if not systems or any(r.get('CloudAccountRoleHealth')!='healthy' for r in systems):
            raise OperationError('ListCloudAccountRoles','SystemRoleUnhealthy')
        matching=[r for r in roles if r.get('CloudAccountRoleName')==name]
        if len(matching)>1 or any(r.get('CloudAccountRoleUsageType')!='user' for r in matching):
            raise OperationError('ListCloudAccountRoles','RoleConflict')
        cloud=self.call('ram','GetRole',{'RoleName':name},absent='EntityNotExist.Role')
        cloud_existed = cloud is not None
        existing=self.call('ram','GetPolicy',{'PolicyName':policy['name'],'PolicyType':'Custom'},absent='EntityNotExist.Policy')
        discovered_policy_version = self.check_policy(existing,policy) if existing else None
        repair_trust = None
        if p['mode'] == 'register' and not cloud:
            raise OperationError('GetRole', 'RegistrationRequiresExistingRole')
        if p['mode'] == 'repair' and (not cloud or not matching):
            raise OperationError('GetRole', 'RepairRequiresExistingUserRole')
        if cloud:
            if p['mode'] == 'repair' and not trust_matches(cloud['Role'].get('AssumeRolePolicyDocument'), constraints):
                if verify_only or int(cloud['Role'].get('MaxSessionDuration', 0)) != constraints['max_session_duration']:
                    raise OperationError('GetRole', 'UnsupportedTrustRepair')
                repair_trust = audience_repair(cloud['Role']['AssumeRolePolicyDocument'], constraints,
                                               p.get('repair_before_trust', {}))
            else:
                self.check_cloud_role(cloud,constraints)
            attachments=self.policies()
            if any((v.get('PolicyName'),v.get('PolicyType'))!=(policy['name'],'Custom') for v in attachments):
                raise OperationError('ListPoliciesForRole','UnexpectedExistingPermissions')
        if discover_only:
            result = {'status': 'discovery_completed', 'role_name': name,
                'cloud_account_role_id': matching[0]['CloudAccountRoleId'] if matching else None,
                'role_arn': cloud['Role'].get('Arn') if cloud else None,
                'eiam_record_exists': bool(matching), 'ram_role_exists': cloud_existed,
                'policy_name': policy['name'], 'policy_version': discovered_policy_version,
                'trust_repair_required': repair_trust is not None,
                'plan_sha256': artifact['sha256'], 'client_token': artifact['client_token'],
                'user_approval_established': False, 'mutations_performed': False,
                'fresh_health_checked': False,
                'summary': 'Discovery only; no provisioning or health check performed. '
                           'Display the original plan and obtain actual approval before changes.'}
            self.save('discovery-result', result)
            return result
        if verify_only and (not matching or not cloud or not existing):
            raise OperationError('Verify','MissingExistingResources')
        self.recheck_plan(artifact, policy, discovered_policy_version, verify_only)
        if matching:
            role_id=matching[0]['CloudAccountRoleId']
        else:
            created=self.eiam('create-cloud-account-role',**{'cloud-account-role-name':name,
                'client-token':artifact['client_token'],'description':'User cloud role; approved regional ECS resource reads'})
            role_id=created.get('CloudAccountRoleId')
        if not isinstance(role_id,str) or not role_id.startswith('carole_'):
            raise OperationError('CreateCloudAccountRole','MissingRoleId')
        record=self.eiam('get-cloud-account-role',**{'cloud-account-role-id':role_id}).get('CloudAccountRole',{})
        if (record.get('CloudAccountRoleUsageType')!='user' or record.get('CloudAccountRoleName')!=name
            or record.get('CloudAccountId')!=p['cloud_account_id']):
            raise OperationError('GetCloudAccountRole','RoleOwnershipMismatch')
        config=self.eiam('get-cloud-account-role-config',**{'cloud-account-role-id':role_id})
        config=config.get('CloudAccountRoleConfig',{}).get('AlibabaCloudAccountRoleConfig',{})
        trust=config.get('TrustConfig',{})
        if (config.get('RoleName')!=name or not trust_matches(trust.get('AssumeRolePolicyDocument'),constraints)
            or int(trust.get('RoleSessionDuration',0))!=constraints['max_session_duration']):
            raise OperationError('GetCloudAccountRoleConfig','UnexpectedGeneratedTrust')
        if repair_trust is not None:
            self.call('ram', 'UpdateRole', {'RoleName':name,
                'NewAssumeRolePolicyDocument':json.dumps(repair_trust)})
        if not cloud:
            self.call('ram','CreateRole',{'RoleName':name,
                'AssumeRolePolicyDocument':json.dumps(document(trust['AssumeRolePolicyDocument'])),
                'MaxSessionDuration':constraints['max_session_duration']})
        if not existing:
            self.call('ram','CreatePolicy',{'PolicyName':policy['name'],
                'PolicyDocument':json.dumps(policy['document']),
                'Description':'Approved Hangzhou ECS resource metadata read-only policy'})
        attachments=self.policies()
        if not any(v.get('PolicyName')==policy['name'] and v.get('PolicyType')=='Custom' for v in attachments):
            if verify_only:raise OperationError('Verify','MissingPolicyAttachment')
            self.call('ram','AttachPolicyToRole',{'RoleName':name,'PolicyName':policy['name'],'PolicyType':'Custom'})
        self.check_health(role_id)
        health=self.last_health
        cloud=self.call('ram','GetRole',{'RoleName':name});self.check_cloud_role(cloud,constraints)
        policy_version=self.check_policy(self.call('ram','GetPolicy',{'PolicyName':policy['name'],'PolicyType':'Custom'}),policy)
        attachments=self.policies()
        if len(attachments)!=1 or (attachments[0].get('PolicyName'),attachments[0].get('PolicyType'))!=(policy['name'],'Custom'):
            raise OperationError('ListPoliciesForRole','UnexpectedFinalPermissions')
        result={'status':'configuration_verified','instance_id':p['instance_id'],
            'cloud_account_id':p['cloud_account_id'],'cloud_account_role_id':role_id,
            'role_arn':cloud['Role']['Arn'],'role_name':name,'health':health,
            'policy_name':policy['name'],'policy_version':policy_version,
            'max_session_duration':cloud['Role']['MaxSessionDuration'],
            'eiam_record_created':not bool(matching),'ram_role_created':not cloud_existed,
            'eiam_create_time':record.get('CreateTime'),
            'ram_create_date':cloud['Role'].get('CreateDate'),
            'plan_sha256':artifact['sha256'],'assigned_to_users':False,
            'effective_user_access_tested':False,'verification_mode':verify_only}
        result = write_completion(result, self.output)
        self.save('verified-result',result)
        return result

    def recheck_plan(self, artifact, policy, discovered_version, verify_only):
        """Revalidate the approved scope immediately before writes or health checks."""
        checked = check(artifact, artifact['sha256'])
        if canonical(checked['plan']) != canonical(self.plan):
            raise OperationError('PlanCheck', 'ExecutionPlanDrift')
        if hasattr(self, 'original_plan_file'):
            argv = [sys.executable, str(Path(__file__).with_name('role_tools.py')),
                    'check', '--input', self.original_plan_file,
                    '--approved-sha256', checked['sha256']]
            try:
                result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                    text=True, encoding='utf-8', errors='replace', shell=False, timeout=15)
            except subprocess.TimeoutExpired:
                raise OperationError('PlanCheck', 'LocalPlanCheckTimeout') from None
            print(json.dumps({'command': shlex.join(argv), 'exit_code': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}), flush=True)
            if result.returncode:
                raise OperationError('PlanCheck', 'OriginalPlanFileDrift')
        for domain, owner in [('sts_eiam', self.plan['eiam_owner_id']),
                              ('sts_cloud', self.plan['account_id'])]:
            verify_identity(self, domain, owner)
        current = self.call('ram', 'GetPolicy',
            {'PolicyName': policy['name'], 'PolicyType': 'Custom'},
            absent='EntityNotExist.Policy')
        version = self.check_policy(current, policy) if current else None
        if version != discovered_version:
            raise OperationError('GetPolicy', 'PolicyVersionDrift')
        event = {'event': 'plan_rechecked', 'plan_sha256': checked['sha256'],
            'client_token': checked['client_token'], 'policy_name': policy['name'],
            'policy_version': version, 'verification_mode': verify_only,
            'eiam_owner_id': self.plan['eiam_owner_id'], 'account_id': self.plan['account_id']}
        if hasattr(self, 'audit'):
            event['command_index'] = len(self.audit['commands'])
            self.audit['original_plan_artifact'] = checked
            self.audit.setdefault('plan_checks', []).append(event)
            self.flush_audit()
        print(json.dumps(event), flush=True)

    def check_health(self, role_id):
        started = int(time.time()*1000)
        monotonic_started = time.monotonic()
        if hasattr(self, 'audit'):
            self.audit['health'] = {'status': 'incomplete', 'polls': 0,
                'started_ms': started, 'started_monotonic': monotonic_started}
            self.flush_audit()
        if hasattr(self, 'original_artifact') and hasattr(self, 'output'):
            with (self.output/'role-eval-plan.json').open('x',encoding='utf-8') as handle:
                json.dump({'health_check_start_ms':started,
                    'plan_sha256':self.original_artifact['sha256'],
                    'sealed_plan':self.original_artifact},handle,indent=2)
        deadline = min(self.deadline, monotonic_started+60)
        self.operation_deadline = deadline
        try:
            self.eiam('check-cloud-account-role-config', **{'cloud-account-role-id':role_id})
            self.poll_health(role_id, started, deadline=deadline)
        finally:
            if hasattr(self, 'audit'):
                self.audit['health']['elapsed_seconds'] = time.monotonic() - monotonic_started
                self.flush_audit()
            if hasattr(self, 'operation_deadline'):
                del self.operation_deadline

    def poll_health(self, role_id, started, deadline=None):
        """At most six reads, including CLI latency, within sixty seconds."""
        deadline = min(self.deadline, deadline if deadline is not None else time.monotonic()+60)
        self.operation_deadline = deadline
        try:
            for attempt in range(6):
                if time.monotonic() >= deadline:
                    break
                record = self.eiam('get-cloud-account-role',
                    **{'cloud-account-role-id': role_id})['CloudAccountRole']
                if hasattr(self, 'audit'):
                    self.audit['health']['polls'] += 1
                health = record.get('CloudAccountRoleHealthCheckResult', {})
                if (record.get('CloudAccountRoleHealth') == 'healthy'
                    and health.get('Result') == 'success'
                    and health.get('LastCheckTime', 0) >= started):
                    self.last_health = health
                    if hasattr(self, 'audit'):
                        self.audit['health']['status'] = 'confirmed'
                    return
                remaining = deadline - time.monotonic()
                if attempt < 5 and remaining > 0:
                    time.sleep(min(5, remaining))
        finally:
            del self.operation_deadline
        raise OperationError('CheckCloudAccountRoleConfig', 'FreshHealthNotEstablished')

    def check_policy(self, existing, policy):
        version=existing['Policy']['DefaultVersion']
        if policy.get('version') is not None and policy['version'] != version:
            raise OperationError('GetPolicy', 'PolicyVersionDrift')
        value=self.call('ram','GetPolicyVersion',{'PolicyName':policy['name'],'PolicyType':'Custom','VersionId':version})
        if canonical(document(value['PolicyVersion']['PolicyDocument']))!=canonical(policy['document']):
            raise OperationError('GetPolicyVersion','PolicyConflict')
        return version

    def check_cloud_role(self, cloud, constraints):
        role=cloud['Role']
        if (not trust_matches(role.get('AssumeRolePolicyDocument'),constraints)
            or int(role.get('MaxSessionDuration',0))!=constraints['max_session_duration']):
            raise OperationError('GetRole','ExistingRoleTrustConflict')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-file',required=True)
    parser.add_argument('--approved-sha256',required=True)
    parser.add_argument('--session-id',required=True)
    parser.add_argument('--evidence-dir',required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify-only',action='store_true')
    mode.add_argument('--discover-only',action='store_true',
        help='Read current identity, instance, provider, roles and policies; no writes or health checks')
    parser.add_argument('--audit-file')
    parser.add_argument('--page-size',type=int,default=100)
    parser.add_argument('--read-command', nargs=argparse.REMAINDER,
        help='Optional exact official initial account or target-role read argv, executed by this audited runner')
    args=parser.parse_args()
    try:
        try:
            original = load(args.plan_file)
        except OSError:
            print(json.dumps({'status':'missing_original_plan',
                'cloud_calls_performed':False, 'automatic_rollback':False,
                'next_step':'Recover the original sealed artifact; do not discover substitutes or reseal'}))
            return 2
        artifact=check(original,args.approved_sha256)
        if args.read_command and args.read_command[1:3] not in (
                ['eiam', 'get-cloud-account'], ['ram', 'get-role']):
            raise ValueError('Role lifecycle accepts only its initial account or target-role read')
        checked_read_command(artifact['plan'], args.read_command)
        from role_environment import inspect
        environment = inspect('alibaba_cloud', scope=('planning' if args.discover_only else 'verification' if args.verify_only else 'setup'))
        if environment['status'] != 'cli_capabilities_available':
            print(json.dumps(environment))
            return 2
        executor=Executor(artifact['plan'],args.evidence_dir,args.session_id,
            args.audit_file,args.page_size,args.read_command)
        executor.original_plan_file = str(Path(args.plan_file).resolve())
        result=executor.run(artifact,args.verify_only,args.discover_only)
        print(json.dumps(result));return 0
    except OperationError as exc:
        print(json.dumps({'status':'blocked_or_partial','failed_action':exc.action,
            'error_code':exc.code,'RequestId':exc.request_id,
            'automatic_rollback':False,'next_step':'Read preserved evidence and exact targets before resume'}));return 2
    except (ValueError,KeyError,TypeError,OSError):
        print(json.dumps({'status':'invalid_plan_or_response','automatic_rollback':False}));return 2


if __name__=='__main__':
    sys.exit(main())
