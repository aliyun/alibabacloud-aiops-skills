---
name: alibabacloud-cloud-firewall-acl-manager
description: >
  Alibaba Cloud Cloud Firewall ACL policy management tool centered on
  backup/restore/management. Backs up and restores ACL policies (Internet
  boundary, NAT boundary, VPC boundary) together with their supporting
  configurations (address books - custom IP, cloud asset IP, custom domain,
  port; sync nodes - ACK cluster, private DNS), with differential restore
  (only fills items missing online). Also provides ACL policy export and
  statistical analysis (hit analysis, duplicate rule detection, shadow rule
  detection, compliance audit) and single-point changes (add policy,
  enable/disable). 以备份/恢复/管理为核心的阿里云云防火墙ACL策略管理工具。
  支持备份和恢复ACL策略（互联网边界、NAT边界、VPC边界）及其配套配置
  （地址簿：自定义IP、云资产IP、自定义域名、端口，同步节点：ACK集群、私有DNS），
  支持差异恢复（只补线上缺失项）；还提供ACL策略的导出与统计分析（命中分析、
  重复规则检测、影子规则检测、合规巡检）与单点变更（新增策略、启用/禁用）。
  当用户提到云防火墙备份、云防火墙恢复、地址簿备份、ACL策略备份、防火墙配置
  导出导入、ACL策略导出、策略命中分析、重复/影子策略检测、新增ACL策略、启用
  禁用策略时使用此技能。不提供策略删除/清理，需用户在控制台手动操作；不做规则
  不生效的故障诊断。
---

# Alibaba Cloud Cloud Firewall ACL Policy Manager

Manages Alibaba Cloud Firewall ACL policies and their supporting configurations
(address books, sync nodes): full backup, restore by type, differential restore;
plus ACL export and analysis (hit analysis, duplicate/shadow detection, compliance
audit) and single-point changes (add, enable/disable).

**Capability boundary**: this skill does NOT provide deletion or cleanup of ACL
policies or address books. Perform those operations manually in the Cloud Firewall
console.

## Operation Routing

| User intent | Command |
|-------------|---------|
| List all backup/restore options | `python scripts/backup.py --list` |
| Backup all configurations | `python scripts/backup.py --types 1` |
| Restore specific types | `python scripts/backup.py --types <options>` |
| Restore only missing items (same-account) | `python scripts/backup.py --types <options> --mode diff --yes` |
| Hit analysis / zero-hit detection | `python scripts/acl_manager.py hit` |
| Duplicate rule detection | `python scripts/acl_manager.py dup` |
| Shadow rule detection | `python scripts/acl_manager.py shadow` |
| Compliance audit (high-risk allow patterns) | `python scripts/acl_manager.py audit` |
| Add a single policy | `python scripts/acl_manager.py add ...` |
| Enable/disable a single policy | `python scripts/acl_manager.py switch ...` |

## User Notice (must present before the first run)

### 1. Supported address book types

| Category | Type | Notes |
|----------|------|-------|
| IP address book | Custom IP | User-defined IPv4/IPv6 address books |
| IP address book | Cloud asset IP | Cloud asset, ACK, ECS tag types |
| IP address book | Cloud service IP | Cloud service type address books |
| Domain address book | Custom domain | User-defined domain address books |
| Domain address book | Cloud service domain | Built-in type, no backup needed |
| Port book | Port book | User-defined port address books |
| Sync node | ACK cluster | ACK cluster connectors |
| Sync node | Private DNS | Private DNS endpoints (Custom maps to self-built DNS) |

### 2. Supported ACL policy types

- Internet firewall ACL policies
- NAT firewall ACL policies
- VPC firewall ACL policies

### 3. Types NOT supported for backup

Application control templates and web filtering templates are NOT supported.
If configured, back them up and restore them manually.

### 4. Restore order requirement (important)

Because configurations reference each other, restore in this order:

```
Step 1: Manually restore application control and web filtering templates (if enabled)
    |
Step 2: Restore sync nodes (ACK cluster + private DNS)  -> options 2, 3
    |
Step 3: Restore other address books  -> options 4, 5, 6, 7
    |
Step 4: Restore ACL policies  -> options 8, 9, 10
```

Violating the order may cause restore failures (for example, an ACL policy
referencing an address book that has not been restored yet).

### 5. Special notes

- Address books do not allow duplicate names. A name conflict reports "already
  exists" and the row is skipped.
- ACL policies allow duplicate names. Restore only appends; existing policies are
  never modified. All restored policies are inserted at the end of the list, so
  check the final policy order after restore.

## Prerequisites and Credentials

Credentials are resolved through the Alibaba Cloud Credentials SDK default
provider chain (`alibabacloud_credentials` with no explicit configuration).
The scripts never parse credential files and never accept or read explicit
AccessKey pairs. Configure credentials once with `aliyun configure` or a
standard credentials file, and the SDK picks them up automatically.

**Credential confidentiality (mandatory).** Never print, cat, or otherwise
dump the contents of credential files (`~/.aliyun/config.json`,
`~/.alibabacloud/credentials`) or credential-related environment variables,
and never echo AccessKey ID, AccessKey Secret, or STS token values in any
form - including truncated prefixes - in commands or responses. When
troubleshooting authentication errors, report only the API error message and
the credential mode in use (for example "StsToken profile resolved"), and
ask the user to re-run `aliyun configure` if credentials are missing.

Dependencies (pinned versions, validated end-to-end):

```bash
pip install -r scripts/requirements.txt
```

Required RAM permissions: see [references/ram-policies.md](references/ram-policies.md).

## Backup and Restore (backup.py)

### Step 1: list available options

```bash
python scripts/backup.py --list
```

### Step 2: present the menu to the user

```
[Backup]
  Option 1: backup all configurations (address books + ACL policies)

[Restore - address books]
  Option 2: sync node - ACK cluster
  Option 3: sync node - private DNS
  Option 4: custom IP
  Option 5: cloud asset IP
  Option 6: custom domain
  Option 7: port
[Restore - ACL policies]
  Option 8: Internet boundary
  Option 9: NAT boundary
  Option 10: VPC boundary
[Restore - all]
  Option 11: restore all address books + ACL
```

### Step 3: execute

```bash
# Backup all configurations
python scripts/backup.py --types 1

# Restore specific types (multiple allowed)
python scripts/backup.py --types 8

# Restore all
python scripts/backup.py --types 11

# Differential restore (mandatory when restoring into the SAME resource as the
# backup source, e.g. recovering an accidental deletion; only re-creates ACL
# policies missing online)
python scripts/backup.py --types 8 9 10 --mode diff --yes --input cfw_policy_backup_260824.xlsx

# Append restore onto DIFFERENT target resources (same-account gateway switch or
# cross-account): rewrite the resource IDs to the user-chosen targets
python scripts/backup.py --types 9 --mode append --yes --input cfw_policy_backup_260824.xlsx \
  --nat-target-gateways ngw-target1[,ngw-target2]
python scripts/backup.py --types 10 --mode append --yes --input cfw_policy_backup_260824.xlsx \
  --vpc-target-groups cen-target1[,cen-target2]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--list` | No | - | List all available options |
| `--types` | Yes | - | Option numbers (multiple allowed, space separated) |
| `--region` | No | cn-hangzhou | Alibaba Cloud region |
| `--output` | No | auto generated | Backup output file name |
| `--input` | No | latest backup file | Input file for restore |
| `--mode` | No | append | Restore mode: `append` = append restore (restoring into a fresh account or onto different target resources; combine with target flags to rewrite resource IDs); `diff` = differential restore (only missing items; only valid when restoring into the SAME resource as the backup source) |
| `--yes` | No | - | Skip the restore-order confirmation; non-interactive shells continue automatically |
| `--nat-target-gateways` | No | - | User-chosen target NAT gateway IDs (comma-separated, multiple allowed). In append mode this takes precedence: every policy's gateway ID is rewritten to the chosen targets and broadcast-restored to each. Covers both same-account gateway switch and cross-account restore |
| `--vpc-target-groups` | No | - | User-chosen target VPC policy group IDs (comma-separated, multiple allowed). In append mode this takes precedence: every policy's group ID is rewritten to the chosen targets and broadcast-restored to each. Covers both same-account group switch and cross-account restore |

### Scenario decision matrix for NAT/VPC restore (mandatory clarification)

NAT and VPC boundary policies are bound to account-specific resources: a NAT
policy needs a real NAT gateway (strictly validated by
CreateNatFirewallControlPolicy), and a VPC policy needs a policy group.
**Never silently reuse the backup file's resource IDs.** Before restoring
NAT/VPC policies, clarify the scenario with the user and pick the mode and
target accordingly:

| Scenario | Mode | Target resource |
|----------|------|-----------------|
| Same account, SAME gateway/group as the backup (recover accidental deletion) | `--mode diff` | The backup's own resource; only missing policies are filled in |
| Same account, DIFFERENT gateway/group (copy policies from gateway A to B) | `--mode append` | User-chosen target; policy IDs are rewritten via `--nat-target-gateways` / `--vpc-target-groups` |
| Cross-account, different gateway/group | `--mode append` | User-chosen target in the target account; same ID rewrite as above |

If the user's intent is ambiguous (target resource not stated), STOP and ask:
which gateway/policy group should receive the policies? Do not guess.
`--mode diff` and `--nat-target-gateways`/`--vpc-target-groups` are mutually
exclusive; the script rejects the combination.

Target resolution behavior in append mode:

- Explicit `--nat-target-gateways` / `--vpc-target-groups`: validated against
  the account (DescribeSecurityProxy / DescribeVpcFirewallAclGroupList), then
  every policy's resource ID is rewritten to the chosen targets regardless of
  whether the backup's IDs exist in this account.
- No explicit target and the backup's IDs exist in this account: fall back to
  the backup's IDs (same-resource append) with a hint to use `--mode diff`
  if the goal is filling missing items.
- No explicit target and the backup's IDs are missing: interactive terminals
  show a numbered multi-select list of available gateways/groups;
  non-interactive shells exit with guidance to pass the target flags.
  Selected targets receive a broadcast copy of every policy. Row status
  records partial success per row (e.g. `部分成功(1/2)`) so retries stay safe.
- Note: CreateVpcFirewallControlPolicy validates policy groups loosely; a
  missing group check here protects against writing policies into phantom
  groups that protect no real VPC firewall traffic.

### Backup sheets

Full backup writes `cfw_policy_backup_yymmdd.xlsx` with these sheets:

| Sheet | Content | API |
|-------|---------|-----|
| Sync node - ACK cluster | ACK cluster connectors | DescribeAckClusterConnectors |
| Sync node - private DNS | Private DNS endpoints | DescribePrivateDnsEndpointList + DescribePrivateDnsDomainNameList |
| Custom IP address book | IPv4/IPv6 address books | DescribeAddressBook (GroupType=ip,ipv6) |
| Cloud asset IP address book | Cloud asset/ACK/ECS tag | DescribeAddressBook (GroupType=asset,assetIpv6,ackNamespace,ackLabel,tag,tagPrivate) |
| Custom domain address book | Domain address books | DescribeAddressBook (GroupType=domain) |
| Port book | Port address books | DescribeAddressBook (GroupType=port) |
| Internet firewall ACL | Internet boundary policies | DescribeControlPolicy |
| NAT firewall ACL | NAT boundary policies | DescribeNatFirewallControlPolicy |
| VPC firewall ACL | VPC boundary policies | DescribeVpcFirewallControlPolicy |

Backup normalization: for Internet boundary policies whose application list
is empty in the Describe response (policies created via CLI/API without an
application binding, system defaults, NDR auto-created rules), the backup
records `ANY` instead of leaving the column blank. `ANY` is the server's
canonical value for "no specific application bound" (verified: a policy
created with `ANY` reads back as `['ANY']`), so the normalization is
lossless, keeps the backup file complete and reviewable, and satisfies the
mandatory ApplicationNameList parameter on restore.

### Restore mode selection (important)

ACL policies allow duplicate names and the built-in restore is a blind append
(all rows inserted at the end of the policy list). Choose the mode by scenario:

| Scenario | Mode | Reason |
|----------|------|--------|
| Restore into a fresh account (disaster recovery / environment copy) | `--mode append` (default) | No existing policies; full append is correct |
| Restore into the SAME resource of the backup source account (recover accidental deletion) | `--mode diff` | Blind append would duplicate every policy and change matching order |
| Restore onto a DIFFERENT gateway/policy group (same-account switch or cross-account) | `--mode append` + target flags | Target resource is different; rewrite IDs via `--nat-target-gateways` / `--vpc-target-groups` (see the scenario decision matrix above) |

For the Internet boundary (not bound to account-specific resources), the rule
simplifies to: fresh account -> append; backup source account -> diff.

Differential restore (`--mode diff`) workflow:

1. Fetch current online ACL policies (read-only Describe).
2. Render online rows with the plugin column definitions and compare row
   signatures against the backup sheet (volatile columns such as priority are
   excluded from the signature).
3. Only rows present in the backup but missing online are written to a temp
   sheet and restored through the plugin.
4. Re-run the same command to verify (expected missing count: 0).

Address books are idempotent server-side by name (duplicates report "already
exists" and are skipped), so both modes use the normal restore path without
duplication risk.

### Address book restore APIs

| Option | Type | Restore API | Notes |
|--------|------|-------------|-------|
| 2 | Sync node - ACK cluster | CreateAckClusterConnector | Create ACK cluster connector |
| 3 | Sync node - private DNS | CreatePrivateDnsEndpoint + AddPrivateDnsDomainName | Create endpoint and add domains |
| 4 | Custom IP | AddAddressBook (GroupType=ip/ipv6) | Create IP address book |
| 5 | Cloud asset IP | AddAddressBook (6 subtypes) | Create cloud asset/ACK/ECS tag address book |
| 6 | Custom domain | AddAddressBook (GroupType=domain) | Create domain address book |
| 7 | Port | AddAddressBook (GroupType=port) | Create port address book |

### ACL policy restore APIs

| Option | Type | Restore API | Notes |
|--------|------|-------------|-------|
| 8 | Internet boundary | AddControlPolicy | IPv4/IPv6, in/out directions |
| 9 | NAT boundary | CreateNatFirewallControlPolicy | Outbound direction only |
| 10 | VPC boundary | CreateVpcFirewallControlPolicy | Restored per policy group |

### Cloud asset IP subtypes

| Subtype | GroupType | Extra parameters |
|---------|-----------|------------------|
| Public asset | asset | AssetMemberUids, AssetRegionResourceTypes (JSON) |
| Public asset IPv6 | assetIpv6 | AssetMemberUids, AssetRegionResourceTypes (JSON) |
| ECS public tag | tag | TagList (flattened), AutoAddTagEcs, TagRelation |
| ECS private tag | tagPrivate | TagList (flattened), AutoAddTagEcs, TagRelation |
| ACK pod label | ackLabel | AckLabels (flattened), AckClusterConnectorId |
| ACK namespace | ackNamespace | AckNamespaces (flattened), AckClusterConnectorId |

### Restore status tracking

Each restore updates the "restore status" column in the Excel sheet:
- pending: not restored yet
- success: restored successfully
- failed: restore failed
- exists: resource already exists (skipped)
- skipped: already restored earlier (not re-created)

## ACL Policy Management (acl_manager.py)

Standalone ACL management, independent from backup/restore. No delete/cleanup is
provided. All write operations are Plan-First with two-phase confirmation: the
change plan is shown first, then executed after confirmation, then verified.

### Read-only analysis (zero risk)

```bash
# Hit analysis: sort by hit count, identify zero-hit policies (cleanup candidates)
python scripts/acl_manager.py hit --top 20

# Duplicate rule detection: merged across all three boundaries
python scripts/acl_manager.py dup

# Shadow rule detection: policies fully covered by a broader preceding rule
python scripts/acl_manager.py shadow

# Compliance audit: high-risk allow patterns (full CIDR + full port allow, etc.)
python scripts/acl_manager.py audit
```

Audit coverage: both inbound and outbound directions of the Internet boundary.
Check items: full CIDR + full port allow (high), high-risk port allow from/to
full CIDR (high), generic full-CIDR allow (medium), observe-mode policies (info).
The high-risk port list lives in `HIGH_RISK_PORTS` in `scripts/acl_manager.py`
(~50 ports across remote management, LAN services, mail, database, and
middleware categories, each with a brief risk note; sourced from public
security practice such as cnblogs.com/yjiejie/p/18405794). Generic web ports
(53/80/443/8080) are intentionally excluded to avoid false positives on
system default rules and normal web services.

### Single-point changes (write operations)

**Clarify before writing (mandatory).** Before executing `add`, every
required parameter must come from the user's request: boundary type,
direction, action, source + source type, destination + destination type,
protocol, and port. If any of them is missing or ambiguous, STOP and ask
the user for the missing values. NEVER fill gaps with the example values
shown below - they are syntax illustrations only, not safe defaults, and
executing them against a real account creates an unwanted policy. Confirm
the complete parameter set with the user before running with `--yes`.

No silent defaults exist for boundary, protocol, or port: `add` rejects
the command outright when any of them is missing. Do NOT infer missing
values from semantics alone (for example, reading "block access" as
protocol ANY + port 0/0) - such inferences are guesses, not user input.
In non-interactive environments where the user cannot be asked, output the
clarification questions as the final response and do NOT execute the
command.

```bash
# Add a single Internet boundary policy (dry-run first)
python scripts/acl_manager.py add --boundary internet --direction in --name "deny-test" \
  --acl-action drop --source 203.0.113.0/24 --destination 192.0.2.1/32 \
  --proto TCP --port 8080/8080 --description "test rule" --dry-run

# NAT boundary (direction is always out, gateway id required)
python scripts/acl_manager.py add --boundary nat --nat-gateway-id ngw-xxx \
  --name "nat-deny-test" --acl-action drop --source 10.0.0.0/16 \
  --destination 0.0.0.0/0 --proto TCP --port 23/23 --description "test rule" --dry-run

# VPC boundary (policy group id required; obtain from dup output or backup Excel)
python scripts/acl_manager.py add --boundary vpc --vpc-firewall-id cen-xxx \
  --name "vpc-deny-test" --acl-action drop --source 10.1.0.0/16 \
  --destination 10.2.0.0/16 --proto TCP --port 3306/3306 --description "test rule" --dry-run

# After confirming the plan, add --yes to execute
# (interactive terminals are prompted per step without --yes)

# Enable/disable a single policy (Internet boundary)
python scripts/acl_manager.py switch --acl-uuid <UUID> --direction in --disable --yes
# NAT/VPC boundaries require --boundary plus the scope parameter
python scripts/acl_manager.py switch --boundary nat --nat-gateway-id ngw-xxx --acl-uuid <UUID> --disable --yes
python scripts/acl_manager.py switch --boundary vpc --vpc-firewall-id cen-xxx --acl-uuid <UUID> --enable --yes
```

Write operation safety:
- Plan-First: a change plan table is printed before execution; `--dry-run` shows
  the plan without executing.
- Post-write verification: the policy state is re-checked after execution.
- Idempotent switch: policies already in the target state are skipped.
- Limitations: new policies are always appended at the end (NewOrder=-1); adjust
  priority in the console. NAT/VPC boundaries have no policy name field; the
  description serves as the identifier.
- Analysis limitations: hit counters are only provided by the Internet boundary
  API; coverage relations involving address book or domain types cannot be
  resolved automatically and are flagged for manual review.

## Observability

Every Cloud Firewall API call made by the scripts carries a User-Agent header
generated at the script layer:

- UA template: `AlibabaCloud-Agent-Skills/alibabacloud-cloud-firewall-acl-manager/{session-id}`
- session-id: 32-character lowercase hex string, generated once per session and
  reused for every API call within the same session.
- The UA is injected by `scripts/core.py` for all HTTP requests; no deprecated
  global configuration mechanism is used.
- An externally supplied `ALIBABA_CLOUD_USER_AGENT` environment variable, when
  set, takes precedence over the generated UA.

## Project Structure

```
alibabacloud-cloud-firewall-acl-manager/
- SKILL.md                        Skill document
- related_apis.yaml               Declared cloud APIs
- references/
  - ram-policies.md               Required RAM permissions
- scripts/
  - backup.py                     Main entry (backup/restore)
  - core.py                       Core engine (API calls, signing, Excel, credentials, UA)
  - diff_restore.py               Differential restore engine
  - acl_manager.py                ACL management (hit/dup/shadow/audit/add/switch)
  - requirements.txt              Pinned Python dependency versions
  - address_book/                 Address book plugins
    - __init__.py                 Auto-discovery registration
    - base.py                     Plugin base class (common restore logic)
    - custom_ip.py                Custom IP address book
    - cloud_asset_ip.py           Cloud asset IP address book (6 subtypes)
    - custom_domain.py            Custom domain address book
    - port.py                     Port book
    - ack_cluster.py              Sync node - ACK cluster
    - private_dns.py              Sync node - private DNS
  - acl_policy/                   ACL policy plugins
    - __init__.py                 Auto-discovery registration
    - base.py                     Plugin base class
    - internet.py                 Internet boundary ACL
    - nat.py                      NAT boundary ACL
    - vpc.py                      VPC boundary ACL
```
