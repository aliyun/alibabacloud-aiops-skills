---
name: alibabacloud-sls-index-config-management
description: |
  Alibaba Cloud SLS (Simple Log Service) index configuration manager skill. Use this skill to help users inspect, create, update, or delete a Logstore index, generate an index configuration from user-provided structured log samples, and optimize an existing index configuration for given query/SQL workloads, write throughput, and storage cost — all through the aliyun CLI.
  Triggers: "SLS 索引", "索引配置", "create index", "update index", "delete index", "generate index", "optimize index", "全文索引", "字段索引", "log index config", "aliyun sls index".
---

# Alibaba Cloud SLS Index Configuration Manager

## Scenario Description

Use this skill for SLS Logstore index configuration.

This file only covers trigger-time setup, routing, and cross-scenario safety. Read only the
reference document needed for the user's request.

---

## Prerequisites

These checks apply when executing cloud operations; log-sample generation can run offline.

### Install Aliyun CLI

Run `aliyun version` to verify the version is `>= 3.3.8`. If not installed or outdated, follow [references/cli-installation-guide.md](references/cli-installation-guide.md) to install or update.

### Check Alibaba Cloud credentials configured

Run `aliyun configure list` to check if credentials are configured.
If no valid profile is shown, **STOP** here and ask the user to run `aliyun configure` outside of this session.

**Security rules:**

- **NEVER** read, echo, or print AK/SK values
- **NEVER** ask the user to paste AK/SK into the conversation
- **ONLY** use `aliyun configure list` to check credential status

---

## RAM Permission Requirements

On `Unauthorized` error, surface [references/ram-policies.md](references/ram-policies.md) to the user. Do **not** retry with a different account without explicit confirmation.

---

## Observability

Run [scripts/user_agent.py](scripts/user_agent.py) once per session to generate the UA, then reuse
it for all cloud API commands, including request-only dry runs:

```bash
SLS_INDEX_USER_AGENT="$(python3 scripts/user_agent.py)" || exit 1
aliyun sls get-index --project <project> --logstore <logstore> \
  --user-agent "$SLS_INDEX_USER_AGENT"
```

Example generated UA:

```text
AlibabaCloud-Agent-Skills/alibabacloud-sls-index-config-management/59ae5afe2075fc3dc1f0e7e39539c902 skill-version/0.0.1
```

---

## Routing the Request

Follow the reference matching the user's request:

| If the user wants to …                                                                                                      | Go to                                                                            |
| --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| View / create / update / delete an index, or change a field, TTL, `max_text_len`, full-text, automatic index discovery, log_reduce, etc. | [references/manage-index-config.md](references/manage-index-config.md)           |
| Build an index for a Logstore that has none, or rebuild from scratch using user-provided structured log samples             | [references/generate-index-from-logs.md](references/generate-index-from-logs.md) |
| Adjust an existing index to support a new query / SQL, reduce cost, or improve write throughput                             | [references/optimize-index-config.md](references/optimize-index-config.md)       |

Mixed requests are common (e.g. "generate an index for these logs and then update it on Logstore X"). Read the relevant scenario docs in order.

---

## Global Rules

- **No writes without the scenario reference.** Before any write operation, read the relevant reference document and follow its confirmation, full-body, rollback, and timing rules.
- **Preserve discovered indexes.** Keep `line.auto_text_keys` unchanged on updates unless explicitly requested otherwise; see [automatic index discovery](references/manage-index-config.md#automatic-index-discovery).
- **Use exact SLS CLI names.** Product is `sls`; subcommands and flags are kebab-case. Use [references/acceptance-criteria.md](references/acceptance-criteria.md) only when validating command shape or debugging CLI invocation issues.

---

## Reference Documents

| Document                                                                         | Description                                                                    |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [references/manage-index-config.md](references/manage-index-config.md)           | Index config format and get / create / update / delete command examples        |
| [references/generate-index-from-logs.md](references/generate-index-from-logs.md) | Infer a complete index configuration from user-provided structured log samples |
| [references/optimize-index-config.md](references/optimize-index-config.md)       | Optimize an existing index for query/SQL workload, cost, and write throughput  |
| [references/related-apis.md](references/related-apis.md)                         | `GetIndex` / `CreateIndex` / `UpdateIndex` / `DeleteIndex` API & CLI reference |
| [related_apis.yaml](related_apis.yaml)                                           | Machine-readable dependent API metadata for this skill                         |
| [references/ram-policies.md](references/ram-policies.md)                         | Minimum and complete RAM policies for index management                         |
| [references/acceptance-criteria.md](references/acceptance-criteria.md)           | CLI invocation acceptance tests                                                |
| [references/cli-installation-guide.md](references/cli-installation-guide.md)     | Aliyun CLI install, auth modes, profiles                                       |
