# Mining Indicators Reference

Single reference for the mining (cryptojacking) recognition heuristics used by
the skill. The authoritative source of the keyword list is
`scripts/_constants.py` (`MINING_ALERT_KEYWORDS`, `MINING_EVENT_TYPES`).

## Recognition Keywords (`MINING_ALERT_KEYWORDS`)

An SAS alert is classified as mining when its **name**, **type**, or
**description** contains any of these (case-insensitive substring match):

### Chinese wording
See `MINING_ALERT_KEYWORDS` in `scripts/_constants.py` (the Chinese entries are
kept in the Python source for runtime matching against SAS alert text).

### English generic
`mining`, `miner`, `cryptomining`, `cryptojacking`, `coinminer`, `coin miner`,
`monero`, `stratum`, `mining pool`, `pool connection`

### Known miner families / tools
`xmrig`, `xmr-stak`, `minerd`, `cpuminer`, `ccminer`, `nbminer`,
`phoenixminer`, `kdevtmpfsi`, `kinsing`, `watchdogs`, `sysrv`, `wannamine`,
`photominer`, `lemon_duck` / `lemonduck`, `z0miner`, `teamtnt`, `8220`,
`outlaw`, `rocke`

## Relevant SAS Alert Types (`MINING_EVENT_TYPES`)

Mining commonly surfaces under these Security Center alert categories:

| Alert Type | Meaning | Mining relevance |
|------------|---------|------------------|
| Malicious script | Mining install/dropper scripts | Dropper / installer stage |
| Malicious process | The miner binary itself | Direct miner detection |
| Process anomaly | High-CPU / unusual process behavior | Crypto-mining CPU signature |
| Suspicious network connection | Mining-pool (stratum) communication | Pool beaconing / C2 |
| Self-mutating trojan / worm | Worm-style miners (sysrv, kinsing) | Lateral spread |
| Webshell / backdoor | Common miner entry vector | Exploited web service |
| Application intrusion | Exploited exposed service (entry) | Entry via exposed service |
| Malicious network behavior | C2 / pool beaconing | Outbound pool connection |

## Severity Ranking (`LEVEL_ORDER`)

| SAS Level | Rank | Report severity contribution |
|-----------|------|------------------------------|
| serious | 3 | Drives CRITICAL |
| suspicious | 2 | HIGH |
| remind | 1 | HIGH (if mining-confirmed) |

## IOC Types Extracted (Step 2)

| IOC | Use |
|-----|-----|
| Mining-pool IPs (public IPv4) | Block on egress; confirms active mining |
| Domains (FQDN) | Block; pool/C2 endpoints |
| Sample MD5 / SHA256 | Fleet-wide threat hunting |
| Process / command indicators | Identify & kill; find persistence |

## Notes

- Keyword matching is intentionally broad to catch renamed/obfuscated miners;
  the `matchedKeywords` field records which keywords fired for evidence.
- The `8220` entry is broad; it is validated in context by
  co-occurring alert types, so false positives are surfaced (not hidden) with
  their matched keywords for the analyst to judge.
- IOCs are never masked; account-scoped identifiers (UID, asset uuid) are.
