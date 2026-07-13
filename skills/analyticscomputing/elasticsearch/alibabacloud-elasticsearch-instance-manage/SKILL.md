---
name: alibabacloud-elasticsearch-instance-manage
description: |
  Alibaba Cloud Elasticsearch Instance & Config Management Skill. Use for managing the lifecycle of an Elasticsearch instance (create, query, list, restart, upgrade/downgrade, node info) and for managing instance-side config such as snapshot backup and analyzer dictionaries.
  Triggers: "elasticsearch", "ES instance", "elasticsearch instance", "create ES", "query ES instance", "restart ES", "ES node", "cluster node", "upgrade ES", "downgrade ES", "scale ES", "resize ES", "ES snapshot", "ES backup", "snapshot setting", "create snapshot", "ES dict", "IK dict", "hot dict", "synonyms dict", "aliws dict", "analyzer dictionary"
---

# Elasticsearch Instance & Config Management

Manage Alibaba Cloud Elasticsearch instances and instance-side configuration via the Aliyun CLI: instance lifecycle (create / describe / list / restart / upgrade / downgrade / node info) and instance config (snapshot backup, analyzer dictionaries).

This skill uses **intent routing**: this file identifies the user's intent and dispatches to the relevant module document. Read the matched module document fully before generating any CLI command.

## Architecture

```
Alibaba Cloud Elasticsearch Management
├── Instance Lifecycle           --> references/instance-manage.md
│   ├── createInstance           (Create Instance)
│   ├── DescribeInstance         (Query Instance Details)
│   ├── ListInstance             (List Instances)
│   ├── RestartInstance          (Restart Instance)
│   ├── UpdateInstance           (Upgrade / Downgrade)
│   ├── ListAllNode              (Query Cluster Node Info)
│   ├── UpdateAdminPassword      (Update Admin Password)
│   ├── UpdateDescription        (Update Instance Name)
│   ├── UpdateInstanceChargeType (Convert pay-as-you-go to subscription)
│   ├── UpgradeInfo              (Query available upgrade versions)
│   ├── UpgradeEngineVersion     (Upgrade ES version / kernel patch)
│   ├── ListActionRecords        (Query change records / upgrade progress)
│   └── ContinueEsVersionUpgrade (Continue gray upgrade of remaining nodes)
├── Instance Config              --> references/config-manage.md
│   ├── Snapshot Management
│   │   ├── UpdateSnapshotSetting    (Set auto-snapshot policy)
│   │   ├── DescribeSnapshotSetting  (Query auto-snapshot policy)
│   │   └── CreateSnapshot           (Trigger one-shot snapshot)
│   ├── Dict Management
│   │   ├── ListDicts                (List analyzer dicts)
│   │   ├── UpdateDict               (Cold-update IK dict)
│   │   ├── UpdateHotIkDicts         (Hot-update IK dict)
│   │   ├── UpdateSynonymsDicts      (Update synonyms dict)
│   │   └── UpdateAliwsDict          (Update AliNLP dict)
│   ├── Kibana Settings
│   │   ├── DescribeKibanaSettings   (Query Kibana config)
│   │   └── UpdateKibanaSettings     (Update Kibana language)
│   └── ES Cluster YML
│       └── UpdateInstanceSettings   (Update YML config — triggers restart)
└── Plugin Management            --> references/plugin-manage.md
    ├── ListPlugins              (List system plugins)
    ├── ListUserPlugin           (List user custom plugins)
    ├── InstallSystemPlugin      (Install system plugin)
    ├── UninstallPlugin          (Uninstall system plugin)
    ├── PluginAnalysis           (Upload custom plugin to library)
    └── InstallUserPlugins       (Install user custom plugins)
```

---

## Intent Routing

Match the user request to the FIRST matching row, then load the listed module doc and follow its API spec.

| If the user wants to ... (keywords) | Module | Required reading | Key APIs |
|---|---|---|---|
| Create / describe / list / restart instance, upgrade / downgrade configuration, query nodes, scale, resize, query cluster status, change password, reset password, rename instance, update description, convert charge type, pay-as-you-go to subscription, postpaid to prepaid, upgrade version, upgrade engine, kernel patch, aliVersion, check available version, upgrade info, change records, action records, upgrade progress, change history, continue upgrade, resume upgrade, gray upgrade, continue gray, finish upgrade | Instance Lifecycle | [references/instance-manage.md](references/instance-manage.md) | createInstance, DescribeInstance, ListInstance, RestartInstance, UpdateInstance, ListAllNode, UpdateAdminPassword, UpdateDescription, UpdateInstanceChargeType, UpgradeInfo, UpgradeEngineVersion, ListActionRecords, ContinueEsVersionUpgrade |
| Configure / view / trigger snapshot, automatic backup, manual backup, snapshot cron | Config — Snapshot | [references/config-manage.md#snapshot-management](references/config-manage.md#snapshot-management) | UpdateSnapshotSetting, DescribeSnapshotSetting, CreateSnapshot |
| Manage analyzer dictionaries: IK main / stopword (cold or hot update), synonyms, AliWS / AliNLP | Config — Dict | [references/config-manage.md#dict-management](references/config-manage.md#dict-management) | ListDicts, UpdateDict, UpdateHotIkDicts, UpdateSynonymsDicts, UpdateAliwsDict |
| Query / view / update Kibana settings, Kibana configuration, Kibana language | Config — Kibana | [references/config-manage.md#kibana-settings](references/config-manage.md#kibana-settings) | DescribeKibanaSettings, UpdateKibanaSettings |
| Update ES YML configuration, elasticsearch.yml, CORS, reindex whitelist, thread pool queue size, audit log, watcher, auto create index, update strategy | Config — ES Cluster YML | [references/config-manage.md#es-cluster-yml-configuration](references/config-manage.md#es-cluster-yml-configuration) | UpdateInstanceSettings |
| List / query plugins, system plugins, user plugins, custom plugins, plugin status, install plugin, uninstall plugin, remove plugin, upload plugin, plugin analysis | Plugin Management | [references/plugin-manage.md](references/plugin-manage.md) | ListPlugins, ListUserPlugin, InstallSystemPlugin, UninstallPlugin, PluginAnalysis, InstallUserPlugins |

> If multiple intents are present, handle them sequentially: route → execute → verify → next route.
> If the intent does not match any row, ask the user to clarify; do NOT guess an API.

---

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

---

## Observability

> **[MUST]** Every business `aliyun` CLI command invocation MUST carry the per-command flag:
> ```
> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/{session-id}
> ```
> where `{session-id}` is the per-skill-session identifier defined below. Identification of this skill is achieved **exclusively** via the per-command `--user-agent` flag on business CLI commands; no CLI-level / session-level user-agent injection mechanism is used.

### session-id generation rule

Generate `{session-id}` ONCE at the start of the skill session and reuse it for every business CLI command in that session.

**Format requirement: 32-character lowercase hexadecimal string (no hyphens)** — e.g. `0123456789abcdef0123456789abcdef`.

```bash
# Preferred (macOS / Linux, openssl is universally available):
SESSION_ID=$(openssl rand -hex 16)

# Fallback 1 — Python:
SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')

# Fallback 2 — pure shell (no external tool):
SESSION_ID=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')
```

- Format: **32 lowercase hex characters, no hyphens, no prefix**. `uuidgen` output (with hyphens) is NOT acceptable — strip hyphens via `tr -d '-' | tr 'A-Z' 'a-z'` if you fall back to it.
- The same `SESSION_ID` MUST be embedded in the `--user-agent` of EVERY business CLI command this session emits.
- Do NOT regenerate `SESSION_ID` on retry — only regenerate at session boundaries (a new skill invocation starts a new session).

### per-command --user-agent format

| Command kind | --user-agent? | Value |
|---|---|---|
| **Business API CLI** (e.g. `aliyun elasticsearch create-instance`, `aliyun elasticsearch list-dicts`, …) | **REQUIRED** | `AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` |
| **System / tool CLI** (e.g. `aliyun configure`, `aliyun configure list`, `aliyun version`, `aliyun plugin update`, `aliyun help`) | **FORBIDDEN** | These commands do NOT support `--user-agent` — never attach the flag. |

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**

> **Security Rules (MUST FOLLOW):**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** accept AK/SK provided directly by users in the conversation
> - **ONLY** read credentials from environment variables or pre-configured CLI profiles
>
> **CRITICAL: Handling User-Provided Credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "My AK is xxx, SK is yyy"):
> 1. **STOP immediately** — do NOT execute any command
> 2. **Reject the request politely** with the following message:
>    ```
>    For your account security, please do not provide Alibaba Cloud AccessKey ID and AccessKey Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Interactive configuration via aliyun configure (Recommended)
>        aliyun configure
>        # Enter AK/SK as prompted; credentials will be stored securely in the local config file
>
>    Method 2: Configure via environment variables
>        export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
>        export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
>
>    After configuration, please retry your request.
>    ```
> 3. **Do NOT proceed** with any Alibaba Cloud operations until credentials are properly configured
>
> **Check CLI configuration**:
> ```bash
> aliyun configure list
> ```
> Look for a valid profile (AK, STS, or OAuth identity). **If none exists, STOP here.**

---

## Global Conventions

These conventions apply to EVERY CLI command produced by this skill, regardless of which module is routed.

### Common CLI Arguments

| Item | Convention |
|---|---|
| Timeouts | All commands append `--connect-timeout 3 --read-timeout 10`. Write operations (create / update / restart / snapshot / dict update) use `--read-timeout 30`. |
| `--region` | REQUIRED and MUST be explicitly provided by the user. NEVER guess. NEVER use a default region. |
| `--instance-id` | REQUIRED for any per-instance operation. MUST be explicitly provided by the user. |
| `--user-agent` | **Scope: business API commands ONLY** (e.g. `aliyun elasticsearch ...`). Such commands MUST explicitly pass `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` (see [Observability](#observability)). **System / tool commands** (`aliyun configure`, `aliyun version`, `aliyun plugin update`, `aliyun help`, etc.) **MUST NOT** carry `--user-agent` — these commands do not support the flag. |
| `--body` | All ROA APIs accept `--body '<JSON>'` for complex request bodies. Use `--body $(cat payload.json)` to read from a file. |
| `--cli-query` | Prefer JMESPath projection (`--cli-query "Result[].{...}"`) for readable outputs in list-style APIs. |

### Idempotency for Write Operations

For write APIs (`createInstance`, `RestartInstance`, `UpdateInstance`, `CreateSnapshot`, `UpdateSnapshotSetting`, `UpdateDict`, `UpdateHotIkDicts`, `UpdateSynonymsDicts`, `UpdateAliwsDict`, `UpdateKibanaSettings`, `UpdateInstanceSettings`, `InstallSystemPlugin`, `UninstallPlugin`, `UpdateInstanceChargeType`, `UpgradeEngineVersion`) you **MUST** use `--client-token`.

- Format: UUID. Generate via `uuidgen` (or PowerShell `[guid]::NewGuid()`); fall back to `idem-<timestamp>-<semantic>` if `uuidgen` is unavailable. Never abort the workflow because of an unavailable command.
- On timeout / failure, retry with **the same** `clientToken`. Wait ~10 seconds before retrying.
- Duplicate calls with the same `clientToken` will not re-execute the operation.

```bash
CLIENT_TOKEN=$(uuidgen)   # reuse on retry
```

---

## RAM Policy

The RAM principal needs the union of permissions for the modules it will use. See [references/ram-policies.md](references/ram-policies.md) for full policy JSON.

**Minimum required actions:**

| Module | Actions |
|---|---|
| Instance Lifecycle | `elasticsearch:CreateInstance`, `elasticsearch:DescribeInstance`, `elasticsearch:ListInstance`, `elasticsearch:RestartInstance`, `elasticsearch:UpdateInstance`, `elasticsearch:ListAllNode` |
| Snapshot Management | `elasticsearch:UpdateSnapshotSetting`, `elasticsearch:DescribeSnapshotSetting`, `elasticsearch:CreateSnapshot` |
| Dict Management | `elasticsearch:ListDicts`, `elasticsearch:UpdateDict`, `elasticsearch:UpdateHotIkDicts`, `elasticsearch:UpdateSynonymsDicts`, `elasticsearch:UpdateAliwsDict` |

> Snapshot/Dict modules also need OSS read access to the bucket holding the dict files.

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for module-by-module verification steps.

**Quick check after instance lifecycle changes:**

```bash
aliyun elasticsearch describe-instance \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --cli-query "Result.status" \
  --connect-timeout 3 \
  --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

Expected status: `active`.

**Quick check after snapshot/dict changes:**

```bash
# Snapshot setting changed
aliyun elasticsearch describe-snapshot-setting \
  --region <RegionId> --instance-id <InstanceId> \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Dict list refreshed (analyzerType: IK | IK_HOT | SYNONYMS | ALIWS)
aliyun elasticsearch list-dicts \
  --region <RegionId> --instance-id <InstanceId> \
  --analyzer-type <TYPE> \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

## Reference Links

| Reference | Description |
|---|---|
| [references/instance-manage.md](references/instance-manage.md) | Instance lifecycle APIs (create / describe / list / restart / update / nodes) |
| [references/config-manage.md](references/config-manage.md) | Instance config APIs (snapshot + analyzer dicts) |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/verification-method.md](references/verification-method.md) | Verification steps |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct / incorrect patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/node-specifications-by-region.md](references/node-specifications-by-region.md) | Node specs by region and role |
| [Elasticsearch Product Page](https://www.aliyun.com/product/bigdata/elasticsearch) | Official product page |
| [Elasticsearch API Reference](https://next.api.aliyun.com/product/elasticsearch) | Official API reference |