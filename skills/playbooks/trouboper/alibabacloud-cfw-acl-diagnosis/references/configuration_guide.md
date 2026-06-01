# Cloud Firewall ACL Configuration Guide

> This document provides console configuration guidance for Cloud Firewall ACL rules.
> All configuration must be manually completed by users in the Alibaba Cloud Console.

---

## 1. Internet Firewall Configuration

### 1.1 Enable Asset Protection

**Prerequisite**: Assets must be protected before ACL rules take effect.

**Console Path**: `Cloud Firewall Console` → `Firewall Switch` → `Internet Firewall`

**Steps**:
1. Navigate to Firewall Switch tab
2. Find target asset (public IP/EIP)
3. Toggle protection status to **ON** (ProtectStatus=open)
4. Wait ~30 seconds for生效

**Important**:
- Rules won't work if asset protection is disabled
- Verify in CLI: `DescribeAssetList` → `ProtectStatus=open`

### 1.2 Set ACL Engine Mode to Strict

**Required for**: Domain name rules to work properly.

**Console Path**: `Cloud Firewall Console` → `Firewall Switch` → `Internet Firewall` → Asset Settings

**Steps**:
1. Find target asset
2. Click ACL Engine Mode settings
3. Change from **Loose** to **Strict**
4. Confirm change

**Important**:
- In loose mode, domain rules don't participate in matching
- Only 4-tuple matching (src IP + dst IP + dst port + protocol)
- In strict mode, 7-tuple matching (adds application protocol + domain)

### 1.3 Create ACL Rule

**Console Path**: `Cloud Firewall Console` → `Protection Configuration` → `Access Control` → `Internet Traffic`

**Steps**:
1. Click "Create Rule"
2. Select direction: **Inbound** (external→internal) or **Outbound** (internal→external)
3. Configure match conditions:
   - **Source**: IP address / address book / location
   - **Destination**: IP address / domain / address book
   - **Port**: Single port or port range (e.g., 80/80, 1-1024)
   - **Protocol**: TCP / UDP / ICMP / ANY
4. For domain rules, select **Domain Recognition Mode**:
   - **FQDN**: Exact domain match
   - **DNS**: Based on DNS resolution
   - **Both**: FQDN + DNS
5. Set action: **Allow** / **Deny** / **Monitor**
6. Set rule priority (lower number = higher priority)
7. Click "OK"

**Important**:
- Direction must be correct: Inbound = external→internal, Outbound = internal→external
- Domain rules require strict mode enabled
- Multiple domains/IPs/ports: **Recommend creating address books** for management
- Rule takes effect in ~10-30 seconds

**⚠️ CRITICAL: Internet Firewall Outbound Rule Configuration**

Internet Firewall protects **public IP assets** (ECS public IP, EIP, NAT IP, SLB public IP, etc.).

| Direction | Source Field | Destination Field | Example Use Case |
|-----------|--------------|-------------------|------------------|
| **Inbound** (external→internal) | External IP or 0.0.0.0/0 | Protected asset's public IP/EIP | Allow SSH from specific IP to server |
| **Outbound** (internal→external) | **Protected asset's public IP** | **Target domain/IP or 0.0.0.0/0** | Allow server to access specific external API |

**Common Outbound Configuration Examples**:

✅ **Example 1: Allow specific ECS public IP to access only huawei.com**
- Direction: Outbound
- Source: 114.55.95.82/32 (ECS public IP)
- Destination: www.huawei.com (domain)
- DestinationType: domain
- Port: 80/443
- Action: Allow

✅ **Example 2: Deny all other outbound traffic (fallback rule)**
- Direction: Outbound
- Source: 114.55.95.82/32 (same ECS public IP)
- Destination: 0.0.0.0/0
- DestinationType: net
- Port: 0/0
- Proto: ANY
- Action: Deny

**Key Points**:
- Internet Firewall outbound: Source=protected asset's public IP, Destination=external target
- Protected assets include: ECS public IP, EIP, NAT Gateway IP, SLB public IP
- Domain rules require strict mode (EngineMode=strict)

### 1.4 Configure Address Books

**Console Path**: `Cloud Firewall Console` → `Protection Configuration` → `Address Book`

**Steps**:
1. Click "Create Address Book"
2. Select type: **IP** / **Domain** / **Location**
3. Enter name (no spaces, use _ or -)
4. Add entries (one per line)
5. Click "OK"

---

## 2. VPC Boundary Firewall Configuration

### 2.1 Enable VPC Boundary Firewall

**Console Path**: `Cloud Firewall Console` → `Firewall Switch` → `VPC Boundary Firewall`

**Steps**:
1. Enable VPC Boundary Firewall
2. Select VPC instances or CEN instances to protect
3. Confirm activation

### 2.2 Create ACL Rule

**Console Path**: `Cloud Firewall Console` → `Protection Configuration` → `Access Control` → `VPC Traffic`

**Steps**:
1. Click "Create Rule"
2. Configure match conditions:
   - **Source**: VPC CIDR / IP address
   - **Destination**: VPC CIDR / IP address
   - **Port**: Single port or port range
   - **Protocol**: TCP / UDP / ICMP / ANY
3. Set action: **Allow** / **Deny** / **Monitor**
4. Set rule priority
5. Click "OK"

**Important**:
- **No domain rules supported** (Layer 4 only: IP + port + protocol)
- **One-way rules**: Source→destination, need two rules for bidirectional access
- **No strict mode concept** (always 4-layer matching)

---

## 3. NAT Boundary Firewall Configuration

### 3.1 Enable NAT Boundary Firewall

**Console Path**: `Cloud Firewall Console` → `Firewall Switch` → `NAT Boundary Firewall`

**Steps**:
1. Enable NAT Boundary Firewall
2. Select NAT Gateway instances to protect
3. Confirm activation

### 3.2 Enable Strict Mode (Required for Domain Rules)

**Console Path**: `Cloud Firewall Console` → `Firewall Switch` → `NAT Boundary Firewall` → Settings

**Steps**:
1. Find Strict Mode setting
2. Change from **Loose** (0) to **Strict** (1)
3. Confirm change

**Important**:
- Domain rules **won't work** without strict mode
- Verify in CLI: `DescribeNatFirewallList` → `StrictMode=1`

### 3.3 Create ACL Rule

**Console Path**: `Cloud Firewall Console` → `Protection Configuration` → `Access Control` → `NAT Traffic`

**Steps**:
1. Click "Create Rule"
2. Configure match conditions:
   - **Source**: IP address / address book (must match actual source IP after SNAT)
   - **Destination**: IP address / domain / address book
   - **Port**: Single port or port range
   - **Protocol**: TCP / UDP / ICMP / ANY
3. For domain rules, select **Domain Recognition Mode**:
   - **FQDN**: Exact domain match
   - **DNS**: Based on DNS resolution
   - **Both**: FQDN + DNS
4. Set action: **Allow** / **Deny** / **Monitor**
5. Set rule priority
6. Click "OK"

**Important**:
- **Verify actual source IP** through NAT Gateway SNAT table before configuring rules
- Domain rules require strict mode enabled
- Multiple domains/IPs/ports: **Recommend creating address books**

---

## 4. Security Warnings

### 4.1 Rule Priority

- Rules are evaluated by `Order` value (ascending)
- First matching rule is executed, stops checking
- **Common mistake**: Broad rule with lower Order value blocks specific rule
- **Solution**: Set specific rules with lower Order values (higher priority)

### 4.2 Default Allow Behavior

- If no rules match, traffic is **allowed by default**
- **Recommendation**: Add a final "deny all" rule (0.0.0.0/0) at the end
- Example: Last rule → Deny 0.0.0.0/0 → 0.0.0.0/0 → ANY → ANY

### 4.3 Layer 7 Pre-Match Mechanism

**Applies to**: Internet/NAT firewall domain rules

When domain-type ACL policies are configured, Cloud Firewall starts pre-match mechanism:

```
Traffic arrives (e.g., telnet to example.com:80)
        ↓
System attempts application识别 (DPI)
        ↓
Cannot immediately identify domain (no HTTP request) → AppName=Unknown
        ↓
"Pre-matches" to L7 rule with domain configured (AclPreRuleId points to this rule)
        ↓
AclPreState = app_unknown → Allow first, wait for subsequent data to identify domain
        ↓
If始终无法识别 (e.g., pure TCP traffic) → Traffic continuously allowed
```

**Solutions**:
- Test domain rules using `curl -k "https://domain"`, **NOT telnet**
- To block pure TCP/Unknown traffic: Use DNS resolution mode, or configure Layer 4 fallback rule
- Allow only HTTP/HTTPS outbound: Configure L7 domain rule + final Layer 4 deny 0.0.0.0/0 rule

### 4.4 Rule Modification Delay

- Rules take effect in **10-30 seconds** after modification
- Wait before testing
- If still not working after 1 minute, re-check configuration

---

## 5. Best Practices

1. **Use address books** for multiple IPs/domains/ports
2. **Test in Monitor mode** before switching to Deny
3. **Document rule purposes** in rule names or descriptions
4. **Regular audit** of unused rules (check HitTimes)
5. **Configure deny-all fallback** rule at the end
6. **Enable strict mode** for domain rules
7. **Verify asset protection** is enabled (Internet firewall)
8. **Confirm actual source IP** before configuring NAT rules
