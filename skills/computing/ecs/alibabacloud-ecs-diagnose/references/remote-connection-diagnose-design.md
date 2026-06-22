# Alibaba Cloud ECS Remote Connection / Service Access Diagnostic Guide

## Overview

This guide provides a systematic diagnostic workflow for Alibaba Cloud ECS remote
connection issues, applicable to scenarios such as SSH/RDP failures and inaccessible services.

---

## 1. Problem Localization Strategy

### 1.1 Initial Information Gathering

When a user reports "cannot remotely connect to an ECS instance" or "service is inaccessible",
use a **progressive information-gathering** strategy:

**Step 1: Ask for key information**

✩ Instance ID (required) — format: `i-xxxxxxxxxxxxxxxxx`
✩ Region (required) — e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`
✩ Connection method — SSH(22) / RDP(3389) / VNC / other ports / Workbench / Web service
✩ Error message or symptom description

**Rationale:**

✫ Avoid blind guessing; gather the minimum necessary information
✫ Provide a common-issues checklist so the user can do initial self-triage
✫ If the user provides only partial information, proactively request what is missing

### 1.2 Adaptive Lookup

When the user says "find it for me" or the information is incomplete, switch strategy immediately:

✩ Traverse common Alibaba Cloud regions to locate the instance
✩ Prioritize high-frequency regions: `cn-hangzhou`, `cn-beijing`, `cn-shanghai`, `cn-shenzhen`
✩ Stop searching as soon as the instance is found

> **⚠️ Empty-result handling ([MUST]):** If `describe-instances` still returns an empty
> result after traversing the candidate regions (`TotalCount = 0`), **follow the
> "Empty-result protocol" in Phase 0 of `SKILL.md`** strictly (terminate the workflow,
> do NOT enumerate/switch instances, output the fixed message template). This document
> does not repeat the rule, to keep a single source of truth.

**Region-traversal commands:**

```bash
# Get the list of all regions
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Look up the instance in a specific region
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxx"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

---

## 2. Systematic Diagnostic Workflow

### 2.1 Layered Diagnostic Model

```
Layer 1: Instance basic status
  ├─ Whether the instance exists
  ├─ Instance running status (Running/Stopped/Pending/Starting/Stopping)
  └─ System status check (StatusKey)

Layer 2: Network reachability
  ├─ Whether a public IP / Elastic IP (EIP) exists
  ├─ VPC / VSwitch configuration
  └─ Route tables and NAT gateway

Layer 3: Security control
  ├─ Security group inbound rules ⭐ most common issue
  ├─ Network ACL rules (Enterprise Edition VPC)
  └─ OS firewall (iptables/firewalld/Windows Firewall)

Layer 4: Authentication configuration
  ├─ Key pair configuration (Linux SSH)
  ├─ Login password (Linux/Windows)
  └─ Username correctness (root/ecs-user/Administrator)
```

### 2.2 Diagnostic Execution Order

#### Step 1: Get complete instance information

```bash
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --instance-ids '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**A single call returns:**

✫ Running status (Status)
✫ Public IP (PublicIpAddress)
✫ Elastic IP (EipAddress)
✫ Security group ID list (SecurityGroupIds)
✫ VPC / VSwitch ID (VpcAttributes)
✫ Key pair name (KeyPairName)
✫ Operating system type (OSType: linux/windows)

**Key field parsing:**

```json
{
  "Status": "Running",
  "PublicIpAddress": {"IpAddress": ["47.xx.xx.xx"]},
  "EipAddress": {"IpAddress": "47.xx.xx.xx"},
  "SecurityGroupIds": {"SecurityGroupId": ["sg-xxx"]},
  "VpcAttributes": {
    "VpcId": "vpc-xxx",
    "VSwitchId": "vsw-xxx",
    "PrivateIpAddress": {"IpAddress": ["192.168.x.x"]}
  },
  "KeyPairName": "my-keypair",
  "OSType": "linux"
}
```

#### Step 2: Check security group rules

```bash
# Query security group inbound rules
aliyun ecs describe-security-group-attribute \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**Focus on:**

✫ Whether SSH port 22 (Linux) or RDP port 3389 (Windows) is open
✫ Whether the target service port is open (e.g., 80, 443, 8080)
✫ Whether the authorization object (SourceCidrIp) includes the user's IP or `0.0.0.0/0`

**Security group rule response example:**

```json
{
  "Permissions": {
    "Permission": [
      {
        "PortRange": "22/22",
        "SourceCidrIp": "0.0.0.0/0",
        "IpProtocol": "TCP",
        "Policy": "Accept",
        "Direction": "ingress"
      }
    ]
  }
}
```

#### Step 3: Check instance system status

```bash
# Check instance status
aliyun ecs describe-instance-status \
  --biz-region-id <region> \
  --instance-id.1 <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Check system events (planned maintenance, anomalies, etc.)
aliyun ecs describe-instance-history-events \
  --biz-region-id <region> \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

#### Step 4: Check Cloud Assistant status (backup connection method)

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id.1 <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

#### Step 5: Provide solutions based on findings

---

## 3. Problem Identification Logic

### 3.1 Typical Diagnostic Result Example

```
Instance status check:
  ✓ Status: Running
  ✓ PublicIp: 47.xx.xx.xx
  ✓ KeyPairName: my-keypair

Security group rule check:
  ✓ 80/80 TCP - 0.0.0.0/0 (HTTP)
  ✓ 443/443 TCP - 0.0.0.0/0 (HTTPS)
  ❌ Missing 22/22 TCP (SSH) inbound rule
```

**Diagnostic conclusion:** Security group does not open the SSH port → this is the root
cause of 80% of connection issues.

### 3.2 Common Problem Patterns and Priority

| Priority | Problem Type | Proportion | Check Method |
|----------|--------------|------------|--------------|
| 1 | Security group port not open | 80% | DescribeSecurityGroupAttribute |
| 2 | Instance not running | 8% | DescribeInstances → Status |
| 3 | No public IP | 5% | Check PublicIpAddress and EipAddress |
| 4 | Key/password issue | 4% | User confirmation or verify via VNC |
| 5 | OS internal fault | 3% | Cloud Assistant or VNC diagnostics |

---

## 4. Solution Library

### 4.1 Add Security Group Rules

**Add SSH access rule (Linux):**

```bash
# Temporary option - allow all IPs (not recommended for production)
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range 22/22 \
  --source-cidr-ip 0.0.0.0/0 \
  --description "SSH access - temporary" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Recommended option - restrict to a specific IP
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range 22/22 \
  --source-cidr-ip <user-ip>/32 \
  --description "SSH access - specific IP" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**Add RDP access rule (Windows):**

```bash
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range 3389/3389 \
  --source-cidr-ip <user-ip>/32 \
  --description "RDP remote desktop access" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**Add Web service ports:**

```bash
# HTTP 80
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range 80/80 \
  --source-cidr-ip 0.0.0.0/0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# HTTPS 443
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range 443/443 \
  --source-cidr-ip 0.0.0.0/0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 4.2 Solution for Instance Without Public IP

**Option A: Bind an Elastic IP**

```bash
# 1. Create an EIP
aliyun vpc allocate-eip-address \
  --biz-region-id <region> \
  --bandwidth 5 \
  --internet-charge-type PayByTraffic \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# 2. Bind the EIP to the instance
aliyun vpc associate-eip-address \
  --biz-region-id <region> \
  --allocation-id <eip-allocation-id> \
  --instance-id <instance-id> \
  --instance-type EcsInstance \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**Option B: Use a NAT gateway (private-network instance)**

```bash
# Query NAT gateways
aliyun vpc describe-nat-gateways \
  --biz-region-id <region> \
  --vpc-id <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 4.3 Solution for Instance Not Running

```bash
# Start the instance
aliyun ecs start-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Check startup status
aliyun ecs describe-instance-status \
  --biz-region-id <region> \
  --instance-id.1 <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 4.4 Password Reset (when login is impossible)

```bash
# Reset password (requires a reboot to take effect)
aliyun ecs modify-instance-attribute \
  --instance-id <instance-id> \
  --password '<NewPassword123!>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Reboot the instance to apply the new password
aliyun ecs reboot-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 4.5 Connect via Cloud Assistant (backup option)

When neither SSH nor RDP is usable:

```bash
# 1. Check Cloud Assistant status
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id.1 <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# 2. Send a diagnostic command (command content must be Base64-encoded)
aliyun ecs run-command \
  --biz-region-id <region> \
  --instance-id.1 <instance-id> \
  --type RunShellScript \
  --command-content '<base64-encoded-command>' \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# 3. View command execution results
aliyun ecs describe-invocation-results \
  --biz-region-id <region> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 4.6 Use the VNC Console (last resort)

Via the Alibaba Cloud console:
✩ Log in to the ECS console
✩ Find the target instance → Remote Connect → VNC connection
✩ Log in with the VNC password to perform internal diagnostics

---

## 5. Verification Strategy

### 5.1 Multi-Layer Verification

**Verification 1: Configuration layer**

```bash
# Confirm the security group rule has been added
aliyun ecs describe-security-group-attribute \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

**Verification 2: Network layer**

```bash
# Test port reachability (10s timeout)
nc -zv -w 10 <public-ip> 22

# Or wrap telnet with timeout (10s timeout)
timeout 10 telnet <public-ip> 22
```

**Verification 3: Application layer**

```bash
# SSH connection test (10s timeout)
ssh -o ConnectTimeout=10 -i <key-file> root@<public-ip>

# RDP connection test (Windows) - use a remote desktop client or PowerShell
Test-NetConnection -ComputerName <public-ip> -Port 3389 -InformationLevel Detailed
```

### 5.2 Problem-Transfer Handling

Process for handling newly discovered issues:

```
SSH port is open but connection still fails
    ↓
Check the OS firewall
    ↓
Run via Cloud Assistant: iptables -L / firewall-cmd --list-all
    ↓
Found iptables blocking → provide disable/configure commands
    ↓
Verify the connection
```

---

## 6. User Interaction Design Principles

### 6.1 Progressive Disclosure

**Stage 1: Quick diagnosis**
✫ Start acting without waiting for the user to provide all information
✫ User says "find it for me" → immediately auto-search common regions

**Stage 2: Problem presentation**

```
Diagnostic result:
✓ Instance status: Running
✓ Public IP: 47.xx.xx.xx
✓ Cloud Assistant: installed
❌ Security group does not open port 22 ← root cause
```

**Stage 3: Solution**
✫ Provide concrete CLI commands
✫ Ask whether to execute them
✫ Give security recommendations

### 6.2 Operation Confirmation Rules

**Operations requiring user confirmation:**
✩ Modify security group rules
✩ Reboot the instance
✩ Reset the password
✩ Bind/unbind an EIP

**Operations that can run automatically:**
✩ Query instance information
✩ Check configuration status
✩ Test port connectivity
✩ Check Cloud Assistant status

### 6.3 Security Reminder

```
⚠️ Security recommendation:
The current configuration allows access from all IPs (0.0.0.0/0). Recommendations:
1. Restrict the source IP to your actual IP address
2. Your current public IP is: <obtained via API>
3. Recommended command: --SourceCidrIp <your-ip>/32
```

---

## 7. Parallel Diagnostics Optimization

### 7.1 Checks That Can Run in Parallel

```bash
# The following checks can run simultaneously:
Parallel task 1: aliyun ecs describe-instances ... --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}        # Instance status
Parallel task 2: aliyun ecs describe-security-group-attribute ... --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}  # Security group
Parallel task 3: aliyun ecs describe-cloud-assistant-status ... --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}    # Cloud Assistant
Parallel task 4: nc -zv -w 10 <ip> 22                    # Port test (10s timeout)
```

### 7.2 Smart Recommendation

Infer the required ports from the instance name/tags:

| Instance Name Keyword | Recommended Ports to Open |
|-----------------------|---------------------------|
| web, nginx, httpd | 80, 443 |
| mysql, mariadb | 3306 |
| redis | 6379 |
| mongodb | 27017 |
| postgresql | 5432 |
| elasticsearch | 9200, 9300 |
| rabbitmq | 5672, 15672 |

---

## 8. Common CLI Command Quick Reference

### 8.1 Instance Operations

```bash
# Query instance details
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --instance-ids '["<id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Query instance status
aliyun ecs describe-instance-status \
  --biz-region-id <region> \
  --instance-id.1 <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Start instance
aliyun ecs start-instance \
  --instance-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Stop instance
aliyun ecs stop-instance \
  --instance-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Reboot instance
aliyun ecs reboot-instance \
  --instance-id <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 8.2 Security Group Operations

```bash
# Query the security groups associated with the instance
aliyun ecs describe-security-groups \
  --biz-region-id <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Query security group rules
aliyun ecs describe-security-group-attribute \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Add an inbound rule
aliyun ecs authorize-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range <port>/<port> \
  --source-cidr-ip <cidr> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Delete an inbound rule
aliyun ecs revoke-security-group \
  --biz-region-id <region> \
  --security-group-id <sg-id> \
  --ip-protocol tcp \
  --port-range <port>/<port> \
  --source-cidr-ip <cidr> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 8.3 Network Operations

```bash
# Query EIPs
aliyun vpc describe-eip-addresses \
  --biz-region-id <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Allocate an EIP
aliyun vpc allocate-eip-address \
  --biz-region-id <region> \
  --bandwidth 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Bind an EIP
aliyun vpc associate-eip-address \
  --biz-region-id <region> \
  --allocation-id <eip-id> \
  --instance-id <instance-id> \
  --instance-type EcsInstance \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Unbind an EIP
aliyun vpc unassociate-eip-address \
  --allocation-id <eip-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

### 8.4 Cloud Assistant Operations

```bash
# Check Cloud Assistant status
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id.1 <id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Run a Shell command (Linux) - command content must be Base64-encoded
aliyun ecs run-command \
  --biz-region-id <region> \
  --instance-id.1 <id> \
  --type RunShellScript \
  --command-content '<base64-encoded-command>' \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# Run a PowerShell command (Windows) - command content must be Base64-encoded
aliyun ecs run-command \
  --biz-region-id <region> \
  --instance-id.1 <id> \
  --type RunPowerShellScript \
  --command-content '<base64-encoded-command>' \
  --timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}

# View command execution results
aliyun ecs describe-invocation-results \
  --biz-region-id <region> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-diagnose/{session-id}
```

---

## 9. Diagnostic Decision Tree

```
Start diagnosis
    │
    ▼
Does the instance exist? ──No──► Check that the instance ID and region are correct
    │Yes
    ▼
Is the instance Running? ──No──► Start the instance
    │Yes
    ▼
Does it have a public IP/EIP? ──No──► Bind an EIP or configure NAT
    │Yes
    ▼
Does the security group open the target port? ──No──► Add a security group rule
    │Yes
    ▼
Is the port reachable (nc/telnet)? ──No──► Check the OS firewall (iptables/firewalld)
    │Yes
    ▼
Is the SSH/RDP service running? ──No──► Start the service via Cloud Assistant
    │Yes
    ▼
Are the key/password correct? ──No──► Reset the password or replace the key
    │Yes
    ▼
Connection succeeds ✓
```

---

## 10. Summary

This diagnostic workflow embodies:

✩ **Systematic thinking**: a layered diagnostic model, troubleshooting from outside in
✩ **Efficiency first**: minimal information gathering, fastest problem localization
✩ **User-friendly**: proactive action, clear feedback, offering choices
✩ **Security awareness**: balancing convenience and security
✩ **Fault-tolerant design**: automatically adjusting strategy on new issues, providing backups
