"""Check the public registry; apply an update only after explicit user approval."""
import argparse
from datetime import datetime
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import tempfile
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from user_agent import create_user_agent

NAME = 'alibabacloud-bailian-managed-agent'
METADATA_URL = f'https://skills.aliyun.com/api/public/skills/{NAME}'
DOWNLOAD_URL = METADATA_URL + '/download'
ROOT = Path(__file__).resolve().parents[1]
MAX_ZIP = 32 * 1024 * 1024
MAX_UNPACKED = 128 * 1024 * 1024


def description_version(content):
    """Read this skill's description without executing YAML constructors or body text."""
    match = re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|$)', content, re.S)
    if not match:
        raise ValueError('Missing SKILL.md frontmatter')
    frontmatter = match.group(1)
    name = re.search(r'^name:\s*[\'\"]?([a-z0-9-]+)[\'\"]?\s*$', frontmatter, re.M)
    if not name or name.group(1) != NAME:
        raise ValueError('Skill name does not match the requested skill')
    description = re.search(r'^description:[^\n]*(?:\n[ \t]+[^\n]*)*', frontmatter, re.M)
    if not description:
        raise ValueError('Missing skill description')
    versions = set(re.findall(r'\bv[0-9]{8}\b', description.group()))
    if not versions:
        return None
    if len(versions) != 1:
        raise ValueError('Ambiguous description version')
    version = versions.pop()
    datetime.strptime(version, 'v%Y%m%d')
    return version


def installed_version(root):
    version = description_version((root / 'SKILL.md').read_text(encoding='utf-8'))
    manifest = json.loads((root / 'references/manifest.json').read_text(encoding='utf-8'))
    if not version or manifest.get('version') != version:
        raise ValueError('Local description and manifest must have the same vYYYYMMDD version')
    return version


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise ValueError('Refusing a non-HTTPS download redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, user_agent, limit):
    request = Request(url, headers={'User-Agent': user_agent})
    with build_opener(HTTPSRedirects()).open(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Registry response exceeds the size limit')
    return data


def unpack(payload, stage, expected_version):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = archive.infolist()
        if len(entries) > 5000 or sum(item.file_size for item in entries) > MAX_UNPACKED:
            raise ValueError('ZIP exceeds unpacking limits')
        seen = set()
        for item in entries:
            path = PurePosixPath(item.filename)
            kind = stat.S_IFMT(item.external_attr >> 16)
            if (path.is_absolute() or '..' in path.parts or '.git' in path.parts
                    or '\\' in item.filename or ':' in item.filename
                    or kind not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or path in seen):
                raise ValueError('Unsafe or duplicate ZIP entry')
            seen.add(path)
        for item in entries:
            target = stage / item.filename
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(item))
                if item.external_attr >> 16 & 0o111:
                    target.chmod(0o755)
    if (stage / 'SKILL.md').is_file():
        candidate = stage
    else:
        children = list(stage.iterdir())
        if len(children) != 1 or not children[0].is_dir():
            raise ValueError('ZIP must contain one skill at its root or in one directory')
        candidate = children[0]
    if installed_version(candidate) != expected_version:
        raise ValueError('Downloaded package version does not match registry metadata')
    return candidate


def install(root, payload, current, latest):
    # Keep backups/staging in a hidden folder separate from the active installation.
    storage = root.parent / '.skill-update-backups'
    storage.mkdir(exist_ok=True)
    if storage.is_symlink():
        raise ValueError('Backup directory must not be a symlink')
    lock = storage / (NAME + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        with tempfile.TemporaryDirectory(prefix='stage-', dir=storage) as temp:
            candidate = unpack(payload, Path(temp), latest)
            if installed_version(root) != current:
                raise ValueError('Installed version changed during the update; check again next invocation')
            backup = storage / f'{NAME}-{current}-{secrets.token_hex(4)}'
            root.rename(backup)
            try:
                candidate.rename(root)
            except OSError:
                try:
                    backup.rename(root)
                except OSError as error:
                    raise RuntimeError(f'Restore the previous installation from {backup}') from error
                raise
        return backup
    finally:
        lock.unlink()


def check(root, apply=False, user_agent=None):
    root = Path(root).resolve()
    current = installed_version(root)
    user_agent = user_agent or create_user_agent(root)
    if not re.fullmatch(r'AlibabaCloud-Agent-Skills/' + re.escape(NAME)
                        + r'/[0-9a-f]{32} skill-version/' + re.escape(current), user_agent):
        raise ValueError('User-Agent must identify this skill, its current version, and a valid session ID')
    result = {'local_version': current, 'skill_root': str(root), 'user_agent': user_agent}
    metadata = json.loads(fetch(METADATA_URL, user_agent, 2 * 1024 * 1024))
    data = metadata.get('data') if isinstance(metadata, dict) else None
    if not isinstance(data, dict) or metadata.get('code') != 200 or data.get('skillName') != NAME:
        raise ValueError('Unexpected registry response or skill name')
    latest = description_version(data['content'])
    result['remote_version'] = latest
    if latest is None:
        return dict(result, status='version_unknown')
    if latest <= current:
        return dict(result, status='up_to_date' if latest == current else 'local_newer')
    if not apply:
        return dict(result, status='update_available',
                    message=f'当前 Skill 版本为 {current}，发现新版本 {latest}。是否更新？'
                            '暂不更新也可以继续当前任务，但 Skill 中的知识可能落后于最新版本。')
    if any((parent / '.git').exists() for parent in (root, *root.parents)):
        return dict(result, status='source_checkout')
    payload = fetch(DOWNLOAD_URL, user_agent, MAX_ZIP)
    backup = install(root, payload, current, latest)
    result['user_agent'] = user_agent.rsplit(' skill-version/', 1)[0] + ' skill-version/' + latest
    return dict(result, status='updated', installed_version=latest, backup_path=str(backup),
                restart_recommended=True,
                message='Skill 已更新；建议新建对话以刷新宿主缓存的 Skill 列表和 description。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='Install a strictly newer release only after explicit user approval; default is check-only')
    parser.add_argument('--user-agent', help='Reuse the initial check\'s user_agent for an approved update in the same invocation')
    args = parser.parse_args()
    user_agent = None
    try:
        user_agent = args.user_agent or create_user_agent(ROOT)
        result = check(ROOT, apply=args.apply, user_agent=user_agent)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile) as error:
        print(json.dumps({'status': 'error', 'message': str(error), 'user_agent': user_agent}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
