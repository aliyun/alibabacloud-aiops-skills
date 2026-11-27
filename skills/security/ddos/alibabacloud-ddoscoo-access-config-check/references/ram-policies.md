# RAM Policies — alibabacloud-ddoscoo-access-config-check

Minimum permissions to run this skill. All of them are read-only except the CloudMonitor one-off probe
creation, which creates a transient probe task and no persistent resource.

## Required

| API | Action | Used for |
|-----|--------|----------|
| ddoscoo DescribeInstances | `yundun-ddoscoo:DescribeInstances` | Instance existence + Anti-DDoS instance IPs |
| ddoscoo DescribeWebRules | `yundun-ddoscoo:DescribeWebRules` | Domain / CNAME / certificate name / proxy types and ports / origins |
| ddoscoo DescribeSchedulerRules | `yundun-ddoscoo:DescribeSchedulerRules` | Traffic-scheduler rules (CNAME, RuleType, line ValueType/Status) |
| ddoscoo DescribeDomains (optional) | `yundun-ddoscoo:DescribeDomains` | Auxiliary protected-domain list |
| Cms DescribeSiteMonitorISPCityList | `cms:DescribeSiteMonitorISPCityList` | Mainland + overseas vantage point selection |
| Cms CreateInstantSiteMonitor | `cms:CreateInstantSiteMonitor` | One-off DNS / HTTP probes |
| Cms DescribeSiteMonitorLog | `cms:DescribeSiteMonitorLog` | Per-probe-point results |

## Required for C2 (bound certificate expiry) — `cas`

| API | Action | Used for |
|-----|--------|----------|
| cas ListUserCertificateOrder | `yundun-cert:ListUserCertificateOrder` | Find the certificate bound on Anti-DDoS and read `EndDate` / `Expired` |
| cas GetUserCertificateDetail | `yundun-cert:GetUserCertificateDetail` | Supply `EndDate` / `Expired` by `CertId` when the list record has none |

The RAM code prefix for SSL Certificates Service is `yundun-cert`, authorization granularity
is operation-level, and these operations only support `Resource: "*"`. If you would rather not grant a custom
policy, attach the read-only system policy **`AliyunYundunCertReadOnlyAccess`** instead.

**`cas` is C2's only data source** — this skill does not read the served certificate. When the permission is
missing, every domain's C2 is `NOT_DETECTED` with that reason named. A missing `cas` permission must never
block the whole run: C1, C3 and C4 are unaffected and still produce verdicts.

## Custom policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeWebRules",
        "yundun-ddoscoo:DescribeSchedulerRules",
        "yundun-ddoscoo:DescribeDomains"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeSiteMonitorISPCityList",
        "cms:CreateInstantSiteMonitor",
        "cms:DescribeSiteMonitorLog"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cert:ListUserCertificateOrder",
        "yundun-cert:GetUserCertificateDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

Drop the third statement only when running with `--no-cas`; every domain's C2 then becomes `NOT_DETECTED`,
because `cas` is C2's only data source.

## System policy reference

- `AliyunYundunDDoSReadOnlyAccess` — Anti-DDoS read-only, covers the three ddoscoo actions.
- `AliyunCloudMonitorFullAccess`, or a custom policy limited to the three `cms:` actions above. There is no
  read-only CloudMonitor system policy that also permits creating one-off probes, because probe creation is a
  write operation on a pay-as-you-go resource.
- `AliyunYundunCertReadOnlyAccess` — SSL Certificates Service read-only (optional block).

## Cost note to disclose before running

`CreateInstantSiteMonitor` is billed pay-as-you-go by the site-monitor (Network Analysis and Monitoring) service and requires
that service to be activated. The cost of a handful of one-off probes is small but non-zero, and each domain
consumes at least one `DNS` task plus one `HTTP` task per endpoint probed. Tell the user the expected task
count before creating them (`create_probes.py --dry-run` prints exactly that), and keep `--max-endpoints`
low. Billing details: https://www.alibabacloud.com/help/zh/cms/cloudmonitor-1-0/product-overview/pay-as-you-go

If the service is not activated, `CreateInstantSiteMonitor` fails with a not-activated error — fall back to
local probing per the decision tree in SKILL.md (error type A) and mark the mainland-vs-overseas comparison
`NOT_DETECTED`.
