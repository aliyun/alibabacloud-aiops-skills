"""Local role-request validation and immutable plan artifacts; no cloud calls.

These checks do not establish IAM semantics, discovery or human authorization.
"""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys

VENDORS = ('alibaba_cloud', 'aws', 'tencent_cloud')
SECRET_KEYS = re.compile(r'(access.?key|secret|password|refresh.?token|access.?token|credential)', re.I)


def load(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))


def reject_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEYS.search(key):
                raise ValueError('Credential fields do not belong in role artifacts')
            reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            reject_secrets(item)


def text(value, key):
    item = value.get(key)
    if not isinstance(item, str) or not item.strip() or any(ord(c) < 32 for c in item):
        raise ValueError('Missing or invalid ' + key)
    return item


def validate(value):
    if not isinstance(value, dict):
        raise ValueError('Request must be a JSON object')
    reject_secrets(value)
    vendor = text(value, 'vendor')
    if vendor not in VENDORS:
        raise ValueError('Unsupported vendor')
    if not re.fullmatch(r'idaas_[A-Za-z0-9]+', text(value, 'instance_id')):
        raise ValueError('Invalid instance_id')
    width = r'\d{12}' if vendor in ('aws', 'tencent_cloud') else r'\d{12,20}'
    if not re.fullmatch(width, text(value, 'account_id'), flags=re.ASCII):
        raise ValueError('Invalid owner account_id')
    name = text(value, 'role_name')
    # A documented conservative subset; official vendor schema remains authoritative.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,63}', name):
        raise ValueError('Role name outside portable first-version subset')
    if name.lower().startswith(('idaas-eiam-', 'aliyunservicerole', 'awsservicerole')):
        raise ValueError('Reserved or system-role name')
    text(value, 'permission_intent')
    return value


def policy_document(document, vendor=None):
    if not isinstance(document, dict):
        raise ValueError('Policy document must be an object')
    statements = document.get('Statement', document.get('statement'))
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list) or not statements:
        raise ValueError('Policy requires nonempty statements')
    for statement in statements:
        if not isinstance(statement, dict):
            raise ValueError('Invalid policy statement')
        if statement.get('Effect', statement.get('effect')) not in ('Allow', 'Deny', 'allow', 'deny'):
            raise ValueError('Missing policy effect')
        if any(k.lower() in ('notaction', 'notresource', 'principal', 'notprincipal') for k in statement):
            raise ValueError('Unsupported business-policy element; review separately')
        actions = statement.get('Action', statement.get('action'))
        actions = [actions] if isinstance(actions, str) else actions
        action_pattern = r'(?:name/)?[A-Za-z0-9_-]+:[A-Za-z0-9_-]+' if vendor == 'tencent_cloud' else r'[A-Za-z0-9_-]+:[A-Za-z0-9_-]+'
        if not isinstance(actions, list) or not actions or any(
                not isinstance(a, str) or not re.fullmatch(action_pattern, a)
                for a in actions):
            raise ValueError('Business actions must be explicit service:Action values')
        resources = statement.get('Resource', statement.get('resource'))
        resources = [resources] if isinstance(resources, str) else resources
        if not isinstance(resources, list) or not resources or any(
                not isinstance(r, str) or not r.strip() for r in resources):
            raise ValueError('Missing business resources')
    return document


def validate_plan(plan):
    validate(plan)
    for key in ('eiam_profile', 'cloud_profile', 'eiam_owner_id', 'cloud_account_id',
                'site', 'mode', 'project_selection'):
        text(plan, key)
    if not re.fullmatch(r'\d{12,20}', plan['eiam_owner_id'], flags=re.ASCII):
        raise ValueError('Invalid EIAM owner')
    if not re.fullmatch(r'ca_[A-Za-z0-9]+', plan['cloud_account_id']):
        raise ValueError('Invalid connected account ID')
    if plan['site'] not in ('china_mainland', 'global'):
        raise ValueError('Invalid site')
    if plan['vendor'] == 'alibaba_cloud' and plan['site'] != 'china_mainland':
        raise ValueError('Unsupported Alibaba site')
    if plan['mode'] not in ('create', 'register', 'reuse', 'repair'):
        raise ValueError('Unsupported operation')
    for key in ('changes', 'discovery_evidence'):
        if not isinstance(plan.get(key), list) or not plan[key] or any(
                not isinstance(v, str) or not v.strip() for v in plan[key]):
            raise ValueError('Missing ' + key)
    constraints = plan.get('trust_constraints')
    if not isinstance(constraints, dict):
        raise ValueError('Missing trust constraints')
    for key in ('provider_id', 'issuer', 'audience'):
        text(constraints, key)
    if not constraints['issuer'].startswith('https://'):
        raise ValueError('HTTPS issuer required')
    duration = constraints.get('max_session_duration')
    if type(duration) is not int or not 3600 <= duration <= 43200:
        raise ValueError('Invalid session duration')
    policies = plan.get('business_policies')
    if not isinstance(policies, list) or not policies:
        raise ValueError('Explicit business policies required')
    names = set()
    for policy in policies:
        if not isinstance(policy, dict) or policy.get('kind') not in ('custom', 'managed', 'inline'):
            raise ValueError('Invalid policy kind')
        name = text(policy, 'name')
        if name in names:
            raise ValueError('Duplicate policy name')
        names.add(name)
        if policy['kind'] == 'managed':
            text(policy, 'id')
            text(policy, 'version')
        policy_document(policy.get('document'), plan['vendor'])
    return plan


def canonical(value):
    # Object order/whitespace are irrelevant; array order is preserved deliberately.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def seal(plan):
    validate_plan(plan)
    digest = hashlib.sha256(canonical(plan)).hexdigest()
    return {'schema_version': 1, 'plan': plan, 'sha256': digest,
            'client_token': 'role-' + digest[:59]}


def check(artifact, approved):
    if not isinstance(artifact, dict) or artifact.get('schema_version') != 1:
        raise ValueError('Unsupported artifact schema')
    if not isinstance(approved, str) or not re.fullmatch(r'[0-9a-f]{64}', approved):
        raise ValueError('Approved SHA256 required')
    expected = seal(artifact.get('plan'))
    for field in ('sha256', 'client_token'):
        actual = artifact.get(field)
        if not isinstance(actual, str) or not hmac.compare_digest(actual, expected[field]):
            raise ValueError('Plan artifact was changed')
    if not hmac.compare_digest(approved, expected['sha256']):
        raise ValueError('Plan differs from approved digest')
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'seal', 'check'):
        p = sub.add_parser(command)
        p.add_argument('--input', required=True)
        if command == 'seal':
            p.add_argument('--output', required=True)
        if command == 'check':
            p.add_argument('--approved-sha256', required=True)
    p = sub.add_parser('compare')
    p.add_argument('--expected', required=True)
    p.add_argument('--actual', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            validate(load(args.input))
            result = {'status': 'local_validation_passed', 'cloud_calls_performed': False}
        elif args.command == 'seal':
            result = seal(load(args.input))
            # Never overwrite an existing approved artifact.
            with Path(args.output).open('x', encoding='utf-8') as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            result = {'status': 'sealed', 'sha256': result['sha256'],
                      'cloud_calls_performed': False, 'user_approval_established': False}
        elif args.command == 'check':
            check(load(args.input), args.approved_sha256)
            result = {'status': 'integrity_verified', 'user_approval_established': False}
        else:
            equal = canonical(load(args.expected)) == canonical(load(args.actual))
            result = {'status': 'structurally_equal' if equal else 'different',
                      'effective_permissions_verified': False}
            print(json.dumps(result))
            return 0 if equal else 2
        print(json.dumps(result))
        return 0
    except (ValueError, KeyError, OSError, TypeError):
        # Do not echo untrusted artifact content, including possible secrets.
        print(json.dumps({'status': 'invalid_input_or_artifact', 'cloud_calls_performed': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
