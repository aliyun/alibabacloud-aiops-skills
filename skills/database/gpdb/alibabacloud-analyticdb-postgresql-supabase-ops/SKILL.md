---
name: alibabacloud-analyticdb-postgresql-supabase-ops
description: |
  Manage the full lifecycle of ADBPG Supabase projects.
  Use for listing/querying projects, create, pause/resume, reset password, API Keys, and security IP management.
  Triggers: "Supabase", "supabase project", "spb-xxx", "ADBPG Supabase"
---

# ADBPG Supabase Project Management

Manage the full lifecycle of Supabase projects based on AnalyticDB PostgreSQL (ADBPG).

**Architecture**: `ADBPG (AnalyticDB PostgreSQL) + Supabase + VPC + VSwitch`

### Scope — Alibaba Cloud ADBPG only (not Supabase CLI)

- This skill controls projects **provisioned on Alibaba Cloud** via **GPDB / `aliyun gpdb`** APIs.
- **Do not** use the standalone **`supabase`** CLI (`supabase login`, `supabase projects list`, etc.) for create/list/pause/resume here — that targets **Supabase Cloud or self-hosted** stacks, **not** ADBPG-managed Supabase instances.
- All lifecycle and query operations in this skill are **`aliyun gpdb …`** with **`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`**.

### ProjectId format (`spb-`)

- **`ProjectId`** from create/list/get APIs uses the prefix **`spb-`** plus an alphanumeric suffix (e.g. `spb-2zen7c8752x12328`). Use this exact value in **`--project-id`**.
- If the user’s string does not match any instance, run **`list-supabase-projects`** in the right **`--biz-region-id`** and match **`ProjectName`** or the returned **`ProjectId`**.

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then **[MUST]** run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

## Credential Verification

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

## RAM Permissions

Ensure the current account has the required permissions before executing operations. See [references/ram-policies.md](references/ram-policies.md) for details.

**Permission Pre-check**: Use `ram-permission-diagnose` skill to check current user permissions, compare against `references/ram-policies.md`, and abort with prompt if any permission is missing.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, ProjectId, instance names, CIDR blocks,
> passwords, VPC/VSwitch IDs, etc.) MUST be confirmed with the user.
> For **create**, the skill supplies **recommended defaults** (and optional auto-discovery). You **must** present that full plan and obtain **explicit user approval** (or replaced values) before running `create-supabase-project`.

### Final execution confirmation (read-only vs mutating)

- **No separate final “execute” step** — only for **read-only information retrieval**: **`aliyun gpdb list-supabase-projects`**, **`aliyun gpdb get-supabase-project`**, **`get-supabase-project-api-keys`**, **`get-supabase-project-dashboard-account`**, and **discovery-only** calls such as **`aliyun vpc describe-vpcs`**, **`aliyun vpc describe-vswitches`**, **`aliyun gpdb describe-regions`** (same class as **list / describe**: no resource state change).
- **Final user confirmation [MUST]** — before the CLI runs, for **every mutating operation**: **create**, **pause**, **resume**, **reset password**, **modify security IPs**. Show **what** will execute and **key parameters** (e.g. `project-id`, new password hint without logging secret, new whitelist). Obtain **explicit approval**.
- **After create**, **provisioning poll** via **`get-supabase-project`** does **not** need a new confirmation — the user already approved create; polling is verification only.

**CreateSupabaseProject** is defined in the [official API reference](https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/developer-reference/api-gpdb-2016-05-03-createsupabaseproject). Full CLI mapping, VPC/VSwitch discovery, name/password rules: [references/create-supabase-project-parameters.md](references/create-supabase-project-parameters.md).

| Parameter | Required/Optional | Description | Default / recommendation |
|-----------|-------------------|-------------|---------------------------|
| ProjectId | Required (non-create) | Instance ID from API/list (`spb-` + suffix) | — |
| BizRegionId | Optional (create) | Region ID (`RegionId` in API) | `cn-beijing` |
| ProjectName | Required (create) | Project name | Derive from user scenario; user may replace |
| ZoneId | Required (create) | Availability zone ID | `cn-beijing-i` |
| VpcId | Required (create) | VPC ID | User input **or** from discovery (see Create Project) |
| VSwitchId | Required (create) | VSwitch ID (must match `ZoneId`) | User input **or** recommend **max `AvailableIpAddressCount`** in zone |
| AccountPassword | Required (create) / reset | Database password | User input **or** generate per API rules; user may replace |
| SecurityIPList | Required (create) / modify | IP whitelist | **`127.0.0.1`**; user may supply IPs/CIDRs |
| ProjectSpec | Required (create) | Instance spec | **`2C2G`** (skill default recommendation; user may choose e.g. `1C1G`) |
| StorageSize | Optional (create) | Storage (GB) | **`20`** (skill default recommendation) |
| DiskPerformanceLevel | Optional (create) | PL0 / PL1 | `PL0` |
| PayType / UsedTime / Period | Optional (create) | Billing | **`POSTPAY`** (后付费) by default; set `--period` / `--used-time` only for prepaid/subscription |
| ClientToken | Optional (create) | Idempotency | Omit unless user retries same create |

## Timeout Configuration

> **Timeout Settings**
> - Default CLI read timeout is often **~60 seconds** per HTTP read — usually enough for **`create-supabase-project`**, because creation is **asynchronous**: the API accepts the request and returns **`ProjectId`** quickly; it does **not** block until the instance is ready.
> - **3–5 minutes** is the typical time for **background provisioning** to finish — not the duration of the create HTTP response. Use **Success Verification** (poll `get-supabase-project` until `Status` is `running`) to wait for that phase.
> - **Create success criterion**: after `create-supabase-project` returns **`ProjectId`**, the instance is **not** ready until **`get-supabase-project`** reports **`Status` = `running`** (API uses **lowercase**) — that state means **provisioning succeeded** and the project is usable.
> - If any command hits read timeouts in practice, raise `--read-timeout` for that call (e.g. `--read-timeout 120`).

## Core Workflow

All commands use `aliyun gpdb <command>` format, **must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`**.

Per **[Final execution confirmation](#final-execution-confirmation-read-only-vs-mutating)**: read-only **list / get / describe** may run without a final execute prompt; **create, pause, resume, reset password, modify IPs** require **explicit final user confirmation** before invocation.

### List Projects

```bash
aliyun gpdb list-supabase-projects \
  --biz-region-id cn-beijing \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Low | Read-only — no final execution confirmation

### Get Project Details

```bash
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Low | Read-only — no final execution confirmation

### Get API Keys

```bash
aliyun gpdb get-supabase-project-api-keys \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Low | Read-only — no final execution confirmation
- **Policy**: Fulfilling a request to read keys via this **official Alibaba Cloud API** (with RAM/account access) is **not** the same as scraping secrets from an unrelated codebase. Decline only when the task is clearly exfiltration from repos or third-party systems; otherwise run **`get-supabase-project-api-keys`**, return keys **minimally** (no logging full secrets), and remind the user to rotate if exposed.

### Get Dashboard Account

```bash
aliyun gpdb get-supabase-project-dashboard-account \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Low | Read-only — no final execution confirmation

### Create Project

**Automated workflow** — When user provides intent like "帮我在北京 i 创建 ADBPG Supabase 项目", run these steps:

#### Step 1: Auto-discover all information (no user input needed yet)

1. **Region + Zone** — Use user-specified values or defaults (`cn-beijing`, `cn-beijing-i`).
2. **ProjectName** — Run `scripts/generate-project-name.sh` to get 1-3 candidates (timestamp-based).
3. **Password** — Run `scripts/generate-password.py` to generate a compliant password.
4. **VPC/VSwitch discovery** — Run `scripts/discover-vswitch.sh --biz-region-id <region> --zone-id <zone>` to get the VSwitch with the most available IPs.
5. **SecurityIPList** — Default `127.0.0.1`.
6. **Optional flags** — Use defaults: `2C2G`, `20` GB, `POSTPAY`, `PL0`.
7. **ClientToken** — Generate one UUID.

#### Step 2: Present creation plan (single confirmation)

Display the full parameter table to the user with options:

```
=== Create Supabase Project Plan ===
Project Name:   <generated-or-user-confirmed>
Region:         <biz-region-id>
Zone:           <zone-id>
VPC:            <vpc-id from discovery>
VSwitch:        <vswitch-id from discovery> (Available IPs: <count>)
Instance Spec:  2C2G
Storage:        20 GB
Pay Type:       POSTPAY
Security IP:    127.0.0.1
Password:       <generated, shown once or masked>
=================================

Select an option:
1. Confirm and create (default)
2. Modify parameters
3. Cancel

Press Enter for [1], or type option number:
```

#### Step 3: Execute after confirmation

If user selects "1" or presses Enter (confirm), run:

```bash
aliyun gpdb create-supabase-project \
  --biz-region-id <BizRegionId> \
  --zone-id <ZoneId> \
  --project-name <ProjectName> \
  --account-password ‘<Password>’ \
  --security-ip-list "127.0.0.1" \
  --vpc-id <VpcId> \
  --vswitch-id <VSwitchId> \
  --project-spec 2C2G \
  --storage-size 20 \
  --disk-performance-level PL0 \
  --pay-type POSTPAY \
  --client-token "<ClientToken>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

Then proceed to **Success Verification** (polling) as described below.

**Async create — HTTP retries (before you have `ProjectId`)**

- **Goal**: absorb transient CLI/network/API errors without double-creating a different resource.
- **Reuse** the same **`--client-token`** on every create attempt in this session for this intended project.
- **Retry create** (max **3** attempts total, including the first) **only if** the response has **no** `ProjectId` **and** the error looks **transient**: e.g. throttling, connection reset, read timeout, `ServiceUnavailable`. Backoff: **5s → 15s → 45s** between attempts.
- **Do not** blindly retry create for **business** errors (e.g. `VSwitchIp.NotEnough`, invalid parameter) — stop, explain, fix with the user.
- **If** any attempt returns **`ProjectId`** → **stop calling create**; switch to **provisioning poll** (Success Verification).
- **If** create **times out** but might have succeeded server-side → **poll `get-supabase-project`** by **name/region** (e.g. `list-supabase-projects` filtered by `ProjectName`) before issuing another create with the same token/name.

```bash
# CLIENT_TOKEN: generate once (e.g. uuidgen) before first attempt; reuse on safe create retries.
aliyun gpdb create-supabase-project \
  --biz-region-id cn-beijing \
  --zone-id cn-beijing-i \
  --project-name my_supabase \
  --account-password '<user-or-generated>' \
  --security-ip-list "127.0.0.1" \
  --vpc-id vpc-xxxxx \
  --vswitch-id vsw-xxxxx \
  --project-spec 2C2G \
  --storage-size 20 \
  --disk-performance-level PL0 \
  --pay-type POSTPAY \
  --client-token "$CLIENT_TOKEN" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: High | **Final user confirmation** — full parameter plan approved before execution
- Password: at least 3 of uppercase, lowercase, digits, specials from `!@#$%^&*()_+-=`; length 8–32 (per API)
- Project name: letters/numbers/hyphens/underscores; must start with letter or `_`; length 1–128

### Pause Project

```bash
aliyun gpdb pause-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Medium | **Final user confirmation** required before execution
- Service unavailable after pause, but data is retained

### Resume Project

```bash
aliyun gpdb resume-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Medium | **Final user confirmation** required before execution (mutating)

### Reset Database Password

```bash
aliyun gpdb reset-supabase-project-password \
  --project-id spb-xxxxx \
  --account-password 'NewPass456!' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Medium | **Final user confirmation** required before execution
- Existing connections using old password will be disconnected

### Modify Security IPs

```bash
aliyun gpdb modify-supabase-project-security-ips \
  --project-id spb-xxxxx \
  --security-ip-list "10.0.0.1,10.0.0.2/24" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

- **Risk**: Medium | **Final user confirmation** required before execution
- Multiple IPs separated by commas, CIDR format supported

## Success Verification

Use the steps below first; extended tables and edge cases are in [references/verification-method.md](references/verification-method.md).

### After create (`create-supabase-project`)

1. **Capture `ProjectId`** from the create response (format **`spb-` + suffix**). The create call returns after the request is accepted, not when provisioning finishes. If create fails or times out, **list or get** to see if the project already exists **before** another create (same **`--client-token`** if retrying create per **Create Project**).

2. **Provisioning poll until `running` or terminal failure** — async work often finishes in **3–5 minutes** but can run longer under load. Use a **two-tier** wait:

   - **Tier A — primary**: every **30 seconds**, call **`get-supabase-project`**, up to **20 attempts** (~10 minutes).
   - **Tier B — extension** (optional): if `Status` is still a **non-terminal** provisioning state (e.g. creating / pending — exact strings depend on API), **inform the user** and add up to **10 more** attempts (~5 minutes) before giving up.

3. **Per-poll retry (transient)**: For **each** scheduled poll, if **get** fails with network/read timeout or throttling, retry the **same** **get** up to **3 times** with **5 seconds** between tries, then continue the outer loop (still count as one poll cycle).

4. **Interpret `Status`**:
   - **`running`** → **create / provisioning succeeded**; instance is ready — report success to the user.
   - **Terminal failure** (if API returns explicit failure/cancelled states) → **stop** polling; report error code/message; do not assume success.
   - **Empty / unknown / in-progress** → keep polling within Tier A/B limits.

```bash
PROJECT_ID="spb-xxxxx"
STATUS=""
MAX_PRIMARY=20
SLEEP=30
for attempt in $(seq 1 "$MAX_PRIMARY"); do
  RAW=""
  for inner in 1 2 3; do
    RAW=$(aliyun gpdb get-supabase-project \
      --project-id "$PROJECT_ID" \
      --read-timeout 90 \
      --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops \
      2>/dev/null) && break
    sleep 5
  done
  STATUS=$(echo "$RAW" | jq -r '.Status // empty')
  [ "$STATUS" = "running" ] && break
  sleep "$SLEEP"
done
# Optional: extend with user consent +10 polls if still provisioning
[ "$STATUS" = "running" ] || exit 1
```

If `jq` is unavailable, inspect the **get** output for `Status` each time; same retry and tier rules apply.

### After other operations

| Operation | Verify with | Success hint |
|-----------|-------------|--------------|
| List | `list-supabase-projects` | `Projects` present in JSON, `RequestId` present |
| Get / API keys / dashboard | matching `get-*` command | Expected fields in JSON, no error code |
| Pause / resume | `get-supabase-project` | `Status` matches paused / running per API |
| Reset password / modify IPs | `get-supabase-project` | Whitelist or success response as applicable; password change is also validated by reconnecting (see reference doc) |

## Best Practices

1. **Read-only** list/get/describe (see [Final execution confirmation](#final-execution-confirmation-read-only-vs-mutating)) may run without a final execute prompt; **never** run create/pause/resume/reset-password/modify-IPs without **explicit final user confirmation**
2. If users lack VPC/VSwitch IDs, discover with `vpc describe-vswitches` (and optionally `vpc describe-vpcs`) before create
3. Must issue **warning** before pausing projects (service will become unavailable)
4. **Do not recommend setting whitelist to 0.0.0.0/0** due to security risks
5. **`ProjectId`** is always **`spb-…`** — if the user’s id is wrong or unknown, use **`list-supabase-projects`** to resolve by name or id
6. Never substitute **`supabase` CLI** for **`aliyun gpdb`** on this product
7. Pausing projects saves costs while data is preserved
8. All commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`
9. After **create**, always run **provisioning poll** (or confirm terminal failure) — do not treat “create returned ProjectId” as “instance ready”

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI Installation Guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM Permission Requirements |
| [references/related-apis.md](references/related-apis.md) | Related API List |
| [references/verification-method.md](references/verification-method.md) | Operation Verification Methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |
| [references/create-supabase-project-parameters.md](references/create-supabase-project-parameters.md) | Create API parameters, defaults, VPC/VSwitch discovery |
