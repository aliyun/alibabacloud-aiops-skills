# RAM Policies - Elasticsearch Instance Network Management

This document lists the RAM permissions required to execute Elasticsearch instance network management operations.

---

## Full Permission Policy

To execute all network management operations, use the following full permission policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:TriggerNetwork",
        "elasticsearch:EnableKibanaPvlNetwork",
        "elasticsearch:DisableKibanaPvlNetwork",
        "elasticsearch:UpdateKibanaPvlNetwork",
        "elasticsearch:ModifyWhiteIps",
        "elasticsearch:OpenHttps",
        "elasticsearch:CloseHttps",
        "elasticsearch:UpdateKibanaSso"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Per-Operation Permission Policies

### 1. DescribeInstance - View Instance Details

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:DescribeInstance",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

Limit to specific instance:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:DescribeInstance",
      "Resource": "acs:elasticsearch:cn-hangzhou:*:instances/es-cn-xxxxxx"
    }
  ]
}
```

### 2. TriggerNetwork - Trigger Network Change

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:TriggerNetwork",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 3. EnableKibanaPvlNetwork - Enable Kibana Private Network Access

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:EnableKibanaPvlNetwork",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 4. DisableKibanaPvlNetwork - Disable Kibana Private Network Access

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:DisableKibanaPvlNetwork",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 5. UpdateKibanaPvlNetwork - Update Kibana Private Network Access Configuration

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:UpdateKibanaPvlNetwork",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 6. ModifyWhiteIps - Modify Whitelist

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:ModifyWhiteIps",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 7. OpenHttps - Enable HTTPS

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:OpenHttps",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 8. CloseHttps - Disable HTTPS

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:CloseHttps",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

### 9. UpdateKibanaSso - Enable/Disable Kibana SSO Authentication

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "elasticsearch:UpdateKibanaSso",
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

---

## Read-Only Permission Policy

Only view instance information, no modification operations:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Network Management Permission Policy

Allow viewing and managing network configurations (excluding architecture changes):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:EnableKibanaPvlNetwork",
        "elasticsearch:DisableKibanaPvlNetwork",
        "elasticsearch:UpdateKibanaPvlNetwork",
        "elasticsearch:ModifyWhiteIps",
        "elasticsearch:OpenHttps",
        "elasticsearch:CloseHttps",
        "elasticsearch:UpdateKibanaSso"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Resource ARN Format

Elasticsearch resource ARN format:

```
acs:elasticsearch:{region}:{account-id}:instances/{instance-id}
```

**Examples:**

| Scenario | ARN |
|----------|-----|
| All instances in all regions | `acs:elasticsearch:*:*:instances/*` |
| All instances in Hangzhou region | `acs:elasticsearch:cn-hangzhou:*:instances/*` |
| Specific instance | `acs:elasticsearch:cn-hangzhou:1234567890:instances/es-cn-xxxxxx` |

---

## Related Dependency Permissions

### VPC Related Permissions (required for TriggerNetwork)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeVSwitchAttributes"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Reference Links

- [RAM Policy Overview](https://help.aliyun.com/document_detail/93732.html)
- [Elasticsearch Authorization Information](https://help.aliyun.com/document_detail/169951.html)
