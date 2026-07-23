# SKU Parameter File Format / OpenClaw Image Lookup

> Split out from SKILL.md; contains the SKU parameter YAML format spec and the OpenClaw dynamic image lookup logic.

## SKU parameter file format (references/sku-params/*.yaml)

```text
# references/sku-params/starter_webui.yaml example structure (ECS primary path; when the price inquiry misses, switch to variant=traffic_fallback branch, PayByTraffic 100Mbps ¥284.99/yr)
sku: starter_webui
variant: default                       # internal marker: default=ECS primary path / swas_fallback=fallback, decided by deploy's price inquiry
version: v1.0.0
region_default: cn-beijing
monthly_price: "约 ¥8.25/月（按 ¥99/年活动摊算）"
disclaimer: "💡 价格供参考，实际以最终下单为准。ECS ¥99/年活动以下单时活动可用性为准。"

user_summary: |
  即将为你创建：
  - 你的「小店面」（ECS 经济型e 2核2G，命中 ¥99/年活动）—— 产品跑在上面，随时在线
  - 全球加速（ESA 免费版）—— 全国访问都快
  月费合计：约 ¥8.25/月（按 ¥99/年活动摊算，北京地域）
  💡 价格供参考，实际以最终下单为准。

steps:
  # ⚠️ Image resolution is **not at the yaml layer** —— it is consolidated into SKILL.md Phase 0.4 for central execution (maintained in one place, avoiding drift across 7 yamls).
  # All 7 yamls' RunInstances / CreateScalingConfiguration always write `ImageId: "${state.resources.ecs.image_id}"` to purely consume state; using ${latest_image_id} or a hardcoded literal is forbidden.
  # Reuse case: state.resources.ecs.image_id already exists → the whole Phase 0.4 is skipped, going straight to Phase 1 to load this yaml; scale-out/rebuild use the same ImageId and won't silently bump the OS major version overnight.

  - name: "创建你的小店面（服务器）"
    type: api
    product: ecs
    action: RunInstances
    params:
      RegionId: "${region}"
      InstanceType: "ecs.e-c1m1.large"
      ImageId: "${state.resources.ecs.image_id}"   # always read from state, ensuring scale-out/rebuild reuse the same image
      InstanceChargeType: "PrePaid"
      Period: 12
      PeriodUnit: "Month"  # ⚠️ RunInstances only accepts Month (not Year); 12 months = 1 year
      KeyPairName: "${key_pair_name}"  # before Phase 3 creation, first CreateKeyPair or ImportKeyPair
      # ... other params
    wait_until:
      action: DescribeInstanceStatus
      condition: "Status == Running"
    output_vars:
      ecs_instance_id: "InstanceIdSets.InstanceIdSet[0]"
    report: "✓ 你的小店面已开门（IP: ${public_ip}）"

  - name: "开通全球加速（ESA 免费版）"
    type: api
    product: esa
    action: PurchaseRatePlan
    params:
      PlanName: "entranceplan"
      ChargeType: "PREPAY"
      AutoPay: true
      AutoRenew: false  # auto-renew off by default
      Period: 1
    output_vars:
      esa_instance_id: "InstanceId"
    report: "✓ 全球加速已激活（ESA 免费版，¥0）"
    # ESA API: product ESA / version 2024-09-10
    # PlanName enum (China site): entranceplan(free) / basic / medium(standard, limited-time ¥99) / high
    # CLI: aliyun esa purchase-rate-plan --PlanName entranceplan --ChargeType PREPAY --AutoPay true --Period 1 [--force]
    # ⚠️ Version guard: before executing, compare against [cli_meta].esa_native_since
    #   - current CLI version < esa_native_since (including "pending") → keep --force, log a warning
    #   - current CLI version >= esa_native_since → drop --force
    #   Failures do not silently retry; the unified user-facing line: "开通全球加速遇到问题，先停下来。可以稍后再试，或提工单：https://smartservice.console.aliyun.com/service/create-ticket"
```

> **Deprecated starter_webui_swas.yaml**: the original SWAS ¥45/month fallback path has been removed. When the price inquiry misses the ¥99/yr promo, starter_webui switches to the `variant: traffic_fallback` sub-config (within the same starter_webui.yaml) —— ECS `ecs.e-c1m1.large` + `InternetChargeType: PayByTraffic` + `InternetMaxBandwidthOut: 100`, ¥284.99/yr (Beijing), and Phase 4 automatically adds a CloudMonitor outbound-traffic alarm. starter_app fallback works the same way (shares fallback_ecs_config).
>
> **Lite/Pro yaml** SWAS steps use the hardcoded PlanId `swas.s.c2m4s50b1.linux` (Beijing general-purpose, 2C4G 50G 200M peak; OpenClaw host); the ImageId is dynamically looked up by Phase 1.2.6 (see the OpenClaw dynamic image lookup below), no longer hardcoded.
>
> **Lite/Pro RDS steps** DBInstanceStorageType is uniformly `general_essd` (high-performance cloud disk); DBInstanceClass is bound to each SKU's default:
> - lite_seed → `mysql.n2e.small.1` (Basic 1C2G)
> - lite_growth → `mysql.n2.medium.1` (Basic 2C4G)
> - lite_traction → `mysql.n2.large.1` (Basic 4C8G)
> - pro_steady / pro_burst → `mysql.n2.large.2c` (HA 4C8G 200G)
> All RDS steps use `AccountType: "Normal"` + `GrantAccountPrivilege` granting only ReadWrite; passwords never enter state (iron-rule #7).


---

## OpenClaw dynamic image lookup

In the Lite/Pro yaml, the `ImageId` of the SWAS CreateInstances step is no longer hardcoded; it is dynamically looked up in Phase 1.2.6 (before the 1.3 resource-list display):

```bash
aliyun swas-open list-images \
  --profile opc \
  --RegionId cn-beijing \
  --image-type app \
  --biz-region-id cn-beijing
```

> ⚠️ CLI naming gotchas measured (not stated in the API docs):
> - the API name `ListImages` is kebab-case `list-images` in the CLI
> - parameter names are also kebab-case: `--image-type app` (not `--ImageType`)
> - the required parameter `--biz-region-id cn-beijing` is not marked in the API docs but the CLI metadata requires it

Return structure (measured): each image contains `ImageId / ImageName / ImageType / Platform / Description`, with **no separate timestamp field**. Version identification relies entirely on the ImageName date suffix (format `OpenClaw-YYYY.M.DD`, e.g. `OpenClaw-2026.5.19`).

**Filtering and sorting logic**:
1. filter `ImageName` starting with the literal `OpenClaw-`
2. parse the suffix `YYYY.M.DD` into a date
3. take the one **closest to and not exceeding today** → `${openclaw_image_id}`
4. inject it into the SWAS CreateInstances `ImageId` parameter

**User-facing error copy iron rule** (no technical jargon):
- when the filter result is empty:

```text
暂时没找到 AI 助理（OpenClaw）的安装包，可能是镜像列表正在更新。可以稍后再试一次；如果一直不行，提个工单让阿里云帮看看：👉 https://smartservice.console.aliyun.com/service/create-ticket
```
- when the API call fails (network/credential/throttling):

```text
查询安装包列表遇到点问题，先停一下。[ 重试 ] [ 提工单 ]
```
- ⚠️ Forbidden to show technical jargon (e.g., "confirming region" / "checking params" / "ListImages returned empty")
