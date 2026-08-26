# RAM Permission Policies

This Skill is **read-only**. The minimum permissions required are listed below.

## Permission List

| Permission | Description |
| --- | --- |
| `yundun-waf:DescribeInstance` | Retrieve WAF instance information, including InstanceId and RegionId |
| `yundun-waf:DescribePostpayBills` | Query pay-as-you-go bill details, including daily and hourly breakdowns |
| `yundun-waf:DescribeElasticBills` | Query daily bill summaries for the last 7 days |
| `yundun-waf:DescribePrepayDailyBills` | Query elastic postpaid bills for prepaid instances |
| `yundun-waf:DescribeChargeModule` | Query WAF pricing module information (unit price, tiered pricing) |
| `yundun-waf:DescribeChargeResult` | Calculate SeCU/Credit cost based on usage |

## Minimum RAM Policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribePostpayBills",
        "yundun-waf:DescribeElasticBills",
        "yundun-waf:DescribePrepayDailyBills",
        "yundun-waf:DescribeChargeModule",
        "yundun-waf:DescribeChargeResult"
      ],
      "Resource": "*"
    }
  ]
}
```
