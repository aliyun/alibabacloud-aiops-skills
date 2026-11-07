#!/usr/bin/env python3
"""PAM feature permission authorization (fully automated, in two stages):
  A. RS level: AuthorizeResourceServerToClient(iap_pam) (idempotent).
  B. Scope level: ListResourceServerScopes(--resource-server-scope-type all) finds
     the ress_id for cloud_account_role:obtain_access_credential,
     then calls AuthorizeResourceServerScopesToClient.

Usage: authorize_pam_scope.py <region> <instance_id> <client_app_id>
Final output: PAM_AUTH=auto_done | module_disabled | scope_not_found

Verified findings (2026-10; corrected in v0.4.0):
- The PAM system application has the fixed ID iap_pam (ApplicationCreationType=system_init).
  ListApplications excludes it by default; GetApplication can query it directly.
- ListResourceServerScopes returns 0 without the type filter. PAM scopes have type
  application_delegated/delegated; --resource-server-scope-type all is required to see
  all 14 scopes, including cloud_account_role:obtain_access_credential.
- AuthorizeResourceServerScopesToClient requires ress_id. Passing the scope value as
  its ID causes InvalidParameter.ResourceServerScopeIds. The documented approach
  uses the plugin's JSON array parameter.
- Token endpoint states: RS not authorized -> 400 invalid_request;
  RS authorized but scope not authorized -> 400 invalid_scope;
  RS and scope both authorized -> 200.
"""
import json
import sys

from common import die, info, run_aliyun

PAM_MODULE_KEY = "urn:alibaba:idaas:license:module:pam"
PAM_APP_ID = "iap_pam"
PAM_RS_IDENTIFIER = "urn:cloud:idaas:pam"
PAM_SCOPE_VALUE = "cloud_account_role:obtain_access_credential"


def check_pam_module(region: str, iid: str) -> bool:
    d = run_aliyun(["eiam", "check-instance-module-status", "--region", region,
                    "--instance-id", iid, "--module-key", PAM_MODULE_KEY])
    status = (d.get("Module") or {}).get("ModuleStatus")
    if not isinstance(status, str) or not status:
        die("PAM query returned no module status; do not treat a failed query as disabled")
    if status != "enabled":
        info(f"PAM module is not enabled (service status={status}); basic M2M remains available if licensed")
    return status == "enabled"


def verify_pam_app(region: str, iid: str) -> bool:
    d = run_aliyun(["eiam", "get-application", "--region", region,
                    "--instance-id", iid, "--application-id", PAM_APP_ID])
    a = d.get("Application", d)
    return a.get("ResourceServerIdentifier") == PAM_RS_IDENTIFIER


def authorize_rs(region: str, iid: str, client_id: str) -> None:
    run_aliyun(["eiam", "authorize-resource-server-to-client", "--region", region,
                "--instance-id", iid, "--client-application-id", client_id,
                "--resource-server-application-id", PAM_APP_ID])


def find_pam_scope(region: str, iid: str):
    token = None
    seen = set()
    while True:
        args = ["eiam", "list-resource-server-scopes", "--region", region,
                "--instance-id", iid, "--application-id", PAM_APP_ID,
                "--max-results", "50", "--resource-server-scope-type", "all"]
        if token:
            args += ["--next-token", token]
        d = run_aliyun(args)
        for scope in d.get("ResourceServerScopes", []):
            if scope.get("ResourceServerScopeValue") == PAM_SCOPE_VALUE:
                return scope.get("ResourceServerScopeId")
        token = d.get("NextToken")
        if not token:
            return None
        if token in seen:
            die("Repeated scope pagination token; query did not complete")
        seen.add(token)


def authorize_scope(region: str, iid: str, client_id: str, scope_id: str) -> None:
    run_aliyun(["eiam", "authorize-resource-server-scopes-to-client",
                "--region", region,
                "--instance-id", iid, "--client-application-id", client_id,
                "--resource-server-application-id", PAM_APP_ID,
                "--resource-server-scope-ids", json.dumps([scope_id])])


def main() -> None:
    if len(sys.argv) < 4:
        die("Usage: authorize_pam_scope.py <region> <instance_id> <client_app_id>")
    region, iid, client_id = sys.argv[1:4]

    if not check_pam_module(region, iid):
        info("PAM is not enabled on this instance. Skip this step if only an M2M token is needed, without PAM-to-STS exchange.")
        print("PAM_AUTH=module_disabled")
        return

    if not verify_pam_app(region, iid):
        die(f"Failed to query fixed ID {PAM_APP_ID}, or the RS identifier did not match; the PAM application may not be initialized")

    authorize_rs(region, iid, client_id)

    scope_id = find_pam_scope(region, iid)
    if not scope_id:
        info(f"⚠️ Scope {PAM_SCOPE_VALUE} not found (was --resource-server-scope-type all specified?)")
        info("Fallback: Console > Permission Center > Feature Permission Management > Privileged Access Management > authorize this client > select the scope")
        print("PAM_AUTH=scope_not_found")
        return

    authorize_scope(region, iid, client_id, scope_id)
    info(f"Scope-level authorization completed: {client_id} -> {PAM_SCOPE_VALUE} ({scope_id})")
    info(f"Token scope: {PAM_RS_IDENTIFIER}|{PAM_SCOPE_VALUE}")
    info("STS exchange also requires a console data-permission rule linking the application to the target cloud role")
    print("PAM_AUTH=auto_done")


if __name__ == "__main__":
    main()
