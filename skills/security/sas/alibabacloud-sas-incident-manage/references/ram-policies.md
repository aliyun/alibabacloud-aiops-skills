# RAM Policies - Cloud Security Center Incident Management

This document details the RAM permissions required for the Cloud SIEM incident management skill.

## Required Permissions

- `yundun-sas:ListIncidents` — 查询安全事件列表 (Query security incident list)
- `yundun-sas:GetIncident` — 获取事件详情 (Get incident details)
- `yundun-sas:DescribeEventCountByThreatLevel` — 查询各威胁等级事件统计 (Query event count by threat level)

## Minimum Permission Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:ListIncidents",
        "yundun-sas:GetIncident",
        "yundun-sas:DescribeEventCountByThreatLevel"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Request Steps

### Via RAM Console

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permission Management** > **Policies**
3. Click **Create Policy**
4. Select **Script** mode, enter policy name (e.g., `CloudSIEMIncidentReadOnly`)
5. Paste the minimum permission policy JSON above
6. Click **OK** to create
7. Navigate to **Identities** > **Users**
8. Select the target user, click **Add Permissions**
9. Select the newly created policy and authorize

## Permission Verification

```bash
# Test ListIncidents permission
python3 scripts/siem_client.py list-incidents --size 1

# Expected: Returns JSON with RequestId and Incidents array
# If permission error: Returns Forbidden.RAM error
```

## Common Errors

### Error: Forbidden.RAM

```json
{
  "Code": "Forbidden.RAM",
  "Message": "User not authorized to operate on the specified resource."
}
```

**Resolution**: User lacks required RAM permissions. Follow the permission request steps above.

### Error: InvalidAccessKeyId.NotFound

```json
{
  "Code": "InvalidAccessKeyId.NotFound",
  "Message": "Specified access key is not found."
}
```

**Resolution**: AccessKey is invalid or disabled. Check credential configuration.

### Error: SignatureDoesNotMatch

```json
{
  "Code": "SignatureDoesNotMatch",
  "Message": "The specified signature is invalid."
}
```

**Resolution**: AccessKeySecret is incorrect. Verify credentials.

## Security Best Practices

1. **Least Privilege**: Grant only the minimum permissions needed
2. **Use RAM Users**: Never use root account AccessKeys
3. **Regular Rotation**: Rotate AccessKeys every 90 days
4. **Permission Audit**: Regularly audit and remove unused permissions
5. **STS Tokens**: Use temporary credentials (STS) when possible

## References

- [RAM Policy Syntax](https://help.aliyun.com/document_detail/28664.html)
- [Cloud Security Center API Permissions](https://help.aliyun.com/document_detail/28674.html)
- [AccessKey Management](https://ram.console.aliyun.com/manage/ak)
