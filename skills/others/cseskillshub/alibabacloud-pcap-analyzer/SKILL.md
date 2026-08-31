---
name: alibabacloud-pcap-analyzer
description: |
  Analyze local pcap/pcapng captures to diagnose network transfer problems.
  Use when given a pcap file to explain slow network transfer, connection
  issues, abrupt TCP session termination, security association setup error,
  private network tunnel establishment problem, DNS, TLS or encrypted
  session establishment error, MTU or oversized packet drop, or receiver
  buffer exhaustion. Read-only; no credentials required.
  Triggers: "pcap analysis", "packet capture analysis", "analyze pcap file",
  "slow network transfer", "TCP retransmission", "connection reset",
  "IPsec/IKE negotiation failed", "VPN negotiation failure",
  "TLS handshake failed", "DNS resolution failure", "MTU issue",
  "zero window", "abrupt TCP session termination",
  "domain name lookup error", "encrypted session establishment error",
  "oversized packet drop".
---

# PCAP Analysis

Analyze local Wireshark pcap/pcapng packet capture files and produce a structured Markdown diagnosis report. The analyzer covers TCP transfer performance (throughput, window, RTT, retransmission), connection anomalies (FIN/RST, failed handshakes), IPsec/IKE VPN negotiation, MTU/large-packet issues, DNS resolution, TLS handshake, ICMP errors, and TCP zero-window/Keepalive behavior. Suspicious patterns are reported in dedicated dynamic sections, and the report ends with a consolidated conclusion ranking the likely root causes.

Requires Python 3 and the scapy library:

```bash
pip3 install scapy
```

## Module Index

| Module | Purpose | File |
|--------|---------|------|
| Analysis Rules | Diagnosis decision rules and thresholds (rate, FIN/RST, retransmission, window, RTT, MTU modes, DNS, TLS, TCP setup, ICMP, zero window, IKE) | [references/analysis-rules.md](references/analysis-rules.md) |
| Report Structure | The 16-section report layout and the trigger conditions of the dynamic sections | [references/report-structure.md](references/report-structure.md) |
| Limitations | Usage limitations and full notes for interpreting results | [references/limitations.md](references/limitations.md) |

> Load references on demand. Do not read all reference files unless the task requires them.

## User Confirmation

- Before running any analysis, confirm the pcap file path with the user.
- If the user has not provided a pcap file, ask for the file path first. Never guess, derive, or scan for pcap files on your own.

## Execution Principle

MANDATORY:

- **Read-only**: this skill only reads and analyzes. It MUST NOT modify, move, or delete any user file, and it requires no credentials of any kind.
- **Single entry point**: all analysis MUST be executed through the entry script `scripts/pcap_analyze.py`. Do not hand-assemble diagnostic command chains.
- **User-provided files only**: only analyze pcap files the user explicitly specifies. Never open or analyze files the user did not point to.
- **No scanning**: never search for or open pcap files beyond the one the user provided.

## Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| C1 | Transfer Rate Diagnosis | Per-second throughput statistics, peak/average/minimum, sudden-drop detection, and root-cause ranking |
| C2 | TCP Performance Analysis | Window shrinkage/zero-window, RTT statistics and spikes, retransmission bursts, out-of-order and duplicate ACK detection |
| C3 | Connection Anomaly Detection | Abnormal FIN/RST terminations, RST-with-payload (middlebox injection) detection, failed TCP handshakes |
| C4 | IPsec/IKE Negotiation Analysis | IKEv1/IKEv2 auto-detection, SA proposal suites, notify messages, retry patterns, NAT-T detection |
| C5 | MTU / Large-Packet Analysis | ICMP Fragmentation Needed, large-packet ratio, MSS vs. retransmission mismatch, remediation advice |
| C6 | DNS Anomaly Analysis | NXDOMAIN/SERVFAIL/REFUSED, unanswered queries, TCP fallback, slow queries |
| C7 | TLS Handshake Analysis | ClientHello/ServerHello pairing, Alert messages, outdated protocol versions, SNI extraction |
| C8 | ICMP Error Summary | Destination Unreachable / Time Exceeded / Redirect classification |
| C9 | Filtered Analysis | Focus on a specific flow with `--src`, `--dst`, `--port` |
| C10 | Markdown Report Output | Write the full report to a file with `--output` |

Detection rules and thresholds behind each capability are documented in [references/analysis-rules.md](references/analysis-rules.md).

## Commands

Set the skill directory once, then run the entry script:

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-pcap-analyzer
```

### Analyze a whole capture file

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py capture.pcap
```

### Filter by source/destination IP and port

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py capture.pcap --src 10.0.0.1 --dst 10.0.0.2 --port 443
```

### Write the report to a Markdown file

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py capture.pcap --output report.md
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `pcap` | Path to the pcap/pcapng file (required) |
| `--src <IP>` | Filter by source IP |
| `--dst <IP>` | Filter by destination IP |
| `--port <PORT>` | Filter by TCP port |
| `--output <FILE>` | Output Markdown file path (defaults to stdout when omitted) |

Exit code contract: `0` = analysis succeeded; `1` = input/file error (missing path, not a regular file, or not readable); `2` = missing dependency (scapy not installed).

## Report Overview

The analyzer outputs a Markdown report with up to 16 sections. The first eight sections are always present and cover the capture basics: file metadata, TCP session overview, transfer rate, window size, RTT, retransmission/reordering, FIN/RST behavior, and packet size distribution.

Sections 9 through 15 are dynamic and appear only when the corresponding analysis detects a suspicious pattern: DNS anomalies, TLS handshake failures, TCP connection establishment failures, ICMP error summary, MTU/large-packet issues, TCP zero-window/Keepalive events, and IPsec/IKE negotiation (the IKE section appears when UDP 500/4500 traffic is present). The final section is a consolidated diagnosis conclusion that aggregates all detected anomalies and ranks the likely causes of the observed problem. See [references/report-structure.md](references/report-structure.md) for the full section list and trigger conditions, and [references/analysis-rules.md](references/analysis-rules.md) for the detection rules behind each section.

## Examples

**Example 1**: User: "File transfer between these two servers is very slow, here is the capture: /tmp/transfer.pcap"

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py /tmp/transfer.pcap --src 10.0.0.1 --dst 10.0.0.2 --output slow_transfer.md
```

**Example 2**: User: "Our site-to-site VPN keeps failing to establish, analyze this capture."

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py vpn_ike.pcap --output ike_report.md
```

**Example 3**: User: "DNS lookups fail intermittently, I captured the traffic."

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py dns_issue.pcap --port 53 --output dns_report.md
```

**Example 4**: User: "Large packets do not go through over the VPN, small ones work fine."

```bash
cd $SKILL_DIR && python3 scripts/pcap_analyze.py mtu_issue.pcap --output mtu_report.md
```

## Important Notes

- The analysis relies on complete TCP streams. RTT calculation and accurate retransmission/out-of-order detection require captures that include the SYN/SYN-ACK handshake.
- For encrypted traffic (TLS), the analysis works at the TCP/TLS-handshake layer, not at the application layer; encrypted payloads cannot be inspected.
- Large captures (over 100 MB) may take a long time to analyze. Narrow the scope first with `--src`, `--dst`, or `--port`.
- When a capture contains multiple sessions, use the filter parameters to focus on the IP/port the user cares about.
- The IPsec/IKE section is generated only when the capture contains IKE traffic on UDP 500 or UDP 4500. Both IKEv1 and IKEv2 are supported.
- The DNS section is generated only when DNS traffic (UDP/TCP 53) is present; the TLS section only when TLS traffic is present.
- The MTU/large-packet section appears only when a suspicious pattern is detected (e.g. ICMP Fragmentation Needed, very low large-packet ratio). Normal traffic does not produce this section.
- For VPN/IPsec deployments, encapsulation adds roughly 50-80 bytes of overhead; consider lowering the interface MTU to 1400 or below on both VPN endpoints.
- See [references/limitations.md](references/limitations.md) for the complete list of limitations and interpretation caveats.
