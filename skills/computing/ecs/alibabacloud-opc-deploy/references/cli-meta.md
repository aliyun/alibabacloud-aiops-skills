# CLI Meta — Version Pinning and SHA256

> Split out from SKILL.md; contains the CLI version-pinning and SHA256 verification config.

<!-- cli_meta: the skill reads this block before startup to decide the CLI version and verification values -->
```toml
[cli_meta]
# Prefer aligning CLI installation with the official docs
official_doc_url     = "https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli"
github_releases_url  = "https://github.com/aliyun/aliyun-cli/releases"
# Minimum compatible Alibaba Cloud CLI version: ensures reproducibility; going below this is forbidden.
# Switched from "exact pinning" to a "minimum version + compatible range" strategy——
#   the real environment may already have a higher version (e.g. 3.3.x); it is backward-compatible, no downgrade needed.
#   at startup the skill only needs to check `aliyun version` >= min_version to pass.
#   for exact pinning use the sha256 hard check; if sha256 is empty, only the lower-bound version check is done.
min_version = "3.0.236"
# SHA256 verification strategy:
#   * Source: at release time the maintainer pulls the official Alibaba Cloud CDN package and writes it via `shasum -a 256`;
#   * If the field value is an empty string "", the install flow enters TOFU (trust on first use): it relies on HTTPS+CDN domain checks for download integrity,
#     after the first successful install the actual SHA256 is written to ~/.opc/cli-tofu-${VER}.sha256, and subsequent installs are force-compared;
#   * ⚠️ TOFU first-use blind spot: on the first download there is no hash to compare = zero verification,
#     if the first HTTPS+CDN path is MITM'd / the CDN origin is poisoned, TOFU records the tampered hash, and later "passing" comparisons instead mask the problem.
#     This is an inherent limitation of the TOFU model, not an implementation bug; the premise = "HTTPS+CDN integrity is trustworthy on first download".
#     **Maintainers should fill in the real value ASAP to keep the empty-value window as short as possible.**
#   * Placeholders like "REPLACE_*" are strictly forbidden —— a placeholder means verification always fails = a paper-thin integrity line.
#   * The sha256 values correspond to the min_version package; when the user already has a higher version, SHA256 verification is skipped (no matching hash).
sha256_darwin_arm64 = "372a84443439ed631b36c8217b7ff93ce54bf5fa0d6be36c5b2b85bc02839735"
sha256_darwin_amd64 = "7c948e38964761d74e54f4659d5847996b1d40a5537528cd9c6dac952f0a2dcf"
sha256_linux_amd64  = "a1d1af9eb02e43ef8552f7e184fd8a570a89bfef2a6e5a7c1d0e28e46da1203f"
# The version where ESA PurchaseRatePlan gains native support in the CLI metadata
# When the current version < this version, PurchaseRatePlan must carry --force; when >= it drops --force
esa_native_since = "pending"  # change to the actual version after Alibaba Cloud CLI metadata backfills ESA 2024-09-10
```

## Plugin-mode flag conventions (CLI 3.4.x · E2E-measured)

From 3.4.x on, product commands (`ecs` / `vpc` / `rds` / `alb` / `ess` / `swas-open` / `esa` …)
run as on-demand plugins, and their flags come from per-product metadata rather than the API parameter
names in the docs. The rules below were measured against CLI 3.4.11 (vpc plugin 0.7.6) during E2E runs.
**Read this table before writing any new CLI call** — guessing flag shapes burns retries and collides with
iron-rule #26's ban on multi-posture trial-and-error.

| Concern | ✅ Accepted | ❌ Rejected |
|---|---|---|
| Region — ecs / vpc / rds / ess | `--biz-region-id cn-beijing` | `--RegionId` / `--region-id` → `unknown flag`. Note `--biz-region-id` is **hidden**: it does not appear in `--help`, but it is accepted and required |
| Region — **`swas-open`** | **BOTH: the global `--region cn-beijing` AND `--biz-region-id cn-beijing`** | Passing `--biz-region-id` **alone** does NOT error and the call succeeds — but it only lands in the request body, while the **service endpoint** is still derived from the profile's default region, so the instance is created in the profile's region. E2E-measured 2026-08-27: `swas-open create-instances --biz-region-id cn-beijing` on a cn-hangzhou-default profile silently created the instance **in Hangzhou** (¥70 wasted, unrecoverable without a refund ticket); adding the global `--region cn-beijing` on the retry put it in Beijing. **Applies to every `swas-open` subcommand, read and write alike** — a List that omits `--region` reads the wrong region's inventory and will report "0 instances" for resources that exist. **Verify it for free instead of paying ¥70 again**: `aliyun swas-open create-instances --cli-dry-run --profile <a profile whose default region is NOT the target> --biz-region-id cn-beijing …` prints `Endpoint: swas.cn-hangzhou.aliyuncs.com` while the body says `RegionId: cn-beijing`; adding `--region cn-beijing` moves the endpoint to Beijing. Re-confirmed on CLI 3.4.11, 2026-08-31, zero cost, no request sent |
| Region — **`alb` (all subcommands)** | **the global `--region cn-beijing`** — alb has NO region parameter flag | `--biz-region-id` / `--region-id` → `unknown flag` on every `alb` subcommand. **Omitting a region entirely does NOT error** — the CLI silently derives the endpoint from the profile's default region, so an alb deploy aimed at another region lands in the profile's region instead, in a different region from its own VPC/ECS |
| Scalar params | kebab-case: `--vpc-name` / `--cidr-block` / `--image-family` / `--page-size` | PascalCase `--VpcName` etc. → `unknown flag` |
| `VSwitchId` | **`--vswitch-id`** (one word, no hyphen after `v`) | `--v-switch-id` → `unknown flag`. The generic PascalCase→kebab split produces the wrong form here |
| Nested object params | `--system-disk Category=cloud_essd Size=40` | dot form `--system-disk.category` → `unknown flag` |
| RepeatList / struct lists — **single** entry | JSON array `--resource-id '["vpc-x"]'` · JSON objects `--tag '[{"Key":"k","Value":"v"}]'` · inline pairs `--tag Key=k Value=v` · bare value `--resource-id vpc-x` | `.N` suffix `--resource-id.1` / `--tag.1.key` → `unknown flag` |
| RepeatList / struct lists — **two or more** entries | **JSON array ONLY**: `--tag '[{"Key":"opc:managed","Value":"true"},{"Key":"opc:sku","Value":"lite_seed"}]'` | 🚨 **inline pairs SILENTLY DISCARD every entry but the last.** `--tag Key=opc:managed Value=true Key=opc:sku Value=lite_seed` produced exactly `Tag.1.Key: opc:sku` — `opc:managed` vanished with no error. Same trap on `--zone-mappings ZoneId=a,VSwitchId=b ZoneId=c,VSwitchId=d` → one entry, second pair swallowed into the first as a literal string |
| `rds` tags — **its own convention** | numbered scalar flags: `--tag-1-key opc:managed --tag-1-value true --tag-2-key opc:sku --tag-2-value <sku>` | `rds add-tags-to-resource` has **no `--tag` list flag at all** → `--tag '[...]'` gives `unknown flag: --tag` |
| `ess tag-resources` resource ids | **`--resource-id`** (singular) even though the API parameter is `ResourceIds` | `--resource-ids` → `unknown flag` |
| `--output` row selector | single-quote it: `'rows=Regions.Region[]'` | unquoted `rows=Regions.Region[]` → zsh globs it away before the CLI runs (`no matches found`) |
| `--output` on object fields | parse raw JSON instead | `rows=Image` where `Image` is an object → `jmespath 'RootFilter[0].Image' failed: need array expression` (quoting does not help) |

🚨 **The two silent-failure rows above are the dangerous ones — they cost money, not just a retry.**
Both `opc:managed=true` and `opc:sku=<sku>` must land on every created resource: iron-rule #5 finds
reusable VPCs by `opc:managed=true`, and the teardown statements in `ram-policies.md` are gated on the
`acs:ResourceTag` condition. If the inline form drops `opc:managed`, the resource becomes invisible to
reuse **and un-deletable** — teardown gets `Forbidden.RAM` and the user keeps paying for something they
cannot remove. So: **whenever a call carries more than one tag or more than one struct entry, write a
JSON array. Never the inline pair form.** After tagging, read the tags back and confirm both are present.


Additional measured notes:

- **`--biz-region-id` is required, not optional**, on ecs / vpc / rds / swas-open / ess calls — including
  ones whose docs never mention a region (e.g. `ecs create-security-group`, `ecs authorize-security-group`,
  `ecs tag-resources`). Omitting it yields an empty response or `Error: --biz-region-id is required`.
  **`alb` is the exception** — it rejects `--biz-region-id`; use the global `--region` there (see the table).
  - 🚨 **A region flag has TWO jobs, and only one of them is visible in the command's exit code.**
    `--biz-region-id` fills the **request body**; the global `--region` selects the **service endpoint**.
    Products differ in which one actually decides where the resource lands, and **getting it wrong never
    errors** — the call returns 200 and the resource quietly appears in the profile's default region.
    Consequences: `alb` needs the global flag only, `swas-open` needs **both**, ecs/vpc/rds/ess are fine with
    `--biz-region-id`.
    → **Therefore a create call is NOT verified by "the command succeeded".** After every create, **read the
    resource back and compare its actual region against the target**; if they differ, stop and tell the user
    before creating anything else. `--cli-dry-run` cannot catch this class of bug at all — it only proves the
    command shape parses, not where the resource would land.
    → **Zero-cost endpoint check, usable BEFORE spending money** (E2E-measured): run the product's own List
    command twice against the target region, once **with** the global `--region <target>` and once without.
    Different inventories back = the endpoint really did switch, so the global flag is taking effect. Same
    inventory back = the flag is being ignored and a create would land in the profile's region.
- **`esa` has no regional endpoint**: always pass `--endpoint esa.cn-hangzhou.aliyuncs.com`, otherwise
  `endpoint not configured for product 'esa' in region '<region>'`.
- **The legacy `oss` verb is DEPRECATED — use `aliyun ossutil`**: the CLI answers the old `oss` verb
  with a notice telling you to switch to `ossutil`. `ossutil` is a standalone tool, not an OpenAPI
  plugin: fs-style verbs (`ossutil ls` / `mb` / `cp`) sit alongside API-level ones
  (`ossutil api put-bucket-tags`), and its output is plain text, not JSON (`ossutil ls` prints
  `Bucket Number is: N`).
- 🚨 **`ossutil -n/--dry-run` IS NOT A DRY RUN — it really calls the API and really creates the resource.**
  Measured 2026-08-26: `aliyun --profile <p> ossutil mb oss://<name> --region cn-beijing --acl private
  --storage-class Standard --redundancy-type LRS --dry-run` **created the bucket** (confirmed by a
  follow-up `ossutil ls`); the command even exited non-zero with a confusing
  `403 AccessDenied / The bucket you access does not belong to you`, so it looks like a failure while
  having succeeded. Its help text ("Do a trial run with no permanent changes") is misleading.
  **Never treat it as a safe pre-check, and never use it to test whether OSS is activated** — that turns a
  probe into an unrequested write on the user's account. This is NOT the same flag as the Alibaba Cloud
  CLI's own `--cli-dry-run`, which genuinely only prints the request (verified on `esa purchase-rate-plan`:
  it prints Method / Endpoint / Query Parameters and sends nothing). Rule of thumb: `--cli-dry-run` on
  `aliyun <product> <action>` = safe; `--dry-run` on `ossutil` = a real call.
- **`ossutil rb` only removes an EMPTY bucket** (`ossutil rb oss://<name> --region <region>`); it needs
  `--force` for a non-empty one, which silently destroys the user's objects — never pass `--force` unasked.
- **Plugins auto-install on first use** once `aliyun configure set --auto-plugin-install true` has run
  (Step 0.1b); the first call otherwise errors with `Plugin 'aliyun-cli-<product>' is required … but not installed`.
- **Some tags do not persist at create time** (`CreateVpc` / `CreateVSwitch` / `CreateSecurityGroup` /
  `RunInstances` / `CreateDBInstance`): always back-fill with `TagResources` (or `AddTagsToResource` for RDS)
  after creation, or tag-conditioned teardown is later denied `Forbidden.RAM`.
