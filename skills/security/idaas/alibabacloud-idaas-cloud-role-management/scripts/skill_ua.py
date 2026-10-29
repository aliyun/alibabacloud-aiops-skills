"""Manifest-derived user agent. Does not resolve credentials or call cloud APIs."""
import json
import os
from pathlib import Path
import re
import uuid

MANIFEST_PATH = Path(__file__).resolve().parents[1] / 'references' / 'manifest.json'
SKILL_NAME = 'alibabacloud-idaas-cloud-role-management'


def user_agent(session=None):
    version = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))['version']
    if not isinstance(version, str) or not re.fullmatch(
            r'\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?', version):
        raise ValueError('Invalid manifest version; refusing cloud calls')
    session = session or os.environ.get('SKILL_SESSION_ID') or uuid.uuid4().hex
    if not re.fullmatch(r'[0-9a-f]{32}', session):
        raise ValueError('Session ID must be 32 lowercase hexadecimal characters')
    return f'AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session} skill-version/{version}'


if __name__ == '__main__':
    print(user_agent())
