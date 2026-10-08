---
name: alibabacloud-sls-dashboard
description: "Design and manage Alibaba Cloud SLS dashboards and visualizations. Use when creating or editing dashboards and charts, explaining visualization settings, troubleshooting display issues, or managing scheduled dashboard reports."
metadata:
  name_cn: SLS Dashboard
  description_cn: Design, create, edit, validate, and publish SLS dashboards and manage scheduled Report subscriptions.
---

# SLS Dashboards

Design dashboards around the user's questions and verified SLS data. Resolve script
paths relative to this file.

## Prerequisites

Explanation, offline construction and validation do not require CLI setup or cloud
credentials. Offline scripts still need the [Python dependencies](references/cli-installation-guide.md#python-dependencies).
Before the first build or cloud operation, run `python3 scripts/doctor.py` with
the Python interpreter that will run the task. It checks Python dependencies,
Aliyun CLI **3.3.22 or later**, CLI profile configuration, the SLS plugin, and
dashboard/query command help, and prints versions and suggested commands. Use `--offline` for offline work;
add `--with-sdk` for Metric StoreView queries or scheduled reports. See
[environment setup](references/cli-installation-guide.md) for details.

For cloud operations, use the configured profile by default; add `--profile` when
the user specifies one. The caller needs the
[RAM permissions](references/ram-policies.md) for the operation.

## Observability (required for cloud operations)

Before the first cloud call, read [manifest.json](references/manifest.json) and use
its non-empty `version` as `{skill-version}`. Stop if the file or version is invalid;
do not guess a version.

Generate one random 32-character lowercase hexadecimal `{session-id}` for this skill
in the conversation. Reuse it for all operations, pagination and retries. When
switching skills, use each skill's own version and session ID, including on return.

Set `ALIBABACLOUD_SLS_DASHBOARD_USERAGENT` to:

```text
AlibabaCloud-Agent-Skills/alibabacloud-sls-dashboard/{session-id} skill-version/{skill-version}
```

The bundled scripts use this variable for cloud requests. For direct cloud API
commands, including request-only dry runs, add:

```sh
--user-agent "$ALIBABACLOUD_SLS_DASHBOARD_USERAGENT"
```

Local help, version, plugin and configure commands, offline dashboard operations,
and doctor checks do not need it. Never send literal placeholders, credentials or
personal identifiers.

## Choose a workflow

| Request | Read |
| --- | --- |
| Explain settings or review JSON/Plan | [Consult](references/workflows/consult.md) |
| Create a dashboard or build a supplied Plan | [Create](references/workflows/create.md) |
| Edit, add, remove charts, or combine changes | [Edit](references/workflows/edit.md) |
| Publish or delete a dashboard | [Publish](references/workflows/publish.md) |
| Diagnose missing data or broken controls | [Diagnose](references/workflows/diagnose.md) |
| Manage scheduled reports | [Subscriptions](references/integrations/subscriptions.md) |

Use the [knowledge index](references/index.md) to select references. Explain each
setting's purpose and effect. Include commands or configuration fields when needed
to complete the task; omit implementation details.

For a simple starting configuration, read [common chart examples](references/charts/examples.md)
and open the selected single-chart grid Dashboard JSON. Follow its links for detailed settings.

For CLI or script failures, use [skill usage troubleshooting](references/troubleshooting.md).

## Working guidelines

- Plan builds and online operations support SLS Logstore, Metricstore and existing
  named StoreViews. The [capability table](references/datasources/overview.md)
  lists tool support and other Dashboard JSON sources, including
  [builtin simulated data](references/datasources/builtin.md).
- Keep the destination Project/Region independent of query sources. Preserve
  StoreView identity instead of replacing a view with a member store.
- Use resource names, fields, metrics and labels from user input, existing
  configuration or discovery. A sampled field does not prove SQL indexing.
- Prefer a [Plan](references/model/plan.md) for new content. Complete Dashboard JSON
  can be validated directly. Edit existing JSON without regenerating unrelated content.
  Use lowercase stable IDs for new charts; see [chart naming](references/model/dashboard.md).
- Use `grid` for new dashboards; use `free` only when a custom layout is needed.
  Set `attribute.type` explicitly. Validation accepts empty existing layout settings
  as `free`; see [layout](references/features/layout.md).
- Display-only edits need no datasource discovery. Field changes must account for
  query results, transformations and display bindings. Controls need matching consumers.
- Keep an original baseline for edits and review the diff before publishing.
- Build and validation are offline. Publish/delete require user authorization
  and `--execute`; an explicit request to publish authorizes publishing.
  Creating a dashboard does not authorize report deliveries.
- Report the [checks performed](references/validation/checks.md). Saving successfully
  does not prove that queries or charts render correctly.

## Run the tools

Use Python 3.10+ with the [Python
dependencies](references/cli-installation-guide.md#python-dependencies) installed.
Metric StoreView queries and scheduled reports also need the optional packages in that
guide. Offline work needs no cloud credentials.

- `python3 scripts/sls.py --help`: resources, discovery, queries and dashboard reads.
- `python3 scripts/dashboard.py --help`: build, edit checks, publishing and subscriptions.
- `python3 scripts/validator.py --help`: individual chart or dashboard configuration checks.

Cloud commands accept `--profile` and `--endpoint` after the operation name;
`--region` remains required. See [commands and connection options](references/datasources/api.md).
