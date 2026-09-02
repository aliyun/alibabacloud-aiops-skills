---
name: alibabacloud-ddoscoo-port-configuration-backup
description: "Export, import, and restore Alibaba Cloud DDoS Pro manual non-website TCP and UDP port forwarding rules and their portable configuration through Aliyun CLI. Use for non-website port backup, migration, reuse on another instance, or recovery; do not use for website-generated rules, website or infrastructure protection, or runtime traffic and attack data."
---

# Alibaba Cloud DDoS Pro Port Configuration Backup and Restore

## Scenario

This Skill is the entry point and router for backing up and restoring manual
non-website DDoS Pro port configuration. It confirms the operation boundary,
loads the applicable business workflow, and enforces authentication,
permissions, parameters, safety, and success criteria.

The export and import procedures are maintained only in
[`references/export-workflow.md`](references/export-workflow.md) and
[`references/import-workflow.md`](references/import-workflow.md). Do not
reconstruct or duplicate those procedures here.

The portable scope includes manual TCP and UDP forwarding rules and their
configuration, plus the instance-level non-website AI switch and mode. The AI
policy applies to the IP object: the product has no independent port object, so
all non-website ports on one instance share the same setting. Each port backup
records that shared desired state, but it is not a port-exclusive setting.

Exclude website-derived automatic rules, scenario-specific protection,
Protection for Infrastructure, website protection, and runtime traffic,
connections, attacks, blackholes, and logs.

### Architecture

`user request -> parameter and authorization boundary -> export or import workflow -> Aliyun CLI -> one-port YAML desired state -> exact readback verification`

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version`. If the CLI is missing or older than 3.3.3, follow
> [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
> and continue only after the version check succeeds.

**Pre-check: Aliyun CLI plugin update required**

> Run `aliyun configure set --auto-plugin-install true` and then
> `aliyun plugin update`.

## Environment

Set no credential environment variables. Use only an existing Aliyun CLI
profile explicitly selected by the user. Never read, display, or persist
credential environment variables.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (for example, `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ~~~bash
> aliyun configure list
> ~~~
> Check the output for a valid profile (AK, STS, or OAuth identity). The exact
> profile selected by the user must appear in the output. Never substitute a
> similar name or silently use the default profile.
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside this session** with `aliyun configure`
> 3. Return only after `aliyun configure list` shows a valid profile

Every cloud API call must explicitly carry the confirmed `--profile`,
`--region`, and required User-Agent. The profile name is command-local and
must not appear in backups, results, or reports.

## RAM Policy

Export requires read-only permissions. Import adds temporary, least-privilege
write permissions only for the selected workflow. Read
[`references/ram-policies.md`](references/ram-policies.md) for the complete
Action sets.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

A permission failure means the state is unknown. Never reinterpret it as an
empty configuration, disabled feature, or unsupported capability, and never
change the request route to bypass the permission boundary.

## Parameter Confirmation

Before the first cloud API call, confirm every user-customizable parameter
required by the selected mode. Do not assume a profile, region, resource-group
scope, protocol, or target instance. An unspecified export directory uses the
documented default. The selected workflow owns all later confirmation points.

| Parameter | Requirement | Description | Default |
|---|---|---|---|
| Operation | Required | `export` or `import` | None |
| CLI profile | Required | Existing profile used explicitly on every call | None |
| Region | Required | One DDoS Pro control-plane region per run: `cn-hangzhou` for Mainland China or `ap-southeast-1` outside Mainland China | None |
| Resource-group scope | Required | One exact resource group or an explicitly confirmed all-accessible-groups scope | None |
| Backup scope | Export | `single_port`, `multiple_ports`, `instance`, or `account`; always one YAML per port | None |
| Source | Export | Exact IP or instance ID; account scope follows the export workflow | None |
| Port selector | Port export | Protocol and frontend port for every manual rule; a bare port number follows limited discovery | None |
| Input or output path | Mode-specific | Export defaults to `./ddoscoo-port-backups/`; import requires one or more one-port YAML files | Export default |
| Target instance | Import | Target instance for every YAML; use the only usable EIP directly, otherwise ask the user to choose | None |
| Import authorization | Import | Explicit request to restore validated YAML to the selected target instance and EIP | None |
| Shared non-website AI decision | Conditional import | Required only when backup and target shared values conflict | None |

## Observability

When loading this Skill, generate one random 32-character lowercase hexadecimal
session ID and reuse it for every cloud API call in the same export or import.

Every `aliyun` command that calls a cloud API must include:

~~~
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Example:

~~~bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 \
  --region '<REGION>' --profile '<PROFILE>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-port-configuration-backup/{session-id}
~~~

Local management commands (`aliyun version`, `aliyun configure list`,
`aliyun configure set`, and `aliyun plugin update`) do not accept the
User-Agent flag. Do not use global AI mode or an environment variable to set
the User-Agent.

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any cloud API call,
> confirm all user-customizable parameters required by the selected mode. If
> only a port number is provided, the export workflow may perform one limited
> ownership discovery; confirm the resolved protocol and port identity before
> reading per-port details.

1. Select exactly one mode: export configuration, or import/restore from a
   specified backup.
2. Complete the CLI, authentication, RAM, and parameter gates before any cloud
   API call.
3. Load only the references required by that mode:
   - Export: read and execute
     [`references/export-workflow.md`](references/export-workflow.md) in full.
   - Import or restore: read and execute
     [`references/import-workflow.md`](references/import-workflow.md) in full.
   - Both modes use
     [`references/verification-method.md`](references/verification-method.md)
     for normalization and success decisions.
   - Load the schema, coverage matrix, or command index only when that detail is
     needed.
4. Complete the selected workflow and exact readback. Never use a process exit
   code or RequestId as a substitute for configuration equality.

### Reference authority

- `export-workflow.md` and `import-workflow.md` own business order,
  confirmation points, stop conditions, and artifacts.
- `related-commands.md` owns command and parameter spelling, but cannot expand
  the restore scope.
- `verification-method.md` owns normalization and success decisions; it cannot
  add business operations.
- `acceptance-criteria.md` owns package and release checks, not runtime steps.

If two references genuinely conflict, resolve them by this authority order. If
the conflict remains, stop before the affected cloud write and report it
precisely; do not guess.

## Non-negotiable Gates

- Operate only on confirmed manual non-website ports. Automatic rules may be
  used to detect identity conflicts, but never written or deleted.
- Non-website AI is an instance-shared policy. If it conflicts with the target,
  explain that all non-website ports on the instance are affected and obtain
  the user's explicit choice before any write for that instance.
- Missing, denied, timed-out, or unknown values are not empty, disabled, or
  inapplicable values.
- Use only commands verified in the references. Never guess an Action,
  parameter, API version, or request body.
- Never save a profile name, AccessKey, token, Authorization value, Cookie,
  signature, signed URL, or request header in any artifact.
- If a write result is uncertain, read the current state before deciding
  whether a retry is safe.
- Mark an item successful only after fresh readback exactly matches the
  normalized desired state.

## Completion

Use [`references/verification-method.md`](references/verification-method.md).
Import succeeds only when every applicable field in the selected scope matches
after final readback. Report every other state item by item.

Import creates no result file by default. Save one only when the user requests
it. Never delete the input backup. After import, remind the user to revoke
temporary write permissions.

## References

| Reference | Read when |
|---|---|
| [Export workflow](references/export-workflow.md) | Any export, backup, or source capture; authoritative export procedure |
| [Import workflow](references/import-workflow.md) | Any import, migration recovery, or reuse on another instance; authoritative import procedure |
| [Verification method](references/verification-method.md) | Export delivery and import success decisions |
| [One-port YAML schema](references/schema.md) | Building or validating a backup |
| [Coverage matrix](references/coverage-matrix.md) | Determining capability scope and portability |
| [Related commands](references/related-commands.md) | Constructing or checking a verified command |
| [RAM policies](references/ram-policies.md) | Authorization or any permission failure |
| [Acceptance criteria](references/acceptance-criteria.md) | Package, test, release, or delivery review |
| [CLI installation guide](references/cli-installation-guide.md) | Missing CLI, old version, plugin, or profile troubleshooting |
