# MTR Metrics Detailed Reference

## Introduction to MTR

MTR (My Traceroute) combines traceroute and ping, continuously tracing route paths and displaying packet loss rate and latency for each hop.

## Output Field Descriptions

### Standard Fields

| Field | Description | Normal Range | Abnormality Criteria |
|-------|------------|-------------|---------------------|
| **Hop** | Hop sequence number, indicating the Nth node traversed | 1-30 | >30 may indicate a routing loop |
| **Hostname** | Node hostname or IP address | - | Can be used to identify ISP |
| **Loss%** | Packet loss rate | 0-1% | >5% warrants attention, >20% severe |
| **Sent** | Number of packets sent | >50 | Too few means unreliable data |
| **Last** | Latency of the last packet | Distance-dependent | Sudden large increase warrants attention |
| **Avg** | Average latency | Distance-dependent | Large gap from Best indicates instability |
| **Best** | Best latency | Distance-dependent | - |
| **Wrst** | Worst latency | Should not greatly exceed Avg | Large gap from Avg indicates high jitter |

### Latency Reference Values

#### Domestic Links (Same ISP)

| Distance | Normal Latency | Acceptable Latency | High Latency |
|----------|---------------|-------------------|-------------|
| Same province | < 20ms | 20-50ms | > 50ms |
| Cross-province | 20-50ms | 50-100ms | > 100ms |
| Cross-border (HK/Macau/TW) | 30-80ms | 80-150ms | > 150ms |

#### International Links

| Region | Normal Latency | Acceptable Latency | High Latency |
|--------|---------------|-------------------|-------------|
| East Asia (Japan/Korea) | 50-100ms | 100-200ms | > 200ms |
| Southeast Asia | 80-150ms | 150-250ms | > 250ms |
| Europe | 150-250ms | 250-350ms | > 350ms |
| US West | 150-200ms | 200-300ms | > 300ms |
| US East | 200-280ms | 280-400ms | > 400ms |

## Packet Loss Type Analysis

### Real Packet Loss vs ICMP Rate Limiting

**Real packet loss characteristics:**
- Persistent high packet loss starting from a certain hop
- All subsequent hops show similar loss rates
- Actual business is affected

**ICMP rate limiting characteristics:**
- Only a single intermediate hop shows packet loss
- Subsequent hops recover to normal loss rates
- Actual business may be unaffected
- Commonly seen at ISP core routers

### Packet Loss Severity Levels

| Loss Rate | Level | Impact | Recommendation |
|-----------|-------|--------|---------------|
| 0% | Excellent | None | No action needed |
| 0-1% | Good | Nearly imperceptible | Monitor |
| 1-5% | Fair | Slight impact | Investigate |
| 5-10% | Poor | Noticeable impact | Action required |
| 10-20% | Severe | Serious impact | Urgent action required |
| >20% | Critical | Nearly unusable | Immediate action required |

## Common Problem Patterns

### Pattern 1: Local Network Issue

**Characteristics:**
- High packet loss starting from hop 1-2
- All subsequent hops show high loss

**Possible causes:**
- Weak WiFi signal
- Cable/interface failure
- Local router overloaded
- Bandwidth exhausted

**Troubleshooting suggestions:**
1. Check local network connection
2. Restart router
3. Try wired connection
4. Check bandwidth usage

### Pattern 2: ISP Access Issue

**Characteristics:**
- High packet loss starting from hop 2-4 (after leaving local network)
- Subsequent hops show persistent high loss

**Possible causes:**
- ISP access layer congestion
- ISP equipment failure
- Regional network outage

**Troubleshooting suggestions:**
1. Contact ISP customer service
2. Inquire about regional outages
3. Try changing DNS
4. Consider backup network

### Pattern 3: Backbone Issue

**Characteristics:**
- High packet loss at an intermediate hop (typically provincial or national backbone)
- Sudden significant latency increase

**Possible causes:**
- Backbone congestion
- International gateway congestion
- Cross-ISP interconnection issues

**Troubleshooting suggestions:**
1. Wait for ISP repair
2. Try using proxy/VPN to bypass
3. Report to ISP

### Pattern 4: Destination Issue

**Characteristics:**
- Only the last hop or last few hops show high loss
- All preceding hops are normal

**Possible causes:**
- Target server under high load
- Target network ingress congestion
- Target server firewall restrictions

**Troubleshooting suggestions:**
1. Contact target service provider
2. Try accessing other IPs in the same subnet
3. Wait for target side to resolve

### Pattern 5: Route Detour

**Characteristics:**
- Sudden large latency increase at a certain hop (>50ms)
- Subsequent hops maintain high latency

**Possible causes:**
- Normal route disrupted, using backup route
- ISP routing policy adjustment
- International link detour

**Troubleshooting suggestions:**
1. Compare with historical MTR results
2. Confirm whether it is a temporary detour
3. Contact ISP for routing information

## ISP Identification

### China Telecom

**Common IP ranges:**
- 202.96.x.x - 202.97.x.x (backbone/international gateway)
- 116.x.x.x, 118.x.x.x, 124.x.x.x

> Note: `219.158.x.x` belongs to **China Unicom** backbone, NOT China Telecom.

**Typical hostnames:**
- *.chinanet.cn
- *.telecom.cn

### China Unicom

**Common IP ranges:**
- 219.158.x.x (backbone/international gateway)
- 221.4.x.x, 125.33.x.x
- 119.x.x.x, 123.x.x.x

**Typical hostnames:**
- *.chinaunicom.cn
- *.cnc.cn
- *.uni-cdn.net

### China Mobile

**Common IP ranges:**
- 221.183.x.x, 223.120.x.x
- 111.13.x.x, 117.x.x.x
- 120.x.x.x, 223.x.x.x

**Typical hostnames:**
- *.chinamobile.com
- *.cmcc.cn
- *.mobile.cn

### International ISPs

**Common international nodes:**
- Telia: *.telia.net
- Level3: *.level3.net
- NTT: *.ntt.net
- PCCW: *.pccwglobal.net
- Hurricane Electric: *.he.net

## Analysis Tips

### 1. Comparative Analysis

**Horizontal comparison:**
- Same target, different time periods
- Same target, different network environments
- Different targets, same network environment

**Vertical comparison:**
- Compare with historical normal periods
- Compare with other users on the same path

### 2. Packet Capture Verification

When MTR results don't match actual business performance:
- Use tcpdump for packet capture analysis
- Compare ICMP and actual business protocol performance
- Check for QoS policy impact

### 3. Multi-Tool Verification

- Use standard ping for verification
- Use tcptraceroute for TCP-layer tracing
- Test from different ISP networks

## Report Template

```markdown
## MTR Diagnostic Report

### Test Information
- Test time: YYYY-MM-DD HH:MM
- Test target: xxx.xxx.xxx.xxx
- Test network: ISP + bandwidth

### Problem Description
User report: xxx

### MTR Results Summary
- Total hops: X hops
- Maximum packet loss: X% (hop X)
- Final destination latency: X ms

### Problem Location
Issue appears at hop X (IP/Hostname), classified as:
- [ ] Local network
- [ ] ISP access layer
- [ ] Backbone
- [ ] Destination

### Root Cause Analysis
xxx

### Recommended Actions
1. xxx
2. xxx
3. xxx

### Tracking Status
- [ ] ISP contacted
- [ ] Awaiting ISP response
- [ ] Issue resolved
```

## Linux/ECS Server MTR Usage Guide

### Installation

```bash
# CentOS / RHEL / Alibaba Cloud Linux
yum install -y mtr

# Ubuntu / Debian
apt-get update && apt-get install -y mtr
```

### Basic Usage

```bash
# Report mode (non-interactive, script-friendly)
mtr -r -c 100 -n <target_IP_or_domain>

# Parameter descriptions:
#   -r    Report mode, outputs results after completion
#   -c N  Send N probe packets (default 10, recommend 100+ for stable data)
#   -n    Skip DNS reverse lookup (faster, more stable output)

# Interactive mode (real-time refresh)
mtr <target_IP_or_domain>
```

### Output Example

```
Start: 2025-01-01T10:00:00+0800
HOST: ecs-test                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 172.16.0.1             0.0%   100    0.3   0.4   0.2   1.2   0.1
  2.|-- 10.54.0.1              0.0%   100    1.2   1.5   0.8   3.2   0.5
  3.|-- 202.97.33.1            0.0%   100    5.3   6.1   4.9   12.5  1.2
  4.|-- 8.8.8.8                0.0%   100   28.5  29.1  27.2  35.1  1.8
```

## TCP MTR Usage Guide

### Use Cases

- Target ICMP is blocked or rate-limited by firewall/security group, making ICMP MTR unreliable
- Need to test link quality for a specific TCP port (e.g., 80/443)
- Troubleshooting port-level blocking issues

### Usage

```bash
# TCP MTR (specify port)
mtr --tcp -P 80 -r -c 100 <target_IP>
mtr --tcp -P 443 -r -c 100 <target_IP>

# UDP MTR
mtr --udp -r -c 100 <target_IP>

# Parameter descriptions:
#   --tcp     Use TCP SYN probes instead of ICMP
#   -P <port> Specify TCP port number
#   --udp     Use UDP probes instead of ICMP
```

### TCP MTR Interpretation Differences

- TCP MTR sends TCP SYN packets instead of ICMP Echo; some intermediate routers don't reply with TCP RST, which may show as `???`
- The final destination node result is most valuable — it determines whether the target port is reachable
- 100% loss (`???`) at intermediate nodes does NOT mean the link is broken; it only means that node doesn't reply with TCP RST

### Comparison Analysis

| Scenario | ICMP MTR | TCP MTR | Conclusion |
|----------|----------|---------|-----------|
| High ICMP loss, normal TCP | High loss | Normal | ICMP filtered, business is normal |
| Normal ICMP, high TCP loss | Normal | High loss | TCP port blocked |
| Both show high loss | High loss | High loss | Real link issue |
| Both normal | Normal | Normal | Link is healthy |

## Bidirectional MTR Testing Guide

### Why Bidirectional Testing Is Needed

Forward and reverse network paths may take completely different routes (asymmetric routing), therefore:

- **Forward packet loss may be a reverse link issue**: Packet loss shown in MTR may be from lost reverse response packets, not lost forward probe packets
- **Different ISPs**: Forward may go through China Telecom, reverse may go through China Unicom
- **Problem location**: Unidirectional testing cannot distinguish between "outbound" and "return" issues

### Bidirectional Testing Methods

1. **Forward test** (Client -> Server): Run `mtr -r -c 100 -n <server_IP>` on the client
2. **Reverse test** (Server -> Client): Run `mtr -r -c 100 -n <client_IP>` on the server

If the server is an Alibaba Cloud ECS, you can use this Skill's Cloud Assistant automated mode to remotely execute reverse MTR.

### Asymmetric Routing Pattern

```
Forward (A -> B): A -> Telecom Access -> Telecom Backbone -> Alibaba Cloud -> B
Reverse (B -> A): B -> Alibaba Cloud -> Unicom Backbone -> Unicom Access -> A
```

In this scenario:
- Forward MTR showing packet loss may actually be caused by **reverse** Unicom backbone return-path packet loss causing response loss
- Bidirectional MTR is needed for accurate problem location

### Bidirectional Comparison Analysis Key Points

| Observation | Conclusion | Recommendation |
|------------|-----------|---------------|
| Forward loss, reverse normal | Outbound link issue | Investigate abnormal nodes on the forward path |
| Forward normal, reverse loss | Return link issue | Investigate abnormal nodes on the reverse path |
| Both show loss, different nodes | Both directions have issues | Investigate both directions separately |
| Both show loss, same node | Overall node failure | Contact the corresponding ISP |
| Forward/reverse paths use different ISPs | Asymmetric routing | Normal phenomenon, but increases troubleshooting difficulty |
