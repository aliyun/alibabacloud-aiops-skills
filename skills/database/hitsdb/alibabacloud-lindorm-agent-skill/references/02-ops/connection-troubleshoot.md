# Connection Troubleshooting Scenarios

When a user reports issues such as "unable to connect to the Lindorm instance" or "connection timeout", follow this guide for troubleshooting.

## Trigger Conditions

Typical user expressions:
- "Cannot connect to the instance"
- "Connection timeout"
- "Unable to access Lindorm"
- "Is the whitelist configuration correct?"
- "Why is the connection refused?"

## Troubleshooting Principles

Connection troubleshooting uses a **layered troubleshooting** strategy: instance status → whitelist → network configuration, locating the issue layer by layer.

Output format: **Issue Location → Root Cause Analysis → Solution**

## Execution Flow

### Step 1: Check Instance Status

**Purpose**: Confirm whether the instance is running normally.

**Command**:

```bash
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>
```

**Check points**:

| Instance Status | Meaning | Connectable | Solution |
|---------|------|:--------:|----------|
| `ACTIVATION` | Running | ✅ Yes | Continue checking other items |
| `CREATING` | Creating | ❌ Wait | Wait until instance creation is complete, usually 10 to 30 minutes |
| `MAINTAINING` | Maintaining | ⚠️ May be interrupted | Wait until maintenance is complete or contact technical support |
| `STOPPED` | Stopped | ❌ Need to start | Start the instance before connecting |
| `DELETED` | Released | ❌ Cannot recover | The instance has been released and cannot be connected |
| `CLASS_CHANGING` | Specification changing | ⚠️ May be interrupted | Wait until the specification change is complete |

**Output example**:

```text
[Step 1: Instance Status Check]

✅ Instance status is normal
- Instance ID: ld-uf6l5kr48wqm6rf1h
- Status: ACTIVATION, running
- Created at: 2025-01-15 10:30:00

Continue checking whitelist configuration...
```

If the status is abnormal:

```text
[Step 1: Instance Status Check]

❌ Instance status is abnormal
- Instance ID: ld-uf6l5kr48wqm6rf1h
- Status: CREATING, creating

[Root Cause] The instance has not been created yet and cannot be connected.

[Solution]
- Wait 10 to 30 minutes. The instance automatically changes to ACTIVATION after creation is complete.
- You can continuously check the status through the get_instance command.
```

---

### Step 2: Check Whitelist Configuration

**Purpose**: Confirm whether the client IP address is in the whitelist.

**Command**:

```bash
aliyun hitsdb get-instance-ip-white-list \
    --instance-id <instance-id>
```

**Check points**:

- Does the whitelist contain the client IP address?
- Is the whitelist format correct?
  - Single IP: `192.168.1.100`
  - CIDR block: `192.168.1.0/24`
  - Public access: `0.0.0.0/0`, which is ⚠️ not recommended because it has high security risk
- Internal access requires either the same VPC or the VPC CIDR block in the whitelist.

**Output example**:

```text
[Step 2: Whitelist Check]

Current whitelist configuration:
- 10.0.0.0/8, internal VPC CIDR block
- 172.16.1.100, specific IP

[Check Result]
- Your client IP: 192.168.1.50
- ❌ Not in the whitelist

[Root Cause] The client IP is not in the whitelist, so the connection is refused.

[Solution]
1. Option 1: Add the client IP to the whitelist.
   
   📍 Exact path:
   1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
   2. On the instance list page, click the **target instance ID**.
   3. In the left-side navigation pane, click **Access Control** → **Whitelist**.
   4. Click "Modify" to add the client IP:
      - Single IP: 192.168.1.50
      - CIDR block: 192.168.1.0/24

2. Option 2: Access from an ECS instance in the same VPC.
   - Make sure ECS and Lindorm are in the same VPC.
   - Configure the whitelist as the VPC CIDR block, such as 10.0.0.0/8.

For more details, see the official whitelist configuration guide:
https://help.aliyun.com/zh/lindorm/getting-started/configure-a-whitelist

Do you need help checking the network configuration?
```

---

### Step 3: Check Network Configuration

**Purpose**: Confirm whether the network type matches the access method.

**Command**:

```bash
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>
```

**Check points**:

Extract network configuration from instance details:
- `NetworkType`: Network type, such as `vpc`
- `VpcId`: VPC ID
- `VswitchId`: vSwitch ID

**Network type and access method**:

| Network Type | Access Method | Requirement | Connection Address Feature |
|---------|---------|------|---------------|
| `vpc` | **Internal access** | Client is in the same VPC | V1: `-vpc.lindorm.rds.aliyuncs.com`; V2: `-vpc.lindorm.aliyuncs.com`, Type=INTRANET |
| `vpc` | **Public access** | Public endpoint enabled + whitelist contains the public IP | V1: `-pub.lindorm.rds.aliyuncs.com`; V2: `-pub.lindorm.aliyuncs.com`, Type=INTERNET |

**Output example**:

```text
[Step 3: Network Configuration Check]

Network configuration:
- Network type: VPC
- VPC ID: vpc-uf6xxxxx
- vSwitch ID: vsw-uf6xxxxx

[Access Method Judgment]
- Your client: public IP, 182.92.xxx.xxx
- Instance configuration: VPC internal network

[Root Cause] The instance uses VPC internal access, while the client is on the public network and cannot directly connect.

[Solution]
1. Option 1: Access from an ECS instance in the same VPC.
   - Create an ECS instance in the same VPC.
   - Access Lindorm through the ECS internal IP address.

2. Option 2: Enable a public connection address. Recommended for public network users.
   
   📍 Exact path:
   1. Console: https://lindorm.console.aliyun.com/
   2. Click instance ID "ld-xxx".
   3. Left-side menu: **Configuration and Management** → **Database Connection**.
   4. Find the corresponding engine and click **Apply for Public Connection Address**.
   5. Wait until the public address is generated, usually 1 to 3 minutes.
   6. Go to **Configuration and Management** → **Access Control** → **Whitelist** and add the client public IP.

   > ⚠️ Enabling a public address is not the same as binding an EIP. Lindorm public access is implemented by applying for a public connection address and does not require binding an EIP.

3. Option 3: Configure VPN or Express Connect.
   - Connect the client network to the VPC through VPN or Express Connect.

For more details, see the official connection guide:
https://help.aliyun.com/zh/lindorm/getting-started/connect-to-an-instance
```

---

### Step 4: Network Connectivity Test (Advanced Troubleshooting)

**Purpose**: Use network tools such as ping and telnet to verify network connectivity.

**⚠️ Prerequisite**: The first three checks are normal, but the connection still fails.

#### 4.1 Use ping to Test Network Reachability (Reference Only)

**⚠️ Note**: The ping test is for reference only. **Ping failure does not mean the instance cannot be connected**.

**Applicable scenario**: Initially determine network-layer connectivity. Lindorm may disable ICMP responses.

**Procedure**:
```bash
# Run on the client machine.
ping <lindorm-host>

# Example.
ping lindorm-xxx.lindorm.rds.aliyuncs.com
```

**Result judgment**:

| Result | Meaning | Next Step |
|-----|------|----------|
| ✅ Normal response | Network layer is reachable | Continue checking the port, step 4.2 |
| ❌ Request timeout | ICMP is disabled or network is unreachable | **Continue testing the port with telnet. Do not directly judge the network as unreachable.** |
| ❌ Unknown host | DNS resolution failed | Check DNS configuration or connect directly by IP |

**Important tips**:
- Cloud products usually disable ICMP ping responses to improve security.
- **When ping fails, prefer `telnet/nc` or direct client connection tests**.
- Only when telnet also fails should it be considered a network connectivity issue.

**Complete troubleshooting guide**:
- Official documentation: [Use the ping command to check the connection](https://help.aliyun.com/zh/lindorm/support/run-the-ping-command-to-check-the-connection-between-an-ecs-instance-and-a-lindorm-instance)

#### 4.2 Use telnet to Test Port Connectivity

**Applicable scenario**: Ping succeeds but connection still fails, and you need to test whether a specific port is open.

**Procedure**:
```bash
# Test the wide table engine HBase API port.
telnet <lindorm-host> 30020

# Test the wide table engine MySQL protocol port. Recommended.
telnet <lindorm-host> 33060

# Test the time series engine port.
telnet <lindorm-host> 8242

# Test the search engine port.
telnet <lindorm-host> 30070
```

**Common ports**:

Use `SKILL.md` → "Code generation specifications / Port number quick reference" as the authoritative source for ports.

**Result judgment**:

```bash
# ✅ Port is reachable, normal.
Trying <ip>...
Connected to <host>.
Escape character is '^]'.

# ❌ Port is unreachable, abnormal.
Trying <ip>...
telnet: connect to address <ip>: Connection refused
```

**Common issues**:
- Port unreachable → Check whether security group rules allow the corresponding port.
- Port reachable but connection fails → Check authentication information, such as username, password, or AccessKey.

**Complete troubleshooting guide**:
- Official documentation: [Use the telnet command to check port connectivity](https://help.aliyun.com/zh/lindorm/support/run-the-telnet-command-to-check-the-connectivity-of-the-service-ports-of-lindorm)

#### 4.3 Check Security Group Rules

**Applicable scenario**: ping or telnet fails, and the ECS security group needs to be checked.

**Check points**:
1. ECS outbound rules: allow access to the Lindorm IP and ports.
2. Lindorm whitelist: contains the ECS IP address.

**Configuration example**:
```text
ECS security group outbound rule:
- Protocol: TCP
- Port range: Allow the ports based on the engine or protocol used. For ports, see SKILL.md → "Code generation specifications / Port number quick reference".
- Destination: Lindorm instance IP or 0.0.0.0/0

Lindorm whitelist:
- Add the ECS private IP or VPC CIDR block.
```

---

## Common Issues and Solutions

### Issue 1: Connection Timeout

**Possible causes**:
1. Instance status is not ACTIVATION.
2. Network is unreachable, such as VPC or whitelist issues.
3. Port is not open or blocked by a firewall.

**Troubleshooting steps**:
1. Check instance status, Step 1.
2. Check whitelist configuration, Step 2.
3. Check network configuration, Step 3.
4. Confirm that the correct connection address and port are used.

---

### Issue 2: Authentication Failed

**Possible causes**:
1. Username or password is incorrect.
2. AccessKey has no permission.

**Troubleshooting steps**:
1. Confirm that the username and password are correct in the Lindorm console → Account Management.
2. Confirm that the AccessKey has Lindorm operation permissions in the RAM console → Permission Management.

---

### Issue 3: Public Network Cannot Access

**Possible causes**:
1. Public access is not enabled, meaning no public connection address has been applied for.
2. The whitelist does not contain the public IP address.

**Troubleshooting steps**:
1. Confirm that a public connection address is enabled for the instance. In the Lindorm console, go to Configuration and Management → Database Connection and check whether a public address exists.
2. Confirm that the whitelist contains the public IP address, Step 2.

---

### Issue 4: Internal Network Cannot Access

**Possible causes**:
1. The client is not in the same VPC.
2. The VPC access whitelist is not configured.

**Troubleshooting steps**:
1. Confirm that the client is in the same VPC, Step 3.
2. Confirm that the whitelist contains the VPC CIDR block, Step 2.

---

## Common Connection Errors and Solutions

When the Agent encounters a connection error, it should query the official documentation for detailed solutions:

**⭐ Key documents**:
- **Lindorm connection issues and solutions**: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- **Lindorm connection errors and solutions**: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions

**Common error types**:

| Error Type | Example Error Message | Reference Documentation |
|---------|------------|---------|
| **Connection timeout** | Connection timeout, SocketTimeoutException | The preceding documents + ping/telnet troubleshooting |
| **Connection refused** | Connection refused | Check ports, security groups, and whitelist |
| **Authentication failed** | Authentication failed | Check username, password, and AccessKey |
| **Network unreachable** | Network is unreachable | Check VPC and route table |
| **DNS resolution failed** | Unknown host | Check DNS configuration |

**Special scenario**:
- **Spark access connection timeout**: https://help.aliyun.com/zh/lindorm/support/cause-analysis-of-connection-timout-problem-in-sparkonmc-access-to

---

## Obtain Connection Addresses

Different Lindorm engines have different connection addresses. **Always select the corresponding address based on the client environment**:

### Confirm the Client Environment

| Client Location | Address to Use | Address Feature |
|-----------|-------------|----------|
| Alibaba Cloud ECS, same VPC | Internal address | V1: `-vpc.lindorm.rds.aliyuncs.com`; V2: `-vpc.lindorm.aliyuncs.com`, Type=INTRANET |
| Local computer / public server | Public address | V1: `-pub.lindorm.rds.aliyuncs.com`; V2: `-pub.lindorm.aliyuncs.com`, Type=INTERNET |
| Alibaba Cloud ECS, cross VPC | Public address or Cloud Enterprise Network | Additional network connectivity configuration is required |

> ⚠️ **Common mistake**: Using a VPC internal address from a public network environment causes connection timeout. You must confirm the client environment before selecting the corresponding address.

### Obtain a Connection Address

**Method 1: Alibaba Cloud console**

📍 Exact path:
1. Console: https://lindorm.console.aliyun.com/
2. Click instance ID "ld-xxx".
3. Left-side menu: **Configuration and Management** → **Database Connection**.
4. View the internal and public connection addresses of each engine.
5. If no public address exists, click **Apply for Public Connection Address**.

> ⚠️ Enabling a public address is not the same as binding an EIP. Lindorm public access is implemented by applying for a public connection address and does not require binding an EIP.

**Method 2: Obtain through API**

```bash
# V1/V2 common: query engine connection endpoints.
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-xxx

# V2 only: query instance details, including ConnectAddressList.
aliyun hitsdb get-lindorm-v2-instance-details --instance-id ld-xxx
```

**`get-lindorm-instance-engine-list`, V1/V2 common**:
Returns `NetInfoList`. Determine the network type by `NetType`:
- `NetType: "0"` → Public address, `-pub`
- `NetType: "2"` → VPC internal address, `-vpc`

**`get-lindorm-v2-instance-details`, V2 only**:
Returns `ConnectAddressList`. Determine the network type by `Type`:
- `Type: INTERNET` → Public address, `-pub`
- `Type: INTRANET` → VPC internal address, `-vpc`

> If neither API response contains a public address, meaning no `NetType: "0"` and no `Type: INTERNET`, public access has not been enabled and must be applied for in the console.

### Enable Public Access

**Prerequisite**: You need to connect to Lindorm from the public network, such as a local computer.

📍 Operation path:
1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, click **Database Connection**.
4. Switch to the target engine tab and click **Enable Public Address** in the upper-right corner.
5. Wait until the address is generated, usually 1 to 3 minutes.
6. In the left-side navigation pane, click **Access Control** → **Whitelist** and add the client public IP address.

> 💡 View your public IP: `curl ifconfig.me`

---

## Quick Diagnostic Commands

Run complete troubleshooting with one set of commands:

```bash
# 1. Check instance status.
aliyun hitsdb get-lindorm-instance --instance-id ld-xxx

# 2. Check whitelist.
aliyun hitsdb get-instance-ip-white-list --instance-id ld-xxx
```

---

## Complete Troubleshooting Checklist

**Basic checks, using APIs**:

| Check Item | Command | Expected Result |
|--------|------|----------|
| **Instance status** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | `InstanceStatus = ACTIVATION` |
| **Whitelist configuration** | `aliyun hitsdb get-instance-ip-white-list --instance-id <id>` | Contains the client IP or VPC CIDR block |
| **Network type** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | `NetworkType = vpc` |
| **VPC match** | `aliyun hitsdb get-lindorm-instance --instance-id <id>` | Client and instance are in the same VPC for internal access |
| **Public address** | View in console or API | Public connection address has been enabled, not EIP |

**Network connectivity tests, advanced troubleshooting**:

| Check Item | Command | Expected Result |
|--------|------|----------|
| **Network reachability** | `ping <host>` | Normal response |
| **Port connectivity** | `telnet <host> <port>` | Connected |
| **DNS resolution** | `nslookup <host>` | Correctly resolves to an IP address |
| **Security group rules** | View in console | Allows access to the corresponding port |

---

## Official Documentation Index for Agent Reference

When handling connection issues, the Agent is **strongly recommended** to query the following official documents for the latest information:

| Document | Link | Purpose |
|------|------|------|
| **Lindorm connection issues and solutions** | [View](https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions) | ⭐ Summary of common connection issues |
| **Lindorm connection errors and solutions** | [View](https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions) | ⭐ Explanation of connection error codes |
| **Use the ping command to check connection** | [View](https://help.aliyun.com/zh/lindorm/support/run-the-ping-command-to-check-the-connection-between-an-ecs-instance-and-a-lindorm-instance) | ⭐ Network reachability test |
| **Use the telnet command to check ports** | [View](https://help.aliyun.com/zh/lindorm/support/run-the-telnet-command-to-check-the-connectivity-of-the-service-ports-of-lindorm) | ⭐ Port connectivity test |
| **Spark connection timeout issue** | [View](https://help.aliyun.com/zh/lindorm/support/cause-analysis-of-connection-timout-problem-in-sparkonmc-access-to) | Spark-specific scenario |

**⭐ Key documents**: The first four documents are the core references for connection troubleshooting. The Agent should query them first when handling connection issues.

---

## Output Format

The connection issue diagnosis report uses a fixed structure:

```text
[Connection Issue Diagnosis Report] Instance ld-uf6l5kr48wqm6rf1h

[Issue Location] Whitelist configuration issue

[Root Cause Analysis]
- Instance status: ✅ ACTIVATION, running
- Whitelist configuration: ❌ Client IP is not in the whitelist
  - Current whitelist: 10.0.0.0/8, 172.16.1.100
  - Client IP: 192.168.1.50
- Network configuration: ✅ VPC configuration is normal
- Network test:
  - ping: ✅ Reachable
  - telnet 30020: ❌ Connection refused, restricted by whitelist

[Solution]
1. Add the client IP to the whitelist:
   
   📍 Exact path:
   1. Console: https://lindorm.console.aliyun.com/
   2. Click instance ID "ld-xxx".
   3. Security Settings → IP Whitelist → Modify.
   4. Add IP: 192.168.1.50 or 192.168.1.0/24

2. Or access from an ECS instance in the same VPC.

📚 Complete troubleshooting guides:
- Connection issue summary: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-issues-and-solutions
- Connection error solutions: https://help.aliyun.com/zh/lindorm/support/lindorm-connection-errors-and-solutions

After applying the preceding solution, retry the connection. If the issue persists, provide the error log.
```

---

## Missing Parameter Handling

### Missing instance-id

**Follow-up strategy**: Run `list_instances` first and let the user select an instance.

---

## Error Handling

| Error | Cause | Guide User |
|------|------|----------|
| **Instance does not exist** | Instance ID is incorrect or the instance has been released | Recommend running `list_instances` first to confirm the instance ID |
| **Insufficient permissions** | AccessKey has no Lindorm permission | Indicate that `AliyunLindormReadOnlyAccess` permission is required |
