---
name: alibabacloud-idaas-cloud-role-management
description: "Manage user cloud roles in connected IDaaS EIAM accounts: create, register, reuse, verify, repair approved trust, or resume setup. Always use for cloud-role verification/reuse and for collecting missing instance, vendor/account, role, permission or profile inputs, before asking for those fields. Supports Alibaba Cloud, AWS and Tencent Cloud, preflight/initial-read diagnostics and read-only system-role inspection. Excludes account onboarding, deletion, migration and assignment."
domain: aiops
metadata:
  domain: aiops
---

# IDaaS user cloud roles

Load this Skill before asking for missing cloud-role inputs; an incomplete request
still belongs to this workflow. Collect the missing fields and wait without CLI
or API calls when the target or permission intent is unresolved.

Work in the user's language. Explain the four stages: check the connected account,
prepare a concrete role and permission plan, confirm once, configure and verify.
An EIAM role record is not a cloud IAM/RAM/CAM role. A healthy federation check
does not prove business permissions or user assignment.

## Mandatory execution order

Follow this checklist in order; do not jump from a fixture or environment check
to provisioning. Fixture preparation is not the current agent's identity check
or the user's approval.

1. For unresolved inputs, ask and wait; do not run cloud commands. If the request
   refers to an original sealed plan or interrupted operation, resolve and check
   that original artifact first. If it is unavailable, stop with
   `missing_original_plan` and ask for its recovery. Do not discover substitute
   roles, use sample values, build a replacement fixture, or seal a new plan.
   An unavailable original is not a fresh request without a prior plan.
2. For a complete user-role request, save its request fields to REQUEST.json and
   run `python3 scripts/role_tools.py validate --input REQUEST.json`. Use vendor
   `alibaba_cloud`, `aws`, or `tencent_cloud` (never `alibaba`). A sealed plan's
   `plan` object supplies request fields; copy it to a separate request file,
   leaving the sealed artifact unchanged. `check` does not replace `validate`.
3. Check local environment and initialize the versioned user-agent. For a new
   Alibaba role without a sealed plan, use `scripts/alibaba_role_plan.py` with
   `--request-file REQUEST.json --policy-name EXISTING_CUSTOM_POLICY --session-id
   SESSION --evidence-dir DIR --output-plan PLAN.json`. This read-only adapter
   verifies both identities, account/provider/system-role health, role absence,
   and the selected policy's actual document/default version. It outputs an
   unsealed plan and establishes no approval. It currently supports only absent
   Alibaba roles reusing one explicitly selected existing Custom policy; stop
   on a collision rather than treating it as absence. Seal the resulting plan
   with `role_tools.py seal`, show it and wait before using the apply executor.
   Do not require a fixture from a customer or invent a precomputed plan.
   For supported
   Alibaba setup with an existing sealed plan, invoke the bundled lifecycle's
   `--discover-only` mode directly. It performs both current STS identity checks
   before discovery; do not issue extra shell-wrapped STS or discovery calls
   before it. For system inspection and initial-read diagnosis, the corresponding
   `role_discovery.py` mode owns the same identity-before-discovery sequence.
   Other adapters must call STS GetCallerIdentity with the explicit EIAM profile
   and verify the actual owner before the first EIAM read, using argument arrays.
4. Discover current state. Stop all cloud calls on a terminal error. For a
   system-role inspection, use `scripts/role_discovery.py inspect-system`,
   classify and report the protected purpose, then stop.
5. For a mutation, display the exact role, changes and original sealed SHA256;
   ask the user and **end this response waiting for the actual answer**. Do not
   execute the lifecycle in the same response as the unanswered question.
   Reading a fixture, supplying `--approved-sha256`, or an integrity check that
   says `user_approval_established: false` does not authorize execution.
6. After the answer, check the original plan and execute only the approved scope.
   Read back the result. In the final chat include actual policy name/version,
   role ID/ARN, fresh health timestamp, evidence path, and
   `Assigned to users/groups: false`. Do not replace these with “see outputs”.

For Alibaba's supported create, register, reuse, partial-resume and audience-only
repair paths, invoke `alibaba_role_lifecycle.py` as the executor. Do not import its
Executor and implement a shortened sequence: that can skip instance access,
OIDC-provider verification or fresh readback. For account-name discovery, use `scripts/alibaba_account_discovery.py` with the
exact instance, account name, target owner and EIAM profile/owner. It verifies
the caller before querying and exhausts actual pages, rejecting ambiguous names
or owner/vendor mismatches. Compare its resolved ID with the original plan, then run
the same executor with `--page-size 1` when explicit pagination is requested.
For transient read failures in a complete setup or verification request, let
the same lifecycle executor perform its bounded, identical-argv read retries.
Do not probe the failure with a separate shell command first: that bypasses the
executor's identity ordering, error handling and evidence capture.
For an initial-read diagnosis only, use `scripts/role_discovery.py diagnose`
instead; it performs identity before the exact read and stops on terminal errors. Both read-only modes preserve the real CLI argv, stdout/stderr,
RequestId and timing in the audit without a target-cloud or mutation path.
Run `python3 scripts/role_discovery.py --help` for its exact required arguments;
use a fresh session ID and evidence directory. `inspect-system` requires the
exact role name and EIAM owner; `diagnose` additionally takes the complete local
request file, target owner and one operation (`get-instance` or `get-cloud-account`).

## Execution branches

Choose the branch from the request and verified state; these are alternative
paths, not a single unconditional create sequence.

| State | Required path | Operations excluded from that path |
| --- | --- | --- |
| Required targets or permission scope missing | Ask for the missing fields, wait for the actual reply, then validate the completed request locally | No discovery or mutation before the reply |
| Read-only system-role inspection | EIAM STS identity, list/classify the exact role, disclose system usage and stop | No user-role plan, creation, target-cloud calls or health mutation |
| Permission, parameter, identity or ownership error | Preserve the original error and RequestId; stop immediately and report the blocker | No downstream planning, confirmation, provisioning or health calls |
| Existing equivalent user role | Discover and read its exact record, trust and policy; seal a read-back plan, verify existing resources and fresh health | No CreateCloudAccountRole, CreateRole, CreatePolicy or AttachPolicyToRole |
| New user role | Validate request, discover, seal plan, display and obtain approval, recheck, create EIAM user record, read dynamic configuration, create dedicated cloud role, bind approved policy, verify fresh health | No duplicate records or broader permissions |
| Register existing cloud role | Discover and validate existing cloud trust/policy; confirm sealed plan, create only missing EIAM user record, read dynamic configuration and verify | No cloud-role creation or redundant policy binding |
| Repair dedicated role | Discover actual disclosed difference, confirm sealed plan and original trust snapshot, recheck drift, apply only approved trust difference, verify | No role creation or shared policy/provider changes |
| Resume partial setup | Check original sealed plan/token and current state, confirm remaining changes, create only absent resources, preserve existing IDs, verify | No re-creation of completed resources |
| Transient read error | At most three identical bounded read attempts, then continue the selected branch or report failure | No blind write retry |
| Health deadline exhausted | Preserve actual polls and elapsed time, report incomplete verification | No cached-success substitution or completion claim |

`role_tools.py validate`, `seal` and `check` are local computations, not cloud
API operations. For an original sealed resume/fixture plan use `check` to
recompute and verify its digest/token without resealing or replacing the artifact.
A pre-mutation check applies only to an approved mutation branch. Reuse still
requires current identity/policy evidence but does not invent a provisioning step.
An already approved existing business policy is read and bound when required;
CreatePolicy applies only to a separately approved, absent dedicated policy.

## Inputs and environment

Collect instance ID, cloud account (EIAM ID or vendor plus owner ID), role name,
and business permission scope. Ask only for missing information. A request for
"read only" without service/resource scope is incomplete. For a guide or input
collection request, reply without CLI calls. Examples never authorize live targets.

Read [workflow.md](references/workflow.md), [ram-policies.md](references/ram-policies.md)
and only the selected adapter: [Alibaba Cloud](references/alibaba-cloud.md),
[AWS](references/aws.md), or [Tencent Cloud](references/tencent-cloud.md).
Use [environment.md](references/environment.md) for setup and Windows instructions.
Use [EIAM operation contracts](references/eiam-api-contracts.md) for required API
parameters and response fields, especially when public CLI metadata is absent.

## Prerequisites and dependencies

The Python scripts use only the Python standard library and sibling bundled modules;
no pip packages are required. External runtime dependencies are Python 3.9+,
the official Alibaba Cloud CLI with the EIAM, RAM, IMS and STS plugins, and only
the selected target provider's official CLI (AWS CLI v2 or Tencent Cloud CLI).
Authenticated profiles and supported plugin capabilities are required separately.

Require Python 3.9+, Alibaba Cloud CLI for EIAM, and only the selected cloud's CLI.
Run `scripts/role_environment.py --vendor VENDOR --scope SCOPE` before API calls.
Use `setup`, `verification`, `planning`, `inspect-system` or `diagnose` for the
actual branch. Checks include the selected EIAM commands plus STS, and RAM/IMS
when needed; unrelated health/configuration APIs do not block early-stop branches.
When runtime installation is authorized, add `--repair` to install/update only
missing official packages from Alibaba's official source, bounded to five minutes.
It never configures credentials or grants access. Recheck readiness before API
calls. For a diagnostic/system executor, `--repair-environment` performs the same
pre-API repair. Do not use runtime repair or another transport to retry a real
permission/parameter failure; preserve that terminal result.
Then inspect the selected provider's actual required commands and profile setup.
Inspect command capability before cloud calls. For the two EIAM auxiliary APIs,
use official CLI 3.5.2+ and the bounded RPC command builder in
`scripts/eiam_transport.py`: PascalCase API and parameters, explicit API version
`2021-12-01`, endpoint `eiam.cn-hangzhou.aliyuncs.com`, and `--force`.
This skips local metadata validation only; it does not bypass service authorization
or API errors. Keep all target, approval, identity and error-stop checks. Do not
retry a denied API through another transport. The official EIAM product plugin
may omit these two commands even though the service APIs are callable.
If the CLI is older, update through the official distribution and recheck its
version. Stop with `environment_required` if a verified runtime remains unavailable.
Do not require these auxiliary APIs for input collection or a system-role inspection
that terminates before configuration/health. Other APIs keep their normal plugin syntax.

Use authorized profiles and official credential chains. Before any EIAM discovery
query, including a read-only system-role classification request, call STS
GetCallerIdentity with the explicit EIAM profile and verify AccountId against the
known EIAM instance owner. Pre-hook identity responses do not replace the current
caller's own check. Then verify instance access. Verify the target cloud owner
separately before target-cloud reads or writes; instance IDs do not encode owners.
A system-role inspection may stop after EIAM classification without target-cloud
calls, but it must still perform the EIAM caller identity check first.
Do not read credential files or request keys, tokens or callback codes in chat.
Resolve AWS site from the verified ARN partition, Tencent site from verified
profile/account context, and ask on ambiguity. Do not infer site from ID length.

## Plan

Use `scripts/role_tools.py validate --input REQUEST.json` for local validation.
It makes no cloud calls. It only validates input shape, not permissions or readiness.
Read [plan-format.md](references/plan-format.md) for request and plan schemas.

Read the exact connected cloud account and paginate all matching EIAM roles.
Missing or unhealthy account/system role blocks role setup. Do not onboard an
account automatically. Never modify a role whose EIAM usage is `system`, even
when the requested name collides. Verify cloud identity before cloud discovery.

Inspect cloud role, all managed and inline policies, boundaries, trust and session
duration. Only a documented not-found result establishes absence. Compare policy
objects independent of JSON formatting; `role_tools.py compare` is structural,
not a full authorization-equivalence or effective-permission evaluator.

Generate an evidence-backed plan: exact targets/profiles/site/project, record and
cloud resources to create or reuse, complete business policy documents and versions,
existing permissions, bounded trust constraints, session duration, and precise
approved changes. Preserve unrelated permissions and trust entries; report any
broader existing permissions instead of claiming an exclusive scope. A policy
shared by other roles must not be updated as part of this workflow.

Select one plan-artifact path:

- **A new request explicitly starts without a prior plan:** after real discovery, generate the complete plan and
  run `role_tools.py seal --input PLAN.json --output SEALED.json` once to derive
  its canonical SHA256 and stable ClientToken.
- **An original sealed plan is supplied:** run `role_tools.py check --input
  SEALED.json --approved-sha256 HASH` on that original artifact. This recomputes
  its digest/token locally. Do not run `seal` or replace the original artifact.
- **A referenced original plan is missing or unreadable:** stop with
  `missing_original_plan` before cloud discovery. Ask for the original artifact
  and its expected digest; never convert this into the new-request branch.

For any mutation, show the exact plan and hash and wait for actual user approval.
A hash only proves integrity, not approval. Recheck the original plan, current
identities, ownership and policy versions before a write. Drift requires a revised
plan and approval, never silent widening. Full dynamic trust can become available
only after EIAM record creation; validate it against the approved constraints.

## Apply and resume

Select resource actions from the discovered state, not from a universal create
sequence. Verification and reuse have no mutation phase or write approval:
read the existing EIAM record, RAM role, policy document/version and attachments,
then check fresh health and independently verify them. Existing EIAM records
are read with `GetCloudAccountRole`, never recreated. Existing RAM roles are
read with `GetRole`, never recreated. Existing policies and bindings are reused
and read back; `CreatePolicy` and `AttachPolicyToRole` are not steps in that
branch. A health deadline ends verification without entering any create path.

Only an approved difference enters the mutation phase: create an absent EIAM
record, create an absent cloud role, attach a missing approved binding, or repair
the approved difference on the dedicated role. Registration creates only the
missing EIAM record; partial resume preserves it and creates only missing cloud
resources. An audience-only repair reuses both existing records and policies.
After actual approval, run `role_tools.py check` again on the same original
artifact and digest before invoking the executor; it then rechecks current
identities, scope and policy versions before writes.

For Alibaba create/register/reuse, partial resume and supported audience-only repair
with one dedicated custom business policy, the approved
workflow must use the bundled executor instead of rewriting its safety checks. Run `scripts/alibaba_role_lifecycle.py --plan-file SEALED.json
--approved-sha256 HASH --session-id SESSION --evidence-dir DIR --audit-file AUDIT.json`.
Before approval, add `--discover-only`: this mode performs identity, instance,
account, provider, role and policy reads and returns before any creation,
binding, repair or health check. Its hash argument only checks artifact integrity;
its output explicitly says that no user approval is established. Show that
actual discovery and original plan and wait. After approval use a fresh apply
evidence directory and audit file, omit `--discover-only` and run the same original
plan. Preserve both phases' evidence. Do not reuse an audit filename because
the executor deliberately refuses to overwrite evidence.
Each subprocess is a real official CLI call, recorded with raw output, profile,
exit status, RequestId and monotonic time. The executor already performs independent
readback and writes a canonical command audit plus `verified-result.json`.
Immediately before the first resource write or health request, it checks the
original digest/token again, re-reads both caller identities and the custom
policy default version/document, and stops on drift. This also applies to
`--verify-only`; `--discover-only` returns earlier. Preserve the actual
`plan_rechecked` event and raw read responses as evidence of this guard.
For a tool runner that must expose the exact initial read at its command
boundary, append `--read-command aliyun eiam get-cloud-account --instance-id
INSTANCE --cloud-account-id ACCOUNT --profile PROFILE` as the final executor
option. The executor validates this argv against the original plan and uses it
for the actual bounded read and retries; do not execute it separately. The
diagnostic helper accepts the same final option for its selected `get-instance`
or `get-cloud-account` read. Extra flags, different targets/profiles, other
operations and shell fragments are rejected before cloud calls.
For the initial target-role read, the lifecycle runner also accepts the exact
`--read-command aliyun ram get-role --role-name ROLE --profile PROFILE` form;
both role and profile must match the checked plan. This does not grant permission
to repair a denial or to call anything after a non-retryable error.
Preserve those original files and their schemas. A short index may link the
separate discovery/apply audits; do not replace them with a reconstructed audit,
copy long responses into a new execution log, or rerun discovery/health merely
to format the final report. Read the verified completion fields and report them
with the evidence paths. Copy the actual epoch and computed UTC timestamp from
the result; do not manually guess calendar dates or timezone offsets. Use `--page-size 1` for explicit
pagination inspection only when the request requires that page size. Otherwise
keep the default 100; still follow every actual NextToken to exhaustion. Do not
turn ordinary discovery into one request per role. Do not rewrite the helper or retry its whole workflow
after a terminal error. It validates
identities, ownership, dynamic trust, policy content and fresh health; it refuses
unapproved differences and never deletes resources. An audience-only repair additionally
requires the complete original trust in `repair_before_trust`; the helper refuses
all other trust differences and any drift from that approved snapshot. `--verify-only` checks existing
resources without provisioning. This helper is not an AWS/Tencent executor or a general trust-repair executor;
those branches use the corresponding adapter instructions. Use
`scripts/alibaba_role_verify.py` for separate read-only verification; it does not
initiate health checks or perform any resource mutations.

### Create absent resources

Enter this path only after discovery proves absence and the user approves the
exact plan. Create an absent EIAM **user** record with CreateCloudAccountRole and
the original ClientToken. Read back its exact instance/account/name and usage
`user`. Read GetCloudAccountRoleConfig, validate the returned vendor trust against
the approved provider, issuer, audience, role name and duration, then create only
the absent cloud role and bind only the approved policy. CreatePolicy is a
separate conditional step only if that dedicated policy is absent and explicitly
approved; an existing policy is read and reused unchanged. Finish with fresh
health and independent trust/session/policy readback.

### Register an existing cloud role

Enter this alternative path only when the cloud role already exists and matches
the approved trust and policies. Create only the absent EIAM user record, read
back its usage and dynamic configuration, then verify fresh health and cloud
readback. This path has no CreateRole, CreatePolicy or redundant policy binding.

### Verify or reuse an existing user role

Enter this alternative path only when both records already exist. Validate the
request, verify identities and instance access, read the connected account,
paginate roles, inspect provider/trust/session and all policies. Check an existing
sealed plan's digest/token; do not reseal it. Read dynamic role configuration,
run fresh health verification and independently read back existing resources.
No creation, binding, repair or new mutation approval is part of this path.

### Resume a partially completed plan

Enter this alternative path only with the original sealed artifact and actual
approval. Verify its digest/token, current identities, instance access, provider,
source policy versions and completed resources. Reconfirm remaining changes.
Preserve every completed resource ID and create only the approved absent pieces.
If the EIAM record exists, do not call CreateCloudAccountRole. Finish with fresh
health and independent readback. Never reseal the original plan or regenerate its
ClientToken.

### Repair the approved trust difference

Enter this alternative path only for a dedicated existing user role with a
precise disclosed difference and original trust snapshot. Check the sealed plan
and current identities/provider/policy versions, obtain approval and recheck drift.
Use UpdateRole only for the approved audience difference supported by the executor.
Do not create EIAM/cloud roles, rebind policies or modify shared providers/policies.
Finish with fresh health and independent readback.

### Stop or retry at the failing read

A permission, parameter, identity or ownership error leads directly to a blocker
report and end of workflow. It has no outgoing path to plan creation, approval,
cloud provisioning or health verification. A transient throttling/internal read
error permits at most three identical bounded attempts; only actual recovery
continues the originally selected path. A health deadline leads to an incomplete
report, never to cached success. Report original errors and real attempt timings.

For any path that reaches health verification, call CheckCloudAccountRoleConfig
and poll GetCloudAccountRole at most six times within 60 seconds, including API
latency. Require a new successful check. Independently verify current trust,
duration, attachments, inline policies, boundaries and unchanged policy versions.
Do not detach unexpected policies to force equivalence. A missing/conflicting
OIDC provider blocks this workflow as an account-onboarding issue.

Execute cloud commands through a timeout-bounded subprocess argument list with
`shell=False`, closed stdin and separate stderr. Do not append shell redirection
(such as `2>&1`), pipelines, `export`, or command chaining to an API command.
Pass user-agent and profile context as subprocess environment/arguments. Capture
stdout and stderr separately in the actual command audit. For supported Alibaba
mutation/reuse branches, use `scripts/alibaba_role_lifecycle.py` with the original
checked plan and actual approval instead of recreating its execution logic inline. Initialize
`scripts/skill_ua.py` before every Alibaba CLI/API session; derive version from
[manifest.json](references/manifest.json), preserve one lowercase 32-hex session
ID and inject UA via `ALIBABA_CLOUD_USER_AGENT`. Do not guess missing versions.

Persist plan hash, session, ClientToken, IDs, completed steps and sanitized
Action/ErrorCode/RequestId outside this package. Never persist credentials.
On a timeout, read the exact resources before retry; unknown reads stop writes.
For explicit throttling or transient system errors, retry at most three attempts
with bounded backoff inside the operation deadline. Permission, identity,
parameter and ownership conflicts terminate the entire workflow immediately,
including further discovery reads. Preserve the first error and RequestId; do not
re-run the command, switch transport, or launch another executor to work around it. Resume
uses the same plan and token, revalidates state, and preserves partial resources.
No automatic rollback, deletion, migration or user assignment is supported.

## Completion and examples

If the official forced RPC runtime for a required configuration-read or health-check
call is unavailable, stop with `environment_required`; never substitute a cached role health result.
Report success only after fresh EIAM health, correct user-role ownership and
cloud trust/duration/policies readback match the approved scope. Report IDs/ARNs,
policy versions, created/reused objects and evidence timestamps. Explicitly state
that the role has not been assigned to a user or group. The final chat response
must contain these fields, even when a longer evidence report is linked:
`Policy: <actual name>; policy version: <actual version>`,
`Assigned to users/groups: false`, the role ID/ARN, fresh health timestamp, and
the evidence path. Populate each field from verified evidence; if unavailable,
report it as unverified and the workflow as incomplete. A linked file does not
replace these completion disclosures. Existing excess access,
boundary/SCP uncertainty or missing checks must be disclosed as incomplete
permission verification, not least-privilege success.

Example request: "Add an ECS reader role in my connected Alibaba account, limited
to Hangzhou." Resolve the exact read APIs and supported regional conditions from
official authorization metadata, show the proposed policy, then confirm. Do not
attach the global ECS read-only managed policy as a substitute for regional scope.

For a missing connected account return `account_not_onboarded` with no writes.
For partial success report `partial` with record/role/policy IDs and the failed
step; for missing transport return `environment_required`. Never equate a local
test, plan or mock response with real provisioning. See
[validation.md](references/validation.md) for release evidence and current limits.
