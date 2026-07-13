# OPC SKU Matrix

This file is the advisor's **core decision table** and deploy's **input index**.

After completing the conversation decision, the advisor outputs exactly one of 7 SKU names. Deploy routes to the corresponding deployment parameters by SKU name.

> Prices are based on **cn-beijing region**, precise to the cent. Other regions vary by ±5%.
> Every SKU price quote MUST include the disclaimer: `「💡 价格供参考，实际以最终下单为准」`

---

## Part 1: Standalone Product Catalog

> Each product is defined once. Packages (Part 2) compose products by referencing their IDs.

### Compute

| ID | Product | Spec | API Parameters | Standard Monthly Price | Promo Price |
|---|---|---|---|---|---|
| `ecs-e-starter` | ECS Economy e | 2C2G, 40G ESSD Entry, 3Mbps fixed bandwidth | `InstanceType: ecs.e-c1m1.large`<br>`SystemDisk: cloud_essd_entry/40G`<br>`Internet: PayByBandwidth/3Mbps` | ¥130.14/mo | **¥99/yr** (promo) |
| `ecs-e-fallback` | ECS Economy e (fallback) | 2C2G, 40G ESSD Entry, pay-by-traffic 100Mbps | `InstanceType: ecs.e-c1m1.large`<br>`SystemDisk: cloud_essd_entry/40G`<br>`Internet: PayByTraffic/100Mbps` | **¥284.99/yr** | — |
| `ecs-c9i-2c4g` | ECS c9i | 2C4G, 40G ESSD PL0, pay-by-traffic 100Mbps | `InstanceType: ecs.c9i.large`<br>`SystemDisk: cloud_essd/40G/PL0`<br>`Internet: PayByTraffic/100Mbps` | **¥205.91/mo** | — |
| `ecs-c9i-4c8g` | ECS c9i | 4C8G, 40G ESSD PL0, pay-by-traffic 100Mbps | `InstanceType: ecs.c9i.xlarge`<br>`SystemDisk: cloud_essd/40G/PL0`<br>`Internet: PayByTraffic/100Mbps` | **¥391.82/mo** | — |
| `ecs-c9i-8c16g` | ECS c9i | 8C16G, 40G ESSD PL0, pay-by-traffic 100Mbps | `InstanceType: ecs.c9i.2xlarge`<br>`SystemDisk: cloud_essd/40G/PL0`<br>`Internet: PayByTraffic/100Mbps` | **¥763.64/mo** | — |
| `swas-openclaw` | Simple Application Server | 2C4G, 50G system disk, 200Mbps with included traffic | `plan-id: swas.s.c2m4s50b1.linux`<br>`biz-region-id: cn-beijing` | **¥70/mo** | First month ¥29 |

### Database

| ID | Product | Spec | API Parameters | Standard Monthly Price |
|---|---|---|---|---|
| `rds-1c2g` | RDS MySQL 8.0 Basic | 1C2G, 100GB general_essd | `DBInstanceClass: mysql.n2e.small.1`<br>`Storage: 100/general_essd` | **¥116/mo** |
| `rds-2c4g` | RDS MySQL 8.0 Basic | 2C4G, 100GB general_essd | `DBInstanceClass: mysql.n2.medium.1`<br>`Storage: 100/general_essd` | **¥256/mo** |
| `rds-4c8g` | RDS MySQL 8.0 Basic | 4C8G, 100GB general_essd | `DBInstanceClass: mysql.n2.large.1`<br>`Storage: 100/general_essd` | **¥465/mo** |
| `rds-4c8g-ha` | RDS MySQL 8.0 HA | 4C8G, 200GB general_essd | `DBInstanceClass: mysql.n2.large.2c`<br>`Storage: 200/general_essd` | **¥1262/mo** |

### AI & Storage

| ID | Product | Spec | Standard Monthly Price |
|---|---|---|---|
| `token-standard` | Token Plan Standard | 25,000 credits/mo | **¥198/mo** |
| `pds-200g` | Alibaba Cloud Drive Enterprise (PDS) | 200GB | **¥6.63/mo** |
| `pds-500g` | Alibaba Cloud Drive Enterprise (PDS) | 500GB | **¥16.58/mo** |
| `oss-40g` | OSS Standard LRS | 40GB | **¥9/yr** |
| `oss-500g` | OSS Standard LRS | 500GB | ¥60/mo or **¥119/yr** (one-time purchase) |
| `qwcn-pro` | QoderWork CN Pro Desktop | 2000 credits/mo | **¥59/mo** |

### Network & Security

| ID | Product | Spec | API Parameters | Standard Monthly Price | Promo Price |
|---|---|---|---|---|---|
| `esa-free` | ESA Edge Security | Free tier | `PlanName: free` | **¥0** | — |
| `esa-medium` | ESA Edge Security | Standard medium | `PlanName: medium` | ¥375/mo | **¥99/mo** (limited time) |
| `alb` | Application Load Balancer | Single instance | — | **¥35.28/mo** + LCU pay-as-you-go | — |
| `ess` | Auto Scaling ESS | Service free | — | **¥0** (pay only for scaled-out ECS) | — |

### Image (shared by all ECS-containing SKUs)

> Verified via dry-run `aliyun ecs describe-images` (287 system images) on cn-beijing real account, 2026-06-25.

**ImageFamily naming convention:**
- Prefix `acs:` + all lowercase + **underscore-separated** (not hyphens)
- **Include full minor version** (`3_2104` not `3`, `9_7` not `9`)
- Architecture suffix `_x64` / `_arm64`
- Valid: `acs:alibaba_cloud_linux_3_2104_lts_x64`
- Invalid: `acs:alibaba-cloud-linux-3-x64` (hyphens = 0 matches in dry-run)

**Primary family (pinned):**

| Purpose | Family | OS Display Name | Pinned ImageId | pinned_at | review_due |
|---|---|---|---|---|---|
| **General Web/App x64 (default)** | `acs:alibaba_cloud_linux_3_2104_lts_x64` | Alibaba Cloud Linux 3.2104 LTS 64-bit | `aliyun_3_x64_20G_alibase_20260513.vhd` | 2026-06-25 | 2026-12-25 |
| General ARM | `acs:alibaba_cloud_linux_3_2104_lts_arm64` | Alibaba Cloud Linux 3.2104 LTS ARM | Resolved by describe-image-from-family | 2026-06-25 | 2026-12-25 |

**Alternative distros (only when user explicitly requests):**

| Distribution | Family |
|---|---|
| Ubuntu 24.04 | `acs:ubuntu_24_04_x64` |
| Ubuntu 22.04 | `acs:ubuntu_22_04_x64` |
| Rocky Linux 9.7 | `acs:rocky_linux_9_7_x64` |
| AlmaLinux 9.7 | `acs:almalinux_9_7_x64` |

**Advisor output format:**

```yaml
image:
  family: "acs:alibaba_cloud_linux_3_2104_lts_x64"  # required, include minor version
  os_series: "Alibaba Cloud Linux 3.2104 LTS"       # required, display name
  arch: "x64"                                       # required
  family_pinned_at: "2026-06-25"                    # required
  next_review_due: "2026-12-25"                     # required (+6 months)
  # NEVER pass image_id / image_name (deploy resolves via describe-image-from-family, then locks into state)
```

**Deploy usage rules:**
1. `describe-image-from-family --ImageFamily ${family}` → get ImageId
2. Show user for confirmation → write to `state.resources.ecs.image_id` (permanently locked)
3. Scale-out/rebuild reuses ImageId from state. **Never roll across major versions** (Linux 3→4 breaks glibc/systemd)
4. 0 matches → hard-stop, send user back to advisor for new prescription

**Compatibility constraint:** ARM instances can only use `_arm64` images; advisor SKU selection already avoids heterogeneous instances.

**Maintenance:** Review every 6 months at `next_review_due` to check for minor version updates.

---

## Part 2: Package Composition Table

> Each SKU = combination of multiple products. Price = sum of component monthly prices.

### Starter (two tiers, split by "Does it call AI?")

| | starter_webui | starter_app |
|---|---|---|
| **Positioning** | Portfolio / personal page / showcase | AI accounting / chatbot / language tutor |
| **Trigger** | Product does NOT call AI | Product calls AI |
| **Included products** | `ecs-e-starter` + `qwcn-pro` + `esa-free` | `ecs-e-starter` + `qwcn-pro` + `esa-free` + `token-standard` + `pds-200g` |
| **Monthly price** | **¥99/yr** (≈¥8.25/mo) + ¥59/mo | **≈¥212.88/mo** (incl. ECS ¥99/yr amortized) |
| **Fallback price** | ¥284.99/yr (≈¥23.75/mo) + ¥59/mo | **≈¥228/mo** |
| **Purchase page card** | OPC Starter - Web Presence | OPC Starter - AI App |

**Starter notes:**
- If user already has a desktop AI assistant → can skip `qwcn-pro` (-¥59/mo)
- Fallback is auto-triggered by deploy pricing check; advisor does not differentiate

### Lite (three tiers, by business load)

| | lite_seed | lite_growth | lite_traction |
|---|---|---|---|
| **Positioning** | A few to ~15 concurrent users | Tens of concurrent users | 100-200 concurrent users |
| **ECS** | `ecs-c9i-2c4g` | `ecs-c9i-2c4g` | `ecs-c9i-4c8g` |
| **RDS** | `rds-1c2g` | `rds-2c4g` | `rds-4c8g` |
| **Shared products** | `swas-openclaw` + `token-standard` + `pds-200g` + `oss-40g` + `esa-free` |||
| **Monthly price** | **¥596.54/mo** | **¥736.54/mo** | **¥1131.45/mo** |
| **Purchase page card** | OPC Lite (default) | OPC Lite (upgrade RDS) | OPC Lite (upgrade ECS+RDS) |

**Lite progression logic:**
- seed → growth: upgrade RDS only (+¥140), DB bottlenecks first
- growth → traction: upgrade both ECS + RDS (+¥395), compute + storage under pressure
- Prefer vertical scaling first (live migration, no downtime); if 4C8G still insufficient, consider Pro

### Pro (two tiers, by traffic challenge)

| | pro_steady | pro_burst |
|---|---|---|
| **Positioning** | Stable 200+ concurrent, high availability | Burst spikes 500-1000 concurrent |
| **ECS** | `ecs-c9i-4c8g` x **2 instances** | `ecs-c9i-8c16g` x **2-3 instances** |
| **RDS** | `rds-4c8g-ha` | `rds-4c8g-ha` |
| **Network** | `alb` + `esa-medium` | `alb` + `esa-medium` + `ess` (min=2, max=3) |
| **Shared products** | `swas-openclaw` + `token-standard` + `pds-500g` + `oss-500g` |||
| **Monthly price (fixed)** | **¥2524.55/mo** | **¥3258.19/mo** (min=2) |
| **Purchase page card** | OPC Pro (default) | OPC Pro (upgrade ECS + enable auto-scaling) |

**Pro value leap (vs lite_traction):**
1. Dual-instance — one down, the other holds
2. HA RDS — primary-standby failover, no data loss
3. ALB — traffic distribution + health check + HTTPS offload

---

## Part 3: Operational Rules

### Fallback Logic (starter only)

When deploy Phase 0 confirms the ECS ¥99/yr promo is **NOT available**:

1. Auto-switch to `ecs-e-fallback` config (¥284.99/yr)
2. Explicitly confirm the price with user before proceeding
3. run-instances parameters must exactly match the pricing query
4. Phase 4 auto-creates CloudMonitor outbound traffic alert
5. **The SWAS ¥45/mo fallback path is deprecated**

**Sample output (zh-CN):**

```text
ECS ¥99/年如果没命中，我会自动给你切到按流量计费的备选配置（¥284.99/年），同时帮你装一个出流量告警防过冲。
```

### Starter → Lite Upgrade Conditions

- **PII hard-upgrade:** registration + data storage → MUST output `lite_seed`. No self-rationalizing a downgrade in thinking.
- Only escape: user explicitly states "5 or fewer people + no data storage at all"
- Public-facing + concurrent users > 20 → upgrade to lite

### Token Plan Upgrade Advice (mandatory for all SKUs containing Token Plan)

**Sample output (zh-CN):**

```text
套餐含 Token Plan 标准版（25k/月），覆盖百炼全部模型。
- 用到 80%（≈20k）→ 升高级版（100k/月，¥698）
- 高级版 80% → 升尊享版（250k/月，¥1398）

升档前先报新月费让你确认才执行。降档等当前周期结束。
```

### Pro Tier Selection Question

Ask user:

**Sample output (zh-CN):**

```text
你目前最头疼的是哪种情况？
1. 用户量稳定、访问平稳，主要想高可用 → pro_steady
2. 流量集中某些时段（直播/活动/秒杀）→ pro_burst
```

---

## Part 4: Pricing CLI Reference (used by deploy)

> Deploy Phase 0 gate-check uses these CLI structures to query prices. Promo eligibility is auto-returned by the API; no need to pass RuleId.

### SWAS

```bash
aliyun swas-open describe-price \
  --commodity-type Server \
  --plan-id swas.s.c2m4s50b1.linux \
  --biz-region-id cn-beijing \
  --period 1 --price-unit Month --pay-type Prepaid
```

> Note: SWAS uses `biz-region-id` (not `RegionId`) and `plan-id` (not InstanceType)

### ECS

```bash
# Promo pricing (starter default)
aliyun ecs describe-price \
  --RegionId cn-beijing --ResourceType instance \
  --InstanceType ecs.e-c1m1.large \
  --PriceUnit Year --Period 1 \
  --SystemDisk.Category cloud_essd_entry --SystemDisk.Size 40 \
  --InternetChargeType PayByBandwidth --InternetMaxBandwidthOut 3 --Amount 1

# Fallback pricing (pay-by-traffic)
aliyun ecs describe-price \
  --RegionId cn-beijing --ResourceType instance \
  --InstanceType ecs.e-c1m1.large \
  --PriceUnit Year --Period 1 \
  --SystemDisk.Category cloud_essd_entry --SystemDisk.Size 40 \
  --InternetChargeType PayByTraffic --InternetMaxBandwidthOut 100 --Amount 1

# Lite/Pro (replace InstanceType; PL0 must be explicit)
aliyun ecs describe-price \
  --RegionId cn-beijing --ResourceType instance \
  --InstanceType <see Part 1 product table> \
  --PriceUnit Month --Period 1 \
  --SystemDisk.Category cloud_essd --SystemDisk.Size 40 \
  --SystemDisk.PerformanceLevel PL0 \
  --InternetChargeType PayByTraffic --InternetMaxBandwidthOut 100 --Amount 1
```

### RDS

```bash
aliyun rds describe-price \
  --RegionId cn-beijing --ZoneId cn-beijing-l \
  --Engine MySQL --EngineVersion 8.0 \
  --DBInstanceClass <see Part 1 product table> \
  --DBInstanceStorage <100 or 200> \
  --DBInstanceStorageType general_essd \
  --PayType Prepaid --TimeType Month --UsedTime 1 \
  --Quantity 1 --CommodityCode rds
```

### ESA

```bash
aliyun esa describe-rate-plan-price \
  --PlanName <free | medium> --Period 1 --Amount 1
```

---

## Advisor Output Contract

After completing the conversation, the advisor produces a structured YAML passed **internally to the `alibabacloud-opc-deploy` skill** — it is NOT dumped to the user. The user-facing output is the 5-section prescription (`诊断` / `处方` / `你会拿到什么` / `怎么搞起来` / `什么时候该升级`) ONLY. The `scope_declaration` (`我能做什么` / `不能做什么`) is internal YAML — passed to deploy, NEVER rendered to the user. The structured YAML MUST contain:

```yaml
advisor_recommendation:
  sku: <one of 7 SKU names>
  account_type: <personal_real_name | company_real_name | individual_business | unknown>
  region: cn-beijing
  estimated_monthly_price_cny: <exact value from Part 2>

advisor_questionnaire_answered:   # 7 fields filled from 2 asked (Q-scale→Q1_pv/Q3_qps, Q-userdata→Q2a/Q2b) + 5 inferred (Q4/Q5/Q6 + split); see sku-sizing-questionnaire.md §1/§6
  Q1_pv: ...
  Q2a_has_registration: ...
  Q2b_has_ugc_upload: ...
  Q3_qps: ...
  Q4_public: ...
  Q5_account_type: ...
  Q6_vlm: ...

scope_declaration:
  can_do: [SKU selection, ordering, deploy user's code, console guidance]
  cannot_do: [write business code, business ops, app-layer hardening guarantees, business decisions]

fallback_ecs_config:          # starter only
  instance_type: ecs.e-c1m1.large
  disk: { category: cloud_essd_entry, size_gb: 40 }
  internet: { charge_type: PayByTraffic, max_bandwidth_out: 100 }
  region_anchor: cn-beijing
  expected_price_yearly: 284.99

image:                        # all ECS-containing SKUs
  family: acs:alibaba_cloud_linux_3_2104_lts_x64
  os_series: "Alibaba Cloud Linux 3.2104 LTS"
  arch: x64
  family_pinned_at: "2026-06-25"
  next_review_due: "2026-12-25"

purchase_action: |            # A/B dual path (Chinese output)
  A. 让我帮你下单（推荐）
  B. 自己去 https://opc.aliyun.com/products → 选对应卡片
```

---

> **Maintenance:** Run Part 4 pricing commands on the 1st of each month. When promos expire, immediately update affected SKU prices.
