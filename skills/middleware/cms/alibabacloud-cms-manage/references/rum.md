# Real User Monitoring (RUM) Module

> Global conventions (credentials, output format, error codes, command prefix, distributions) - see [../SKILL.md](../SKILL.md).

## Product Overview

ARMS Real User Monitoring (RUM) captures the real, end-user view of frontend applications. It reconstructs the user session (page load, API call, errors, crashes) without code-level instrumentation in most cases, stores raw logs into the customer's SLS project, and exposes metrics through ARMS Prometheus and Grafana.

Core capabilities:

| Capability | What it gives you |
|-----------|-------------------|
| Multi-platform SDKs | One product covers Web/H5, mobile (Android/iOS/HarmonyOS), miniapps, and cross-platform runtimes (Flutter / React Native / Unity) |
| Low-touch onboarding | Install dependency + initialize SDK; no manual event instrumentation required for baseline data |
| Full-link tracing | Session-centric analysis; can correlate with ARMS APM for end-to-end (frontend → backend) traces |
| Log + metric storage | Raw events in customer-owned SLS; metrics in ARMS Prometheus — both queryable by the user |
| Data exploration | Free combination of dimensions/metrics for ad-hoc analysis |
| Visualization | Built-in scenario dashboards in ARMS Grafana plus user-customizable boards |

Typical signals captured: page-load timing (incl. Web Vitals on web targets), XHR/fetch performance and errors, JS errors, native crashes, ANR, network errors, and custom user actions.

Product reference: https://help.aliyun.com/zh/arms/user-experience-monitoring/product-overview/what-is-real-user-monitoring

---

## Scope

Guided workflow to create an Alibaba Cloud ARMS Real User Monitoring (RUM) application with the `aliyun cms2` CLI, retrieve the identifiers needed by the SDK, then fetch platform-specific RUM SDK setup instructions through `aliyun cms2 integration addon get` to install, initialize, start, and verify data reporting.

**In-Scope**: Initialize RUM observability infrastructure, create/list/get RUM application services, extract `serviceId`, `pid`, `workspace`, and `endpoint`, fetch the matching RUM SDK setup guide via `aliyun cms2 integration addon get`, and verify first data after the app starts.

**Out-of-Scope**: Maintaining a local copy of platform SDK setup instructions, changing application code without following the addon-provided guide, sampling or alert configuration after data appears, and historical data analysis.

---

## Supported Client Targets

Use this module to create the RUM application. SDK setup instructions for each platform are fetched on demand through `aliyun cms2 integration addon get` (the addon list itself can be inspected with `aliyun cms2 integration addon list`):

| Target | `attributes.siteType` | `--addon-name` |
|--------|-----------------------|----------------|
| Web / H5 | `web` | `rum-web-h5` |
| Android | `android` | `rum-android` |
| iOS | `ios` | `rum-ios` |
| Miniapp | `miniapp` | `rum-miniapp` |
| HarmonyOS | `harmonyos` | `rum-harmonyos` |
| Flutter | `flutter` | `rum-flutter` |
| React Native | `reactnative` | `rum-reactnative` |
| Unity | `unity` | `rum-unity` |

> Other valid `siteType` values accepted by the API: `electron`, `macOS`, `Windows`, `minigame`, `uniapp`. Always confirm with `aliyun cms2 rum service create --help` for the latest list.

Example (fetch the Web / H5 SDK setup guide):

```bash
aliyun cms2 integration addon get \
  --addon-name rum-web-h5 \
  --env-type Client
```

---

## CLI Commands Reference

> Always run `aliyun cms2 <command> <subcommand> --help` first. The RUM module is exposed under two dedicated command groups: `rum configuration` (infrastructure / entry points) and `rum service` (application service CRUD). Both ultimately call the same backend APIs as the shared `service-observability` / `service` commands but do not require `--type rum` / `--service-type RUM` — the type is implied by the `rum` prefix.

| Command | Purpose | Required Flags | Optional Flags |
|---------|---------|----------------|----------------|
| `rum configuration create` | Provision RUM observability infrastructure for the workspace (returns only a `requestId`; poll `get` for status) | `--workspace` | — |
| `rum configuration get` | Retrieve RUM init status and `entryPointInfo` (`authToken`, `publicDomain`, `privateDomain`, `project`), plus `feeType`, `settings`, `quotas` | `--workspace` | — |
| `rum service create` | Create a RUM application service (returns `requestId`, `serviceId`, `pid`) | `--workspace`, `--body` (JSON or `@file.json`) | `--show-example-body`, `--show-schema` |
| `rum service list` | List / filter RUM (or other) application services in a workspace | `--workspace` | `--service-type` (TRACE / RUM / XTRACE), `--service-name`, `--resource-group-id`, `--tag` (JSON array), `--max-results`, `--next-token` |
| `rum service get` | Get a RUM application's full detail (`service.{serviceId, serviceName, serviceType, serviceStatus, displayName, regionId, workspace, pid, description, attributes, resourceGroupId, createTime, tags}`) | `--workspace`, `--service-id` | — |
| `rum service update` | Update `displayName`, `description`, `attributes`, or `serviceStatus` (the RUM-effective fields) | `--workspace`, `--service-id`, `--body` | `--show-example-body`, `--show-schema` |
| `rum service delete` | Permanently delete a RUM application service (irreversible — data cannot be recovered) | `--workspace`, `--service-id` | — |

Global flags applicable to all of the above: `--region`, `--access-key-id`, `--access-key-secret`, `--security-token`, `--endpoint`, `-o {text|json}`.

Output conventions (from the binary's top-level `--help`):
- `-o text` (default) → list commands emit CSV with a `# <entity> returned=N total=T truncated=...` metadata header; get/mutate commands emit single-line compact JSON `{"success":true,"data":{...}}`.
- `-o json` → indented success envelope on stdout; failures always go to stderr as JSON.

> `rum service create --body @file` may need `< /dev/null` in shell environments where stdin conflicts with the CLI.

---

## Onboarding Workflow

### Step 1 - Gather Parameters

| Parameter | Required | How to Obtain |
|-----------|----------|---------------|
| `regionId` | Yes | Ask user. Common: `cn-hangzhou`, `cn-shanghai`, `cn-beijing` |
| `userId` / AccountId | Yes, unless workspace provided | `aliyun sts get-caller-identity` -> `.AccountId`, or ask user |
| `workspace` | Yes | Default format: `default-cms-{userId}-{regionId}` |
| `appName` | Yes | User-defined RUM application name |
| `target` | Yes | Web/H5, Android, iOS, Miniapp, HarmonyOS, Flutter, React Native, Unity |
| `siteType` | **Yes (must be set in `attributes`)** | Derived from `target` per the [Supported Client Targets](#supported-client-targets) table; valid values include `web`, `android`, `ios`, `miniapp`, `harmonyos`, `flutter`, `reactnative`, `unity`, `electron`, `macOS`, `Windows`, `minigame`, `uniapp` |
| `network` | Yes | `public` for browsers/mobile users on the Internet; `vpc` only for internal clients |
| `env` | Recommended | `prod`, `gray`, `pre`, `daily`, or `local`, depending on SDK support |
| `projectPath` | Recommended | Path to the client app to modify and start |

If the user asks to create the app only, stop after Step 4 and report the handoff values. If the user asks to create and start, continue through the SDK setup skill and verification.

### Step 2 - Initialize RUM Observability

```bash
aliyun cms2 rum configuration create \
  --workspace {workspace} \
  --region {regionId}
```

The create command returns only a `requestId`. It is idempotent for already-initialized workspaces in normal onboarding flows. Always poll status with `get`.

```bash
aliyun cms2 rum configuration get \
  --workspace {workspace} \
  --region {regionId} \
  -o json
```

Status meanings (the binary's `--help` confirms `Running` as the ready state; the other values reflect lifecycle states the backend may return during provisioning):

| Status | Meaning | Action |
|--------|---------|--------|
| `Created` | Provisioning is in progress | Wait briefly, then poll again |
| `Running` | RUM infrastructure is ready | Continue |
| `Failed` | Initialization failed; backend may retry | Poll once more, then surface request ID if still failed |
| `Pending` | Awaiting activation or missing dependencies | Ask user to verify workspace and mapped SLS resources |

Extract these values:

| Field Path | Variable | Use |
|------------|----------|-----|
| `entryPointInfo.publicDomain` | `publicEndpoint` | SDK endpoint for public Internet clients |
| `entryPointInfo.privateDomain` | `vpcEndpoint` | SDK endpoint for clients inside Alibaba Cloud VPC |
| `entryPointInfo.project` | `project` | Backend project metadata; usually not needed by client SDKs |
| `entryPointInfo.authToken` | `authToken` | Sensitive reporting credential; do not print unless required |

For SDK setup, set:

```text
endpoint = https://{publicEndpoint}   # public network
endpoint = https://{vpcEndpoint}      # VPC network
```

If the CLI response already includes `https://`, do not add another scheme.

### Step 3 - Create the RUM Application

> **Important — `attributes.siteType` is required.** When creating a RUM application via `aliyun cms2 rum service create`, the request body MUST include an `attributes` field whose JSON string contains a `siteType` key identifying the client platform (e.g. `android`, `ios`, `web`). The backend uses `siteType` to drive SDK behavior, dashboards, and addon resolution. Run `aliyun cms2 rum service create --help` to inspect the full list of accepted `siteType` values.

Minimal request body — `serviceName`, `serviceType`, and `attributes.siteType` are required by the API; `displayName` and `description` are RUM-effective and recommended:

```json
{
  "serviceName": "{appName}",
  "serviceType": "RUM",
  "displayName": "{appName}",
  "description": "Created by aliyun cms2 RUM onboarding",
  "attributes": "{\"siteType\":\"{siteType}\"}"
}
```

Note: `attributes` is a JSON **string** (not an object) — escape internal quotes when placing it inside another JSON document. Per-platform examples:

```json
// Android
"attributes": "{\"siteType\":\"android\"}"
// iOS
"attributes": "{\"siteType\":\"ios\"}"
// Web / H5
"attributes": "{\"siteType\":\"web\"}"
```

Additional `attributes` keys (e.g. `env`, `language`) can be combined in the same JSON string:

```json
"attributes": "{\"siteType\":\"android\",\"env\":\"prod\",\"language\":\"cn\"}"
```

Optional top-level fields (all accepted by `rum service create --body`):

```json
{
  "resourceGroupId": "{resourceGroupId}",
  "tags": [
    { "key": "env", "value": "prod" }
  ]
}
```

> `pid` is generally auto-generated by the backend; do not set it in the request body unless you have an explicit reason. Run `aliyun cms2 rum service create --show-example-body` / `--show-schema` to inspect the full body shape.

Run:

```bash
aliyun cms2 rum service create \
  --workspace {workspace} \
  --region {regionId} \
  --body @rum-service.json \
  -o json < /dev/null
```

Expected response fields (per `rum service create --help`):

| Field | Meaning | SDK handoff |
|-------|---------|-------------|
| `serviceId` | CMS2 application service ID | Use for SDKs that ask for `ServiceId` |
| `pid` | Legacy ARMS app ID | Use for Web/H5 and Miniapp SDKs that ask for `pid` or `app id` |
| `requestId` | Request ID | Keep for troubleshooting |

Do not invent IDs. If a platform skill names the parameter `pid`, pass `pid`. If it names the parameter `ServiceId`, pass `serviceId`.

### Step 4 - Verify the Application

```bash
aliyun cms2 rum service list \
  --workspace {workspace} \
  --service-type RUM \
  --service-name {appName} \
  --region {regionId} \
  -o json
```

For a single service:

```bash
aliyun cms2 rum service get \
  --workspace {workspace} \
  --service-id {serviceId} \
  --region {regionId} \
  -o json
```

Expected: `service.serviceType` is `RUM`, `service.serviceStatus` is `Running` (or another usable lifecycle state), and `service.pid` is present. Additional fields exposed by `rum service get`: `serviceName`, `displayName`, `description`, `regionId`, `workspace`, `attributes`, `resourceGroupId`, `createTime`, `tags`.

### Step 5 - Fetch the Platform SDK Setup Guide

Detect the platform from project files (`package.json`, `build.gradle`, `Podfile`, `pubspec.yaml`, `build-profile.json5`, `.csproj`, etc.), then fetch the matching SDK setup guide through the integration addon command.

```bash
aliyun cms2 integration addon get \
  --addon-name {addon-name} \
  --env-type Client
```

Use the addon name that matches the detected target (full mapping in [Supported Client Targets](#supported-client-targets)). For example:

```bash
# Web / H5
aliyun cms2 integration addon get --addon-name rum-web-h5    --env-type Client
# Android
aliyun cms2 integration addon get --addon-name rum-android   --env-type Client
# iOS
aliyun cms2 integration addon get --addon-name rum-ios       --env-type Client
# Miniapp
aliyun cms2 integration addon get --addon-name rum-miniapp   --env-type Client
# HarmonyOS
aliyun cms2 integration addon get --addon-name rum-harmonyos --env-type Client
# Flutter
aliyun cms2 integration addon get --addon-name rum-flutter   --env-type Client
# React Native
aliyun cms2 integration addon get --addon-name rum-reactnative --env-type Client
# Unity
aliyun cms2 integration addon get --addon-name rum-unity     --env-type Client
```

If the platform is unclear, list the available addons first:

```bash
aliyun cms2 integration addon list --env-type Client
```

Tell the user which platform was detected and which `--addon-name` will be used. Then follow the returned addon content exactly to install dependencies, initialize the SDK, and start the app.

When invoking the SDK using the values returned by Steps 2-4, use this handoff bundle:

```json
{
  "appName": "{appName}",
  "workspace": "{workspace}",
  "serviceId": "{serviceId}",
  "pid": "{pid}",
  "endpoint": "{endpoint}",
  "env": "{env}",
  "network": "{public|vpc}",
  "regionId": "{regionId}"
}
```

Platform parameter mapping:

| Platform | ID parameter | Endpoint parameter |
|----------|--------------|--------------------|
| Web / H5 | `pid` | `endpoint` |
| Miniapp | `pid` | `endpoint` |
| Android | `serviceId` | `endpoint`, plus `workspace` |
| iOS | `serviceId` | `endpoint`, plus `workspace` |
| HarmonyOS | `serviceId` | `endpoint`, plus `workspace` |
| Flutter | `serviceId` | `endpoint`, plus `workspace` |
| React Native | `serviceId` | `endpoint`, plus `workspace` |
| Unity | `serviceId` | `endpoint`, plus `workspace` |

### Step 6 - Start and Verify Data

Follow the returned addon content to install dependencies, initialize the SDK as early as possible in the app lifecycle, then start the app:

| Target | Start / verification expectation |
|--------|----------------------------------|
| Web / H5 | Start dev server or deploy static page, open in browser, trigger page view and optional test JS error |
| Android | Build/run the app, open at least one Activity, optionally trigger a test exception only in a safe debug build |
| iOS | Build/run on simulator or device, open initial view, optionally trigger a safe test error |
| Miniapp | Run in target miniapp developer tool and trigger page/API activity |
| Flutter / React Native / Unity / HarmonyOS | Build/run the target platform and trigger a normal user journey |

After startup, tell the user data can take several minutes to appear in ARMS User Experience Monitoring. If no data appears, check endpoint reachability, ID mapping, SDK initialization order, CSP or safe-domain allowlists, and app/network logs.

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| `unknown command "rum ..."` | Local binary is older than the build that introduced the `rum` command group | Upgrade the `aliyun cms2` plugin (run `aliyun plugin update`); as a fallback, use the shared `service-observability --type rum` / `service --service-type RUM` form |
| `Forbidden` / `AccessDenied` | Missing CMS permissions | Grant `cms:CreateServiceObservability`, `cms:GetServiceObservability`, `cms:CreateService`, `cms:GetService`, `cms:ListServices` |
| Missing or invalid `siteType` | `attributes` not set, or `siteType` value not in the allow-list | Add `attributes` JSON string with a valid `siteType` (e.g. `{"siteType":"android"}`); confirm allowed values via `aliyun cms2 rum service create --help` |
| `ServiceObservability not exists` | RUM infrastructure not initialized | Run `rum configuration create --workspace {workspace}` |
| RUM app already exists | Duplicate `serviceName` in workspace | Reuse existing app from `rum service list`, or choose a new name |
| Endpoint missing | Initialization not `Running`, or response shape changed | Poll `rum configuration get -o json`; inspect `entryPointInfo` before SDK setup |
| Data not appearing | Wrong `pid/serviceId`, endpoint, workspace, SDK order, or network block | Re-check handoff bundle and the addon-provided troubleshooting section |

---

## Security Notes

- `serviceId`, `pid`, `workspace`, and `endpoint` identify the reporting target and are normally safe in client code.
- `authToken` is sensitive. Do not print it in final responses, commit it to source code, or expose it in screenshots/logs unless a specific SDK requires it and the user accepts the risk.
- For public Web/H5 or mobile apps, prefer the public endpoint. VPC endpoints usually do not work for end-user devices outside Alibaba Cloud private networks.
