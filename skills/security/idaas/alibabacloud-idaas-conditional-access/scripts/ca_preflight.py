#!/usr/bin/env python3
"""Read-only conditional access preflight for IDaaS EIAM instances.

Discovers conditional access policies, network zones, and applications; checks
custom-policy quota, priority occupancy, and entity references (including the
system-app configurability split); and simulates policy hit chains. This helper
never writes to the instance.

Usage:
  cloud:  python3 ca_preflight.py --instance-id ID --eiam-profile PROFILE \
            [--app-id APP_ID ...] [--network-zone-id ZONE_ID ...] \
            [--sim-user U --sim-group G ... --sim-ou OU ... --sim-app A --sim-ip IP]
  local:  python3 ca_preflight.py --local-only --instance-id ID [other args]
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

CUSTOM_POLICY_LIMIT = 10
CUSTOM_PRIORITY_MIN = 1
CUSTOM_PRIORITY_MAX = 100
DEFAULT_PRIORITY = 1001
MAX_RESULTS = 50
TIMEOUT = 60
STDERR_TAIL = 400

INSTANCE_ID_PATTERN = r'^idaas_[A-Za-z0-9_.@-]{6,128}$'
APP_ID_PATTERN = r'^app_[A-Za-z0-9_.@-]+$'
ZONE_ID_PATTERN = r'^network_[A-Za-z0-9_.@-]+$'
PORTAL_APP_ID = 'iap_user_portal'

AUTH_MARKERS = ('InvalidAccessKeyId', 'SignatureDoesNotMatch', 'Forbidden',
                'Unauthorized', 'LoginRequired', 'ExpiredToken', 'STS.ExpiredToken')
INSTANCE_MARKERS = ('not exist', 'NotExist', 'InvalidInstanceId')
ENVIRONMENT_MARKERS = ('unknown profile', 'Configuration failed', 'no such file or directory')


class CommandError(Exception):
    def __init__(self, argv, message, error_type='cloud', stderr_tail='', request_id=''):
        super().__init__(message)
        self.argv = list(argv)
        self.error_type = error_type
        self.stderr_tail = (stderr_tail or '')[-STDERR_TAIL:]
        self.request_id = request_id

    def fields(self):
        command = self.argv[2] if len(self.argv) > 2 else (self.argv[0] if self.argv else '')
        return {'error_type': self.error_type, 'action': command,
                'message': str(self), 'stderr_tail': self.stderr_tail,
                'RequestId': self.request_id}


def load_manifest_version():
    manifest = Path(__file__).resolve().parent.parent / 'references' / 'manifest.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    version = data.get('version')
    if isinstance(version, str) and re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.-]{0,31}', version):
        return version
    return None


def user_agent():
    version = load_manifest_version()
    if not version:
        raise CommandError([], 'skill manifest missing or invalid; no cloud calls permitted',
                           error_type='environment')
    session = os.environ.get('SKILL_SESSION_ID', '')
    if not re.fullmatch(r'[0-9a-f]{32}', session or ''):
        raise CommandError([], 'invalid SKILL_SESSION_ID; no cloud calls permitted',
                           error_type='environment')
    return (f'AlibabaCloud-Agent-Skills/alibabacloud-idaas-conditional-access/{session} '
            f'skill-version/{version}')


def run(argv, timeout=TIMEOUT):
    env = os.environ.copy()
    env['ALIBABA_CLOUD_USER_AGENT'] = user_agent()
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, env=env)


def run_json(argv, timeout=TIMEOUT):
    try:
        proc = run(argv, timeout)
    except subprocess.TimeoutExpired as exc:
        raise CommandError(argv, f'timed out calling {argv[1] if len(argv) > 1 else argv[0]}',
                           error_type='timeout') from exc
    except FileNotFoundError as exc:
        raise CommandError(argv, 'aliyun CLI not found; install the official CLI first',
                           error_type='environment') from exc
    if proc.returncode:
        stderr = proc.stderr or ''
        request_id = ''
        match = re.search(r'"RequestId"\s*:\s*"([^"]+)"', stderr)
        if match:
            request_id = match.group(1)
        if any(marker in stderr for marker in AUTH_MARKERS):
            error_type = 'auth'
        elif any(marker in stderr for marker in INSTANCE_MARKERS):
            error_type = 'instance'
        elif any(marker in stderr for marker in ENVIRONMENT_MARKERS):
            error_type = 'environment'
        else:
            error_type = 'cloud'
        raise CommandError(argv, f'{argv[1] if len(argv) > 1 else argv[0]} failed with exit '
                                  f'{proc.returncode}', error_type=error_type,
                          stderr_tail=stderr, request_id=request_id)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CommandError(argv, 'non-JSON output from CLI; installation messages may have '
                                  'corrupted the response', error_type='environment',
                          stderr_tail=(proc.stderr or '')) from exc


def flat_args(prefix, value):
    """Aliyun CLI 'flat' serialization: lists become 1-based indexed flags.
    Object parameters cannot be sent through the CLI at all; see eiam_call."""
    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            yield from flat_args(f'{prefix}.{index}', item)
    else:
        yield prefix, str(value)


def eiam_call(profile, action, evidence, **params):
    argv = ['aliyun', 'eiam', action, '--profile', profile]
    for key, value in params.items():
        if value is None or value == '' or value == {} or value == []:
            continue
        if isinstance(value, dict):
            # Verified live: EIAM rejects JSON strings for object params ('Flat
            # format is required', i.e. 'DecisionConfig.Effect=Allow') and the
            # CLI itself rejects dot-path flags. Object params need the SDK transport.
            raise CommandError(argv, f'{key} is an object parameter; the aliyun CLI cannot '
                                      f'send EIAM object parameters; use the SDK transport',
                               error_type='environment')
        for flag, item in flat_args(key, value):
            argv.extend(['--' + flag, item])
    data = run_json(argv)
    evidence.append({'product': 'eiam', 'action': action, 'RequestId': data.get('RequestId')})
    return data


def _strip_ansi(text):
    """Remove ANSI escape sequences that some aliyun CLI versions embed in --help."""
    if not text:
        return ''
    return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', text)


def require_eiam_commands():
    argv = ['aliyun', 'eiam', 'ListConditionalAccessPolicies', '--help']
    try:
        proc = run(argv, timeout=20)
    except subprocess.TimeoutExpired as exc:
        raise CommandError(argv, 'local EIAM command capability check timed out',
                           error_type='environment') from exc
    stdout = _strip_ansi(proc.stdout)
    if proc.returncode or 'ListConditionalAccessPolicies' not in stdout \
            or '--InstanceId' not in stdout:
        raise CommandError(argv, 'installed EIAM CLI does not provide the required command',
                           error_type='environment')


def paginate_tokens(profile, action, key, evidence, instance_id, **fixed):
    """Token-paginated list (NextToken/MaxResults). Guards repeated tokens."""
    items, token, seen = [], None, set()
    while True:
        params = dict(InstanceId=instance_id, MaxResults=MAX_RESULTS, **fixed)
        if token:
            params['NextToken'] = token
        data = eiam_call(profile, action, evidence, **params)
        page = data.get(key)
        if not isinstance(page, list):
            raise CommandError(['aliyun', 'eiam', action], f'malformed response: {key} not a list')
        items.extend(page)
        token = data.get('NextToken')
        if not token or not page or token in seen:
            break
        seen.add(token)
    return items


def paginate_pages(profile, action, key, evidence, instance_id, **fixed):
    """PageNumber/PageSize-paginated list."""
    items, page = [], 1
    while True:
        params = dict(InstanceId=instance_id, PageSize=MAX_RESULTS, PageNumber=page, **fixed)
        data = eiam_call(profile, action, evidence, **params)
        chunk = data.get(key)
        if not isinstance(chunk, list):
            raise CommandError(['aliyun', 'eiam', action], f'malformed response: {key} not a list')
        items.extend(chunk)
        if len(chunk) < MAX_RESULTS:
            break
        page += 1
    return items


def is_default_policy(policy):
    # Custom policies use priorities 1-100; the system default policy is 1001.
    # ConditionalAccessPolicyType cannot identify defaults: GetConditionalAccessPolicy
    # shows custom policies also carry type 'arn:alibaba:idaas:authn:access:policy:system'.
    priority = policy.get('Priority')
    return not isinstance(priority, int) or priority < CUSTOM_PRIORITY_MIN \
        or priority > CUSTOM_PRIORITY_MAX


def policy_summary(policy):
    decision = policy.get('DecisionConfig') or {}
    conditions = policy.get('ConditionsConfig') or {}
    applications = conditions.get('Applications') or {}
    users = conditions.get('Users') or {}
    zones = conditions.get('NetworkZones') or {}
    return {
        'policy_id': policy.get('ConditionalAccessPolicyId'),
        'name': policy.get('ConditionalAccessPolicyName'),
        # Live instances return capitalized enums ('Allow'/'Deny'); normalize for matching.
        'status': (policy.get('Status') or '').lower() or None,
        'priority': policy.get('Priority'),
        'default': is_default_policy(policy),
        'effect': (decision.get('Effect') or '').lower() or None,
        'mfa_type': (decision.get('MfaType') or '').lower() or None,
        'mfa_methods': decision.get('MfaAuthenticationMethods') or [],
        'session_reuse': (decision.get('ActiveSessionReuseStatus') or '').lower() or None,
        'include_applications': applications.get('IncludeApplications') or [],
        'exclude_applications': applications.get('ExcludeApplications') or [],
        'include_users': users.get('IncludeUsers') or [],
        'include_groups': users.get('IncludeGroups') or [],
        'include_organizational_units': users.get('IncludeOrganizationalUnits') or [],
        'exclude_users': users.get('ExcludeUsers') or [],
        'exclude_groups': users.get('ExcludeGroups') or [],
        'exclude_organizational_units': users.get('ExcludeOrganizationalUnits') or [],
        'include_network_zones': zones.get('IncludeNetworkZones') or [],
        'exclude_network_zones': zones.get('ExcludeNetworkZones') or [],
    }


def zone_contains(zone, address):
    if str(zone.get('NetworkZoneType') or '').endswith(':vpc'):
        return None  # VPC zone membership cannot be verified locally from an IP.
    cidrs = list(zone.get('Ipv4Cidrs') or []) + list(zone.get('Ipv6Cidrs') or [])
    for cidr in cidrs:
        try:
            if address in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def simulate(policies, zones_by_id, sim):
    ordered = sorted((policy_summary(p) for p in policies if p.get('Status') == 'enabled'),
                     key=lambda s: s['priority'] if isinstance(s['priority'], int)
                     else DEFAULT_PRIORITY)
    if not any(s['default'] for s in ordered):
        ordered.append({'policy_id': 'default_policy', 'name': 'Default policy (system fallback)',
                        'priority': DEFAULT_PRIORITY, 'default': True,
                        'effect': 'allow', 'mfa_type': 'mfa_required',
                        'mfa_methods': [], 'session_reuse': None,
                        'include_applications': [], 'exclude_applications': [],
                        'include_users': [], 'include_groups': [],
                        'include_organizational_units': [],
                        'exclude_users': [], 'exclude_groups': [],
                        'exclude_organizational_units': [],
                        'include_network_zones': [], 'exclude_network_zones': []})
    groups, ous = set(sim['groups']), set(sim['ous'])

    def app_match(summary):
        if summary['exclude_applications'] and sim['app'] in summary['exclude_applications']:
            return False
        return not summary['include_applications'] or sim['app'] in summary['include_applications']

    def user_match(summary):
        include_scope = (set(summary['include_users']) | set(summary['include_groups'])
                         | set(summary['include_organizational_units']))
        included = (not include_scope or sim['user'] in set(summary['include_users'])
                    or groups & set(summary['include_groups'])
                    or ous & set(summary['include_organizational_units']))
        excluded = (sim['user'] in set(summary['exclude_users'])
                    or groups & set(summary['exclude_groups'])
                    or ous & set(summary['exclude_organizational_units']))
        return included and not excluded

    def network_match(summary):
        if summary['exclude_network_zones'] and address is not None:
            for zone_id in summary['exclude_network_zones']:
                zone = zones_by_id.get(zone_id)
                if zone and zone_contains(zone, address):
                    return False
        if not summary['include_network_zones']:
            return True
        if address is None:
            return None
        results = []
        for zone_id in summary['include_network_zones']:
            zone = zones_by_id.get(zone_id)
            if zone:
                results.append(zone_contains(zone, address))
        return any(result is True for result in results)

    try:
        address = ipaddress.ip_address(sim['ip']) if sim['ip'] else None
    except ValueError:
        address = None

    for summary in ordered:
        if app_match(summary) and user_match(summary) and network_match(summary):
            return {
                'policy_id': summary['policy_id'], 'name': summary['name'],
                'priority': summary['priority'],
                'decision': decision_text(summary),
                'simulated': {'user': sim['user'], 'app': sim['app'], 'ip': sim['ip']},
                'approximate': address is None and any(
                    zone in zones_by_id and zones_by_id[zone].get('NetworkZoneType', '').endswith(':vpc')
                    for zone in summary['include_network_zones'] if zone in zones_by_id),
            }
    return None


def decision_text(summary):
    if summary['effect'] == 'deny':
        return 'Deny access'
    if summary['mfa_type'] == 'mfa_required':
        methods = '/'.join(summary['mfa_methods']) or 'console second-factor settings'
        return f'Allow access + MFA required ({methods})'
    return 'Allow access (no second factor)'


def local_validation(args):
    errors = []
    if not re.fullmatch(INSTANCE_ID_PATTERN, args.instance_id or ''):
        errors.append('instance_id: expect idaas_xxx')
    for app_id in args.app_id or []:
        if app_id == PORTAL_APP_ID:
            continue
        if not re.fullmatch(APP_ID_PATTERN, app_id):
            if app_id.startswith('iap_'):
                errors.append(f'app_id: system application, not configurable '
                              f'(the portal {PORTAL_APP_ID} is the only '
                              f'configurable system app): {app_id}')
            else:
                errors.append(f'app_id: invalid format: {app_id}')
    for zone_id in args.network_zone_id or []:
        if not re.fullmatch(ZONE_ID_PATTERN, zone_id):
            errors.append(f'network_zone_id: invalid format: {zone_id}')
    if args.sim_ip:
        try:
            ipaddress.ip_address(args.sim_ip)
        except ValueError:
            errors.append(f'sim_ip: not an IP address: {args.sim_ip}')
    if (args.sim_user or args.sim_app) and not (args.sim_user and args.sim_app):
        errors.append('simulation requires both --sim-user and --sim-app')
    if errors:
        return {'schema_version': 1, 'status': 'local_validation_failed',
                'errors': errors}, 2
    return {'schema_version': 1, 'status': 'local_validation_passed',
            'instance_id': args.instance_id,
            'app_ids': args.app_id or [], 'network_zone_ids': args.network_zone_id or [],
            'simulation_requested': bool(args.sim_user or args.sim_app)}, 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--instance-id', help='EIAM instance ID (idaas_xxx)')
    parser.add_argument('--eiam-profile', help='aliyun CLI profile authorized for EIAM')
    parser.add_argument('--app-id', action='append', default=[],
                        help='application ID referenced by the intent (repeatable)')
    parser.add_argument('--network-zone-id', action='append', default=[],
                        help='network zone ID referenced by the intent (repeatable)')
    parser.add_argument('--sim-user', help='hit-preview: user ID')
    parser.add_argument('--sim-group', action='append', default=[],
                        help='hit-preview: group IDs the user belongs to (repeatable)')
    parser.add_argument('--sim-ou', action='append', default=[],
                        help='hit-preview: organizational unit IDs (repeatable)')
    parser.add_argument('--sim-app', help='hit-preview: application ID')
    parser.add_argument('--sim-ip', help='hit-preview: source IP address')
    parser.add_argument('--local-only', action='store_true',
                        help='syntax-only validation; no CLI discovery or cloud calls')
    args = parser.parse_args()

    if args.local_only:
        result, code = local_validation(args)
        print(json.dumps(result, indent=2))
        return code

    if not args.instance_id or not args.eiam_profile:
        print(json.dumps({'schema_version': 1, 'status': 'input_required',
                          'missing': [field for field, value in
                                      (('instance_id', args.instance_id),
                                       ('eiam_profile', args.eiam_profile)) if not value]}))
        return 2

    os.environ.setdefault('SKILL_SESSION_ID', uuid.uuid4().hex)
    evidence = []
    errors = []
    try:
        require_eiam_commands()
        policies = paginate_tokens(args.eiam_profile, 'ListConditionalAccessPolicies',
                                   'ConditionalAccessPolicies', evidence, args.instance_id)
        zones = paginate_tokens(args.eiam_profile, 'ListNetworkZones',
                                'NetworkZones', evidence, args.instance_id)
        apps = []
        not_configurable = []
        if args.app_id:
            # Default ApplicationCreationType=user_custom resolves only
            # user-created apps: conditional access targets are user_custom
            # apps plus the portal (the sole configurable system app).
            # NOTE: we do NOT pass ApplicationIds to the CLI. Aliyun CLI 3.5.0
            # rejects the legacy flat-indexed array format for this plugin
            # command, so we fetch all pages and filter locally.
            all_user_apps = paginate_pages(args.eiam_profile, 'ListApplications',
                                           'Applications', evidence, args.instance_id)
            apps = [a for a in all_user_apps
                    if a.get('ApplicationId') in set(args.app_id)]
            # The portal is a fixed constant and never resolves via the
            # user_custom query; count it as resolved so the second pass
            # never classifies it as a not-configurable system app.
            resolved = {a.get('ApplicationId') for a in apps} | {PORTAL_APP_ID}
            unresolved = [app_id for app_id in args.app_id if app_id not in resolved]
            if unresolved:
                # Second pass with all: separates existing-but-system (not
                # configurable) from nonexistent IDs. Again no ApplicationIds
                # filter, to stay compatible with CLI 3.5.0.
                all_system_apps = paginate_pages(args.eiam_profile, 'ListApplications',
                                                 'Applications', evidence, args.instance_id,
                                                 ApplicationCreationType='all',
                                                 ApplicationIdentityType='all')
                system_ids = {a.get('ApplicationId') for a in all_system_apps}
                not_configurable = [app_id for app_id in unresolved
                                    if app_id in system_ids]
    except CommandError as error:
        status = {'auth': 'auth_required', 'instance': 'instance_unavailable',
                  'environment': 'environment_required'}.get(error.error_type,
                                                              'discovery_incomplete')
        print(json.dumps({'schema_version': 1, 'status': status,
                          'errors': [error.fields()], 'evidence': evidence}, indent=2))
        return 2

    summaries = [policy_summary(p) for p in policies]
    zones_by_id = {z.get('NetworkZoneId'): z for z in zones}
    apps_by_id = {a.get('ApplicationId'): a for a in apps}

    missing_apps = [app_id for app_id in args.app_id
                    if app_id != PORTAL_APP_ID
                    and app_id not in apps_by_id
                    and app_id not in not_configurable]
    missing_zones = [zone_id for zone_id in args.network_zone_id if zone_id not in zones_by_id]

    custom = [s for s in summaries if not s['default']]
    occupied = sorted({s['priority'] for s in custom if isinstance(s['priority'], int)})
    free = [p for p in range(CUSTOM_PRIORITY_MIN, CUSTOM_PRIORITY_MAX + 1) if p not in occupied][:5]

    related = []
    for summary in custom:
        if args.app_id and set(args.app_id) & set(summary['include_applications']):
            related.append({'policy_id': summary['policy_id'], 'name': summary['name'],
                            'priority': summary['priority'], 'effect': summary['effect']})

    simulation = None
    if args.sim_user and args.sim_app:
        simulation = simulate(policies, zones_by_id,
                              {'user': args.sim_user, 'groups': args.sim_group,
                               'ous': args.sim_ou, 'app': args.sim_app, 'ip': args.sim_ip})

    if missing_apps or missing_zones:
        status = 'entity_missing'
    elif not_configurable:
        status = 'entity_not_configurable'
    elif len(custom) >= CUSTOM_POLICY_LIMIT:
        status = 'quota_exceeded'
    else:
        status = 'ready'

    print(json.dumps({
        'schema_version': 1,
        'status': status,
        'instance_id': args.instance_id,
        'quota': {'custom_policy_limit': CUSTOM_POLICY_LIMIT,
                  'custom_policy_count': len(custom),
                  'remaining': max(0, CUSTOM_POLICY_LIMIT - len(custom))},
        'priorities_occupied': occupied,
        'priorities_free_sample': free,
        'policies': summaries,
        'network_zones': [{'zone_id': z.get('NetworkZoneId'),
                           'name': z.get('NetworkZoneName'),
                           'type': z.get('NetworkZoneType'),
                           'ipv4_cidrs': z.get('Ipv4Cidrs') or [],
                           'ipv6_cidrs': z.get('Ipv6Cidrs') or []} for z in zones],
        'referenced_apps_missing': missing_apps,
        'referenced_apps_not_configurable': not_configurable,
        'referenced_zones_missing': missing_zones,
        'related_policies': related,
        'simulation': simulation,
        'evidence': evidence,
    }, indent=2, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
