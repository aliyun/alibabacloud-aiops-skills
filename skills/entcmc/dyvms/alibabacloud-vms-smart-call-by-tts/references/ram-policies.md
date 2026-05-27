# RAM Policy — Alibaba Cloud VMS Smart Voice Call

## Minimum Required Policy

The following policy grants the exact RAM permissions required to call `SubmitIntent` and `QueryCallDetailByCallId`. Action list is enumerated to the minimum set (no wildcards).

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dyvms:SubmitIntent",
        "dyvms:QueryCallDetailByCallId"
      ],
      "Resource": [
        "acs:dyvms:*:*:*"
      ]
    }
  ]
}
```

## Field Reference

| Field | Value | Description |
|---|---|---|
| `Action[0]` | `dyvms:SubmitIntent` | Initiates an AI-driven smart voice call |
| `Action[1]` | `dyvms:QueryCallDetailByCallId` | Queries the call detail record (CDR) by `CallId` |
| `Resource` | `acs:dyvms:*:*:*` | All VMS resources under the account (resource-level granularity is not supported by dyvmsapi) |

## Applicability

| Caller Identity | Policy Required |
|---|---|
| Root account AK | No (root account has all permissions implicitly) |
| RAM sub-account | **Yes** — attach this policy to the user or to a group containing the user |
| STS temporary credential | **Yes** — the role being assumed must include this policy |

## How to Grant

### Option 1: Console

1. Sign in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions → Policies → Create Policy**
3. Choose **Script Editor** mode and paste the JSON above
4. Attach the policy to the target RAM user / group / role

### Option 2: CLI

```bash
# Create the custom policy
aliyun ram create-policy \
  --policy-name SubmitIntentAccess \
  --policy-document '{
    "Version": "1",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["dyvms:SubmitIntent", "dyvms:QueryCallDetailByCallId"],
      "Resource": ["acs:dyvms:*:*:*"]
    }]
  }' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"

# Attach the policy to a RAM user
aliyun ram attach-policy-to-user \
  --policy-name SubmitIntentAccess \
  --policy-type Custom \
  --user-name <RAM_USER_NAME> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

## Permission Errors

| Code | Meaning | Resolution |
|---|---|---|
| `Forbidden.RAM` / `NoPermission` | The sub-account lacks `dyvms:SubmitIntent` or `dyvms:QueryCallDetailByCallId` | Re-attach the policy above and retry. If `SubmitIntent` returns a permission error referring to address-book read access, see the **Known Limitation** below. |
| `InvalidAccessKeyId.NotFound` | AK does not exist or has been disabled | Verify the AK status in the [AK Management Console](https://ram.console.aliyun.com/manage/ak) |

## Known Limitation — Address Book Read Permission

`SubmitIntent` internally reads the caller's address book to perform LLM-driven contact matching. If the runtime returns `Forbidden.RAM` referencing address-book read access (an internal action that is **not enumerable** through the standard RAM Action namespace), this Skill cannot work around it via additional explicit Actions — wildcard Actions such as `dyvms:*` are **not permitted by this Skill's least-privilege baseline**, and even granting them would not necessarily expose the internal address-book Action.

If — and only if — that specific failure is observed at runtime, contact Alibaba Cloud Voice Service technical support to have the address-book read permission granted on the account / role server-side. Do **not** broaden the local RAM policy to wildcards as a workaround.

The minimum-Action policy at the top of this document is the canonical, recommended grant for this Skill.
