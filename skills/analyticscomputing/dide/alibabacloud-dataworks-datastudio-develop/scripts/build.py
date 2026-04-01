#!/usr/bin/env python3
"""Merge the 3-file node/workflow structure into API-ready FlowSpec JSON.

3-file structure:
  my_node/
  ├── my_node.spec.json        # FlowSpec definition (with ${spec.xxx} placeholders)
  ├── my_node.sql              # Code file
  └── dataworks.properties     # Actual values for placeholders

Merge logic:
  1. Read dataworks.properties -> parse into key=value dict
  2. Read spec.json -> replace all ${spec.xxx} and ${projectIdentifier} placeholders
  3. Read code file -> embed into spec.nodes[0].script.content
  4. Output the merged JSON (can be used directly as the Spec parameter for CreateNode API)

Usage:
  python build.py ./my_node              # Output to stdout
  python build.py ./my_node -o /tmp/spec.json  # Output to file
"""

import json
import re
import sys
from pathlib import Path

SKIP_EXTENSIONS = {'.json', '.properties'}


def parse_properties(filepath):
    """Parse dataworks.properties into a key=value dict."""
    props = {}
    for line in filepath.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        props[key.strip()] = value.strip()
    return props


def replace_placeholders(text, props):
    """Replace ${spec.xxx}, ${projectIdentifier} and other placeholders.

    Only replaces placeholders that have a corresponding key in properties; unmatched ones are kept as-is.
    """
    def replacer(match):
        key = match.group(1)
        if key in props:
            return props[key]
        # Key in spec.xxx format
        if key.startswith('spec.') and key in props:
            return props[key]
        return match.group(0)  # Keep as-is

    return re.sub(r'\$\{([^}]+)\}', replacer, text)


def find_spec_file(node_dir):
    """Find the .spec.json file."""
    specs = list(node_dir.glob('*.spec.json'))
    if len(specs) == 1:
        return specs[0]
    if len(specs) == 0:
        print(f"Error: No .spec.json file found in {node_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"Error: Multiple .spec.json files found in {node_dir}: {[s.name for s in specs]}", file=sys.stderr)
    sys.exit(1)


def find_code_file(node_dir):
    """Find the code file (excluding .spec.json and .properties)."""
    for f in node_dir.iterdir():
        if f.is_file() and f.suffix not in SKIP_EXTENSIONS:
            return f
    return None


def build(node_dir):
    """Merge 3-file structure into complete FlowSpec JSON."""
    node_dir = Path(node_dir)

    if not node_dir.is_dir():
        print(f"Error: {node_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # 1. Read properties
    props_file = node_dir / 'dataworks.properties'
    props = parse_properties(props_file) if props_file.exists() else {}

    # 2. Read spec.json + replace placeholders
    spec_file = find_spec_file(node_dir)
    spec_text = spec_file.read_text(encoding='utf-8')
    spec_text = replace_placeholders(spec_text, props)
    spec = json.loads(spec_text)

    # 3. Find code file + embed into script.content
    code_file = find_code_file(node_dir)
    if code_file:
        code_content = code_file.read_text(encoding='utf-8')
        # Node: spec.nodes[0].script.content
        nodes = spec.get('spec', {}).get('nodes', [])
        if nodes:
            nodes[0].setdefault('script', {})['content'] = code_content
        # Workflows have no code file, skip

    return spec


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Merge 3-file structure into FlowSpec JSON')
    parser.add_argument('dir', help='Path to node or workflow directory')
    parser.add_argument('-o', '--output', help='Output file path (default: stdout)')
    args = parser.parse_args()

    result = build(args.dir)
    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
