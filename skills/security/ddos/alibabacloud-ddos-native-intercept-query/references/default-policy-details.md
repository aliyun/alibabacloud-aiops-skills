# Default Protection Policy Details

> Default protection policies only take effect when the protected asset is **under active attack**. After a protected asset is added to a DDoS Native Protection instance, the protection level defaults to **Normal**.

## 1. Protection Levels (General)

### Loose

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP

> The scrubbing policy is relatively lenient — it only blocks packets with obvious attack signatures. There is a risk that some sophisticated attacks may pass through. It is recommended to enable this level only when false positives are observed.

### Normal

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP
- Performs verification and rate limiting on some anomalous source IPs

> The scrubbing policy is suitable for the vast majority of workloads and effectively mitigates common DDoS attacks.

### Strict

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP
- Performs rigorous verification and rate limiting on some source IPs
- Strictly restricts all UDP packets

> The scrubbing policy is relatively aggressive. In extreme cases there is a risk of false positives. It is recommended to enable this level only when attack traffic is passing through the scrubbing.

## 2. Business Scenario Protection Templates

Customized policies provided for DDoS Protection (Enhanced) EIPs.

### Office Network Policy

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets
- Allows IP protocols such as GRE/IPSec to pass through
- Applies relatively lenient verification on source IPs

> Outbound access restrictions are relatively lenient. Suitable for office network environments.

### TCP Game Policy

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP
- Performs verification and rate limiting on some anomalous source IPs
- Strictly verifies and restricts UDP packets

> Recommended when the workload is primarily TCP-based.

### UDP Game Policy

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP
- Applies relatively lenient verification on UDP packets

> Recommended when the workload is primarily UDP-based.

### General Policy

- Filters malformed packets that violate protocol specifications
- Filters TCP/UDP/ICMP packets with clear attack signatures
- Filters IP fragmented packets and protocols other than TCP/UDP/ICMP

> Suitable for most general-purpose workload scenarios.

### Voice Service Protection Policy

- Supports allowing legitimate SIP fragmented packets while actively detecting and blocking malicious fragment-based attacks

> Suitable for VoIP, multimedia streaming, and similar workloads. Provides finer-grained protection for commonly used SIP protocol packets.

## 3. Name to Console Display Name Mapping

Each policy returned by `ListPolicy --type default` contains a `Name` (policy identifier) and a `Remark` (console display name). When presenting information to users, show only the console display name and do not expose the internal Name field. Rules:

- **Remark is non-empty**: Use `Remark` directly (e.g., `"语音业务防护策略"`)
- **Remark is empty**: Map the Name to a display name per the table below

| Name | Console Display Name |
|---|---|
| `loose` | 宽松 |
| `normal` | 正常 |
| `strict` | 严格 |
| `game_tcp` | 游戏TCP策略 |
| `game_udp` | 游戏UDP策略 |
| `office_network` | 办公策略 |
| `gf_origin_protect_eip_loose` | 通用策略 |
| `gf_origin_protect_eip_office_network` | 办公网策略 |
| `gf_origin_protect_eip_game_tcp` | TCP游戏策略 |
| `gf_origin_protect_eip_game_udp` | UDP游戏策略 |
