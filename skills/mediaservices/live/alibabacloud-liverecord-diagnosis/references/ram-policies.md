# RAM Policies for Live Recording Diagnostic Skill

This document lists all RAM permissions required for the Alibaba Cloud Live Recording Diagnostic Skill.

## Required RAM Permissions

The following permissions are required to run all diagnostic operations in this skill:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "live:DescribeLiveDomainMapping",
        "live:DescribeLiveStreamRecordContent",
        "live:DescribeLiveStreamRecordIndexFiles",
        "live:DescribeLiveRecordConfig",
        "live:DescribeLiveRecordVodConfigs",
        "live:DescribeLiveRecordNotifyConfig",
        "live:DescribeLiveStreamsOnlineList",
        "live:DescribeLiveStreamsPublishList",
        "live:DescribeLiveCenterStreamRateData",
        "live:DescribeLiveRecordNotifyRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Details

### Domain Operations

| Permission | Description | Used In |
|------------|-------------|---------|
| `live:DescribeLiveDomainMapping` | Query domain mappings between ingest and playback domains | Step 2.1 - Domain Mapping Query |

### Recording Content Operations

| Permission | Description | Used In |
|------------|-------------|---------|
| `live:DescribeLiveStreamRecordContent` | Query recording content for a specific stream | Step 2.2 - Recording Content Query |
| `live:DescribeLiveStreamRecordIndexFiles` | Query recording index files in OSS | Step 2.3 - Recording Index Files Query |

### Configuration Operations

| Permission | Description | Used In |
|------------|-------------|---------|
| `live:DescribeLiveRecordConfig` | Query recording configuration for OSS | Step 3.1 - OSS Recording Configuration Query |
| `live:DescribeLiveRecordVodConfigs` | Query recording configuration for VOD | Step 3.2 - VOD Recording Configuration Query |
| `live:DescribeLiveRecordNotifyConfig` | Query callback configuration | Step 4.1 - Callback Configuration Query |

### Stream Operations

| Permission | Description | Used In |
|------------|-------------|---------|
| `live:DescribeLiveStreamsOnlineList` | Query currently online streams | Step 5.1 - Online Streams Query |
| `live:DescribeLiveStreamsPublishList` | Query historical stream publish records | Step 5.2 - Stream Publish History Query |
| `live:DescribeLiveCenterStreamRateData` | Query audio/video frame rate data | Step 5.3 - Stream Rate Data Query |

### Callback Operations

| Permission | Description | Used In |
|------------|-------------|---------|
| `live:DescribeLiveRecordNotifyRecords` | Query recording callback event records | Step 6.1 - Callback Records Query |

## Minimum Permission Policy (Read-Only)

This skill requires **read-only** access to ApsaraVideo Live. The policy above grants only query permissions and cannot modify any configurations or data.

## Creating a Custom Policy

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Policies** > **Custom Policies**
3. Click **Create Policy**
4. Enter the following:
   - **Policy Name**: `AliyunLiveRecordingDiagnosisReadOnly`
   - **Policy Document**: Copy the JSON policy above
5. Click **OK** to create the policy

## Attaching the Policy to a User

1. In the RAM Console, navigate to **Users**
2. Select the user who will run the diagnostic skill
3. Click **Add Permissions**
4. Select **Custom Policy** and find `AliyunLiveRecordingDiagnosisReadOnly`
5. Click **OK** to attach the policy

## Using RAM Roles (Recommended for Production)

For production environments, it's recommended to use RAM roles instead of long-lived user credentials.

> **Security Rule**: Do NOT pass AK/SK literals to `aliyun configure set` or any CLI/SDK call. Rely on the default credential chain (environment variables, instance RAM role, or externally managed profiles) so credentials are never handled in this skill.

**Recommended approaches (configure outside of this session):**

1. **ECS instance RAM role** — attach a RAM role to the ECS instance running the skill; the CLI/SDK default credential chain will pick it up automatically.
2. **External RAM role assumption** — have your platform/CI assume the target role and inject short-lived STS credentials via environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, `ALIBABA_CLOUD_SECURITY_TOKEN`).
3. **Pre-configured profile** — configure the profile once outside this session (e.g., `aliyun configure` interactively, or your org's credential helper), then the skill only verifies it via `aliyun configure list`.

The skill itself must only read credential status via `aliyun configure list` and never invoke `aliyun configure set` with credential values.

## Permission Troubleshooting

### Error: Forbidden.RAM

```json
{
  "Code": "Forbidden.RAM",
  "Message": "User not authorized to operate on the specified resource"
}
```

**Resolution:**
1. Verify the RAM policy is attached to your user
2. Check that all required permissions are included in the policy
3. Wait 1-2 minutes for permission changes to propagate

### Error: InvalidAccessKeyId.NotFound

```json
{
  "Code": "InvalidAccessKeyId.NotFound",
  "Message": "Specified access key is not found"
}
```

**Resolution:**
1. Verify your Access Key ID is correct
2. Check that the Access Key is active in the RAM console
3. Ensure you're using the correct Alibaba Cloud account

## Additional Permissions for OSS Recording

If you need to verify OSS bucket access (not included in this diagnostic skill), you'll also need:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetBucket",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:<bucket-name>",
        "acs:oss:*:*:<bucket-name>/*"
      ]
    }
  ]
}
```

## Security Best Practices

1. **Use RAM users, not root account** - Never use your Alibaba Cloud root account for daily operations
2. **Principle of least privilege** - Only grant the minimum permissions required
3. **Use temporary credentials** - Consider using STS tokens for short-lived access
4. **Rotate credentials regularly** - Update Access Keys every 90 days
5. **Enable MFA** - Require multi-factor authentication for RAM users
6. **Audit regularly** - Review RAM user permissions and access logs

## References

- [RAM Policy Language](https://help.aliyun.com/ram/policy-elements)
- [ApsaraVideo Live RAM Authorization](https://help.aliyun.com/live/user-guide/live-stream-recording)
- [RAM Best Practices](https://help.aliyun.com/zh/ram/product-overview/best-practices-for-identity-and-access-control)
