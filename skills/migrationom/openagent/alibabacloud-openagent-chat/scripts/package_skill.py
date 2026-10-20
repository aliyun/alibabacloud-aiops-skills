"""Build a local distribution from the release inventory only; never upload it."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile
from release_metadata import MANIFEST, read_release
from package_audit import BUILD_TARGETS, audit, profile_payloads


def package(root, output, target='production'):
    root, output = Path(root).resolve(), Path(output).resolve()
    metadata = read_release(root, allow_legacy=False)
    header = (root / 'SKILL.md').read_text().split('---\n', 2)[1]
    names = re.findall(r'^name: ([a-z0-9-]+)$', header, re.MULTILINE)
    if names != ['alibabacloud-openagent-chat']:
        raise ValueError('Expected the canonical skill identity')
    inventory = {}
    for name, expected in metadata['files'].items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or str(path) != name
                or '\\' in name or ':' in name
                or not (name == 'SKILL.md' or path.parts[0] in ('scripts', 'references', 'assets', 'agents'))):
            raise ValueError('Invalid distribution path: ' + name)
        source = root / name
        if any(p.is_symlink() for p in (source, *source.parents)):
            raise ValueError('Symbolic links are forbidden')
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Manifest hash mismatch: ' + name)
        inventory[name] = content
    inventory[MANIFEST] = (root / MANIFEST).read_bytes()
    inventory = profile_payloads(inventory, target)
    if output.is_relative_to(root) or output.exists():
        raise ValueError('Use a new output path outside the source tree')
    if target != 'production' and not output.name.endswith('-' + target + '.zip'):
        raise ValueError('Dedicated package filename must identify its target')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + output.name, suffix='.part', dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in sorted(inventory.items()):
                # Fixed timestamps and permissions make identical reviewed
                # sources produce identical customer archives on every host.
                entry = zipfile.ZipInfo(names[0] + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, content, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            expected = {names[0] + '/' + name for name in inventory}
            if set(archive.namelist()) != expected or len(archive.namelist()) != len(expected):
                raise ValueError('Archive inventory changed')
            audit({name[len(names[0]) + 1:]: archive.read(name) for name in archive.namelist()}, target)
        # The archive is complete and audited; publish without replacing a file
        # created by another builder after our initial existence check.
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', choices=BUILD_TARGETS, default='production')
    args = parser.parse_args()
    print(package(args.root, args.output, args.target))
