#!/usr/bin/env bash
# Update ALB listener attributes via aliyun CLI.
# Currently supports replacing the default certificate on HTTPS/QUIC listeners.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: update_listener.sh --region REGION --listener-id LSN_ID --cert-id CERT_ID [OPTIONS]

Update an ALB listener. Currently this script replaces the default certificate
on an HTTPS or QUIC listener and verifies the listener afterwards.

Required:
  --region        Region ID (e.g. cn-hangzhou)
  --listener-id   Listener ID (e.g. lsn-xxx)
  --cert-id       Certificate ID to bind as the default listener certificate

Options:
  --dry-run       Only precheck, do not actually update
  --json          Output raw JSON response from UpdateListenerAttribute
  --output        Write output to file
  -h, --help      Show this help

Examples:
  bash update_listener.sh --region cn-hangzhou --listener-id lsn-xxx --cert-id 12345678
  bash update_listener.sh --region cn-hangzhou --listener-id lsn-xxx --cert-id 12345678 --dry-run
EOF
    exit 0
}

REGION=""
LISTENER_ID=""
CERT_ID=""
DRY_RUN=false
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)       REGION="$2"; shift 2 ;;
        --listener-id)  LISTENER_ID="$2"; shift 2 ;;
        --cert-id)      CERT_ID="$2"; shift 2 ;;
        --dry-run)      DRY_RUN=true; shift ;;
        --json)         JSON_OUTPUT=true; shift ;;
        --output)       OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--region" "$REGION"
require_arg "--listener-id" "$LISTENER_ID"
require_arg "--cert-id" "$CERT_ID"
require_prefix "--listener-id" "$LISTENER_ID" "lsn-"

extract_default_cert_id() {
    python3 -c '
import json
import sys

data = json.load(sys.stdin)
certs = data.get("Certificates") or []

for cert in certs:
    if cert.get("IsDefault") is True:
        print(cert.get("CertificateId", ""))
        raise SystemExit(0)

if certs:
    print(certs[0].get("CertificateId", ""))
'
}

echo "Querying listener $LISTENER_ID ..." >&2
LISTENER_RESULT=$(run_cli "Failed to query listener $LISTENER_ID." \
    "${ALIYUN_CMD[@]}" alb get-listener-attribute \
    --region "$REGION" \
    --listener-id "$LISTENER_ID")

LISTENER_PROTOCOL=$(printf '%s' "$LISTENER_RESULT" | json_get_field "ListenerProtocol" "")
if [[ "$LISTENER_PROTOCOL" != "HTTPS" && "$LISTENER_PROTOCOL" != "QUIC" ]]; then
    echo "Error: certificate updates are only supported for HTTPS or QUIC listeners." >&2
    echo "       Listener $LISTENER_ID protocol is: ${LISTENER_PROTOCOL:-unknown}" >&2
    exit 1
fi

OLD_CERT_ID=$(printf '%s' "$LISTENER_RESULT" | normalize_json_output | extract_default_cert_id)

CMD=("${ALIYUN_CMD[@]}" alb update-listener-attribute
    --region "$REGION"
    --listener-id "$LISTENER_ID"
    --certificates "CertificateId=$CERT_ID")

if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run - would update listener certificate:"
    echo "  Listener: $LISTENER_ID"
    echo "  Protocol: $LISTENER_PROTOCOL"
    echo "  Current:  ${OLD_CERT_ID:-unknown}"
    echo "  Target:   $CERT_ID"

    if DRYRUN_OUTPUT=$(run_api_dry_run "${CMD[@]}" --dry-run true); then
        echo "$DRYRUN_OUTPUT"
        echo "API precheck passed."
    else
        echo "$DRYRUN_OUTPUT"
        echo "API precheck failed (see above)."
    fi
    exit 0
fi

echo "Updating listener $LISTENER_ID certificate to $CERT_ID ..." >&2
RESULT=$(run_cli "Failed to update listener certificate." "${CMD[@]}")

UPDATED_RESULT=""
UPDATED_CERT_ID=""
for attempt in {1..40}; do
    UPDATED_RESULT=$(run_cli "Failed to query listener $LISTENER_ID during wait." \
        "${ALIYUN_CMD[@]}" alb get-listener-attribute \
        --region "$REGION" \
        --listener-id "$LISTENER_ID")
    UPDATED_CERT_ID=$(printf '%s' "$UPDATED_RESULT" | normalize_json_output | extract_default_cert_id)

    if [[ "$UPDATED_CERT_ID" == "$CERT_ID" ]]; then
        break
    fi

    if (( attempt < 40 )); then
        sleep 3
    fi
done

if [[ "$UPDATED_CERT_ID" != "$CERT_ID" ]]; then
    echo "Error: listener $LISTENER_ID did not bind certificate $CERT_ID." >&2
    echo "       Current default certificate: ${UPDATED_CERT_ID:-unknown}" >&2
    exit 1
fi

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        echo "Listener certificate updated successfully."
        echo "  ListenerId: $LISTENER_ID"
        echo "  Protocol:   $LISTENER_PROTOCOL"
        echo "  OldCertId:  ${OLD_CERT_ID:-unknown}"
        echo "  NewCertId:  $CERT_ID"
    fi
}

write_output "$OUTPUT_FILE" output_result
