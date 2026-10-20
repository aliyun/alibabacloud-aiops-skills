"""Development-only validation of package identity and customer inventory.

Builders and release tests use this module; it is not shipped with the client.
"""
import json
from pathlib import Path, PurePosixPath
import re
from openagent_client.common import ClientError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'assets/release.json'
LEGACY_MANIFEST = 'release.json'
CANONICAL_NAME = 'alibabacloud-openagent-chat'


def _valid(condition):
    if not condition:
        raise ValueError()


def validate_metadata(metadata):
    """Validate package identity and inventory without invoking any network API."""
    try:
        _valid(isinstance(metadata, dict))
        _valid(metadata['name'] == CANONICAL_NAME)
        _valid(isinstance(metadata['version'], str) and re.fullmatch(
            r'(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})', metadata['version']))
        _valid(isinstance(metadata['api_version'], str) and metadata['api_version'])
        _valid(type(metadata['compatibility']) is int and metadata['compatibility'] >= 0)
        _valid(metadata.get('distribution', 'production') in ('production', 'stable-pre'))
        _valid(isinstance(metadata['files'], dict) and bool(metadata['files']))
        for name, checksum in metadata['files'].items():
            _valid(isinstance(name, str))
            path = PurePosixPath(name)
            _valid(name and not path.is_absolute() and '..' not in path.parts and str(path) == name)
            _valid('\\' not in name and ':' not in name and name not in (MANIFEST, LEGACY_MANIFEST))
            _valid(isinstance(checksum, str) and re.fullmatch(r'[0-9a-f]{64}', checksum))
        return metadata
    except (KeyError, TypeError, ValueError):
        raise ClientError('InvalidRelease', 'The release metadata is invalid.') from None


def manifest_path(root=ROOT, allow_legacy=False):
    root = Path(root)
    current, legacy = root / MANIFEST, root / LEGACY_MANIFEST
    if current.is_symlink() or legacy.is_symlink() or (current.exists() and legacy.exists()):
        raise ClientError('InvalidRelease', 'The release metadata layout is ambiguous or unsafe.')
    if current.exists():
        return current
    # Reading historical metadata is useful to maintenance tools. It does not
    # enable automatic migration, download, or replacement of an installed skill.
    if allow_legacy and legacy.exists():
        return legacy
    raise ClientError('InvalidRelease', 'The installed release metadata is missing.')


def read_release(root=ROOT, allow_legacy=False):
    try:
        path = manifest_path(root, allow_legacy)
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Metadata size limit')
        return validate_metadata(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):
        raise ClientError('InvalidRelease', 'The installed release metadata could not be read.') from None
