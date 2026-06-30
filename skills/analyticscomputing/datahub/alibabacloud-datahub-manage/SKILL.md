---
name: alibabacloud-datahub-manage
description: |
  Alibaba Cloud DataHub full-lifecycle resource management skill.
  Use for creating, querying, updating, and deleting DataHub Projects, Topics, and Subscriptions via Aliyun CLI.
  Triggers: "datahub", "datahub project", "datahub topic", "datahub subscription", "datahub resource management", "streaming data management".
---

# DataHub Resource Management

Manage the full lifecycle of Alibaba Cloud DataHub resources (Project → Topic → Subscription) using the Aliyun CLI plugin mode.

**Architecture**: `Region → Project → Topic → Subscription`

---

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

This skill requires DataHub permissions. See `references/ram-policies.md` for the full policy document.

Required actions: `dhs:ListProjects`, `dhs:CreateProject`, `dhs:GetProject`, `dhs:UpdateProject`, `dhs:DeleteProject`, `dhs:ListTopics`, `dhs:CreateTopic`, `dhs:GetTopic`, `dhs:UpdateTopic`, `dhs:DeleteTopic`, `dhs:ListSubscriptions`, `dhs:CreateSubscription`, `dhs:GetSubscription`, `dhs:DeleteSubscription`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `region` | Yes | Target region for DataHub resources | — (must confirm) |
| `project-name` | Yes | DataHub project name (3-32 chars, letter start, alphanumeric + underscore) | — |
| `topic-name` | Yes (for Topic ops) | Topic name (3-128 chars) | — |
| `record-type` | Yes (for create-topic) | BLOB or TUPLE | — |
| `shard-count` | Yes (for create-topic) | Number of shards | — |
| `lifecycle` | Yes (for create-topic) | Data retention in days | — |
| `record-schema` | Conditional | Required when record-type is TUPLE | — |
| `application` | Yes (for create-subscription) | Application description (max 256 chars) | — |
| `subscription-id` | Optional | Manual subscription ID (4-40 chars, lowercase) | Auto-generated |

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun datahub list-projects --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

---

## Core Workflow

### Resource Dependency

```
Region
  └── Project
        └── Topic (BLOB / TUPLE)
              └── Subscription
```

**Creation order**: Project → Topic → Subscription
**Deletion order** (reverse): Subscription → Topic → Project

---

### Step 1: Create Project

```bash
# 1.1 List existing projects to check name conflicts
aliyun datahub list-projects \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}

# 1.2 Create project
aliyun datahub create-project \
  --region <region> \
  --project-name <project-name> \
  --comment "<project-description>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}

# 1.3 Verify creation
aliyun datahub get-project \
  --region <region> \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

---

### Step 2: Create Topic

#### 2.1 Create BLOB Topic (binary data)

```bash
aliyun datahub create-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <blob-topic-name> \
  --comment "<topic-description>" \
  --shard-count <shard-count> \
  --record-type BLOB \
  --lifecycle <days> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

#### 2.2 Create TUPLE Topic (structured data with schema)

```bash
aliyun datahub create-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <tuple-topic-name> \
  --comment "<topic-description>" \
  --shard-count <shard-count> \
  --record-type TUPLE \
  --lifecycle <days> \
  --record-schema '{"fields":[{"name":"<field_name>","type":"STRING","notnull":"false"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

#### 2.3 Verify topic

```bash
aliyun datahub get-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

#### 2.4 Update topic description

```bash
aliyun datahub update-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --comment "<new-description>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

---

### Step 3: Create Subscription

```bash
# Option A: Auto-generated subscription-id
aliyun datahub create-subscription \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --application "<application-description>" \
  --comment "<subscription-description>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}

# Option B: Manual subscription-id
aliyun datahub create-subscription \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --application "<application-description>" \
  --comment "<subscription-description>" \
  --subscription-id <subscription-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

Verify:
```bash
aliyun datahub get-subscription \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --subscription-id <subscription-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

---

### Step 4: Resource Cleanup

**[MUST] Delete in reverse dependency order.**

> **⚠️ DESTRUCTIVE OPERATION — User Confirmation Required**
>
> Before executing ANY delete command (`delete-subscription`, `delete-topic`, `delete-project`),
> you **MUST** explicitly list the resources to be deleted and ask the user for confirmation.
> **Do NOT proceed until the user explicitly approves the deletion.**
>
> Example prompt to user:
> > "I am about to delete the following resources (this action is **irreversible**):
> > - Subscription: `<subscription-id>` on topic `<topic-name>`
> > - Topic: `<topic-name>` in project `<project-name>`
> > - Project: `<project-name>`
> >
> > Do you confirm? (yes/no)"

#### 4.1 Delete Subscription

```bash
aliyun datahub delete-subscription \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --subscription-id <subscription-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

#### 4.2 Delete Topic (pre-check: no active subscriptions)

```bash
# Pre-check
aliyun datahub list-subscriptions \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}

# Delete topic
aliyun datahub delete-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

#### 4.3 Delete Project (pre-check: no active topics)

```bash
# Pre-check
aliyun datahub list-topics \
  --region <region> \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}

# Delete project
aliyun datahub delete-project \
  --region <region> \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/{session-id}
```

> **⚠️ WARNING**: Deleting a Project removes all its Topics, data, and Subscriptions. This operation is **irreversible**. Always obtain explicit user confirmation before execution.

---

## Success Verification

See `references/verification-method.md` for detailed verification steps for each operation.

---

## Best Practices

1. **Always verify after creation** — Use `get-project`, `get-topic`, `get-subscription` to confirm resources exist.
2. **Follow dependency order** — Create: Project → Topic → Subscription; Delete: reverse.
3. **Pre-check before deletion** — List child resources before deleting parent resources.
4. **Use meaningful names** — Follow naming conventions (see `references/related-commands.md`).
5. **Set appropriate lifecycle** — Configure data retention (`--lifecycle`) based on business requirements.
6. **Choose correct record-type** — Use BLOB for binary streams, TUPLE for structured data requiring schema.
7. **Confirm parameters** — Always confirm region, project name, and other user-specific values before execution.

---

## Reference Links

| Document | Description |
|----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/related-commands.md](references/related-commands.md) | Full CLI command reference |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Testing acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [DataHub Product Docs](https://www.aliyun.com/product/datahub) | DataHub product introduction |
| [DataHub Help Center](https://help.aliyun.com/zh/datahub/) | Detailed usage guide |
