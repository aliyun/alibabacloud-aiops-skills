# Report Structure

The analyzer outputs a Markdown report with up to 16 sections. Sections 9 through 15 are dynamic: each appears only when the corresponding analysis detects a suspicious pattern (`suspicious_pattern=True`), and section numbers shift accordingly.

## Fixed Sections (always present)

| # | Section | Content |
|---|---------|---------|
| 1 | Capture Overview | File metadata, packet count, duration, average rate |
| 2 | TCP Session Overview | Frame count / byte count / duration of every TCP connection |
| 3 | Transfer Rate Analysis | Per-second throughput chart, peak / average / minimum values, sudden-drop detection |
| 4 | Window Size Analysis | Client/server window time series, sudden window-drop events, persistent small-window detection |
| 5 | RTT Analysis | RTT statistics (min/max/avg/P50/P95/P99), sudden RTT spike detection, jitter assessment |
| 6 | Retransmission & Reordering Analysis | Retransmission count, burst retransmission detection (more than 5 in 1 second), duplicate ACKs, out-of-order packets |
| 7 | FIN/RST Analysis | Whether the FIN four-way handshake completed normally, whether RST carries payload (middlebox RST injection detection) |
| 8 | Packet Size Distribution | Share of packets in each size bucket, MSS negotiation issue hints |

## Dynamic Sections (on demand)

| Section | Content | Trigger Condition |
|---------|---------|-------------------|
| DNS Anomaly Analysis | Query/response pairing, NXDOMAIN/SERVFAIL/REFUSED error responses, unanswered queries, TCP fallback (Truncated), slow queries (>1 second) | DNS traffic present and a suspicious pattern is detected |
| TLS Handshake Failure Analysis | ClientHello/ServerHello pairing, Alert messages (handshake_failure / protocol_version / certificate_expired / unknown_ca, etc.), outdated SSL/TLS version detection, SNI server name extraction | TLS traffic present and a suspicious pattern is detected |
| TCP Connection Establishment Failure Analysis | SYN/SYN-ACK pairing, establishment failure (SYN with no response), SYN retransmission detection, slow handshake (SYN to SYN-ACK >1 second) | A suspicious pattern is detected |
| ICMP Error Summary Analysis | Destination Unreachable (port/host/network unreachable, administratively prohibited), Time Exceeded, Redirect classification statistics | A suspicious pattern is detected |
| MTU / Large-Packet Blockage Analysis | ICMP Fragmentation Needed detection, TCP MSS negotiation values, large-packet ratio analysis, path MTU limitation diagnosis, remediation advice | A large-packet blockage suspicious pattern is detected |
| TCP Zero Window / Keepalive Analysis | Zero-window event detection and duration calculation, Keepalive probe/ACK counts, application-layer bottleneck diagnosis, TCP buffer tuning advice | A suspicious pattern is detected |
| IPsec/IKE Negotiation Analysis | IKE version auto-detection (IKEv1/IKEv2), SA negotiation state, algorithm suites, notify messages, retry detection, NAT-T detection, SM crypto algorithm identification | IKE traffic on UDP 500/4500 exists in the capture |
| Consolidated Diagnosis Conclusion | Aggregates all anomalies (including DNS / TLS / TCP connection / ICMP / MTU / zero window / IKE) and ranks the main causes of the low rate | Always present as the final section |

> Sections 9-15 use dynamic numbering: a section is emitted only when its analysis detects a suspicious pattern, and the remaining numbers shift forward accordingly.
