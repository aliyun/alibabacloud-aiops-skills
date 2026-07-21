#!/usr/bin/env bash
# bss-purchase.sh — Wrapper for BSS (Billing) API calls.
# Uses the aliyun-cli-bssopenapi plugin in PLUGIN MODE (lowercase-hyphenated
# subcommands, e.g. `aliyun bssopenapi create-instance`), and wraps the
# operations behind a stable interface that constructs --parameter pairs internally.
#
# Usage:
#   bash scripts/bss-purchase.sh check-plugin --profile <p> --region <r>
#   bash scripts/bss-purchase.sh create-instance \
#     --profile <p> --region <r> \
#     --product-code <cas|cas_intl> --product-type <type> \
#     --period <months> --product-value <value> --merge <0|1> \
#     --cert-type <dv|ov|ev> \
#     [--full-spec <spec>] [--full-count <n>] \
#     [--wildcard-spec <spec>] [--wildcard-count <n>] \
#     [--auto-issue]
#   bash scripts/bss-purchase.sh get-order-detail --profile <p> --region <r> --order-id <id>
#
# Dependencies: bash (>=4.0), aliyun-cli (>=3.3.3), aliyun-cli-bssopenapi plugin

set -euo pipefail

# BSS PricingCycle value: 2 means the --period unit is MONTH
# (verified via `aliyun bssopenapi create-instance --help`).
PRICING_CYCLE="2"

UA="AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/${CERT_SESSION_ID:-unknown}"

usage() {
  echo "Usage: $0 <action> [options]"
  echo ""
  echo "Actions:"
  echo "  check-plugin      Verify BSS plugin is installed"
  echo "  create-instance   Purchase a certificate instance"
  echo "  get-order-detail  Query order details"
  exit 1
}

# Retry wrapper for transient errors (timeout, 5xx) on READ-ONLY operations.
# NEVER use this for paid/non-idempotent operations (e.g. create-instance):
# retrying a purchase can double-charge the user.
# Usage: retry_readonly_api <command> [args...]
retry_readonly_api() {
  local max_attempts=2
  local retry_delay=10
  local attempt=1
  while [ $attempt -le $max_attempts ]; do
    if "$@" 2>&1; then
      return 0
    fi
    if [ $attempt -lt $max_attempts ]; then
      echo "Attempt $attempt/$max_attempts failed, retrying in ${retry_delay}s..." >&2
      sleep $retry_delay
    fi
    attempt=$((attempt + 1))
  done
  echo "All $max_attempts attempts failed." >&2
  return 1
}

ACTION="${1:-}"
shift 2>/dev/null || true
[ -z "$ACTION" ] && usage

PROFILE=""
REGION=""
PRODUCT_CODE=""
PRODUCT_TYPE=""
PERIOD=""
PRODUCT_VALUE=""
MERGE="0"
CERT_TYPE=""
FULL_SPEC=""
FULL_COUNT=""
WILDCARD_SPEC=""
WILDCARD_COUNT=""
AUTO_ISSUE=false
ORDER_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --product-code) PRODUCT_CODE="$2"; shift 2 ;;
    --product-type) PRODUCT_TYPE="$2"; shift 2 ;;
    --period) PERIOD="$2"; shift 2 ;;
    --product-value) PRODUCT_VALUE="$2"; shift 2 ;;
    --merge) MERGE="$2"; shift 2 ;;
    --cert-type) CERT_TYPE="$2"; shift 2 ;;
    --full-spec) FULL_SPEC="$2"; shift 2 ;;
    --full-count) FULL_COUNT="$2"; shift 2 ;;
    --wildcard-spec) WILDCARD_SPEC="$2"; shift 2 ;;
    --wildcard-count) WILDCARD_COUNT="$2"; shift 2 ;;
    --auto-issue) AUTO_ISSUE=true; shift ;;
    --order-id) ORDER_ID="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

case "$ACTION" in
  check-plugin)
    [ -z "$PROFILE" ] && { echo "ERROR: --profile required"; exit 1; }
    [ -z "$REGION" ] && { echo "ERROR: --region required"; exit 1; }
    if retry_readonly_api aliyun bssopenapi query-product-list \
      --profile "$PROFILE" --region "$REGION" \
      --user-agent "$UA" --page-num 1 --page-size 1; then
      echo "BSS plugin is available."
    else
      echo "ERROR: BSS plugin check failed. Install with: aliyun plugin install --names aliyun-cli-bssopenapi" >&2
      exit 1
    fi
    ;;

  create-instance)
    [ -z "$PROFILE" ] && { echo "ERROR: --profile required"; exit 1; }
    [ -z "$REGION" ] && { echo "ERROR: --region required"; exit 1; }
    [ -z "$PRODUCT_CODE" ] && { echo "ERROR: --product-code required"; exit 1; }
    [ -z "$PRODUCT_TYPE" ] && { echo "ERROR: --product-type required"; exit 1; }
    [ -z "$PERIOD" ] && { echo "ERROR: --period required"; exit 1; }
    [ -z "$PRODUCT_VALUE" ] && { echo "ERROR: --product-value required"; exit 1; }
    [ -z "$CERT_TYPE" ] && { echo "ERROR: --cert-type required"; exit 1; }
    [[ "$PERIOD" =~ ^[0-9]+$ ]] || { echo "ERROR: --period must be a positive integer" >&2; exit 1; }

    CMD=(aliyun bssopenapi create-instance
      --profile "$PROFILE" --region "$REGION"
      --user-agent "$UA"
      --product-code "$PRODUCT_CODE" --product-type "$PRODUCT_TYPE"
      --subscription-type Subscription
      --period "$PERIOD" --pricing-cycle "$PRICING_CYCLE"
      --parameter Code=product Value="$PRODUCT_VALUE"
      --parameter Code=merge Value="$MERGE"
      --parameter Code=certdomain Value="$CERT_TYPE"
    )

    if [ -n "$FULL_SPEC" ]; then
      CMD+=(--parameter Code=fullSpec Value="$FULL_SPEC")
      CMD+=(--parameter Code=fullDomainCount Value="${FULL_COUNT:-1}")
    fi

    if [ -n "$WILDCARD_SPEC" ]; then
      CMD+=(--parameter Code=wildcardSpec Value="$WILDCARD_SPEC")
      CMD+=(--parameter Code=wildcardDomainCount Value="${WILDCARD_COUNT:-1}")
    fi

    if [ "$AUTO_ISSUE" = true ]; then
      CMD+=(--parameter Code=autoIssue Value=true)
    fi

    # NOTE: create-instance is a paid, non-idempotent operation — NEVER auto-retry.
    # A timeout does NOT mean the order failed; retrying may double-charge.
    echo "Executing: ${CMD[*]}"
    if ! "${CMD[@]}"; then
      echo "ERROR: create-instance failed or timed out. Do NOT blindly retry (may double-charge)." >&2
      echo "       First verify whether an order was already created via:" >&2
      echo "       bash scripts/bss-purchase.sh get-order-detail --profile $PROFILE --region $REGION --order-id <ORDER_ID>" >&2
      exit 1
    fi
    ;;

  get-order-detail)
    [ -z "$PROFILE" ] && { echo "ERROR: --profile required"; exit 1; }
    [ -z "$REGION" ] && { echo "ERROR: --region required"; exit 1; }
    [ -z "$ORDER_ID" ] && { echo "ERROR: --order-id required"; exit 1; }
    retry_readonly_api aliyun bssopenapi get-order-detail \
      --profile "$PROFILE" --region "$REGION" \
      --user-agent "$UA" \
      --order-id "$ORDER_ID"
    ;;

  *)
    echo "Unknown action: $ACTION"
    usage
    ;;
esac
