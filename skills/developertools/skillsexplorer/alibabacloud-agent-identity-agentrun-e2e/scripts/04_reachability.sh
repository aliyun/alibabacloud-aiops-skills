#!/usr/bin/env bash
# 04_reachability.sh — after the console deploy: construct the invocation
# endpoint and probe it. Expects RUNTIME_NAME in the state (set by the agent
# from the console page) or as an env override.
#
# Endpoint shape (field-verified):
#   https://<account>.agentrun-data.<region>.aliyuncs.com/agent-runtimes/
#   <runtime>/endpoints/Default/invocations/openai/v1/chat/completions
# NOTE: the bare .../invocations path 404s inside the app — the OpenAI path
# MUST follow it.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

load_e2e_env
ACCOUNT_ID="${ACCOUNT_ID:?run 00_detect_env.sh first}"
RUNTIME_NAME="${RUNTIME_NAME:-${E2E_RUNTIME_NAME:?set E2E_RUNTIME_NAME (console runtime name, e.g. agent-08-14)}}"
save_kv E2E_RUNTIME_NAME "$RUNTIME_NAME"

ENDPOINT="https://${ACCOUNT_ID}.agentrun-data.${AGENTRUN_REGION}.aliyuncs.com/agent-runtimes/${RUNTIME_NAME}/endpoints/Default/invocations/openai/v1/chat/completions"
save_kv E2E_ENDPOINT "$ENDPOINT"

# probe WITHOUT a token: expect 401 "no ID token provided" — this proves the
# route exists and AgentIdentity inbound auth is armed.
code=$(curl -s -o "$STATE_DIR/probe.json" -w '%{http_code}' -m 30 \
  -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"ping"}],"stream":false}' || echo 000)

if [ "$code" = "401" ] && grep -q "no ID token provided" "$STATE_DIR/probe.json" 2>/dev/null; then
  log_ok "endpoint reachable, inbound auth armed (401 no ID token provided)"
  echo "ENDPOINT: $ENDPOINT"
else
  log_fail "unexpected probe result (HTTP $code):"
  head -c 400 "$STATE_DIR/probe.json" >&2 || true
  echo >&2
  echo "  If 404: check the runtime name / region." >&2
  echo "  If 200 with an app error: the path is wrong — see references/troubleshooting.md." >&2
  exit 1
fi
