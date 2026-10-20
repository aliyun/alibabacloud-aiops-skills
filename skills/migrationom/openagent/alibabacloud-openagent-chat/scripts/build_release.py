#!/usr/bin/env python3
"""Generate the customer inventory and optionally a local install directory.

No upload or publication is performed. Development files are never copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from release_metadata import ROOT, MANIFEST, read_release

# Explicit runtime inventory: adding a client resource requires updating this list.
CLIENT_MODULES = (
    '__init__', 'cli', 'common', 'concurrency', 'contract', 'credentials',
    'presentation', 'settings', 'stream', 'transport',
    'validation', 'workflows',
)
REFERENCES = ('setup', 'tasks', 'ram-policies')
FILES = (
    'SKILL.md', 'scripts/bootstrap.py', 'scripts/openagent.py',
    'assets/requirements.txt',
    *(f'references/{name}.md' for name in REFERENCES),
    *(f'scripts/openagent_client/{name}.py' for name in CLIENT_MODULES),
)


def build(output=None):
    metadata = read_release(ROOT, allow_legacy=False)
    if output is not None:
        output = Path(output).resolve()
        if output == ROOT or output.is_relative_to(ROOT) or ROOT.is_relative_to(output):
            raise ValueError('The customer directory must be outside the source tree.')
        if output.exists():
            raise ValueError('The customer directory must not already exist.')
    contents = {}
    for name in FILES:
        path = ROOT / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != ROOT.parent):
            raise ValueError('Customer resources must not be symbolic links.')
        contents[name] = path.read_bytes()
    metadata['files'] = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(contents.items())}
    encoded = (json.dumps(metadata, indent=2) + '\n').encode()
    (ROOT / MANIFEST).write_bytes(encoded)
    if output is not None:
        output.mkdir(parents=True)
        for name, content in {**contents, MANIFEST: encoded}.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            shutil.copymode(ROOT / name, path)
    return {'version': metadata['version'], 'files': len(contents), 'output': str(output) if output else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Create a fresh local customer directory outside the source tree.')
    args = parser.parse_args()
    print(json.dumps(build(args.output)))
