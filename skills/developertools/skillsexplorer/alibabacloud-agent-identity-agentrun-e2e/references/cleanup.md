# Cleanup: What Is Deleted How, and What Stays

`07_cleanup.sh` automates the API-deletable parts and prints the console
checklist. This document explains the split.

## Deleted by script (API)

| Resource | How |
|---|---|
| Cedar policies `e2e-permit-tool` / `e2e-permit-param` + the `e2e-policy` set (if this skill created them) | AgentIdentity API |
| OSS test object + bucket `e2e-test-<account>` (if this skill created them) | oss2 |

## Console checklist (no delete API)

Console labels are quoted verbatim in Chinese — that is what the page shows.

1. AgentRun console → `Agent 运行时` (Agent runtimes) → delete the test runtime.
2. AgentRun console → `工具与Skills` (Tools & Skills) → delete the test MCP tool(s)
   (including any DingTalk marketplace tool).
3. AgentIdentity console → `凭证提供商` (credential providers) → delete test
   providers created for this run (the API-key one, and the OAuth2 one if
   test-only).
4. AgentIdentity console → `身份提供商` (identity providers) → user-provided ones
   stay; delete only test-specific registrations.
5. DingTalk documents created during Group E are user content — keep or
   delete inside DingTalk.

## Never touched

- The user's IdP, RAM OAuth2 app, and model service (they pre-date the run
  or outlive it).
- Workload identities auto-created by the platform: deleting the runtime in
  step 1 removes its identity; do not try to edit them via API
  (`WorkloadIdentityPlatformMismatch` — platform-managed).
- Anything matching `workload-*` in other regions — not created by this
  skill.

## Field notes

- Deleting a role requires detaching its attached policies first
  (the script pattern: ListPoliciesForRole → Detach → DeleteRole).
- Tools created via the CreateTool API vanish by themselves (see
  troubleshooting) — nothing to clean there.
