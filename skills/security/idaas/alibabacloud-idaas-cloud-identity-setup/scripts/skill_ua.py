"""Manifest-derived Alibaba Cloud skill attribution; standard library only."""
import json
import os
from pathlib import Path
import re
import uuid

MANIFEST_PATH = Path(__file__).resolve().parents[1] / 'references' / 'manifest.json'
SKILL_NAME = 'alibabacloud-idaas-cloud-identity-setup'
VERSION_RE = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?')
_SESSION = None


def user_agent():
    global _SESSION
    try:
        version = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))['version']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Cannot read skill version from references/manifest.json; refusing cloud calls') from exc
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise ValueError('Invalid manifest version; refusing cloud calls')
    if _SESSION is None:
        session = os.environ.get('SKILL_SESSION_ID') or uuid.uuid4().hex
        if not re.fullmatch(r'[0-9a-f]{32}', session):
            raise ValueError('SKILL_SESSION_ID must be 32 lowercase hex characters')
        _SESSION = session
    return f'AlibabaCloud-Agent-Skills/{SKILL_NAME}/{_SESSION} skill-version/{version}'


if __name__ == '__main__':
    print(user_agent())
