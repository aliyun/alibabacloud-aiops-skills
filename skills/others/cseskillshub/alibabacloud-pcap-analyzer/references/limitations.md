# Limitations

Complete list of usage limitations and interpretation caveats for the pcap analyzer.

- The script parses pcap/pcapng files with scapy and tracks TCP sequence numbers via TCP state machine logic to detect retransmissions, out-of-order packets, and duplicate ACKs. Complete TCP streams are required; RTT can only be calculated when the SYN/SYN-ACK handshake is present in the capture.
- For encrypted traffic (TLS), the analysis operates on the TCP layer, not on application-layer data.
- Analysis of large files (over 100 MB) may be slow; narrow the scope first with `--src`, `--dst`, and `--port`.
- When a capture contains multiple sessions, use the filter parameters to specify the IP/port of interest.
- IPsec/IKE analysis is triggered automatically only when the capture contains UDP 500 or UDP 4500 traffic.
- The script supports both IKEv1 and IKEv2. Notify message numbering differs between versions: IKEv1 uses IPsec DOI numbering (e.g. NO-PROPOSAL-CHOSEN = 14) while IKEv2 uses RFC 7296 numbering (e.g. NO_PROPOSAL_CHOSEN = 34); both are covered.
- IKEv2 SA Proposal fields differ from IKEv1: IKEv2 uses Integrity Algorithm / PRF Algorithm / Diffie-Hellman Group, while IKEv1 uses HASH Algorithm / Authentication Method / Group Description.
- SM cryptographic algorithm (SM2/SM3/SM4) detection is based on algorithm-name keyword matching. Both endpoints must support the SM crypto module for negotiation to succeed.
- The MTU/large-packet section is emitted only when a suspicious pattern is detected (ICMP Fragmentation Needed, large-packet ratio below 10%, MSS-vs-retransmission mismatch, fragmentation gap). Normal traffic does not produce this section.
- TCP MSS value + 40 bytes (20-byte IP header + 20-byte TCP header) = interface MTU. Keep this relationship in mind when changing the MTU.
- In VPN/IPsec scenarios, ESP encapsulation adds roughly 50-80 bytes of overhead. It is recommended to lower the interface MTU to 1400 or below on both VPN endpoints.
- DNS anomaly analysis is triggered automatically only when DNS traffic (UDP 53 or TCP 53) is present. Queries and responses are paired by DNS transaction ID.
- TLS handshake analysis is triggered automatically only when TLS traffic is present. It analyzes TLS handshake messages at the TCP layer, not encrypted application data.
- TCP connection establishment failure analysis is based on SYN/SYN-ACK pairing. Non-standard handshakes (e.g. TFO) may produce false positives.
- The ICMP error summary covers Type 3 (Unreachable), Type 5 (Redirect), and Type 11 (Time Exceeded). Other ICMP types are not reported.
- TCP zero-window analysis is implemented by detecting TCP header `window_size = 0`. Zero-window duration is measured as the time span between the first and the last zero-window packet.
- Keepalive detection is based on ACK packets with payload length of 0 or 1 byte; no idle-time heuristic is applied. Some operating systems may not send Keepalive probes at all.
