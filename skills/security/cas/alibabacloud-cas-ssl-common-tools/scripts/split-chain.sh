#!/bin/bash
# split-chain.sh — Split fullchain PEM into server cert + intermediate chain
# Dependencies: openssl (required)
# Usage: ./split-chain.sh <input_fullchain.pem> <output_dir>
set -euo pipefail

INPUT="${1:?Usage: split-chain.sh <input.pem> <output_dir>}"
OUTPUT_DIR="${2:-.}"

# Safety: reject empty or root output directory before any write/delete operation
if [ -z "$OUTPUT_DIR" ] || [ "$OUTPUT_DIR" = "/" ]; then
  echo "ERROR: Unsafe output directory: '$OUTPUT_DIR'"
  exit 1
fi
mkdir -p "$OUTPUT_DIR"

# Count certificates in chain
CERT_COUNT=$(grep -c 'BEGIN CERTIFICATE' "$INPUT" 2>/dev/null || echo 0)

if [ "$CERT_COUNT" -eq 0 ]; then
  echo "ERROR: No certificates found in $INPUT"
  exit 1
fi

# Split each certificate
awk 'BEGIN{n=0} /-----BEGIN CERTIFICATE-----/{n++; out="'"$OUTPUT_DIR"'/cert" n ".pem"} {print > out}' "$INPUT"

# First cert is server certificate
mv "$OUTPUT_DIR/cert1.pem" "$OUTPUT_DIR/server_only.pem"

# Remaining certs are intermediate chain (skip cert1)
if [ "$CERT_COUNT" -gt 1 ]; then
  # Dynamically build chain from cert2 to certN
  for i in $(seq 2 "$CERT_COUNT"); do
    cat "$OUTPUT_DIR/cert${i}.pem"
  done > "$OUTPUT_DIR/chain.pem"
else
  touch "$OUTPUT_DIR/chain.pem"
fi

# Clean up only the intermediate files created by this run (cert1 was renamed above)
for i in $(seq 2 "$CERT_COUNT"); do
  rm -f "$OUTPUT_DIR/cert${i}.pem"
done

# Also create fullchain (server + intermediate)
cat "$OUTPUT_DIR/server_only.pem" "$OUTPUT_DIR/chain.pem" > "$OUTPUT_DIR/fullchain.pem"

echo "Certificates found: $CERT_COUNT"
echo "  server_only.pem — server certificate"
echo "  chain.pem       — intermediate chain ($((CERT_COUNT - 1)) certs)"
echo "  fullchain.pem   — server + intermediate"

# Verify chain
echo ""
echo "Chain verification:"
openssl verify -CAfile "$OUTPUT_DIR/chain.pem" "$OUTPUT_DIR/server_only.pem" 2>&1 || echo "(chain verification failed — check intermediate completeness)"
