#!/bin/bash
# Verify the Aliyun CLI `cs` (Container Service) plugin is installed and the
# CLI version is >= 3.3.3. Exits 0 when ready, 1 when something needs fixing.
#
# Usage:
#   ./check-cs-plugin.sh
#
# This script is ACK-specific by design. For other plugins, install directly
# with `aliyun plugin install --names <name>`.

set -e

MIN_CLI=3.3.3

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<EOF
Usage: $0
Verify the aliyun CLI (>= $MIN_CLI) and cs plugin are installed.

Exits 0 when both are ready; exits 1 with fix instructions otherwise.
No arguments. ACK-specific by design — for other plugins use
'aliyun plugin install --names <name>'.
EOF
    exit 0
fi

if ! command -v aliyun >/dev/null 2>&1; then
    echo "✗ aliyun CLI not found in PATH" >&2
    echo "  Install: /bin/bash -c \"\$(curl -fsSL https://aliyuncli.alicdn.com/setup.sh)\"" >&2
    exit 1
fi

CLI_VER=$(aliyun version 2>/dev/null | head -1 | awk '{print $NF}')
if [ -z "$CLI_VER" ]; then
    echo "✗ Could not parse 'aliyun version' output" >&2
    exit 1
fi

# Compare versions: lowest of [MIN_CLI, CLI_VER] should equal MIN_CLI
LOWEST=$(printf '%s\n%s\n' "$MIN_CLI" "$CLI_VER" | sort -V | head -1)
if [ "$LOWEST" != "$MIN_CLI" ]; then
    echo "✗ aliyun CLI $CLI_VER is older than required $MIN_CLI" >&2
    echo "  Upgrade: /bin/bash -c \"\$(curl -fsSL https://aliyuncli.alicdn.com/setup.sh)\"" >&2
    exit 1
fi
echo "✓ aliyun CLI $CLI_VER (>= $MIN_CLI)"

if aliyun plugin list 2>/dev/null | grep -q "aliyun-cli-cs"; then
    PLUGIN_VER=$(aliyun plugin list 2>/dev/null | awk '/aliyun-cli-cs/ {print $2}')
    echo "✓ cs plugin installed (version $PLUGIN_VER)"
    exit 0
else
    echo "✗ cs plugin not installed" >&2
    echo "  Install: aliyun plugin install --names cs" >&2
    echo "  Or run:  ./install-cs-plugin.sh" >&2
    exit 1
fi
