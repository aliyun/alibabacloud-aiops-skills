#!/usr/bin/env python3
"""Confirmed conditional access policy changes with plan-hash binding.

plan:             local intent validation, read-only discovery, priority
                  allocation, then the exact plan file plus SHA256. No writes.
plan-delete /
plan-disable /
plan-enable:      bind target policies from the session's saved preflight result
                  (zero cloud calls); full snapshots travel in the plan for drift
                  checks. One apply of a delete plan runs disable -> readback ->
                  delete -> removal verification (shortest observation); the
                  observation gate can instead be split by applying plan-disable
                  first and plan-delete after user observation.
apply:            re-verified execution of exactly the approved plan only, dispatched
                  by plan operation. create: preflight re-check, policy creation with
                  stable ClientToken and timeout readback, enable-if-disabled, and
                  per-field readback verify. delete/disable/enable: policies-only
                  re-check (one List call, no zones, no capability probe), switch,
                  status readback, then delete and removal verification.
Network zones are discovered and referenced by ID only; this helper never
creates, updates, or deletes them (they are shared instance-level resources
managed outside this skill).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import ca_preflight as preflight

MFA_METHODS = {'ia_otp_sms', 'ia_otp_email', 'ia_totp', 'ia_webauthn'}
POLICY_TYPE_SYSTEM = 'arn:alibaba:idaas:authn:access:policy:system'
DECISION_TYPE_ENFORCEMENT = 'enforcement'
EVALUATE_AT_AFTER_STEP1 = 'arn:alibaba:idaas:authn:access:rule:eval_at:after_step1'
ID_RULES = {
    'user_': 'user_[A-Za-z0-9_.@-]+',
    'group_': 'group_[A-Za-z0-9_.@-]+',
    'ou_': 'ou_[A-Za-z0-9_.@-]+',
    'app_': 'app_[A-Za-z0-9_.@-]+',
    'network_': 'network_[A-Za-z0-9_.@-]+',
}
PORTAL_APP_ID = 'iap_user_portal'
MFA_INTERVAL_FIXED = 300
STATE_OPERATIONS = ('delete', 'disable', 'enable')
STATE_PLAN_MODES = {'plan-delete': 'delete', 'plan-disable': 'disable',
                    'plan-enable': 'enable'}
PREFLIGHT_BINDABLE_STATUSES = ('ready', 'quota_exceeded', 'entity_missing',
                               'entity_not_configurable')
CREATE_WRITE_ACTIONS = ('CreateConditionalAccessPolicy', 'EnableConditionalAccessPolicy',
                        'GetConditionalAccessPolicy')
STATE_WRITE_ACTIONS = {
    'delete': ('DisableConditionalAccessPolicy', 'DeleteConditionalAccessPolicy',
               'GetConditionalAccessPolicy'),
    'disable': ('DisableConditionalAccessPolicy', 'GetConditionalAccessPolicy'),
    'enable': ('EnableConditionalAccessPolicy', 'GetConditionalAccessPolicy'),
}


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def covers(requested, actual):
    """True when every non-empty requested field is present and equal in the
    actual readback. The server synthesizes defaults for unspecified fields
    (observed live: MfaAuthenticationIntervalSeconds=300,
    ActiveSessionReuseStatus='disabled'), so strict equality would reject a
    correctly created policy; a wrong requested value still fails."""
    if isinstance(requested, dict):
        for key, value in requested.items():
            if value is None or value == '' or value == {} or value == []:
                continue
            if not isinstance(actual, dict) or not covers(value, actual.get(key)):
                return False
        return True
    if isinstance(requested, list):
        return isinstance(actual, list) and requested == actual
    return requested == actual


def normalize_decision(decision):
    """Live instances return capitalized enums ('Allow'/'Deny'); the public docs
    specify lowercase. Normalize to lowercase for validation, planning, and readback
    comparison regardless of which side the value came from."""
    result = dict(decision or {})
    for key in ('Effect', 'MfaType', 'ActiveSessionReuseStatus'):
        if isinstance(result.get(key), str):
            result[key] = result[key].lower()
    return result


def blocked(reason, evidence, **extra):
    result = {'schema_version': 1, 'status': 'blocked', 'reason': reason,
              'evidence': evidence,
              'recovery': 'read back current state; resume the same approved plan; '
                          'do not auto-rollback or delete completed records'}
    result.update(extra)
    print(json.dumps(result, indent=2, default=str))
    return 2


def collect_refs(policies):
    app_ids, zone_refs = set(), set()
    for policy in policies:
        conditions = policy.get('ConditionsConfig') or {}
        applications = conditions.get('Applications') or {}
        zones = conditions.get('NetworkZones') or {}
        for key in ('IncludeApplications', 'ExcludeApplications'):
            app_ids.update(applications.get(key) or [])
        for key in ('IncludeNetworkZones', 'ExcludeNetworkZones'):
            zone_refs.update(zones.get(key) or [])
    return sorted(app_ids), sorted(zone_refs)


def discovery_app_ids(policies):
    # The portal is the sole configurable system app; the default user_custom
    # listing filters system apps out, so validating the fixed portal ID
    # there would produce a false entity_missing.
    app_ids, _ = collect_refs(policies)
    return [app_id for app_id in app_ids if app_id != PORTAL_APP_ID]


def id_format_errors(scope, values):
    errors = []
    for value in values:
        if not isinstance(value, str):
            errors.append(f'{scope}: ID must be a string: {value!r}')
            continue
        if value == PORTAL_APP_ID:
            continue
        if value.startswith('iap_'):
            errors.append(f'{scope}: system application, not configurable '
                          f'(the portal {PORTAL_APP_ID} is the only configurable '
                          f'system app): {value}')
            continue
        for prefix, pattern in ID_RULES.items():
            if value.startswith(prefix):
                if not re.fullmatch(pattern, value):
                    errors.append(f'{scope}: invalid ID format: {value}')
                break
        else:
            errors.append(f'{scope}: unknown ID prefix: {value}')
    return errors


def validate_policy_syntax(policy, index):
    errors = []
    name = policy.get('ConditionalAccessPolicyName')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64:
        errors.append(f'policies[{index}].ConditionalAccessPolicyName: 1-64 chars required')
    priority = policy.get('Priority')
    if priority is not None and (not isinstance(priority, int)
                                 or not preflight.CUSTOM_PRIORITY_MIN <= priority
                                 <= preflight.CUSTOM_PRIORITY_MAX):
        errors.append(f'policies[{index}].Priority: expect null or 1-100')
    decision = normalize_decision(policy.get('DecisionConfig'))
    effect = decision.get('Effect')
    if effect not in ('allow', 'deny'):
        errors.append(f'policies[{index}].DecisionConfig.Effect: expect allow or deny')
    if effect == 'allow':
        mfa_type = decision.get('MfaType')
        if mfa_type not in ('directly_access', 'mfa_required'):
            errors.append(f'policies[{index}].DecisionConfig.MfaType: expect '
                          f'directly_access or mfa_required')
        if mfa_type == 'mfa_required':
            methods = decision.get('MfaAuthenticationMethods') or []
            if not methods or not set(methods) <= MFA_METHODS:
                errors.append(f'policies[{index}].DecisionConfig.MfaAuthenticationMethods: '
                              f'require non-empty subset of {sorted(MFA_METHODS)}')
        interval = decision.get('MfaAuthenticationIntervalSeconds')
        if interval is not None and interval != MFA_INTERVAL_FIXED:
            errors.append(f'policies[{index}].DecisionConfig.MfaAuthenticationIntervalSeconds: '
                          f'fixed to {MFA_INTERVAL_FIXED} by this skill; omit the field or '
                          f'set {MFA_INTERVAL_FIXED}')
        reuse = decision.get('ActiveSessionReuseStatus')
        if reuse is not None and reuse not in ('enabled', 'disabled'):
            errors.append(f'policies[{index}].DecisionConfig.ActiveSessionReuseStatus: '
                          f'expect enabled or disabled')
    conditions = policy.get('ConditionsConfig') or {}
    users = conditions.get('Users') or {}
    for key in ('IncludeUsers', 'ExcludeUsers'):
        errors.extend(id_format_errors(f'policies[{index}].Users.{key}', users.get(key) or []))
    for key in ('IncludeGroups', 'ExcludeGroups'):
        errors.extend(id_format_errors(f'policies[{index}].Users.{key}', users.get(key) or []))
    for key in ('IncludeOrganizationalUnits', 'ExcludeOrganizationalUnits'):
        errors.extend(id_format_errors(f'policies[{index}].Users.{key}',
                                       users.get(key) or []))
    applications = conditions.get('Applications') or {}
    for key in ('IncludeApplications', 'ExcludeApplications'):
        errors.extend(id_format_errors(f'policies[{index}].Applications.{key}',
                                       applications.get(key) or []))
    zones = conditions.get('NetworkZones') or {}
    for key in ('IncludeNetworkZones', 'ExcludeNetworkZones'):
        errors.extend(id_format_errors(f'policies[{index}].NetworkZones.{key}',
                                       zones.get(key) or []))
    return errors


def validate_intent(intent):
    """Local-only syntax validation; runs before any cloud call."""
    errors = []
    if intent.get('schema_version') != 1:
        errors.append('intent: schema_version must be 1')
    if 'network_zones' in intent:
        errors.append('intent: network_zones is not supported; this skill manages '
                      'conditional access policies only—reference existing network '
                      'zone IDs in policies and create/update/delete zones outside '
                      'this skill')
    policies = intent.get('policies')
    if not isinstance(policies, list) or not policies:
        errors.append('intent: policies must be a non-empty list')
        policies = []
    for index, policy in enumerate(policies):
        errors.extend(validate_policy_syntax(policy, index))
    names = [p.get('ConditionalAccessPolicyName') for p in policies]
    if len(names) != len(set(names)):
        errors.append('intent: duplicate policy names')
    return errors


def run_discovery(instance_id, profile, app_ids, evidence):
    argv = [sys.executable, str(Path(__file__).with_name('ca_preflight.py')),
            '--instance-id', instance_id, '--eiam-profile', profile]
    for app_id in app_ids:
        argv.extend(['--app-id', app_id])
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        evidence.append({'product': 'local', 'action': 'ca_preflight', 'error': 'timeout'})
        return {'status': 'discovery_incomplete'}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {'status': 'discovery_incomplete',
                'stderr_tail': (proc.stderr or '')[-preflight.STDERR_TAIL:]}


def require_write_commands(actions=CREATE_WRITE_ACTIONS):
    for action in actions:
        argv = ['aliyun', 'eiam', action, '--help']
        try:
            proc = preflight.run(argv, timeout=20)
        except subprocess.TimeoutExpired as exc:
            raise preflight.CommandError(argv, 'local command capability check timed out',
                                         error_type='environment') from exc
        stdout = preflight._strip_ansi(proc.stdout)
        if proc.returncode or action not in stdout or '--InstanceId' not in stdout:
            raise preflight.CommandError(
                argv, 'installed EIAM CLI does not provide the required write command',
                error_type='environment')


SDK_ENDPOINT = 'eiam.cn-hangzhou.aliyuncs.com'


def sdk_call(credential, action, endpoint, version, query, evidence):
    """SDK transport for EIAM writes with object parameters. Verified live: the
    aliyun CLI cannot send DecisionConfig/ConditionsConfig (JSON strings are
    rejected with 'Flat format is required'; dot-path flags are rejected by the
    CLI), while OpenApiUtil.query produces exactly the console-captured flat
    form 'DecisionConfig.Effect=Allow' / 'MfaAuthenticationMethods.1'."""
    try:
        from alibabacloud_openapi_util.client import Client as OpenApiUtil
        from alibabacloud_tea_openapi.client import Client
        from alibabacloud_tea_openapi import models as api
        from alibabacloud_tea_util import models as util
        client = Client(api.Config(credential=credential, endpoint=endpoint,
                                   user_agent=preflight.user_agent(),
                                   connect_timeout=5000, read_timeout=15000))
        params = api.Params(action=action, version=version, protocol='HTTPS',
                            method='POST', auth_type='AK', style='RPC', pathname='/',
                            req_body_type='formData', body_type='json')
        result = client.call_api(params,
                                 api.OpenApiRequest(query=OpenApiUtil.query(query)),
                                 util.RuntimeOptions(autoretry=False, max_attempts=1,
                                                     connect_timeout=5000,
                                                     read_timeout=15000))
        body = result.get('body') or {}
        evidence.append({'product': 'sts' if endpoint.startswith('sts') else 'eiam',
                         'action': action, 'transport': 'sdk',
                         'RequestId': body.get('RequestId')})
        return body
    except Exception as exc:
        # SDK exception messages can embed request headers; only surfaced fields below.
        if isinstance(exc, ImportError):
            raise preflight.CommandError(['sdk', action],
                                         'SDK transport dependencies are not installed '
                                         '(alibabacloud-tea-openapi, alibabacloud-credentials, '
                                         'alibabacloud-tea-util, alibabacloud-openapi-util)',
                                         error_type='environment') from exc
        data = getattr(exc, 'data', None)
        data = data if isinstance(data, dict) else {}
        code = data.get('Code') or data.get('code') or getattr(exc, 'code', '')
        request_id = data.get('RequestId') or data.get('requestId') or ''
        if 'Timeout' in type(exc).__name__:
            error_type = 'timeout'
        elif isinstance(code, str) and any(marker in code for marker in preflight.AUTH_MARKERS):
            error_type = 'auth'
        else:
            error_type = 'cloud'
        raise preflight.CommandError(['sdk', action],
                                     f'{action} failed via SDK transport '
                                     f'({code or type(exc).__name__})',
                                     error_type=error_type, request_id=request_id) from exc


def cli_caller_identity(profile, evidence):
    data = preflight.run_json(['aliyun', 'sts', 'GetCallerIdentity', '--profile', profile])
    account = data.get('AccountId')
    if not account:
        raise preflight.CommandError(['aliyun', 'sts', 'GetCallerIdentity'],
                                     'GetCallerIdentity returned no AccountId',
                                     error_type='auth')
    evidence.append({'product': 'sts', 'action': 'GetCallerIdentity',
                     'transport': 'cli', 'AccountId': account})
    return account


def write_credential(profile, evidence):
    """Resolve and identity-bind the SDK write transport before any write."""
    try:
        from alibabacloud_credentials.client import Client as Credentials
        credential = Credentials()
    except Exception as exc:
        raise preflight.CommandError(['sdk', 'credentials'],
                                     f'SDK credential chain unavailable: {type(exc).__name__}',
                                     error_type='environment') from exc
    sdk_account = sdk_call(credential, 'GetCallerIdentity', 'sts.cn-hangzhou.aliyuncs.com',
                           '2015-04-01', {}, evidence).get('AccountId')
    cli_account = cli_caller_identity(profile, evidence)
    if sdk_account != cli_account:
        raise preflight.CommandError(
            ['sdk', 'GetCallerIdentity'],
            f'SDK transport account {sdk_account} differs from CLI profile account '
            f'{cli_account}; writes require the same identity',
            error_type='auth')
    return credential


def wire_decision(decision):
    """Console-captured wire format: Effect is capitalized ('Allow'/'Deny');
    MfaType and ActiveSessionReuseStatus stay lowercase. Readback compares both
    sides through normalize_decision, so casing never affects verification."""
    result = dict(decision or {})
    if result.get('Effect') in ('allow', 'deny'):
        result['Effect'] = result['Effect'].capitalize()
    return result


def cmd_plan(args):
    evidence = []
    try:
        intent = json.loads(Path(args.intent_file).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        return blocked(f'intent file unreadable: {error}', evidence)
    errors = validate_intent(intent)
    if errors:
        return blocked('intent syntax invalid: ' + '; '.join(errors), evidence)
    if not args.instance_id or not args.eiam_profile:
        return blocked('plan requires --instance-id and --eiam-profile', evidence)

    app_ids = discovery_app_ids(intent['policies'])
    discovery = run_discovery(args.instance_id, args.eiam_profile, app_ids, evidence)
    if discovery.get('referenced_apps_not_configurable'):
        return blocked(f'referenced applications are system apps and cannot be '
                       f'conditional access targets (the portal '
                       f'{PORTAL_APP_ID} is the only configurable system app): '
                       f'{discovery["referenced_apps_not_configurable"]}', evidence,
                       discovery=discovery)
    if discovery.get('status') != 'ready':
        return blocked(f'discovery blocks the plan: {discovery.get("status")}', evidence,
                       discovery=discovery)

    _, zone_refs = collect_refs(intent['policies'])
    existing_zone_ids = {z['zone_id'] for z in discovery.get('network_zones') or []}
    for ref in zone_refs:
        if ref not in existing_zone_ids:
            return blocked(f'referenced network zone not found: {ref}; this skill does not '
                           f'create zones—create it in the console (or another authorized '
                           f'path), then regenerate the plan', evidence)

    if discovery.get('referenced_apps_missing'):
        return blocked(f'referenced applications missing: '
                       f'{discovery["referenced_apps_missing"]}', evidence)

    custom_count = discovery['quota']['custom_policy_count']
    if custom_count + len(intent['policies']) > preflight.CUSTOM_POLICY_LIMIT:
        return blocked(f'quota: {custom_count} custom policies exist, creating '
                       f'{len(intent["policies"])} exceeds the limit of '
                       f'{preflight.CUSTOM_POLICY_LIMIT}', evidence)

    occupied = set(discovery.get('priorities_occupied') or [])
    free = [p for p in range(preflight.CUSTOM_PRIORITY_MIN,
                             preflight.CUSTOM_PRIORITY_MAX + 1) if p not in occupied]
    assigned, requested = [], []
    for policy in intent['policies']:
        priority = policy.get('Priority')
        if priority is None:
            if not free:
                return blocked('no free priority in 1-100', evidence)
            priority = free.pop(0)
        elif priority in occupied:
            return blocked(f'priority {priority} is occupied by an existing policy', evidence)
        assigned.append(priority)
        requested.append(priority)
    if len(requested) != len(set(requested)):
        return blocked('duplicate priorities inside the intent', evidence)

    plan_policies = []
    for policy, priority in zip(intent['policies'], assigned):
        decision = normalize_decision(policy.get('DecisionConfig'))
        if decision.get('Effect') == 'allow' and decision.get('MfaType') == 'mfa_required':
            decision['MfaAuthenticationIntervalSeconds'] = MFA_INTERVAL_FIXED
        plan_policies.append({
            'ConditionalAccessPolicyName': policy['ConditionalAccessPolicyName'],
            'Description': policy.get('Description'),
            'Priority': priority,
            'DecisionConfig': decision,
            'ConditionsConfig': policy.get('ConditionsConfig') or {},
            'ClientToken': uuid.uuid4().hex,
        })

    simulation = None
    if args.sim_user and args.sim_app:
        try:
            raw = preflight.paginate_tokens(args.eiam_profile, 'ListConditionalAccessPolicies',
                                            'ConditionalAccessPolicies', evidence, args.instance_id)
        except preflight.CommandError as error:
            return blocked(f'hit-preview discovery failed: {error}', evidence,
                           **error.fields())
        zones_by_id = {z['zone_id']: {'NetworkZoneId': z['zone_id'],
                                      'NetworkZoneType': z['type'],
                                      'Ipv4Cidrs': z['ipv4_cidrs'],
                                      'Ipv6Cidrs': z['ipv6_cidrs']}
                       for z in discovery.get('network_zones') or []}
        planned_raw = [{'ConditionalAccessPolicyId': 'planned:' + p['ConditionalAccessPolicyName'],
                        'ConditionalAccessPolicyName': p['ConditionalAccessPolicyName'],
                        'Status': 'enabled', 'Priority': p['Priority'],
                        'DecisionConfig': p['DecisionConfig'],
                        'ConditionsConfig': p['ConditionsConfig']} for p in plan_policies]
        simulation = preflight.simulate(raw + planned_raw, zones_by_id,
                                        {'user': args.sim_user, 'groups': args.sim_group,
                                         'ous': args.sim_ou, 'app': args.sim_app,
                                         'ip': args.sim_ip})

    plan = {
        'schema_version': 1,
        'instance_id': args.instance_id,
        'eiam_profile': args.eiam_profile,
        'intent_name': intent.get('intent_name'),
        'preflight_status': discovery['status'],
        'policies': plan_policies,
        'actions': ['create_policies', 'enable_policies_if_disabled', 'readback_verify'],
        'hit_preview': simulation,
        'entity_checks': {'apps_validated': app_ids, 'zones_referenced': zone_refs},
    }
    path = Path(args.plan_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'schema_version': 1, 'status': 'awaiting_confirmation',
                      'plan': plan, 'plan_sha256': digest(plan),
                      'note': 'show the plan and hit_preview to the user; apply only '
                              'after one explicit confirmation of this exact plan'},
                     indent=2, default=str))
    return 0


def create_policy(credential, profile, instance_id, policy, evidence):
    # DecisionConfig/ConditionsConfig are object parameters: only the SDK transport
    # can serialize them (flat dot-path form). ConditionalAccessPolicyType is required
    # by the public schema; the documented enum only shows ':system'.
    query = dict(InstanceId=instance_id,
                 ConditionalAccessPolicyName=policy['ConditionalAccessPolicyName'],
                 ConditionalAccessPolicyType=POLICY_TYPE_SYSTEM,
                 DecisionType=DECISION_TYPE_ENFORCEMENT,
                 EvaluateAt=EVALUATE_AT_AFTER_STEP1,
                 Description=policy.get('Description'),
                 Priority=policy['Priority'],
                 DecisionConfig=wire_decision(policy.get('DecisionConfig') or {}),
                 ConditionsConfig=policy.get('ConditionsConfig') or {},
                 ClientToken=policy['ClientToken'])
    query = {key: value for key, value in query.items()
             if value not in (None, '', {}, [])}
    try:
        result = sdk_call(credential, 'CreateConditionalAccessPolicy', SDK_ENDPOINT,
                         '2021-12-01', query, evidence)
        return result['ConditionalAccessPolicyId'], 'created'
    except preflight.CommandError as error:
        if error.error_type != 'timeout':
            raise
        # A timeout does not prove failure; read back before one stable-token retry.
        policies = preflight.paginate_tokens(profile, 'ListConditionalAccessPolicies',
                                              'ConditionalAccessPolicies', evidence,
                                              instance_id)
        for existing in policies:
            if existing.get('ConditionalAccessPolicyName') == policy['ConditionalAccessPolicyName']:
                return existing['ConditionalAccessPolicyId'], 'recovered_after_timeout'
        result = sdk_call(credential, 'CreateConditionalAccessPolicy', SDK_ENDPOINT,
                         '2021-12-01', query, evidence)
        return result['ConditionalAccessPolicyId'], 'created'


def policy_signature(summary):
    """Drift identity of a policy. Status is deliberately excluded: state operations
    change status by design (a disable executed between binding and this apply is
    expected flow, and reruns skip already-switched policies); every other field must
    match exactly or the binding is stale."""
    result = dict(summary or {})
    result.pop('status', None)
    return result


def list_policy_summaries(profile, instance_id, evidence):
    """Policies-only discovery for state plans: one paginated List call, no network
    zones, no capability probe (the probe runs once before writes instead)."""
    raw = preflight.paginate_tokens(profile, 'ListConditionalAccessPolicies',
                                    'ConditionalAccessPolicies', evidence, instance_id)
    return [preflight.policy_summary(p) for p in raw]


def validate_state_plan(plan):
    problems = []
    if plan.get('operation') not in STATE_OPERATIONS:
        problems.append(f'operation must be one of {STATE_OPERATIONS}')
    if not isinstance(plan.get('bound_policies'), list) or not plan['bound_policies']:
        problems.append('bound_policies must be a non-empty list')
    for field in ('instance_id', 'eiam_profile'):
        if not plan.get(field):
            problems.append(f'{field} is required')
    for index, policy in enumerate(plan.get('bound_policies') or []):
        if not isinstance(policy, dict) or not policy.get('policy_id'):
            problems.append(f'bound_policies[{index}]: policy_id is required')
    return problems


def cmd_plan_state(args):
    """Bind targets from the session's saved preflight result; zero cloud calls."""
    evidence = []
    operation = STATE_PLAN_MODES[args.mode]
    if not args.eiam_profile:
        return blocked(f'{args.mode} requires --eiam-profile', evidence)
    if not args.preflight_file:
        return blocked(f'{args.mode} requires --preflight-file: the saved ca_preflight '
                       f'discovery result from this session (run ca_preflight.py first, '
                       f'save its stdout to a file)', evidence)
    try:
        discovery = json.loads(Path(args.preflight_file).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        return blocked(f'preflight file unreadable: {error}', evidence)
    if discovery.get('schema_version') != 1:
        return blocked('preflight file: schema_version must be 1', evidence)
    instance_id = discovery.get('instance_id')
    if not instance_id or not re.fullmatch(preflight.INSTANCE_ID_PATTERN, instance_id):
        return blocked('preflight file: instance_id missing or malformed', evidence)
    if args.instance_id and args.instance_id != instance_id:
        return blocked(f'--instance-id {args.instance_id} does not match the preflight '
                       f'result {instance_id}; binding requires the same instance',
                       evidence)
    status = discovery.get('status')
    if status not in PREFLIGHT_BINDABLE_STATUSES:
        return blocked(f'preflight result status {status!r} is not bindable '
                       f'(bindable: {", ".join(PREFLIGHT_BINDABLE_STATUSES)}); the '
                       f'policy list is only trustworthy after complete discovery',
                       evidence)
    summaries = discovery.get('policies')
    if not isinstance(summaries, list):
        return blocked('preflight file: policies list missing', evidence)
    by_id = {}
    for summary in summaries:
        policy_id = summary.get('policy_id') if isinstance(summary, dict) else None
        if policy_id:
            by_id[policy_id] = summary
    if args.policy_id:
        bound, missing, out_of_scope, seen = [], [], [], set()
        for policy_id in args.policy_id:
            if policy_id in seen:
                continue
            seen.add(policy_id)
            summary = by_id.get(policy_id)
            if summary is None:
                missing.append(policy_id)
            elif summary.get('default'):
                out_of_scope.append(policy_id)
            else:
                bound.append(summary)
        if missing:
            return blocked(f'policy IDs not present in the preflight result: {missing}; '
                           f'refresh discovery before binding', evidence)
        if out_of_scope:
            return blocked(f'default (fallback) policies are out of scope for state '
                           f'operations: {out_of_scope}', evidence)
    else:
        bound = [s for s in summaries
                 if isinstance(s, dict) and s.get('policy_id') and not s.get('default')]
    if not bound:
        return blocked('no custom conditional access policies found to bind', evidence)
    plan = {
        'schema_version': 1,
        'operation': operation,
        'instance_id': instance_id,
        'eiam_profile': args.eiam_profile,
        'intent_name': f'{operation}-{len(bound)}-policies',
        'preflight_status': status,
        'preflight_evidence_request_ids': [e.get('RequestId')
                                           for e in discovery.get('evidence') or []
                                           if isinstance(e, dict)],
        'bound_policies': bound,
        'actions': {
            'delete': ['disable_policies', 'readback_verify_disabled',
                       'delete_policies', 'readback_verify_removed'],
            'disable': ['disable_policies', 'readback_verify_disabled'],
            'enable': ['enable_policies', 'readback_verify_enabled'],
        }[operation],
        'deletion_irreversible': operation == 'delete',
    }
    path = Path(args.plan_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    note = {
        'delete': 'deletion is irreversible; apply runs disable -> readback -> delete -> '
                  'removal verification; split the observation gate by applying '
                  'plan-disable first, observing, then plan-delete',
        'disable': 'apply runs disable with per-policy status readback only',
        'enable': 'apply runs enable with per-policy status readback only',
    }[operation]
    print(json.dumps({'schema_version': 1, 'status': 'awaiting_confirmation',
                      'plan': plan, 'plan_sha256': digest(plan),
                      'note': 'show the plan to the user; apply only after one explicit '
                              f'confirmation of this exact plan. {note}'},
                     indent=2, default=str))
    return 0


def apply_state(plan, args, evidence):
    problems = validate_state_plan(plan)
    if problems:
        return blocked('state plan invalid: ' + '; '.join(problems), evidence)
    operation = plan['operation']
    instance_id, profile = plan['instance_id'], plan['eiam_profile']
    bound = plan['bound_policies']
    bound_ids = [entry['policy_id'] for entry in bound]

    fresh = list_policy_summaries(profile, instance_id, evidence)
    fresh_by_id = {entry['policy_id']: entry for entry in fresh}
    drift = []
    for entry in bound:
        summary = fresh_by_id.get(entry['policy_id'])
        if summary is None:
            drift.append(f'{entry["policy_id"]} disappeared after confirmation')
        elif policy_signature(summary) != policy_signature(entry):
            drift.append(f'{entry["policy_id"]} changed after confirmation')
    if drift:
        return blocked('bound policies drifted after confirmation: ' + '; '.join(drift)
                       + '; regenerate the plan from fresh discovery', evidence)

    try:
        require_write_commands(STATE_WRITE_ACTIONS[operation])
    except preflight.CommandError as error:
        return blocked(str(error), evidence, **error.fields())

    target = 'disabled' if operation in ('delete', 'disable') else 'enabled'
    switch_action = ('EnableConditionalAccessPolicy' if operation == 'enable'
                     else 'DisableConditionalAccessPolicy')
    results = []
    for entry in bound:
        result = {'policy_id': entry['policy_id'], 'name': entry.get('name'),
                  'priority': entry.get('priority')}
        if fresh_by_id[entry['policy_id']]['status'] == target:
            result['switched'] = False
            result['operation'] = f'already_{target}'
        else:
            try:
                preflight.eiam_call(profile, switch_action, evidence,
                                    InstanceId=instance_id,
                                    ConditionalAccessPolicyId=entry['policy_id'])
            except preflight.CommandError as error:
                return blocked(f'policy switch failed: {entry["policy_id"]}: {error}',
                               evidence, completed=results, **error.fields())
            result['switched'] = True
            result['operation'] = f'switched_to_{target}'
        results.append(result)

    for entry, result in zip(bound, results):
        try:
            detail = preflight.eiam_call(profile, 'GetConditionalAccessPolicy', evidence,
                                         InstanceId=instance_id,
                                         ConditionalAccessPolicyId=entry['policy_id']
                                         )['ConditionalAccessPolicy']
        except preflight.CommandError as error:
            return blocked(f'switch readback failed: {entry["policy_id"]}: {error}',
                           evidence, completed=results, **error.fields())
        status = (detail.get('Status') or '').lower() or None
        result['status'] = status
        if status != target:
            return blocked(f'hard-order check failed: {entry["policy_id"]} reads back '
                           f'{status!r}, expected {target!r} before '
                           f'{"deletion" if operation == "delete" else "completing"}; '
                           f'resume the same approved plan once the state settles',
                           evidence, completed=results)

    if operation == 'delete':
        for entry, result in zip(bound, results):
            try:
                preflight.eiam_call(profile, 'DeleteConditionalAccessPolicy', evidence,
                                    InstanceId=instance_id,
                                    ConditionalAccessPolicyId=entry['policy_id'])
            except preflight.CommandError as error:
                return blocked(f'policy deletion failed: {entry["policy_id"]}: {error}; '
                               f'already-disabled records are preserved, no rollback',
                               evidence, completed=results, **error.fields())
            result['operation'] = 'deleted'
        fresh_final = list_policy_summaries(profile, instance_id, evidence)
        remaining = [policy_id for policy_id in bound_ids
                     if any(entry['policy_id'] == policy_id for entry in fresh_final)]
        if remaining:
            return blocked(f'deletion verification failed; policies still listed: '
                           f'{remaining}', evidence, completed=results)
        remaining_custom = sum(1 for entry in fresh_final if not entry['default'])

    output = {'schema_version': 1, 'status': 'applied', 'operation': operation,
              'instance_id': instance_id, 'policies': results,
              'propagation_note': 'Policy changes take effect in about 3 minutes; a consistent read-back does not mean live effect',
              'resume_command': f'python3 scripts/ca_lifecycle.py apply '
                                f'--plan-file {args.plan_file} '
                                f'--approved-plan {args.approved_plan}',
              'evidence': evidence}
    if operation == 'delete':
        output['deletion_note'] = ('Deletion is irreversible; the default policy (priority '
                                   '1001 fallback) is out of scope — after deletion all '
                                   'traffic falls back to the default policy')
        output['remaining_custom_policies'] = remaining_custom
    print(json.dumps(output, indent=2, default=str))
    return 0


def cmd_apply(args):
    evidence = []
    try:
        plan = json.loads(Path(args.plan_file).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        return blocked(f'plan file unreadable: {error}', evidence)
    if args.approved_plan != digest(plan):
        return blocked('exact plan has not been confirmed; no cloud calls', evidence)
    operation = plan.get('operation', 'create')
    if operation == 'create':
        return apply_create(plan, args, evidence)
    if operation in STATE_OPERATIONS:
        return apply_state(plan, args, evidence)
    return blocked(f'unknown plan operation: {operation!r}; no cloud calls', evidence)


def apply_create(plan, args, evidence):
    if plan.get('preflight_status') != 'ready':
        return blocked('plan is not in an approved ready state', evidence)

    instance_id, profile = plan['instance_id'], plan['eiam_profile']
    app_ids = discovery_app_ids(plan['policies'])
    discovery = run_discovery(instance_id, profile, app_ids, evidence)
    if discovery.get('referenced_apps_not_configurable'):
        return blocked(f'referenced applications are system apps and cannot be '
                       f'conditional access targets (the portal '
                       f'{PORTAL_APP_ID} is the only configurable system app): '
                       f'{discovery["referenced_apps_not_configurable"]}', evidence,
                       discovery=discovery)
    if discovery.get('status') != 'ready':
        return blocked(f're-verified discovery blocks the apply: '
                       f'{discovery.get("status")}', evidence, discovery=discovery)

    custom_count = discovery['quota']['custom_policy_count']
    discovered_names = {p.get('name') for p in discovery.get('policies') or []}
    creating = [p for p in plan['policies']
                if p['ConditionalAccessPolicyName'] not in discovered_names]
    if custom_count + len(creating) > preflight.CUSTOM_POLICY_LIMIT:
        return blocked(f'quota changed since confirmation: {custom_count} custom policies '
                       f'exist; a new plan and confirmation are required', evidence)
    occupied = set(discovery.get('priorities_occupied') or [])
    for policy in creating:
        if policy['Priority'] in occupied:
            return blocked(f'priority {policy["Priority"]} was occupied after confirmation; '
                           f'generate a new plan', evidence)
    if discovery.get('referenced_apps_missing'):
        return blocked(f'referenced applications disappeared: '
                       f'{discovery["referenced_apps_missing"]}', evidence)
    existing_zone_ids = {z['zone_id'] for z in discovery.get('network_zones') or []}
    for policy in plan['policies']:
        zones = (policy.get('ConditionsConfig') or {}).get('NetworkZones') or {}
        for key in ('IncludeNetworkZones', 'ExcludeNetworkZones'):
            for ref in zones.get(key) or []:
                if ref not in existing_zone_ids:
                    return blocked(f'referenced network zone disappeared: {ref}', evidence)

    try:
        preflight.require_eiam_commands()
        require_write_commands()
        credential = write_credential(profile, evidence)
    except preflight.CommandError as error:
        return blocked(str(error), evidence, **error.fields())

    created_policies = []
    for policy in plan['policies']:
        existing = next((p for p in discovery.get('policies') or []
                         if p.get('name') == policy['ConditionalAccessPolicyName']), None)
        if existing:
            # Partial-failure resume: a policy an earlier interrupted apply already
            # created is reused when it still matches the confirmed plan.
            detail = preflight.eiam_call(profile, 'GetConditionalAccessPolicy', evidence,
                                         InstanceId=instance_id,
                                         ConditionalAccessPolicyId=existing['policy_id']
                                         )['ConditionalAccessPolicy']
            if (detail.get('Priority') != policy['Priority']
                    or not covers(normalize_decision(policy.get('DecisionConfig') or {}),
                                  normalize_decision(detail.get('DecisionConfig') or {}))
                    or not covers(policy.get('ConditionsConfig') or {},
                                  detail.get('ConditionsConfig') or {})):
                return blocked(f'existing policy {policy["ConditionalAccessPolicyName"]} '
                               f'differs from the confirmed plan; a new plan is required',
                               evidence, existing_policy=existing['policy_id'])
            created_policies.append({'ConditionalAccessPolicyId': existing['policy_id'],
                                     'name': policy['ConditionalAccessPolicyName'],
                                     'priority': policy['Priority'], 'readback_match': True,
                                     'operation': 'reused_after_partial_apply',
                                     'status': (detail.get('Status') or '').lower() or None})
            continue
        try:
            policy_id, operation = create_policy(credential, profile, instance_id, policy,
                                                 evidence)
        except preflight.CommandError as error:
            return blocked(f'policy creation failed: {policy["ConditionalAccessPolicyName"]}: '
                           f'{error}', evidence, **error.fields())
        detail = preflight.eiam_call(profile, 'GetConditionalAccessPolicy', evidence,
                                     InstanceId=instance_id,
                                     ConditionalAccessPolicyId=policy_id)['ConditionalAccessPolicy']
        readback_match = (detail.get('ConditionalAccessPolicyName')
                          == policy['ConditionalAccessPolicyName']
                          and detail.get('Priority') == policy['Priority']
                          and detail.get('Description') == policy.get('Description')
                          and covers(normalize_decision(policy.get('DecisionConfig') or {}),
                                     normalize_decision(detail.get('DecisionConfig') or {}))
                          and covers(policy.get('ConditionsConfig') or {},
                                     detail.get('ConditionsConfig') or {}))
        enabled = (detail.get('Status') or '').lower() == 'enabled'
        if not enabled:
            preflight.eiam_call(profile, 'EnableConditionalAccessPolicy', evidence,
                                InstanceId=instance_id, ConditionalAccessPolicyId=policy_id)
            enabled = True
        created_policies.append({'ConditionalAccessPolicyId': policy_id,
                                 'name': policy['ConditionalAccessPolicyName'],
                                 'priority': policy['Priority'],
                                 'readback_match': readback_match,
                                 'operation': operation, 'status': 'enabled' if enabled
                                 else detail.get('Status')})
        if not readback_match:
            return blocked(f'readback mismatch for {policy["ConditionalAccessPolicyName"]}; '
                           f'preserve the created record and report', evidence,
                           created_policy=policy_id)

    print(json.dumps({'schema_version': 1, 'status': 'applied', 'instance_id': instance_id,
                      'policies': created_policies,
                      'propagation_note': 'Policy changes take effect in about 3 minutes; a consistent read-back does not mean live effect',
                      'resume_command': f'python3 scripts/ca_lifecycle.py apply '
                                         f'--plan-file {args.plan_file} '
                                         f'--approved-plan {args.approved_plan}',
                      'evidence': evidence}, indent=2, default=str))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=['plan', 'apply', 'plan-delete', 'plan-disable',
                                         'plan-enable'])
    parser.add_argument('--plan-file', required=True)
    parser.add_argument('--intent-file', help='plan mode: agent-generated intent JSON')
    parser.add_argument('--instance-id')
    parser.add_argument('--eiam-profile')
    parser.add_argument('--sim-user')
    parser.add_argument('--sim-group', action='append', default=[])
    parser.add_argument('--sim-ou', action='append', default=[])
    parser.add_argument('--sim-app')
    parser.add_argument('--sim-ip')
    parser.add_argument('--approved-plan', help='apply mode: SHA256 of the confirmed plan')
    parser.add_argument('--preflight-file',
                        help='plan-delete/disable/enable: saved ca_preflight.py stdout '
                             'to bind targets from; zero cloud calls')
    parser.add_argument('--policy-id', action='append', default=[],
                        help='plan-delete/disable/enable: bind this policy ID '
                             '(repeatable); omit to bind every custom policy')
    args = parser.parse_args()
    os.environ.setdefault('SKILL_SESSION_ID', uuid.uuid4().hex)
    try:
        if args.mode == 'plan':
            if not args.intent_file:
                return blocked('plan mode requires --intent-file', [])
            return cmd_plan(args)
        if args.mode in STATE_PLAN_MODES:
            return cmd_plan_state(args)
        return cmd_apply(args)
    except (KeyError, TypeError, ValueError) as error:
        return blocked(f'malformed plan or intent structure: {error!r}', [])


if __name__ == '__main__':
    sys.exit(main())
