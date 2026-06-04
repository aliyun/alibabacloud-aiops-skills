#!/bin/bash
# Install or update the Aliyun CLI `cs` (Container Service) plugin.
# Non-interactive: idempotent install; pass --update to refresh if already installed.
#
# Usage:
#   ./install-cs-plugin.sh             # install if missing; no-op if already installed
#   ./install-cs-plugin.sh --update    # always update to latest (install if missing)
#
# This script is ACK-specific by design. For other plugins, run
#   aliyun plugin install --names <name>
# directly.

set -e

UPDATE_FLAG="${1:-}"

if [ "$UPDATE_FLAG" = "--help" ] || [ "$UPDATE_FLAG" = "-h" ]; then
    cat <<EOF
Usage: $0 [--update]
Install or update the aliyun cs (Container Service) plugin. Non-interactive.

Options:
  --update   Always update to latest (install if missing).
  (no args)  Install if missing; no-op if already installed.

ACK-specific by design — for other plugins run
'aliyun plugin install --names <name>' directly.
EOF
    exit 0
fi

if ! command -v aliyun >/dev/null 2>&1; then
    echo "✗ aliyun CLI not found. Install it first:" >&2
    echo "  /bin/bash -c \"\$(curl -fsSL https://aliyuncli.alicdn.com/setup.sh)\"" >&2
    exit 1
fi

if aliyun plugin list 2>/dev/null | grep -q "aliyun-cli-cs"; then
    PLUGIN_VER=$(aliyun plugin list 2>/dev/null | awk '/aliyun-cli-cs/ {print $2}')
    if [ "$UPDATE_FLAG" = "--update" ]; then
        echo "cs plugin already installed (version $PLUGIN_VER) — updating..."
        aliyun plugin update --name cs
        NEW_VER=$(aliyun plugin list 2>/dev/null | awk '/aliyun-cli-cs/ {print $2}')
        echo "✓ Updated to $NEW_VER"
    else
        echo "✓ cs plugin already installed (version $PLUGIN_VER)"
        echo "  Pass --update to refresh to the latest version."
    fi
else
    echo "Installing cs plugin..."
    aliyun plugin install --names cs
    PLUGIN_VER=$(aliyun plugin list 2>/dev/null | awk '/aliyun-cli-cs/ {print $2}')
    echo "✓ cs plugin installed (version $PLUGIN_VER)"
fi

echo
echo "Next: verify auth + plugin work end-to-end with"
echo "  aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou"
