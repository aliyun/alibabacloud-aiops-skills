# RAM Permissions

The `tablestore-agent-storage` SDK requires the following Alibaba Cloud RAM permissions.

---

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Required Permissions

This SDK follows the principle of least privilege. You need to create a custom RAM policy and grant authorization. See "Custom Permission Policy" below for details.

---

## Authorization Methods

### Method 1: Create and Grant Custom Policy via Console (Recommended)

1. Log in to the [RAM Console](https://ram.console.aliyun.com/policies)
2. Click "Create Policy", select "JSON" mode, and paste the "Custom Permission Policy" content below
3. Enter a policy name such as `TablestoreAgentStoragePolicy`, then click Confirm
4. Go to the [RAM User List](https://ram.console.aliyun.com/users), find the target user, and click "Add Permissions"
5. Select "Custom Policy", search for and select the newly created policy

### Method 2: Create and Grant via CLI

```bash
# 1. Create custom policy (save the policy JSON as policy.json first)
aliyun ram create-policy \
  --policy-name TablestoreAgentStoragePolicy \
  --policy-document file://policy.json \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Grant custom policy
aliyun ram attach-policy-to-user \
  --policy-type Custom \
  --policy-name TablestoreAgentStoragePolicy \
  --user-name <your-ram-user-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## API Permissions Details

### Tablestore (OTS) Instance APIs (Required only when auto-creating instances)

| API Operation | Corresponding CLI Command | Required Permission |
|---------|-------------|---------|
| InsertInstance | `create_instance` | `ots:InsertInstance` |
| ListInstance | `list_instance` | `ots:ListInstance` |
| GetInstance | `describe_instance` | `ots:GetInstance` |

### Tablestore (OTS) Knowledge Base APIs

| API Operation | Corresponding SDK Method | Required Permission |
|---------|-------------|---------|
| CreateKnowledgeBase | `create_knowledge_base` | `ots:CreateKnowledgeBase` |
| DescribeKnowledgeBase | `describe_knowledge_base` | `ots:DescribeKnowledgeBase` |
| ListKnowledgeBase | `list_knowledge_base` | `ots:ListKnowledgeBase` |
| AddDocuments | `add_documents` | `ots:AddDocuments` |
| GetDocument | `get_document` | `ots:GetDocument` |
| ListDocuments | `list_documents` | `ots:ListDocuments` |
| Retrieve | `retrieve` | `ots:Retrieve` |

### OSS Related APIs (Required only when uploading local files)

| API Operation | Corresponding SDK Method | Required Permission |
|---------|-------------|---------|
| CreateBucket | Initialize OSS Bucket (first time use) | `oss:CreateBucket` |
| PutObject | `upload_documents` (internal file upload to OSS) | `oss:PutObject` |

---

## Custom Permission Policy

Create a custom RAM policy using the following JSON, granting only the minimum permissions required by the SDK:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:InsertInstance",
        "ots:ListInstance",
        "ots:GetInstance"
      ],
      "Resource": "acs:ots:*:*:instance/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ots:CreateKnowledgeBase",
        "ots:DescribeKnowledgeBase",
        "ots:ListKnowledgeBase",
        "ots:AddDocuments",
        "ots:GetDocument",
        "ots:ListDocuments",
        "ots:Retrieve"
      ],
      "Resource": "acs:ots:*:*:instance/*/table/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:CreateBucket",
        "oss:PutObject",
        "oss:GetObject",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:<your-bucket-name>",
        "acs:oss:*:*:<your-bucket-name>/*"
      ]
    }
  ]
}
```

> Replace `<your-bucket-name>` with the actual OSS bucket name. OSS-related permissions are only required when using the local file upload feature. If not used, the second Statement can be deleted.

---

## AliyunOTSAccessingOSSRole Authorization

When using OSS-related features (such as uploading local files or importing OSS documents), Tablestore needs permission to access OSS on behalf of the user. This is achieved through the **AliyunOTSAccessingOSSRole** service-linked role.

### What Is AliyunOTSAccessingOSSRole?

`AliyunOTSAccessingOSSRole` is a RAM service-linked role that grants Tablestore the permission to read and write objects in your OSS buckets. Without this role, knowledge base operations involving OSS (e.g., `upload_documents`, `add_documents`) will fail with permission errors.

### How to Authorize

Click the following link to create and authorize the `AliyunOTSAccessingOSSRole` role via the RAM Console:

[Authorize AliyunOTSAccessingOSSRole](https://ram.console.aliyun.com/authorize?request=%7B%22payloads%22%3A%5B%7B%22missionId%22%3A%22Tablestore.RoleForOTSAccessingOSS%22%7D%5D%2C%22callback%22%3A%22https%3A%2F%2Fotsnext.console.aliyun.com%2F%22%2C%22referrer%22%3A%22Tablestore%22%7D)

After clicking the link:
1. Log in to the RAM Console (if not already logged in)
2. Review the role permissions and click **Confirm Authorization**
3. The role will be automatically created and attached to your account

> **Note:** This is a one-time setup per Alibaba Cloud account. If the role has already been authorized, no further action is needed.

---

## References

- RAM Console: https://ram.console.aliyun.com/
- OTS Permissions: https://help.aliyun.com/zh/tablestore/developer-reference/overview-of-ram
- OSS Permissions: https://help.aliyun.com/zh/oss/developer-reference/overview-of-ram
