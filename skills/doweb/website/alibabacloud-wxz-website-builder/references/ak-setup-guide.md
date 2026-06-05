# Alibaba Cloud AccessKey Setup Guide

This guide helps users obtain and configure Alibaba Cloud AccessKey credentials from scratch.

## Step 1: Log in to Alibaba Cloud Console

Open https://www.aliyun.com and log in with your Alibaba Cloud account.

> If you don't have an account yet, click "Free Registration" to create one.

## Step 2: Create a RAM User (Recommended)

**IMPORTANT**: Do NOT use your root account AccessKey in production. Always create a RAM (Resource Access Management) sub-user with least-privilege permissions.

1. Go to RAM Console: https://ram.console.aliyun.com/users
2. Click **"Create User"**
3. Fill in:
   - Login Name: e.g. `aistaff-builder`
   - Display Name: e.g. `aistaff-builder`
   - Access Mode: check **"OpenAPI Access"** (this generates AccessKey)
4. Click **"OK"**
5. **IMPORTANT**: On the success page, immediately save the **AccessKey ID** and **AccessKey Secret** — the Secret is only shown once!

## Step 3: Grant Permissions

For the AI Staff Website Builder, the RAM user needs a custom policy with these specific Actions (least-privilege). See `references/ram-policies.md` for the full permission list and policy JSON.

1. In RAM Console → Users → click the user → **"Permissions"** tab
2. Click **"Grant Permission"**
3. Create a custom policy and attach it (see `references/ram-policies.md` for the complete policy JSON):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "zero2staff:CreateAIStaffConversation",
        "zero2staff:CreateAIStaffChat",
        "zero2staff:RetryAIStaffChat",
        "zero2staff:ListAIStaffChatEvents",
        "zero2staff:ListAIStaffChatMessages",
        "zero2staff:GetAIStaffPreviewUrl"
      ],
      "Resource": "*"
    }
  ]
}
```

## Step 4: Configure Credentials

### Option A: Environment Variables (Recommended for development)

```bash
export ALIBABACLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABACLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
export ALIBABACLOUD_REGION_ID="cn-hangzhou"   # optional, defaults to cn-hangzhou
```

Add these to your `~/.bashrc`, `~/.zshrc`, or shell profile for persistence.

### Option B: Credentials File (Recommended for multi-profile setup)

Create or edit `~/.alibabacloud/credentials`:

```ini
[default]
type = access_key
access_key_id = your-access-key-id
access_key_secret = your-access-key-secret
```

## Step 5: Verify Setup

```bash
cd skills/ai/service/alibabacloud-wxz-website-builder
python scripts/aistaff_api.py create-conversation --text "test connectivity"
```

If you see a JSON response with `ConversationId`, the setup is successful.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ALIBABACLOUD_ACCESS_KEY_ID ... must be set` | Environment variables not set | Export the variables or create credentials file |
| `InvalidAccessKeyId` | Wrong AccessKey ID | Double-check the AccessKey ID in RAM Console |
| `SignatureDoesNotMatch` | Wrong AccessKey Secret | Regenerate the AccessKey in RAM Console |
| `Forbidden` / `NoPermission` | Missing permissions | Add required policy to the RAM user |

## Security Best Practices

- Never commit AccessKey to git repositories
- Use environment variables or credentials files, never hardcode in scripts
- Rotate AccessKey regularly (RAM Console → User → AccessKey → Create New → Disable Old)
- For CI/CD, use STS (Security Token Service) for temporary credentials
- Enable MFA for the root account
