# Module 7: Deep Entry-Vector Scan (SAS-only) — Post-Confirmation

## Purpose
Once mining is confirmed (Step 1 found at least one alert), deepen the intrusion
entry-vector hypothesis using additional Security Center read-only APIs that
surface **why** the miner got in:

1. **Baseline weak-config risks** — weak passwords, unauthorized Redis/Docker/
   Hadoop, risky OS/app configurations. These are the most common opportunistic
   cryptominer entry vectors.
2. **Grouped vulnerabilities** — unfixed vulns aggregated by type/necessity; shows
   which CVE class is the leading suspect.
3. **Exposure statistics** — account-wide exposed-instance/port/component counts;
   a one-shot "how big is the attack surface" summary.

## APIs — Public SAS (version 2018-12-03)

```
Product: sas  (endpoint tds.{region}.aliyuncs.com, version 2018-12-03)
Actions:
  DescribeCheckWarningSummary   -- baseline / weak-config risk items (CurrentPage/PageSize)
  DescribeGroupedVul            -- vulnerabilities grouped by type (cve/app/cms)
  DescribeExposedStatistics     -- one-shot exposure-surface summary counts
```

All three require `yundun-aegis:*` read-only permissions (same family as the core
Steps 1–4 APIs). No new product or permission family needed.

## Conditional Triggering

Step 4a runs **automatically** once `len(alerts) > 0` (mining confirmed); it does
NOT run on a clean account. This avoids unnecessary API calls and keeps the
report focused. No extra flag is required. Failures degrade gracefully (captured
in `deep.errors`, never fatal).

## Output

```json
{
  "baseline": {
    "count": 5,
    "items": [
      {"name": "Weak SSH password", "level": "high",
       "type": "baseline", "affectedCount": 2}
    ]
  },
  "groupedVul": [
    {"type": "cve", "name": "CVE-2022-XXXX (Remote Code Execution)", "necessity": "asap", "count": 3}
  ],
  "exposedStatistics": {
    "exposedInstanceCount": 4,
    "exposedPortCount": 7,
    "exposedComponentCount": 3,
    "gatewayAssetCount": 1
  },
  "errors": []
}
```

## How Results Feed Into the Report

- **Risk assessment (Step 5):** If baseline weak-configs or unfixed grouped-vuln
  items are present, they strengthen the "likely intrusion entry vector" finding
  and may escalate severity.
- **Markdown report:** rendered as "## Step 4a: Deep Entry-Vector Scan (SAS)"
  with baseline list, grouped vuln table, and exposure summary.
- **JSON report:** available under `step4a_deep_scan`.

## Standalone Script

```bash
python scripts/query_deep_scan.py
python scripts/query_deep_scan.py --region cn-hangzhou --format json
```
