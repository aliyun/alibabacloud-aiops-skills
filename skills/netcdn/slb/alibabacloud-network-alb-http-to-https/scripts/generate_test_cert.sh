#!/usr/bin/env bash
# Generate a self-signed test certificate using openssl.
# Usage: bash generate_test_cert.sh --domain test.example.com [--days 365] [--out-dir /tmp/certs]

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: generate_test_cert.sh --domain DOMAIN [OPTIONS]

Generate a self-signed SSL certificate for testing purposes.
Outputs cert.pem and key.pem to the specified directory.

Required:
  --domain      Domain name for the certificate (e.g. test.example.com)

Optional:
  --days        Certificate validity in days (default: 365)
  --out-dir     Output directory (default: /tmp/alb-test-certs)
  -h, --help    Show this help

Examples:
  bash generate_test_cert.sh --domain test.example.com
  bash generate_test_cert.sh --domain "*.example.com" --days 30
EOF
    exit 0
}

DOMAIN=""
DAYS=365
OUT_DIR="/tmp/alb-test-certs"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)    DOMAIN="$2"; shift 2 ;;
        --days)      DAYS="$2"; shift 2 ;;
        --out-dir)   OUT_DIR="$2"; shift 2 ;;
        -h|--help)   usage ;;
        *)           echo "Error: Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$DOMAIN" ]]; then
    echo "Error: --domain is required." >&2
    exit 1
fi

if ! command -v openssl &>/dev/null; then
    echo "Error: openssl is not installed." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

CERT_FILE="$OUT_DIR/cert.pem"
KEY_FILE="$OUT_DIR/key.pem"

echo "Generating self-signed certificate for $DOMAIN ..." >&2

openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days "$DAYS" \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN" \
    2>/dev/null

echo "Certificate generated:"
echo "  Domain:  $DOMAIN"
echo "  Valid:   $DAYS days"
echo "  Cert:    $CERT_FILE"
echo "  Key:     $KEY_FILE"
echo ""
echo "Next: upload with upload_cert.sh"
echo "  bash scripts/upload_cert.sh --name test-cert --cert-file $CERT_FILE --key-file $KEY_FILE"
