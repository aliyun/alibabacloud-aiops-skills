"""Development-only distribution gates and in-memory dedicated profiles."""
import ast
import hashlib
import json
import pprint
import re
from urllib.parse import urlsplit
from build_release import FILES
from openagent_client.common import parse_manifest
from release_metadata import MANIFEST, validate_metadata

CANONICAL_NAME = 'alibabacloud-openagent-chat'
BUILD_TARGETS = {
    'production': {'catalog': {'cn-hangzhou': 'openagent.cn-hangzhou.aliyuncs.com',
                               'ap-southeast-1': 'openagent.ap-southeast-1.aliyuncs.com'},
                   'app_name': 'openagent'},
    'stable-pre': {'catalog': {'cn-hangzhou': 'openagent-pre.cn-hangzhou.aliyuncs.com'},
                   'app_name': 'openagent-stable-pre'},
}
SESSION_PATH = '/openapi/v1/agent/sessions'
SUPPORTED_OPERATIONS = {
    'CreateSession': ('POST', SESSION_PATH),
    'GetSession': ('GET', SESSION_PATH + '/{sessionId}'),
    'ListSessions': ('GET', SESSION_PATH),
    'ListMessages': ('GET', SESSION_PATH + '/{sessionId}/messages'),
    'GetRun': ('GET', SESSION_PATH + '/{sessionId}/runs/{runId}'),
    'CancelRun': ('POST', SESSION_PATH + '/{sessionId}/runs/{runId}/cancel'),
    'SendMessage': ('POST', SESSION_PATH + '/{sessionId}/messages'),
}
PUBLIC_URL_HOSTS = {'skills.aliyun.com', 'json-schema.org', 'www.alibabacloud.com'}


FORBIDDEN = {
    'preview-distribution-copy': r'(?i)\bstable[-_]pre\b|\bpre-release\b|\bpreview build\b',
    'internal-domain': r'(?i)\b(?:[a-z0-9-]+\.)*(?:alibaba-inc\.com|aliyun-inc\.com|alipay-inc\.com|antfin-inc\.com|taobao\.org)\b',
    'test-service': r'(?i)openagent-(?:pre|test|staging|daily)[a-z0-9.-]*\.aliyuncs\.com|\bpreview environment\b',
    'private-address': r'(?i)\blocalhost\b|\b(?:127|10)\.(?:\d{1,3}\.){2}\d{1,3}\b|\b192\.168\.\d{1,3}\.\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b',
    'personal-path': r'(?i)/(?:Users|home)/[^\s/]+|~/(?:\.codex|\.qwenworkcn|\.claude)(?:/|\b)|[A-Z]:\\Users\\',
    'development-path': r'(?i)/(?:private/)?tmp/[^\s]+|[A-Z]:\\(?:Temp|tmp)\\',
    'internal-profile-diagnostic': r'\b(?:PROFILE_VERSION|profile_version)\b',
    'internal-schema-identity': r'(?i)agui-profile|2026-08-18',
    'internal-reference': r'(?i)\b(?:oneagent|janus|aone|wenyang|gaorutong)\b|镇元|预发|内网',
    'real-resource-identifier': r'\b(?:ses_|sess_|run_)[A-Za-z0-9]{10,}\b|\b(?:i|vpc|vsw|sg|eip)-[A-Za-z0-9]{12,}\b|(?<![\w])\d{16}(?![\w])',
    'email-address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'credential-value': r'\bLTAI[A-Za-z0-9]{12,}\b|\bsk-[A-Za-z0-9_-]{16,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'embedded-secret': r'''(?i)["']?(?:access_key_secret|accessKeySecret|api_key|apiKey|password|security_token)["']?\s*[:=]\s*["'][^"'\r\n]+["']''',
    'release-policy-copy': r'(?is)(?:this skill|本\s*skill|本技能).{0,60}(?:does not contain|contains no|不包含).{0,60}(?:internal|内部)',
}

def assignment(payload, name):
    try:
        tree = ast.parse(payload.decode('utf-8'))
    except (SyntaxError, UnicodeError):
        raise ValueError('Invalid Python in a customer resource') from None
    matches = [node for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    if len(matches) != 1:
        raise ValueError('Release audit failed: expected one reviewed configuration declaration.')
    return matches[0].value

def literal_span(payload, node):
    lines = payload.splitlines(keepends=True)
    return (sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset,
            sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset)

def replace_literal(payload, name, value):
    start, end = literal_span(payload, assignment(payload, name))
    return payload[:start] + pprint.pformat(value, width=110, sort_dicts=True).encode() + payload[end:]

def rehash(payloads):
    metadata = json.loads(payloads[MANIFEST])
    metadata['files'] = {name: hashlib.sha256(content).hexdigest()
                         for name, content in sorted(payloads.items()) if name != MANIFEST}
    payloads[MANIFEST] = (json.dumps(metadata, indent=2) + '\n').encode()
    return payloads


def catalog_value(payload, node):
    if isinstance(node, ast.DictComp):
        expected = ast.parse("{region: f'openagent.{region}.aliyuncs.com' for region in SERVICE_REGIONS}", mode='eval').body
        if ast.dump(node) != ast.dump(expected):
            raise ValueError('Unreviewed service catalog expression')
        regions = ast.literal_eval(assignment(payload, 'SERVICE_REGIONS'))
        return {region: 'openagent.' + region + '.aliyuncs.com' for region in regions}
    return ast.literal_eval(node)


def audit(payloads, target='production'):
    """Require the reviewed inventory, identity, routing, API set and digest."""
    if target not in BUILD_TARGETS or set(payloads) != set(FILES) | {MANIFEST}:
        raise ValueError('Unexpected build target or customer file inventory')
    profile = BUILD_TARGETS[target]
    settings = payloads['scripts/openagent_client/settings.py']
    catalog_node = assignment(settings, 'PRODUCTION_ENDPOINTS')
    if catalog_value(settings, catalog_node) != profile['catalog']:
        raise ValueError('Service catalog does not match the build target')
    if set(ast.literal_eval(assignment(settings, 'SERVICE_REGIONS'))) != set(profile['catalog']):
        raise ValueError('Selectable regions differ from the service catalog')
    if ast.literal_eval(assignment(payloads['scripts/openagent_client/common.py'], 'APP_NAME')) != profile['app_name']:
        raise ValueError('Storage namespace does not match the build target')
    operations = ast.literal_eval(assignment(payloads['scripts/openagent_client/contract.py'], 'OPERATIONS'))
    if operations != {name: {'method': method, 'path': path}
                      for name, (method, path) in SUPPORTED_OPERATIONS.items()}:
        raise ValueError('The package must contain exactly the supported 7 conversation APIs')
    contract_schemas = ast.literal_eval(assignment(payloads['scripts/openagent_client/contract.py'], 'SCHEMAS'))
    if any(name.startswith(('UpdateSession', 'DeleteSession'))
           for name in contract_schemas['api']['$defs']):
        raise ValueError('Session administration schemas must not enter the conversation package')
    skill = payloads['SKILL.md'].decode('utf-8')
    if not skill.startswith('---\n') or '\n---\n' not in skill[4:]:
        raise ValueError('Missing skill identity')
    header = skill[4:].split('\n---\n', 1)[0]
    if re.findall(r'^name:[ \t]*(.*?)[ \t]*$', header, re.MULTILINE) != [CANONICAL_NAME]:
        raise ValueError('Expected the canonical skill identity')
    for name, payload in payloads.items():
        text = payload.decode('utf-8')
        if name.endswith('.py'):
            try:
                compile(payload, name, 'exec')
            except SyntaxError:
                raise ValueError('Invalid Python in ' + name) from None
        for rule, expression in FORBIDDEN.items():
            if target != 'production' and rule == 'preview-distribution-copy':
                continue
            inspected = payload
            if target != 'production' and name == 'scripts/openagent_client/settings.py' and rule == 'test-service':
                for node in ast.walk(catalog_node):
                    if isinstance(node, ast.Constant) and node.value in profile['catalog'].values():
                        start, end = literal_span(payload, node)
                        if payload[start:end] not in (repr(node.value).encode(), json.dumps(node.value).encode()):
                            raise ValueError('The service address must be one exact string literal')
                        inspected = inspected[:start] + b' ' * (end - start) + inspected[end:]
            if re.search(expression, inspected.decode('utf-8')):
                # Never echo the matched content: it could contain a secret.
                raise ValueError('Package audit failed: ' + name + ': ' + rule)
        for url in re.findall(r"https?://[^\s\"'<>]+", text):
            parsed = urlsplit(url.rstrip(').,;'))
            if parsed.hostname not in PUBLIC_URL_HOSTS or parsed.username or parsed.password:
                raise ValueError('Unreviewed URL in ' + name)
    metadata = validate_metadata(json.loads(payloads[MANIFEST]))
    api_version = ast.literal_eval(assignment(payloads['scripts/openagent_client/contract.py'], 'API_VERSION'))
    if metadata['api_version'] != api_version or api_version != '2026-08-01':
        raise ValueError('Release and reviewed contract API versions differ')
    if metadata.get('name') != CANONICAL_NAME or metadata.get('distribution', 'production') != target:
        raise ValueError('Release identity or distribution mismatch')
    if metadata.get('version') != parse_manifest(payloads[MANIFEST], MANIFEST):
        raise ValueError('Release and runtime versions differ')
    if {'catalog_identifier', 'update_channel'} & metadata.keys():
        raise ValueError('Conversation packages must not carry online update configuration')
    expected = {name: hashlib.sha256(content).hexdigest() for name, content in payloads.items() if name != MANIFEST}
    if metadata['files'] != expected:
        raise ValueError('Manifest hash mismatch')
    return {'version': metadata['version'], 'distribution': target, 'files': len(payloads), 'apis': len(operations)}


def profile_payloads(payloads, target='production'):
    """Create a dedicated package in memory, preserving production source."""
    audit(payloads)
    result = dict(payloads)
    if target == 'production':
        return result
    if target not in BUILD_TARGETS:
        raise ValueError('Unsupported build target')
    profile = BUILD_TARGETS[target]
    result['scripts/openagent_client/settings.py'] = replace_literal(
        result['scripts/openagent_client/settings.py'], 'PRODUCTION_ENDPOINTS', profile['catalog'])
    result['scripts/openagent_client/settings.py'] = replace_literal(
        result['scripts/openagent_client/settings.py'], 'SERVICE_REGIONS', {'cn-hangzhou': 'Hangzhou'})
    result['scripts/openagent_client/common.py'] = replace_literal(
        result['scripts/openagent_client/common.py'], 'APP_NAME', profile['app_name'])
    notice = ('Preview build: stable-pre. Service access is limited to cn-hangzhou. '
              'Local files are isolated from production.\n\n').encode()
    for name, heading in [('SKILL.md', b'# OpenAgent\n\n'),
                          ('references/setup.md', b'# OpenAgent Skill connection setup\n\n')]:
        if result[name].count(heading) != 1:
            raise ValueError('Expected one package introduction')
        result[name] = result[name].replace(heading, heading + notice, 1)
    result['references/setup.md'] = result['references/setup.md'].replace(
        b'/openagent`', ('/' + profile['app_name'] + '`').encode())
    for name in ('SKILL.md', 'references/setup.md'):
        result[name] = result[name].replace(
            b'Hangzhou (cn-hangzhou) or Singapore (ap-southeast-1)', b'Hangzhou (cn-hangzhou)')
    result['references/setup.md'] = result['references/setup.md'].replace(
        b'The client resolves the service address as `openagent.${regionId}.aliyuncs.com` for the selected supported region;',
        b'This dedicated build supplies a fixed service address for its supported region;')
    metadata = json.loads(result[MANIFEST])
    metadata.update(distribution=target)
    result[MANIFEST] = (json.dumps(metadata, indent=2) + '\n').encode()
    rehash(result)
    audit(result, target)
    return result
