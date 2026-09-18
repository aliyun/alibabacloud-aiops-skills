# Instance Lifecycle, Create / Modify / Release / Billing Conversion

Covers Lindorm instance **write operations** for both V1 and V2: creation, configuration changes such as scaling and enabling engines, release, and billing conversion.

## Trigger Conditions

- "Create/provision a Lindorm instance"
- "Scale out/in, upgrade, add nodes, expand storage, or enable the search engine"
- "Release/delete/unsubscribe an instance"
- "Convert pay-as-you-go to subscription, or subscription to pay-as-you-go"

---

## [MUST] Universal Safety Protocol for Write Operations

Commands in this document affect billing or have irreversible consequences, unlike the read-only scenarios in this Skill. Before executing any command:

| # | Requirement |
|---|------|
| 1 | **Run `describe` first**: show `instance_id`, `instance_name`, `status`, `region_id`, and `pay_type`, and have the user confirm the target. |
| 2 | **Status must be `ACTIVATION`**: requests during `CREATING`, `RESIZING`, or `RELEASING` are rejected with `Instance.NotActive` or `OperationDenied.OrderProcessing`. Wait for `ACTIVATION`. |
| 3 | **Preview with `--dry-run` first**, where supported by create/modify. Explain the request JSON in plain language and remove `--dry-run` only after explicit approval. |
| 4 | **Do not choose optional values for the user**: region, zone, VPC, VSwitch, specification, and instance name all require the user to choose or explicitly delegate the recommendation to AI. |
| 5 | **Use `--yes` only after explicit user confirmation**. Never issue an unattended write. |
| 6 | **Release is irreversible**: confirm each instance separately. Do not use one ambiguous "yes" to release multiple instances. |
| 7 | **Use `--lindorm-region`**, never `--region`. See SKILL.md → "Region Policy". |

> A successful dry run does not guarantee that the real order succeeds. Many errors appear only during the real call; see the pitfalls in each section.

**Command form**: Examples use the `aliyun lindorm ...` plugin form. The standalone `lindorm-open-api-cli ...` uses identical subcommands and parameters; only standalone mode also accepts `--region`. See `references/03-ref/related-commands.md` for installation, credentials, global parameters, and return structures.

---

## 1. Create an Instance

### Step 1: Collect Requirements

Collect and map the following:

| User intent | Parameter | Description |
|---------|------|------|
| Instance name | `--name` | Must be provided by the user. Do not invent names such as `lindorm-demo-1234`. If the user says "anything", ask again. Omission prompts interactively and fails under `--non-interactive`. |
| Engine | First segment of `--engine` | KV/wide table → `TABLE`; time series → `TSDB`; search → `LSEARCH`; vector → `LVECTOR`; stream → `LTS`; column store → `LCOLUMN` |
| Region | `--lindorm-region` | For example, `cn-beijing` |
| Architecture | `--arch-version` | `1.0` single-zone / `2.0` multi-zone basic / `3.0` multi-zone high availability |
| Billing | `--pay-type` | `POSTPAY` pay-as-you-go / `PREPAY` subscription, plus `--duration` |
| Specification and node count | `--engine TABLE:<spec>:<count>` | See constraints below |
| Instance storage | `--cloud-storage-type` + `--cloud-storage-size` | `StandardStorage` / `PerformanceStorage` / `CapacityStorage` |

**V2 specification and node-count constraints**:

- Minimum two nodes per engine; the `LTS` stream engine is the exception and allows one node.
- Minimum specification is 8C16G, `lindorm.c.2xlarge`. The CLI rejects 4C specifications `lindorm.c.xlarge` and `lindorm.g.xlarge`.
- Node-count step: 1 for architecture `1.0`; 2 for `2.0` and `3.0`, so counts must be even.
- Storage minimum: `--cloud-storage-size` ≥ total instance node count × 80 GB; two nodes require at least 160 GB.
- Common specifications: `lindorm.c.2xlarge`=8C16G, `lindorm.g.2xlarge`=8C32G, `lindorm.g.4xlarge`=16C64G.
- Multiple engines can be combined by repeating `--engine`.

**Per-node disk**, optional and recommended only for architecture 3.0: append `:<DiskType>:<DiskSizeGB>` to `--engine`, for example `TABLE:lindorm.g.2xlarge:2:cloud_essd:400`, mapping to `NodeDiskType` and `NodeDiskSize`.

- Per-node disks are not recommended for architecture `1.0` or `2.0`, which use shared instance storage by default. The command can still succeed but writes `[warn]` to stderr. Prefer `--cloud-storage-type` and `--cloud-storage-size`.
- Architecture `3.0` recommends per-node disks; if omitted, only instance-level storage is used.

### Step 2: Select the Network

First ask whether the user wants to select values or delegate the recommendation to AI.

**Method A: The user selects from Agent-provided options**

Do not pipe automatic choices to CLI stdin. Use read-only commands to obtain structured candidates, present them to the user, then pass explicit IDs to `create`:

```bash
# 1. List VPCs in the region and present them for selection.
aliyun lindorm vpc list --lindorm-region <region> --output json

# 2. List all VSwitches in the selected VPC, group by zone_id, and present them.
aliyun lindorm vpc vswitch --vpc-id <chosen-vpc> --lindorm-region <region> --output json

# 3. Filter by zone when required.
aliyun lindorm vpc vswitch --vpc-id <chosen-vpc> --zone-id <zone> --lindorm-region <region> --output json
```

Presentation rules:

- List each option separately with its own number. Do not collapse options into ranges such as "2-8" or vague labels such as "other k8s VPC".
- Use specific labels, such as `yn-test (192.168.0.0/16)`.
- Even if a zone has only one VSwitch, show it and obtain confirmation instead of selecting silently.
- If there are more than four candidates, present the most relevant options and allow the user to provide another name or ID.

**Method B: AI recommends defaults**

Use reasonable defaults, preferring a test VPC and the zone with the most remaining IP addresses. Run `--dry-run` and present the complete configuration for approval.

**Method C: The user runs the interactive CLI**

When IDs are omitted, the CLI calls the VPC APIs and prompts by number. Omitting `--vpc-id` lists VPCs; omitting a zone lists zones in that VPC with available VSwitches, excluding zones already chosen for standby/coordinator; omitting a VSwitch lists VSwitches with remaining IP counts. Pressing Enter selects the first item.

Under `--non-interactive`, no selection prompt appears. Missing values fail immediately by flag name, such as `--vpc-id is required in non-interactive mode`, without making a network request. CI must pass every value explicitly.

### Step 3: Dry-run Preview

```bash
# Multi-zone architecture 2.0 or 3.0 requires three zones.
aliyun lindorm v2 instance create --lindorm-region <r> --name <n> --vpc-id <vpc> \
  --arch-version 2.0 --pay-type POSTPAY \
  --primary-zone-id <z1> --primary-vswitch-id <v1> \
  --standby-zone-id <z2> --standby-vswitch-id <v2> \
  --coordinator-zone-id <z3> --coordinator-vswitch-id <v3> \
  --engine TABLE:lindorm.g.2xlarge:4 \
  --cloud-storage-type PerformanceStorage --cloud-storage-size 400 --dry-run
```

Verify that dry-run output contains `ArbiterZoneId` and `ArbiterVSwitchId`. Missing values cause the real creation call to report the misleading `Resource.SoldOut`.

Single-zone architecture 1.0:

```bash
aliyun lindorm v2 instance create --lindorm-region <r> --name <n> \
  --zone-id cn-beijing-i --vpc-id <vpc> --vswitch-id <vsw> \
  --arch-version 1.0 --pay-type POSTPAY \
  --engine TABLE:lindorm.g.2xlarge:2 \
  --cloud-storage-type PerformanceStorage --cloud-storage-size 400 --dry-run
```

### Step 4: Create and Verify

Remove `--dry-run` and add `--output json`. Record `instance_id` and `order_id`, then run:

```bash
aliyun lindorm v2 instance describe <instance_id> --lindorm-region <r> --output json
```

After creation, proactively remind the user about billing and ask whether unused instances should be released.

### V2 Creation Pitfalls Not Caught by Dry Run

- **`Resource.SoldOut` often means a missing coordinator zone, not unavailable inventory.** For multi-zone 2.0/3.0, the most common cause is omitted coordinator/arbiter values. Both versions require `--coordinator-zone-id` and `--coordinator-vswitch-id`, and all three zones must differ. Treat `SoldOut` as real inventory exhaustion only after confirming all three zones.
- **`MissingZoneId`**: multi-zone creation still requires top-level `ZoneId`. The CLI fills it from the primary zone; use a version containing that fix.
- **`LindormErrorCode.LocalDiskCapacityZero`**: the `TABLE` engine has no storage. Add `--cloud-storage-type` and `--cloud-storage-size`, or for 3.0 only use `TABLE:spec:count:cloud_essd:400`.
- **`LindormErrorCode.ResourceEvaluateFailed`**: after confirming all three zones, this indicates real inventory shortage. Change the specification or zones; repeated multi-zone failures can fall back to single-zone `1.0`. Failed creation is not billed.
- **Per-node disk on 1.0/2.0**: the command succeeds but stderr warns that per-node-group disks are recommended only for 3.0. Remove the disk suffix from `--engine`.
- **bad file descriptor / occasional 443**: transient network issue; retry.
- Terminology: users see **coordinator**, while OpenAPI fields remain `ArbiterZoneId` and `ArbiterVSwitchId`.

### V1 Creation, CreateLindormInstance

V1 uses `v1 instance create` with a parameter model completely different from V2 `--engine`.

| User intent | CLI flag | API parameter | Notes |
|---|---|---|---|
| Wide table cloud-storage node specification | `--lindorm-spec` | `LindormSpec` | Minimum **16C64G**, `lindorm.g.4xlarge` |
| Wide table node count | `--lindorm-num` | `LindormNum` | Single-zone ≥ 2 |
| Total instance storage, GB | `--instance-storage` | `InstanceStorage` | Required; minimum 480 GB for two nodes |
| Disk type | `--disk-category` | `DiskCategory` | `cloud_efficiency` / `cloud_ssd` / `cloud_essd` |
| Billing | `--pay-type` | `PayType` | Must be `POSTPAY` or `PREPAY` |
| Local-disk node specification | `--core-spec` | `CoreSpec` | Only for `local_ssd_pro` / `local_hdd_pro` |
| Per-node local-disk storage | `--core-storage` | `CoreSingleStorage` | Only for multi-zone local disks |

```bash
# Create a single-zone V1 wide table cloud-storage instance.
aliyun lindorm v1 instance create \
  --name <name> --lindorm-region cn-beijing --zone-id cn-beijing-i \
  --vpc-id <vpc-id> --vswitch-id <vsw-id> \
  --lindorm-spec lindorm.g.4xlarge --lindorm-num 2 --instance-storage 480 \
  --disk-category cloud_efficiency --pay-type POSTPAY --output json
```

**V1 versus V2**: V2 uses `--engine TABLE:<spec>:<count>` with `--cloud-storage-*`; V1 uses `--lindorm-spec`, `--lindorm-num`, `--instance-storage`, and `--disk-category`. V1 has no `--dry-run`, so manually confirm the parameter summary before ordering. V1 `--core-spec` and `--core-storage` apply only to local-disk/multi-zone cases and must not be passed for cloud-storage wide tables.

### V1 Creation Pitfalls

- **`InvalidParameter.LindormSpec`**: cloud-storage wide table nodes require at least 16C64G, `lindorm.g.4xlarge`. Although 8C16G and 8C32G appear in enumerations, some regions do not sell them on this path. Try `lindorm.g.4xlarge`, then `lindorm.c.8xlarge` or `lindorm.g.8xlarge`.
- **`Commodity.NotFound`**: usually an invalid PayType enum, such as `PayAsYouGo` instead of `POSTPAY`. The API reaches commodity lookup and reports a missing SKU rather than invalid input. Use exactly `POSTPAY` or `PREPAY`.
- **`InvalidParameter.InstanceStorage (empty)`**: V1 cloud storage requires `--instance-storage`.
- **`InvalidParameter.TotalCoreCount`, core num < 2**: `--lindorm-num` is missing or below 2.
- **`InvalidParameter.InstanceStorage must be in [480`**: two nodes require at least 480 GB; follow the API-provided minimum.

---

## 2. Modify an Instance, Scaling / Upgrade / Enable Engine

> First identify the architecture from `arch` or `service_type` returned by `instance list` or `instance describe`. V1 and V2 use completely different APIs.

### V2 Modification, UpdateLindormV2Instance, Read-Modify-Write

The CLI first reads the current resources through `GetLindormV2InstanceDetails`, fills the existing engine topology back into the request, and overrides only the requested fields.

One call can change only one difference class, storage or nodes. Do not combine unrelated changes.

```bash
# Expand storage, the most common change.
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --cloud-storage-size 800 --dry-run
```

Confirm in dry-run output that `CloudStorageSize` has the new value while `CloudStorageType` and `EngineList`, including `GroupId`, still match the current instance.

**Adding nodes requires coupled storage expansion.** Shared cloud storage is distributed across all nodes: current total storage ÷ total nodes across engines = storage per node. If the target is unknown, first run with only `--engine`; `ModifyCheckFailed` returns the required minimum storage in its hint. Add that value and retry:

```bash
# Probe the target storage while changing 4 → 6 nodes.
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --engine TABLE:lindorm.g.2xlarge:6 --dry-run
# The API returns ModifyCheckFailed with "expand storage to 1200 GB".
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --engine TABLE:lindorm.g.2xlarge:6 --cloud-storage-size 1200 --dry-run
```

Confirm that the expanded group retains its original `GroupId` in the dry run. The CLI inherits it by engine type plus node specification, allowing the backend to expand the existing group rather than create a new one.

**Enabling a new engine is a full topology declaration, not an append.** `--engine` replaces the topology. Pass both existing and new engines, or omitted existing engines are treated as deletions:

```bash
# Add LSEARCH while retaining TABLE.
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --engine TABLE:lindorm.g.2xlarge:2 \
  --engine LSEARCH:lindorm.g.2xlarge:2 \
  --cloud-storage-size 800 --dry-run
```

Existing engines retain inherited `GroupId` values, creating zero differences. New engines have no GroupId and receive a new group from the backend. Storage must cover the new total node count.

**Storage scale-in flow**: When the CLI detects `new < current`, it prints a detailed warning. Present the following warning in full and obtain explicit consent, or stop:

> **⚠️ Storage Scale-in Risk Warning**
>
> **Service impact**: No obvious application impact, but prechecks apply. The new total capacity must exceed actual used data, or the operation is blocked. During scale-in, the instance is in storage-scale-in status and cannot accept other management operations such as enabling services or changing configuration.
>
> **Duration factors**: Data volume and node count.
>
> **Elapsed time**: Scale-in can take a long time; PB-scale data may require days. Run it during off-peak hours.
>
> **Quiet period**: After migration completes, a 12-hour quiet period begins and the cluster remains in configuration-scale-down status. This blocks management operations only; reads and writes continue normally.
>
> Reference: https://help.aliyun.com/zh/lindorm/user-guide/faq-about-instance-operation-and-maintenance

After confirmation, execute the command. The real CLI call also asks for y/N:

```bash
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --cloud-storage-size 400 --dry-run
```

**Execution and verification**:

```bash
# Remove --dry-run after user approval.
aliyun lindorm v2 instance modify <instance_id> --lindorm-region <r> \
  --cloud-storage-size 800 --output json
# Success returns order_id and request_id.

sleep 5
aliyun lindorm v2 instance describe <instance_id> --lindorm-region <r> --output json   # status -> RESIZING
```

The status changes to `RESIZING` and returns to `ACTIVATION` after completion.

### V1 Modification, UpgradeLindormInstance

Each call can perform only one modification type, determined by `UpgradeType`. The CLI infers it from flags, with optional explicit `--type`, describes the current state, runs local validation, prints a current-to-target summary, and asks for confirmation. `--yes` skips the prompt; `--non-interactive` rejects an unconfirmed operation.

| Intent | CLI flag | UpgradeType | Required/accompanying parameters |
|---|---|---|---|
| Expand cloud-disk storage | `--cluster-storage <GB>` | `upgrade-disk-size` | ClusterStorage, 480–1017600 |
| Enable/expand cold storage | `--cold-storage <GB>` | `upgrade-cold-storage` | ColdStorage, 800–1000000 |
| Upgrade wide table specification | `--lindorm-spec <spec>` | `upgrade-lindorm-engine` | LindormSpec |
| Change wide table node count | `--lindorm-num <n>` | `upgrade-lindorm-core-num` | Both LindormNum and ClusterStorage |
| Enable/modify time series | `--tsdb-spec` / `--tsdb-num` | `open-tsdb-engine` / `upgrade-tsdb-*` | Opens the engine if it does not exist |
| Enable/modify search | `--search-spec` / `--search-num` | `open-search-engine` / `upgrade-search-*` | Opens the engine if it does not exist |

- `ZoneId` is required by the API. Without `--zone-id`, the CLI fills it from describe.
- For multi-zone instances, use `--core-storage`, CoreSingleStorage, as per-node disk capacity.
- During modification, `--core-spec` is a deprecated alias of `--lindorm-spec`, retained only for compatibility. During creation it has a different valid meaning for local-disk node specification.
- Do not mix multiple modification types in one call; the CLI requires separate calls.

```bash
# Expand wide table nodes from 2 to 4; total storage must also reach the new minimum.
aliyun lindorm v1 instance modify ld-xxxx --lindorm-region cn-beijing --lindorm-num 4 --yes
#   -> LindormErrorCode.StorageInvalid: Please expand instance storage from 1120 to 1280 GB
# The error provides the target value; add --cluster-storage accordingly.
aliyun lindorm v1 instance modify ld-xxxx --lindorm-region cn-beijing \
  --lindorm-num 4 --cluster-storage 1280 --yes --output json

# Expand storage from 480 to 540 GB; UpgradeType is inferred as upgrade-disk-size.
aliyun lindorm v1 instance modify ld-xxxx --lindorm-region cn-beijing \
  --cluster-storage 540 --yes --output json
```

### V1 Modification Pitfalls

- **`LindormErrorCode.StorageInvalid: Please expand instance storage from X to Y GB`**: when adding nodes, `ClusterStorage` is required total instance storage and must meet the new minimum. The error provides Y. It occurs before order creation and is safe to retry.
- **`ClusterStorage` means total storage, not per-node storage.** `instance_storage` from describe may use a different validation basis; one observed case showed 540 in describe while the API reported current storage as 1120. Follow the API error values.
- **Cloud disks can expand but not shrink**: the CLI blocks `--cluster-storage` below the current value.
- **Minimum two nodes**: single-zone wide table requires at least two nodes; the CLI rejects `--lindorm-num 1`.

### V2 Modification Pitfalls

- **`MissingEngineList`**: `EngineList` is required by `UpdateLindormV2Instance`; a storage-only payload is insufficient. The CLI fills it automatically.
- **`LindormErrorCode.MultiChangeIsNotAllowedConcurrently`**: only one difference class is accepted per call. Pure storage expansion and pure specification changes are separate classes. Node expansion plus its mandatory storage increase is one class and must be sent together.
- **`ModifyCheckFailed ... Please expand instance storage to N GB`**: adding nodes or an engine requires increasing `--cloud-storage-size`. If unknown, omit it once and retry with the hinted value.
- **Minimum two nodes**, except `LTS` allows one. Node-count steps are 1 for 1.0 and 2 for 2.0/3.0. The backend validates modify; the CLI validates create.
- **`GroupId` is critical for zero-difference fill-back**: the backend matches node groups by GroupId. Without it, an unchanged group can be interpreted as a new group and trigger MultiChange. GroupId comes from `NodeGroup.SpecId`; the CLI maps and inherits it during `--engine` overrides.
- **The user selects when an engine has multiple node groups**: if GroupId is ambiguous, the CLI lists GroupId, specification, and node count for selection. `--non-interactive` fails with the candidates; switch to interactive mode or modify one group at a time.
- **Minimum specification 8C16G**: 4C `lindorm.c.xlarge` and `lindorm.g.xlarge` are rejected.
- Field mapping, details → request: `Engine`→`EngineType`, `NodeGroup.Quantity`→`NodeCount`, `NodeGroup.SpecId`→`GroupId`, `DiskCategory`→`CloudStorageType`.

---

## 3. Release an Instance

Release is irreversible and destroys both the instance and its data.

### Step 1: Confirm the Target

```bash
aliyun lindorm v2 instance describe <instance_id> --lindorm-region <r> --output json
# Use v1 instance describe for V1.
```

Show `instance_name`, `status`, `region_id`, `zone_id`, and `pay_type`.

- If status is already `RELEASING`, skip to Step 4 verification.
- If describe reports `Instance.IsDeleted`, tell the user that it is already gone.

### Step 2: Billing Gate, POSTPAY Only

| `pay_type` | Handling |
|---|---|
| `POSTPAY` / `PostPaid` / `PayAsYouGo` | ✅ Continue |
| `PREPAY` / `PrePaid` / `Subscription` | ❌ Stop. The CLI rejects release of prepaid instances. Direct the user to unsubscribe in the [console](https://lindorm.console.aliyun.com/). Do not call `release`. |
| Empty / unknown | ❌ Stop and ask the user to verify in the console. The CLI also rejects it for safety. |

### Step 3: Explicit Confirmation

State that the operation is irreversible and data will be destroyed. Include the exact instance ID, name, and pay type, and ask the user to confirm or cancel.

### Step 4: Release and Verify

```bash
aliyun lindorm v2 instance release <instance_id> --lindorm-region <r> --yes --output json
```

- `--yes` only skips the CLI prompt after Step 3 confirmation.
- The CLI always refreshes `pay_type` before release and rejects PREPAY even with `--yes`; the billing gate cannot be bypassed.
- Success returns `RELEASING` and `request_id`; asynchronous teardown takes several seconds.
- The underlying API is `ReleaseLindormV2Instance`, or `ReleaseLindormInstance` for V1.

```bash
sleep 8
aliyun lindorm v2 instance describe <instance_id> --lindorm-region <r> --output json   # Expect Instance.IsDeleted.
aliyun lindorm instance list --lindorm-region <r>                                     # The instance should be absent.
```

### Release Pitfalls

- `Instance.IsDeleted` from describe is the expected success signal, not a failure.
- `--immediate` skips the recycle bin and cannot be recovered. Use it only for temporary CI instances.
- POSTPAY instances continue billing until release. Remind the user to clean up unused instances, with separate confirmation for each.
- Do not confuse similarly named instances. Match by instance ID, not name.
- Modify only explicitly named instances. Ask before touching anything that merely looks abandoned.

---

## 4. Billing Conversion

The underlying `ModifyInstancePayType` API and parameters are shared by V1 and V2.

| From | To | Additional parameters |
|---|---|---|
| POSTPAY pay-as-you-go | PREPAY subscription | `--pricing-cycle Month\|Year` + `--duration N` |
| PREPAY subscription | POSTPAY pay-as-you-go | None |

### Flow

1. Run `describe`, confirm the target, record current `pay_type`, and require `ACTIVATION`.
2. Explain the current and target billing types, duration, and financial impact. PREPAY creates a new subscription order for immediate payment; POSTPAY conversion may forfeit remaining prepaid time or follow Alibaba Cloud refund policy. Obtain explicit confirmation.
3. Execute:

```bash
# Pay-as-you-go → one-month subscription.
aliyun lindorm v2 instance switch-pay-type <instance_id> --lindorm-region <r> \
  --pay-type PREPAY --pricing-cycle Month --duration 1 --yes --output json

# Subscription → pay-as-you-go.
aliyun lindorm v2 instance switch-pay-type <instance_id> --lindorm-region <r> \
  --pay-type POSTPAY --yes --output json
```

Success returns `instance_id`, `order_id`, and `request_id`.

4. Verify with `describe` that `pay_type` changed to the target.

### Parameters and Pitfalls

| Parameter | Description | Required |
|---|---|---|
| `--pay-type` | Target `PREPAY` or `POSTPAY` | Always |
| `--pricing-cycle` | `Month` or `Year` | PREPAY only |
| `--duration` | Month 1-9; Year 1-3 | PREPAY only |

- **Wrong direction**: requesting PREPAY when already PREPAY may error or do nothing. Describe the current value first.
- **Duration out of range**: Month 1-9 and Year 1-3 are validated locally before the API call.
- **Missing `--pricing-cycle`**: PREPAY conversion fails locally without calling the API.
- **Status is not ACTIVATION**: wait for `ACTIVATION`.
- **V1 and V2 are identical**: both command paths call the same API; the instance ID identifies the target.

---

## Verification Checklist

**Create**: dry-run JSON matches the user's intended region, architecture, zones, specification, storage, and billing → real creation returns `instance_id` and `order_id` → describe shows expected `zone_id`, `vpc_id`, and `pay_type`, with status progressing from `CREATING`/`LAUNCHING` to `ACTIVATION` → billing reminder delivered. V1 has no dry run, so manually confirm the parameter summary.

**Modify**: target described and ID/name confirmed, status `ACTIVATION` → dry run shown and approved, with one difference class and `EngineList` retaining correct `GroupId` values → real call returns `order_id` and `request_id` → status becomes `RESIZING`, and a follow-up read shows the new value.

**Release**: target described and exact ID/name confirmed → `pay_type` is POSTPAY, otherwise directed to the console → returns `RELEASING` and `request_id` → describe returns `Instance.IsDeleted` and list no longer shows it → only the named instance was released.

**Billing conversion**: target described and ID/name/current pay type confirmed, status `ACTIVATION` → direction and duration confirmed → returns `order_id` and `request_id` → describe shows the new `pay_type`.

---

## Related Scenarios

- Instance queries, including list/details/engines/storage → `instance-management.md`
- CLI quick reference, region rules, return structures, and read-only checks → `../03-ref/related-commands.md`
- Whitelist / security group → `network-access-control.md`
- Performance analysis before modification → `monitoring-guide.md`
- Storage usage analysis → `storage-analysis.md`
