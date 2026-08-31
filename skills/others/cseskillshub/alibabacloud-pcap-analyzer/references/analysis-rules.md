# Analysis Rules

Detection rules and thresholds used by `scripts/pcap_analyze.py`. Each rule set maps to a report section; see [report-structure.md](report-structure.md) for the section layout.

## Low Transfer Rate

The script investigates the cause of low throughput in the following priority order:

1. **TCP window bottleneck** - client/server window persistently below 10 KB indicates the application layer cannot read data fast enough.
2. **High RTT** - average RTT above 100 ms limits the bandwidth-delay product (BDP) and lowers window utilization.
3. **Frequent retransmissions** - more than 10 retransmissions reduces effective throughput.
4. **Throughput sudden drop** - per-second throughput drops more than 50% compared with the previous second.

## Abnormal FIN/RST

- **FIN count != 2** - possibly one-sided close or an incomplete capture.
- **RST carrying payload** - a typical signature of RST injection/forgery by a middlebox (firewall/IPS).
- **RST after FIN** - normal cleanup of a half-closed state.

## Retransmission Bursts

- **More than 5 retransmissions within 1 second** - classified as a retransmission burst, usually caused by link packet loss or congestion.
- **More than 3 duplicate ACKs** - may trigger fast retransmission.

## Window Anomalies

- **Window drop greater than 50%** - application-layer processing delay or buffer configuration change.
- **Persistently small window (<10 KB for over 2 seconds)** - TCP flow control is in effect and limits the sending rate.

## RTT Analysis

- RTT statistics: min / max / average / P50 / P95 / P99.
- Sudden RTT spikes are detected and reported.
- RTT requires a complete TCP stream (SYN/SYN-ACK present) to be calculated accurately.

## MTU / Large-Packet Blockage

The script detects MTU/large-packet problems with four patterns:

1. **ICMP Fragmentation Needed** - a router on the path sends an ICMP Type 3 Code 4 message, indicating a packet exceeds the path MTU; the message carries the next-hop MTU value.
2. **Very low large-packet ratio** - large packets (>1400 bytes) make up less than 10% of traffic, meaning large packets are dropped somewhere on the path while small packets pass.
3. **TCP MSS vs. retransmission mismatch** - MSS is negotiated to a large value but large packets are still retransmitted, meaning the actual path MTU is smaller than the MSS.
4. **Fragmentation gap** - packets larger than 1500 bytes exist but no 1400-1500 byte packets exist, suggesting abnormal IP fragmentation.

Remediation advice includes: changing the interface MTU on Linux (`ip link set dev <iface> mtu`) or Windows (`netsh interface ipv4 set subinterface`), changing the TCP MSS via Linux iptables TCPMSS or the Windows registry, and the encapsulation overhead explanation for VPN/IPsec scenarios (ESP header + IV + padding + authentication add roughly 50-80 bytes).

## DNS Anomalies

The script pairs DNS queries and responses by DNS transaction ID and detects:

1. **NXDOMAIN / SERVFAIL / REFUSED** - domain does not exist, server failure, or query refused; check the domain configuration or the DNS server state.
2. **Query with no response** - a query was sent but no response arrived; the DNS server may be unreachable.
3. **TCP fallback** - the DNS response was truncated (TC flag), forcing the client to retry over TCP port 53, which may increase resolution latency.
4. **Slow query** - response time exceeds 1 second, which may delay connection establishment.

## TLS Handshake Failure

The script extracts TLS ClientHello / ServerHello / Alert messages and detects:

1. **Incomplete handshake** - ClientHello received no ServerHello; the server may be unreachable or may not support TLS.
2. **Alert messages** - Alert types are decoded, e.g. handshake_failure (40), protocol_version (70), certificate_expired (45), unknown_ca (48), bad_certificate (42).
3. **Outdated protocol version** - SSL 2.0/3.0 or TLS 1.0/1.1 detected; upgrade to TLS 1.2 or later is recommended.
4. **SNI extraction** - the server_name extension is extracted from ClientHello to identify the target domain.

## TCP Connection Establishment Failure

The script pairs SYN and SYN-ACK by connection tuple (src/sport/dst/dport) and detects:

1. **Connection establishment failure** - SYN sent but no SYN-ACK received; the target port is unreachable or blocked by a firewall.
2. **SYN retransmission** - multiple SYNs for the same connection; the first attempt timed out and was retried.
3. **Slow handshake** - SYN-to-SYN-ACK delay exceeds 1 second, possibly caused by network congestion or middlebox delay.

## ICMP Error Summary

All ICMP messages are extracted and classified by Type/Code:

1. **Destination Unreachable (Type 3)** - port unreachable (Code 3), host unreachable (Code 1), network unreachable (Code 0), administratively prohibited (Code 13).
2. **Time Exceeded (Type 11)** - TTL expired; a routing loop may exist.
3. **Redirect (Type 5)** - route redirect; possible middlebox intervention.

## TCP Zero Window / Keepalive

The script detects TCP zero-window events and Keepalive behavior:

1. **Zero window** - the receiver advertises a window of 0 and the sender pauses; persistent zero window indicates insufficient application-layer consumption speed.
2. **Zero-window duration** - the time span between the first and the last zero-window packet; a longer span means a more severe application-layer bottleneck.
3. **Keepalive probes** - counts Keepalive probe and ACK packets; normal keepalive behavior on long-idle connections.
4. **Remediation advice** - Linux: enlarge buffers with `sysctl -w net.core.rmem_max=16777216` and set `SO_RCVBUF` in the application; Windows: adjust window scaling via the `Tcp1323Params` registry key.

## IPsec/IKE Negotiation

- **NO-PROPOSAL-CHOSEN** - the responder supports none of the algorithm combinations proposed by the initiator; check that the SA Proposal configurations on both ends match (IKEv1 notify number = 14, IKEv2 notify number = 34).
- **TS-UNACCEPTABLE** (IKEv2) - the Traffic Selector is unacceptable; check the IP address/port range configuration on both ends.
- **AUTHENTICATION_FAILED** (IKEv2) - authentication failed; the pre-shared key or certificate does not match.
- **IKE version mismatch** - the two ends use different IKE versions, which may cause negotiation failure.
- **Retry pattern** - the initiator keeps retrying (typically every 5-10 seconds), indicating the peer consistently rejects; inspect the algorithm configuration.
- **SM cryptographic algorithms** - when SM2/SM3/SM4 is detected, confirm that both endpoints support the SM crypto module (detection works for both IKEv1 and IKEv2).
- **NAT-Traversal** - NAT-T support detection: IKEv1 via Vendor ID and UDP 4500; IKEv2 via NAT-DETECTION-SOURCE-IP / NAT-DETECTION-DESTINATION-IP notify payloads.
- IKEv2 SA Proposal fields differ from IKEv1: IKEv2 uses Integrity Algorithm / PRF Algorithm / Diffie-Hellman Group, while IKEv1 uses HASH Algorithm / Authentication Method / Group Description.
- Notify message numbering is version-specific: IKEv1 uses IPsec DOI numbering (e.g. NO-PROPOSAL-CHOSEN = 14), IKEv2 uses RFC 7296 numbering (e.g. NO_PROPOSAL_CHOSEN = 34); both are covered.
