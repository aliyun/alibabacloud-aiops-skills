# Symptom Error Strings — what the customer's literal wording predicts

## Quotable customer-facing error strings (authoritative tier list)

These strings may be quoted back to the customer verbatim as official
symptom names:

| String | Primary reading | First layers to check |
|---|---|---|
| `Connection timed out` / `timed out` / `err_connection_timed_out` | packets are being DROPPED somewhere (no answer at all) | L4 missing allow / enterprise egress deny -> L5 DROP rules -> L7 path blocking |
| `Connection refused` | an RST answered the SYN immediately: the packet REACHED a host | L6 nothing listening / loopback-only bind -> L5 local REJECT rule; NOT a silent security-group drop |
| `Connection reset` / `connection reset` | an established or half-open flow was RST mid-flight | WHO sent the RST: server logs show the request? TLS completed? spoofed-source RST with odd TTL/TOS -> L7 middlebox / compliance interception; client-side reset recorded in server auth log -> L0 |

## Additional ticket-evidenced customer wordings (real dialogues; not part
of the official quotable list — echo them only as "the message you saw",
never as an official error code)

| Wording | Layer prior | Why |
|---|---|---|
| `No route to host` (often after an intra-VPC telnet) | L5 | a local firewall REJECT answers with ICMP-unreachable; classic firewalld case |
| `read ECONNRESET` / `ERR_CONNECTION_RESET` | L1 / L7 | reset injected before the app sees the request; server logs empty |
| `i/o timeout` from tools/SDKs | L4 egress / L7 | outbound call blocked or path dropping |
| "cannot connect to the remote server" from console-side upload functions | L4 egress | managed flows download via internal service endpoints; enterprise groups deny egress |
| "identity / authentication error" on Remote Desktop once TCP works | L6 / system layer | credential or RDP-service layer, NOT the security group; do not keep re-reporting group findings |
| "Remote Desktop can't connect to the remote computer" | L4 / L7 | test TCP 3389 from a second network to split platform vs path |
| ping works but every TCP port times out | L5 kernel parameters | the tcp_tw_recycle + timestamps pattern under NAT; or a path filtering TCP only |

## Decision discipline

1. Record the EXACT string (ask for the literal text or screenshot); a
   guessed symptom kills the mapping value.
2. A timeout proves DROP only — it never identifies the layer alone; walk
   L4 -> L5 -> L2/L7 with evidence.
3. Refused proves arrival — the walk then goes UPward (listener -> local
   reject), skipping "is the group open" theatrics but still verifying the
   group for completeness.
4. Reset demands direction analysis: server access logs, auth logs,
   connection state at the moment of failure, and (customer-side manual,
   never executed by this skill) both-sides captures saved as .cap files
   with TTL/TOS comparison of the RST vs handshake packets.
5. Multiple strings across clients = scope differential (one carrier fails
   -> L7; all fail -> platform layers; one colleague fails -> L0 egress
   differences).
