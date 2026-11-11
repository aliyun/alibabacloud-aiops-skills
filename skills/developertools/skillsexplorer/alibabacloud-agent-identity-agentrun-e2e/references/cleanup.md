# Cleanup: What Is Deleted How, and What Stays

`07_cleanup.sh` deletes recorded Cedar and OSS test resources and prints the console
checklist. This document explains the split.

## Deleted by script (API)

| Resource | How |
|---|---|
| Cedar policies `e2e-permit-tool` / `e2e-permit-param` + the `e2e-policy` set (if this skill created them) | AgentIdentity API |
| OSS test object + bucket `e2e-test-<account>` (if this skill created them) | oss2 |

Before cleanup, restore the original permission-control settings and bindings,
and remove only this run's policy-set binding in the console. Restore a reused
Runtime's original code package and configuration using the retained source
described in `agentrun-deploy.md`. Wait for READY, compare the actual
`codeChecksum` in the Runtime's `概览` page with the saved value, and check the
restored configuration. Language and startup-command values alone do not prove
code restoration. Do not remove a code source still used by a Runtime or delete
reused resources.
For a reused Runtime, check the output retained from `05_attach_role_policy.sh`.
If it attached `AliyunOSSReadOnlyAccess`, open RAM console → `身份管理` → `角色`,
select the saved `E2E_WI_ROLE`, and remove that policy from its permission list.
If the script reported it was already attached, preserve it. Removing a new grant
requires `ram:DetachPolicyFromRole`, included in the operator policy example in
`ram-policies.md`.
Failed deletions remain recorded and cause a nonzero exit; resolve the reported
failure and rerun with the same state directory. Repeat after successful cleanup
to confirm that no recorded resources remain.

## Console checklist (not automated by this Skill)

Console labels are quoted verbatim in Chinese — that is what the page shows.

1. AgentRun console → `Agent 运行时` (Agent runtimes) → delete only the Runtime
   created for this run; retain a reused Runtime after restoring its configuration.
2. AgentRun console → `工具与Skills` (Tools & Skills) → delete only test MCP tool(s)
   created for this run (including any DingTalk marketplace tool).
3. AgentIdentity console → `凭证提供商` (credential providers) → delete test
   providers created for this run (the API-key one, and the OAuth2 one if
   test-only).
4. AgentIdentity console → `身份提供商` (identity providers) → delete only
   registrations created for this run; retain user-provided registrations.
5. DingTalk documents created during Group E are user content — keep or
   delete inside DingTalk.

## Never touched

- The user's IdP, RAM OAuth2 app, and model service (they pre-date the run
  or outlive it).
- Workload identities auto-created by the platform: deleting the runtime in
  step 1 removes its identity; do not try to edit them via API
  (`WorkloadIdentityPlatformMismatch` — platform-managed).
- Resources without this run's creation records, including resources in other
  regions.
