# RAM Policies for alibabacloud-ebs-disk-events

This document lists the Alibaba Cloud RAM (Resource Access Management) permissions required by the `alibabacloud-ebs-disk-events` Skill.

---

## Required Permissions

The following permissions are required to perform all operations in this skill:

| API Name | Permission | Description |
|----------|------------|-------------|
| DescribeEvents | `ebs:DescribeEvents` | Query cloud disk risk events |

---

## Minimal RAM Policy

The minimal RAM policy required to run this skill is as follows:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ebs:DescribeEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Create a Custom RAM Policy

### Via Alibaba Cloud Console

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select the **JSON** tab
5. Paste the minimal RAM policy above
6. Name the policy, e.g., `EBSDiskEventsReadOnlyPolicy`
7. Click **OK**

### Via Aliyun CLI

```bash
# Create policy file
cat > ebs-events-policy.json <<EOF
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ebs:DescribeEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create RAM policy
aliyun ram create-policy \
  --policy-name EBSDiskEventsReadOnlyPolicy \
  --policy-document "$(cat ebs-events-policy.json)" \
  --description "Policy for querying EBS disk risk events"

# Attach policy to user (replace YOUR_USER_NAME)
aliyun ram attach-policy-to-user \
  --policy-name EBSDiskEventsReadOnlyPolicy \
  --policy-type Custom \
  --user-name YOUR_USER_NAME
```

---

## Resource-Level Permissions

The `ebs:DescribeEvents` API currently requires `"Resource": "*"`, because it queries events across multiple cloud disks and does not yet support resource-level authorization.

---

## Permission Verification

Verify that the current credentials have the required permissions:

```bash
# Simple call to the DescribeEvents API
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 1
```

**Success**: Returns an event list or an empty list (indicating no events).

**Permission Denied Error**:

```
{
  "Code": "Forbidden",
  "Message": "User is not authorized to operate."
}
```

When encountering a permission error:
1. Review this document to confirm the required permissions
2. Use the `ram-permission-diagnose` skill for troubleshooting
3. Contact the account administrator to grant the permissions

---

## Extended Permissions (Advanced Usage)

To extend this skill with other EBS operations, consider the following permissions:

| Permission | Description |
|------------|-------------|
| `ebs:DescribeDisks` | List and view cloud disk details |
| `ebs:DescribeDiskReplicaPairs` | Query cloud disk replica pairs |
| `ebs:CreateSnapshot` | Create a snapshot for data protection events |
| `ebs:ResizeDisk` | Resize a cloud disk for capacity/performance issues |
| `ecs:ModifyInstanceSpec` | Modify instance spec for instance-disk spec mismatch |

---

## Security Best Practices

1. **Least Privilege**: Grant only the `ebs:DescribeEvents` read-only permission
2. **Use RAM Roles**: Prefer RAM roles over AccessKeys in ECS instances or container environments
3. **Rotate Credentials Regularly**: Periodically replace AccessKey pairs
4. **Enable MFA**: Enable multi-factor authentication for sensitive operations
5. **Audit Logs**: Monitor API calls via ActionTrail

---

## References

- [Alibaba Cloud RAM Documentation](https://www.alibabacloud.com/help/en/ram)
- [EBS API Authorization](https://www.alibabacloud.com/help/en/ebs/developer-reference/api-authorization)
- [RAM Policy Elements](https://www.alibabacloud.com/help/en/ram/developer-reference/policy-elements)
