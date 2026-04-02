---
name: alibabacloud-flink-instance-manage
description: >
  Manage Alibaba Cloud Real-Time Compute for Apache Flink instances across the
  full lifecycle, including create/query/scale/renew/convert, namespace
  operations, tagging, cleanup, and batch execution. Use this skill only when
  the user explicitly asks to operate Alibaba Cloud Flink instances or their
  direct child resources in a region; do not trigger for unrelated prompts.
license: Apache-2.0
compatibility: >
  Requires Python dependencies from assets/requirements.txt, valid Alibaba Cloud
  credentials, and network access to Flink OpenAPI (2021-10-28). Aliyun CLI is
  optional and only used for environment diagnostics/credential inspection.
  Verified targets: models qwen3-max and qwen3.5-plus; execution engines
  qwen-code, qoder, and openclaw.
metadata:
  domain: aiops
  owner: flink-team
  contact: flink-team@alibaba-inc.com
---

# Alibaba Cloud Flink Instance Manage

Use this skill to operate Alibaba Cloud Flink instances, namespaces, and tags
through `scripts/instance_ops.py`.

## Execution Entrypoint Lock (mandatory)

All resource operations in this skill **must** be executed through:

```bash
python scripts/instance_ops.py <command> ...
```

Hard constraints:

- Do not execute resource mutations with raw product commands such as
  `aliyun foasconsole ...` or `aliyun ververica ...`.
- Do not bypass `scripts/instance_ops.py` by calling OpenAPI/SDK snippets directly
  during task execution.
- `aliyun version` and `aliyun configure list` are allowed only as environment
  diagnostics, not as operation execution entrypoints.

If `scripts/instance_ops.py` cannot run (for example `ModuleNotFoundError`):

1. Follow `references/python-environment-setup.md` to install dependencies and verify.
2. Re-run `python scripts/instance_ops.py describe_regions`.
3. If still blocked, stop and report the blocker; do not fallback to raw `aliyun foasconsole` operations.

## Core lifecycle fast-path (high priority)

When user asks an end-to-end lifecycle flow (create/tag/query/delete), execute this
strictly in order on the **same instance context**:

1. `create` (with `--confirm`) -> capture created `InstanceId`
2. wait/read-back (`describe`) until target instance is visible/operable
3. `tag_resources` -> `list_tags` verification
4. `untag_resources` -> `list_tags` verification
5. `describe` verification for target instance
6. `delete` (with `--force_confirmation`) -> `describe` absence verification

Hard rules for lifecycle flows:

- Do not switch to another pre-existing instance in the middle of a flow unless
  user explicitly approves the switch.
- If target instance is still provisioning, poll with read checks first; do not
  claim tag/delete success without readiness verification.
- If the same-instance chain cannot be completed, mark `incomplete` and report
  blocker/remediation; never report completed with partial substitution.

## 0) Trigger gate (mandatory)

Apply this skill only when both are true:

1. User intent is a Flink cloud resource operation (`create`, `describe`,
   `modify`, `delete`, `renew`, `convert`, namespace ops, tag ops, cleanup).
2. Request clearly targets Flink instance scope (for example Flink `instance_id`,
   namespace under a Flink instance, Flink instance tags, Flink instance billing
   or spec changes, Flink instance lifecycle flow).

Do not trigger for unrelated prompts, generic coding questions, or tasks that do
not require Flink cloud operations.
Do not trigger for non-Flink Alibaba Cloud resources (for example ECS/RDS/SLB
instances, VPC-only operations, or generic "Aliyun instance" requests without
Flink context).

If request intent is ambiguous, ask one clarification question before running
any command.

## 1) Quick checks

1. Verify toolchain and credentials before any resource operation.
2. Use explicit user-provided parameters for region, instance, namespace, and spec.
3. Run read operations first when a write operation depends on current resource state.

```bash
aliyun version
aliyun configure list
```

Use `scripts/instance_ops.py` as the only resource-operation execution entrypoint.
For toolchain verification, run a read-only operation instead of `--help`:

```bash
python scripts/instance_ops.py describe_regions
```

If CLI is missing or outdated, read `references/cli-installation-guide.md`.
If permission errors appear, read `references/ram-policies.md`.

### Credential setup (default credential chain only)

Do not export or hardcode AccessKey ID/Secret in scripts or shell commands.
Use Alibaba Cloud default credential chain instead:

```bash
# Option A (recommended): use default CLI profile credentials
aliyun configure
aliyun configure list
```

Option B: when running on Alibaba Cloud compute environments, attach a RAM role
(ECS/ACK/FC/SAE, etc.) and rely on role-based temporary credentials.

## 2) Mandatory safety rules

For any write operation, confirmation flags are mandatory:

Use the single source of truth in
`references/required-confirmation-model.md` (section 2.2) for the
command-to-flag mapping.

Additional guardrails (must follow):

- Never auto-switch write operation type after a failure.
- Any fallback that changes operation type requires explicit user approval first.
- Never substitute target resource (instance/namespace) in a lifecycle flow without
  explicit user approval.
- Never assume default region; always require `--region_id`.
- Never claim success from write response only.

If a required flag is missing:

1. Do not execute.
2. Rebuild the command with the correct flag.
3. Execute once.

Never use blind retries. Follow the retry policy in `references/output-handling.md`.

## 3) End-to-end execution protocol

Before running any mutating command (`create`, `modify_spec`, `delete`,
namespace writes, tag writes):

1. Read `references/required-confirmation-model.md`
2. Read `references/output-handling.md`
3. Use command examples in `references/core-execution-flow.md`
4. For create-namespace, tag, delete-cleanup, follow `references/e2e-playbooks.md`

Execution steps:

1. **Plan**: list target resources and expected final state.
2. **Execute**: run write command with required confirmation flag.
3. **Verify**: run follow-up read command and validate state change.
4. **Report**: provide closure output including:
   - command result (`success` / `error.code`)
   - verification evidence (read-back result)
   - final status (`completed` / `incomplete`) with reason

## 4) Batch execution protocol

When user asks batch operations (or provides multiple IDs/names):

1. Keep deterministic order (input order).
2. Execute and verify each item independently.
3. Continue processing remaining items after a single-item failure unless user
   explicitly requires all-or-nothing.
4. Return per-item summary: `item -> write result -> read-back verification`.

## 5) Idempotency and consistency rules

- Maximum attempts for same write command: 2 (initial + one corrected retry).
- `AlreadyExists` can be treated as success only if read-back matches expected
  target state.
- `NotFound` during delete/untag can be treated as success only if read-back
  confirms absence.
- For eventual consistency, perform read-back up to 3 checks before deciding
  retry/fail.

## 6) Completion gate (mandatory)

A write task is complete only when all checks pass:

1. Write command returns `success: true` (or validated idempotent equivalent).
2. Follow-up read confirms expected state.
3. Final output states what changed and how it was verified.

If any check fails, mark task as incomplete and provide remediation guidance.

## 7) References

- `references/quick-start.md`: compact command checklist
- `references/required-confirmation-model.md`: confirmation gate and flag mapping
- `references/core-execution-flow.md`: operation command flow and examples
- `references/e2e-playbooks.md`: end-to-end playbooks for key scenarios
- `references/output-handling.md`: output parsing and retry handling
- `references/related-apis.md`: API and CLI mapping
- `references/ram-policies.md`: required RAM permissions and policy guidance
- `references/verification-method.md`: post-execution verification steps
- `references/acceptance-criteria.md`: expected success and failure behaviors
- `references/python-environment-setup.md`: Python runtime and dependency setup
- `references/cli-installation-guide.md`: Aliyun CLI install and configuration
