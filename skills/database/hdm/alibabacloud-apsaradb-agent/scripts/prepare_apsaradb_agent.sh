#!/usr/bin/env bash
# Local dependencies only: this script makes no cloud API requests.
set -euo pipefail

check_only=false
case "${1:-}" in
    "") ;;
    --check-only) check_only=true ;;
    --help|-h)
        printf 'Usage: bash prepare_apsaradb_agent.sh [--check-only]\n'
        printf 'Verify credentials, CLI >= 3.3.3 and jq; prepare the official DAS plugin.\n'
        printf '%s\n' '--check-only verifies readiness without installing or changing configuration.'
        exit 0
        ;;
    *) printf 'Error: unsupported setup option.\n' >&2; exit 2 ;;
esac
if (($# > 1)); then
    printf 'Error: provide at most one setup option.\n' >&2
    exit 2
fi
for dependency in aliyun jq; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        printf 'Error: required local dependency is missing: %s\n' "$dependency" >&2
        exit 1
    fi
done

# Keep configure-list output internal; never print configuration or credential values.
if ! aliyun configure list 2>/dev/null | jq -Rse '
    split("\n") | any(.[];
        split("|") | map(gsub("^\\s+|\\s+$"; "")) |
        length >= 3 and (.[0] | endswith(" *")) and .[2] == "Valid")
' >/dev/null; then
    printf 'Error: selected credential profile is missing or invalid; configure it outside the agent session.\n' >&2
    exit 1
fi
cli_version=$(aliyun version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1) || true
if [[ ! "$cli_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Error: cannot determine the installed CLI version.\n' >&2
    exit 1
fi
IFS=. read -r major minor patch <<<"$cli_version"
if ((major < 3 || (major == 3 && minor < 3) || (major == 3 && minor == 3 && patch < 3))); then
    printf 'Error: CLI >= 3.3.3 is required; found %s.\n' "$cli_version" >&2
    exit 1
fi
if [[ "$check_only" == false ]]; then
    # Official skill-creator prerequisites. Never set identity/secret/UA configuration.
    aliyun configure set --auto-plugin-install true </dev/null
    aliyun plugin update </dev/null
    if ! aliyun das get-yao-chi-agent --help >/dev/null 2>&1; then
        aliyun plugin install --names aliyun-cli-das </dev/null
    fi
fi
if ! aliyun das get-yao-chi-agent --help >/dev/null 2>&1; then
    printf 'Error: DAS plugin is unavailable; run the setup script before any agent query.\n' >&2
    exit 1
fi
case "${ALIBABA_CLOUD_CLI_MOCK:-false}" in
    true|TRUE|1) printf '[ExecutionMode] platform-mock; results are evaluation evidence, not live API verification.\n' ;;
    *) printf '[ExecutionMode] no CLI mock flag detected; live results still require API evidence.\n' ;;
esac
printf '[Ready] CLI %s, valid profile, jq and DAS plugin verified.\n' "$cli_version"
