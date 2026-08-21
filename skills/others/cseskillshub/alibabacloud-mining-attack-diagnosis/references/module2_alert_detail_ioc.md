# Module 2: Alert Detail & IOC Extraction

## Purpose
For each mining alert found in Step 1, fetch the full alert detail from
Security Center (SAS) and extract Indicators of Compromise (IOCs): mining-pool
IPs/domains, sample hashes, and malicious process/command indicators. IOCs feed
the containment recommendations (block pool IPs, hunt the sample cluster-wide).

## APIs — Public SAS (version 2018-12-03)

```
Product: sas  (endpoint tds.{region}.aliyuncs.com, version 2018-12-03)
Actions:
  DescribeAlarmEventDetail  -- detail of an aggregated alarm  (by UniqueInfo)
  DescribeSuspEventDetail   -- detail of a raw event          (by SuspEventId)
```

## Request Parameters

| API | Key Parameter | Source |
|-----|---------------|--------|
| DescribeAlarmEventDetail | `UniqueInfo` (+ `From=sas`, `Lang`) | `uniqueInfo` from a Step 1 alarm record |
| DescribeSuspEventDetail | `SuspEventId` (+ `Lang`) | `eventId` from a Step 1 susp record |

## IOC Extraction (best-effort)

The detail response contains nested key/value detail fields whose exact schema
varies by alert type. The extractor walks all string leaves and pattern-matches:

| IOC | Method |
|-----|--------|
| Mining-pool IPs | Public IPv4 regex (private/reserved ranges excluded) |
| Domains | FQDN regex (aliyun/aliyuncs infra domains excluded) |
| Sample MD5 / SHA256 | 32-/64-hex regex |
| Process / command | Strings that look like paths or command lines AND contain a mining keyword |

IOCs are **never masked** — they carry forensic value and are needed for
containment. Do not treat internal/private IPs as pool endpoints.

## Aggregation

Across all detailed alerts, IOCs are de-duplicated and aggregated into a single
IOC table for the report:

```json
{
  "miningPoolIps": ["45.9.148.x"],
  "domains": ["pool.example-mining.tld"],
  "sampleMd5": ["<md5>"],
  "sampleSha256": ["<sha256>"],
  "processIndicators": ["/tmp/kdevtmpfsi", "xmrig -o stratum+tcp://..."],
  "matchedKeywords": ["xmrig", "stratum"]
}
```

## Interpreting Results

- **Pool IPs/domains present** → active outbound mining traffic; attacker likely
  still controls the host. Highest urgency.
- **Persistence indicators** (cron, systemd, startup scripts, `authorized_keys`)
  in the process/command strings → will re-infect after a simple process kill;
  remove persistence before restoring service.
- **Sample hash present** → hunt the same hash across the fleet to find
  additional compromised hosts.

## Standalone Script

```bash
python scripts/query_alert_detail.py --unique-info <UNIQUE_INFO>
python scripts/query_alert_detail.py --event-id <SUSP_EVENT_ID> --format json
```
