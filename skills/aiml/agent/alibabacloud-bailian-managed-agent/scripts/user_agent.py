"""Build this skill's per-run User-Agent without network or credentials."""
import json
import re
import secrets
from pathlib import Path


def create_user_agent(skill_root=None):
    root = Path(skill_root) if skill_root else Path(__file__).resolve().parents[1]
    frontmatter = root.joinpath('SKILL.md').read_text().split('---', 2)[1]
    name = re.search(r'^name:\s*([a-z0-9-]+)\s*$', frontmatter, re.M)
    if not name:
        raise ValueError('Missing skill frontmatter name')
    version = json.loads(root.joinpath('references/manifest.json').read_text()).get('version')
    if not isinstance(version, str) or not version.strip() or re.search(r'\s', version):
        raise ValueError('Manifest version must be a non-empty token')
    session_id = secrets.token_hex(16)
    return f'AlibabaCloud-Agent-Skills/{name.group(1)}/{session_id} skill-version/{version}'


if __name__ == '__main__':
    print(create_user_agent())
