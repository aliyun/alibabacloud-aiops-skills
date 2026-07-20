#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -ne 1 ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 1.1.0"
  exit 1
fi

VERSION="$1"

if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Error: version must be semver (e.g. 1.1.0)"
  exit 1
fi

echo "==> Releasing v${VERSION}"

echo "$VERSION" > "$ROOT/VERSION"
echo "    Updated VERSION"

python3 -c "
import re, sys
p = '$ROOT/scripts/cli/pyproject.toml'
with open(p) as f: t = f.read()
t = re.sub(r'^version\s*=\s*\"[^\"]+\"', f'version = \"$VERSION\"', t, count=1, flags=re.MULTILINE)
with open(p, 'w') as f: f.write(t)
print(f'    Updated scripts/cli/pyproject.toml')
"

echo "==> All version files updated to ${VERSION}"
echo ""
echo "Next steps:"
echo "  git add VERSION scripts/cli/pyproject.toml"
echo "  git commit -m \"chore(release): v${VERSION}\""
echo "  git tag v${VERSION}"
echo "  git push && git push --tags"
