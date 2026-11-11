#!/usr/bin/env bash
# 01_prepare_identities.sh — create/reuse the identity-chain resources via API
# The script supports:
#   A. OIDC identity provider registration  [API]   idempotent, reuse if exists
#   B. OAuth2 callback backfill into the RAM app [API]  (IMS update_application)
#   C. API Key provider (fixed name test-provider-api-key) [API]  reuse if exists
# Console steps (see references/console-guides.md):
#   - Create the RAM OAuth2 application and OAuth2 credential provider in the
#     console, with the scopes required by the sample.
# Inputs (collect before running):
#   E2E_IDP_NAME=<name> E2E_IDP_DISCOVERY_URL=<url>  → runs step A
#   E2E_RAM_APP_ID=<id>  E2E_CALLBACK_URL=<url>      → runs step B
#   (both pairs given → A then B; neither → only step C runs)
# Re-run freely: existing resources are detected and reused, never duplicated.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

# Trigger steps A/B only from explicitly supplied environment variables. Capture them
# before load_e2e_env restores saved values, so a previous run cannot
# trigger changes to its resources.
EXPLICIT_IDP_NAME="${E2E_IDP_NAME:-}"
EXPLICIT_IDP_DISCOVERY_URL="${E2E_IDP_DISCOVERY_URL:-}"
EXPLICIT_RAM_APP_ID="${E2E_RAM_APP_ID:-}"
EXPLICIT_CALLBACK_URL="${E2E_CALLBACK_URL:-}"

load_e2e_env

py_sdk /dev/stdin \
  "${EXPLICIT_IDP_NAME}" "${EXPLICIT_IDP_DISCOVERY_URL}" \
  "${EXPLICIT_RAM_APP_ID}" "${EXPLICIT_CALLBACK_URL}" <<'PYEOF'
import os
import sys

from alibabacloud_agentidentity20250901.client import Client as AIClient
from alibabacloud_agentidentity20250901 import models as am
from alibabacloud_ims20190815.client import Client as ImsClient
from alibabacloud_ims20190815 import models as im
from alibabacloud_tea_openapi import models as om
from alibabacloud_credentials.client import Client as CredClient

region = os.environ.get("AGENTRUN_REGION", "cn-hangzhou")
ua = os.environ.get("SKILL_UA", "")
cred = CredClient()
ai = AIClient(om.Config(credential=cred, region_id=region,
                        endpoint=f"agentidentity.{region}.aliyuncs.com",
                        user_agent=ua))
ims = ImsClient(om.Config(credential=cred, region_id=region, endpoint="ims.aliyuncs.com",
                         user_agent=ua))

idp_name, discovery_url, ram_app_id, callback_url = sys.argv[1:5]

# Step A: OIDC identity provider (API, reuse if exists)
if idp_name and discovery_url:
    try:
        d = ai.get_identity_provider(
            am.GetIdentityProviderRequest(identity_provider_name=idp_name))
        d = d.body.to_map().get("IdentityProvider") or {}
        print(f"[SKIP] IdP exists: {idp_name} (discovery: {(d.get('DiscoveryURL') or '')[:60]})")
    except Exception as error:
        if getattr(error, "code", None) != "EntityNotExists.IdentityProvider":
            raise
        ai.create_identity_provider(am.CreateIdentityProviderRequest(
            identity_provider_name=idp_name,
            description=f"created by agentrun-e2e skill ({idp_name})",
            allowed_audience=["*"],
            discovery_url=discovery_url))
        print(f"[OK] IdP created: {idp_name}")
elif idp_name or discovery_url:
    sys.exit("[FAIL] step A needs BOTH E2E_IDP_NAME and E2E_IDP_DISCOVERY_URL")

# Step B: OAuth2 callback backfill into the RAM app (IMS API)
if ram_app_id and callback_url:
    ims.update_application(im.UpdateApplicationRequest(
        app_id=ram_app_id, new_redirect_uris=callback_url))
    g = ims.get_application(im.GetApplicationRequest(app_id=ram_app_id))
    uris = (g.body.to_map()["Application"].get("RedirectUris") or {}).get("RedirectUri") or []
    if callback_url in uris:
        print(f"[OK] callback backfilled into RAM app {ram_app_id}")
    else:
        sys.exit(f"[FAIL] backfill verification mismatch: {uris}")
elif ram_app_id or callback_url:
    sys.exit("[FAIL] step B needs BOTH E2E_RAM_APP_ID and E2E_CALLBACK_URL")

# Step C: API Key provider (fixed name, reuse if exists)
APIKEY_PROVIDER = "test-provider-api-key"  # fixed by the sample's weather tool
try:
    ai.get_apikey_credential_provider(
        am.GetAPIKeyCredentialProviderRequest(
            apikey_credential_provider_name=APIKEY_PROVIDER))
    print(f"[SKIP] API Key provider exists (reused): {APIKEY_PROVIDER}")
except Exception as error:
    if getattr(error, "code", None) != "EntityNotExists.APIKeyCredentialProvider":
        raise
    ai.create_apikey_credential_provider(am.CreateAPIKeyCredentialProviderRequest(
        apikey_credential_provider_name=APIKEY_PROVIDER,
        description="created by agentrun-e2e skill; mock value (tool checks non-empty injection)",
        apikey="demo-key-123"))
    print(f"[OK] API Key provider created: {APIKEY_PROVIDER}")

print("NEXT: RAM app + OAuth2 provider remain console steps (console-guides.md 2.2);")
print("      after the console provider step, re-run with E2E_RAM_APP_ID + E2E_CALLBACK_URL")
print("      to backfill the callback via API.")
PYEOF

[ -n "${EXPLICIT_IDP_NAME}" ] && save_kv E2E_IDP_NAME "$EXPLICIT_IDP_NAME"
[ -n "${EXPLICIT_RAM_APP_ID}" ] && save_kv E2E_RAM_APP_ID "$EXPLICIT_RAM_APP_ID"
[ -n "${EXPLICIT_CALLBACK_URL}" ] && save_kv E2E_CALLBACK_URL "$EXPLICIT_CALLBACK_URL"
exit 0
