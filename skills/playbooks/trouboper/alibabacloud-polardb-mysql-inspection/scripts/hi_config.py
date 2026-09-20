"""PolarDB MySQL Health Inspection - Global configuration and CLI invocation helpers"""
import subprocess
import json
import sys
import os
import secrets

_CLI_PROFILE = None
_INSPECT_DAYS = 7

ALL_ITEMS = ['resource', 'space', 'slowlog', 'session', 'alert']
_INSPECT_ITEMS = set(ALL_ITEMS)

_SKILL_NAME = 'alibabacloud-polardb-mysql-inspection'

# --- UA construction (reads SKILL_SESSION_ID & SKILL_VERSION from env) ---
_LOCAL_ONLY_COMMANDS = {'configure', 'version', 'plugin'}


def _resolve_skill_version():
    """Return skill version from env var, falling back to manifest.json."""
    ver = os.environ.get('SKILL_VERSION', '').strip()
    if ver:
        return ver
    # fallback: read references/manifest.json relative to this script
    manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'references', 'manifest.json')
    try:
        with open(manifest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        v = data.get('version', '')
        if isinstance(v, str) and v.strip():
            return v.strip()
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return 'unknown'


def _resolve_session_id():
    """Return session id from env var, generating a random one as fallback."""
    sid = os.environ.get('SKILL_SESSION_ID', '').strip()
    if sid:
        return sid
    return secrets.token_hex(16)  # 32-char lowercase hex


# Cache resolved values for the lifetime of this process
_SKILL_VERSION = None
_SESSION_ID = None


def get_user_agent():
    """Build the UA string per skill contract."""
    global _SKILL_VERSION, _SESSION_ID
    if _SKILL_VERSION is None:
        _SKILL_VERSION = _resolve_skill_version()
    if _SESSION_ID is None:
        _SESSION_ID = _resolve_session_id()
    return (f'AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{_SESSION_ID} '
            f'skill-version/{_SKILL_VERSION}')


def call_cli(product, action, region=None, endpoint=None, **kwargs):
    cmd = ['aliyun', product, action]
    # Append --user-agent only for cloud API commands, not local utilities
    if product not in _LOCAL_ONLY_COMMANDS:
        cmd.extend(['--user-agent', get_user_agent()])
    if _CLI_PROFILE:
        cmd.extend(['--profile', _CLI_PROFILE])
    if region:
        cmd.extend(['--region', region])
    if endpoint:
        cmd.extend(['--endpoint', endpoint])
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            stderr = result.stderr.strip()
            if stderr:
                print(f'  [WARN] {product} {action}: {stderr[:150]}', file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f'  [WARN] {product} {action} timed out', file=sys.stderr)
    except json.JSONDecodeError:
        pass
    return None


REGIONS = [
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen',
    'cn-qingdao', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-chengdu',
    'cn-hongkong', 'ap-southeast-1', 'ap-southeast-3',
    'ap-southeast-5', 'ap-northeast-1', 'us-west-1', 'us-east-1',
    'eu-west-1', 'eu-central-1', 'me-east-1',
]


STORAGE_TYPE_MAP = {
    'HighPerformance': 'PSL5',
    'PSL4': 'PSL4',
    'essdautopl': 'ESSD AutoPL',
    'essdpl0': 'ESSD PL0',
    'essdpl1': 'ESSD PL1',
    'essdpl2': 'ESSD PL2',
    'essdpl3': 'ESSD PL3',
}

CATEGORY_MAP = {
    'Normal': ('Cluster', '集群版'),
    'Basic': ('Single Node', '单节点'),
    'Archive': ('X-Engine', '高压缩引擎（X-Engine）'),
    'NormalMultimaster': ('Multi-Master Cluster', '多主架构集群版'),
    'SENormal': ('Standard', '标准版'),
}
