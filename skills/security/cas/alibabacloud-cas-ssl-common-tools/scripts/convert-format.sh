#!/bin/bash
# convert-format.sh — Convert between PEM/PFX/JKS/DER certificate formats
# Dependencies: openssl (required), keytool from JDK/JRE (required for JKS operations)
# Usage: ./convert-format.sh <command> [options]
#
# Commands:
#   pem-to-pfx  <cert.pem> <key.pem> <output.pfx> [chain.pem] [password]
#   pfx-to-pem  <input.pfx> <output_prefix> [password]
#   pem-to-jks  <cert.pem> <key.pem> <output.jks> [alias] [password]
#   jks-to-pem  <input.jks> <output_prefix> [jks_password] [pem_password]
#   pem-to-der  <cert.pem> <output.der>
#   der-to-pem  <input.der> <output.pem>
#   pfx-to-jks  <input.pfx> <output.jks> [pfx_password] [jks_password] [alias]
set -euo pipefail

# Cleanup handler for temp files
_TMP_FILES=()
cleanup() { rm -f "${_TMP_FILES[@]}" 2>/dev/null || true; }
trap cleanup EXIT
_mktemp() { local f; f=$(mktemp "$@"); _TMP_FILES+=("$f"); echo "$f"; }

CMD="${1:?Usage: convert-format.sh <command> [options]}"
shift

case "$CMD" in
  pem-to-pfx)
    CERT="${1:?cert.pem required}"; KEY="${2:?key.pem required}"
    OUTPUT="${3:?output.pfx required}"; CHAIN="${4:-}"; PASSWORD="${5:-changeit}"
    ARGS=(-export -out "$OUTPUT" -inkey "$KEY" -in "$CERT" -passout "pass:$PASSWORD")
    [ -n "$CHAIN" ] && ARGS+=(-certfile "$CHAIN")
    openssl pkcs12 "${ARGS[@]}"
    echo "PFX created: $OUTPUT"
    ;;

  pfx-to-pem)
    INPUT="${1:?input.pfx required}"; PREFIX="${2:?output_prefix required}"; PASSWORD="${3:-}"
    openssl pkcs12 -in "$INPUT" -nokeys -out "${PREFIX}.crt" -passin "pass:$PASSWORD"
    openssl pkcs12 -in "$INPUT" -nocerts -nodes -out "${PREFIX}.key" -passin "pass:$PASSWORD"
    echo "Extracted: ${PREFIX}.crt + ${PREFIX}.key"
    ;;

  pem-to-jks)
    CERT="${1:?cert.pem required}"; KEY="${2:?key.pem required}"
    OUTPUT="${3:?output.jks required}"; ALIAS="${4:-myalias}"; PASSWORD="${5:-changeit}"
    TMP_PFX=$(_mktemp /tmp/cert-XXXXXX.pfx)
    openssl pkcs12 -export -in "$CERT" -inkey "$KEY" -out "$TMP_PFX" -name "$ALIAS" -passout "pass:$PASSWORD"
    keytool -importkeystore -srckeystore "$TMP_PFX" -srcstoretype PKCS12 -srcstorepass "$PASSWORD" \
      -destkeystore "$OUTPUT" -deststoretype JKS -deststorepass "$PASSWORD" -alias "$ALIAS"
    echo "JKS created: $OUTPUT (alias=$ALIAS)"
    ;;

  jks-to-pem)
    INPUT="${1:?input.jks required}"; PREFIX="${2:?output_prefix required}"
    JKS_PASS="${3:-changeit}"; PEM_PASS="${4:-changeit}"
    TMP_PFX=$(_mktemp /tmp/cert-XXXXXX.pfx)
    keytool -importkeystore -srckeystore "$INPUT" -srcstoretype JKS -srcstorepass "$JKS_PASS" \
      -destkeystore "$TMP_PFX" -deststoretype PKCS12 -deststorepass "$PEM_PASS"
    openssl pkcs12 -in "$TMP_PFX" -nokeys -out "${PREFIX}.crt" -passin "pass:$PEM_PASS"
    openssl pkcs12 -in "$TMP_PFX" -nocerts -nodes -out "${PREFIX}.key" -passin "pass:$PEM_PASS"
    echo "Extracted: ${PREFIX}.crt + ${PREFIX}.key"
    ;;

  pem-to-der)
    INPUT="${1:?cert.pem required}"; OUTPUT="${2:?output.der required}"
    openssl x509 -in "$INPUT" -outform DER -out "$OUTPUT"
    echo "DER created: $OUTPUT"
    ;;

  der-to-pem)
    INPUT="${1:?input.der required}"; OUTPUT="${2:?output.pem required}"
    openssl x509 -in "$INPUT" -inform DER -out "$OUTPUT"
    echo "PEM created: $OUTPUT"
    ;;

  pfx-to-jks)
    INPUT="${1:?input.pfx required}"; OUTPUT="${2:?output.jks required}"
    PFX_PASS="${3:-}"; JKS_PASS="${4:-changeit}"; ALIAS="${5:-myalias}"
    TMP_PFX=$(_mktemp /tmp/cert-XXXXXX.pfx)
    # Re-export PFX to ensure clean state
    openssl pkcs12 -in "$INPUT" -passin "pass:$PFX_PASS" | openssl pkcs12 -export -out "$TMP_PFX" -passout "pass:$JKS_PASS" -name "$ALIAS"
    keytool -importkeystore -srckeystore "$TMP_PFX" -srcstoretype PKCS12 -srcstorepass "$JKS_PASS" \
      -destkeystore "$OUTPUT" -deststoretype JKS -deststorepass "$JKS_PASS" -alias "$ALIAS"
    echo "JKS created: $OUTPUT"
    ;;

  *)
    echo "Unknown command: $CMD"
    echo "Available: pem-to-pfx, pfx-to-pem, pem-to-jks, jks-to-pem, pem-to-der, der-to-pem, pfx-to-jks"
    exit 1
    ;;
esac
