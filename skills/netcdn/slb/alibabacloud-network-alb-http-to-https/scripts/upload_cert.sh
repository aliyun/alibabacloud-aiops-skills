#!/usr/bin/env bash
# Upload SSL certificate to Alibaba Cloud Certificate Management Service via aliyun CLI.
# Usage: bash upload_cert.sh --name my-cert --cert-file cert.pem --key-file key.pem

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: upload_cert.sh --name NAME --cert-file FILE --key-file FILE [OPTIONS]

Upload an SSL certificate (PEM format) to Alibaba Cloud Certificate Management Service.
Returns a CertificateId that can be used with create_listener.sh --cert-id.

Required:
  --name        Certificate name (unique within your account)
  --cert-file   Path to certificate PEM file
  --key-file    Path to private key PEM file

Optional:
  --json        Output raw JSON response
  --output      Write output to file
  -h, --help    Show this help

Examples:
  bash upload_cert.sh --name test-cert --cert-file /tmp/alb-test-certs/cert.pem --key-file /tmp/alb-test-certs/key.pem
EOF
    exit 0
}

NAME=""
CERT_FILE=""
KEY_FILE=""
JSON_OUTPUT=false
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)       NAME="$2"; shift 2 ;;
        --cert-file)  CERT_FILE="$2"; shift 2 ;;
        --key-file)   KEY_FILE="$2"; shift 2 ;;
        --json)       JSON_OUTPUT=true; shift ;;
        --output)     OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help)    usage ;;
        *)            echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

require_arg "--name" "$NAME"
require_arg "--cert-file" "$CERT_FILE"
require_arg "--key-file" "$KEY_FILE"

if [[ ! -f "$CERT_FILE" ]]; then
    echo "Error: Certificate file not found: $CERT_FILE" >&2
    exit 1
fi

if [[ ! -f "$KEY_FILE" ]]; then
    echo "Error: Key file not found: $KEY_FILE" >&2
    exit 1
fi

CERT_CONTENT=$(cat "$CERT_FILE")
KEY_CONTENT=$(cat "$KEY_FILE")

echo "Uploading certificate '$NAME' ..." >&2

RESULT=$(run_cli "Failed to upload certificate." \
    "${ALIYUN_CMD[@]}" cas upload-user-certificate \
    --name "$NAME" \
    --cert "$CERT_CONTENT" \
    --key "$KEY_CONTENT")

CERT_ID=$(printf '%s' "$RESULT" | json_get_field "CertId" "")

output_result() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        echo "$RESULT"
    else
        echo "Certificate uploaded successfully."
        echo "  Name:   $NAME"
        echo "  CertId: $CERT_ID"
        echo ""
        echo "Use this CertId with create_listener.sh:"
        echo "  bash scripts/create_listener.sh --cert-id $CERT_ID ..."
    fi
}

write_output "$OUTPUT_FILE" output_result
