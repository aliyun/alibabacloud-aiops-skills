# Module 4: Attack Surface Detection

## Purpose
Identify the most likely intrusion entry for the mining compromise by
assessing the account's attack surface through Security Center (SAS):
internet-exposed assets and unpatched high-risk vulnerabilities. Correlating
these with the mining-affected assets (Step 1/3) narrows down the root cause.

## APIs — Public SAS (version 2018-12-03)

```
Product: sas  (endpoint tds.{region}.aliyuncs.com, version 2018-12-03)
Actions:
  DescribeExposedInstanceList  -- internet-exposed assets (attack surface)
  DescribeVulList              -- vulnerability records (entry vectors)
```

## Request Parameters

| API | Key Parameters | Notes |
|-----|----------------|-------|
| DescribeExposedInstanceList | `CurrentPage`, `PageSize`, `Lang` | exposed IP/port/component per asset |
| DescribeVulList | `Type` (cve/sys/cms/app/emg/sca), `Necessity` (asap/later/nntf), `Dealed` | defaults: `Type=cve`, `Necessity=asap` |

## Why This Matters for Mining

Cryptominers are overwhelmingly delivered through **opportunistic exploitation
of exposed, unpatched services** rather than targeted attacks. Based on analysis
of 73 confirmed mining tickets, the entry vectors ranked by real-world frequency:

1. **Port exposure (27/73):** SSH(22), MySQL(3306), Redis(6379), and app ports
   (3000, 9997, etc.) left open to 0.0.0.0/0 in the security group.
2. **Component unauthorized-access / RCE vulnerabilities (23/73):** Nacos ≤1.4.0
   unauthorized API, xxl-job-executor unauthorized access (port 9997), litellm
   vulnerabilities, PostgreSQL, Docker/Kubernetes API, Confluence, Log4j-class
   issues — services that require no authentication or have known auth-bypass CVEs.
3. **Weak credentials / brute-force (17/73):** SSH/RDP/database accounts with
   weak or default passwords cracked by automated scanning.
4. **Poisoned custom image (2/73):** a custom image created from an already-
   infected instance carries the malware; every new instance launched from it
   boots compromised (see module5 warning).

## Correlation Logic

1. List internet-exposed assets and their exposed ports/components.
2. List `asap`-necessity vulnerabilities.
3. Intersect the affected mining assets (Step 3) with exposed + vulnerable
   assets. An affected asset that is **both exposed and has an `asap` vuln** is
   the prime entry-vector suspect and drives the P1 patch recommendation.
4. If the affected instance was created from a **custom image** and exhibited
   mining symptoms immediately after boot, trace the image's source instance —
   it was likely already compromised when the image was captured.

## Output

```json
{
  "exposed_count": 3,
  "vul_count": 5,
  "exposed_instances": [
    {"instanceName": "web-prod-01", "internetIp": "1.2.3.4",
     "exposurePort": "6379", "exposureComponent": "redis"}
  ],
  "vulnerabilities": [
    {"aliasName": "CVE-2022-xxxx ...", "necessity": "asap",
     "instanceName": "web-prod-01", "status": "unfixed"}
  ]
}
```

## Standalone Script

```bash
python scripts/query_attack_surface.py --account <UID>
python scripts/query_attack_surface.py --vul-type cve --necessity asap --format json
python scripts/query_attack_surface.py --scope exposed
```
