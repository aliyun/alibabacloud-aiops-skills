# RAM Permissions for DTS Task Query

## Required Permissions

This skill requires the following RAM permission to query DTS task status:

### Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dts:DescribeDtsJobs"
      ],
      "Resource": "*"
    }
  ]
}
```

**Why this permission:**
- `dts:DescribeDtsJobs` - Required to query the list of DTS jobs and their status information across regions via plugin mode (`aliyun dts describe-dts-jobs` - using plugin mode, NOT PascalCase `DescribeDtsJobs`)

### System Policy (Not Recommended)

If you prefer using system policies (though they may grant more permissions than needed):

- `AliyunDTSReadOnlyAccess` - Provides read-only access to DTS resources

**Note:** System policies may include additional permissions beyond what this skill needs. For security best practices, use the custom policy above following the principle of least privilege.

## How to Attach the Policy

### Option 1: Attach to RAM User

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identities > Users**
3. Click on the target RAM user
4. Go to the **Permissions** tab
5. Click **Grant Permission**
6. Select **Custom Policy** and create/select the policy above
7. Click **OK**

### Option 2: Attach to RAM Role

If using a RAM role for ECS or other services:

1. Navigate to **Identities > Roles**
2. Select the target role
3. Follow the same steps as above to attach the policy

## Verification

After attaching the policy, verify permissions:

```bash
# Test the permission with aliyun-cli (plugin mode - lowercase with hyphens)
aliyun dts describe-dts-jobs --region cn-hangzhou --page-size 1
```

If successful, you should receive a JSON response with DTS job information. If you see `DTS.Msg.RamPermissionDenied`, the policy is not correctly attached.

## Troubleshooting

### Permission Denied

**Error:** `DTS.Msg.RamPermissionDenied`

**Solution:**
1. Verify the policy is attached to the correct RAM user/role
2. Check if there are any explicit Deny statements in other policies
3. Wait a few minutes for policy changes to take effect
4. Use the [Policy Simulator](https://ram.console.aliyun.com/tools/simulator) to test permissions

### Multiple Policies Conflict

If multiple policies are attached, ensure no policy has an explicit `Deny` statement for `dts:DescribeDtsJobs`. Deny statements always override Allow statements.
