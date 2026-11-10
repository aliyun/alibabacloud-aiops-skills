#!/usr/bin/env bash
# Local dependencies only: this script makes no cloud API requests.
set -euo pipefail

check_only=false
case "${1:-}" in
    "") ;;
    --check-only) check_only=true ;;
    --help|-h)
        printf 'Usage: bash prepare_apsaradb_agent.sh [--check-only]\n'
        printf 'Verify credentials, CLI >= 3.5.0 and jq; prepare the official DAS plugin.\n'
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
read_cli_version() {
    cli_version=$(aliyun version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1) || true
    [[ "$cli_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}
cli_version_supported() {
    local major minor patch
    IFS=. read -r major minor patch <<<"$cli_version"
    ((10#$major > 3 || (10#$major == 3 && 10#$minor >= 5)))
}
if ! read_cli_version; then
    printf 'Error: cannot determine the installed CLI version.\n' >&2
    exit 1
fi
if ! cli_version_supported; then
    if [[ "$check_only" == true ]]; then
        printf 'Error: CLI >= 3.5.0 is required; found %s. Run setup without --check-only to attempt an upgrade.\n' "$cli_version" >&2
        exit 1
    fi
    printf '[Setup] CLI %s is below 3.5.0; attempting aliyun upgrade --yes.\n' "$cli_version"
    # Use the official self-update through PATH; do not bypass platform wrappers.
    # No sudo, identity changes, alternate binary or repeated upgrade attempts.
    if aliyun upgrade --yes </dev/null; then
        hash -r
    else
        upgrade_status=$?
        printf '[SetupFailed] CLI upgrade failed (exit %s). Ask the environment owner to update Aliyun CLI to >= 3.5.0; no agent request was sent.\n' "$upgrade_status" >&2
        exit 1
    fi
    if ! read_cli_version; then
        printf '[SetupFailed] Cannot verify CLI version after upgrade; no agent request was sent.\n' >&2
        exit 1
    fi
    if ! cli_version_supported; then
        printf '[SetupFailed] CLI upgrade completed but active CLI is still %s (< 3.5.0). Ask the environment owner to check the CLI installation or platform wrapper; no agent request was sent.\n' "$cli_version" >&2
        exit 1
    fi
    printf '[Setup] CLI upgrade verified: %s.\n' "$cli_version"
fi
# Probe local plugin validation only. --cli-dry-run never sends an agent request.
# Keep SOURCE canonical for operation policy; WIRE_SOURCE is transport-only.
resolve_wire_source() {
    local canonical="$1" alias=""
    local probe_args=(das get-yao-chi-agent --query 'Source compatibility check'
        --extra-info '{"mode":"readonly"}' --cli-dry-run
        --endpoint das.cn-shanghai.aliyuncs.com)
    WIRE_SOURCE="$canonical"
    SOURCE_PROBE_ERROR=""
    if SOURCE_PROBE_ERROR=$(aliyun "${probe_args[@]}" --source "$canonical" 2>&1); then
        return 0
    fi
    # Only a local source-enum rejection permits an alias probe, never a network
    # error, credential error or any response from a live request.
    if ! printf '%s' "$SOURCE_PROBE_ERROR" | jq -e --arg source "$canonical" '
        (.message // "") | contains("--source value \"" + $source + "\" is not allowed")
    ' >/dev/null 2>&1; then
        return 1
    fi
    case "$canonical" in
        yaochi-console) alias=yaochi ;;
        polardb-console) alias=polardb ;;
        tair-console) alias=tair ;;
        mongodb-console) alias=mongodb ;;
        lindorm-console) alias=lindorm ;;
        polarx-console) alias=polarx ;;
        dbs-console) alias=dbs ;;
        *) return 1 ;;
    esac
    if SOURCE_PROBE_ERROR=$(aliyun "${probe_args[@]}" --source "$alias" 2>&1); then
        WIRE_SOURCE="$alias"
        return 0
    fi
    return 1
}

das_ready() {
    aliyun das get-yao-chi-agent --help >/dev/null 2>&1 &&
        aliyun das create-yao-chi-agent-confirm --help >/dev/null 2>&1
}
if [[ "$check_only" == false ]]; then
    # Official skill-creator prerequisites. Never set identity/secret/UA configuration.
    aliyun configure set --auto-plugin-install true </dev/null
    aliyun plugin update </dev/null
    if ! das_ready; then
        aliyun plugin install --names aliyun-cli-das </dev/null
    fi
fi
if ! das_ready; then
    printf 'Error: DAS query or confirmation command is unavailable; run the setup script before any agent query.\n' >&2
    exit 1
fi
for route in yaochi-console polardb-console tair-console; do
    if ! resolve_wire_source "$route"; then
        printf '[SetupFailed] DAS plugin cannot validate source route %s locally. Inspect aliyun das get-yao-chi-agent --help-search source; no agent request was sent.\n' "$route" >&2
        exit 1
    fi
    printf '[SourceReady] %s -> %s (local dry-run).\n' "$route" "$WIRE_SOURCE"
done
case "${ALIBABA_CLOUD_CLI_MOCK:-false}" in
    true|TRUE|1) printf '[ExecutionMode] platform-mock; results are evaluation evidence, not live API verification.\n' ;;
    *) printf '[ExecutionMode] no CLI mock flag detected; live results still require API evidence.\n' ;;
esac
printf '[Ready] CLI %s, valid profile, jq and DAS plugin verified.\n' "$cli_version"
