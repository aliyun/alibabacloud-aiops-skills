#!/bin/bash
# modulus-check.sh — Compare modulus of key, certificate, and CSR files
# Dependencies: openssl (required)
# Usage: ./modulus-check.sh <type> <file1> [file2]
#
# Types:
#   key-cert   <key.pem> <cert.pem>     — Check if private key matches certificate
#   key-csr    <key.pem> <csr.pem>      — Check if private key matches CSR
#   cert-csr   <cert.pem> <csr.pem>     — Check if certificate matches CSR
#   all        <key.pem> <cert.pem> <csr.pem> — Check all three
set -euo pipefail

TYPE="${1:?Usage: modulus-check.sh <key-cert|key-csr|cert-csr|all> <file1> <file2> [file3]}"
shift

get_modulus_md5() {
  local FILE="$1" FILETYPE="$2" RAW=""
  case "$FILETYPE" in
    key)
      # Try RSA modulus first; fall back to ECC public key hash
      RAW=$(openssl rsa -noout -modulus -in "$FILE" 2>/dev/null || true)
      if [ -z "$RAW" ] || echo "$RAW" | grep -q "Wrong Algorithm"; then
        # ECC key: extract public key for comparison
        RAW=$(openssl req -new -x509 -key "$FILE" -subj "/CN=__modulus_check__" -days 1 2>/dev/null | openssl x509 -pubkey -noout 2>/dev/null || true)
      fi
      ;;
    cert)
      RAW=$(openssl x509 -noout -modulus -in "$FILE" 2>/dev/null || true)
      if [ -z "$RAW" ] || echo "$RAW" | grep -q "Wrong Algorithm"; then
        # ECC cert: compare public key instead
        RAW=$(openssl x509 -in "$FILE" -pubkey -noout 2>/dev/null || true)
      fi
      ;;
    csr)
      RAW=$(openssl req -noout -modulus -in "$FILE" 2>/dev/null || true)
      if [ -z "$RAW" ] || echo "$RAW" | grep -q "Wrong Algorithm"; then
        # ECC CSR: compare public key instead
        RAW=$(openssl req -in "$FILE" -pubkey -noout 2>/dev/null || true)
      fi
      ;;
    *)    echo "ERROR: Unknown type $FILETYPE"; exit 1 ;;
  esac
  if [ -z "$RAW" ]; then
    echo "ERROR: Could not extract modulus or public key from $FILE"
    exit 1
  fi
  echo "$RAW" | openssl md5
}

compare() {
  local LABEL1="$1" FILE1="$2" TYPE1="$3"
  local LABEL2="$4" FILE2="$5" TYPE2="$6"
  local MD5_1 MD5_2
  MD5_1=$(get_modulus_md5 "$FILE1" "$TYPE1")
  MD5_2=$(get_modulus_md5 "$FILE2" "$TYPE2")
  printf "%-12s %s  %s\n" "$LABEL1:" "$MD5_1" "$FILE1"
  printf "%-12s %s  %s\n" "$LABEL2:" "$MD5_2" "$FILE2"
  if [ "$MD5_1" = "$MD5_2" ]; then
    echo "Result: MATCH"
    return 0
  else
    echo "Result: MISMATCH"
    return 1
  fi
}

case "$TYPE" in
  key-cert)
    KEY="${1:?key.pem required}"; CERT="${2:?cert.pem required}"
    compare "Key" "$KEY" key "Certificate" "$CERT" cert
    ;;
  key-csr)
    KEY="${1:?key.pem required}"; CSR="${2:?csr.pem required}"
    compare "Key" "$KEY" key "CSR" "$CSR" csr
    ;;
  cert-csr)
    CERT="${1:?cert.pem required}"; CSR="${2:?csr.pem required}"
    compare "Certificate" "$CERT" cert "CSR" "$CSR" csr
    ;;
  all)
    KEY="${1:?key.pem required}"; CERT="${2:?cert.pem required}"; CSR="${3:?csr.pem required}"
    echo "=== Key vs Certificate ==="
    compare "Key" "$KEY" key "Certificate" "$CERT" cert || true
    echo ""
    echo "=== Key vs CSR ==="
    compare "Key" "$KEY" key "CSR" "$CSR" csr || true
    echo ""
    echo "=== Certificate vs CSR ==="
    compare "Certificate" "$CERT" cert "CSR" "$CSR" csr || true
    ;;
  *)
    echo "Unknown type: $TYPE"
    echo "Available: key-cert, key-csr, cert-csr, all"
    exit 1
    ;;
esac
