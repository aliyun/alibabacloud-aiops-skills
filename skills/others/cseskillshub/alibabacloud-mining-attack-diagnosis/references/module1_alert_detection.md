# Module 1: Mining Alert Detection

## Purpose
Detect cryptomining (cryptojacking) compromises by querying Security Center
(SAS) alert events and filtering them for mining indicators. This is Step 1 of
the SOP and the authoritative signal — SAS's threat-detection engine flags
mining programs, mining-pool communication, and self-mutating trojans/worms
that frequently carry miners.

## Triggering Signals (Strong vs Weak)

Route a request into this mining SOP based on **mining-specific** signals, not on
generic symptoms. This distinction is derived from real ECS ticket analysis
(see the git-ignored `test/weak_association_symptoms.md`).

**Strong signals (drive this skill on their own):**
- mining / coinminer / cryptojacking / cryptomining / mining-program / mining-trojan
- mining pool / stratum / pool outbound connection; monero
- **A mining-pool outbound-connection notification, or ECS ports auto-blocked by
  Alibaba Cloud because of mining-pool communication** (real high-frequency,
  mining-specific phrasing)
- Known miner family/tool names: xmrig, kdevtmpfsi, kinsing, sysrv, minerd,
  watchdogs, wannamine, lemonduck, z0miner, teamtnt, 8220
- A Security Center mining-program / malicious-process alert; an AI phone-call
  notification about mining
- High CPU **explicitly suspected by the user to be mining** (qualified, e.g.
  "CPU at 100% for days — is it mining crypto?")

**Weak / ambiguous symptoms (do NOT trigger this skill on their own — multi-cause):**
- SSH unreachable / remote login failure / port 22 blocked
- CPU 100% / resource exhaustion / server freeze (without mining qualifier)
- Generic "server is under attack" without specifics
- Bandwidth / traffic spike
- Isolated "port blocked by platform" (without mining-pool context)

**Routing rule:** a weak symptom enters this SOP only when it co-occurs with an
explicit mining signal — i.e. `weak symptom + (SAS mining alert | mining-pool
outbound | miner process name | user explicitly suspects mining)`. A bare
connectivity/performance/traffic complaint with no mining signal should be
handled by the relevant ECS/network troubleshooting skill, not here.

## APIs — Public SAS (version 2018-12-03)

```
Product: sas  (endpoint tds.{region}.aliyuncs.com, version 2018-12-03)
Actions:
  DescribeSuspEvents      -- security alert events (primary data source)
```

All calls go through the dual-backend layer in `scripts/_cli.py`.

## Request Parameters (common)

| Parameter | Meaning | Notes |
|-----------|---------|-------|
| `CurrentPage` / `PageSize` | Pagination | Handled by `_cli.paginate_page()` |
| `Dealed` | Handled status | `Y` handled, `N` pending; omit for all |
| `Levels` | Severity filter | `serious` / `suspicious` / `remind` |
| `AlarmEventType` | Alert category | e.g. malicious script / process anomaly |
| `Lang` | Response language | `en` or `zh` |

## Mining Recognition

Alerts are classified as mining when the event **name**, **type**, or
**description** contains any keyword in `MINING_ALERT_KEYWORDS`
(`scripts/_constants.py`). This covers:

- Chinese wording: see `MINING_ALERT_KEYWORDS` in `scripts/_constants.py`
- English generic: `mining`, `miner`, `coinminer`, `cryptojacking`, `monero`,
  `stratum`, `mining pool`
- Known miner families/tools: `xmrig`, `minerd`, `kdevtmpfsi`, `kinsing`,
  `sysrv`, `watchdogs`, `wannamine`, `lemonduck`, `z0miner`, `teamtnt`, `8220`

The typical SAS alert **types** carrying miners are listed in
`MINING_EVENT_TYPES`: malicious script, malicious process,
process anomaly, suspicious network connection (mining-pool comms),
self-mutating trojan/worm.

## Output (normalized alert record)

```json
{
  "source": "alarm|susp",
  "alarmEventName": "Malicious script (mining program)",
  "alarmEventType": "malicious_script",
  "level": "serious",
  "dealed": "N",
  "instanceName": "web-prod-01",
  "internetIp": "1.2.3.4",
  "uuid": "inst-uuid",
  "uniqueInfo": "...",           // used for DescribeAlarmEventDetail (Step 2)
  "eventId": "...",              // used for DescribeSuspEventDetail (Step 2)
  "matchedKeywords": ["xmrig", "mining-pool"],
  "levelRank": 3
}
```

## No-Fabrication Rule

If SAS returns **no** mining-matching alerts, report truthfully that no mining
compromise is indicated. Do NOT invent alerts, affected assets, or IOCs to
"complete" a conclusion, and do NOT print the URGENT banner in that case.

## Standalone Script

```bash
python scripts/query_mining_alerts.py --account <UID> --days 30 --dealed N
python scripts/query_mining_alerts.py --source susp --format json
```
