# Cloud Firewall ACL Rule Knowledge Base

This document is a reference for rule configuration consultation scenarios, covering Internet Firewall, VPC Boundary Firewall, and NAT Boundary Firewall.

## Policy Matching Principles

### Match Fields

Cloud Firewall uses the following fields as match items and compares them with traffic packets one by one:
- Source address
- Destination address
- Destination port
- Transport protocol
- Application-layer protocol (Internet Firewall strict mode only)
- Domain name (Internet Firewall strict mode outbound only)

**Fields that do NOT participate in matching**: `Description` is for remarks only and does not affect matching logic.

### Matching Flow

```
Traffic enters → Rules are matched one by one in ascending Order
  ├─ Match → Execute the rule action (accept/drop/log), end
  ├─ No match → Continue to the next rule
  └─ No match for all rules → Default allow
```

### Loose Mode vs Strict Mode

| Dimension | Loose Mode | Strict Mode |
|------|----------|----------|
| Match fields | 4-tuple: source IP + destination IP + destination port + transport protocol | 7-tuple: 4-tuple + application protocol + domain |
| ApplicationName | Does not participate in matching, tag only | Participates in matching |
| Domain name | Does not participate in matching | Participates in matching |
| Applicable scenario | Basic IP/port-level control | Fine-grained application-layer control |
| 4-tuple match but application mismatch | Direct match (does not check application) | Skip and continue to the next rule |
| **Internet Firewall** | `EngineMode=loose` (asset-level) | `EngineMode=strict` (asset-level) |
| **NAT Firewall** | `StrictMode=0` (firewall-level) | `StrictMode=1` (firewall-level) |
| **VPC Firewall** | **Always loose mode** (strict mode not supported) | **Not supported** |

**Practical impact example**:

In loose mode, suppose there are two rules:
1. Order=1, Source=any, Dest=10.0.0.1, Port=443, Proto=TCP, App=HTTPS, Action=**drop**
2. Order=2, Source=any, Dest=10.0.0.1, Port=443, Proto=TCP, App=SSL, Action=**accept**

An SSL (non-HTTPS) request to port 443 comes in:
- Loose mode: Matches Rule 1 (4-tuple matches regardless of App), gets **dropped**
- Strict mode: Rule 1 4-tuple matches but App mismatch (HTTPS != SSL), skip; matches Rule 2, gets **accepted**

## Internet Firewall Rule Configuration

### Inbound Rules (in)

Control traffic from the Internet to cloud assets.

| Configuration Item | Supported Types |
|--------|-----------|
| Source address | IP/CIDR, address book, region |
| Destination address | IP/CIDR, address book (**domain and region not supported**) |

### Outbound Rules (out)

Control traffic from cloud assets to the Internet.

| Configuration Item | Supported Types |
|--------|-----------|
| Source address | IP/CIDR, address book |
| Destination address | IP/CIDR, address book, domain name, region |

### Protected Asset Determination

Determine the protected asset (i.e., the cloud asset) based on the rule direction:
- **Inbound rule**: Protected asset = Destination
- **Outbound rule**: Protected asset = Source

### Special Value Meanings

| Value | Meaning |
|----|------|
| `0.0.0.0/0` | All IPv4 addresses |
| `::/0` | All IPv6 addresses |
| `0/0` (port) | All ports |
| `ANY` (protocol) | All transport protocols |
| `ANY` (application) | All application-layer protocols |

## VPC Boundary Firewall Rule Configuration

### Overview

VPC Boundary Firewall protects traffic between VPCs connected through Cloud Enterprise Network (CEN) or Express Connect.

### Rule Characteristics

| Feature | Description |
|------|------|
| **Direction** | **No Direction parameter**, rules are unidirectional (Source → Destination) |
| **Strict mode** | **Not supported**, always Layer 4 matching |
| **Domain rules** | **Not supported**, destination address can only be IP/CIDR/address book |
| **FirewallId** | Requires `VpcFirewallId` parameter to locate the firewall instance |
| **Protected asset** | VPC CIDR / Cloud Enterprise Network instance |

### Source/Destination Addresses

| Configuration Item | Supported Types |
|--------|-----------|
| Source address | VPC CIDR, address book |
| Destination address | VPC CIDR, address book |

### Typical Scenarios

| Scenario | Configuration Idea |
|------|------|
| VPC-A accesses a specific service in VPC-B | Source=VPC-A CIDR, Dest=VPC-B service IP, Port=service port |
| Prohibit certain VPC mutual access | Source=VPC-A CIDR, Dest=VPC-B CIDR, Action=drop |
| Allow all VPC mutual access (default) | Do not configure rules (default allow) or configure a broad accept rule |

## NAT Boundary Firewall Rule Configuration

### Overview

NAT Boundary Firewall protects traffic passing through NAT Gateway (SNAT outbound / DNAT inbound).

### Rule Characteristics

| Feature | Description |
|------|------|
| **Direction** | **No Direction parameter**, rules are unidirectional (Source → Destination) |
| **Strict mode** | **Supported**, controlled by the `StrictMode` field (`0`=loose, `1`=strict) |
| **Domain rules** | **Supported** (requires strict mode `StrictMode=1`) |
| **FirewallId** | Requires `NatFirewallId` parameter to locate the firewall instance |
| **Protected asset** | NAT Gateway / cloud resources behind NAT |
| **ACL engine mode** | **Firewall-level**, all rules under one instance share the same mode |

### Source/Destination Addresses

| Configuration Item | Supported Types |
|--------|-----------|
| Source address | VPC CIDR, address book (private IP behind NAT) |
| Destination address | IP/CIDR, address book, region (Internet IP or specific destination CIDR) |

### Typical Scenarios

| Scenario | Configuration Idea |
|------|------|
| Assets behind NAT are only allowed to access specific external IPs | Source=NAT backend CIDR, Dest=allowed external IP, Action=accept + final drop |
| Assets behind NAT are prohibited from accessing certain external IPs | Source=NAT backend CIDR, Dest=prohibited external IP, Action=drop |
| Assets behind NAT access all external IPs (default) | Do not configure rules (default allow) or configure a broad accept rule |

## Rule Configuration Best Practices

### Allow Specific Traffic While Blocking Other Traffic

```
Rule 1 (smaller Order = higher priority): Allow target traffic
  Source: IP that needs to be allowed
  AclAction: accept

Rule 2 (larger Order = lower priority): Block remaining traffic
  Source: 0.0.0.0/0
  AclAction: drop
```

**Key**: The Order value of the allow rule must be smaller than that of the block rule.

### Control Outbound Traffic by Domain Name (Internet Firewall only)

```
Rule 1: Allow access to a specific domain
  Direction: out
  Destination: *.example.com
  DestinationType: domain
  AclAction: accept

Rule 2: Deny all other outbound traffic
  Direction: out
  Destination: 0.0.0.0/0
  DestinationType: net
  AclAction: drop
```

Note: Domain-type rules only participate in matching when the engine is in **strict mode**. In loose mode, domain rules are matched only by the 4-tuple.

### Use Address Books to Manage Multiple IPs

When the same policy needs to be applied to multiple IPs, create an address book for unified management:
- `SourceType: group` / `DestinationType: group`
- Address books support IP/CIDR lists
- Modifying address book content automatically affects all rules that reference it

### Verify Rules in Monitor Mode

Before new rules go live, you can first set `AclAction: log` (monitor) to confirm that the hit situation is correct, and then change it to `accept` or `drop`.

## Frequently Asked Questions (FAQ)

**Q: Is there a delay before rules take effect?**
A: Yes. It takes a few seconds to tens of seconds for rules to take effect after modification. If tested immediately after modification, the effect may not be visible.

**Q: Why can't domain names be selected for the destination address of inbound rules?**
A: The destination address of inbound traffic is the public IP of the cloud asset. There is no domain name resolution step, so domain-type destination addresses are not supported.

**Q: Is there an upper limit on the number of rules?**
A: Yes. Different editions have different upper limits. Enterprise Edition and Ultimate Edition have different rule quantity limits. You can view the remaining quota in the console.

**Q: Do domain rules take effect in loose mode?**
A: They still match at the 4-tuple level (IP + port + protocol), but the domain name itself does not participate in matching. If precise domain matching is required, strict mode must be used.

**Q: Do rules take effect immediately after an address book is modified?**
A: After an address book is modified, rules that reference that address book are automatically updated, but there is also a delay of a few seconds before they take effect.

**Q: What does a `HitTimes` field of 0 indicate?**
A: It indicates that the rule has never been matched by any traffic. This may be because the rule is newly created or the matching conditions are too strict.

**Q: Do VPC/NAT Firewalls support domain rules?**
A: **VPC does not support**, **NAT supports** (requires `StrictMode=1` strict mode). VPC Boundary Firewall only has Layer 4 matching capability, and the destination address can only be IP/CIDR or address book. NAT Boundary Firewall supports Layer 7 matching, but strict mode must be enabled.

**Q: Do VPC/NAT Firewalls have the concept of inbound/outbound?**
A: **No**. VPC/NAT Firewall rules have no Direction parameter; rule direction is implicitly determined by Source → Destination.

## Troubleshooting Checklists

### Internet Firewall

When a rule does not take effect, check the following in order:

1. **Is `Release` true?** — Is the rule switch turned on?
2. **Is `ProtectStatus` open?** — Is firewall protection enabled for the corresponding asset? ⚠️ **Most common issue**
3. **Is the `Direction` correct?** — Does inbound/outbound match the traffic direction?
4. **Order priority** — Is a higher-priority rule matched first?
5. **EngineMode** — Loose/strict affects whether the application-layer protocol participates in matching. ⚠️ **Domain rules require strict mode**
6. **Source/Destination range** — Does the address cover the actual traffic IP?
7. **DestPort port range** — Does it include the actual traffic port?
8. **Protocol** — Does it match the transport protocol of the actual traffic?
9. **Address book content** — If an address book is used, does the expanded CIDR list include the target IP?
10. **Activation delay** — Was the rule just modified? Wait a few seconds.

### VPC Boundary Firewall

When a rule does not take effect, check the following in order:

1. **Is the `VpcFirewallId` correct?** — Confirm through `DescribeVpcFirewallList`
2. **Is `Release` true?** — Is the rule switch turned on?
3. **Order priority** — Is a higher-priority rule matched first?
4. **Source/Destination range** — Does the VPC CIDR cover the actual traffic?
5. **DestPort port range** — Does it include the actual traffic port?
6. **Protocol** — Does it match the transport protocol of the actual traffic?
7. **CEN/Express Connect status** — Is the network connection normal?
8. **Activation delay** — Was the rule just modified? Wait a few seconds.

### NAT Boundary Firewall

When a rule does not take effect, check the following in order:

1. **Is the `NatFirewallId` correct?** — Confirm through `DescribeNatFirewallList`
2. **Is the NAT Firewall enabled?** — Query `NatFirewallList` and confirm the instance status. ⚠️ **Must be enabled first**
3. **Is `Release` true?** — Is the rule switch turned on?
4. **StrictMode engine mode** — Loose/strict affects whether the application-layer protocol participates in matching. ⚠️ **Domain rules require strict mode**
5. **Order priority** — Is a higher-priority rule matched first?
6. **Source/Destination range** — Does the address cover the actual traffic?
7. **SNAT actual IP** — Confirm the real source IP after the test server passes through SNAT. ⚠️ **Common issue**
8. **DestPort port range** — Does it include the actual traffic port?
9. **Protocol** — Does it match the transport protocol of the actual traffic?
10. **NAT Gateway status** — Is the NAT Gateway running normally?
11. **SNAT/DNAT rules** — Does the traffic pass through NAT translation?
12. **Activation delay** — Was the rule just modified? Wait a few seconds.

## Configuration Recommendations

> **Never assume asset protection is enabled (Internet Firewall)** — In real scenarios, many assets have `ProtectStatus=closed`.

> **Never assume strict mode is enabled (Internet Firewall)** — Default created resources are usually in loose mode.

> **VPC/NAT Firewall must provide the correct FirewallId** — Otherwise, the API will directly report an error.

> **VPC/NAT Firewall has no Direction parameter** — Do NOT pass `--Direction` to the VPC/NAT firewall creation interface.

> **After configuration is complete, always remind the user** — Rules have an activation delay, and testing immediately may not show results.
