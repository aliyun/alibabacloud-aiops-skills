# Notification users

A notification user stores an individual's email or telephone destinations and channel
switches. Action policies can select users directly or through a group.
Creating a user does not create or authorize a RAM identity.

## Manage users

Use [ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.common.user`; ID/tag map to `user_id` / `user_name`.

## `value` parameters

| Field | JSON type | Meaning |
| --- | --- | --- |
| `user_id` | string | Stable user ID, unique within the Alibaba Cloud account. Action policies and group membership refer to this value. |
| `user_name` | string | Human-readable user name. |
| `email` | array of strings | Email destinations. Use an array even for one address. |
| `country_code` | string | Telephone country/region code without the leading `+`, for example `86`. |
| `phone` | string | Telephone number used by enabled SMS or voice channels. |
| `enabled` | boolean | Enables or disables this SLS notification user. |
| `sms_enabled` | boolean | Allows action policies to send SMS to this user. |
| `voice_enabled` | boolean | Allows action policies to call this user. |

Provide at least one usable email address or telephone number. A channel switch
does not replace the destination itself. Voice notifications support only
mainland China telephone numbers with country code `86`; see
[notification channels](../action-policies/channels.md).

## Simple example

Illustrative email-only value:

```json
{
  "user_id": "example-user",
  "user_name": "Example on-call engineer",
  "enabled": true,
  "email": ["oncall@example.com"],
  "country_code": "86",
  "phone": "",
  "sms_enabled": false,
  "voice_enabled": false
}
```

Replace the example address with the intended recipient before use. Configure
the recipient's telephone number and the relevant switches before selecting SMS or
voice in an action policy.

A change to a user can affect every group and policy that references it. Known group
memberships and direct policy references provide context for deletion. Enabling or
disabling the user uses the
[ResourceRecord update](../api/resource-records.md#update-an-existing-record)
to change `enabled`.

The account-level identifier and user requirements follow the
[official user and group guide](https://help.aliyun.com/zh/sls/create-users-and-user-groups).
