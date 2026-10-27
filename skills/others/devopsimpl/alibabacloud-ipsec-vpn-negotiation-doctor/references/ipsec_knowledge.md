# IPSec VPN Negotiation Quick Reference

## 1. IKEv1 State Machine

### 1.1 Phase 1 - Main Mode (6 packets)

```
Initiator                              Responder
    |                                      |
    |--- (1) SA Proposal --->              |  Algorithm proposal
    |<-- (2) SA Accepted  ---              |  Algorithm confirmed
    |                                      |
    |--- (3) DH + Nonce  --->              |  Key exchange
    |<-- (4) DH + Nonce  ---               |  Key exchange
    |                                      |
    |--- (5) ID + HASH   ===>              |  Identity auth (encrypted)
    |<== (6) ID + HASH   ===               |  Identity auth (encrypted)
    |                                      |
    [=========== IKE SA Established ===========]
```

**Key log keywords:** `phase1`, `initiator`, `responder`, `phase1 completed`

**Status determination:**
- Stuck at 1st/2nd packet: Algorithm mismatch (encryption/auth/DH group)
- Stuck at 3rd/4th packet: DH exchange failure (network issue or middlebox)
- Stuck at 5th/6th packet: Identity auth failure (PSK mismatch or ID mismatch)

### 1.2 Phase 1 - Aggressive Mode (3 packets)

```
Initiator                              Responder
    |                                      |
    |--- SA + DH + Nonce + ID --->         |
    |<-- SA + DH + Nonce + ID + HASH ---   |
    |--- HASH --->                         |
    |                                      |
    [=========== IKE SA Established ===========]
```

### 1.3 Phase 2 - Quick Mode (3 packets)

```
Initiator                              Responder
    |                                      |
    |=== (1) HASH + SA + Nonce + [ID] ===> |  IPSec SA proposal
    |<=== (2) HASH + SA + Nonce + [ID] === |  IPSec SA confirmed
    |=== (3) HASH ===>                     |  Finalized
    |                                      |
    [========== IPSec SA Established ==========]
```

**Key log keywords:** `phase2`, `quick mode`, `phase2 completed`

**Status determination:**
- Stuck at packet 1: Phase2 param mismatch (encryption/auth/PFS/traffic selectors)
- Stuck at packet 2: Responder rejected the proposal

---

## 2. IKEv2 State Machine

### 2.1 Initial Exchange (4 packets)

```
Initiator                              Responder
    |                                      |
    |--- IKE_SA_INIT (SAi1,KEi,Ni) --->    |  Packet 1: plaintext
    |<-- IKE_SA_INIT (SAr1,KEr,Nr) ---     |  Packet 2: plaintext
    |                                      |
    [---- Both sides generate SKEYSEED ----]
    |                                      |
    |=== IKE_AUTH (IDi,AUTH,SAi2,TSi,TSr) =>|  Packet 3: encrypted
    |<== IKE_AUTH (IDr,AUTH,SAr2,TSi,TSr) ==|  Packet 4: encrypted
    |                                      |
    [=== IKE SA + First IPSec SA Pair Established ===]
```

**Key log keywords:** `IKE_SA_INIT`, `IKE_AUTH`, `CREATE_CHILD_SA`, `INFORMATION_EXCHANGE`

**State transitions:**
```
INI_IKE_SA_INIT_SENT  -> IKE_SA_INIT sent, waiting for response
INI_IKE_AUTH_SENT     -> IKE_AUTH sent, waiting for response
ESTABLISHED           -> Negotiation successful
```

**Status determination:**
- Stuck at `INI_IKE_SA_INIT_SENT`: Phase1 failed (algorithm/DH mismatch or peer not responding)
- Stuck at `INI_IKE_AUTH_SENT`: Phase2 failed (PSK/ID mismatch or traffic selector mismatch)
- `ESTABLISHED` -> other state: Tunnel interrupted

### 2.2 CREATE_CHILD_SA Exchange

Used for: multiple IPSec SA pairs, IKE SA rekey, IPSec SA rekey.

### 2.3 INFORMATIONAL Exchange

Used for: DPD probing, SA delete notifications, error notifications.

---

## 3. Common Tunnel Interruption Causes

### 3.1 DPD Timeout

**Mechanism:** DPD R-U-THERE probes sent periodically. N consecutive non-responses -> peer declared dead -> SA deleted -> re-negotiation.

**Key log keywords:** `sending DPD request`, `received DPD response`, `remote seems to be dead`, `retransmission limit reached`

**Common causes:** Peer failure/restart, network packet loss, firewall policy change, NAT session timeout.

### 3.2 SA Lifetime Expiry

**Mechanism:** Time-based (IKE SA default 86400s, IPSec SA 3600s) or traffic-based. Rekey triggered before expiry; if rekey fails, tunnel goes down.

**Key log keywords:** `lifetime expired`, `max_bytes reached`, `initiating rekey`, `deleting SA`

### 3.3 Peer-Initiated Delete

**Mechanism:** Peer sends DELETE payload via INFORMATION_EXCHANGE.

**Common causes:** Peer restart/maintenance, manual SA clear, peer DPD declared our side dead, peer SA lifetime expired first.

### 3.4 NAT-T Port Drift

**Critical scenario:** After interruption, peer only accepts port 4500; Alibaba Cloud IKEv1 initiator sends first 2 packets on port 500 -> peer drops them -> timeout.

**Recommendations:** Configure peer as initiator; disable NAT-T if not required; enable NAT keepalive.

### 3.5 Tunnel Interruption Diagnostic Flow

```
Step 1: Find interruption time -- search "delete SA" / "deleting SA"
Step 2: Find last ESTABLISHED SA before interruption
Step 3: Determine cause:
  (a) DPD: search "remote.*dead" / "retransmission limit"
  (b) Lifetime: search "lifetime" / "expired" / "rekey"
  (c) Peer DELETE: search "received DELETE" / "INFORMATION_EXCHANGE"
  (d) Retransmit timeout: search "retransmit.*limit" / "giving up"
Step 4: Check re-negotiation result after interruption time
```

---

## 4. Transform Type Numbers (IKEv2)

In IKEv2 `proposal mismatch` logs:
- Type 1: Encryption algorithm (ENCR)
- Type 2: PRF algorithm
- Type 3: Integrity/auth algorithm (INTEG)
- Type 4: DH group

---

## 5. Common Log Keywords

| Purpose | Keywords |
|---------|---------|
| Phase1 start | `phase1`, `IKE_SA_INIT`, `initiating Main Mode` |
| Phase2 start | `phase2`, `IKE_AUTH`, `quick mode` |
| SA established | `ESTABLISHED`, `phase1 completed`, `phase2 completed` |
| SA deleted | `delete SA`, `deleting SA`, `DYING` |
| DPD | `dpd`, `dead`, `retransmit`, `remote seems to be dead` |
| Lifetime | `lifetime`, `expired`, `rekey` |
| MID disorder | `Drop unordered Message` |
| Errors | `PROTO_ERR`, `INTERNAL_ERR`, `failed`, `mismatch`, `rejected` |

---

## 6. Third-Party Device Integration Notes

| Vendor | Common Issues | Recommendation |
|--------|--------------|----------------|
| Huawei | DH group naming (group2 vs modp1024) | Verify mapping against Alibaba Cloud docs |
| H3C | Default aggressive mode; security policy needed | Use main mode; allow UDP 500/4500 and ESP |
| Cisco ASA | PRF must match integrity algorithm; byte-based SA expiry | Align PRF with integrity; disable byte-based expiry |
| FortiGate | Must configure Local-in Policy; `localid-type address` | Add local-in policy; verify PFS consistency |
| General | IKEv1 vs IKEv2 mismatch | Ensure same IKE version on both sides |

---

## 7. Algorithm Name Mapping

### 7.1 Encryption

| Alibaba Cloud | Cisco | Huawei/H3C | FortiGate |
|---------------|-------|------------|-----------|
| aes | aes 128 | aes-128 | aes128 |
| aes-192 | aes 192 | aes-192 | aes192 |
| aes256 | aes 256 | aes-256 | aes256 |
| 3des | 3des | 3des | 3des |

### 7.2 Authentication

| Alibaba Cloud | Cisco | Huawei/H3C | FortiGate |
|---------------|-------|------------|-----------|
| sha1 | sha | sha1 | sha1 |
| sha256 | sha256 | sha2-256 | sha256 |
| sha384 | sha384 | sha2-384 | sha384 |
| md5 | md5 | md5 | md5 |

### 7.3 DH Groups

| Alibaba Cloud | Group No. | Key Length | Level |
|---------------|-----------|-----------|-------|
| group2 | DH 2 | 1024-bit MODP | Basic |
| group5 | DH 5 | 1536-bit MODP | Medium |
| group14 | DH 14 | 2048-bit MODP | Recommended |
| group19 | DH 19 | 256-bit ECP | Recommended |
| group20 | DH 20 | 384-bit ECP | High |
