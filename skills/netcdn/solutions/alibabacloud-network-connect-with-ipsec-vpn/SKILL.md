---
name: alibabacloud-network-connect-with-ipsec-vpn
description: |
  Scenario-based skill for connecting Linux servers to Alibaba Cloud VPC via IPsec VPN. Configure StrongSwan on the Linux server to establish dual-tunnel IPsec-VAN secure tunnels over the public network to access Alibaba Cloud VPC.
  Triggers: "connect edge server to Alibaba Cloud VPC", "connect server to Alibaba Cloud VPC"
---

# Connect Linux Server to Alibaba Cloud VPC via IPsec VPN (Guided)

## Scenario Description

Configure IPsec on a Linux server to establish a secure tunnel over the public network connecting to an Alibaba Cloud VPC. Typical use cases: edge servers, lightweight servers, Wuying cloud desktops, and edge nodes establishing secure tunnels via public network to access Alibaba Cloud VPC internal resources.

**Architecture**: Linux Server (StrongSwan) ←IPsec Dual Tunnel→ VPN Gateway → VPC + VSwitch + Security Group

## Preparation

**Requirements:**
* Linux server with public IP (NAT supported) and SSH key authentication
* Network: UDP 500/4500, ESP, TCP 22 allowed to this Linux server
* Alibaba Cloud VPC

Resource provisioning is outside this skill's scope.

## Pre-checks

### 1. Aliyun CLI version verification

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version
```

### 2. Authentication credential verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here** and configure credentials outside of this session.

## Phase 1: Permission Check

Before proceeding, verify that your Alibaba Cloud account has the necessary permissions.

**Required APIs:** `[vpc:DescribeRegions, vpc:DescribeVpcs, vpc:DescribeVswitches, vpc:CreateRouteEntry, vpc:CreateVpnGateway, vpc:DeleteVpnGateway, vpc:CreateCustomerGateway, vpc:DeleteCustomerGateway, vpc:CreateVpnConnection, vpc:DeleteVpnConnection]`

### Step 1.1: Use ram-permission-diagnose skill

Trigger the `ram-permission-diagnose` skill to diagnose current user's permissions:

```bash
# Trigger: ram-permission-diagnose
diagnose permissions for <your-current-user>
```

### Step 1.2: Compare against required policies

Refer to [references/ram-policies.md](references/ram-policies.md) for complete permission requirements.

**IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks, passwords, domain names, resource specifications, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

## Phase 2: Guided Parameter Collection

**Interaction Principles:**
- **Guided & User-Friendly**: Collect from basic to specific — start with foundational params (Region → VPC → VSwitch), use each to auto-query dependent options via API, then drill down to detailed configs
- **Interactive**: All parameters MUST be explicitly confirmed by user. NO auto-selection
- **Immutable Once Confirmed**: NEVER change a previously confirmed parameter without explicit user request
- **WAIT** for user confirmation at each step before proceeding

### Parameters to Collect

| # | Parameter | Source | Depends On |
|---|-----------|--------|------------|
| 1 | RegionId | API query `describe-regions` | — |
| 2 | VpcId | API query `describe-vpcs` | RegionId |
| 3 | Bandwidth & Billing | User choice (recommend 10Mbps, 1yr) | — |
| 4 | VPN Gateway Name | Auto-suggest `ipsec-vpn-{REGION}-{DATE}` | RegionId |
| 5 | Primary VSwitchId | API query `describe-vpn-gateway-available-zones` + `describe-vswitches` | RegionId, VpcId, Bandwidth |
| 6 | Backup VSwitchId | Same as above (must be different AZ) | Same as above |
| 7 | Server Public IP | User input (validate IPv4, warn if RFC1918) | — |
| 8 | SSH Username | User input (default: root) | — |
| 9 | SSH Private Key | User input (path to key file, default: ~/.ssh/id_rsa) | — |
| 10 | LocalSubnet | Recommend full VPC CIDR from Step 2 | VpcId |
| 11 | RemoteSubnet | User input (MUST be internal subnet, NOT public IP, NOT 0.0.0.0/0) | Server info |
| 12 | PSK | Auto-generate `openssl rand -base64 24` (min 16 chars) | — |

### Step 2.1: Select Region

```bash
aliyun vpc describe-regions --cli-query 'Regions.Region[].{RegionId:RegionId,LocalName:LocalName}' --user-agent AlibabaCloud-Agent-Skills
```

Highlight recommended regions (cn-beijing, cn-hangzhou, cn-shanghai, cn-shenzhen).

### Step 2.2: Select VPC

```bash
aliyun vpc describe-vpcs --region {REGION_ID} --biz-region-id {REGION_ID} --cli-query 'Vpcs.Vpc[].{VpcId:VpcId,VpcName:VpcName,CidrBlock:CidrBlock}' --user-agent AlibabaCloud-Agent-Skills
```

### Step 2.3: Configure Bandwidth & Billing

Bandwidth: 5/10(recommended)/20/50/100+ Mbps. Duration: 1mo/3mo/6mo/1yr(recommended)/2yr/3yr.

### Step 2.4: Select VSwitches (Primary + Backup, must be different AZ)

```bash
aliyun vpc describe-vpn-gateway-available-zones --region {REGION_ID} --biz-region-id {REGION_ID} --spec {BANDWIDTH}M --user-agent AlibabaCloud-Agent-Skills
aliyun vpc describe-vswitches --region {REGION_ID} --vpc-id {VPC_ID} --cli-query 'VSwitches.VSwitch[].{VSwitchId:VSwitchId,VSwitchName:VSwitchName,ZoneId:ZoneId,CidrBlock:CidrBlock,AvailableIpAddressCount:AvailableIpAddressCount}' --user-agent AlibabaCloud-Agent-Skills
```

Recommend pairs spanning different AZs. Validate: primary and backup MUST be in different AZ.

### Step 2.5: Server Information

- **Server Public IP**: User input. Validate IPv4 format; warn if RFC1918 private range detected.
- **SSH Username**: Default `root`. User can specify other admin user.
- **SSH Private Key**: Path to private key file (e.g., `~/.ssh/id_rsa`).
- **SSH IP**: Default same as Server Public IP. User can override if SSH uses a different IP/port.

### Step 2.6: Network Planning

- **LocalSubnet**: Recommend full VPC CIDR `{VPC_CIDR}` from Step 2.2
- **RemoteSubnet**: User input. Can SSH to server and run `ip addr show` to get internal subnet. ⚠️ MUST be internal subnet (e.g., 10.0.0.0/24), NOT public IP or 0.0.0.0/0

### Step 2.7: Generate PSK

```bash
PSK=$(openssl rand -base64 24 | tr -d '/+=' | head -c 20)
```

⚠️ Save PSK securely. NEVER echo in plain text. Offer: use generated / regenerate / enter custom (min 16 chars).

## Phase 3: Server-side Pre-check

SSH to server and collect network info before creating cloud resources:

```bash
ssh -o StrictHostKeyChecking=no -i {SSH_KEY_PATH} {SSH_USER}@{SSH_IP}
ip addr show && ip route show
```

**Record:** Server Internal IP, Local Subnet (e.g., 10.0.0.0/24), Default Gateway, Network Interface.

⚠️ `RemoteSubnet` in IPsec config must use server's **internal subnet**, NOT public IP or 0.0.0.0/0.

**OS & Privileges:** Check OS type, admin privileges, network connectivity, StrongSwan status (`which strongswan swanctl`). See [references/server-precheck.md](references/server-precheck.md).

## Phase 4: Confirm Configuration

Display collected parameters and ask user to confirm before proceeding. Explain the upcoming  steps.

## Phase 5: Create Cloud Resources

### Step 5.1: Create VPN Gateway

```bash
aliyun vpc create-vpn-gateway \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpc-id {VPC_ID} --name {VPN_NAME} --bandwidth {BANDWIDTH} --enable-ipsec true \
  --vswitch-id {PRIMARY_VSWITCH_ID} --disaster-recovery-vswitch-id {BACKUP_VSWITCH_ID} \
  --instance-charge-type PREPAY --period {PERIOD_MONTHS} --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills
```

Wait for activation (5-10 minutes), then get dual-tunnel IPs:

```bash
aliyun vpc describe-vpn-gateway --region {REGION_ID} --biz-region-id {REGION_ID} --vpn-gateway-id {VPN_GATEWAY_ID} --cli-query '{PrimaryIp:InternetIp,BackupIp:DisasterRecoveryInternetIp}' --user-agent AlibabaCloud-Agent-Skills
```

**Common Error Handling**

If you encounter `InvalidVSwitchId.SecondVswitchNotSupport` error when create vpn gateway, after double check the existance of this VSwitch, it means the availability zone of the backup VSwitch does not support VPN deployment.

**Solution:** Query VPN-supported availability zones and select a VSwitch in a suitable zone within the same VPC.

**Note:** Always use dual-tunnel mode. Do not fallback to single-tunnel mode.

### Step 5.2: Create Customer Gateway

```bash
aliyun vpc create-customer-gateway --region {REGION_ID} --biz-region-id {REGION_ID} --ip-address {SERVER_PUBLIC_IP} --name cgw-{VPN_NAME} --user-agent AlibabaCloud-Agent-Skills
```

Record `CustomerGatewayId`.

### Step 5.3: Create IPsec Connection (Dual-tunnel Mode)

**Important**: Current CLI version has limited support for `--tunnel-options-specification` parameter in plugin mode. Must use RPC style command with `--method POST --force` parameters.

```bash
aliyun vpc CreateVpnConnection \
  --RegionId {REGION_ID} \
  --VpnGatewayId {VPN_GATEWAY_ID} \
  --LocalSubnet {LOCAL_SUBNET} \
  --RemoteSubnet {REMOTE_SUBNET} \
  --Name ipsec-{VPN_NAME} \
  --EffectImmediately true \
  --AutoConfigRoute true \
  \
  --TunnelOptionsSpecification.1.CustomerGatewayId {CGW_ID} \
  --TunnelOptionsSpecification.1.Role master \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkeVersion ikev2 \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkeMode main \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkeAuthAlg sha256 \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkeEncAlg aes256 \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkeLifetime 86400 \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.IkePfs group14 \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.LocalId {VPN_GW_IP_1} \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.RemoteId {SERVER_PUBLIC_IP} \
  --TunnelOptionsSpecification.1.TunnelIkeConfig.Psk {PSK} \
  --TunnelOptionsSpecification.1.TunnelIpsecConfig.IpsecAuthAlg sha256 \
  --TunnelOptionsSpecification.1.TunnelIpsecConfig.IpsecEncAlg aes256 \
  --TunnelOptionsSpecification.1.TunnelIpsecConfig.IpsecLifetime 86400 \
  --TunnelOptionsSpecification.1.TunnelIpsecConfig.IpsecPfs group14 \
  \
  --TunnelOptionsSpecification.2.CustomerGatewayId {CGW_ID} \
  --TunnelOptionsSpecification.2.Role slave \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkeVersion ikev2 \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkeMode main \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkeAuthAlg sha256 \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkeEncAlg aes256 \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkeLifetime 86400 \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.IkePfs group14 \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.LocalId {VPN_GW_IP_2} \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.RemoteId {SERVER_PUBLIC_IP} \
  --TunnelOptionsSpecification.2.TunnelIkeConfig.Psk {PSK} \
  --TunnelOptionsSpecification.2.TunnelIpsecConfig.IpsecAuthAlg sha256 \
  --TunnelOptionsSpecification.2.TunnelIpsecConfig.IpsecEncAlg aes256 \
  --TunnelOptionsSpecification.2.TunnelIpsecConfig.IpsecLifetime 86400 \
  --TunnelOptionsSpecification.2.TunnelIpsecConfig.IpsecPfs group14 \
  \
  --method POST \
  --force \
  --user-agent AlibabaCloud-Agent-Skills
```

**Note**: This command uses RPC API style (traditional format) because the current plugin mode `create-vpn-connection` command has compatibility issues when handling `--tunnel-options-specification` parameter for dual-tunnel mode. Recommend reporting to Alibaba Cloud CLI team to improve plugin mode support.

Record `VpnConnectionId`.

## Phase 6: Add VPC Routes

⚠️ **Important:** Manual route addition may be required even with `--auto-config-route=true`.

```bash
# Step 6.1: Query Route Tables
aliyun vpc describe-route-table-list --region {REGION_ID} --biz-region-id {REGION_ID} --vpc-id {VPC_ID}  --user-agent AlibabaCloud-Agent-Skills

# Step 6.2: Add Route Entries (for each route table)
aliyun vpc create-route-entry --region {REGION_ID} --biz-region-id {REGION_ID} --route-table-id {ROUTE_TABLE_ID} --destination-cidr-block {REMOTE_SUBNET} --next-hop-id {VPN_GATEWAY_ID} --next-hop-type VpnGateway --user-agent AlibabaCloud-Agent-Skills

# Step 6.3: Verify Routes
aliyun vpc describe-route-entry-list --region {REGION_ID} --biz-region-id {REGION_ID} --route-table-id {ROUTE_TABLE_ID} --destination-cidr-block {REMOTE_SUBNET} --user-agent AlibabaCloud-Agent-Skills
```

Expected: Status = `Available`, next hop = VPN Gateway.

## Phase 7: Server-side StrongSwan Configuration

See [references/strongswan-config.md](references/strongswan-config.md) for complete StrongSwan configuration procedures including:
- **MUST read and follow** the referenced document before proceeding 
- Pre-configuration backup and validation steps
- Installation commands (Ubuntu/Debian/CentOS)
- `/etc/swanctl/swanctl.conf` template with dual-tunnel setup using VICI
- `/etc/strongswan.conf` configuration with VICI plugin
- Firewall rules (UDP 500/4500, ESP protocol)
- Kernel parameter setup (`net.ipv4.ip_forward`)
- Connection initiation and rollback procedures

**Note**: Must use the **VICI (Versatile IKE Configuration Interface)** method with `swanctl.conf` instead of the legacy `ipsec.conf` format. This allows both tunnels to be UP simultaneously using priority-based routing.

### Quick Steps:

1. **Backup existing configuration**:
   ```bash
   cp /etc/swanctl/swanctl.conf /etc/swanctl/swanctl.conf.bak.$(date +%Y%m%d) 2>/dev/null || true
   cp /etc/strongswan.conf /etc/strongswan.conf.bak.$(date +%Y%m%d) 2>/dev/null || true
   ```

2. **Install and configure StrongSwan** (see strongswan-config.md for details)

3. **Validate and load configuration**:
   ```bash
   swanctl --load-all
   ```

   **Note**: If `swanctl` command not found, read [strongswan-config.md](references/strongswan-config.md) and ensure `strongswan-swanctl` package is installed. **NEVER fallback to legacy ipsec.conf.**

4. **Initiate both tunnels**:
   ```bash
   swanctl --initiate --child aliyun-vpn-master-child
   swanctl --initiate --child aliyun-vpn-slave-child
   ```

5. **Verify tunnel status**:
   ```bash
   swanctl --list-sas
   ```

## Phase 8: Verification & Diagnostics

Perform real verification (no simulated data):

### Step 8.1: Check Aliyun Tunnel Status

```bash
aliyun vpc describe-vpn-connections --region {REGION_ID} --biz-region-id {REGION_ID} --vpn-connection-id {VCO_ID} --cli-query 'VpnConnections.VpnConnection[].TunnelOptionsSpecification.TunnelOptions[].{TunnelId:TunnelId,Status:Status,State:State}' --user-agent AlibabaCloud-Agent-Skills

# Or view full output
aliyun vpc describe-vpn-connections --region {REGION_ID} --biz-region-id {REGION_ID} --vpn-connection-id {VCO_ID} --user-agent AlibabaCloud-Agent-Skills
```

Expected: Both tunnels have:
- `State` = `active`
- `Status` = `ipsec_sa_established` (after StrongSwan is configured and started)

### Step 8.2: Check Server-side StrongSwan Status

Run on server:

```bash
sudo swanctl --list-sas
```

Expected: Both tunnels show `ESTABLISHED`.

Alternative detailed view:
```bash
sudo swanctl --stats
```

### Step 8.3: Real Connectivity Test

```bash
ping -c 5 {VPC_ECS_PRIVATE_IP}
```

Expected: All packets received with reasonable latency.

### Step 8.4: Troubleshooting if Failed

See [references/troubleshooting.md](references/troubleshooting.md) for detailed diagnosis:
- Check firewall rules (UDP 500/4500, ESP)
- Verify PSK matching
- Check IKE/IPsec parameter consistency
- Review tunnel logs on both sides

Full verification procedures: [references/verification-method.md](references/verification-method.md).

## Phase 9: Success Criteria

Success criteria:

- ✅ VPN Gateway status = `active`
- ✅ Dual tunnels both show `sa_established`
- ✅ Server-side StrongSwan both tunnels `ESTABLISHED`
- ✅ Bidirectional ping successful (Server ↔ VPC ECS)

## Phase 10: Cleanup (Optional)

Delete resources in order (requires explicit user confirmation):

```bash
# Step 1: Stop StrongSwan on server
sudo swanctl --terminate --ike aliyun-vpn-master
sudo swanctl --terminate --ike aliyun-vpn-slave
# Step 2: Delete IPsec connection
aliyun vpc delete-vpn-connection --region {REGION_ID} --biz-region-id {REGION_ID} --vpn-connection-id {VCO_ID} --user-agent AlibabaCloud-Agent-Skills
# Step 3: Delete customer gateway
aliyun vpc delete-customer-gateway --region {REGION_ID} --biz-region-id {REGION_ID} --customer-gateway-id {CGW_ID} --user-agent AlibabaCloud-Agent-Skills
# Step 4: Delete VPN gateway
aliyun vpc delete-vpn-gateway --region {REGION_ID} --biz-region-id {REGION_ID} --vpn-gateway-id {VPN_GATEWAY_ID} --user-agent AlibabaCloud-Agent-Skills
```

## Best Practices

1. **Security:** Use strong PSK (min 16 chars, mixed case, numbers, special chars). Rotate regularly.
2. **High Availability:** Deploy dual-tunnel mode with VSwitches across different AZs.
3. **Encryption Standard:** IKEv2 + AES256 + SHA256 + DH Group14 (modp2048).
4. **Parameter Consistency:** All IKE/IPsec params on Aliyun and server side MUST match exactly.
5. **Firewall Rules:** Critical! Allow UDP 500 (IKE), UDP 4500 (NAT-T), ESP protocol (#50).
6. **Route Management:** Always verify routes added after IPsec creation; auto-config may fail.
7. **Log Analysis:** Check both Aliyun tunnel logs and server-side StrongSwan logs when troubleshooting.
8. **NAT Traversal:** If server behind NAT, configure `local_addrs=%defaultroute` and `encap=yes` in swanctl.conf.
9. **Dual-Tunnel Mode:** Use `priority` parameter in swanctl.conf to allow both tunnels UP simultaneously (priority=100 for master, priority=200 for slave).

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation & configuration |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/server-precheck.md](references/server-precheck.md) | Server-side pre-check procedures |
| [references/strongswan-config.md](references/strongswan-config.md) | Complete StrongSwan VICI/swanctl config |
| [references/verification-method.md](references/verification-method.md) | Verification steps & diagnostics |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance test criteria |
| [references/troubleshooting.md](references/troubleshooting.md) | Common issues & solutions |
| [references/related-apis.md](references/related-apis.md) | Related APIs & CLI commands |
