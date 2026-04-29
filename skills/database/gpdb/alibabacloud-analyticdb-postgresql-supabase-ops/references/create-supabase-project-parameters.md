# CreateSupabaseProject — parameters & defaults

Official API: [CreateSupabaseProject](https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/developer-reference/api-gpdb-2016-05-03-createsupabaseproject) (ADBPG / GPDB).

CLI command: `aliyun gpdb create-supabase-project` (plugin mode). Every invocation must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`.

**Rule**: The skill proposes **defaults** in the table below. The agent **must** show the user a filled-in plan (or short list of options) and obtain **explicit confirmation** or replacement values before calling create.

**Global policy** (see main [SKILL.md](../SKILL.md) **Final execution confirmation**): only **list / get / describe** (read-only) skip a final execute prompt; **create** and all other mutating GPDB operations require **final user confirmation** before the CLI runs.

## Parameter matrix (API → CLI)

| API field | CLI flag | Required | Default / recommendation | User may override |
|-----------|----------|----------|---------------------------|-------------------|
| RegionId | `--biz-region-id` | No | `cn-beijing` (skill default) | Yes |
| ProjectName | `--project-name` | Yes | Derive from scenario (see below) | Yes |
| ZoneId | `--zone-id` | Yes | `cn-beijing-i` (skill default) | Yes |
| AccountPassword | `--account-password` | Yes | Generate if user omits (see below) | Yes |
| SecurityIPList | `--security-ip-list` | Yes | `127.0.0.1` (no external access until changed) | Yes |
| VpcId | `--vpc-id` | Yes | From discovery if omitted (see below) | Yes |
| VSwitchId | `--vswitch-id` | Yes | From discovery if omitted (see below) | Yes |
| ProjectSpec | `--project-spec` | Yes | **`2C2G`** (skill default recommendation; API doc minimum default is `1C1G`) | Yes |
| StorageSize | `--storage-size` | No | **`20`** (GB, skill default recommendation; API doc default is `1`) | Yes |
| DiskPerformanceLevel | `--disk-performance-level` | No | `PL0` | Yes (`PL1`) |
| PayType | `--pay-type` | No | **`POSTPAY`** (后付费, skill default recommendation) | Yes |
| UsedTime | `--used-time` | No | Omit unless required by chosen PayType | Yes |
| Period | `--period` | No | Omit unless required by chosen PayType | Yes |
| ClientToken | `--client-token` | No | **Skill**: generate **one** UUID (or stable string) **before** first create; **reuse** on safe create retries; see [Async create retries](#async-create-retries-skill) | Yes |

## ProjectName from scenario

1. Take the user’s intent (e.g. “user auth production”, “demo app”).
2. Normalize to API rules: length 1–128; only `[A-Za-z0-9_-]`; **must start with** `[A-Za-z_]`.
3. Replace spaces with `_`, remove invalid characters, collapse repeats.
4. Examples: `User Auth Prod` → `user_auth_prod`; `demo-app` → `demo_app` or keep `demo-app` if valid.
5. Offer **1–2** candidates; user confirms or supplies another name.

## AccountPassword when user does not provide one

Per API: length **8–32**; at least **three** of: uppercase, lowercase, digit, special from **`!@#$%^&*()_+-=`**.

1. Generate a random password meeting rules (e.g. use a cryptographically secure RNG in code, or `python3 -c` / `openssl` in a pinch).
2. **Do not** paste the full password into logs or transcripts; show once for user confirmation/storage, or confirm “generated and will be used” per session policy.
3. User may replace with their own password before create; validate rules before submit.

## SecurityIPList

- **Default**: `127.0.0.1` (per product semantics: blocks external access until whitelist is widened).
- User may set comma-separated IPs or CIDRs (e.g. `10.0.0.0/16,203.0.113.10`).
- Avoid recommending `0.0.0.0/0` unless user explicitly accepts risk.

## VPC / VSwitch discovery (when `VpcId` or `VSwitchId` is missing)

Use **VPC OpenAPI via CLI** (requires `vpc:DescribeVSwitches` and usually `vpc:DescribeVpcs` — see [ram-policies.md](ram-policies.md)). Always add `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops`.

### Step A — list VSwitches in the target zone (primary path)

```bash
aliyun vpc describe-vswitches \
  --biz-region-id <BizRegionId> \
  --zone-id <ZoneId> \
  --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

Use **`--pager`** (see `aliyun vpc describe-vswitches --help`) or increase **`--page-number`** until all VSwitches are collected.

- Parse the JSON: each item includes **`VSwitchId`**, **`VpcId`**, **`ZoneId`**, and typically **`AvailableIpAddressCount`** (or equivalent field in output).
- **Keep only** switches where `ZoneId` equals the chosen `<ZoneId>` (should already match filter).
- If the user already provided **`VpcId`**, filter to that VPC only.
- Sort by **`AvailableIpAddressCount` descending** (missing → `0`).
- **Recommend** the first row’s `VSwitchId` + `VpcId`; also show **top 3–5** with VPC ID, VSwitch ID, and available IP count so the user can pick another.

### Step B — optional `describe-vpcs` (when user asks for VPC list first)

```bash
aliyun vpc describe-vpcs \
  --biz-region-id <BizRegionId> \
  --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-supabase-ops
```

Note: some CLI versions default **`--is-default`** in a way that limits results. If the list looks incomplete, run additional calls with `--is-default true` and `--is-default false` and merge by `VpcId`, or follow local `aliyun vpc describe-vpcs --help`.

After user picks a VPC, run **Step A** with `--vpc-id <VpcId>` (still require `--zone-id` to match the Supabase zone).

## Final check before create

- `ZoneId` matches the selected VSwitch’s zone.
- All **required** CLI flags are set; optional flags only if user confirmed.
- User gave **final OK** on the full parameter set (including generated password if any).
- **`CLIENT_TOKEN`** is set once for this create intent and passed as `--client-token` (recommended for correct retry behavior).

## Async create retries (skill)

Aligned with [SKILL.md](../SKILL.md) **Create Project** and **Success Verification**:

1. **Create HTTP**: max **3** attempts with backoff **5s / 15s / 45s** only when **no** `ProjectId` and error is **transient**; **same** `--client-token` every time. **Never** retry blindly on business errors.
2. **After `ProjectId`**: only **`get-supabase-project`** polling — no second create.
3. **Timeout without `ProjectId`**: **`list-supabase-projects`** (filter by name/region) before another create.
4. **Provisioning**: poll every **30s**, **20** attempts primary + optional **10** with user notice; each poll: up to **3** inner **get** retries, **5s** apart.
5. **Create success**: when **`get-supabase-project`** returns **`Status` = `running`**, provisioning **succeeded** — report **create success** to the user (not merely having `ProjectId` from create).

Full scripts: main skill file and [verification-method.md](verification-method.md) § Create.
