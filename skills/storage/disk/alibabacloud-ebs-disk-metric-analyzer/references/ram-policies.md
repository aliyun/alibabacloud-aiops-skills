# RAM Policies for EBS Disk Monitoring and Metric Analysis

This document lists all RAM (Resource Access Management) permissions required for the `alibabacloud-ebs-disk-metric-analyzer` skill.

---

## Required Permissions

The following permissions are required to execute all operations in this skill:

| API Name | Permission | Description |
|----------|------------|-------------|
| DescribeMetricData | `ebs:DescribeMetricData` | Query monitoring metric data for cloud disks |

---

## Minimum RAM Policy

Below is the minimum RAM policy required for this skill to function:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ebs:DescribeMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Creating a Custom RAM Policy

### Via Alibaba Cloud Console

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select **JSON** tab
5. Paste the minimum RAM policy above
6. Name the policy (e.g., `EBSDiskMetricAnalyzerPolicy`)
7. Click **OK** to create

### Via Aliyun CLI

```bash
# Create policy file
cat > ebs-metric-policy.json <<EOF
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ebs:DescribeMetricData"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create the RAM policy
aliyun ram create-policy \
  --policy-name EBSDiskMetricAnalyzerPolicy \
  --policy-document "$(cat ebs-metric-policy.json)" \
  --description "Policy for EBS disk monitoring and metric analysis"

# Attach policy to a user (replace YOUR_USER_NAME)
aliyun ram attach-policy-to-user \
  --policy-name EBSDiskMetricAnalyzerPolicy \
  --policy-type Custom \
  --user-name YOUR_USER_NAME
```

---

## Resource-Level Permissions

The `ebs:DescribeMetricData` API currently requires `"Resource": "*"` as it queries metrics across multiple disks and does not support resource-level authorization.

---

## Permission Verification

To verify that your current credentials have the required permissions:

```bash
# Test the DescribeMetricData API with a simple query
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id cn-hangzhou \
  --period 60
```

**Expected Success**: Returns monitoring data or an empty DataList (if no disks exist).

**Permission Denied Error**:
```
{
  "Code": "Forbidden",
  "Message": "User is not authorized to operate."
}
```

If you receive a permission error:
1. Review this document to confirm required permissions
2. Use the `ram-permission-diagnose` skill to troubleshoot
3. Contact your account administrator to grant the necessary permissions

---

## Additional Permissions for Advanced Usage

If you plan to extend this skill with additional EBS operations, consider these permissions:

| Permission | Description |
|------------|-------------|
| `ebs:DescribeDisks` | List and describe cloud disks |
| `ebs:DescribeDiskReplicaPairs` | Query disk replica pairs |
| `ebs:DescribeDiskReplicaGroups` | Query disk replica groups |
| `cms:DescribeMetricList` | Alternative CloudMonitor API for metrics |

---

## Troubleshooting Permission Issues

### Common Error Codes

| Error Code | Cause | Solution |
|------------|-------|----------|
| `Forbidden` | Missing `ebs:DescribeMetricData` permission | Add permission to RAM policy and attach to user |
| `InvalidAccountStatus.NotEnoughBalance` | Insufficient account balance | Top up your Alibaba Cloud account |
| `NoPermission.SLR` | Missing service-linked role | Create `AliyunServiceLinkedRoleForEBS` via RAM console |

### Debug Steps

1. **Verify credentials are configured**:
   ```bash
   aliyun configure list
   ```

2. **Check user permissions**:
   ```bash
   aliyun ram list-policies-for-user --user-name YOUR_USER_NAME
   ```

3. **Verify policy contains required actions**:
   ```bash
   aliyun ram get-policy --policy-name EBSDiskMetricAnalyzerPolicy --policy-type Custom
   ```

---

## Security Best Practices

1. **Principle of Least Privilege**: Only grant `ebs:DescribeMetricData` if users only need to query metrics
2. **Use RAM Roles**: For ECS instances or container environments, use RAM roles instead of AccessKey credentials
3. **Rotate Credentials**: Regularly rotate AccessKey pairs
4. **Enable MFA**: Enable multi-factor authentication for sensitive operations
5. **Audit Logs**: Enable ActionTrail to monitor API calls and permission usage

---

## Reference

- [Alibaba Cloud RAM Documentation](https://www.alibabacloud.com/help/en/ram)
- [EBS API Authorization](https://www.alibabacloud.com/help/en/ebs/developer-reference/api-authorization)
- [RAM Policy Elements](https://www.alibabacloud.com/help/en/ram/developer-reference/policy-elements)
