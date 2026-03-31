# GA Acceleration Performance Verification Guide

> Reference: [Use the network dial test tool to test the acceleration](https://help.aliyun.com/zh/ga/use-cases/use-the-network-dial-test-tool-to-test-the-acceleration)

---

## Prerequisites

- GA instance is deployed and configured (listener + endpoint group)
- Listener ports have been added to the origin server's security group whitelist
- UDP testing requires additional preparation (see UDP section below)

---

## Important: ICMP Ping / TCPing Cannot Be Used to Test Acceleration Performance

GA supports response termination -- ICMP Ping and TCPing requests are responded to directly in the acceleration region and **do not reflect the actual end-to-end acceleration performance**.

- Ping / TCPing **can only be used for connectivity testing**
- **Cannot be used for latency measurement or acceleration performance evaluation**
- Use curl or UDP dial test tools for acceleration performance verification

---

## Important: Do Not Speculate on Acceleration Results

> **It is strictly forbidden to provide any speculative acceleration performance conclusions.** All test results and performance evaluations presented to the user must be based on actual test data.
> Do not provide speculative conclusions such as "latency reduced by approximately XX%" or "significant acceleration improvement" based on experience, theoretical analysis, or expectations.
> You must first execute actual tests, then present results to the user based on the test data.

---

## Method 1: Online Dial Test Tool (Recommended)

Alibaba Cloud CloudMonitor provides an online network dial test tool that supports multi-region, multi-ISP probe points.

### Domain Acceleration Testing

```
1. Open the Alibaba Cloud network dial test tool page
2. Enter the service domain (CNAME'd to GA)
3. Click "Start Detection"
4. Filter by "acceleration region" to view latency data from each probe point
5. Compare pre- and post-GA deployment results to evaluate acceleration performance
```

### IP Acceleration Testing

```
1. Select "Comparison Detection" mode
2. Enter the "origin server IP" (as the non-accelerated baseline)
3. Enter the "accelerated IP address" (assigned by GA)
4. Filter by target region and compare the two result sets
```

---

## Method 2: Manual curl Testing (HTTP/HTTPS/TCP)

Execute the following commands on a client machine in the acceleration region to compare latency data before and after acceleration.

### HTTP Testing

Output metrics: TCP connection time, time to first byte, total time

```bash
# Non-accelerated (direct access to origin server)
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "http://<origin-server-IP-or-domain>:<port>"

# Accelerated (access through GA)
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "http://<GA-accelerated-IP-or-domain>:<port>"
```

### HTTPS Testing

Output metrics: TCP connection time, SSL handshake time, time to first byte, total time

```bash
# Non-accelerated (direct access to origin server)
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_appconnect: %{time_appconnect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "https://<origin-server-domain>"

# Accelerated (access through GA)
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_appconnect: %{time_appconnect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "https://<GA-accelerated-domain>"
```

### TCP Testing (Non-HTTP Scenarios)

Output metrics: TCP connection time, time to first byte, total time

```bash
# Non-accelerated
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "telnet://<origin-server-IP>:<port>"

# Accelerated
curl -o /dev/null -s --max-time 60 -w "time_connect: %{time_connect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total: %{time_total}s\n" \
  "telnet://<GA-accelerated-IP>:<port>"
```

### Metric Descriptions

| Metric | Description | Applicable Protocols |
|------|------|----------|
| `time_connect` | TCP connection time -- time to complete the TCP three-way handshake | HTTP / HTTPS / TCP |
| `time_appconnect` | SSL handshake time -- time to complete SSL/TLS negotiation | HTTPS |
| `time_starttransfer` | Time to first byte (TTFB) -- time from sending the request to receiving the first response byte | HTTP / HTTPS / TCP |
| `time_total` | Total time -- total time from sending the request to completing the response session | HTTP / HTTPS / TCP |

> **Additional metric**: When testing via domain, you can append `time_namelookup: %{time_namelookup}s` to the output to get the DNS resolution time, which helps isolate the DNS impact on latency.

### Result Analysis

Compare the **non-accelerated** and **accelerated** data sets:

- `time_connect` decreases -> TCP connection latency reduced (accelerated path optimization)
- `time_appconnect` decreases -> SSL handshake latency reduced (HTTPS scenarios)
- `time_starttransfer` decreases -> Time to first byte reduced (end-to-end acceleration effect)
- `time_total` decreases -> Overall request time reduced

---

## Method 3: UDP Dial Test

> **Prerequisite**: Before executing UDP tests, confirm with the user that a UDP Echo Server is running on the endpoint server (e.g., started with `socat -v UDP-LISTEN:<port>,fork PIPE`). If not deployed, remind the user to deploy it on the server first before testing.

### Client Preparation

Use the built-in udping tool (located at `scripts/udping.py`) on a client machine in the acceleration region:

```bash
# The script is included in the skill directory scripts/udping.py; copy it to the client machine for use
python udping.py [-c COUNT] [-l LENGTH] [-i INTERVAL] <target-IP> <target-port>

# Parameters:
#   -c COUNT      Number of packets to send (default 0 = unlimited, Ctrl+C to stop)
#   -l LENGTH     Payload length in bytes (default 64)
#   -i INTERVAL   Packet sending interval in ms (default 1000)
```

### Test Commands

```bash
# Non-accelerated (direct access to origin server, send 10 packets)
python udping.py -c 10 <origin-server-IP> <listener-port>

# Accelerated (access through GA accelerated IP, send 10 packets)
python udping.py -c 10 <GA-accelerated-IP> <listener-port>
```

### Output Metrics

| Metric | Description |
|------|------|
| `time` (per-packet RTT) | Round-trip time per packet (ms) |
| `packets transmitted / received` | Packets sent / received |
| `packet loss` | Packet loss rate (%) |
| `rtt min/avg/max` | Minimum / average / maximum RTT (ms) |

### Result Analysis

Compare the **non-accelerated** and **accelerated** data sets:

- `avg RTT` decreases -> UDP end-to-end latency reduced (accelerated path optimization)
- `packet loss` decreases -> Packet loss rate reduced (improved path quality)

> UDP is a connectionless protocol; packets are forwarded directly to the endpoint, so UDP dial tests can accurately reflect the acceleration performance.

---

## Testing Recommendations

1. **Run multiple tests and take the average** -- Single tests may be affected by network jitter; it is recommended to run at least 10-20 tests and take the average
2. **Test from multiple regions** -- Test from different acceleration regions to understand the acceleration performance in each region
3. **Test at different times** -- Acceleration performance may vary between peak and off-peak hours
4. **Use actual business scenarios** -- The examples provided here are for reference only; actual acceleration performance should be verified with real business workloads

---

## Related Links

- [Official Documentation - Use the network dial test tool to test the acceleration](https://help.aliyun.com/zh/ga/use-cases/use-the-network-dial-test-tool-to-test-the-acceleration)
