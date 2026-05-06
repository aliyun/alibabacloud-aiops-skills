# RAM Permission Policies

## Minimum Permission List

### DDoS Basic Protection (antiddos-public)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "antiddos-public:DescribeInstanceIpAddress",
        "antiddos-public:DescribeDdosEventList"
      ],
      "Resource": "*"
    }
  ]
}
```

### DDoS Native Protection (ddosbgp)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ddosbgp:DescribeInstanceList",
        "ddosbgp:DescribePackIpList",
        "ddosbgp:DescribeDdosEvent",
        "ddosbgp:DescribeTraffic"
      ],
      "Resource": "*"
    }
  ]
}
```

### DDoS Anti-DDoS Pro/Premium (ddoscoo)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ddoscoo:DescribeInstances",
        "ddoscoo:DescribeDomains",
        "ddoscoo:DescribeDDoSEvents",
        "ddoscoo:DescribeDDosAllEventList",
        "ddoscoo:DescribeDomainQPSList",
        "ddoscoo:DescribePortFlowList",
        "ddoscoo:DescribeDomainStatusCodeList"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Permission Note

All permissions listed above are **read-only permissions**, supporting only query (Describe/List) operations. No create, modify, or delete write operations are included.

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read this file (`references/ram-policies.md`) to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
