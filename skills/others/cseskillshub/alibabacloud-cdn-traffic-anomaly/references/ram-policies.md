# RAM Policies (Read-Only)

This skill only calls Describe-class (read-only) APIs. Grant the following exact actions — no wildcards are needed.

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "cdn:DescribeDomainBpsData",
        "cdn:DescribeDomainUsageData",
        "cdn:DescribeDomainQpsData",
        "cdn:DescribeDomainRealTimeBpsData",
        "cdn:DescribeDomainSrcBpsData",
        "cdn:DescribeCdnDomainLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

## Action → usage mapping

| Action | Used by | Purpose |
|--------|---------|---------|
| `sts:GetCallerIdentity` | both scripts | Derive caller UID for traceability (informational) |
| `cdn:DescribeDomainUsageData` | `cdn_traffic_anomaly.py` | bps + flow series per interval (primary baseline source) |
| `cdn:DescribeDomainBpsData` | `cdn_traffic_anomaly.py` | Bandwidth trend backup series |
| `cdn:DescribeDomainQpsData` | `cdn_traffic_anomaly.py` | Request-rate correlation series |
| `cdn:DescribeDomainRealTimeBpsData` | `cdn_traffic_anomaly.py` | Fine-grained view of the most recent period |
| `cdn:DescribeDomainSrcBpsData` | `cdn_traffic_anomaly.py` | Origin (return-to-source) bandwidth series; backs the T6 origin-amplification assessment |
| `cdn:DescribeCdnDomainLogs` | `cdn_traffic_analysis.py` | List offline access-log download URLs for forensics |

## Notes

- The skill never calls mutating APIs; do NOT grant `cdn:Modify*`, `cdn:Set*`, `cdn:Refresh*`, `cdn:Push*`, `cdn:Stop*`, or `cdn:Delete*` for this skill.
- On `Forbidden` / `NoPermission` errors the scripts log `[WARN]` and continue with the remaining queries.
