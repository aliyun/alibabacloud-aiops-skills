#!/usr/bin/env python3
"""Build a deterministic public Skill ZIP from runtime files only."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def build(root, output):
    root = root.resolve()
    version = json.loads((root / 'references/manifest.json').read_text())['version']
    files = [root / 'SKILL.md']
    for folder in ('scripts', 'references'):
        files += [path for path in (root / folder).rglob('*')
                  if '__pycache__' not in path.parts and (path.is_file() or path.is_symlink())]
    files.sort()
    for path in files:
        if path.is_symlink() or path.suffix not in ('.md', '.json', '.py', '.sh'):
            raise ValueError('Unexpected runtime file: ' + str(path.relative_to(root)))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as out, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            item = zipfile.ZipInfo('alibabacloud-apsaradb-agent/' + path.relative_to(root).as_posix(),
                                   date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = (0o100755 if path.suffix in ('.py', '.sh') else 0o100644) << 16
            archive.writestr(item, path.read_bytes())
    return {'version': version, 'archive': str(output.resolve()), 'files': len(files),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'bytes': output.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
