#!/bin/bash
# ga-discover-certificate.sh
# List CAS certificates usable by GA HTTPS listeners, with remaining validity and
# the GA certificate ID format (<CertificateId>-<region>).
#
# Usage:
#   bash scripts/ga-discover-certificate.sh                       # all valid certs
#   bash scripts/ga-discover-certificate.sh --domain example.com  # filter by domain
#   bash scripts/ga-discover-certificate.sh --region cn-shanghai  # non-default region
#   bash scripts/ga-discover-certificate.sh --show-size 100
#
# Requires: aliyun CLI, jq. Uses $GA_USER_AGENT when it is already exported.

set -euo pipefail

DOMAIN=""
REGION="${GA_CERT_REGION:-cn-hangzhou}"
SHOW_SIZE=50

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="${2:?--domain requires a value}"; shift 2 ;;
    --region) REGION="${2:?--region requires a value}"; shift 2 ;;
    --show-size) SHOW_SIZE="${2:?--show-size requires a value}"; shift 2 ;;
    *) echo "ERROR: unknown argument '$1' (supported: --domain, --region, --show-size)" >&2; exit 1 ;;
  esac
done

if ! command -v aliyun >/dev/null 2>&1; then
  echo "ERROR: aliyun CLI not found" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq not found" >&2
  exit 1
fi

UA_ARGS=()
if [ -n "${GA_USER_AGENT:-}" ]; then
  UA_ARGS=(--user-agent "$GA_USER_AGENT")
fi

# list-certificates returns every certificate visible in the region (uploaded and
# issued) and, unlike list-user-certificate-order, carries CertificateId and
# CertIdentifier (already in the GA-ready "<id>-<region>" form).
RAW=$(aliyun cas list-certificates \
  --region "$REGION" \
  --current-page 1 \
  --show-size "$SHOW_SIZE" \
  "${UA_ARGS[@]}")

NOW_MS=$(date +%s000)

echo "$RAW" | jq --argjson now "$NOW_MS" --arg domain "$DOMAIN" --arg region "$REGION" '
  [.CertificateList[]?
   | select(.NotAfter > $now)
   | select(($domain == "")
            or (((.CommonName // "") | contains($domain)))
            or (((.Domain // "") | contains($domain))))
   | {CertificateId, InstanceId, CertificateName, CommonName, CertificateStatus, NotAfter,
      RemainingDays: (((.NotAfter - $now) / 86400000) | floor),
      GaCertificateId: (.CertIdentifier // "\(.CertificateId)-\($region)")}]
  | sort_by(-.RemainingDays)'

echo "" >&2
echo "Use GaCertificateId with: aliyun ga create-listener ... --certificates Id=<GaCertificateId>" >&2
